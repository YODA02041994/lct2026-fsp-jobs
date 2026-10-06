from fastapi import APIRouter
from ..catalog import SPECIALIZATIONS, GRADES, WORK_FORMATS, DEFAULT_WEIGHTS
from ..config import get_settings
from ..services.skills_catalog import SKILLS

router = APIRouter(tags=["catalog"])


@router.get("/catalog")
def catalog():
    s = get_settings()
    return {
        "specializations": [{"code": c, "name": n, "description": d, "has_bank": hb} for c, n, d, hb, _ in SPECIALIZATIONS],
        "grades": [{"code": c, "title": t, "description": d} for c, t, d in GRADES],
        "work_formats": [{"code": c, "title": t} for c, t in WORK_FORMATS],
        "skills": [{"code": c, "name": n, "group": g} for c, n, _, g in SKILLS],
        "weights": DEFAULT_WEIGHTS,
        "test": {"block_size": s.test_block_size, "blocks": s.test_blocks, "item_seconds": s.test_item_seconds,
                 "grade_change_cooldown_days": s.grade_change_cooldown_days},
        "demo_mode": s.demo_mode,
        "email_demo": s.email_demo,
        "demo_accounts": [
            {"email": "candidate.demo@fsp-demo.ru", "password": "demo12345", "role": "candidate", "note": "кандидат с историей ФСП"},
            {"email": "candidate2.demo@fsp-demo.ru", "password": "demo12345", "role": "candidate", "note": "кандидат без истории ФСП"},
            {"email": "employer.demo@fsp-demo.ru", "password": "demo12345", "role": "employer", "note": "работодатель с вакансиями и подборками"},
        ] if s.demo_mode else [],
    }
