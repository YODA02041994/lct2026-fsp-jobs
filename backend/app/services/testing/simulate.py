"""Симуляция прохождения теста синтетическим кандидатом — тем же движком, что в бою (подбор шаблонов, блоки, EAP, решение).

Используется в трёх местах, чтобы они не расходились: валидация теста (scripts/validate_testing.py), демонстрационные данные
(app/seed.py) и миры для оценки подбора (scripts/evolve/features.py).

Модель ответа: P(верно) = g + (1 − g)·σ(θ − b + поправка), g — вероятность угадывания (engine.guess_rate), та же, что в оценке θ. Поправка KNOWLEDGE_GAP вычитается, если
задание проверяет технологию, которую кандидат заявил, но на самом деле не знает (её нет в истинном стеке, а других технологий
задания он тоже не знает). Это допущение симуляции: в реальности такой разрыв оценивается по накопленным ответам.
"""
from __future__ import annotations
import math
import random

from .bank import REGISTRY
from .engine import pick_templates, eap, decide, next_level_after_block, technology_summary, guess_rate

KNOWLEDGE_GAP = 1.5      # логитов: насколько хуже кандидат решает задание по технологии, которую приписал себе


def item_guess(code: str, rng: random.Random) -> float:
    t = REGISTRY[code]
    if t.fmt in ("choice", "multichoice"):
        inst = t.generate(random.Random(rng.randrange(1, 10**9)))
        return guess_rate(t.fmt, len(inst.options or []) or 5)
    return 0.0


def p_correct(theta: float, code: str, rng: random.Random, true_stack: set[str] | None = None, declared: set[str] | None = None,
              g: float | None = None) -> bool:
    t = REGISTRY[code]
    shift = 0.0
    if true_stack is not None and declared is not None:
        techs = set(t.technologies)
        if techs & declared and not techs & true_stack:
            shift = -KNOWLEDGE_GAP
    p = 1 / (1 + math.exp(-(theta + shift - t.difficulty)))
    g = item_guess(code, rng) if g is None else g
    p = g + (1 - g) * p
    return rng.random() < p


def run_session(theta: float, spec: str, claimed: str, declared: list[str], rng: random.Random, block_size: int, blocks: int,
                has_bank: bool = True, true_stack: list[str] | None = None, leaked: set[tuple[str, int]] | None = None,
                parametrized: bool = True) -> dict:
    """→ {theta, sd, grade, decision, items: [(код, зерно, верно)], tech: {технология: (верно, всего)}}."""
    level = claimed
    used: set[str] = set()
    responses: list[tuple[float, bool]] = []
    items = []
    ts = set(true_stack) if true_stack is not None else None
    ds = set(declared) if true_stack is not None else None
    for b in range(1, blocks + 1):
        codes = pick_templates(spec, level, declared, block_size, rng, exclude=used, has_bank=has_bank)
        used |= set(codes)
        correct = 0
        for code in codes:
            seed = 1 if not parametrized else rng.randrange(1, 2**31)      # фиксированный набор = у всех одно зерно
            g = item_guess(code, rng)
            ok = True if leaked is not None and (code, seed) in leaked else p_correct(theta, code, rng, ts, ds, g=g)
            correct += int(ok)
            responses.append((REGISTRY[code].difficulty, ok, g))
            items.append((code, seed, ok))
        out = next_level_after_block(level, correct, len(codes), b, blocks)
        if out.next_level is None:
            break
        level = out.next_level
    th, sd = eap(responses)
    grade, decision = decide(th, sd, claimed)
    tech = {row["skill"]: (row["correct"], row["total"]) for row in technology_summary([(c, ok) for c, _, ok in items])}
    return {"theta": th, "sd": sd, "grade": grade, "decision": decision, "items": items, "tech": tech}
