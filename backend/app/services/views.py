"""Представления сущностей для API: профиль кандидата, карточка для работодателя, сеанс теста."""
from __future__ import annotations
from datetime import timedelta
from sqlalchemy.orm import Session
from ..catalog import category_title
from ..config import get_settings
from ..models import Candidate, TestSession, Achievement, Employer, FspEvent
from .skills_catalog import skill_name
from .testing.engine import technology_summary

TRUST_TITLE = {"source": "подтверждено источником", "document": "подтверждено документом", "claimed": "заявлено участником"}
LEVEL_TITLE = {"A5": "высший", "A4": "КМС или призёр чемпионата/Кубка России", "A3": "I разряд или призёр окружного этапа",
               "A2": "II–III разряд или призёр регионального этапа", "A1": "участие"}


def grade_change_available_at(c: Candidate):
    if not c.grade_changed_at:
        return None
    return c.grade_changed_at + timedelta(days=get_settings().grade_change_cooldown_days)


def consents_of(c: Candidate) -> dict:
    out = {"processing": False, "publication": False}
    for k in c.consents:
        if k.revoked_at is None:
            out[k.kind] = True
    return out


def achievement_view(a: Achievement, db: Session | None = None) -> dict:
    ev = None
    if a.event_id and db is not None:
        e = db.get(FspEvent, a.event_id)
        if e:
            ev = {"name": e.name, "ekp_number": e.ekp_number, "level": e.level, "date_start": e.date_start}
    return {"id": a.id, "kind": a.kind, "title": a.title, "discipline": a.discipline, "level_code": a.level_code,
            "level_title": LEVEL_TITLE.get(a.level_code, a.level_code), "place": a.place, "date": a.date,
            "valid_until": a.valid_until, "trust_level": a.trust_level, "trust_title": TRUST_TITLE.get(a.trust_level, a.trust_level),
            "status": a.status, "hidden": a.hidden, "document_name": a.document_name, "event": ev}


def session_view(s: TestSession, reveal: bool = False) -> dict:
    items = []
    for it in s.items:
        items.append({"id": it.id, "block_no": it.block_no, "order_no": it.order_no, "level": it.level,
                      "payload": it.payload, "answered": it.candidate_answer is not None,
                      "seconds_left": None if it.candidate_answer is not None else get_settings().test_item_seconds,
                      **({"correct": it.correct, "explanation": it.answer_key.get("explanation", "")} if reveal and s.status == "finished" else {})})
    result = None
    if s.status == "finished":
        answered = [(it.template_code, it.correct) for it in s.items]
        by_tech = technology_summary(answered)
        for row in by_tech:
            row["name"] = skill_name(row["skill"])
        result = {"theta": round(s.theta or 0, 2), "theta_sd": round(s.theta_sd or 0, 2), "result_grade": s.result_grade,
                  "decision": s.decision, "correct_total": sum(1 for it in s.items if it.correct),
                  "items_total": len(s.items), "by_technology": by_tech,
                  "can_apply": s.decision in ("suggest_lower", "suggest_higher")}
    return {"id": s.id, "status": s.status, "specialization_code": s.specialization_code, "claimed_grade": s.claimed_grade,
            "declared_skills": s.declared_skills, "current_block": s.current_block, "blocks_total": s.blocks_total,
            "block_size": s.block_size, "current_level": s.current_level, "started_at": s.started_at,
            "finished_at": s.finished_at, "items": items, "result": result}


def candidate_profile(c: Candidate, db: Session) -> dict:
    last = None
    if db is not None:
        from sqlalchemy import select
        s = db.scalar(select(TestSession).where(TestSession.candidate_id == c.id).order_by(TestSession.id.desc()).limit(1))
        if s:
            last = {"id": s.id, "status": s.status, "result_grade": s.result_grade, "decision": s.decision, "finished_at": s.finished_at,
                    "specialization_code": s.specialization_code, "claimed_grade": s.claimed_grade}
    return {
        "id": c.id, "alias": c.alias, "full_name": c.full_name, "phone": c.phone, "telegram": c.telegram, "email": c.user.email if c.user else "",
        "city": c.city, "experience_years": c.experience_years, "roles": c.roles, "soft_skills": c.soft_skills, "about": c.about,
        "salary_min": c.salary_min, "salary_max": c.salary_max, "work_format": c.work_format,
        "specialization_code": c.specialization_code, "claimed_grade": c.claimed_grade, "grade": c.grade,
        "grade_changed_at": c.grade_changed_at, "grade_change_available_at": grade_change_available_at(c),
        "fsp_id": c.fsp_id, "fsp_linked_at": c.fsp_linked_at, "visible_to_employers": c.visible_to_employers,
        "privacy": c.privacy, "consents": consents_of(c),
        "skills": [{"skill": k.skill, "name": skill_name(k.skill), "source": k.source, "confirmed_by_test": k.confirmed_by_test, "test_score": k.test_score}
                   for k in sorted(c.skills, key=lambda x: (not x.confirmed_by_test, x.skill))],
        "category": ({"specialization_code": c.specialization_code, "grade": c.grade, "title": category_title(c.specialization_code, c.grade)}
                     if c.specialization_code and c.grade else None),
        "achievements_count": sum(1 for a in c.achievements if not a.hidden and a.status == "active"),
        "last_test": last,
    }


def achievements_summary(c: Candidate) -> str:
    acts = [a for a in c.achievements if not a.hidden and a.status == "active" and a.trust_level in ("source", "document")]
    if not c.fsp_id and not acts:
        return "история ФСП отсутствует"
    if not acts:
        return "связь с ФСП ID есть, подтверждённых достижений нет"
    best = max(acts, key=lambda a: a.level_code)
    return f"{best.title} ({TRUST_TITLE[best.trust_level]})" + (f"; всего записей: {len(acts)}" if len(acts) > 1 else "")


def candidate_card(c: Candidate, score: dict | None, unlocked: bool, db: Session) -> dict:
    priv = c.privacy or {}
    card = {
        "candidate_id": c.id, "alias": c.alias,
        "category": {"specialization_code": c.specialization_code, "grade": c.grade, "title": category_title(c.specialization_code, c.grade)},
        "experience_years": c.experience_years, "roles": c.roles, "about": c.about[:400] if c.about else "",
        "skills": [{"skill": k.skill, "name": skill_name(k.skill), "confirmed_by_test": k.confirmed_by_test} for k in c.skills],
        "achievements_summary": achievements_summary(c) if priv.get("achievements", True) else "скрыто кандидатом",
        "achievements": [achievement_view(a, db) for a in c.achievements if not a.hidden and a.status == "active"] if priv.get("achievements", True) else [],
        "fsp_linked": bool(c.fsp_id) if priv.get("fsp_link", True) else None,
        "city": c.city if priv.get("city", True) else None,
        "salary_min": c.salary_min if priv.get("salary", True) else None,
        "salary_max": c.salary_max if priv.get("salary", True) else None,
        "work_format": c.work_format, "last_active_at": c.last_active_at,
        "contacts_unlocked": unlocked,
    }
    if score:
        card.update({"score": score["score"], "parts": score["parts"], "explanation": score["explanation"]})
    if unlocked:
        card["contacts"] = {"full_name": c.full_name, "phone": c.phone, "telegram": c.telegram, "email": c.user.email if c.user else ""}
    return card


def employer_view(e: Employer) -> dict:
    return {"id": e.id, "company_name": e.company_name, "description": e.description, "industry": e.industry, "website": e.website,
            "city": e.city, "contact_person": e.contact_person, "contact_email": e.contact_email, "contact_phone": e.contact_phone,
            "verified": e.verified, "email": e.user.email if e.user else ""}
