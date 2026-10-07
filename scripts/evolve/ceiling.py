#!/usr/bin/env python3
"""Потолок признаков: насколько хорошо можно ранжировать по тем же наблюдаемым данным, если не требовать объяснимости.

Градиентный бустинг (sklearn HistGradientBoostingRegressor) и линейная модель учатся предсказывать пользу пары
«потребность — кандидат» на обучающих мирах и ранжируют кандидатов на контрольных. Сравнение с формулой — тем же парным
бутстрепом (significance.py). Если формула в пределах шума от бустинга — оптимизировать её дальше бессмысленно.

    python scripts/evolve/ceiling.py --train 11,12,13,16,17 --control 14,15,18 --formula scripts/evolve/best_2026-10-07b.py
"""
from __future__ import annotations
import argparse
import math
import os
import sys

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fitness_matching import GRADES, LEVEL_SCORE, SPEC_DISCIPLINE, load_worlds, load_score, keyword_baseline  # noqa: E402
from significance import per_query, compare  # noqa: E402

NAMES = ["n_stack", "conf", "decl", "failed", "missing", "conf_share", "decl_share", "failed_share", "covered_share", "conf_score_mean",
         "grade_diff", "claimed_diff", "claimed_gap", "theta", "theta_rel", "theta_days", "fsp_best", "fsp_in_disc",
         "active_days", "sal_overlap", "sal_cmin_over_nmax", "fmt_match", "skills_total", "skills_conf_total"]


def pair_features(c: dict, need: dict) -> list[float]:
    nan = float("nan")
    stack = need.get("stack") or []
    sk = c.get("skills") or {}
    conf = [s for s in stack if s in sk and sk[s]["confirmed"]]
    failed = [s for s in stack if s in sk and not sk[s]["confirmed"] and sk[s]["tested"]]
    decl = [s for s in stack if s in sk and not sk[s]["confirmed"] and not sk[s]["tested"]]
    n = len(stack) or 1
    scores = [sk[s]["score"] for s in conf if sk[s].get("score") is not None]
    gn = GRADES.index(need["grade"])
    gc = GRADES.index(c["grade"]) if c.get("grade") in GRADES else nan
    gcl = GRADES.index(c["claimed_grade"]) if c.get("claimed_grade") in GRADES else nan
    th = c.get("theta")
    disc = SPEC_DISCIPLINE.get(c.get("spec"), set())
    fsp = [LEVEL_SCORE.get(a.get("level"), 0.2) for a in c.get("fsp") or []]
    fsp_in = [LEVEL_SCORE.get(a.get("level"), 0.2) for a in c.get("fsp") or [] if a.get("discipline") in disc]
    nmin, nmax, cmin = need.get("salary_min"), need.get("salary_max"), c.get("salary_min")
    cmax = c.get("salary_max") or nmax
    if None not in (nmin, nmax, cmin) and cmax:
        ov = max(0.0, min(nmax, cmax) - max(nmin, cmin)) / max(nmax - nmin, 1.0)
        ratio = cmin / nmax if nmax else nan
    else:
        ov, ratio = nan, nan
    nf, cf = need.get("work_format"), c.get("work_format")
    fmt = nan if not (nf and cf) else float(nf == cf or "hybrid" in (nf, cf))
    return [len(stack), len(conf), len(decl), len(failed), n - len(conf) - len(decl) - len(failed),
            len(conf) / n, len(decl) / n, len(failed) / n, (len(conf) + len(decl)) / n, float(np.mean(scores)) if scores else nan,
            gc - gn, gcl - gn, gcl - gc, th if th is not None else nan, (th - (-1.5 + gn)) if th is not None else nan,
            c.get("theta_days") if c.get("theta_days") is not None else nan, max(fsp) if fsp else 0.0, max(fsp_in) if fsp_in else 0.0,
            float(c.get("active_days") if c.get("active_days") is not None else 999), ov, ratio, fmt, len(sk), sum(1 for v in sk.values() if v["confirmed"])]


def pool_of(w, need):
    gi = GRADES.index(need["grade"])
    return [c for c in w["candidates"] if c["spec"] == need["spec"] and c["grade"] and abs(GRADES.index(c["grade"]) - gi) <= 1]


def dataset(worlds):
    X, y = [], []
    for w in worlds:
        for need in w["needs"]:
            for c in pool_of(w, need):
                X.append(pair_features(c, need)); y.append(need["gain"].get(str(c["id"]), 0))
    return np.array(X, dtype=float), np.array(y, dtype=float)


def as_score(model):
    cache = {}

    def score(c, need):
        key = (id(need), c["id"])
        if key not in cache:
            cache[key] = float(model.predict(np.array([pair_features(c, need)], dtype=float))[0])
        return cache[key]
    return score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", default=os.path.join(os.path.dirname(os.path.dirname(HERE)), "data", "evolve"))
    ap.add_argument("--train", default="11,12,13,16,17")
    ap.add_argument("--control", default="14,15,18")
    ap.add_argument("--formula", default=os.path.join(HERE, "best_2026-10-07b.py"))
    args = ap.parse_args()
    tr = load_worlds(args.worlds, seeds=[int(x) for x in args.train.split(",")])
    ct = load_worlds(args.worlds, seeds=[int(x) for x in args.control.split(",")])
    X, y = dataset(tr)
    print(f"обучение: {len(tr)} миров, пар {len(y)}; контроль: {len(ct)} миров")
    gbm = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=40, l2_regularization=1.0, random_state=0).fit(X, y)
    lin = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), Ridge(alpha=1.0)).fit(X, y)
    pq = {"формула": per_query(load_score(args.formula), ct), "бустинг (потолок)": per_query(as_score(gbm), ct),
          "линейная модель": per_query(as_score(lin), ct), "слова резюме": per_query(keyword_baseline, ct)}
    for name, d in pq.items():
        print(f"  {name:22} фитнес {np.mean(list(d.values())):.4f}")
    print()
    for a, b in (("бустинг (потолок)", "формула"), ("формула", "линейная модель"), ("формула", "слова резюме")):
        r = compare(pq[a], pq[b])
        print(f"{a + ' над ' + b:42} Δ {r['delta']:+.4f} [{r['lo']:+.4f}; {r['hi']:+.4f}]  миров в плюс {r['wins']}/{r['worlds']}")
    Xc, yc = dataset(ct)
    imp = permutation_importance(gbm, Xc, yc, n_repeats=5, random_state=0)
    order = np.argsort(-imp.importances_mean)[:10]
    print("\nважность признаков для бустинга (перестановочная, контрольные миры):")
    for i in order:
        print(f"  {NAMES[i]:22} {imp.importances_mean[i]:.4f}")


if __name__ == "__main__":
    main()
