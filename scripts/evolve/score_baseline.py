"""Текущая боевая формула подбора в виде чистой функции над признаками (зеркало app/services/matching.py).

cand: {spec, grade, skills:{code:{confirmed,tested,score}}, theta, theta_days, fsp:[{level,discipline}], active_days,
       salary_min, salary_max, work_format}
need: {spec, grade, stack:[codes], salary_min, salary_max, work_format}
Возвращает (итог, слагаемые): итог — число, больше — выше в выдаче; слагаемые — словарь имя → значение 0…1 для объяснения.
"""
# EVOLVE-BLOCK-START
WEIGHTS = {"stack": 0.35, "grade": 0.25, "strength": 0.20, "fsp": 0.10, "activity": 0.05, "conditions": 0.05}


def score(cand, need):
    # стек: подтверждённая тестом технология = 1,0; заявленная без проверки = 0,4; проверенная и проваленная = 0,1
    stack = need.get("stack") or []
    if stack:
        acc = 0.0
        for s in stack:
            k = cand["skills"].get(s)
            if k is None:
                continue
            acc += 1.0 if k["confirmed"] else (0.1 if k["tested"] else 0.4)
        stack_v = min(acc / len(stack), 1.0)
    else:
        stack_v = 0.0
    # грейд
    if need.get("grade") and cand.get("grade"):
        d = abs(GRADES.index(need["grade"]) - GRADES.index(cand["grade"]))
        grade_v = 1.0 if d == 0 else 0.5 if d == 1 else 0.0
    else:
        grade_v = 0.0
    # сила профиля: θ в [0, 1] со штрафом за давность
    if cand.get("theta") is not None:
        base = min(max((cand["theta"] + 2.5) / 5.0, 0.0), 1.0)
        days = cand.get("theta_days") or 0
        decay = 1.0 if days <= 90 else max(0.6, 1.0 - (days - 90) / 365)
        strength_v = base * decay
    else:
        strength_v = 0.0
    # достижения ФСП
    fsp_v = 0.0
    for a in cand.get("fsp") or []:
        v = LEVEL_SCORE.get(a["level"], 0.2)
        if a["discipline"] and cand.get("spec") and a["discipline"] not in SPEC_DISCIPLINE.get(cand["spec"], set()):
            v *= 0.5
        fsp_v = max(fsp_v, v)
    # активность
    days = cand.get("active_days", 999)
    activity_v = 1.0 if days <= 7 else 0.6 if days <= 30 else 0.2
    # условия
    parts, n = 0.0, 0
    if need.get("salary_min") is not None and need.get("salary_max") is not None and cand.get("salary_min") is not None:
        n += 1
        lo, hi = max(need["salary_min"], cand["salary_min"]), min(need["salary_max"], cand["salary_max"] or need["salary_max"])
        parts += 1.0 if lo <= hi else 0.0
    if need.get("work_format") and cand.get("work_format"):
        n += 1
        parts += 1.0 if (need["work_format"] == cand["work_format"] or "hybrid" in (need["work_format"], cand["work_format"])) else 0.0
    cond_v = parts / n if n else 0.0
    parts = {"stack": stack_v, "grade": grade_v, "strength": strength_v, "fsp": fsp_v, "activity": activity_v, "conditions": cond_v}
    total = sum(WEIGHTS[k] * parts[k] for k in parts)
    return total, parts
# EVOLVE-BLOCK-END
