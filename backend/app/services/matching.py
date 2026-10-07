"""Механика подбора (docs/07): категории, ранжирование по объяснимым слагаемым, обоснование.

Устройство:
  1. candidate_features / need_features — наблюдаемые признаки из базы в виде словарей (единственное место, где ORM
     превращается в признаки; его же использует scripts/evolve/features.py, поэтому поиск формулы и бой видят одно и то же);
  2. matching_formula.score — сама формула (EVOLVE-BLOCK, найден эволюционным поиском и установлен install_formula.py;
     эталон и сверка — scripts/evolve/);
  3. калибровка — сырой итог монотонно переводится в вероятность «кандидат подходит» (scripts/evolve/calibrate.py);
  4. обоснование одной строкой из тех же слагаемых.

Слагаемые от 0 до 1 (их видит работодатель): stack — покрытие технологий потребности с учётом подтверждения тестом;
grade — соответствие подтверждённого грейда (заявленный — только подсказка); strength — θ относительно требуемого грейда
с учётом давности; fsp — подтверждённое достижение ФСП (вклад ограничен); activity — активность; conditions — зарплата
и формат. Стек и грейд — обязательные множители, остальное — добавка. Подробности и цифры — docs/07 и docs/09.
"""
from __future__ import annotations
import math
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..catalog import DEFAULT_WEIGHTS, category_title, GRADE_TITLE
from ..models import Candidate, TestSession, GRADES
from .skills_catalog import skill_name
from . import matching_formula as formula
from .matching_formula import LEVEL_SCORE, SPEC_DISCIPLINE  # noqa: F401  (нужны features.py и проверкам)

CALIBRATION = {"a": 9.6380, "b": -3.4724}     # p = σ(a·raw + b); calibrate.py на мирах 11,12,13,16,17, проверено на 14 и 15 (docs/09)
TRUSTED = ("source", "document")


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _days(now: datetime, dt) -> int | None:
    return (now - _aware(dt)).days if dt else None


def candidate_features(c: Candidate, last_theta: tuple | None, now: datetime | None = None) -> dict:
    """Наблюдаемые признаки кандидата для формулы. Истинных данных здесь нет и быть не может."""
    now = now or datetime.now(timezone.utc)
    theta, fin = last_theta if last_theta else (None, None)
    acts = [a for a in c.achievements if not a.hidden and a.status == "active" and a.trust_level in TRUSTED]
    return {
        "id": c.id, "spec": c.specialization_code, "grade": c.grade, "claimed_grade": c.claimed_grade,
        "skills": {k.skill: {"confirmed": bool(k.confirmed_by_test), "tested": k.test_score is not None, "score": k.test_score} for k in c.skills},
        "theta": theta, "theta_days": _days(now, fin) if theta is not None else None,
        "fsp": [{"level": a.level_code, "discipline": a.discipline} for a in acts],
        "active_days": _days(now, c.last_active_at) if c.last_active_at else 999,
        "salary_min": c.salary_min, "salary_max": c.salary_max, "work_format": c.work_format,
    }


def need_features(need: dict) -> dict:
    return {"spec": need.get("specialization_code"), "grade": need.get("grade"), "stack": list(need.get("stack") or []),
            "salary_min": need.get("salary_min"), "salary_max": need.get("salary_max"), "work_format": need.get("work_format")}


def stack_detail(need_stack: list[str], cand_skills) -> dict:
    """Какие технологии потребности подтверждены тестом, заявлены без проверки, провалены, отсутствуют — для обоснования."""
    conf, decl, failed, miss = [], [], [], []
    by = {k.skill: k for k in cand_skills}
    for s in need_stack:
        k = by.get(s)
        if k and k.confirmed_by_test:
            conf.append(s)
        elif k and k.test_score is not None:
            failed.append(s)
        elif k:
            decl.append(s)
        else:
            miss.append(s)
    return {"confirmed": conf, "declared": decl, "failed": failed, "missing": miss}


def fsp_text(c: Candidate) -> str | None:
    acts = [a for a in c.achievements if not a.hidden and a.status == "active" and a.trust_level in TRUSTED]
    if not acts:
        return None
    best, best_val = None, -1.0
    for a in acts:
        v = LEVEL_SCORE.get(a.level_code, 0.2)
        if a.discipline and c.specialization_code and a.discipline not in SPEC_DISCIPLINE.get(c.specialization_code, set()):
            v *= 0.5
        if v > best_val:
            best, best_val = a, v
    return f"{best.title}" + (" (подтверждено источником)" if best.trust_level == "source" else " (подтверждено документом)")


def calibrated(raw: float) -> float:
    """Сырой итог → вероятность «подходит» (монотонно, порядок не меняется)."""
    return 1.0 / (1.0 + math.exp(-(CALIBRATION["a"] * raw + CALIBRATION["b"])))


def score_candidate(c: Candidate, need: dict, weights: dict, last_theta: tuple | None) -> dict:
    """need: {specialization_code, grade, stack, salary_min, salary_max, work_format}.
    score — калиброванная оценка, если потребность задана (есть грейд или стек), иначе сырой итог; raw_score — сырой итог всегда."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    feat = candidate_features(c, last_theta)
    nf = need_features(need)
    raw_score, raw_parts = formula.score(feat, nf, w)
    hint = False
    if c.claimed_grade and c.claimed_grade != c.grade:
        _, parts_no = formula.score({**feat, "claimed_grade": None}, nf, w)
        hint = raw_parts["grade"] > parts_no["grade"] + 1e-9
    inflated = bool(c.claimed_grade in GRADES and c.grade in GRADES and GRADES.index(c.claimed_grade) > GRADES.index(c.grade) + 1)
    has_need = bool(nf["grade"] or nf["stack"])
    score = calibrated(raw_score) if has_need else min(raw_score, 1.0)
    detail = stack_detail(nf["stack"], c.skills)
    theta, fin = last_theta if last_theta else (None, None)
    # обоснование одной строкой
    bits = []
    if nf["stack"]:
        bits.append(f"технологии: подтверждено тестом {len(detail['confirmed'])}, заявлено без проверки {len(detail['declared'])}"
                    + (f", не подтверждено тестом {len(detail['failed'])}" if detail["failed"] else "") + f" из {len(nf['stack'])}"
                    + (f" (нет: {', '.join(skill_name(x) for x in detail['missing'][:3])})" if detail["missing"] else ""))
    if c.grade:
        days = feat["theta_days"]
        bits.append(f"грейд {GRADE_TITLE.get(c.grade, c.grade)} подтверждён тестом"
                    + (f" (θ = {theta:.2f}, {days} дн. назад)" if theta is not None and days is not None else "")
                    + (f"; заявленный {GRADE_TITLE.get(c.claimed_grade, c.claimed_grade)} учтён как подсказка" if hint else "")
                    + ("; заявленный грейд на два выше подтверждённого — доверие к непроверенным технологиям снижено" if inflated else ""))
    else:
        bits.append("грейд не подтверждён")
    bits.append(fsp_text(c) or "истории ФСП нет")
    if raw_parts["activity"] >= 1.0:
        bits.append("активен на этой неделе")
    return {"score": round(score, 3), "raw_score": round(raw_score, 4), "parts": {k: round(v, 3) for k, v in raw_parts.items()},
            "explanation": "; ".join(bits), "stack_detail": detail}


def last_thetas(db: Session, candidate_ids: list[int]) -> dict[int, tuple]:
    if not candidate_ids:
        return {}
    rows = db.execute(select(TestSession.candidate_id, TestSession.theta, TestSession.finished_at)
                      .where(TestSession.candidate_id.in_(candidate_ids), TestSession.status == "finished")
                      .order_by(TestSession.finished_at.desc())).all()
    out: dict[int, tuple] = {}
    for cid, theta, fin in rows:
        out.setdefault(cid, (theta, fin))
    return out


def candidate_pool(db: Session, filters: dict) -> list[Candidate]:
    q = select(Candidate).where(Candidate.visible_to_employers.is_(True), Candidate.grade.is_not(None))
    if filters.get("specialization_code"):
        q = q.where(Candidate.specialization_code == filters["specialization_code"])
    if filters.get("grades"):
        q = q.where(Candidate.grade.in_(filters["grades"]))
    if filters.get("city"):
        q = q.where(Candidate.city.ilike(f"%{filters['city']}%"))
    cands = list(db.scalars(q).all())
    if filters.get("skills"):
        want = set(filters["skills"])
        cands = [c for c in cands if want & {k.skill for k in c.skills}]
    if filters.get("fsp_only"):
        cands = [c for c in cands if any(a.trust_level in TRUSTED and a.status == "active" and not a.hidden for a in c.achievements)]
    if filters.get("salary_max") is not None:
        cands = [c for c in cands if c.salary_min is None or c.salary_min <= filters["salary_max"]]
    return cands


def build_selection(db: Session, need: dict, filters: dict, weights: dict | None, limit: int = 30) -> tuple[list[dict], list[dict]]:
    """→ (категории, ранжированные результаты)."""
    f = dict(filters or {})
    # по умолчанию — специализация потребности и соседние грейды
    if "specialization_code" not in f and need.get("specialization_code"):
        f["specialization_code"] = need["specialization_code"]
    if "grades" not in f and need.get("grade"):
        gi = GRADES.index(need["grade"])
        f["grades"] = [g for g in GRADES if abs(GRADES.index(g) - gi) <= 1]
    pool = candidate_pool(db, f)
    thetas = last_thetas(db, [c.id for c in pool])
    scored = []
    for c in pool:
        sc = score_candidate(c, need, weights or {}, thetas.get(c.id))
        scored.append((c, sc))
    scored.sort(key=lambda x: (-x[1]["raw_score"], x[0].id))
    cats: dict[tuple, list[float]] = {}
    for c, sc in scored:
        cats.setdefault((c.specialization_code, c.grade), []).append(sc["score"])
    categories = [{"specialization_code": k[0], "grade": k[1], "title": category_title(*k), "count": len(v),
                   "avg_score": round(sum(v) / len(v), 3)} for k, v in cats.items()]
    categories.sort(key=lambda x: (-x["avg_score"] * min(x["count"], 5), x["title"]))
    results = [{"candidate_id": c.id, **sc} for c, sc in scored[:limit]]
    return categories, results
