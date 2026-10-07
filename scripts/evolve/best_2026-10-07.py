"""Итог эволюции формулы подбора 07.10.2026 (scripts/evolve/evolve_matching.py): лучшая особь первого захода (g6c0)
плюс одно ручное ограничение — заявленный грейд учитывается как подсказка, только если он соседний с подтверждённым тестом
(по абляции это ничего не стоит и согласуется с замыслом: заявление без проверки не должно решать само по себе).
Эта формула перенесена в backend/app/services/matching.py; scripts/evolve/check_port.py сверяет перенос."""
# EVOLVE-BLOCK-START
WEIGHTS = {"stack": 0.40, "grade": 0.24, "strength": 0.16, "fsp": 0.06, "activity": 0.06, "conditions": 0.08}


def score(cand, need):
    skills = cand.get("skills") or {}
    need_grade = need.get("grade")

    # --- θ как относительная величина к требуемому грейду ---
    theta = cand.get("theta")
    if theta is not None:
        base = min(max((theta + 2.5) / 5.0, 0.0), 1.0)
        days = cand.get("theta_days") or 0
        decay = 1.0 if days <= 90 else max(0.6, 1.0 - (days - 90) / 365)
        strength_v = base * decay
    else:
        strength_v = 0.0

    if need_grade in GRADES:
        need_idx = GRADES.index(need_grade)
        expected = -2.5 + (need_idx / max(len(GRADES) - 1, 1)) * 5.0
        if theta is not None:
            rel = (theta - expected) / 2.5
            rel = min(max(rel, -1.0), 1.0)
        else:
            rel = -0.5
    else:
        rel = 0.0

    # вес неподтверждённых навыков: сильнее зависит от θ относительно грейда
    untested_w = 0.20 + 0.55 * (rel + 1.0) / 2.0
    untested_w = min(max(untested_w, 0.12), 0.80)

    # --- стек ---
    stack = need.get("stack") or []
    if stack:
        acc = 0.0
        for s in stack:
            k = skills.get(s)
            if k is None:
                continue
            if k.get("confirmed"):
                sc = k.get("score")
                if sc is not None:
                    v = 0.85 + 0.15 * min(max(sc, 0.0), 1.0)
                else:
                    v = 1.0
            elif k.get("tested"):
                v = 0.12
            else:
                v = untested_w
            acc += v
        stack_v = min(acc / len(stack), 1.0)
    else:
        stack_v = 0.0

    # --- грейд ---
    grade_v = 0.0
    cg0, fg0 = cand.get("claimed_grade"), cand.get("grade")
    use_cg = cg0 if (cg0 in GRADES and fg0 in GRADES and abs(GRADES.index(cg0) - GRADES.index(fg0)) == 1) else None
    for g in (fg0, use_cg):
        if need_grade in GRADES and g in GRADES:
            d = abs(GRADES.index(need_grade) - GRADES.index(g))
            gv = 1.0 if d == 0 else 0.5 if d == 1 else 0.0
            if gv == 1.0 and rel < -0.5:
                gv = 0.6
            if gv > grade_v:
                grade_v = gv
    cg = cand.get("claimed_grade")
    fg = cand.get("grade")
    if cg in GRADES and fg in GRADES and GRADES.index(cg) > GRADES.index(fg) + 1:
        grade_v *= 0.7

    # --- ФСП: ограниченный вклад, только для разрешения ничьей ---
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
    # жёсткое ограничение вклада ФСП, чтобы не перебивал стек
    fsp_v = min(fsp_v, 0.7)

    # --- активность ---
    days = cand.get("active_days")
    if days is None:
        activity_v = 0.4
    elif days <= 7:
        activity_v = 1.0
    elif days <= 30:
        activity_v = 0.6
    else:
        activity_v = 0.2

    # --- условия ---
    parts_sum, n = 0.0, 0
    if need.get("salary_min") is not None and need.get("salary_max") is not None and cand.get("salary_min") is not None:
        n += 1
        cmax = cand.get("salary_max")
        if cmax is None:
            cmax = need["salary_max"]
        lo = max(need["salary_min"], cand["salary_min"])
        hi = min(need["salary_max"], cmax)
        parts_sum += 1.0 if lo <= hi else 0.0
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

    mandatory = (0.45 + 0.55 * stack_v) * (0.55 + 0.45 * grade_v)
    soft = (
        WEIGHTS["strength"] * strength_v
        + WEIGHTS["fsp"] * fsp_v
        + WEIGHTS["activity"] * activity_v
        + WEIGHTS["conditions"] * cond_v
    )
    core = WEIGHTS["stack"] * stack_v + WEIGHTS["grade"] * grade_v
    total = mandatory * (core + soft)

    if stack_v >= 0.8 and grade_v >= 1.0:
        total *= 1.08

    return total, parts
# EVOLVE-BLOCK-END
