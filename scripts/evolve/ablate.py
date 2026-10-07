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


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "evolve", "run", "best.py")
    src = open(path, encoding="utf-8").read()
    folder = os.path.join(ROOT, "data", "evolve")
    sets = {"обучение 11,12": load_worlds(folder, seeds=[11, 12]), "отложенный 13": load_worlds(folder, seeds=[13]), "свежий 14": load_worlds(folder, seeds=[14])}
    base = {k: evaluate(load_score(path), w)["fitness"] for k, w in sets.items()}
    print(f"{'вариант':62} " + " ".join(f"{k:>14}" for k in sets))
    print(f"{'лучшая формула':62} " + " ".join(f"{base[k]:>14.4f}" for k in sets))
    for name, edits in EDITS.items():
        s = src
        ok = True
        for a, b in edits:
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
