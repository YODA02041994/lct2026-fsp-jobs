#!/usr/bin/env python3
"""Расширение банка параметризованных заданий: модель предлагает шаблоны, программа их проверяет.

Принцип тот же, что в evolve_matching.py: модель — генератор кандидатов, а судья — код, не мнение модели.
Пробелы банка считаются по специализациям и грейдам (docs/08, раздел 6: у mobile/devops/analytics/security нет своих
шаблонов; у остальных мало senior и lead). Для каждого пробела модель пишет ОДИН шаблон, кандидат проверяется в отдельном
процессе (scripts/evolve/validate_candidate.py) с лимитом времени, принятые сохраняются в
backend/app/services/testing/bank/generated/<код>.py со статусом «черновик» в REGISTRY.md.

В боевой банк черновики не попадают, пока в load_all() (bank/__init__.py) не добавлена строка
    from . import generated  # noqa: F401
— так задумано: сначала просмотр человеком.

    cd backend && ../.venv/bin/python ../scripts/evolve/propose_templates.py [--workers 3] [--limit-usd 2] [--max-cells N] [--dry-run]

Ключ модели берёт llm_client (переменная FSP_LLM_API_KEY или ssh к серверу владельца); в вывод и файлы ключ не пишется.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BACKEND = os.path.join(ROOT, "backend")
GEN_DIR = os.path.join(BACKEND, "app", "services", "testing", "bank", "generated")
REGISTRY_MD = os.path.join(GEN_DIR, "REGISTRY.md")
RUN_LOG = os.path.join(GEN_DIR, "_run_log.jsonl")
REJECTED_DIR = os.path.join(GEN_DIR, "_rejected")
VALIDATOR = os.path.join(HERE, "validate_candidate.py")
VALIDATE_TIMEOUT = 30
sys.path.insert(0, HERE)
sys.path.insert(0, BACKEND)
import llm_client  # noqa: E402
from app.catalog import SPEC_TITLE  # noqa: E402
from app.services.skills_catalog import CODES, NAMES  # noqa: E402
from app.services.testing.bank import load_all  # noqa: E402

SPECS = ["backend", "frontend", "data", "qa", "mobile", "devops", "analytics", "security"]
GRADES = ["junior", "middle", "senior", "lead"]
GRADE_HINT = {
    "junior": "базовые понятия, чтение простого кода или конфигурации, одна идея на задание",
    "middle": "самостоятельная работа: типовые ловушки, поведение инструмента в неочевидном, но повседневном случае",
    "senior": "проектирование и неочевидные эффекты: производительность, согласованность, отказоустойчивость",
    "lead": "решения уровня команды и системы с компромиссами: процессы, архитектура, риски, приоритеты",
}

# Целевой план (ячейка = специализация × грейд × технологии × формат). Формат назначает программа, а не модель:
# exact допустим только там, где ключ проверяется независимо (Python — исполнением, SQL — через sqlite3,
# JavaScript — в node); для Kotlin/Swift/YAML/команд — выбор из вариантов.
PLAN: list[dict] = [
    # --- специализации без своих шаблонов: 2 junior, 2 middle, 1 senior, 1 lead
    dict(spec="mobile", grade="junior", techs=["kotlin", "android"], fmt="choice",
         hint="основы Kotlin в Android: null-safety (?. и ?:), val/var, data class, when; или порядок методов жизненного цикла Activity"),
    dict(spec="mobile", grade="junior", techs=["swift", "ios"], fmt="choice",
         hint="основы Swift в iOS: optionals, let/var, guard let, структуры против классов; жизненный цикл UIViewController или View в SwiftUI"),
    dict(spec="mobile", grade="middle", techs=["sql", "android"], fmt="exact",
         hint="локальная база приложения (SQLite/Room): таблицы сообщений/кэша/заказов, запрос с JOIN или GROUP BY — число строк или значение"),
    dict(spec="mobile", grade="middle", techs=["android", "rest"], fmt="multichoice",
         hint="сетевой слой и фоновая работа: корутины/Retrofit, повтор запросов, кэш ответов, обработка ошибок сети, работа при повороте экрана"),
    dict(spec="mobile", grade="senior", techs=["flutter", "http"], fmt="choice",
         hint="Flutter: состояние и перерисовка (setState/Provider/BLoC), производительность длинных списков, обработка сетевых ошибок и таймаутов"),
    dict(spec="mobile", grade="lead", techs=["android", "ios"], fmt="multichoice",
         hint="архитектура мобильного приложения (MVVM/Clean), релизный процесс двух платформ, флаги функций, обратная совместимость с API, падения в проде"),

    dict(spec="devops", grade="junior", techs=["docker", "linux"], fmt="choice",
         hint="Dockerfile: слои и кэш сборки, CMD против ENTRYPOINT, EXPOSE и -p, .dockerignore; повседневные команды docker"),
    dict(spec="devops", grade="junior", techs=["bash", "linux"], fmt="choice",
         hint="права доступа (chmod/chown, восьмеричная запись), конвейеры и grep/awk/sort/uniq, процессы и сигналы, переменные окружения"),
    dict(spec="devops", grade="middle", techs=["kubernetes", "docker"], fmt="choice",
         hint="манифест Deployment/Service: readiness и liveness, requests/limits, селекторы и метки, образ с тегом latest — найти причину проблемы"),
    dict(spec="devops", grade="middle", techs=["ci_cd", "git"], fmt="multichoice",
         hint="конвейер CI: стадии и зависимости, кэш и артефакты, запуск по веткам и тегам, секреты, нестабильные шаги"),
    dict(spec="devops", grade="senior", techs=["python", "linux"], fmt="exact",
         hint="скрипт разбора журнала на Python: строки журнала заданы в коде, считаются коды ответов, уникальные адреса, "
              "ошибки за окно времени — код печатает число или строку"),
    dict(spec="devops", grade="lead", techs=["kubernetes", "prometheus"], fmt="multichoice",
         hint="SLO и алерты (бюджет ошибок, симптомы против причин), стратегии выката (канареечный, сине-зелёный), автошкалирование, разбор инцидента"),

    dict(spec="analytics", grade="junior", techs=["sql", "excel"], fmt="exact",
         hint="сводная таблица средствами SQL: GROUP BY по категории/месяцу, сумма или среднее, HAVING — одно число"),
    dict(spec="analytics", grade="junior", techs=["system_analysis", "uml"], fmt="choice",
         hint="функциональные и нефункциональные требования, пользовательские истории и критерии приёмки, какая диаграмма UML подходит под задачу"),
    dict(spec="analytics", grade="middle", techs=["sql", "product_analytics"], fmt="exact",
         hint="воронка, удержание или конверсия на SQL: таблица событий пользователей, сколько пользователей дошли до шага / вернулись"),
    dict(spec="analytics", grade="middle", techs=["bpmn", "system_analysis"], fmt="choice",
         hint="элементы BPMN (шлюзы И/ИЛИ/исключающий, события, дорожки), чтение схемы процесса в тексте, поиск противоречия в постановке"),
    dict(spec="analytics", grade="senior", techs=["python", "statistics"], fmt="exact",
         hint="расчёт метрики на Python по заданным целым данным: медиана, персентиль, доля, сравнение конверсий двух групп — "
              "код печатает целое число или строку (без плавающих чисел в ответе)"),
    dict(spec="analytics", grade="lead", techs=["system_analysis", "agile"], fmt="multichoice",
         hint="приоритизация бэклога (RICE/MoSCoW), управление изменениями требований, работа с заинтересованными сторонами, критерии готовности"),

    dict(spec="security", grade="junior", techs=["security_basics", "networking"], fmt="choice",
         hint="OWASP Top 10: распознать класс уязвимости по описанию инцидента; порты и протоколы; что защищает TLS, а что нет"),
    dict(spec="security", grade="junior", techs=["linux", "bash"], fmt="choice",
         hint="права файлов и sudo, журнал входов, поиск подозрительного процесса или задания cron, что делает команда"),
    dict(spec="security", grade="middle", techs=["python", "cryptography"], fmt="exact",
         hint="Python: шифр сдвига или XOR над строкой, hashlib/base64 — код печатает результат одной строкой (короткой)"),
    dict(spec="security", grade="middle", techs=["security_basics", "sql"], fmt="exact",
         hint="SQL-инъекция: в запрос подставлена строка пользователя (например, ' OR '1'='1), запрос выполняется на таблице — сколько строк вернётся"),
    dict(spec="security", grade="senior", techs=["security_basics", "docker"], fmt="multichoice",
         hint="безопасность контейнеров и секретов: запуск не от root, секреты не в образе, сканирование образов, сетевые политики, read-only ФС"),
    dict(spec="security", grade="lead", techs=["security_basics", "networking"], fmt="multichoice",
         hint="модель угроз, сегментация сети и нулевое доверие, реагирование на инцидент (сдерживание, устранение, разбор), политика доступа"),

    # --- существующие специализации: по 2 senior и 2 lead
    dict(spec="backend", grade="senior", techs=["python", "oop"], fmt="exact",
         hint="Python: классы и наследование, property, __slots__, порядок вызова __init__/super(), dunder-методы — код печатает результат"),
    dict(spec="backend", grade="senior", techs=["sql", "postgresql"], fmt="exact",
         hint="оконные функции, CTE, подзапросы, GROUP BY в два уровня (диалект SQLite) — одно значение или число строк"),
    dict(spec="backend", grade="lead", techs=["system_design", "kafka"], fmt="multichoice",
         hint="гарантии доставки и идемпотентность потребителей, партиционирование и порядок сообщений, очередь против журнала, обратное давление"),
    dict(spec="backend", grade="lead", techs=["python", "rest"], fmt="choice",
         hint="проектирование публичного API: версионирование, пагинация, обратная совместимость, лимиты запросов, формат ошибок"),

    dict(spec="frontend", grade="senior", techs=["javascript", "typescript"], fmt="exact",
         hint="JavaScript: замыкания, порядок микрозадач и макрозадач (Promise/setTimeout), this, деструктуризация — "
              "код исполним в node без импортов и печатает ответ одной строкой через console.log"),
    dict(spec="frontend", grade="senior", techs=["react", "javascript"], fmt="choice",
         hint="React: лишние перерисовки, ключи списков, зависимости useEffect, мемоизация, устаревшее замыкание — найти причину"),
    dict(spec="frontend", grade="lead", techs=["typescript", "react"], fmt="multichoice",
         hint="архитектура фронтенда: разделение состояния, производительность, доступность, дизайн-система, микрофронтенды — компромиссы"),
    dict(spec="frontend", grade="lead", techs=["webpack", "javascript"], fmt="choice",
         hint="сборка и доставка: разделение кода, кэширование по хешу, бюджеты производительности, карты исходников, выбор инструмента"),

    dict(spec="data", grade="senior", techs=["python", "statistics"], fmt="exact",
         hint="Python: медиана, мода, персентиль по целым данным, скользящее окно, нормализация в целых — код печатает целое или строку"),
    dict(spec="data", grade="senior", techs=["sql"], fmt="exact",
         hint="оконные функции ROW_NUMBER/LAG/SUM OVER, дедупликация, топ-N в группе (диалект SQLite) — одно значение или число строк"),
    dict(spec="data", grade="lead", techs=["ml", "system_design"], fmt="multichoice",
         hint="модель в проде: дрейф данных, утечка признаков, разбиение по времени, мониторинг качества, выкат модели через A/B"),
    dict(spec="data", grade="lead", techs=["airflow", "spark"], fmt="choice",
         hint="конвейеры данных: идемпотентность задач, повторная загрузка за прошлое, партиционирование, инкрементальная загрузка, SLA"),

    dict(spec="qa", grade="senior", techs=["python", "pytest"], fmt="exact",
         hint="Python: число тест-случаев при параметризации и попарном переборе (itertools.product), порядок вызова "
              "фикстур смоделирован функциями — код печатает число или строку"),
    dict(spec="qa", grade="senior", techs=["sql", "testing_theory"], fmt="exact",
         hint="проверка данных после миграции на SQL: сравнение двух таблиц (EXCEPT, LEFT JOIN ... IS NULL) — сколько строк расходятся"),
    dict(spec="qa", grade="lead", techs=["testing_theory", "ci_cd"], fmt="multichoice",
         hint="стратегия тестирования: пирамида, нестабильные тесты, пороги качества в CI, тестовые окружения и данные, метрики качества"),
    dict(spec="qa", grade="lead", techs=["testing_theory", "agile"], fmt="choice",
         hint="планирование тестирования в спринте: оценка рисков, критерии выхода, приоритизация регресса, что делать при срыве сроков"),
]

# ---------------------------------------------------------------------------------------------
# Статические проверки сгенерированного кода (до запуска)
# ---------------------------------------------------------------------------------------------

ALLOWED_MODULES = {"random", "math", "string", "itertools", "collections", "functools", "re", "json", "textwrap",
                   "statistics", "fractions", "decimal", "hashlib", "base64", "heapq", "bisect", "operator", "datetime",
                   "calendar", "typing", "dataclasses", "enum", "copy", "binascii", "hmac", "secrets"}
FORBIDDEN = [
    (re.compile(r"\bsubprocess\b"), "subprocess"),
    (re.compile(r"__import__"), "__import__"),
    (re.compile(r"(?<![\w.])open\("), "open("),
    (re.compile(r"(?<![\w.])eval\("), "eval("),
    (re.compile(r"(?<![\w.])exec\("), "exec("),
    (re.compile(r"(?<![\w.])compile\("), "compile("),
    (re.compile(r"\bglobals\(|\blocals\(|__builtins__|\bbreakpoint\(|(?<![\w.])input\("), "доступ к окружению интерпретатора"),
    (re.compile(r"\brandom\.(choice|choices|randint|sample|shuffle|randrange|random|uniform|seed|getrandbits|triangular|gauss)\("),
     "random.* напрямую (вся случайность — только из rng)"),
    (re.compile(r"\bsecrets\.(choice|randbelow|token_\w+)\("), "secrets.* (недетерминировано)"),
    (re.compile(r"datetime\.now\(|date\.today\(|time\.time\(|utcnow\("), "текущее время (недетерминировано)"),
]
IMPORT_RE = re.compile(r"^\s*(?:import\s+([\w.]+)|from\s+([\w.]+)\s+import)", re.M)


def static_errors(src: str, cell: dict) -> list[str]:
    errs: list[str] = []
    try:
        compile(src, "<кандидат>", "exec")
    except SyntaxError as e:
        errs.append(f"синтаксис: строка {e.lineno}: {e.msg}: {(e.text or '').strip()[:120]}")
    if "@template(" not in src:
        errs.append("статика: в ответе нет @template(...) — верните полный файл шаблона")
    if "from ..base import" not in src:
        errs.append("статика: нужен импорт `from ..base import template, Instance, shuffle_options` (две точки: пакет generated лежит внутри bank)")
    if re.search(r"^\s*from \.(base|common) import", src, re.M):
        errs.append("статика: импорты с одной точкой (`from .base`) не сработают — нужно `from ..base` и `from ..common`")
    if re.search(r"^\s*from app\.", src, re.M):
        errs.append("статика: абсолютные импорты `from app....` запрещены — только относительные `from ..base`/`from ..common`")
    for m in IMPORT_RE.finditer(src):
        name = m.group(1) or m.group(2)
        if name.startswith("."):
            continue
        root = name.split(".")[0]
        if root == "__future__":
            continue
        if root not in ALLOWED_MODULES:
            errs.append(f"статика: импорт `{name}` запрещён — только стандартная библиотека из списка {sorted(ALLOWED_MODULES)}")
    for pat, what in FORBIDDEN:
        if pat.search(src):
            errs.append(f"статика: запрещённая конструкция: {what}")
    n_templates = len(re.findall(r"^@template\(", src, re.M))
    if n_templates > 1:
        errs.append(f"статика: в файле {n_templates} декоратора @template, нужен ровно один")
    m = re.search(r"@template\(\s*[\"']([^\"']+)[\"']", src)
    if m:
        code = m.group(1)
        prefix = f"gen_{cell['spec']}_"
        if not (re.fullmatch(r"[a-z0-9_]+", code) and code.startswith(prefix) and len(code) > len(prefix)):
            errs.append(f"статика: код шаблона должен быть вида {prefix}<тема латиницей в нижнем регистре>, получено {code!r}")
        if code in cell["occupied"]:
            errs.append(f"статика: код шаблона {code!r} уже занят, выберите другой")
    if cell["fmt"] == "exact":
        if "python" in cell["techs"] and "_run_python(" not in src:
            errs.append("статика: exact с кодом на Python обязан считать ключ через _run_python(code)")
        if "sql" in cell["techs"] and "_sql_eval(" not in src:
            errs.append("статика: exact с SQL обязан считать ключ через _sql_eval(tables, query)")
    elif cell["fmt"] == "choice" and "_choice(" not in src and "shuffle_options(" not in src:
        errs.append("статика: choice собирается через _choice(...) (варианты перемешиваются)")
    elif cell["fmt"] == "multichoice" and "_multi(" not in src and "shuffle_options(" not in src:
        errs.append("статика: multichoice собирается через _multi(...)")
    return errs


# ---------------------------------------------------------------------------------------------
# Промпт
# ---------------------------------------------------------------------------------------------

INTERFACE = '''# backend/app/services/testing/bank/base.py (сокращённо; менять нельзя)
GRADE_DIFFICULTY = {"junior": -1.5, "middle": -0.5, "senior": 0.5, "lead": 1.5}
FORMATS = ("exact", "choice", "multichoice")

@dataclass
class Instance:
    question: str                       # формулировка на русском (можно с переносами строк)
    answer: str | int | list[int]       # exact: строка; choice: индекс варианта; multichoice: список индексов
    code: str | None = None             # фрагмент кода, конфигурации или данных, который видит кандидат
    language: str | None = None         # ТОЛЬКО python / javascript / sql / text / html / css
    options: list[str] | None = None    # варианты для choice / multichoice (уже в итоговом порядке)
    explanation: str = ""               # короткое пояснение на русском (показывается после теста)

def template(code: str, *, title: str, competency: str, specializations: list[str], technologies: list[str],
             fmt: str, grade_level: str, difficulty_shift: float = 0.0):
    """Декоратор регистрации генератора fn(rng: random.Random) -> Instance. Код шаблона уникален во всём банке."""

def shuffle_options(rng, options: list[str], correct: int | list[int]) -> tuple[list[str], int | list[int]]:
    """Перемешать варианты и пересчитать индекс(ы) правильного ответа."""

# backend/app/services/testing/bank/common.py — помощники
def _run_python(code: str) -> str
    # исполняет фрагмент и возвращает его stdout без крайних пробелов — ТАК считается ключ exact для Python
def _sql_eval(tables: dict[str, tuple[list[str], list[tuple]]], query: str) -> list[tuple]
    # tables: имя -> (колонки, строки); выполняет запрос в sqlite3 (в памяти) и возвращает строки результата
def _sql_block(tables, query) -> str
    # рисует таблицы SQL-комментариями и добавляет запрос — это кладут в code при language="sql"
def _choice(rng, question: str, options: list[str], correct: int, explanation: str, code=None, language=None) -> Instance
    # не меньше 5 УНИКАЛЬНЫХ вариантов; перемешает их и пересчитает индекс правильного
def _multi(rng, question: str, correct: list[str], wrong: list[str], explanation: str, code=None, language=None) -> Instance
    # 2–3 верных утверждения, всего 5–6 вариантов, все уникальны; перемешает и вернёт список индексов
'''

RULES = '''ТРЕБОВАНИЯ К ФАЙЛУ ШАБЛОНА
1. Файл начинается так (ровно эти строки, порядок важен):
   """<одна строка: что проверяет шаблон>"""
   from __future__ import annotations
   import random
   from ..base import template, Instance, shuffle_options
   from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi
   Другие импорты — только стандартная библиотека (math, string, itertools, collections, re, json, statistics, hashlib,
   base64, datetime, textwrap). Запрещены: os, sys, subprocess, open(), eval(), exec(), __import__, сеть, файлы.
2. Ровно ОДИН декоратор @template с кодом вида {code_prefix}<тема латиницей> (не из списка занятых),
   specializations=["{spec}"], technologies={techs}, fmt="{fmt}", grade_level="{grade}", difficulty_shift в пределах ±0.4.
   title и competency — на русском, коротко.
3. Вся случайность — только из переданного rng (rng.choice, rng.randint, rng.sample, rng.shuffle…). Нельзя random.*,
   time, datetime.now: одно зерно — всегда один и тот же экземпляр.
4. Параметризация сильная: на 30 зёрнах должно получиться не меньше 8 экземпляров, различающихся по содержанию
   (данные, имена, числа, сценарий, ПРАВИЛЬНЫЙ ответ), а не только порядком вариантов. Для choice/multichoice —
   список из 5–7 сценариев/случаев, из которого rng выбирает один, плюс случайные имена/числа в тексте.
5. Язык: вопрос, варианты и пояснение — по-русски (термины, названия команд и код — как есть). Без англицизмов там,
   где есть русское слово. Вопрос формулировать так, чтобы ответ был однозначен.
6. language только из списка python / javascript / sql / text / html / css. Для Kotlin, Swift, Dart, YAML, Dockerfile,
   bash-команд, манифестов, схем и нотаций — language="text".
{fmt_rules}
7. Пояснение explanation объясняет, почему ответ именно такой (1–2 предложения).
8. Никакой прозы вне кода. Ответ — ОДИН блок ```python с полным содержимым файла.'''

FMT_RULES = {
    "exact_python": '''ФОРМАТ exact (код на Python):
   - показанный код (поле code, language="python") — самодостаточный фрагмент без импортов вне стандартной библиотеки,
     без ввода, без случайности и без зависимости от порядка хеширования (никаких set в выводе); печатает ответ
     ОДНОЙ строкой через print;
   - ключ считается ТОЛЬКО так: answer=_run_python(code) — никаких вычислений «вручную»;
   - ответ — скаляр или значения через пробел/запятую: целое число, слово, имя класса; НЕ список/словарь/кортеж и
     НЕ плавающее число (при делении используйте //, round до целого или проценты целым числом);
   - вопрос заканчивается подсказкой формата: «Введите число.» / «Введите значения через пробел.» и т. п.;
   - код должен требовать понимания темы, а не только арифметики: ответ не читается из кода напрямую.''',
    "exact_sql": '''ФОРМАТ exact (SQL):
   - таблицы генерируются случайно: tables = {"имя": (["кол1", "кол2"], [(…), (…)])}, 5–9 строк в каждой;
   - запрос в диалекте SQLite (без ILIKE, ::, DATE_TRUNC; строки в одинарных кавычках; оконные функции разрешены);
   - ключ считается ТОЛЬКО так: rows = _sql_eval(tables, query); answer=str(rows[0][0]) или str(len(rows));
     если ответ — несколько значений, склейте их через запятую в порядке ORDER BY;
   - code=_sql_block(tables, query), language="sql";
   - подбирайте параметры в цикле while True … break, чтобы ответ был содержательным (не 0 и не все строки);
   - ответ — целое число или короткая строка, не плавающее (AVG оборачивайте в CAST(... AS INTEGER) или ROUND(...,0)
     с последующим CAST), не NULL;
   - вопрос заканчивается подсказкой формата: «Введите число.» и т. п.''',
    "exact_javascript": '''ФОРМАТ exact (код на JavaScript):
   - показанный код (language="javascript") исполним в node без импортов и без DOM; печатает ответ ОДНОЙ строкой
     через console.log (для асинхронного кода — склейте порядок событий в строку и выведите её один раз в конце);
   - ответ вычисляется в Python-коде генератора ТОЙ ЖЕ логикой, что показанный JavaScript, и answer=str(...);
     ответ — целое число или слова через пробел/запятую, не список и не плавающее число;
   - вопрос заканчивается подсказкой формата: «Введите число.» / «Введите значения через запятую без пробелов.».''',
    "choice": '''ФОРМАТ choice:
   - return _choice(rng, вопрос, options, индекс_правильного, пояснение, code=…, language=…);
   - не меньше 5 УНИКАЛЬНЫХ вариантов; неверные — правдоподобные типичные заблуждения, а не очевидный мусор;
   - правильный ответ должен меняться от экземпляра к экземпляру (сценарий выбирается из списка из 5–7 случаев);
   - если показываете код/конфигурацию (Kotlin, Swift, YAML, Dockerfile, команды) — language="text"; фрагмент должен
     быть корректным и компилируемым целиком в этом языке (return — только внутри функции, объявления полные),
     и ровно один вариант должен быть верным — перепроверьте, что ни один «неверный» вариант не оказался тоже верным.''',
    "multichoice": '''ФОРМАТ multichoice:
   - return _multi(rng, вопрос, correct, wrong, пояснение, code=…, language=…), где correct — 2–3 верных утверждения,
     wrong — остальные, всего 5–6; наборы верных и неверных формируются rng.sample из пулов по 4–6 утверждений;
   - вопрос заканчивается словами «Выберите все подходящие.»;
   - утверждения конкретные и проверяемые, без оценочных слов «лучше/хуже» без критерия; каждое «неверное» утверждение
     должно быть действительно ложным, а не спорным.''',
}

SYSTEM = ("Ты пишешь параметризованные задания для теста на грейд ИТ-специалиста. Пишешь код на Python строго по интерфейсу "
          "банка, на русском языке, без прозы вне кода. Задание должно проверять настоящее понимание темы и иметь однозначный ответ.")

EXAMPLES = {
    "exact_python": ["common_algo_recursion"],
    "exact_sql": ["common_sql_count_rows"],
    "exact_javascript": ["frontend_js_reduce"],
    "choice": ["common_git_command"],
    "multichoice": ["common_git_rebase_merge"],
}


def fmt_kind(cell: dict) -> str:
    if cell["fmt"] != "exact":
        return cell["fmt"]
    if "python" in cell["techs"]:
        return "exact_python"
    if "sql" in cell["techs"]:
        return "exact_sql"
    if "javascript" in cell["techs"]:
        return "exact_javascript"
    return "exact_python"


def example_sources(registry: dict, kind: str) -> str:
    codes = ["common_algo_recursion", "common_git_command"]
    for c in EXAMPLES[kind]:
        if c not in codes:
            codes.append(c)
    parts = []
    for c in codes:
        parts.append(inspect.getsource(registry[c].generate).rstrip())
    return "\n\n\n".join(parts)


def build_prompt(cell: dict, registry: dict, existing_titles: list[str], error: str | None = None,
                 prev_code: str | None = None) -> list[dict]:
    kind = fmt_kind(cell)
    techs_named = ", ".join(f"{t} ({NAMES.get(t, t)})" for t in cell["techs"])
    rules = RULES.format(code_prefix=f"gen_{cell['spec']}_", spec=cell["spec"], techs=json.dumps(cell["techs"]),
                         fmt=cell["fmt"], grade=cell["grade"], fmt_rules=FMT_RULES[kind])
    titles = "\n".join(f"   - {t}" for t in existing_titles) or "   (пока нет)"
    user = f"""{INTERFACE}

ОБРАЗЦЫ ШАБЛОНОВ ИЗ БАНКА (в них импорты другие — у вас должны быть `from ..base` и `from ..common`):

{example_sources(registry, kind)}


ЦЕЛЕВАЯ ЯЧЕЙКА
- специализация: {cell['spec']} — {SPEC_TITLE.get(cell['spec'], cell['spec'])}
- грейд: {cell['grade']} — {GRADE_HINT[cell['grade']]}
- технологии (ровно этот список в technologies): {json.dumps(cell['techs'])} — {techs_named}
- формат: {cell['fmt']}
- тема-ориентир: {cell['hint']}
- уже есть у этой специализации (тему не повторять):
{titles}
- занятые коды шаблонов (взять другой): {", ".join(sorted(cell['occupied']))}

{rules}
"""
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    if error:
        msgs.append({"role": "assistant", "content": f"```python\n{prev_code}\n```"})
        msgs.append({"role": "user", "content": f"Этот шаблон не прошёл проверку:\n{error}\n\n"
                                                 "Исправьте причину и верните полный файл заново — один блок ```python, без прозы."})
    return msgs


# ---------------------------------------------------------------------------------------------
# Валидация в отдельном процессе, принятие, реестр
# ---------------------------------------------------------------------------------------------

def run_validator(args: list[str], timeout: int) -> dict:
    try:
        r = subprocess.run([sys.executable, VALIDATOR, *args], cwd=BACKEND, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "errors": [f"время: проверка не уложилась в {timeout} с (зацикливание в генераторе или слишком тяжёлые вычисления)"],
                "code": None, "info": {}}
    lines = [ln for ln in r.stdout.strip().splitlines() if ln.strip()]
    if not lines:
        tail = " | ".join(r.stderr.strip().splitlines()[-3:]) if r.stderr.strip() else "нет вывода"
        return {"ok": False, "errors": [f"проверка: процесс завершился без результата: {tail}"], "code": None, "info": {}}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"ok": False, "errors": [f"проверка: нечитаемый вывод: {lines[-1][:200]}"], "code": None, "info": {}}


def list_generated() -> dict:
    res = run_validator(["list"], timeout=120)
    if "templates" not in res:
        raise SystemExit(f"не удалось прочитать пакет generated: {res}")
    return res


def write_registry(templates: list[dict]) -> None:
    """REGISTRY.md пересобирается из фактического содержимого пакета; дата и статус уже известных строк сохраняются."""
    known: dict[str, tuple[str, str]] = {}
    if os.path.exists(REGISTRY_MD):
        for ln in open(REGISTRY_MD, encoding="utf-8"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) >= 8 and cells[0].startswith("gen_"):
                known[cells[0]] = (cells[6], cells[7])
    today = dt.date.today().isoformat()
    order = {s: i for i, s in enumerate(SPECS)}
    gorder = {g: i for i, g in enumerate(GRADES)}
    rows = sorted(templates, key=lambda t: (order.get(t["spec"], 99), gorder.get(t["grade"], 99), t["code"]))
    lines = [
        "# Реестр сгенерированных шаблонов",
        "",
        "Черновики, предложенные моделью (`scripts/evolve/propose_templates.py`) и прошедшие автоматическую проверку",
        "(`scripts/evolve/validate_candidate.py`, те же проверки, что в `backend/tests/test_bank.py`). В бой попадают после",
        "просмотра человеком и строки `from . import generated  # noqa: F401` в `load_all()` (`bank/__init__.py`).",
        "Файл пересобирается скриптом из содержимого папки: удалили файл шаблона — строка исчезнет; статус и дату строки скрипт сохраняет.",
        "",
        "| Код | Специализация | Грейд | Технологии | Формат | Название | Дата | Статус |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for t in rows:
        date, status = known.get(t["code"], (today, "draft"))
        lines.append(f"| {t['code']} | {t['spec']} | {t['grade']} | {', '.join(t['techs'])} | {t['fmt']} | {t['title']} | {date} | {status} |")
    lines.append("")
    lines.append(f"Всего: {len(rows)}.")
    with open(REGISTRY_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def log_attempt(rec: dict) -> None:
    with open(RUN_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def save_rejected(cell: dict, n: int, attempt: int, src: str, errors: list[str]) -> None:
    os.makedirs(REJECTED_DIR, exist_ok=True)
    path = os.path.join(REJECTED_DIR, f"{cell['spec']}_{cell['grade']}_{n:03d}_{attempt}.py.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# ОТКЛОНЁН. Причины:\n" + "".join(f"#   - {e}\n" for e in errors) + "\n" + src)


# ---------------------------------------------------------------------------------------------
# Пробелы
# ---------------------------------------------------------------------------------------------

def gap_table(base_registry: dict, generated: list[dict]) -> tuple[str, Counter]:
    have: Counter = Counter()
    for s in base_registry.values():
        for sp in s.specializations:
            have[(sp, s.grade_level)] += 1
    for t in generated:
        have[(t["spec"], t["grade"])] += 1
    target: Counter = Counter((c["spec"], c["grade"]) for c in PLAN)
    base_only: Counter = Counter()
    for s in base_registry.values():
        for sp in s.specializations:
            base_only[(sp, s.grade_level)] += 1
    lines = ["Пробелы банка (есть в банке + принято ранее / план этого скрипта):", "спец.       " + "".join(f"{g:>14}" for g in GRADES)]
    for sp in SPECS:
        cells = []
        for g in GRADES:
            cells.append(f"{base_only[(sp, g)]}+{have[(sp, g)] - base_only[(sp, g)]} / +{target[(sp, g)]}".rjust(14))
        lines.append(f"{sp:<12}" + "".join(cells))
    return "\n".join(lines), have


def todo_cells(generated: list[dict]) -> list[dict]:
    """Ячейки плана, ещё не закрытые принятыми шаблонами. Сначала сопоставление по набору технологий, затем по грейду."""
    done = [False] * len(PLAN)
    unmatched: list[dict] = []
    for t in generated:
        hit = next((i for i, c in enumerate(PLAN) if not done[i] and c["spec"] == t["spec"] and c["grade"] == t["grade"]
                    and set(c["techs"]) == set(t["techs"])), None)
        if hit is None:
            unmatched.append(t)
        else:
            done[hit] = True
    for t in unmatched:
        hit = next((i for i, c in enumerate(PLAN) if not done[i] and c["spec"] == t["spec"] and c["grade"] == t["grade"]), None)
        if hit is not None:
            done[hit] = True
    return [dict(c) for i, c in enumerate(PLAN) if not done[i]]


# ---------------------------------------------------------------------------------------------
# Основной цикл
# ---------------------------------------------------------------------------------------------

class State:
    def __init__(self, base_codes: list[str], generated: list[dict], limit_usd: float):
        self.lock = threading.Lock()
        self.occupied: set[str] = set(base_codes) | {t["code"] for t in generated}
        self.titles: dict[str, list[str]] = {}
        for t in generated:
            self.titles.setdefault(t["spec"], []).append(t["title"])
        self.counter = 0
        self.limit_usd = limit_usd
        self.stop = threading.Event()
        self.accepted: list[dict] = []
        self.reasons: Counter = Counter()
        self.calls = 0

    def next_id(self) -> int:
        with self.lock:
            self.counter += 1
            return self.counter


def reason_key(err: str) -> str:
    return err.split(":", 1)[0].strip() if ":" in err else err[:30]


def process_cell(cell: dict, st: State, registry: dict, verbose: bool) -> dict:
    tag = f"{cell['spec']}/{cell['grade']}/{'+'.join(cell['techs'])}/{cell['fmt']}"
    result = {"cell": tag, "ok": False, "code": None, "errors": [], "attempts": 0}
    error_text, prev_code = None, None
    for attempt in (1, 2):
        if st.stop.is_set():
            result["errors"] = ["остановлено: лимит расхода"]
            break
        if llm_client.cost_usd() >= st.limit_usd:
            st.stop.set()
            result["errors"] = ["остановлено: лимит расхода"]
            break
        with st.lock:
            cell["occupied"] = sorted(st.occupied)
            titles = list(st.titles.get(cell["spec"], []))
        msgs = build_prompt(cell, registry, titles, error_text, prev_code)
        t0 = time.time()
        try:
            raw = llm_client.chat(msgs, max_tokens=2500, temperature=0.7)
        except Exception as e:  # noqa: BLE001
            result["errors"] = [f"модель: {e}"]
            result["attempts"] = attempt
            break
        st.calls += 1
        src = llm_client.extract_code(raw)
        if src.startswith("py\n"):
            src = src[3:]
        src = src.strip("\n") + "\n"
        n = st.next_id()
        errors = static_errors(src, cell)
        res: dict = {"ok": False, "errors": errors, "code": None, "info": {}}
        if not errors:
            cand = f"_cand_{n}"
            cand_path = os.path.join(GEN_DIR, cand + ".py")
            with st.lock:                      # проверка и принятие — последовательно: пакет generated читается целиком
                with open(cand_path, "w", encoding="utf-8") as f:
                    f.write(src)
                fd, expect_path = tempfile.mkstemp(suffix=".json", prefix="expect_")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump({"spec": cell["spec"], "grade": cell["grade"], "techs": cell["techs"], "fmt": cell["fmt"],
                               "occupied": sorted(st.occupied)}, f, ensure_ascii=False)
                try:
                    res = run_validator(["check", cand, expect_path], timeout=VALIDATE_TIMEOUT)
                finally:
                    os.unlink(expect_path)
                if res.get("ok"):
                    code = res["code"]
                    final = os.path.join(GEN_DIR, code + ".py")
                    if os.path.exists(final) or code in st.occupied:
                        res = {"ok": False, "errors": [f"метаданные: код {code!r} уже занят"], "code": code, "info": res.get("info", {})}
                        os.unlink(cand_path)
                    else:
                        os.replace(cand_path, final)
                        st.occupied.add(code)
                        st.titles.setdefault(cell["spec"], []).append(res["info"].get("title", code))
                        rec = {"code": code, "spec": cell["spec"], "grade": cell["grade"], "techs": cell["techs"], "fmt": cell["fmt"],
                               "title": res["info"].get("title", ""), "competency": res["info"].get("competency", ""),
                               "info": res.get("info", {}), "attempt": attempt}
                        st.accepted.append(rec)
                        write_registry(list_generated()["templates"])
                else:
                    if os.path.exists(cand_path):
                        os.unlink(cand_path)
        errors = res.get("errors", [])
        log_attempt({"ts": dt.datetime.now().isoformat(timespec="seconds"), "cell": tag, "attempt": attempt, "ok": bool(res.get("ok")),
                     "code": res.get("code"), "errors": errors, "info": res.get("info", {}), "secs": round(time.time() - t0, 1),
                     "src_sha": hashlib.sha1(src.encode()).hexdigest()[:10], "cost_usd": llm_client.cost_usd()})
        result["attempts"] = attempt
        if res.get("ok"):
            result.update(ok=True, code=res["code"], errors=[])
            print(f"  ✓ {tag} → {res['code']} (попытка {attempt}, {time.time() - t0:.0f} с, "
                  f"разных {res['info'].get('distinct')}/{res['info'].get('distinct_content')})", flush=True)
            break
        save_rejected(cell, n, attempt, src, errors)
        with st.lock:
            for e in errors:
                st.reasons[reason_key(e)] += 1
        result["errors"] = errors
        error_text = "\n".join(f"- {e}" for e in errors)
        prev_code = src
        print(f"  ✗ {tag} попытка {attempt}: {errors[0][:160]}" + (f" (+{len(errors) - 1})" if len(errors) > 1 else ""), flush=True)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=3, help="параллельных обращений к модели")
    ap.add_argument("--limit-usd", type=float, default=2.0, help="лимит расхода в долларах")
    ap.add_argument("--max-cells", type=int, default=0, help="взять только первые N пробелов (для пробного запуска)")
    ap.add_argument("--only-spec", default="", help="только эта специализация")
    ap.add_argument("--dry-run", action="store_true", help="показать пробелы и один промпт, модель не вызывать")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    os.makedirs(GEN_DIR, exist_ok=True)
    registry = load_all()
    listing = list_generated()
    generated = listing["templates"]
    table, _ = gap_table(registry, generated)
    print(table)
    todo = todo_cells(generated)
    if args.only_spec:
        todo = [c for c in todo if c["spec"] == args.only_spec]
    if args.max_cells:
        todo = todo[: args.max_cells]
    print(f"\nВ банке {len(registry)} шаблонов, в generated принято ранее {len(generated)}; к запросу {len(todo)} ячеек "
          f"(план {len(PLAN)}).", flush=True)
    if not todo:
        print("Пробелов по плану нет — делать нечего.")
        return
    st = State(listing["base_codes"], generated, args.limit_usd)
    if args.dry_run:
        c = dict(todo[0]); c["occupied"] = sorted(st.occupied)
        msgs = build_prompt(c, registry, st.titles.get(c["spec"], []))
        print("\n--- ПРОМПТ ДЛЯ ПЕРВОЙ ЯЧЕЙКИ ---\n" + msgs[1]["content"])
        print(f"\n(размер промпта ~{sum(len(m['content']) for m in msgs) // 3} токенов)")
        return

    print(f"Проверка связи с моделью ({llm_client.MODEL})…", end=" ", flush=True)
    pong = llm_client.chat([{"role": "user", "content": "Ответь одним словом: да"}], max_tokens=5, temperature=0)
    print(f"ответ: {pong.strip()!r}\n", flush=True)

    t_start = time.time()
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [ex.submit(process_cell, dict(c), st, registry, args.verbose) for c in todo]
        for fut in as_completed(futs):
            results.append(fut.result())

    # --- отчёт
    final_listing = list_generated()
    write_registry(final_listing["templates"])
    accepted = [r for r in results if r["ok"]]
    print("\n" + "=" * 100)
    print(f"ОТЧЁТ: запрошено ячеек {len(todo)}, обращений к модели {llm_client.SPEND['calls']}, принято {len(accepted)}, "
          f"отклонено ячеек {len(todo) - len(accepted)}; время {(time.time() - t_start) / 60:.1f} мин; "
          f"расход {llm_client.cost_usd():.4f} $ (вход {llm_client.SPEND['input']}, выход {llm_client.SPEND['output']} токенов)"
          + ("; ОСТАНОВЛЕНО ПО ЛИМИТУ РАСХОДА" if st.stop.is_set() else ""))
    by_cell: Counter = Counter()
    for r in accepted:
        sp, g = r["cell"].split("/")[:2]
        by_cell[(sp, g)] += 1
    print("\nПринято по ячейкам (спец. × грейд): " + ", ".join(f"{sp}/{g}: {n}" for (sp, g), n in sorted(by_cell.items())))
    if st.reasons:
        print("\nПричины отказов (по попыткам, одна попытка может иметь несколько причин):")
        for k, n in st.reasons.most_common():
            print(f"  {n:3d}  {k}")
    failed = [r for r in results if not r["ok"]]
    if failed:
        print("\nНезакрытые ячейки:")
        for r in failed:
            print(f"  {r['cell']}: {r['errors'][0][:200] if r['errors'] else '—'}")
    print("\nПринятые шаблоны:")
    print(f"{'код':<42} {'спец.':<10} {'грейд':<7} {'технологии':<28} {'формат':<12} название")
    for t in sorted(final_listing["templates"], key=lambda t: (SPECS.index(t["spec"]) if t["spec"] in SPECS else 99, GRADES.index(t["grade"]), t["code"])):
        print(f"{t['code']:<42} {t['spec']:<10} {t['grade']:<7} {', '.join(t['techs']):<28} {t['fmt']:<12} {t['title']}")
    print(f"\nВсего в generated: {len(final_listing['templates'])}. Реестр: {os.path.relpath(REGISTRY_MD, ROOT)}; "
          f"журнал: {os.path.relpath(RUN_LOG, ROOT)}; отклонённые: {os.path.relpath(REJECTED_DIR, ROOT)}/")
    print("\nЧтобы черновики попали в бой, добавьте в load_all() (backend/app/services/testing/bank/__init__.py) строку:\n"
          "    from . import generated  # noqa: F401\n"
          "Проверка черновиков: cd backend && ../.venv/bin/python -m pytest -q tests/test_generated_bank.py")


if __name__ == "__main__":
    main()
