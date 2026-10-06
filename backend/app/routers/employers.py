"""Кабинет работодателя: профиль, потребности, подборки, банк кандидатов, карточка."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from ..catalog import DEFAULT_WEIGHTS
from ..db import get_db
from ..deps import current_employer
from ..models import Employer, Need, Selection, SelectionVersion, Candidate, Invitation, Application, Vacancy, GRADES
from ..schemas import EmployerUpdate, NeedIn, SelectionIn, RefineIn
from ..services.need_parser import parse
from ..services.skills_catalog import normalize_skill
from ..services.matching import build_selection, candidate_pool, score_candidate, last_thetas
from ..services.views import employer_view, candidate_card
from ..services.audit import log

router = APIRouter(tags=["employer"])


def contacts_unlocked(db: Session, employer_id: int, candidate_id: int) -> bool:
    inv = db.scalar(select(Invitation.id).where(Invitation.employer_id == employer_id, Invitation.candidate_id == candidate_id, Invitation.status == "accepted"))
    if inv:
        return True
    app_ = db.scalar(select(Application.id).join(Vacancy, Vacancy.id == Application.vacancy_id)
                     .where(Vacancy.employer_id == employer_id, Application.candidate_id == candidate_id))
    return bool(app_)


def _norm_stack(items):
    out = []
    for raw in items or []:
        code = normalize_skill(raw) or raw.strip().lower()
        if code and code not in out:
            out.append(code)
    return out


@router.get("/employers/me")
def me(e: Employer = Depends(current_employer)):
    return employer_view(e)


@router.put("/employers/me")
def update(data: EmployerUpdate, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return employer_view(e)


def _need_view(n: Need) -> dict:
    return {"id": n.id, "title": n.title, "text": n.text, "specialization_code": n.specialization_code, "grade": n.grade,
            "stack": n.stack, "salary_min": n.salary_min, "salary_max": n.salary_max, "work_format": n.work_format,
            "city": n.city, "created_at": n.created_at}


@router.post("/needs", status_code=201)
def create_need(data: NeedIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    ext = parse(f"{data.title}. {data.text}")
    if data.salary_min is not None and data.salary_max is not None and data.salary_min > data.salary_max:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Зарплата «от» больше зарплаты «до»")
    if data.grade and data.grade not in GRADES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неизвестный грейд")
    n = Need(employer_id=e.id, title=data.title, text=data.text,
             specialization_code=data.specialization_code or ext["specialization_code"],
             grade=data.grade or ext["grade"],
             stack=_norm_stack(data.stack) if data.stack else ext["stack"],
             salary_min=data.salary_min if data.salary_min is not None else ext["salary_min"],
             salary_max=data.salary_max if data.salary_max is not None else ext["salary_max"],
             work_format=data.work_format or "", city=data.city or "")
    db.add(n)
    db.commit()
    db.refresh(n)
    return {"need": _need_view(n), "extracted": ext}


@router.get("/needs")
def list_needs(e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    return [_need_view(n) for n in db.scalars(select(Need).where(Need.employer_id == e.id).order_by(Need.id.desc())).all()]


def _selection_view(db: Session, sel: Selection, employer_id: int) -> dict:
    versions = []
    for v in sel.versions:
        cards = []
        ids = [r["candidate_id"] for r in v.results]
        cands = {c.id: c for c in db.scalars(select(Candidate).where(Candidate.id.in_(ids))).all()} if ids else {}
        for r in v.results:
            c = cands.get(r["candidate_id"])
            if not c:
                continue
            cards.append(candidate_card(c, r, contacts_unlocked(db, employer_id, c.id), db))
        versions.append({"id": v.id, "version_no": v.version_no, "filters": v.filters, "weights": v.weights, "created_at": v.created_at,
                         "categories": v.categories, "results": cards})
    return {"id": sel.id, "need_id": sel.need_id, "created_at": sel.created_at, "versions": versions}


def _need_dict(n: Need | None) -> dict:
    if not n:
        return {}
    return {"specialization_code": n.specialization_code, "grade": n.grade, "stack": n.stack, "salary_min": n.salary_min,
            "salary_max": n.salary_max, "work_format": n.work_format}


@router.post("/needs/{nid}/selection", status_code=201)
def make_selection(nid: int, data: SelectionIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    n = db.get(Need, nid)
    if not n or n.employer_id != e.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Потребность не найдена")
    weights = {**DEFAULT_WEIGHTS, **(data.weights or {})}
    cats, results = build_selection(db, _need_dict(n), {}, weights)
    sel = Selection(employer_id=e.id, need_id=n.id)
    db.add(sel)
    db.flush()
    db.add(SelectionVersion(selection_id=sel.id, version_no=1, filters={}, weights=weights, categories=cats, results=results))
    log(db, e.user_id, "selection_built", "need", n.id, candidates=len(results))
    db.commit()
    db.refresh(sel)
    return _selection_view(db, sel, e.id)


@router.post("/selections/{sid}/refine")
def refine(sid: int, data: RefineIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    sel = db.get(Selection, sid)
    if not sel or sel.employer_id != e.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Подборка не найдена")
    n = db.get(Need, sel.need_id) if sel.need_id else None
    f = {k: v for k, v in data.filters.model_dump().items() if v not in (None, [], "")}
    if "skills" in f:
        f["skills"] = _norm_stack(f["skills"])
    prev = sel.versions[-1]
    weights = {**prev.weights, **(data.weights or {})}
    cats, results = build_selection(db, _need_dict(n), f, weights)
    db.add(SelectionVersion(selection_id=sel.id, version_no=prev.version_no + 1, filters=f, weights=weights, categories=cats, results=results))
    db.commit()
    db.refresh(sel)
    return _selection_view(db, sel, e.id)


@router.get("/selections")
def list_selections(e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    rows = db.scalars(select(Selection).where(Selection.employer_id == e.id).order_by(Selection.id.desc())).all()
    return [{"id": s.id, "need_id": s.need_id, "created_at": s.created_at, "versions": len(s.versions),
             "candidates": len(s.versions[-1].results) if s.versions else 0} for s in rows]


@router.get("/selections/{sid}")
def get_selection(sid: int, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    sel = db.get(Selection, sid)
    if not sel or sel.employer_id != e.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Подборка не найдена")
    return _selection_view(db, sel, e.id)


@router.get("/candidates/search")
def search(specialization_code: str | None = None, grade: str | None = None, skills: str | None = None,
           fsp_only: bool = False, q: str | None = None, city: str | None = None, limit: int = Query(30, le=100),
           e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    """Банк кандидатов: та же формула с нулевыми слагаемыми потребности (ТЗ: ранжирование внутри категории)."""
    f = {"specialization_code": specialization_code, "grades": [grade] if grade else None,
         "skills": _norm_stack(skills.split(",")) if skills else None, "fsp_only": fsp_only, "city": city}
    f = {k: v for k, v in f.items() if v}
    pool = candidate_pool(db, f)
    if q:
        ql = q.lower()
        pool = [c for c in pool if ql in (c.about or "").lower() or any(ql in k.skill for k in c.skills) or any(ql in r.lower() for r in c.roles)]
    thetas = last_thetas(db, [c.id for c in pool])
    need = {"stack": f.get("skills") or [], "grade": None}
    scored = sorted(((c, score_candidate(c, need, {}, thetas.get(c.id))) for c in pool), key=lambda x: (-x[1]["score"], x[0].id))
    return [candidate_card(c, sc, contacts_unlocked(db, e.id, c.id), db) for c, sc in scored[:limit]]


@router.get("/candidates/{cid}/card")
def card(cid: int, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    c = db.get(Candidate, cid)
    if not c or not c.visible_to_employers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Кандидат не найден или скрыт")
    unlocked = contacts_unlocked(db, e.id, c.id)
    thetas = last_thetas(db, [c.id])
    sc = score_candidate(c, {"stack": [], "grade": None}, {}, thetas.get(c.id))
    if unlocked:
        log(db, e.user_id, "contacts_viewed", "candidate", c.id)
        db.commit()
    return candidate_card(c, sc, unlocked, db)
