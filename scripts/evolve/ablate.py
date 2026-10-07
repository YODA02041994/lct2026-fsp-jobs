#!/usr/bin/env python3
"""Абляция лучшей формулы: убираем по одному изменению и смотрим, что потеряем. Так понятно, что именно двигает метрику.

    python scripts/evolve/ablate.py data/evolve/run/best.py
"""
from __future__ import annotations
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from fitness_matching import load_worlds, load_score, evaluate  # noqa: E402

# имя → список (что_заменить, на_что); замена должна встретиться ровно один раз
EDITS = {
    "вес заявленной технологии не зависит от θ (0,4)": [("untested_w = min(max(untested_w, 0.12), 0.80)", "untested_w = 0.4")],
    "подтверждённая технология = 1,0 без доли верных": [("v = 0.85 + 0.15 * min(max(sc, 0.0), 1.0)", "v = 1.0")],
    "грейд: только подтверждённый тестом": [('for g in (cand.get("grade"), cand.get("claimed_grade")):', 'for g in (cand.get("grade"),):')],
    "без штрафа за заявленный грейд выше подтверждённого": [("grade_v *= 0.7", "grade_v *= 1.0")],
    "без снижения точного грейда при низком θ": [("gv = 0.6", "gv = 1.0")],
    "без ограничения вклада ФСП": [("fsp_v = min(fsp_v, 0.7)", "fsp_v = min(fsp_v, 1.0)")],
    "без мультипликативного ворота стек×грейд": [("total = mandatory * (core + soft)", "total = core + soft")],
    "без надбавки 8 % за полное совпадение": [("total *= 1.08", "total *= 1.0")],
    "без давности θ": [("decay = 1.0 if days <= 90 else max(0.6, 1.0 - (days - 90) / 365)", "decay = 1.0")],
    "исходные веса 0,35/0,25/0,20/0,10/0,05/0,05": [('WEIGHTS = {"stack": 0.40, "grade": 0.24, "strength": 0.16, "fsp": 0.06, "activity": 0.06, "conditions": 0.08}',
                                                     'WEIGHTS = {"stack": 0.35, "grade": 0.25, "strength": 0.20, "fsp": 0.10, "activity": 0.05, "conditions": 0.05}')],
    "ожидаемое θ по шкале b (−1,5/−0,5/+0,5/+1,5), размах 1,5": [("expected = -2.5 + (need_idx / max(len(GRADES) - 1, 1)) * 5.0", "expected = -1.5 + need_idx * 1.0"),
                                                             ("rel = (theta - expected) / 2.5", "rel = (theta - expected) / 1.5")],
}


# для формулы захода 3 (g12c0): другой текст — другие фрагменты
EDITS_V2 = {
    "доверие по расхождению грейдов не учитывается (trust = 1)": [("    trust = min(max(trust, 0.45), 1.0)", "    trust = 1.0")],
    "проваленная технология: 0,12 вместо −0,18": [("    failed_w = -0.18", "    failed_w = 0.12")],
    "длинный стек не смягчается (miss_scale = 1)": [("        miss_scale = max(0.35, 1.0 - 0.09 * max(0, n_req - 4))", "        miss_scale = 1.0")],
    "грейд: соседний выше требуемого = 0,60, как и ниже": [("                gv = 0.28", "                gv = 0.60")],
    "грейд: только подтверждённый тестом (без подсказки)": [("    for g in (fg0, use_cg):", "    for g in (fg0,):")],
    "без штрафа «нет ни одной подтверждённой технологии» (×0,80)": [("            stack_v *= 0.80", "            stack_v *= 1.0")],
    "без мультипликативных ворот стек×грейд": [("    total = mandatory * (core + soft)", "    total = core + soft")],
    "без среза ×0,75 при хорошем стеке и чужом грейде": [("        total *= 0.75", "        total *= 1.0")],
    "без градуированной зарплаты (бинарно)": [("            parts_sum += 0.6 + 0.4 * ratio", "            parts_sum += 1.0"), ("            parts_sum += 0.35 * prox", "            parts_sum += 0.0")],
    "сила профиля без давности θ (decay = 1)": [("    strength_v = base * decay", "    strength_v = base")],
    "вес заявленной технологии не зависит от θ и доверия (0,4)": [("    untested_w = min(max(untested_w, 0.06), 0.72)", "    untested_w = 0.4")],
    "веса предыдущей формулы 0,40/0,24/0,16/0,06/0,06/0,08": [('WEIGHTS = {"stack": 0.44, "grade": 0.24, "strength": 0.14, "fsp": 0.05, "activity": 0.05, "conditions": 0.08}',
                                                              'WEIGHTS = {"stack": 0.40, "grade": 0.24, "strength": 0.16, "fsp": 0.06, "activity": 0.06, "conditions": 0.08}')],
}


# для итоговой формулы best_2026-10-07c (заход 5 + упрощение)
EDITS_V3 = {
    "без зарплатного множителя и среза (зарплата только в «условиях»)": [("    if salary_fit is not None:\n        total *= (0.40 + 0.72 * salary_fit)\n", ""),
                                                                         ("            and cand[\"salary_min\"] > need[\"salary_max\"]):\n        total *= 0.55\n", "            and cand[\"salary_min\"] > need[\"salary_max\"]):\n        total *= 1.0\n")],
    "без ступенек покрытия стека в итоге": [("        if coverage >= 0.9:\n            total *= 1.08\n        elif coverage >= 0.75:\n            total *= 1.03\n        elif coverage <= 0.4:\n            total *= 0.78\n        elif coverage <= 0.6:\n            total *= 0.90\n", "")],
    "без штрафов за недостающие технологии": [("        if n_missing >= 3:\n            total *= 0.80\n        elif n_missing >= 2:\n            total *= 0.90\n", ""),
                                              ("        if n_missing >= 2:\n            stack_v *= max(0.55, 1.0 - 0.10 * (n_missing - 1))\n        if n_missing >= 4:\n            stack_v *= 0.85\n", "")],
    "заявленная технология без нижнего порога 0,55": [("                v = max(untested_w, 0.55)", "                v = untested_w")],
    "проваленная по 1–2 заданиям — отрицательный вклад (−0,18), как в заходе 3": [("    failed_w = 0.3", "    failed_w = -0.18")],
    "грейд: только подтверждённый тестом (без подсказки)": [("    for g in (fg0, use_cg):", "    for g in (fg0,):")],
    "грейд: соседний выше требуемого = 0,60, как и ниже": [("                gv = 0.28", "                gv = 0.60")],
    "без мультипликативных ворот стек×грейд": [("    total = mandatory * (core + soft)", "    total = core + soft")],
}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "evolve", "run", "best.py")
    src = open(path, encoding="utf-8").read()
    folder = os.environ.get("ABLATE_WORLDS") or os.path.join(ROOT, "data", "evolve")
    edits = EDITS_V3 if "salary_fit" in src else EDITS_V2 if "trust = min(max(trust" in src else EDITS
    sets = {"обучение": load_worlds(folder, seeds=[11, 12, 16, 17] if edits is not EDITS else [11, 12]), "отложенный 13": load_worlds(folder, seeds=[13]),
            "контроль 14": load_worlds(folder, seeds=[14]), "контроль 15": load_worlds(folder, seeds=[15]), "контроль 18": load_worlds(folder, seeds=[18])}
    base = {k: evaluate(load_score(path), w)["fitness"] for k, w in sets.items()}
    print(f"{'вариант':62} " + " ".join(f"{k:>14}" for k in sets))
    print(f"{'лучшая формула':62} " + " ".join(f"{base[k]:>14.4f}" for k in sets))
    for name, edit_list in edits.items():
        s = src
        ok = True
        for a, b in edit_list:
            if s.count(a) != 1:
                ok = False
                break
            s = s.replace(a, b)
        if not ok:
            print(f"{name:62} —  (фрагмент не найден, пропуск)")
            continue
        tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
        tmp.write(s); tmp.close()
        vals = {k: evaluate(load_score(tmp.name), w)["fitness"] for k, w in sets.items()}
        os.unlink(tmp.name)
        print(f"{name:62} " + " ".join(f"{vals[k] - base[k]:>+14.4f}" for k in sets))


if __name__ == "__main__":
    main()
