#!/usr/bin/env python3
"""Калибровка показанной оценки: сырой итог формулы → вероятность, что кандидат подходит под потребность.

Порядок кандидатов не меняется (логистическое преобразование монотонно), меняется только смысл числа «из 100»:
80 означает, что среди кандидатов с такой сырой оценкой подходят примерно 8 из 10 (по синтетическим мирам).
Подходит = правило релевантности мира (специализация, истинный грейд ±1, ≥50 % истинного стека, пересечение зарплат).
Пул — как в боевом build_selection: та же специализация и грейд ±1 от требуемого.

    cd backend && ../.venv/bin/python ../scripts/evolve/calibrate.py ../scripts/evolve/best_2026-10-07.py --fit 11,12,13 --check 14
"""
from __future__ import annotations
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from fitness_matching import load_worlds, load_score, GRADES  # noqa: E402


def pairs(score, worlds):
    out = []
    for w in worlds:
        cands = w["candidates"]
        for need in w["needs"]:
            gi = GRADES.index(need["grade"])
            pool = [c for c in cands if c["spec"] == need["spec"] and c["grade"] and abs(GRADES.index(c["grade"]) - gi) <= 1]
            for c in pool:
                v = score(c, need)
                raw = v[0] if isinstance(v, tuple) else v
                out.append((raw, 1 if need["gain"][str(c["id"])] > 0 else 0))
    return out


def fit_logistic(data, iters=100):
    """Ньютон для p = σ(a·x + b)."""
    a, b = 5.0, -2.5
    for _ in range(iters):
        g_a = g_b = h_aa = h_ab = h_bb = 0.0
        for x, y in data:
            p = 1 / (1 + math.exp(-(a * x + b)))
            g_a += (p - y) * x; g_b += (p - y)
            w = p * (1 - p)
            h_aa += w * x * x; h_ab += w * x; h_bb += w
        det = h_aa * h_bb - h_ab * h_ab
        if abs(det) < 1e-12:
            break
        da = (h_bb * g_a - h_ab * g_b) / det
        db = (h_aa * g_b - h_ab * g_a) / det
        a -= da; b -= db
        if abs(da) + abs(db) < 1e-9:
            break
    return a, b


def report(data, a, b, title):
    bins = [[0, 0.0, 0] for _ in range(10)]
    brier_cal = brier_raw = 0.0
    for x, y in data:
        p = 1 / (1 + math.exp(-(a * x + b)))
        i = min(int(p * 10), 9)
        bins[i][0] += 1; bins[i][1] += p; bins[i][2] += y
        brier_cal += (p - y) ** 2; brier_raw += (x - y) ** 2
    n = len(data)
    print(f"\n{title}: пар {n}, доля подходящих {sum(y for _, y in data) / n:.2f}; Брайер сырой {brier_raw / n:.3f} → калиброванный {brier_cal / n:.3f}")
    print("  показано   пар   предсказано  на самом деле")
    for i, (cnt, sp, sy) in enumerate(bins):
        if cnt:
            print(f"  {i * 10:>3}–{i * 10 + 9:<3} {cnt:>6}   {sp / cnt:>8.2f}      {sy / cnt:>8.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("program")
    ap.add_argument("--fit", default="11,12,13")
    ap.add_argument("--check", default="14")
    args = ap.parse_args()
    score = load_score(args.program)
    folder = os.path.join(ROOT, "data", "evolve")
    fit_data = pairs(score, load_worlds(folder, seeds=[int(x) for x in args.fit.split(",")]))
    a, b = fit_logistic(fit_data)
    print(f"калибровка: p = σ({a:.4f}·raw {b:+.4f}); raw 0,3 → {100 / (1 + math.exp(-(a * 0.3 + b))):.0f}, 0,5 → {100 / (1 + math.exp(-(a * 0.5 + b))):.0f}, 0,7 → {100 / (1 + math.exp(-(a * 0.7 + b))):.0f}, 0,9 → {100 / (1 + math.exp(-(a * 0.9 + b))):.0f}")
    report(fit_data, a, b, "обучение")
    check = pairs(score, load_worlds(folder, seeds=[int(x) for x in args.check.split(",")]))
    report(check, a, b, "контроль")
    print(f"\nCALIBRATION = {{\"a\": {a:.4f}, \"b\": {b:.4f}}}")


if __name__ == "__main__":
    main()
