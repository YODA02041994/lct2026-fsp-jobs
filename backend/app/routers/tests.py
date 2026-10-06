"""Тестирование на грейд: сеанс, блоки, ответы, итог, применение грейда."""
import random
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..catalog import SPECIALIZATIONS, GRADES
from ..db import get_db
from ..deps import current_candidate
from ..models import Candidate, TestSession, TestItem, Template, CandidateSkill, GradeHistory, GRADES as GRADE_CODES
from ..schemas import SessionStart, AnswerIn
from ..services.skills_catalog import normalize_skill
from ..services.testing.engine import pick_templates, make_item, grade_item, eap, next_level_after_block, decide, REGISTRY, load_all, technology_summary
from ..services.views import session_view, candidate_profile, grade_change_available_at
from ..services.audit import log

router = APIRouter(prefix="/tests", tags=["testing"])
SPEC_BANK = {c: hb for c, _, _, hb, _ in SPECIALIZATIONS}


def _cooldown_ok(c: Candidate) -> bool:
    at = grade_change_available_at(c)
    return at is None or at <= datetime.now(timezone.utc)


@router.get("/options")
def options(c: Candidate = Depends(current_candidate)):
    return {"specializations": [{"code": s[0], "name": s[1], "has_bank": s[3]} for s in SPECIALIZATIONS],
            "grades": [{"code": g[0], "title": g[1], "description": g[2]} for g in GRADES],
            "can_change_grade": _cooldown_ok(c), "grade_change_available_at": grade_change_available_at(c),
            "current_grade": c.grade}


def _issue_block(db: Session, s: TestSession, level: str, rng: random.Random) -> None:
    used = {it.template_code for it in s.items}
    codes = pick_templates(s.specialization_code, level, s.declared_skills, s.block_size, rng, exclude=used,
                           has_bank=SPEC_BANK.get(s.specialization_code, False))
    if not codes:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Банк заданий пуст для этого уровня")
    start = len(s.items)
    for i, code in enumerate(codes):
        seed = rng.randrange(1, 2**31)
        payload, key = make_item(code, seed)
        db.add(TestItem(session_id=s.id, template_code=code, seed=seed, block_no=s.current_block, order_no=start + i + 1,
                        level=level, payload=payload, answer_key=key))
    db.flush()
    db.refresh(s)


@router.post("/sessions", status_code=201, responses={409: {"description": "Есть незавершённый сеанс или смена грейда пока недоступна"}})
def start(data: SessionStart, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    if data.specialization_code not in SPEC_BANK:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неизвестная специализация")
    active = db.scalar(select(TestSession).where(TestSession.candidate_id == c.id, TestSession.status == "active"))
    if active:
        return session_view(active)
    if c.grade and not _cooldown_ok(c):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Сменить грейд можно не раньше {grade_change_available_at(c).date().isoformat()}")
    settings = get_settings()
    load_all()
    skills = []
    for raw in data.declared_skills:
        code = normalize_skill(raw) or raw.strip().lower()
        if code and code not in skills:
            skills.append(code)
    s = TestSession(candidate_id=c.id, specialization_code=data.specialization_code, claimed_grade=data.claimed_grade,
                    declared_skills=skills, current_level=data.claimed_grade, block_size=settings.test_block_size,
                    blocks_total=settings.test_blocks)
    db.add(s)
    db.flush()
    c.specialization_code = data.specialization_code
    c.claimed_grade = data.claimed_grade
    for code in skills:
        if not any(k.skill == code for k in c.skills):
            db.add(CandidateSkill(candidate_id=c.id, skill=code, source="profile"))
    _issue_block(db, s, s.current_level, random.Random())
    log(db, c.user_id, "test_started", "test_session", s.id, specialization=s.specialization_code, claimed=s.claimed_grade)
    db.commit()
    db.refresh(s)
    return session_view(s)


def _own_session(sid: int, c: Candidate, db: Session) -> TestSession:
    s = db.get(TestSession, sid)
    if not s or s.candidate_id != c.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сеанс не найден")
    return s


@router.get("/sessions")
def history(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    rows = db.scalars(select(TestSession).where(TestSession.candidate_id == c.id).order_by(TestSession.id.desc())).all()
    return [{"id": s.id, "status": s.status, "specialization_code": s.specialization_code, "claimed_grade": s.claimed_grade,
             "result_grade": s.result_grade, "decision": s.decision, "theta": s.theta, "started_at": s.started_at,
             "finished_at": s.finished_at, "items_total": len(s.items), "correct_total": sum(1 for it in s.items if it.correct)} for s in rows]


@router.get("/sessions/{sid}")
def get_session(sid: int, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    return session_view(_own_session(sid, c, db), reveal=True)


@router.post("/sessions/{sid}/answer")
def answer(sid: int, data: AnswerIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    s = _own_session(sid, c, db)
    if s.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Сеанс завершён")
    it = db.get(TestItem, data.item_id)
    if not it or it.session_id != s.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задание не найдено")
    if it.candidate_answer is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ответ уже сохранён")
    limit = get_settings().test_item_seconds
    elapsed = (datetime.now(timezone.utc) - it.issued_at).total_seconds()
    it.candidate_answer = {"value": data.answer}
    it.answered_at = datetime.now(timezone.utc)
    it.correct = grade_item(it.template_code, it.answer_key, data.answer) and elapsed <= limit * len([x for x in s.items if x.block_no == it.block_no]) + 60
    tpl = db.get(Template, it.template_code)
    if tpl:
        tpl.answered += 1
        tpl.correct += int(it.correct)
    block_items = [x for x in s.items if x.block_no == it.block_no]
    block_done = all(x.candidate_answer is not None for x in block_items)
    db.commit()
    return {"item_id": it.id, "accepted": True, "block_done": block_done, "session_status": s.status}


def _finish(db: Session, s: TestSession, c: Candidate) -> None:
    responses = [(REGISTRY[it.template_code].difficulty, bool(it.correct)) for it in s.items if it.candidate_answer is not None]
    theta, sd = eap(responses)
    s.theta, s.theta_sd = theta, sd
    s.result_grade, s.decision = decide(theta, sd, s.claimed_grade)
    s.status = "finished"
    s.finished_at = datetime.now(timezone.utc)
    # подтверждение технологий тестом
    by_tech = {row["skill"]: row for row in technology_summary([(it.template_code, it.correct) for it in s.items])}
    existing = {k.skill: k for k in c.skills}
    for skill, row in by_tech.items():
        share = row["correct"] / row["total"] if row["total"] else 0
        k = existing.get(skill)
        if not k:
            k = CandidateSkill(candidate_id=c.id, skill=skill, source="test")
            db.add(k)
        k.test_score = round(share, 2)
        k.confirmed_by_test = share >= 0.5
    # грейд: подтверждённый заявленный применяется сразу; предложения — по кнопке
    if s.decision == "confirmed":
        _apply_grade(db, c, s, s.result_grade)
    c.last_active_at = datetime.now(timezone.utc)


def _apply_grade(db: Session, c: Candidate, s: TestSession, new_grade: str) -> None:
    if c.grade != new_grade:
        db.add(GradeHistory(candidate_id=c.id, session_id=s.id, old_grade=c.grade, new_grade=new_grade))
        c.grade = new_grade
        c.grade_changed_at = datetime.now(timezone.utc)
        log(db, c.user_id, "grade_changed", "candidate", c.id, new=new_grade, session=s.id)
    elif c.grade_changed_at is None:
        c.grade_changed_at = datetime.now(timezone.utc)


@router.post("/sessions/{sid}/next")
def next_block(sid: int, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    s = _own_session(sid, c, db)
    if s.status != "active":
        return session_view(s, reveal=True)
    block_items = [x for x in s.items if x.block_no == s.current_block]
    if any(x.candidate_answer is None for x in block_items):
        raise HTTPException(status.HTTP_409_CONFLICT, "Сначала ответьте на все задания блока")
    outcome = next_level_after_block(s.current_level, sum(1 for x in block_items if x.correct), len(block_items), s.current_block, s.blocks_total)
    if outcome.next_level is None:
        _finish(db, s, c)
    else:
        s.current_block += 1
        s.current_level = outcome.next_level
        _issue_block(db, s, outcome.next_level, random.Random())
    db.commit()
    db.refresh(s)
    return session_view(s, reveal=(s.status == "finished"))


@router.post("/sessions/{sid}/apply")
def apply_suggestion(sid: int, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    s = _own_session(sid, c, db)
    if s.status != "finished" or s.decision not in ("suggest_lower", "suggest_higher"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Для этого сеанса нет предложения по грейду")
    if s.decision == "suggest_higher":
        _apply_grade(db, c, s, s.result_grade)
    else:
        # понижение не принудительное: кандидат соглашается пройти тест ниже — грейд ставится по результату (result_grade)
        _apply_grade(db, c, s, s.result_grade)
    s.decision = "applied"
    db.commit()
    db.refresh(c)
    return candidate_profile(c, db)
