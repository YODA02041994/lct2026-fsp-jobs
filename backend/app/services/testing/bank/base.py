"""Интерфейс шаблона задания (docs/08).

Шаблон = компетенция + технологии + формат + сложность + генератор. Генератор получает random.Random с зерном
и возвращает Instance: текст вопроса, код, варианты и правильный ответ. Все экземпляры одного шаблона
считаются равными по сложности — это основа сопоставимости между кандидатами.
"""
from __future__ import annotations
import random
import re
from dataclasses import dataclass, field
from typing import Callable

GRADE_DIFFICULTY = {"junior": -1.5, "middle": -0.5, "senior": 0.5, "lead": 1.5}
FORMATS = ("exact", "choice", "multichoice")


@dataclass
class Instance:
    question: str                       # формулировка (можно с переносами строк)
    answer: str | int | list[int]       # exact: строка; choice: индекс варианта; multichoice: список индексов
    code: str | None = None             # фрагмент кода или данных
    language: str | None = None         # python / javascript / sql / text
    options: list[str] | None = None    # варианты для choice / multichoice (уже в итоговом порядке)
    explanation: str = ""               # короткое пояснение (кандидату не показывается до конца теста)


@dataclass
class TemplateSpec:
    code: str
    title: str
    competency: str
    specializations: list[str]          # [] — общий шаблон для всех специализаций
    technologies: list[str]
    fmt: str
    grade_level: str
    generate: Callable[[random.Random], Instance]
    difficulty_shift: float = 0.0       # поправка к сложности грейда, в пределах ±0.4

    @property
    def difficulty(self) -> float:
        return GRADE_DIFFICULTY[self.grade_level] + self.difficulty_shift


REGISTRY: dict[str, TemplateSpec] = {}


def template(code: str, *, title: str, competency: str, specializations: list[str], technologies: list[str],
             fmt: str, grade_level: str, difficulty_shift: float = 0.0):
    """Декоратор регистрации генератора."""
    assert fmt in FORMATS, fmt
    assert grade_level in GRADE_DIFFICULTY, grade_level
    assert abs(difficulty_shift) <= 0.4

    def deco(fn: Callable[[random.Random], Instance]):
        if code in REGISTRY:
            raise ValueError(f"повтор кода шаблона {code}")
        REGISTRY[code] = TemplateSpec(code, title, competency, specializations, technologies, fmt, grade_level, fn, difficulty_shift)
        return fn
    return deco


def shuffle_options(rng: random.Random, options: list[str], correct: int | list[int]) -> tuple[list[str], int | list[int]]:
    """Перемешать варианты и пересчитать индекс(ы) правильного ответа."""
    idx = list(range(len(options)))
    rng.shuffle(idx)
    new_options = [options[i] for i in idx]
    pos = {old: new for new, old in enumerate(idx)}
    if isinstance(correct, list):
        return new_options, sorted(pos[c] for c in correct)
    return new_options, pos[correct]


def normalize_exact(s: str) -> str:
    s = str(s).strip().lower().replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    s = s.replace("'", '"')
    return s


def check_answer(fmt: str, key, given) -> bool:
    if fmt == "exact":
        return normalize_exact(key) == normalize_exact(given)
    if fmt == "choice":
        try:
            return int(key) == int(given)
        except (TypeError, ValueError):
            return False
    if fmt == "multichoice":
        try:
            return sorted(int(x) for x in key) == sorted(int(x) for x in given)
        except (TypeError, ValueError):
            return False
    return False


def instance_to_payload(spec: TemplateSpec, inst: Instance) -> tuple[dict, dict]:
    """Разделить экземпляр на то, что видит кандидат, и ключ ответа."""
    payload = {
        "template": spec.code, "title": spec.title, "competency": spec.competency,
        "technologies": spec.technologies, "format": spec.fmt,
        "question": inst.question, "code": inst.code, "language": inst.language, "options": inst.options,
    }
    key = {"answer": inst.answer, "explanation": inst.explanation}
    return payload, key
