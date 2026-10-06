#!/usr/bin/env python3
"""Оценка механики подбора на синтетическом мире с известной истиной (docs/07, раздел 5).

Строит отдельную базу SQLite, заполняет её синтетическими кандидатами (истинные навыки скрыты, наблюдаемые — производные),
прогоняет потребности через боевой build_selection и сравнивает с истинной релевантностью. Базовые варианты для сравнения:
случайный порядок и подбор только по ключевым словам резюме (заявленный стек = 1,0; грейд — заявленный).

    python scripts/eval_matching.py --candidates 400 --seed 11
"""
from __future__ import annotations
import argparse
import math
import os
import random
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))


def ndcg(rels: list[int], k: int) -> float:
    dcg = sum(r / math.log2(i + 2) for i, r in enumerate(rels[:k]))
    ideal = sorted(rels, reverse=True)
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal[:k]))
    return dcg / idcg if idcg else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", type=int, default=400)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--honesty", default="typical", choices=["honest", "typical", "inflated"])
    args = ap.parse_args()
    tmp = tempfile.mkdtemp()
    os.environ["FSP_DATABASE_URL"] = f"sqlite:///{tmp}/eval.db"
    os.environ["FSP_SECRET_KEY"] = "eval"
    from app.db import init_db, SessionLocal
    from app.seed import ensure_catalog, seed_demo
    from app import synth
    from app.models import Candidate, User
    from app.services.matching import build_selection, candidate_pool, last_thetas, score_candidate
    from sqlalchemy import select
    init_db(); ensure_catalog()
    seed_demo(n_candidates=args.candidates, rng_seed=args.seed, honesty=args.honesty)
    rng = random.Random(args.seed)
    events = synth.load_events()
    truth = {c.idx: c for c in synth.make_candidates(args.candidates, rng, events, honesty=args.honesty)}   # тот же генератор и зерно → та же истина
    needs = synth.make_needs(random.Random(args.seed))
    k = args.k
    rows = []
    agg = {"ours": [], "keywords": [], "random": []}
    with SessionLocal() as db:
        cands = db.scalars(select(Candidate)).all()
        idx_by_id = {}
        for c in cands:
            import re
            m = re.match(r"cand(\d+)@", c.user.email)
            n = int(m.group(1)) - 1 if m else next(i for i, t in truth.items() if t.full_name == c.full_name)   # учётные записи жюри переименованы
            idx_by_id[c.id] = n
        for need in needs:
            nd = {"specialization_code": need.specialization, "grade": need.grade, "stack": need.stack, "salary_min": need.salary_min,
                  "salary_max": need.salary_max, "work_format": need.work_format}
            rel, gain = {}, {}
            for c in cands:
                if not c.visible_to_employers:
                    continue
                t = truth[idx_by_id[c.id]]
                r = int(synth.relevant(need, t))
                rel[c.id] = r
                # градуированная польза по ТЗ: релевантен (1) + точный грейд (1) + сильный профиль (1) + подтверждённое достижение ФСП (1)
                strong = t.theta >= synth.GRADE_THETA[t.true_grade]
                fsp_good = bool(t.fsp and t.fsp["rank"] in ("ms", "kms", "r1"))
                gain[c.id] = 0 if not r else 1 + int(t.true_grade == need.grade) + int(strong) + int(fsp_good)
            total_rel = sum(rel.values())
            # наш подбор
            _, results = build_selection(db, nd, {}, None, limit=len(cands))
            ours = [rel.get(r["candidate_id"], 0) for r in results]
            ours_g = [gain.get(r["candidate_id"], 0) for r in results]
            # базовый: ключевые слова резюме (все заявленные технологии за 1,0, грейд — заявленный)
            pool = candidate_pool(db, {"specialization_code": need.specialization})
            kw = []
            for c in pool:
                declared = {s.skill for s in c.skills}
                stack = len(set(need.stack) & declared) / len(need.stack) if need.stack else 0
                gfit = 1.0 if c.claimed_grade == need.grade else 0.5 if abs(synth.GRADES.index(c.claimed_grade) - synth.GRADES.index(need.grade)) == 1 else 0.0
                kw.append((0.6 * stack + 0.4 * gfit, c.id))
            kw.sort(key=lambda x: (-x[0], x[1]))
            kw_rels = [rel.get(cid, 0) for _, cid in kw]
            kw_g = [gain.get(cid, 0) for _, cid in kw]
            # случайный порядок в той же специализации
            ids = [c.id for c in pool]
            rng.shuffle(ids)
            rnd_rels = [rel.get(cid, 0) for cid in ids]
            rnd_g = [gain.get(cid, 0) for cid in ids]
            for name, rels, gains in (("ours", ours, ours_g), ("keywords", kw_rels, kw_g), ("random", rnd_rels, rnd_g)):
                p5 = sum(rels[:5]) / 5
                pk = sum(rels[:k]) / k
                nd10 = ndcg(gains, k)
                rr = next((1 / (i + 1) for i, r in enumerate(rels) if r), 0.0)
                agg[name].append((p5, pk, nd10, rr))
            rows.append((need.title, total_rel, sum(ours[:5]), sum(kw_rels[:5]), sum(rnd_rels[:5])))
    print(f"Кандидатов: {args.candidates}, потребностей: {len(needs)}, k = {k}, мир: {args.honesty}\n")
    print(f"{'Потребность':48} {'релев.':>7} {'наш@5':>6} {'слова@5':>8} {'случ.@5':>8}")
    for t, tr, a, b, c in rows:
        print(f"{t[:48]:48} {tr:7d} {a:6d} {b:8d} {c:8d}")
    print()
    print(f"{'Метод':12} {'P@5':>6} {'P@'+str(k):>6} {'nDCG@'+str(k)+'*':>9} {'MRR':>6}   (* — градуированная польза: релевантен + точный грейд + сильный профиль + достижение ФСП)")
    for name, title in (("ours", "подбор"), ("keywords", "слова резюме"), ("random", "случайно")):
        m = [sum(x[i] for x in agg[name]) / len(agg[name]) for i in range(4)]
        print(f"{title:12} {m[0]:6.2f} {m[1]:6.2f} {m[2]:8.2f} {m[3]:6.2f}")


if __name__ == "__main__":
    main()
