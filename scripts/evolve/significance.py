#!/usr/bin/env python3
"""Значимость разниц между формулами подбора: парный бутстреп по запросам (потребностям) на контрольных мирах.

Фитнес — линейная комбинация метрик по запросам (0,5·nDCG@10 + 0,3·P@5 + 0,2·P@10), поэтому его можно считать по каждому
запросу отдельно и сравнивать формулы попарно на одних и тех же запросах. Бутстреп перевыбирает потребности внутри каждого мира.
Правило отбора по RRSI: изменение принимается, только если нижняя граница 95 % интервала прироста выше нуля.

    python scripts/evolve/significance.py --worlds data/evolve --seeds 14,15,18 \
        --prog исходная=scripts/evolve/score_baseline.py --prog финал=scripts/evolve/best_2026-10-07b.py --prog слова=keywords \
        --pair финал:исходная --pair финал:слова
"""
from __future__ import annotations
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fitness_matching import GRADES, load_worlds, load_score, keyword_baseline, ndcg, _total  # noqa: E402


def per_query(score, worlds, k: int = 10) -> dict:
    """→ {(мир, № потребности): фитнес запроса}."""
    out = {}
    for w in worlds:
        key = f"{w['meta']['honesty']}_{w['meta']['seed']}"
        for qi, need in enumerate(w["needs"]):
            gi = GRADES.index(need["grade"])
            pool = [c for c in w["candidates"] if c["spec"] == need["spec"] and c["grade"] and abs(GRADES.index(c["grade"]) - gi) <= 1]
            scored = sorted(((_total(score(c, need)), -c["id"], c) for c in pool), key=lambda x: (-x[0], -x[1]))
            gains = [need["gain"].get(str(c["id"]), 0) for _, _, c in scored]
            rels = [1 if g else 0 for g in gains]
            out[(key, qi)] = 0.5 * ndcg(gains, k) + 0.3 * sum(rels[:5]) / 5 + 0.2 * sum(rels[:k]) / k
    return out


def compare(a: dict, b: dict, reps: int = 4000, seed: int = 7) -> dict:
    keys = sorted(a)
    worlds = sorted({k[0] for k in keys})
    by_w = {w: np.array([a[k] - b[k] for k in keys if k[0] == w]) for w in worlds}
    rng = np.random.default_rng(seed)
    boots = np.empty(reps)
    for r in range(reps):
        boots[r] = np.mean(np.concatenate([d[rng.integers(0, len(d), len(d))] for d in by_w.values()]))
    delta = float(np.mean(np.concatenate(list(by_w.values()))))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    wins = sum(1 for d in by_w.values() if d.mean() > 0)
    return {"delta": delta, "lo": float(lo), "hi": float(hi), "p_le0": float(np.mean(boots <= 0)), "wins": wins, "worlds": len(by_w),
            "se": float(np.std(boots))}


def load_prog(spec: str):
    return keyword_baseline if spec == "keywords" else load_score(spec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", default=os.path.join(os.path.dirname(os.path.dirname(HERE)), "data", "evolve"))
    ap.add_argument("--seeds", default="14,15,18")
    ap.add_argument("--prog", action="append", required=True, help="имя=путь (или имя=keywords)")
    ap.add_argument("--pair", action="append", required=True, help="A:B — прирост A над B")
    args = ap.parse_args()
    worlds = load_worlds(args.worlds, seeds=[int(x) for x in args.seeds.split(",")])
    progs = dict(p.split("=", 1) for p in args.prog)
    pq = {name: per_query(load_prog(path), worlds) for name, path in progs.items()}
    n = len(next(iter(pq.values())))
    print(f"контрольные миры: {len(worlds)} (зёрна {args.seeds}), запросов: {n}")
    for name, d in pq.items():
        print(f"  {name:28} фитнес {np.mean(list(d.values())):.4f}")
    print(f"\n{'сравнение':40} {'Δ':>8} {'95 % интервал':>18} {'P(Δ≤0)':>8} {'миров в плюс':>13}")
    for pair in args.pair:
        a, b = pair.split(":")
        r = compare(pq[a], pq[b])
        print(f"{a + ' над ' + b:40} {r['delta']:+8.4f} [{r['lo']:+.4f}; {r['hi']:+.4f}] {r['p_le0']:8.3f} {r['wins']:>6}/{r['worlds']}")


if __name__ == "__main__":
    main()
