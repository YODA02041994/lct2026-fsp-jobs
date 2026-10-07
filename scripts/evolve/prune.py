#!/usr/bin/env python3
"""Упрощение формулы по RRSI: жадно убираем правила по одному; удаление остаётся, если фитнес на обучающих мирах падает
не больше порога шума. Итог сравнивается с исходной формулой на контрольных мирах парным бутстрепом.

    python scripts/evolve/prune.py data/evolve_v2/run5/cand_g8c0.py --worlds data/evolve_v3 --out scripts/evolve/pruned.py
"""
from __future__ import annotations
import argparse
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fitness_matching import load_worlds, load_score, evaluate  # noqa: E402
from significance import per_query, compare  # noqa: E402

EDITS = [
    ("доверие не зависит от давности теста", [("    trust *= (0.85 + 0.15 * decay)\n", "")]),
    ("уверенность в θ не зависит от давности", [("    theta_conf = min(max((rel + 1.5) / 3.0, 0.0), 1.0) * (0.5 + 0.5 * decay)", "    theta_conf = min(max((rel + 1.5) / 3.0, 0.0), 1.0)")]),
    ("подтверждённая технология без поправки на доверие", [("                if trust < 0.9:\n                    v *= (0.90 + 0.05 * trust)\n", "")]),
    ("без штрафа стека за 2+ и 4+ недостающих", [("        if n_missing >= 2:\n            stack_v *= max(0.55, 1.0 - 0.10 * (n_missing - 1))\n        if n_missing >= 4:\n            stack_v *= 0.85\n", "")]),
    ("без надбавки стека за покрытие длинного стека", [("        if n_req >= 5 and coverage >= 0.8:\n            stack_v = min(stack_v * 1.06, 1.0)\n", "")]),
    ("без штрафа «нет подтверждённых» в стеке", [("        if n_confirmed == 0:\n            stack_v *= 0.82\n", "")]),
    ("без штрафа «ничего не проверено» в стеке", [("        if n_tested == 0 and n_hit > 0:\n            stack_v *= 0.90\n", "")]),
    ("стек без множителя покрытия", [("        stack_v *= (0.78 + 0.22 * coverage)\n", "")]),
    ("без надбавки 8 % за полное совпадение", [("    if stack_v >= 0.85 and grade_v >= 1.0:\n        total *= 1.08\n", "")]),
    ("без среза «хороший стек, чужой грейд»", [("    if stack_v >= 0.7 and grade_v == 0.0:\n        total *= 0.75\n", "")]),
    ("без среза за заявленный грейд на 2 выше", [("    if gap >= 2:\n        total *= 0.88\n", "")]),
    ("без среза «ничего не проверено» в итоге", [("    if stack and n_tested == 0:\n        total *= 0.92\n", "")]),
    ("без ступенек покрытия в итоге", [("        if coverage >= 0.9:\n            total *= 1.08\n        elif coverage >= 0.75:\n            total *= 1.03\n        elif coverage <= 0.4:\n            total *= 0.78\n        elif coverage <= 0.6:\n            total *= 0.90\n", "")]),
    ("без штрафа итога за 2+ недостающих", [("        if n_missing >= 3:\n            total *= 0.80\n        elif n_missing >= 2:\n            total *= 0.90\n", "")]),
    ("без надбавки за долю подтверждённых", [("        if n_present > 0:\n            conf_share = n_confirmed / n_present\n            total *= (0.95 + 0.10 * conf_share)\n", "")]),
    ("без штрафа за провалы в итоге", [("        if n_present > 0 and n_failed > 0:\n            total *= max(0.85, 1.0 - 0.06 * n_failed)\n", "")]),
    ("без второго зарплатного среза ×0,55", [("    if (need.get(\"salary_max\") is not None and cand.get(\"salary_min\") is not None\n            and cand[\"salary_min\"] > need[\"salary_max\"]):\n        total *= 0.55\n", "")]),
    ("грейд без поправок на слабое θ", [("            if gv == 1.0 and rel < -0.7:\n                gv = 0.55\n            elif gv == 0.60 and rel < -1.0:\n                gv = 0.35\n", "")]),
    ("недостающие технологии без смягчения длинного стека", [("        miss_scale = max(0.35, 1.0 - 0.09 * max(0, n_req - 4))", "        miss_scale = 1.0")]),
    ("заявленная технология без поправки на расхождение грейдов", [("                if gap >= 1:\n                    v *= (0.72 + 0.28 * theta_conf)\n", "")]),
]


def fit_of(src: str, worlds) -> float:
    t = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8"); t.write(src); t.close()
    try:
        return evaluate(load_score(t.name), worlds)["fitness"]
    finally:
        os.unlink(t.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("program")
    ap.add_argument("--worlds", required=True)
    ap.add_argument("--train", default="11,12,13,16,17")
    ap.add_argument("--control", default="14,15,18")
    ap.add_argument("--tol", type=float, default=0.002, help="допустимая потеря фитнеса на обучении за одно удаление")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    src0 = open(args.program, encoding="utf-8").read()
    tr = load_worlds(args.worlds, seeds=[int(x) for x in args.train.split(",")])
    ct = load_worlds(args.worlds, seeds=[int(x) for x in args.control.split(",")])
    cur, cur_fit = src0, fit_of(src0, tr)
    print(f"исходная: обучение {cur_fit:.4f}")
    removed = []
    for name, reps in EDITS:
        cand = cur
        ok = True
        for a, b in reps:
            if cand.count(a) != 1:
                ok = False
                break
            cand = cand.replace(a, b)
        if not ok:
            print(f"  — {name}: фрагмент не найден")
            continue
        f = fit_of(cand, tr)
        verdict = "убрано" if f >= cur_fit - args.tol else "оставлено"
        print(f"  {verdict:9} {name:58} обучение {f:.4f} (Δ {f - cur_fit:+.4f})")
        if verdict == "убрано":
            cur, cur_fit = cand, f
            removed.append(name)
    open(args.out, "w", encoding="utf-8").write(cur)
    a, b = per_query(load_score(args.out), ct), per_query(load_score(args.program), ct)
    r = compare(a, b)
    print(f"\nубрано правил: {len(removed)} из {len(EDITS)}; строк кода: {src0.count(chr(10))} → {cur.count(chr(10))}")
    print(f"контроль: упрощённая {np.mean(list(a.values())):.4f}, исходная {np.mean(list(b.values())):.4f}; "
          f"Δ {r['delta']:+.4f} [{r['lo']:+.4f}; {r['hi']:+.4f}], миров в плюс {r['wins']}/{r['worlds']}")


if __name__ == "__main__":
    main()
