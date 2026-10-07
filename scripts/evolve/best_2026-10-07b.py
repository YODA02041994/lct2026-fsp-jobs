"""Эталон формулы подбора: заход 3, особь g12c0. Установлен в backend/app/services/matching_formula.py командой install_formula.py 2026-10-07; сверка — check_port.py."""
# EVOLVE-BLOCK-START
WEIGHTS = {"stack": 0.44, "grade": 0.24, "strength": 0.14, "fsp": 0.05, "activity": 0.05, "conditions": 0.08}


def score(cand, need):
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

    if days is None:
        decay = 0.6
    elif days <= 90:
        decay = 1.0
    elif days <= 180:
        decay = 0.85
    elif days <= 365:
        decay = 0.65
    else:
        decay = 0.42
    strength_v = base * decay

    # ---- доверие к кандидату (приукрашивание) ----
    if cg0 in GRADES and fg0 in GRADES:
        gap = GRADES.index(cg0) - GRADES.index(fg0)
    elif cg0 in GRADES:
        gap = 1
    else:
        gap = 0
    if gap > 1:
        trust = 0.55
    elif gap == 1:
        trust = 0.82
    elif gap == 0:
        trust = 1.0
    else:
        trust = 0.95
    if gap >= 1 and rel < 0.0:
        trust *= 0.9
    trust = min(max(trust, 0.45), 1.0)

    # чем выше θ относительно ожидаемого, тем больше весит неподтверждённая технология;
    # чем ниже — тем меньше (низкое θ редко даёт реальные неочевидные навыки)
    theta_conf = min(max((rel + 1.5) / 3.0, 0.0), 1.0)
    untested_w = 0.10 + 0.50 * theta_conf * trust
    untested_w = min(max(untested_w, 0.06), 0.72)
    failed_w = -0.18

    # ---- стек ----
    stack = need.get("stack") or []
    n_confirmed = 0
    n_tested = 0
    n_hit = 0
    if stack:
        n_req = len(stack)
        miss_scale = max(0.35, 1.0 - 0.09 * max(0, n_req - 4))
        acc = 0.0
        n_failed = 0
        for s in stack:
            k = skills.get(s)
            if k is None:
                acc += untested_w * miss_scale * 0.35
                continue
            n_hit += 1
            if k.get("confirmed"):
                n_confirmed += 1
                n_tested += 1
                sc = k.get("score")
                if sc is not None:
                    v = 0.85 + 0.15 * min(max(sc, 0.0), 1.0)
                else:
                    v = 1.0
                if trust < 0.9:
                    v *= 0.93
            elif k.get("tested"):
                v = failed_w
                n_failed += 1
                n_tested += 1
            else:
                # заявленная, но непроверенная технология: вес зависит от θ и доверия
                v = untested_w
                # при явном расхождении грейдов сильнее срезаем неподтверждённое
                if gap >= 1:
                    v *= (0.75 + 0.25 * theta_conf)
            acc += v
        stack_v = max(acc, 0.0) / n_req
        stack_v = min(stack_v, 1.0)
        if n_req >= 5 and n_hit / n_req >= 0.8:
            stack_v = min(stack_v * 1.05, 1.0)
        if n_confirmed == 0:
            stack_v *= 0.80
        # штраф, если вообще нет технологий, проверенных тестом
        if n_tested == 0 and n_hit > 0:
            stack_v *= 0.88
    else:
        stack_v = 0.0

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
                gv = 0.28
            else:
                gv = 0.0
            if gv == 1.0 and rel < -0.7:
                gv = 0.55
            elif gv == 0.60 and rel < -1.0:
                gv = 0.35
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
    fsp_v = min(fsp_v, 0.75)

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

    # ---- условия (зарплата градуированно) ----
    parts_sum, n = 0.0, 0
    if (need.get("salary_min") is not None and need.get("salary_max") is not None
            and cand.get("salary_min") is not None):
        n += 1
        cmax = cand.get("salary_max")
        if cmax is None:
            cmax = need["salary_max"]
        nlo, nhi = need["salary_min"], need["salary_max"]
        clo, chi = cand["salary_min"], cmax
        lo = max(nlo, clo)
        hi = min(nhi, chi)
        if lo <= hi:
            need_span = max(nhi - nlo, 1.0)
            overlap = hi - lo
            ratio = min(max(overlap / need_span, 0.0), 1.0)
            # базовое попадание + бонус за величину пересечения
            parts_sum += 0.6 + 0.4 * ratio
        else:
            # частичное перекрытие «на грани»: чем ближе, тем больше
            gap = lo - hi
            scale = max(nhi - nlo, 1.0)
            prox = max(0.0, 1.0 - gap / (0.5 * scale))
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

    mandatory = (0.50 + 0.50 * stack_v) * (0.60 + 0.40 * grade_v)
    soft = (
        WEIGHTS["strength"] * strength_v
        + WEIGHTS["fsp"] * fsp_v
        + WEIGHTS["activity"] * activity_v
        + WEIGHTS["conditions"] * cond_v
    )
    core = WEIGHTS["stack"] * stack_v + WEIGHTS["grade"] * grade_v
    total = mandatory * (core + soft)

    if stack_v >= 0.85 and grade_v >= 1.0:
        total *= 1.08
    if stack_v >= 0.7 and grade_v == 0.0:
        total *= 0.75
    # сильное расхождение заявленного и фактического грейда — режем итог
    if gap >= 2:
        total *= 0.88
    # нет ни одной проверенной тестом технологии — общий срез
    if stack and n_tested == 0:
        total *= 0.92

    return total, parts
# EVOLVE-BLOCK-END
