"""Кабинет кандидата: профиль, приватность, согласия, достижения."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..deps import current_candidate
from ..models import Candidate, CandidateSkill, Consent, Achievement, WORK_FORMATS
from ..schemas import CandidateUpdate, PrivacyIn, ConsentsIn, AchievementIn
from ..services.skills_catalog import normalize_skill
from ..services.views import candidate_profile, achievement_view
from ..services.audit import log

router = APIRouter(prefix="/candidates/me", tags=["candidate"])


@router.get("")
def me(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    return candidate_profile(c, db)


@router.put("")
def update(data: CandidateUpdate, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    d = data.model_dump(exclude_unset=True)
    skills = d.pop("skills", None)
    if "work_format" in d and d["work_format"] not in ("", None, *WORK_FORMATS):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неизвестный формат работы")
    if d.get("salary_min") and d.get("salary_max") and d["salary_min"] > d["salary_max"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Зарплата «от» больше зарплаты «до»")
    for k, v in d.items():
        setattr(c, k, v)
    if skills is not None:
        wanted = {}
        for raw in skills:
            code = normalize_skill(raw) or raw.strip().lower()
            if code:
                wanted[code] = True
        existing = {k.skill: k for k in c.skills}
        for code in list(existing):
            if code not in wanted and not existing[code].confirmed_by_test:
                db.delete(existing[code])
        for code in wanted:
            if code not in existing:
                db.add(CandidateSkill(candidate_id=c.id, skill=code, source="profile"))
    c.last_active_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return candidate_profile(c, db)


@router.put("/privacy")
def privacy(data: PrivacyIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    d = data.model_dump(exclude_unset=True)
    vis = d.pop("visible_to_employers", None)
    p = dict(c.privacy or {})
    p.update({k: v for k, v in d.items() if v is not None})
    c.privacy = p
    if vis is not None:
        if vis and "publication" not in {k.kind for k in c.consents if k.revoked_at is None}:
            raise HTTPException(status.HTTP_409_CONFLICT, "Сначала дайте согласие на показ профиля работодателям")
        c.visible_to_employers = vis
    log(db, c.user_id, "privacy_changed", "candidate", c.id, **p, visible=c.visible_to_employers)
    db.commit()
    db.refresh(c)
    return candidate_profile(c, db)


@router.post("/consents")
def consents(data: ConsentsIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    for kind in ("processing", "publication"):
        val = getattr(data, kind)
        if val is None:
            continue
        active = [k for k in c.consents if k.kind == kind and k.revoked_at is None]
        if val and not active:
            db.add(Consent(candidate_id=c.id, kind=kind, text_version="1.0", given_at=now))
        if not val:
            for k in active:
                k.revoked_at = now
            if kind == "publication":
                c.visible_to_employers = False
        log(db, c.user_id, "consent_" + ("given" if val else "revoked"), "candidate", c.id, kind=kind)
    db.commit()
    db.refresh(c)
    return candidate_profile(c, db)


@router.get("/achievements")
def achievements(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    return [achievement_view(a, db) for a in sorted(c.achievements, key=lambda a: a.date or "", reverse=True)]


@router.post("/achievements", status_code=201)
def add_achievement(data: AchievementIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    a = Achievement(candidate_id=c.id, kind=data.kind, title=data.title, discipline=data.discipline, date=data.date,
                    place=data.place, level_code="A1", trust_level="claimed", document_name=data.document_name)
    db.add(a)
    db.commit()
    db.refresh(a)
    return achievement_view(a, db)


@router.patch("/achievements/{aid}")
def patch_achievement(aid: int, hidden: bool, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    a = db.get(Achievement, aid)
    if not a or a.candidate_id != c.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Запись не найдена")
    a.hidden = hidden
    db.commit()
    return achievement_view(a, db)


# --- резюме из PDF и PDF-профиль -----------------------------------------------------------------
from fastapi import UploadFile, File
from fastapi.responses import Response
from ..services.resume import pdf_text, parse_resume, enrich_with_model
from ..services.profile_pdf import build_profile_pdf


@router.post("/resume")
def upload_resume(file: UploadFile = File(...), apply: bool = False, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    """Распознаёт PDF-резюме. Поля предзаполняются; уже заполненные перезаписываются только при apply=1.
    Обычная (не async) функция: FastAPI выполняет её в пуле потоков, и обращение к внешней модели не держит цикл событий."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Нужен файл PDF")
    data = file.file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Файл больше 5 МБ")
    text = pdf_text(data)
    if not text.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "В PDF не найден текст (возможно, это скан)")
    parsed = parse_resume(text)
    parsed.setdefault("source", "rules")
    parsed = enrich_with_model(text, parsed)        # без ключа модели возвращает разбор правилами как есть
    applied = False
    for k in ("full_name", "phone", "telegram", "city", "experience_years", "roles", "soft_skills", "about"):
        v = parsed.get(k)
        if v in (None, "", []):
            continue
        if apply or not getattr(c, k):
            setattr(c, k, v)
            applied = True
    existing = {k.skill for k in c.skills}
    for code in parsed["skills"]:
        if code not in existing:
            db.add(CandidateSkill(candidate_id=c.id, skill=code, source="resume"))
            applied = True
    log(db, c.user_id, "resume_parsed", "candidate", c.id, skills=len(parsed["skills"]), source=parsed.get("source"))
    db.commit()
    db.refresh(c)
    return {"parsed": parsed, "applied": applied, "profile": candidate_profile(c, db)}


@router.get("/profile.pdf")
def profile_pdf(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    prof = candidate_profile(c, db)
    acts = [achievement_view(a, db) for a in c.achievements]
    pdf = build_profile_pdf(prof, acts, include_contacts=True)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="profile-{c.id}.pdf"'})
