"""Проверки банка параметризованных заданий (docs/08).

Что проверяется:
  (а) реестр: не меньше 70 шаблонов, формат из FORMATS, грейд из GRADE_DIFFICULTY, технологии только из каталога;
  (б) каждый шаблон на 30 зёрнах генерирует экземпляры без исключений и с корректной структурой;
  (в) среди 30 зёрен не меньше 5 разных экземпляров (защита от утечки: содержимое, а не только порядок вариантов);
  (г) exact-шаблоны с кодом на Python: ответ равен stdout исполнения показанного кода (считается здесь независимо
      от помощников банка, чтобы ошибка помощника не подтверждала сама себя);
  (д) распределение по модулям, грейдам и форматам соответствует требованиям к банку.
Запуск: cd backend && ../.venv/bin/python -m pytest -q tests/test_bank.py
"""
from __future__ import annotations
import contextlib
import io
import random
from collections import Counter

import pytest

from app.services.skills_catalog import CODES
from app.services.testing.bank import load_all, check_answer
from app.services.testing.bank.base import FORMATS, GRADE_DIFFICULTY, Instance, normalize_exact

REGISTRY = load_all()
SPECS = sorted(REGISTRY.values(), key=lambda s: s.code)
SEEDS = list(range(1, 31))

MIN_TOTAL = 70
MIN_PER_MODULE = {"common": 22, "backend": 16, "frontend": 14, "data": 12, "qa": 10}
EXACT_HALF_MODULES = {"backend", "frontend", "data"}
JUNIOR_MIDDLE_SHARE = 0.6


def module_of(spec) -> str:
    return spec.generate.__module__.rsplit(".", 1)[-1]


def generate(spec, seed: int) -> Instance:
    return spec.generate(random.Random(seed))


def signature(inst: Instance) -> tuple:
    """Содержательный отпечаток экземпляра: вопрос, код, варианты в итоговом порядке и ответ."""
    return (inst.question, inst.code, tuple(inst.options or ()), str(inst.answer))


def run_python(code: str) -> str:
    """Независимое исполнение фрагмента: изолированный словарь, перехват stdout."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(code, {"__name__": "__bank_test__"})
    return buf.getvalue().strip()


# ------------------------------------------------------------------------------------------
# (а) реестр
# ------------------------------------------------------------------------------------------

def test_registry_size():
    assert len(REGISTRY) >= MIN_TOTAL, f"в банке {len(REGISTRY)} шаблонов, нужно не меньше {MIN_TOTAL}"


def test_codes_unique_and_latin():
    for spec in SPECS:
        assert REGISTRY[spec.code] is spec, spec.code
        assert spec.code.isascii() and spec.code.islower(), f"код шаблона должен быть латиницей в нижнем регистре: {spec.code}"
        assert spec.code.startswith(module_of(spec) + "_"), f"код {spec.code} должен начинаться с имени модуля"


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.code)
def test_spec_metadata(spec):
    assert spec.fmt in FORMATS
    assert spec.grade_level in GRADE_DIFFICULTY
    assert abs(spec.difficulty_shift) <= 0.4
    assert 1 <= len(spec.technologies) <= 3, spec.technologies
    unknown = set(spec.technologies) - CODES
    assert not unknown, f"технологии вне каталога: {unknown}"
    assert spec.title and spec.competency
    assert module_of(spec) in MIN_PER_MODULE
    if module_of(spec) == "common":
        assert spec.specializations == [], "общий шаблон должен иметь пустой список специализаций"
    else:
        assert spec.specializations, "шаблон специализации должен указывать специализации"


# ------------------------------------------------------------------------------------------
# (б) генерация и структура экземпляров, (в) уникальность
# ------------------------------------------------------------------------------------------

def _check_instance(spec, inst: Instance) -> None:
    assert isinstance(inst, Instance)
    assert inst.question.strip(), "пустой вопрос"
    if inst.code is not None:
        assert inst.language in {"python", "javascript", "sql", "text", "html", "css"}, inst.language
        assert inst.code.strip()
    assert inst.explanation.strip(), "нужно объяснение"
    if spec.fmt == "exact":
        assert isinstance(inst.answer, str) and inst.answer.strip(), "ответ exact — непустая строка"
        assert inst.options is None
        assert check_answer("exact", inst.answer, inst.answer)
    elif spec.fmt == "choice":
        assert inst.options and len(inst.options) >= 5, "choice: не меньше 5 вариантов"
        assert len(set(inst.options)) == len(inst.options), "варианты должны быть уникальны"
        assert isinstance(inst.answer, int) and 0 <= inst.answer < len(inst.options)
        assert check_answer("choice", inst.answer, inst.answer)
    else:
        assert inst.options and 5 <= len(inst.options) <= 6, "multichoice: 5–6 вариантов"
        assert len(set(inst.options)) == len(inst.options), "варианты должны быть уникальны"
        assert isinstance(inst.answer, list) and 2 <= len(inst.answer) <= 3, "multichoice: 2–3 правильных"
        assert len(set(inst.answer)) == len(inst.answer)
        assert all(isinstance(i, int) and 0 <= i < len(inst.options) for i in inst.answer)
        assert check_answer("multichoice", inst.answer, list(reversed(inst.answer)))


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.code)
def test_instances_generate_and_vary(spec):
    seen = set()
    for seed in SEEDS:
        inst = generate(spec, seed)
        _check_instance(spec, inst)
        seen.add(signature(inst))
    assert len(seen) >= 5, f"{spec.code}: всего {len(seen)} разных экземпляров на 30 зёрнах"


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.code)
def test_deterministic_by_seed(spec):
    for seed in SEEDS[:5]:
        assert signature(generate(spec, seed)) == signature(generate(spec, seed)), "одно зерно — один экземпляр"


# ------------------------------------------------------------------------------------------
# (г) ключ exact-заданий с кодом на Python совпадает с настоящим выводом
# ------------------------------------------------------------------------------------------

EXACT_SPECS = [s for s in SPECS if s.fmt == "exact"]


@pytest.mark.parametrize("spec", EXACT_SPECS, ids=lambda s: s.code)
def test_exact_python_answer_matches_execution(spec):
    checked = 0
    for seed in SEEDS:
        inst = generate(spec, seed)
        if inst.language != "python":
            continue
        out = run_python(inst.code)
        assert out, f"{spec.code}: код на Python в exact-задании обязан печатать ответ"
        assert normalize_exact(out) == normalize_exact(inst.answer), f"{spec.code} seed={seed}: вывод {out!r}, ключ {inst.answer!r}"
        checked += 1
    # либо шаблон вовсе не про Python, либо проверены все его экземпляры
    first = generate(spec, SEEDS[0])
    assert (first.language != "python") or checked == len(SEEDS)


def test_exact_answers_are_scalar_like():
    """В ключах exact нет представлений списков/словарей и плавающих чисел — их тяжело ввести однозначно."""
    for spec in EXACT_SPECS:
        for seed in SEEDS[:10]:
            ans = generate(spec, seed).answer
            assert not ans.startswith(("[", "{", "(")), f"{spec.code}: ответ похож на контейнер: {ans!r}"
            assert "." not in ans or not ans.replace(".", "", 1).isdigit(), f"{spec.code}: плавающее число в ответе: {ans!r}"


# ------------------------------------------------------------------------------------------
# (д) распределение по модулям, грейдам и форматам
# ------------------------------------------------------------------------------------------

def test_module_minimums():
    counts = Counter(module_of(s) for s in SPECS)
    for module, minimum in MIN_PER_MODULE.items():
        assert counts[module] >= minimum, f"{module}: {counts[module]} шаблонов, нужно не меньше {minimum}"


@pytest.mark.parametrize("module", sorted(MIN_PER_MODULE))
def test_grades_per_module(module):
    specs = [s for s in SPECS if module_of(s) == module]
    grades = Counter(s.grade_level for s in specs)
    for grade in GRADE_DIFFICULTY:
        assert grades[grade] >= 1, f"{module}: нет шаблонов грейда {grade}"
    share = (grades["junior"] + grades["middle"]) / len(specs)
    assert share >= JUNIOR_MIDDLE_SHARE, f"{module}: junior+middle = {share:.0%}, нужно не меньше {JUNIOR_MIDDLE_SHARE:.0%}"


@pytest.mark.parametrize("module", sorted(EXACT_HALF_MODULES))
def test_exact_share(module):
    specs = [s for s in SPECS if module_of(s) == module]
    exact = sum(1 for s in specs if s.fmt == "exact")
    assert exact * 2 >= len(specs), f"{module}: exact {exact} из {len(specs)}, нужно не меньше половины"


def test_formats_present():
    fmts = Counter(s.fmt for s in SPECS)
    assert all(fmts[f] > 0 for f in FORMATS), fmts
