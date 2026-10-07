"""Формула подбора — EVOLVE-BLOCK, установленный scripts/evolve/install_formula.py
из scripts/evolve/best_2026-10-07d.py (заход 5 на реалистичных мирах + упрощение по RRSI, 2026-10-07). Эталон для сверки: scripts/evolve/best_2026-10-07d.py.

Не править руками: изменения делаются эволюцией (scripts/evolve/evolve_matching.py) и повторной установкой.
Вход: cand и need — словари наблюдаемых признаков (см. matching.candidate_features и matching.need_features),
weights — переопределение весов работодателем. Выход: (сырой итог, слагаемые 0…1).
"""
from __future__ import annotations
import math  # noqa: F401  (доступен формуле)
from ..models import GRADES  # noqa: F401

LEVEL_SCORE = {"A1": 0.2, "A2": 0.4, "A3": 0.6, "A4": 0.8, "A5": 1.0}
# какая дисциплина спортивного программирования ближе к специализации
SPEC_DISCIPLINE = {"backend": {"algorithmic", "product"}, "frontend": {"product"}, "fullstack": {"product"}, "mobile": {"product"},
                   "data": {"algorithmic", "product"}, "devops": {"product", "security"}, "qa": {"product"}, "analytics": {"product"},
                   "security": {"security"}}

# EVOLVE-BLOCK-START
WEIGHTS = {"stack": 0.50, "grade": 0.22, "strength": 0.12, "fsp": 0.04, "activity": 0.04, "conditions": 0.08}


def score(cand, need, weights=None):
    w = {**WEIGHTS, **(weights or {})}
    skills = cand.get("skills") or {}
    need_grade = need.get("grade")
    cg0, fg0 = cand.get("claimed_grade"), cand.get("grade")

    # ---- индекс грейда потребности ----
    if need_grade in GRADES:
        need_idx = GRADES.index(need_grade)
    else:
        need_idx = len(GRADES) // 2

    # ---- θ относительно порога требуемого грейда ----
    theta = cand.get("theta")
    days = cand.get("theta_days")
    expected = -1.5 + (need_idx / max(len(GRADES) - 1, 1)) * 4.0
    if theta is not None:
        rel = (theta - expected) / 2.5
        rel = min(max(rel, -1.5), 1.5)
    else:
        rel = -0.6

    base = min(max((rel + 1.5) / 3.0, 0.0), 1.0)

    # ---- давность теста θ ----
    if days is None:
        decay = 0.55
    elif days <= 60:
        decay = 1.0
    elif days <= 120:
        decay = 0.92
    elif days <= 180:
        decay = 0.82
    elif days <= 365:
        decay = 0.62
    elif days <= 730:
        decay = 0.42
    else:
        decay = 0.28
    strength_v = base * decay

    # ---- доверие (приукрашивание грейда) ----
    if cg0 in GRADES and fg0 in GRADES:
        gap = GRADES.index(cg0) - GRADES.index(fg0)
    elif cg0 in GRADES:
        gap = 1
    else:
        gap = 0
    if gap > 1:
        trust = 0.52
    elif gap == 1:
        trust = 0.80
    elif gap == 0:
        trust = 1.0
    else:
        trust = 0.95
    if gap >= 1 and rel < 0.0:
        trust *= 0.9
    trust = min(max(trust, 0.40), 1.0)

    theta_conf = min(max((rel + 1.5) / 3.0, 0.0), 1.0)
    untested_w = 0.10 + 0.50 * theta_conf * trust
    untested_w = min(max(untested_w, 0.06), 0.72)
    failed_w = 0.3

    # ---- стек: главный сигнал ----
    stack = need.get("stack") or []
    n_confirmed = 0
    n_tested = 0
    n_hit = 0
    n_present = 0
    n_failed = 0
    coverage = 0.0
    n_missing = 0
    n_req = 0
    if stack:
        n_req = len(stack)
        miss_scale = 1.0
        acc = 0.0
        for s in stack:
            k = skills.get(s)
            if k is None:
                acc += untested_w * miss_scale * 0.30
                continue
            n_hit += 1
            if k.get("confirmed"):
                n_confirmed += 1
                n_tested += 1
                n_present += 1
                sc = k.get("score")
                if sc is not None:
                    v = 0.85 + 0.15 * min(max(sc, 0.0), 1.0)
                else:
                    v = 1.0
                # подтверждение шумное — не даём ему полный вес при низком доверии
            elif k.get("tested"):
                # провал тоже шумный: не приравниваем к полному нулю
                v = failed_w
                n_failed += 1
                n_tested += 1
                n_present += 1  # технология заявлена и частично «в игре»
            else:
                n_present += 1
                v = max(untested_w, 0.55)
            acc += v
        stack_v = max(acc, 0.0) / n_req
        stack_v = min(stack_v, 1.0)

        coverage = n_present / n_req
        n_missing = n_req - n_hit

        # покрытие стека — второй по важности сигнал

        if n_missing >= 2:
            stack_v *= max(0.55, 1.0 - 0.10 * (n_missing - 1))
        if n_missing >= 4:
            stack_v *= 0.85

    else:
        stack_v = 0.0
        coverage = 0.0
        n_missing = 0

    # ---- грейд ----
    grade_v = 0.0
    use_cg = None
    if cg0 in GRADES and fg0 in GRADES and abs(GRADES.index(cg0) - GRADES.index(fg0)) <= 1:
        use_cg = cg0
    for g in (fg0, use_cg):
        if g in GRADES:
            d = need_idx - GRADES.index(g)
            if d == 0:
                gv = 1.0
            elif d == 1:
                gv = 0.60
            elif d == -1:
                gv = 0.60
            else:
                gv = 0.0
            if gv > grade_v:
                grade_v = gv
    if cg0 in GRADES and fg0 in GRADES and GRADES.index(cg0) > GRADES.index(fg0) + 1:
        grade_v *= 0.6

    # ---- ФСП ----
    spec = cand.get("spec")
    spec_set = SPEC_DISCIPLINE.get(spec, set()) if spec else set()
    fsp_v = 0.0
    for a in cand.get("fsp") or []:
        v = LEVEL_SCORE.get(a.get("level"), 0.2)
        disc = a.get("discipline")
        if disc and spec_set and disc not in spec_set:
            v *= 0.5
        if v > fsp_v:
            fsp_v = v
    fsp_v = min(fsp_v, 0.65)

    # ---- активность ----
    ad = cand.get("active_days")
    if ad is None:
        activity_v = 0.4
    elif ad <= 7:
        activity_v = 1.0
    elif ad <= 30:
        activity_v = 0.6
    elif ad <= 90:
        activity_v = 0.35
    else:
        activity_v = 0.15

    # ---- условия ----
    parts_sum, n = 0.0, 0
    salary_fit = None
    if (need.get("salary_min") is not None and need.get("salary_max") is not None
            and cand.get("salary_min") is not None):
        n += 1
        cmax = cand.get("salary_max")
        if cmax is None:
            cmax = cand["salary_min"]
        nlo, nhi = need["salary_min"], need["salary_max"]
        clo, chi = cand["salary_min"], max(cmax, cand["salary_min"])
        lo = max(nlo, clo)
        hi = min(nhi, chi)
        need_span = max(nhi - nlo, 1.0)
        if lo <= hi:
            overlap = hi - lo
            ratio = min(max(overlap / need_span, 0.0), 1.0)
            salary_fit = 0.65 + 0.35 * ratio
            parts_sum += 0.6 + 0.4 * ratio
        else:
            gap_s = lo - hi
            prox = max(0.0, 1.0 - gap_s / (0.5 * need_span))
            salary_fit = 0.30 * prox
            parts_sum += 0.35 * prox
    if need.get("work_format") and cand.get("work_format"):
        n += 1
        nf, cf = need["work_format"], cand["work_format"]
        parts_sum += 1.0 if (nf == cf or "hybrid" in (nf, cf)) else 0.0
    cond_v = parts_sum / n if n else 0.0

    parts = {
        "stack": stack_v,
        "grade": grade_v,
        "strength": strength_v,
        "fsp": fsp_v,
        "activity": activity_v,
        "conditions": cond_v,
    }

    # ---- обязательные (стек × грейд) × мягкие ----
    soft = (
        w["strength"] * strength_v
        + w["fsp"] * fsp_v
        + w["activity"] * activity_v
        + w["conditions"] * cond_v
    )
    core = w["stack"] * stack_v + w["grade"] * grade_v
    total = core + soft

    # ---- зарплата как множитель ----
    if salary_fit is not None:
        total *= (0.40 + 0.72 * salary_fit)

    if (need.get("salary_max") is not None and cand.get("salary_min") is not None
            and cand["salary_min"] > need["salary_max"]):
        total *= 0.55

    # ---- бустинги/штрафы ----

    # покрытие стека — второй по важности сигнал (усилен)
    if stack:
        if coverage >= 0.9:
            total *= 1.08
        elif coverage >= 0.75:
            total *= 1.03
        elif coverage <= 0.4:
            total *= 0.78
        elif coverage <= 0.6:
            total *= 0.90
        if n_missing >= 3:
            total *= 0.80
        elif n_missing >= 2:
            total *= 0.90
        # доля подтверждённых среди присутствующих — мягкий буст
        # провалы среди присутствующих — мягкий штраф (шумный сигнал)

    return total, parts
# EVOLVE-BLOCK-END
