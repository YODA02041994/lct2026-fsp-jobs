"""Проверки черновиков банка, предложенных моделью (пакет app.services.testing.bank.generated).

Пакет импортируется напрямую, минуя load_all(): пока в load_all() нет строки `from . import generated`, черновики
кандидатам не выдаются, но проверяются так же строго, как основной банк (backend/tests/test_bank.py):
  (а) метаданные: код вида gen_<специализация>_… и равен имени файла, формат и грейд из допустимых, технологии только
      из каталога, специализация указана и одна;
  (б) 30 зёрен → экземпляры без исключений и с корректной структурой;
  (в) не меньше 5 разных экземпляров на 30 зёрнах, одно зерно — один экземпляр;
  (г) exact с кодом на Python: ответ равен stdout независимого исполнения показанного кода;
  (д) в ключах exact нет контейнеров и плавающих чисел; вопрос и пояснение — на русском, без незаполненных «{имя}».
Если в папке generated нет шаблонов, проверки пропускаются.
Запуск: cd backend && ../.venv/bin/python -m pytest -q tests/test_generated_bank.py
"""
from __future__ import annotations
import contextlib
import io
import random
import re

import pytest

from app.services.skills_catalog import CODES
from app.services.testing.bank import load_all, check_answer
from app.services.testing.bank.base import FORMATS, GRADE_DIFFICULTY, REGISTRY, Instance, normalize_exact

load_all()
import app.services.testing.bank.generated as generated  # noqa: E402  (с 07.10 пакет подключён и в load_all)

GEN_PREFIX = generated.__name__ + "."
_BASE_CODES = {code for code, s in REGISTRY.items() if not s.generate.__module__.startswith(GEN_PREFIX)}   # рукописные модули
SPECS = sorted((s for s in REGISTRY.values() if s.generate.__module__.startswith(GEN_PREFIX)), key=lambda s: s.code)
SEEDS = list(range(1, 31))
CYRILLIC = re.compile(r"[а-яА-ЯёЁ]")
PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")      # «{name}» в тексте — забытая f-строка

pytestmark = pytest.mark.skipif(not SPECS, reason="в папке generated нет шаблонов")


def module_of(spec) -> str:
    return spec.generate.__module__.rsplit(".", 1)[-1]


def generate(spec, seed: int) -> Instance:
    return spec.generate(random.Random(seed))


def signature(inst: Instance) -> tuple:
    return (inst.question, inst.code, tuple(inst.options or ()), str(inst.answer))


def run_python(code: str) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(code, {"__name__": "__bank_test__"})
    return buf.getvalue().strip()


# ------------------------------------------------------------------------------------------
# (а) метаданные
# ------------------------------------------------------------------------------------------

def test_generated_are_new_codes():
    for spec in SPECS:
        assert spec.code not in _BASE_CODES, f"{spec.code}: совпадает с кодом основного банка"
    assert sorted(generated.MODULES) == sorted(module_of(s) for s in SPECS), "каждый модуль папки регистрирует ровно один шаблон"


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.code)
def test_spec_metadata(spec):
    assert spec.code.isascii() and spec.code.islower() and re.fullmatch(r"[a-z0-9_]+", spec.code), spec.code
    assert spec.code == module_of(spec), f"код {spec.code} должен совпадать с именем файла {module_of(spec)}.py"
    assert len(spec.specializations) == 1, "черновик привязан ровно к одной специализации"
    assert spec.code.startswith(f"gen_{spec.specializations[0]}_"), f"код {spec.code} должен начинаться с gen_<специализация>_"
    assert spec.fmt in FORMATS
    assert spec.grade_level in GRADE_DIFFICULTY
    assert abs(spec.difficulty_shift) <= 0.4
    assert 1 <= len(spec.technologies) <= 3, spec.technologies
    unknown = set(spec.technologies) - CODES
    assert not unknown, f"технологии вне каталога: {unknown}"
    assert spec.title.strip() and spec.competency.strip()
    assert CYRILLIC.search(spec.title) and CYRILLIC.search(spec.competency), "название и компетенция — на русском"


# ------------------------------------------------------------------------------------------
# (б) генерация и структура, (в) уникальность и детерминизм
# ------------------------------------------------------------------------------------------

def _check_instance(spec, inst: Instance) -> None:
    assert isinstance(inst, Instance)
    assert inst.question.strip(), "пустой вопрос"
    assert CYRILLIC.search(inst.question), "вопрос на русском"
    if inst.code is not None:
        assert inst.language in {"python", "javascript", "sql", "text", "html", "css"}, inst.language
        assert inst.code.strip()
    assert inst.explanation.strip(), "нужно объяснение"
    assert CYRILLIC.search(inst.explanation), "пояснение на русском"
    for text in (inst.question, inst.explanation, *(inst.options or [])):
        assert not PLACEHOLDER.search(text), f"незаполненная подстановка (забыта f-строка): {text[:120]!r}"
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
# (г) ключ exact совпадает с настоящим выводом кода на Python, (д) ответы exact — скаляры
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
    first = generate(spec, SEEDS[0])
    assert (first.language != "python") or checked == len(SEEDS)


@pytest.mark.parametrize("spec", EXACT_SPECS, ids=lambda s: s.code)
def test_exact_answers_are_scalar_like(spec):
    for seed in SEEDS[:10]:
        ans = generate(spec, seed).answer
        assert not ans.startswith(("[", "{", "(")), f"{spec.code}: ответ похож на контейнер: {ans!r}"
        assert "." not in ans or not ans.replace(".", "", 1).isdigit(), f"{spec.code}: плавающее число в ответе: {ans!r}"
