"""Оценка формулы подбора на сохранённых мирах. Формула — Python-функция score(cand, need) -> float из файла-кандидата
(блок между маркерами EVOLVE-BLOCK-START / EVOLVE-BLOCK-END)."""
from __future__ import annotations
import glob
import json
import math
import os
import sys

GRADES = ["junior", "middle", "senior", "lead"]
SPEC_DISCIPLINE = {"backend": {"algorithmic", "product"}, "frontend": {"product"}, "fullstack": {"product"}, "mobile": {"product"},
                   "data": {"algorithmic", "product"}, "devops": {"product", "security"}, "qa": {"product"}, "analytics": {"product"}, "security": {"security"}}
LEVEL_SCORE = {"A1": 0.2, "A2": 0.4, "A3": 0.6, "A4": 0.8, "A5": 1.0}


def ndcg(gains, k=10):
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains[:k]))
    ideal = sorted(gains, reverse=True)
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal[:k]))
    return dcg / idcg if idcg else 0.0


def load_worlds(folder: str, seeds: list[int] | None = None) -> list[dict]:
    ws = []
    for p in sorted(glob.glob(os.path.join(folder, "world_*.json"))):
        w = json.load(open(p))
        if seeds is None or w["meta"]["seed"] in seeds:
            ws.append(w)
    return ws


def _total(v):
    return v[0] if isinstance(v, tuple) else v


def keyword_baseline(c, need):
    """Базовый вариант: все заявленные технологии за 1,0, грейд — заявленный кандидатом."""
    stack = need.get("stack") or []
    sv = sum(1 for s in stack if s in c["skills"]) / len(stack) if stack else 0.0
    cg = c.get("claimed_grade") or c.get("grade")
    d = abs(GRADES.index(need["grade"]) - GRADES.index(cg)) if cg else 9
    gv = 1.0 if d == 0 else 0.5 if d == 1 else 0.0
    return 0.6 * sv + 0.4 * gv


def load_score(path: str):
    src = open(path, encoding="utf-8").read()
    ns = {"math": math, "GRADES": GRADES, "SPEC_DISCIPLINE": SPEC_DISCIPLINE, "LEVEL_SCORE": LEVEL_SCORE}
    exec(compile(src, path, "exec"), ns)
    return ns["score"]


def evaluate(score, worlds: list[dict], k: int = 10) -> dict:
    per_world = {}
    for w in worlds:
        cands = w["candidates"]
        p5s, p10s, nds = [], [], []
        for need in w["needs"]:
            # как в бою: специализация потребности, соседние грейды
            gi = GRADES.index(need["grade"])
            pool = [c for c in cands if c["spec"] == need["spec"] and c["grade"] and abs(GRADES.index(c["grade"]) - gi) <= 1]
            scored = sorted(((_total(score(c, need)), -c["id"], c) for c in pool), key=lambda x: (-x[0], -x[1]))
            gains = [need["gain"].get(str(c["id"]), 0) for _, _, c in scored]
            rels = [1 if g else 0 for g in gains]
            p5s.append(sum(rels[:5]) / 5); p10s.append(sum(rels[:k]) / k); nds.append(ndcg(gains, k))
        key = f"{w['meta']['honesty']}_{w['meta']['seed']}"
        per_world[key] = {"p5": sum(p5s) / len(p5s), "p10": sum(p10s) / len(p10s), "ndcg": sum(nds) / len(nds)}
    agg = {m: sum(v[m] for v in per_world.values()) / len(per_world) for m in ("p5", "p10", "ndcg")}
    fitness = 0.5 * agg["ndcg"] + 0.3 * agg["p5"] + 0.2 * agg["p10"]
    return {"fitness": round(fitness, 4), **{k2: round(v, 4) for k2, v in agg.items()}, "per_world": per_world}


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "evolve")
    prog = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "score_baseline.py")
    worlds = load_worlds(folder)
    res = evaluate(load_score(prog), worlds)
    print(json.dumps({k: v for k, v in res.items() if k != "per_world"}, ensure_ascii=False))
    for k, v in res["per_world"].items():
        print(f"  {k:16} P@5 {v['p5']:.2f}  P@10 {v['p10']:.2f}  nDCG {v['ndcg']:.2f}")
    base = evaluate(keyword_baseline, worlds)
    print("базовый вариант «слова резюме»:", json.dumps({k: v for k, v in base.items() if k != "per_world"}, ensure_ascii=False))
