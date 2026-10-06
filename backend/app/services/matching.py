"""Механика подбора (docs/07): категории, ранжирование по объяснимым слагаемым, обоснование.

Оценка = Σ вес × слагаемое. Слагаемые от 0 до 1:
  stack      — доля технологий потребности у кандидата (подтверждённая тестом = 1,0; заявленная = 0,3)
  grade      — совпадение грейда (1), соседний (0,5), иначе 0
  strength   — сила подтверждённого профиля: θ последнего теста, приведённый к [0, 1] внутри шкалы, со штрафом за давность
  fsp        — уровень подтверждённого достижения A1–A5 → 0,2…1,0; вне дисциплины, связанной со специализацией, — половина
  activity   — активность за последние дни (короткие задания, вход)
  conditions — пересечение зарплаты и совпадение формата работы, если кандидат их указал
"""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..catalog import DEFAULT_WEIGHTS, category_title, SPEC_TITLE, GRADE_TITLE
from ..models import Candidate, TestSession, GRADES
from .skills_catalog import skill_name

LEVEL_SCORE = {"A1": 0.2, "A2": 0.4, "A3": 0.6, "A4": 0.8, "A5": 1.0}
# какая дисциплина спортивного программирования ближе к специализации
SPEC_DISCIPLINE = {"backend": {"algorithmic", "product"}, "frontend": {"product"}, "fullstack": {"product"}, "mobile": {"product"},
                   "data": {"algorithmic", "product"}, "devops": {"product", "security"}, "qa": {"product"}, "analytics": {"product"},
                   "security": {"security"}}


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def stack_part(need_stack: list[str], cand_skills) -> tuple[float, dict]:
    if not need_stack:
        return 0.0, {"confirmed": [], "declared": [], "missing": []}
    conf, decl, failed, miss = [], [], [], []
    by = {k.skill: k for k in cand_skills}
    for s in need_stack:
        k = by.get(s)
        if k and k.confirmed_by_test:
            conf.append(s)
        elif k and k.test_score is not None:
            failed.append(s)                 # заявлена, проверена тестом, не подтверждена
        elif k:
            decl.append(s)                   # заявлена, тестом не проверялась
        else:
            miss.append(s)
    val = (len(conf) * 1.0 + len(decl) * 0.4 + len(failed) * 0.1) / len(need_stack)
    return min(val, 1.0), {"confirmed": conf, "declared": decl, "failed": failed, "missing": miss}


def grade_part(need_grade: str | None, cand_grade: str | None) -> float:
    if not need_grade or not cand_grade:
        return 0.0
    d = abs(GRADES.index(need_grade) - GRADES.index(cand_grade))
    return 1.0 if d == 0 else 0.5 if d == 1 else 0.0


def strength_part(theta: float | None, finished_at) -> tuple[float, str]:
    if theta is None:
        return 0.0, "тест не пройден"
    base = min(max((theta + 2.5) / 5.0, 0.0), 1.0)        # θ от −2,5 до +2,5 → 0…1
    days = (datetime.now(timezone.utc) - _aware(finished_at)).days if finished_at else 0
    decay = 1.0 if days <= 90 else max(0.6, 1.0 - (days - 90) / 365)
    return round(base * decay, 3), f"θ = {theta:.2f}, {days} дн. назад"


def fsp_part(c: Candidate) -> tuple[float, str | None]:
    acts = [a for a in c.achievements if not a.hidden and a.status == "active" and a.trust_level in ("source", "document")]
    if not acts:
        return 0.0, None
    best, best_val = None, 0.0
    for a in acts:
        v = LEVEL_SCORE.get(a.level_code, 0.2)
        if a.discipline and c.specialization_code and a.discipline not in SPEC_DISCIPLINE.get(c.specialization_code, set()):
            v *= 0.5
        if v > best_val:
            best, best_val = a, v
    return best_val, f"{best.title}" + (" (подтверждено источником)" if best.trust_level == "source" else " (подтверждено документом)")


def activity_part(c: Candidate) -> float:
    if not c.last_active_at:
        return 0.0
    days = (datetime.now(timezone.utc) - _aware(c.last_active_at)).days
    return 1.0 if days <= 7 else 0.6 if days <= 30 else 0.2


def conditions_part(c: Candidate, salary_min, salary_max, work_format) -> float:
    parts, n = 0.0, 0
    if salary_min is not None and salary_max is not None and c.salary_min is not None:
        n += 1
        lo, hi = max(salary_min, c.salary_min), min(salary_max, c.salary_max or salary_max)
        parts += 1.0 if lo <= hi else 0.0
    if work_format and c.work_format:
        n += 1
        parts += 1.0 if (work_format == c.work_format or "hybrid" in (work_format, c.work_format)) else 0.0
    return parts / n if n else 0.0


def score_candidate(c: Candidate, need: dict, weights: dict, last_theta: tuple | None) -> dict:
    """need: {specialization_code, grade, stack, salary_min, salary_max, work_format}."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    stack_v, stack_d = stack_part(need.get("stack") or [], c.skills)
    grade_v = grade_part(need.get("grade"), c.grade)
    theta, fin = last_theta if last_theta else (None, None)
    str_v, str_text = strength_part(theta, fin)
    fsp_v, fsp_text = fsp_part(c)
    act_v = activity_part(c)
    cond_v = conditions_part(c, need.get("salary_min"), need.get("salary_max"), need.get("work_format"))
    parts = {"stack": round(stack_v, 3), "grade": grade_v, "strength": str_v, "fsp": round(fsp_v, 3), "activity": act_v, "conditions": round(cond_v, 3)}
    score = sum(w[k] * parts[k] for k in parts)
    # обоснование одной строкой
    bits = []
    ns = need.get("stack") or []
    if ns:
        bits.append(f"технологии: подтверждено тестом {len(stack_d['confirmed'])}, заявлено без проверки {len(stack_d['declared'])}"
                    + (f", не подтверждено тестом {len(stack_d['failed'])}" if stack_d["failed"] else "") + f" из {len(ns)}"
                    + (f" (нет: {', '.join(skill_name(x) for x in stack_d['missing'][:3])})" if stack_d["missing"] else ""))
    if c.grade:
        bits.append(f"грейд {GRADE_TITLE.get(c.grade, c.grade)} подтверждён тестом" + (f" ({str_text})" if theta is not None else ""))
    else:
        bits.append("грейд не подтверждён")
    bits.append(fsp_text or "истории ФСП нет")
    if act_v >= 1.0:
        bits.append("активен на этой неделе")
    return {"score": round(score, 3), "parts": parts, "explanation": "; ".join(bits), "stack_detail": stack_d}


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
        cands = [c for c in cands if any(a.trust_level in ("source", "document") and a.status == "active" and not a.hidden for a in c.achievements)]
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
    scored.sort(key=lambda x: (-x[1]["score"], x[0].id))
    cats: dict[tuple, list[float]] = {}
    for c, sc in scored:
        cats.setdefault((c.specialization_code, c.grade), []).append(sc["score"])
    categories = [{"specialization_code": k[0], "grade": k[1], "title": category_title(*k), "count": len(v),
                   "avg_score": round(sum(v) / len(v), 3)} for k, v in cats.items()]
    categories.sort(key=lambda x: (-x["avg_score"] * min(x["count"], 5), x["title"]))
    results = [{"candidate_id": c.id, **sc} for c, sc in scored[:limit]]
    return categories, results
