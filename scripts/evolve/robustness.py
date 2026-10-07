#!/usr/bin/env python3
"""Устойчивость к устройству генератора: формулы на мирах с изменёнными правилами (scripts/evolve/features.py --variant).

    python scripts/evolve/robustness.py --prog финал=scripts/evolve/best.py --prog слова=keywords --pair финал:слова
"""
from __future__ import annotations
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fitness_matching import load_worlds  # noqa: E402
from significance import per_query, compare, load_prog  # noqa: E402

TITLE = {"base": "как в обучении (другое зерно)", "idealized": "идеальный тест (прежние миры)", "overlap04": "релевантность: ≥ 40 % стека",
         "overlap06": "релевантность: ≥ 60 % стека", "exact_grade": "релевантность: только точный грейд", "gap05": "незнание приписанной технологии слабее (0,5)",
         "gap25": "незнание приписанной технологии сильнее (2,5)", "extreme": "крайнее приукрашивание резюме"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.dirname(HERE)), "data", "evolve_variants"))
    ap.add_argument("--prog", action="append", required=True)
    ap.add_argument("--pair", action="append", required=True)
    args = ap.parse_args()
    progs = dict(p.split("=", 1) for p in args.prog)
    fns = {k: load_prog(v) for k, v in progs.items()}
    print(f"{'вариант генератора':44} " + " ".join(f"{k[:12]:>12}" for k in progs) + "   " + "   ".join(f"{p.replace(':', ' − ')} [95 %]" for p in args.pair))
    for v in TITLE:
        folder = os.path.join(args.root, v)
        if not os.path.isdir(folder):
            continue
        ws = load_worlds(folder)
        pq = {k: per_query(f, ws) for k, f in fns.items()}
        cells = []
        for pair in args.pair:
            a, b = pair.split(":")
            r = compare(pq[a], pq[b], reps=2000)
            cells.append(f"{r['delta']:+.3f} [{r['lo']:+.3f}; {r['hi']:+.3f}]")
        print(f"{TITLE[v]:44} " + " ".join(f"{np.mean(list(d.values())):12.3f}" for d in pq.values()) + "   " + "   ".join(cells))


if __name__ == "__main__":
    main()
