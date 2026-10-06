#!/usr/bin/env python3
"""Валидация механики тестирования (docs/08, раздел 5) на синтетических кандидатах с известным умением θ.

Ответы моделируются по Рашу: P(верно) = σ(θ − b); для заданий с выбором добавлено угадывание 1/n вариантов.
Прогоняется настоящий движок: подбор шаблонов по уровню и стеку, адаптивные блоки, EAP, решение о грейде.

    python scripts/validate_testing.py --n 300 --seed 5
"""
from __future__ import annotations
import argparse
import math
import os
import random
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app.services.testing.engine import (REGISTRY, load_all, pick_templates, make_item, eap, grade_from_theta, next_level_after_block,  # noqa: E402
                                         decide, GRADES, GRADE_THRESHOLDS)
from app import synth  # noqa: E402

SPEC_BANK = {"backend": True, "frontend": True, "data": True, "qa": True}


def p_correct(theta: float, code: str, rng: random.Random) -> bool:
    t = REGISTRY[code]
    p = 1 / (1 + math.exp(-(theta - t.difficulty)))
    if t.fmt in ("choice", "multichoice"):
        inst = t.generate(random.Random(rng.randrange(1, 10**9)))
        n = len(inst.options or []) or 5
        g = 1 / n if t.fmt == "choice" else 1 / (n * 2)
        p = g + (1 - g) * p
    return rng.random() < p


def run_session(theta: float, spec: str, claimed: str, skills: list[str], rng: random.Random, block_size: int, blocks: int,
                leaked: set[tuple[str, int]] | None = None, parametrized: bool = True):
    """→ (θ-оценка, sd, грейд, решение, список (код, зерно, верно)). leaked — экземпляры (код, зерно), ответы на которые кандидат знает."""
    level = claimed
    used: set[str] = set()
    responses: list[tuple[float, bool]] = []
    items = []
    for b in range(1, blocks + 1):
        codes = pick_templates(spec, level, skills, block_size, rng, exclude=used, has_bank=SPEC_BANK.get(spec, False))
        used |= set(codes)
        correct = 0
        for code in codes:
            seed = 1 if not parametrized else rng.randrange(1, 2**31)      # фиксированный набор = у всех одно зерно
            if leaked is not None and (code, seed) in leaked:
                ok = True
            else:
                ok = p_correct(theta, code, rng)
            correct += int(ok)
            responses.append((REGISTRY[code].difficulty, ok))
            items.append((code, seed, ok))
        out = next_level_after_block(level, correct, len(codes), b, blocks)
        if out.next_level is None:
            break
        level = out.next_level
    th, sd = eap(responses)
    grade, decision = decide(th, sd, claimed)
    return th, sd, grade, decision, items


def auc(pos: list[float], neg: list[float]) -> float:
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--block-size", type=int, default=4)
    ap.add_argument("--blocks", type=int, default=2)
    args = ap.parse_args()
    load_all()
    rng = random.Random(args.seed)
    events = synth.load_events()
    cands = [c for c in synth.make_candidates(args.n, rng, events) if c.specialization in SPEC_BANK]
    print(f"Шаблонов в банке: {len(REGISTRY)}; кандидатов со своим банком: {len(cands)}; блоков {args.blocks} по {args.block_size}\n")

    # 1. соответствие истинному грейду и согласованность (два прохода)
    conf = Counter(); agree = 0; thetas_by_grade = defaultdict(list); est_err = []
    decisions = Counter(); claimed_ok = 0
    for c in cands:
        th1, sd1, g1, d1, _ = run_session(c.theta, c.specialization, c.claimed_grade, c.declared_stack, rng, args.block_size, args.blocks)
        th2, sd2, g2, d2, _ = run_session(c.theta, c.specialization, c.claimed_grade, c.declared_stack, rng, args.block_size, args.blocks)
        measured = grade_from_theta(th1)
        conf[(c.true_grade, measured)] += 1
        agree += int(grade_from_theta(th1) == grade_from_theta(th2))
        thetas_by_grade[c.true_grade].append(th1)
        est_err.append(abs(th1 - c.theta))
        decisions[d1] += 1
        # честность решения: кандидат, завысивший грейд, должен получить suggest_lower; заявивший верно — confirmed
        if GRADES.index(c.claimed_grade) > GRADES.index(c.true_grade):
            claimed_ok += int(d1 == "suggest_lower")
        else:
            claimed_ok += int(d1 in ("confirmed", "suggest_higher"))
    n = len(cands)
    exact = sum(v for (a, b), v in conf.items() if a == b) / n
    adjacent = sum(v for (a, b), v in conf.items() if abs(GRADES.index(a) - GRADES.index(b)) <= 1) / n
    print("Соответствие истинному грейду:")
    print(f"  точно: {exact:.2f}; в пределах соседнего грейда: {adjacent:.2f}; средняя |θ̂ − θ|: {sum(est_err)/n:.2f}")
    print("  матрица (истина → измерено):")
    print("            " + "".join(f"{g:>8}" for g in GRADES))
    for a in GRADES:
        print(f"  {a:>8}  " + "".join(f"{conf[(a, b)]:8d}" for b in GRADES))
    print(f"\nСогласованность (два прохода с разными экземплярами, тот же кандидат): совпадение грейда {agree/n:.2f}")
    print("\nДискриминативность (AUC между соседними истинными грейдами по θ̂):")
    for a, b in zip(GRADES, GRADES[1:]):
        print(f"  {a} vs {b}: {auc(thetas_by_grade[b], thetas_by_grade[a]):.2f}")
    print(f"\nРешения: {dict(decisions)}; доля верных решений о заявленном грейде: {claimed_ok/n:.2f}")

    # 2. устойчивость к утечке: кандидат знает ответы на 40 чужих экземпляров
    print("\nУстойчивость к утечке (слабый кандидат θ = −2,0 знает ответы на 40 экземпляров заданий):")
    leaked_param: set = set(); leaked_fixed: set = set()
    donor = random.Random(777)
    for _ in range(40):
        code = donor.choice(list(REGISTRY))
        leaked_param.add((code, donor.randrange(1, 2**31)))
        leaked_fixed.add((code, 1))
    for label, leak, par in (("без утечки, шаблоны с параметрами", None, True), ("утечка, шаблоны с параметрами", leaked_param, True),
                             ("без утечки, фиксированный набор", None, False), ("утечка, фиксированный набор", leaked_fixed, False)):
        ths = [run_session(-2.0, "backend", "middle", ["python", "sql"], random.Random(1000 + i), args.block_size, args.blocks, leaked=leak, parametrized=par)[0] for i in range(60)]
        print(f"  {label:38} средняя θ̂ = {sum(ths)/len(ths):+.2f}, доля грейда ≥ middle: {sum(grade_from_theta(t) in ('middle','senior','lead') for t in ths)/len(ths):.2f}")

    # 3. корреляция шаблонов с итогом (дискриминативность заданий)
    print("\nШаблоны с самой низкой связью «верно → итоговое θ̂» (точечно-бисериальная корреляция), стоит пересмотреть:")
    per: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for c in cands:
        th, _, _, _, items = run_session(c.theta, c.specialization, c.claimed_grade, c.declared_stack, rng, args.block_size, args.blocks)
        for code, _, ok in items:
            per[code].append((int(ok), th))
    rows = []
    for code, xs in per.items():
        if len(xs) < 12:
            continue
        oks = [o for o, _ in xs]; ths = [t for _, t in xs]
        mo, mt = sum(oks) / len(oks), sum(ths) / len(ths)
        cov = sum((o - mo) * (t - mt) for o, t in xs)
        vo = math.sqrt(sum((o - mo) ** 2 for o in oks)) * math.sqrt(sum((t - mt) ** 2 for t in ths))
        rows.append((cov / vo if vo else 0.0, code, len(xs), mo))
    rows.sort()
    for r, code, k, mo in rows[:6]:
        print(f"  {code:40} r = {r:+.2f}, предъявлений {k}, доля верных {mo:.2f}")
    print(f"  средняя корреляция по {len(rows)} шаблонам: {sum(r for r, *_ in rows)/len(rows):+.2f}")


if __name__ == "__main__":
    main()
