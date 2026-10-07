#!/usr/bin/env python3
"""Проверка одного кандидата шаблона в ОТДЕЛЬНОМ процессе (его запускает propose_templates.py с лимитом времени).

Запуск из папки backend (чтобы пакет app был импортируем):
    python ../scripts/evolve/validate_candidate.py check <модуль в generated> <json-файл с ожиданиями>
    python ../scripts/evolve/validate_candidate.py list

Режим check печатает одну строку JSON: {"ok": bool, "errors": [...], "code": str|None, "info": {...}}.
Режим list печатает JSON со всеми уже принятыми шаблонами папки generated (для подсчёта пробелов).

Проверки повторяют backend/tests/test_bank.py: регистрация ровно одного шаблона, метаданные (формат, грейд, технологии
из каталога, специализация), 30 зёрен без исключений и с корректной структурой экземпляра, не меньше 5 разных
экземпляров и не меньше 3 различающихся по содержанию (не только порядком вариантов), детерминизм по зерну,
русский язык вопроса и пояснения, для exact с кодом на Python — независимое исполнение кода даёт ровно ключ,
для exact с кодом на JavaScript — исполнение в node (если он установлен) даёт ровно ключ.
"""
from __future__ import annotations
import contextlib
import importlib
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import traceback

sys.path.insert(0, os.getcwd())

SEEDS = list(range(1, 31))
LANGUAGES = {"python", "javascript", "sql", "text", "html", "css"}
CYRILLIC = re.compile(r"[а-яА-ЯёЁ]")
PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")      # «{name}» в тексте — забытая f-строка
PKG = "app.services.testing.bank.generated"


def _run_python(code: str) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(code, {"__name__": "__bank_validate__"})
    return buf.getvalue().strip()


def _run_node(code: str) -> str | None:
    node = shutil.which("node")
    if not node:
        return None
    r = subprocess.run([node, "-e", code], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "node завершился с ошибкой")
    return r.stdout.strip()


def _signature(inst) -> tuple:
    return (inst.question, inst.code, tuple(inst.options or ()), str(inst.answer))


def _content_signature(inst) -> tuple:
    """Отпечаток без учёта порядка вариантов: что именно спрашивают и что считается верным."""
    if inst.options is None:
        return (inst.question, inst.code, str(inst.answer))
    if isinstance(inst.answer, list):
        correct = tuple(sorted(inst.options[i] for i in inst.answer))
    else:
        correct = (inst.options[inst.answer],)
    return (inst.question, inst.code, tuple(sorted(inst.options)), correct)


def _check_instance(fmt: str, inst, Instance, check_answer) -> list[str]:
    errs: list[str] = []
    if not isinstance(inst, Instance):
        return [f"генератор вернул {type(inst).__name__}, а не Instance"]
    if not (isinstance(inst.question, str) and inst.question.strip()):
        errs.append("пустой вопрос")
    elif not CYRILLIC.search(inst.question):
        errs.append("вопрос должен быть на русском языке")
    if inst.code is not None:
        if inst.language not in LANGUAGES:
            errs.append(f"language={inst.language!r}, допустимы только {sorted(LANGUAGES)} (для Kotlin/Swift/YAML/команд — 'text')")
        if not (isinstance(inst.code, str) and inst.code.strip()):
            errs.append("поле code задано, но пустое")
    if not (isinstance(inst.explanation, str) and inst.explanation.strip()):
        errs.append("нужно непустое пояснение explanation")
    elif not CYRILLIC.search(inst.explanation):
        errs.append("пояснение должно быть на русском языке")
    if fmt == "exact":
        if not (isinstance(inst.answer, str) and inst.answer.strip()):
            errs.append(f"ответ exact должен быть непустой строкой, получено {inst.answer!r} ({type(inst.answer).__name__}) — оберните в str()")
        else:
            if inst.answer.startswith(("[", "{", "(")):
                errs.append(f"ответ exact похож на контейнер: {inst.answer!r}")
            if "." in inst.answer and inst.answer.replace(".", "", 1).replace("-", "", 1).isdigit():
                errs.append(f"плавающее число в ответе exact: {inst.answer!r}")
        if inst.options is not None:
            errs.append("у exact-задания options должны быть None")
    elif fmt == "choice":
        if not inst.options or len(inst.options) < 5:
            errs.append("choice: не меньше 5 вариантов")
        elif len(set(inst.options)) != len(inst.options):
            errs.append("варианты должны быть уникальны")
        if not (isinstance(inst.answer, int) and not isinstance(inst.answer, bool)):
            errs.append(f"choice: ответ — индекс варианта (int), получено {inst.answer!r}")
        elif inst.options and not (0 <= inst.answer < len(inst.options)):
            errs.append(f"choice: индекс ответа {inst.answer} вне пределов")
    else:
        if not inst.options or not (5 <= len(inst.options) <= 6):
            errs.append("multichoice: 5–6 вариантов")
        elif len(set(inst.options)) != len(inst.options):
            errs.append("варианты должны быть уникальны")
        if not (isinstance(inst.answer, list) and 2 <= len(inst.answer) <= 3):
            errs.append(f"multichoice: 2–3 правильных индекса списком, получено {inst.answer!r}")
        elif len(set(inst.answer)) != len(inst.answer):
            errs.append("multichoice: индексы ответа повторяются")
        elif inst.options and not all(isinstance(i, int) and 0 <= i < len(inst.options) for i in inst.answer):
            errs.append("multichoice: индекс ответа вне пределов")
    if not errs and inst.options is not None:
        for o in inst.options:
            if not (isinstance(o, str) and o.strip()):
                errs.append("все варианты — непустые строки")
                break
    if not errs:
        if not check_answer(fmt, inst.answer, inst.answer):
            errs.append("check_answer не принимает собственный ключ")
    for label, text in (("вопрос", inst.question), ("пояснение", inst.explanation), *(("вариант", o) for o in (inst.options or []))):
        m = PLACEHOLDER.search(text or "")
        if m:
            errs.append(f"{label} содержит незаполненную подстановку {m.group(0)} — забыта f-строка")
            break
    return errs


def check(mod_name: str, expect: dict) -> dict:
    errors: list[str] = []
    info: dict = {}
    from app.services.skills_catalog import CODES
    from app.services.testing.bank import load_all
    from app.services.testing.bank.base import REGISTRY, FORMATS, GRADE_DIFFICULTY, Instance, check_answer, normalize_exact

    load_all()
    importlib.import_module(PKG)              # уже принятые шаблоны
    before = set(REGISTRY)
    try:
        importlib.import_module(f"{PKG}.{mod_name}")
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc().strip().splitlines()
        return {"ok": False, "errors": ["импорт: " + " | ".join(tb[-3:])], "code": None, "info": info}
    new = sorted(set(REGISTRY) - before)
    if len(new) != 1:
        return {"ok": False, "errors": [f"регистрация: ожидался ровно один новый шаблон, зарегистрировано {len(new)}: {new}"],
                "code": None, "info": info}
    code = new[0]
    spec = REGISTRY[code]
    info["code"] = code
    info["title"] = spec.title
    info["competency"] = spec.competency
    if not spec.generate.__module__.endswith("." + mod_name):
        errors.append(f"регистрация: генератор {code} объявлен не в файле кандидата ({spec.generate.__module__})")

    # --- метаданные
    prefix = f"gen_{expect['spec']}_"
    if not (code.isascii() and code.islower() and re.fullmatch(r"[a-z0-9_]+", code) and code.startswith(prefix) and len(code) > len(prefix)):
        errors.append(f"метаданные: код шаблона должен быть вида {prefix}<тема латиницей в нижнем регистре>, получено {code!r}")
    if code in expect.get("occupied", []):
        errors.append(f"метаданные: код {code!r} уже занят, выберите другой")
    if spec.fmt not in FORMATS:
        errors.append(f"метаданные: формат {spec.fmt!r} вне {FORMATS}")
    elif spec.fmt != expect["fmt"]:
        errors.append(f"метаданные: формат должен быть {expect['fmt']!r}, получено {spec.fmt!r}")
    if spec.grade_level not in GRADE_DIFFICULTY:
        errors.append(f"метаданные: грейд {spec.grade_level!r} вне {sorted(GRADE_DIFFICULTY)}")
    elif spec.grade_level != expect["grade"]:
        errors.append(f"метаданные: грейд должен быть {expect['grade']!r}, получено {spec.grade_level!r}")
    if not (1 <= len(spec.technologies) <= 3):
        errors.append(f"метаданные: технологий должно быть 1–3, получено {spec.technologies}")
    unknown = set(spec.technologies) - set(CODES)
    if unknown:
        errors.append(f"метаданные: технологии вне каталога: {sorted(unknown)}")
    if set(spec.technologies) != set(expect["techs"]):
        errors.append(f"метаданные: технологии должны быть ровно {expect['techs']}, получено {spec.technologies}")
    if list(spec.specializations) != [expect["spec"]]:
        errors.append(f"метаданные: specializations должны быть {[expect['spec']]}, получено {spec.specializations}")
    if abs(spec.difficulty_shift) > 0.4:
        errors.append(f"метаданные: |difficulty_shift| ≤ 0.4, получено {spec.difficulty_shift}")
    if not (spec.title and spec.title.strip()) or not (spec.competency and spec.competency.strip()):
        errors.append("метаданные: title и competency обязательны")
    elif not (CYRILLIC.search(spec.title) and CYRILLIC.search(spec.competency)):
        errors.append("метаданные: title и competency должны быть на русском языке")
    if errors:
        return {"ok": False, "errors": errors, "code": code, "info": info}

    # --- 30 зёрен
    seen, content, instances = set(), set(), {}
    for seed in SEEDS:
        try:
            inst = spec.generate(random.Random(seed))
        except Exception:  # noqa: BLE001
            tb = traceback.format_exc().strip().splitlines()
            errors.append(f"генерация: зерно {seed}: " + " | ".join(tb[-2:]))
            break
        errs = _check_instance(spec.fmt, inst, Instance, check_answer)
        if errs:
            errors.extend(f"экземпляр (зерно {seed}): {e}" for e in errs[:3])
            break
        instances[seed] = inst
        seen.add(_signature(inst))
        content.add(_content_signature(inst))
    if errors:
        return {"ok": False, "errors": errors, "code": code, "info": info}
    if len(seen) < 5:
        errors.append(f"разнообразие: всего {len(seen)} разных экземпляров на 30 зёрнах, нужно не меньше 5 — усильте параметризацию")
    if len(content) < 3:
        errors.append(f"разнообразие: по содержанию (без учёта порядка вариантов) различаются только {len(content)} экземпляра(ов), "
                      "нужно не меньше 3 — меняйте сам вопрос/данные/правильный ответ, а не только перемешивайте варианты")
    for seed in SEEDS[:5]:
        if _signature(spec.generate(random.Random(seed))) != _signature(instances[seed]):
            errors.append(f"детерминизм: одно зерно {seed} дало разные экземпляры — вся случайность только из rng, без random.*/time")
            break
    info["distinct"] = len(seen)
    info["distinct_content"] = len(content)

    # --- exact: ключ совпадает с настоящим выводом кода
    if spec.fmt == "exact" and not errors:
        langs = {inst.language for inst in instances.values()}
        info["languages"] = sorted(str(x) for x in langs)
        if "python" in langs and langs != {"python"}:
            errors.append(f"exact: язык кода должен быть одинаков во всех экземплярах, встречаются {sorted(map(str, langs))}")
        checked = 0
        for seed, inst in instances.items():
            if inst.language == "python":
                try:
                    out = _run_python(inst.code)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"exact: зерно {seed}: показанный код падает при исполнении: {type(e).__name__}: {e}")
                    break
                if not out:
                    errors.append(f"exact: зерно {seed}: код на Python обязан печатать ответ")
                    break
                if normalize_exact(out) != normalize_exact(inst.answer):
                    errors.append(f"exact: зерно {seed}: вывод кода {out!r}, а ключ {inst.answer!r} — ключ считайте через _run_python(code)")
                    break
                checked += 1
            elif inst.language == "javascript" and seed <= 10:
                try:
                    out = _run_node(inst.code)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"exact: зерно {seed}: код на JavaScript не исполняется в node: {e}")
                    break
                if out is None:
                    break
                # сравниваем последовательность значений: node печатает по строке на событие, ключ склеен запятыми
                tokens = lambda t: [x for x in re.split(r"[\s,]+", normalize_exact(t)) if x]  # noqa: E731
                if tokens(out) != tokens(inst.answer):
                    errors.append(f"exact: зерно {seed}: вывод node {out!r}, а ключ {inst.answer!r} — ответ вычислен неверно")
                    break
                checked += 1
        info["executed"] = checked
    return {"ok": not errors, "errors": errors, "code": code, "info": info}


def list_generated() -> dict:
    from app.services.testing.bank import load_all
    from app.services.testing.bank.base import REGISTRY
    load_all()
    before = set(REGISTRY)
    importlib.import_module(PKG)
    out = []
    for code in sorted(set(REGISTRY) - before):
        s = REGISTRY[code]
        out.append({"code": code, "title": s.title, "competency": s.competency, "spec": (s.specializations or [None])[0],
                    "grade": s.grade_level, "techs": list(s.technologies), "fmt": s.fmt,
                    "module": s.generate.__module__.rsplit(".", 1)[-1]})
    return {"templates": out, "base_codes": sorted(before)}


def main() -> None:
    mode = sys.argv[1]
    if mode == "list":
        print(json.dumps(list_generated(), ensure_ascii=False))
        return
    mod_name = sys.argv[2]
    with open(sys.argv[3], encoding="utf-8") as f:
        expect = json.load(f)
    try:
        res = check(mod_name, expect)
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc().strip().splitlines()
        res = {"ok": False, "errors": ["проверка упала: " + " | ".join(tb[-3:])], "code": None, "info": {}}
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
