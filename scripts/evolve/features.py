"""Признаки кандидатов и потребностей для быстрой оценки формулы подбора без базы данных.

Строит синтетический мир (как eval_matching.py), один раз вытаскивает из базы наблюдаемые признаки каждого кандидата
и истинную релевантность пар, сохраняет в JSON. Дальше любые варианты формулы оцениваются за секунды."""
from __future__ import annotations
import argparse
import json
import os
import random
import re
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))


VARIANTS = {   # проверка устойчивости: что формула могла выучить о генераторе
    "base": {},
    "idealized": {"realistic_test": False},          # прежние миры: θ̂ = θ + шум 0,35, технологии подтверждаются без ошибок
    "overlap04": {"REL_OVERLAP": 0.4}, "overlap06": {"REL_OVERLAP": 0.6},
    "exact_grade": {"REL_GRADE_SPAN": 0},
    "gap05": {"KNOWLEDGE_GAP": 0.5}, "gap25": {"KNOWLEDGE_GAP": 2.5},
    "extreme": {"honesty_only": "extreme"},
}


def build(candidates: int, seed: int, honesty: str, variant: str = "base") -> dict:
    tmp = tempfile.mkdtemp()
    os.environ["FSP_DATABASE_URL"] = f"sqlite:///{tmp}/w.db"
    os.environ["FSP_SECRET_KEY"] = "evo"
    for m in list(sys.modules):
        if m == "app" or m.startswith("app."):
            del sys.modules[m]
    from app.db import init_db, SessionLocal
    from app.seed import ensure_catalog, seed_demo
    from app import synth
    from app.models import Candidate, TestSession
    from app.services.matching import last_thetas, candidate_features
    from sqlalchemy import select
    from app.services.testing import simulate
    v = VARIANTS[variant]
    for knob in ("REL_OVERLAP", "REL_GRADE_SPAN"):
        if knob in v:
            setattr(synth, knob, v[knob])
    if "KNOWLEDGE_GAP" in v:
        simulate.KNOWLEDGE_GAP = v["KNOWLEDGE_GAP"]
    init_db(); ensure_catalog()
    seed_demo(n_candidates=candidates, rng_seed=seed, honesty=honesty, realistic_test=v.get("realistic_test", True))
    rng = random.Random(seed)
    events = synth.load_events()
    truth = {c.idx: c for c in synth.make_candidates(candidates, rng, events, honesty=honesty)}
    needs = synth.make_needs(random.Random(seed))
    now = datetime.now(timezone.utc)
    out = {"meta": {"candidates": candidates, "seed": seed, "honesty": honesty, "variant": variant}, "candidates": [], "needs": []}
    with SessionLocal() as db:
        cands = db.scalars(select(Candidate)).all()
        thetas = last_thetas(db, [c.id for c in cands])
        cmap = {}
        for c in cands:
            if not c.visible_to_employers:
                continue
            m = re.match(r"cand(\d+)@", c.user.email)
            t = truth[int(m.group(1)) - 1] if m else next(x for x in truth.values() if x.full_name == c.full_name)
            th = thetas.get(c.id)
            feat = candidate_features(c, th, now)
            feat["truth"] = {"grade": t.true_grade, "theta": t.theta, "stack": t.true_stack, "fsp_rank": t.fsp["rank"] if t.fsp else None}
            out["candidates"].append(feat)
            cmap[c.id] = t
        for n in needs:
            rel = {}
            for f in out["candidates"]:
                t = cmap[f["id"]]
                r = int(synth.relevant(n, t))
                strong = t.theta >= synth.GRADE_THETA[t.true_grade]
                fsp_good = bool(t.fsp and t.fsp["rank"] in ("ms", "kms", "r1"))
                rel[str(f["id"])] = 0 if not r else 1 + int(t.true_grade == n.grade) + int(strong) + int(fsp_good)
            out["needs"].append({"title": n.title, "spec": n.specialization, "grade": n.grade, "stack": n.stack, "salary_min": n.salary_min,
                                 "salary_max": n.salary_max, "work_format": n.work_format, "gain": rel})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", type=int, default=300)
    ap.add_argument("--seeds", default="11,12,13")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "evolve"))
    ap.add_argument("--variant", default="base", choices=sorted(VARIANTS))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    honesties = [VARIANTS[args.variant]["honesty_only"]] if "honesty_only" in VARIANTS[args.variant] else ["honest", "typical", "inflated"]
    for honesty in honesties:
        for seed in [int(x) for x in args.seeds.split(",")]:
            w = build(args.candidates, seed, honesty, args.variant)
            p = os.path.join(args.out, f"world_{honesty}_{seed}.json")
            json.dump(w, open(p, "w"), ensure_ascii=False)
            print(p, len(w["candidates"]), "кандидатов", len(w["needs"]), "потребностей")


if __name__ == "__main__":
    main()
