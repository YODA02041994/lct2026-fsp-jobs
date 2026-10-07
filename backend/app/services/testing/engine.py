"""Движок теста: подбор шаблонов по уровню и стеку, адаптивные блоки, оценка умения θ (EAP), грейд и решение.

Модель ответа — Раш: P(верно) = σ(θ − b). Оценка θ — байесовское среднее по сетке с априорным N(0, 1):
устойчива при всех верных или всех неверных ответах и даёт стандартное отклонение (уверенность).
Шкала грейдов — docs/08, раздел «Шкала сложности и грейда».
"""
from __future__ import annotations
import math
import random
from dataclasses import dataclass
from .bank import REGISTRY, load_all, instance_to_payload, check_answer, GRADE_DIFFICULTY

GRADES = ["junior", "middle", "senior", "lead"]
GRADE_THRESHOLDS = {"junior": -2.0, "middle": -1.0, "senior": 0.0, "lead": 1.0}   # θ не ниже порога → грейд
_GRID = [(-4 + 8 * i / 160) for i in range(161)]


def grade_from_theta(theta: float) -> str:
    result = "junior"
    for g in GRADES:
        if theta >= GRADE_THRESHOLDS[g]:
            result = g
    return result


# Априор умения — распределение θ в популяции кандидатов (эмпирический Байес, стандартная практика IRT).
# На старте выводится из долей заявленных грейдов и центров шкалы сложности (docs/08, раздел 3), затем переоценивается
# по накопленным θ̂. Значение задаётся настройками FSP_TEST_PRIOR_MEAN / FSP_TEST_PRIOR_SD.
from ...config import get_settings as _gs  # noqa: E402
PRIOR = {"mean": _gs().test_prior_mean, "sd": _gs().test_prior_sd}


def guess_rate(fmt: str, n_options: int | None) -> float:
    """Вероятность угадать ответ, не зная его: выбор одного из n — 1/n; несколько из n — 1/(2n); точный ответ — 0.
    Используется и в оценке θ (модель ответа с угадыванием), и в симуляции кандидатов — чтобы они не расходились."""
    n = max(int(n_options or 0), 2)
    if fmt == "choice":
        return 1.0 / n
    if fmt == "multichoice":
        return 1.0 / (2 * n)
    return 0.0


def eap(responses: list[tuple], prior_sd: float | None = None, prior_mean: float | None = None) -> tuple[float, float]:
    """responses: [(сложность b, верно ли[, вероятность угадывания g])] → (θ, стандартное отклонение).
    Модель ответа: P(верно) = g + (1 − g)·σ(θ − b); без g — Раш. Априор — нормальный, по умолчанию PRIOR."""
    mu = PRIOR["mean"] if prior_mean is None else prior_mean
    sd0 = PRIOR["sd"] if prior_sd is None else prior_sd
    if not responses:
        return mu, sd0
    weights = []
    for t in _GRID:
        logp = -0.5 * ((t - mu) / sd0) ** 2
        for r in responses:
            b, ok = r[0], r[1]
            g = r[2] if len(r) > 2 else 0.0
            p = g + (1.0 - g) / (1.0 + math.exp(-(t - b)))
            p = min(max(p, 1e-9), 1 - 1e-9)
            logp += math.log(p) if ok else math.log(1 - p)
        weights.append(logp)
    m = max(weights)
    w = [math.exp(x - m) for x in weights]
    z = sum(w)
    mean = sum(t * wi for t, wi in zip(_GRID, w)) / z
    var = sum((t - mean) ** 2 * wi for t, wi in zip(_GRID, w)) / z
    return mean, math.sqrt(var)


def level_up(level: str) -> str:
    i = GRADES.index(level)
    return GRADES[min(i + 1, len(GRADES) - 1)]


def level_down(level: str) -> str:
    i = GRADES.index(level)
    return GRADES[max(i - 1, 0)]


def pick_templates(specialization: str, level: str, declared_skills: list[str], n: int, rng: random.Random,
                   exclude: set[str] = frozenset(), has_bank: bool = True) -> list[str]:
    """Выбрать n шаблонов уровня level: сначала покрывающие заявленные технологии, затем общие.

    Приоритет: шаблоны специализации с заявленными технологиями → шаблоны специализации → общие с заявленными
    технологиями → общие. Внутри группы — случайно. Соседний уровень берётся, если своего не хватило.
    """
    load_all()
    declared = set(declared_skills or [])

    def candidates(lvl: str) -> list[list[str]]:
        groups = [[], [], [], []]
        for code, t in REGISTRY.items():
            if code in exclude or t.grade_level != lvl or not getattr(t, "status_ok", True):
                continue
            spec_match = has_bank and specialization in t.specializations
            common = not t.specializations
            if not (spec_match or common):
                continue
            tech = bool(declared & set(t.technologies))
            if spec_match and tech:
                groups[0].append(code)
            elif spec_match:
                groups[1].append(code)
            elif tech:
                groups[2].append(code)
            else:
                groups[3].append(code)
        return groups

    chosen: list[str] = []
    for lvl in [level, level_down(level), level_up(level)]:
        for g in candidates(lvl):
            rng.shuffle(g)
            for code in g:
                if len(chosen) >= n:
                    return chosen
                if code not in chosen:
                    chosen.append(code)
    return chosen


def make_item(template_code: str, seed: int) -> tuple[dict, dict]:
    spec = REGISTRY[template_code]
    inst = spec.generate(random.Random(seed))
    return instance_to_payload(spec, inst)


def grade_item(template_code: str, key: dict, answer) -> bool:
    spec = REGISTRY[template_code]
    return check_answer(spec.fmt, key["answer"], answer)


@dataclass
class BlockOutcome:
    correct: int
    total: int
    next_level: str | None   # None — тест окончен


def next_level_after_block(level: str, correct: int, total: int, block_no: int, blocks_total: int) -> BlockOutcome:
    if block_no >= blocks_total:
        return BlockOutcome(correct, total, None)
    share = correct / total if total else 0
    if share >= 0.75:
        nxt = level_up(level)
    elif share <= 0.4:
        nxt = level_down(level)
    else:
        nxt = level
    return BlockOutcome(correct, total, nxt)


def decide(theta: float, sd: float, claimed: str) -> tuple[str, str]:
    """→ (грейд по θ, решение). Грейд принудительно не понижается: при провале — предложение пройти уровень ниже."""
    measured = grade_from_theta(theta)
    ci = GRADES.index(claimed)
    mi = GRADES.index(measured)
    if mi > ci and theta - sd >= GRADE_THRESHOLDS[GRADES[ci + 1]]:
        return GRADES[ci + 1], "suggest_higher"      # за один тест категория повышается не более чем на грейд; θ показывается отдельно
    if mi < ci:
        return measured, "suggest_lower"
    # θ̂ в зоне заявленного грейда или выше, но без уверенного запаса — подтверждается заявленный (docs/08, раздел 4);
    # раньше здесь возвращался измеренный грейд, и кандидата молча повышали без уверенности
    return claimed, "confirmed"


def technology_summary(items: list[tuple[str, bool | None]]) -> list[dict]:
    """Доля верных ответов по технологиям: [(template_code, correct)] → [{skill, correct, total}]."""
    acc: dict[str, list[int]] = {}
    for code, ok in items:
        if ok is None:
            continue
        for tech in REGISTRY[code].technologies:
            a = acc.setdefault(tech, [0, 0])
            a[1] += 1
            a[0] += int(ok)
    return [{"skill": k, "correct": v[0], "total": v[1]} for k, v in sorted(acc.items())]
