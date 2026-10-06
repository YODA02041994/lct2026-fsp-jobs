"""Приглашения (инициатива работодателя), вакансии и отклики (инициатива кандидата), короткие задания."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..deps import current_candidate, current_employer, current_user
from ..models import (Candidate, Employer, Invitation, Vacancy, Application, ShortTask, ShortTaskAnswer, User, GRADES, WORK_FORMATS)
from ..schemas import InvitationIn, RespondIn, VacancyIn, ApplyIn, ApplicationStatusIn, ShortTaskIn, ShortTaskAnswerIn, ScoreIn
from ..services.skills_catalog import normalize_skill, extract_skills, skill_name
from ..services.views import candidate_card
from ..services.matching import score_candidate, last_thetas
from ..services.audit import log
from .employers import contacts_unlocked

router = APIRouter(tags=["contacts"])
now = lambda: datetime.now(timezone.utc)  # noqa: E731


def _inv_view(inv: Invitation, db: Session, for_employer: bool) -> dict:
    e = db.get(Employer, inv.employer_id)
    c = db.get(Candidate, inv.candidate_id)
    v = db.get(Vacancy, inv.vacancy_id) if inv.vacancy_id else None
    out = {"id": inv.id, "status": inv.status, "message": inv.message, "salary_min": inv.salary_min, "salary_max": inv.salary_max,
           "contact_method": inv.contact_method, "vacancy": {"id": v.id, "title": v.title} if v else None,
           "sent_at": inv.sent_at, "viewed_at": inv.viewed_at, "responded_at": inv.responded_at,
           "company_name": e.company_name if e else "", "company": {"id": e.id, "name": e.company_name, "industry": e.industry, "city": e.city, "website": e.website} if e else None}
    if for_employer:
        out["candidate"] = {"candidate_id": c.id, "alias": c.alias, "grade": c.grade, "specialization_code": c.specialization_code}
        if inv.status == "accepted":
            out["contacts"] = {"full_name": c.full_name, "phone": c.phone, "telegram": c.telegram, "email": c.user.email if c.user else ""}
    return out


# --- приглашения ---------------------------------------------------------------------------------

@router.post("/invitations", status_code=201)
def invite(data: InvitationIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    if data.salary_min > data.salary_max:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Зарплата «от» больше зарплаты «до»")
    c = db.get(Candidate, data.candidate_id)
    if not c or not c.visible_to_employers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Кандидат не найден или скрыт")
    if data.vacancy_id:
        v = db.get(Vacancy, data.vacancy_id)
        if not v or v.employer_id != e.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Вакансия не найдена")
    dup = db.scalar(select(Invitation).where(Invitation.employer_id == e.id, Invitation.candidate_id == c.id, Invitation.status.in_(["sent", "viewed"])))
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, "У этого кандидата уже есть ваше приглашение без ответа")
    if not e.company_name:
        raise HTTPException(status.HTTP_409_CONFLICT, "Сначала заполните название компании в профиле")
    inv = Invitation(employer_id=e.id, candidate_id=c.id, selection_version_id=data.selection_version_id, vacancy_id=data.vacancy_id,
                     message=data.message, salary_min=data.salary_min, salary_max=data.salary_max, contact_method=data.contact_method)
    db.add(inv)
    log(db, e.user_id, "invitation_sent", "candidate", c.id)
    db.commit()
    db.refresh(inv)
    return _inv_view(inv, db, True)


@router.get("/employers/me/invitations")
def employer_invitations(e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    rows = db.scalars(select(Invitation).where(Invitation.employer_id == e.id).order_by(Invitation.id.desc())).all()
    return [_inv_view(i, db, True) for i in rows]


@router.get("/candidates/me/invitations")
def my_invitations(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    rows = db.scalars(select(Invitation).where(Invitation.candidate_id == c.id).order_by(Invitation.id.desc())).all()
    return [_inv_view(i, db, False) for i in rows]


def _own_inv(iid: int, c: Candidate, db: Session) -> Invitation:
    inv = db.get(Invitation, iid)
    if not inv or inv.candidate_id != c.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Приглашение не найдено")
    return inv


@router.post("/invitations/{iid}/view")
def view_invitation(iid: int, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    inv = _own_inv(iid, c, db)
    if inv.status == "sent":
        inv.status, inv.viewed_at = "viewed", now()
        db.commit()
    return _inv_view(inv, db, False)


@router.post("/invitations/{iid}/respond")
def respond(iid: int, data: RespondIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    inv = _own_inv(iid, c, db)
    if inv.status in ("accepted", "declined"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ответ уже дан")
    inv.status = "accepted" if data.decision == "accept" else "declined"
    inv.responded_at = now()
    if inv.viewed_at is None:
        inv.viewed_at = inv.responded_at
    c.last_active_at = now()
    log(db, c.user_id, "invitation_" + inv.status, "invitation", inv.id, employer=inv.employer_id, contacts_opened=(inv.status == "accepted"))
    db.commit()
    return _inv_view(inv, db, False)


# --- вакансии и отклики --------------------------------------------------------------------------

def _vac_view(v: Vacancy, db: Session, full: bool = False) -> dict:
    e = db.get(Employer, v.employer_id)
    out = {"id": v.id, "title": v.title, "company_name": e.company_name if e else "", "specialization_code": v.specialization_code,
           "grade": v.grade, "stack": v.stack, "stack_names": [skill_name(s) for s in v.stack], "salary_min": v.salary_min, "salary_max": v.salary_max,
           "work_format": v.work_format, "city": v.city, "status": v.status, "created_at": v.created_at}
    if full:
        out["description"] = v.description
        out["company"] = {"name": e.company_name, "description": e.description, "industry": e.industry, "city": e.city, "website": e.website} if e else None
    return out


def _check_vacancy(data: VacancyIn):
    if data.salary_min > data.salary_max:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Зарплата «от» больше зарплаты «до»")
    if data.grade and data.grade not in GRADES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неизвестный грейд")
    if data.work_format and data.work_format not in WORK_FORMATS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неизвестный формат работы")


@router.post("/vacancies", status_code=201)
def create_vacancy(data: VacancyIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    _check_vacancy(data)
    stack = [normalize_skill(s) or s.lower() for s in (data.stack or [])] or extract_skills(data.title + " " + data.description)
    v = Vacancy(employer_id=e.id, title=data.title, description=data.description, specialization_code=data.specialization_code,
                grade=data.grade, stack=stack, salary_min=data.salary_min, salary_max=data.salary_max, work_format=data.work_format,
                city=data.city, status=data.status or "open")
    db.add(v)
    db.commit()
    db.refresh(v)
    return _vac_view(v, db, True)


@router.put("/vacancies/{vid}")
def update_vacancy(vid: int, data: VacancyIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    v = db.get(Vacancy, vid)
    if not v or v.employer_id != e.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вакансия не найдена")
    _check_vacancy(data)
    for k, val in data.model_dump(exclude_unset=True).items():
        if k == "stack":
            val = [normalize_skill(s) or s.lower() for s in (val or [])]
        if val is not None:
            setattr(v, k, val)
    db.commit()
    db.refresh(v)
    return _vac_view(v, db, True)


@router.get("/employers/me/vacancies")
def my_vacancies(e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    rows = db.scalars(select(Vacancy).where(Vacancy.employer_id == e.id).order_by(Vacancy.id.desc())).all()
    out = []
    for v in rows:
        d = _vac_view(v, db, True)
        d["applications_count"] = len(db.scalars(select(Application.id).where(Application.vacancy_id == v.id)).all())
        out.append(d)
    return out


@router.get("/vacancies")
def list_vacancies(specialization_code: str | None = None, grade: str | None = None, skill: str | None = None, q: str | None = None,
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    qr = select(Vacancy).where(Vacancy.status == "open")
    if specialization_code:
        qr = qr.where(Vacancy.specialization_code == specialization_code)
    if grade:
        qr = qr.where(Vacancy.grade == grade)
    rows = db.scalars(qr.order_by(Vacancy.id.desc())).all()
    if skill:
        code = normalize_skill(skill) or skill.lower()
        rows = [v for v in rows if code in v.stack]
    if q:
        ql = q.lower()
        rows = [v for v in rows if ql in v.title.lower() or ql in v.description.lower()]
    return [_vac_view(v, db) for v in rows]


@router.get("/vacancies/{vid}")
def get_vacancy(vid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = db.get(Vacancy, vid)
    if not v:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вакансия не найдена")
    return _vac_view(v, db, True)


@router.post("/vacancies/{vid}/apply", status_code=201)
def apply(vid: int, data: ApplyIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    v = db.get(Vacancy, vid)
    if not v or v.status != "open":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вакансия не найдена или закрыта")
    if db.scalar(select(Application).where(Application.vacancy_id == vid, Application.candidate_id == c.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Вы уже откликались на эту вакансию")
    a = Application(vacancy_id=vid, candidate_id=c.id, message=data.message)
    db.add(a)
    c.last_active_at = now()
    log(db, c.user_id, "application_sent", "vacancy", vid, contacts_opened=True)
    db.commit()
    db.refresh(a)
    return {"id": a.id, "vacancy": _vac_view(v, db), "status": a.status, "message": a.message, "created_at": a.created_at}


@router.get("/candidates/me/applications")
def my_applications(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    rows = db.scalars(select(Application).where(Application.candidate_id == c.id).order_by(Application.id.desc())).all()
    return [{"id": a.id, "vacancy": _vac_view(db.get(Vacancy, a.vacancy_id), db), "status": a.status, "message": a.message,
             "created_at": a.created_at, "updated_at": a.updated_at} for a in rows]


@router.get("/vacancies/{vid}/applications")
def vacancy_applications(vid: int, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    v = db.get(Vacancy, vid)
    if not v or v.employer_id != e.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вакансия не найдена")
    rows = db.scalars(select(Application).where(Application.vacancy_id == vid).order_by(Application.id.desc())).all()
    thetas = last_thetas(db, [a.candidate_id for a in rows])
    out = []
    for a in rows:
        c = db.get(Candidate, a.candidate_id)
        sc = score_candidate(c, {"stack": v.stack, "grade": v.grade, "salary_min": v.salary_min, "salary_max": v.salary_max, "work_format": v.work_format}, {}, thetas.get(c.id))
        out.append({"id": a.id, "candidate": candidate_card(c, sc, True, db), "message": a.message, "status": a.status, "created_at": a.created_at})
    return out


@router.patch("/applications/{aid}")
def set_application_status(aid: int, data: ApplicationStatusIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    a = db.get(Application, aid)
    v = db.get(Vacancy, a.vacancy_id) if a else None
    if not a or not v or v.employer_id != e.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Отклик не найден")
    a.status = data.status
    db.commit()
    return {"id": a.id, "status": a.status}


@router.get("/vacancies/{vid}/test-preview")
def test_preview(vid: int, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    """Как из описания вакансии формируются задания: технологии → шаблоны → экземпляры."""
    import random
    from ..services.testing.engine import pick_templates, make_item, load_all
    v = db.get(Vacancy, vid)
    if not v or v.employer_id != e.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вакансия не найдена")
    load_all()
    techs = v.stack or extract_skills(v.title + " " + v.description)
    level = v.grade or "middle"
    codes = pick_templates(v.specialization_code or "backend", level, techs, 4, random.Random(vid * 7919), has_bank=True)
    items = [make_item(c, 1000 + i)[0] for i, c in enumerate(codes)]
    return {"technologies": [{"code": t, "name": skill_name(t)} for t in techs], "level": level, "items": items}


# --- короткие задания ------------------------------------------------------------------------------

@router.post("/short-tasks", status_code=201)
def create_task(data: ShortTaskIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    techs = [normalize_skill(s) or s.lower() for s in (data.technologies or [])] or extract_skills(data.title + " " + data.text)
    t = ShortTask(employer_id=e.id, title=data.title, text=data.text, specialization_code=data.specialization_code, technologies=techs)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "title": t.title, "text": t.text, "specialization_code": t.specialization_code, "technologies": t.technologies, "created_at": t.created_at}


@router.get("/employers/me/short-tasks")
def my_tasks(e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    rows = db.scalars(select(ShortTask).where(ShortTask.employer_id == e.id).order_by(ShortTask.id.desc())).all()
    out = []
    for t in rows:
        answers = db.scalars(select(ShortTaskAnswer).where(ShortTaskAnswer.task_id == t.id)).all()
        out.append({"id": t.id, "title": t.title, "text": t.text, "specialization_code": t.specialization_code, "technologies": t.technologies,
                    "active": t.active, "created_at": t.created_at,
                    "answers": [{"id": a.id, "candidate": {"candidate_id": a.candidate_id, "alias": db.get(Candidate, a.candidate_id).alias},
                                 "answer": a.answer, "employer_score": a.employer_score, "created_at": a.created_at} for a in answers]})
    return out


@router.get("/candidates/me/short-tasks")
def candidate_tasks(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    q = select(ShortTask).where(ShortTask.active.is_(True))
    rows = db.scalars(q.order_by(ShortTask.id.desc())).all()
    mine = {a.task_id: a for a in db.scalars(select(ShortTaskAnswer).where(ShortTaskAnswer.candidate_id == c.id)).all()}
    out = []
    for t in rows:
        if t.specialization_code and c.specialization_code and t.specialization_code != c.specialization_code:
            continue
        e = db.get(Employer, t.employer_id)
        a = mine.get(t.id)
        out.append({"id": t.id, "title": t.title, "text": t.text, "company_name": e.company_name if e else "", "technologies": t.technologies,
                    "technology_names": [skill_name(x) for x in t.technologies], "answered": a is not None,
                    "employer_score": a.employer_score if a else None, "created_at": t.created_at})
    return out


@router.post("/short-tasks/{tid}/answer", status_code=201)
def answer_task(tid: int, data: ShortTaskAnswerIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    t = db.get(ShortTask, tid)
    if not t or not t.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задание не найдено")
    if db.scalar(select(ShortTaskAnswer).where(ShortTaskAnswer.task_id == tid, ShortTaskAnswer.candidate_id == c.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ответ уже отправлен")
    a = ShortTaskAnswer(task_id=tid, candidate_id=c.id, answer=data.answer)
    db.add(a)
    c.last_active_at = now()
    db.commit()
    return {"id": a.id, "task_id": tid, "answered": True}


@router.patch("/short-task-answers/{aid}")
def score_answer(aid: int, data: ScoreIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    a = db.get(ShortTaskAnswer, aid)
    t = db.get(ShortTask, a.task_id) if a else None
    if not a or not t or t.employer_id != e.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ответ не найден")
    a.employer_score = data.employer_score
    db.commit()
    return {"id": a.id, "employer_score": a.employer_score}
