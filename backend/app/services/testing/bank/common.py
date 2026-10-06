"""Шаблоны: общие для всех специализаций — SQL, алгоритмы и структуры данных, отладка, Git, HTTP, ООП, процессы.

Здесь же лежат помощники, которыми пользуются остальные модули банка (они импортируют их отсюда,
чтобы не менять base.py):
  _run_python  — исполнить сгенерированный фрагмент в изолированном словаре и вернуть stdout;
                 так ключ exact-заданий с кодом на Python всегда совпадает с настоящим выводом;
  _sql_eval    — выполнить показанный кандидату SQL-запрос через sqlite3 на сгенерированных таблицах;
  _sql_block   — отрисовать таблицы (комментариями) вместе с запросом в поле code;
  _choice / _multi — собрать экземпляр с перемешанными вариантами.
Правила: вся случайность — только из переданного rng; в выводе нет множеств и плавающих чисел;
ответы exact — скаляры или строки, склеенные через запятую/пробел.
"""
from __future__ import annotations
import contextlib
import io
import random
import sqlite3

from .base import template, Instance, shuffle_options

# ---------------------------------------------------------------------------------------------
# Помощники
# ---------------------------------------------------------------------------------------------

_NAMES = ["Анна", "Борис", "Вера", "Глеб", "Дарья", "Егор", "Инна", "Кирилл", "Лена", "Марат",
          "Нина", "Олег", "Полина", "Роман", "Света", "Тимур"]
_CITIES = ["Москва", "Казань", "Самара", "Тула", "Пермь", "Омск", "Уфа", "Сочи"]
_COLORS = ["red", "blue", "green", "orange", "purple", "teal", "gray", "navy"]


def _run_python(code: str) -> str:
    """Исполнить фрагмент и вернуть его stdout без крайних пробелов."""
    buf = io.StringIO()
    ns: dict = {"__name__": "__bank__"}
    with contextlib.redirect_stdout(buf):
        exec(code, ns)
    return buf.getvalue().strip()


def _sql_eval(tables: dict[str, tuple[list[str], list[tuple]]], query: str) -> list[tuple]:
    """tables: имя -> (колонки, строки). Возвращает строки результата запроса."""
    con = sqlite3.connect(":memory:")
    try:
        for name, (cols, rows) in tables.items():
            con.execute(f"CREATE TABLE {name} ({', '.join(cols)})")
            con.executemany(f"INSERT INTO {name} VALUES ({', '.join('?' * len(cols))})", rows)
        return con.execute(query).fetchall()
    finally:
        con.close()


def _cell(v) -> str:
    return "NULL" if v is None else str(v)


def _table_lines(name: str, cols: list[str], rows: list[tuple], prefix: str = "-- ") -> list[str]:
    grid = [list(cols)] + [[_cell(v) for v in r] for r in rows]
    widths = [max(len(row[i]) for row in grid) for i in range(len(cols))]
    out = [f"{prefix}{name}"]
    for row in grid:
        out.append(prefix + " | ".join(c.ljust(w) for c, w in zip(row, widths)).rstrip())
    return out


def _sql_block(tables: dict[str, tuple[list[str], list[tuple]]], query: str) -> str:
    """Таблицы как SQL-комментарии, затем запрос."""
    parts: list[str] = []
    for name, (cols, rows) in tables.items():
        parts.extend(_table_lines(name, cols, rows))
        parts.append("")
    parts.append(query)
    return "\n".join(parts)


def _choice(rng: random.Random, question: str, options: list[str], correct: int, explanation: str,
            code: str | None = None, language: str | None = None) -> Instance:
    assert len(options) >= 5 and len(set(options)) == len(options), options
    opts, ans = shuffle_options(rng, list(options), correct)
    return Instance(question=question, answer=ans, code=code, language=language, options=opts,
                    explanation=explanation)


def _multi(rng: random.Random, question: str, correct: list[str], wrong: list[str], explanation: str,
           code: str | None = None, language: str | None = None) -> Instance:
    options = list(correct) + list(wrong)
    assert 2 <= len(correct) <= 3 and 5 <= len(options) <= 6, options
    assert len(set(options)) == len(options), options
    opts, ans = shuffle_options(rng, options, list(range(len(correct))))
    return Instance(question=question, answer=ans, code=code, language=language, options=opts,
                    explanation=explanation)


def _near_numbers(rng: random.Random, correct: int, k: int, lo: int = 0) -> list[int]:
    """k различных чисел рядом с correct, не равных ему и не меньше lo."""
    out: list[int] = []
    spread = max(k + 2, abs(correct) // 2 + 2)
    while len(out) < k:
        cand = correct + rng.randint(-spread, spread)
        if cand != correct and cand >= lo and cand not in out:
            out.append(cand)
    return out


def _number_options(rng: random.Random, correct: int, extra: list[int] | None = None, k: int = 5) -> tuple[list[str], int]:
    """Варианты-числа: правильный + типичные ошибки (extra) + случайные соседи. Возвращает (варианты, индекс)."""
    pool: list[int] = []
    for e in extra or []:
        if e != correct and e >= 0 and e not in pool:
            pool.append(e)
    for n in _near_numbers(rng, correct, k + 3):
        if n not in pool:
            pool.append(n)
    wrong = pool[:k]
    options = [str(correct)] + [str(w) for w in wrong]
    return options, 0


# ---------------------------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------------------------

def _orders_table(rng: random.Random, n: int, cities: list[str]) -> list[tuple]:
    return [(i + 1, rng.choice(cities), rng.randrange(100, 1000, 50)) for i in range(n)]


@template("common_sql_count_rows", title="Сколько вернёт COUNT с условием", competency="SQL: фильтрация WHERE",
          specializations=[], technologies=["sql"], fmt="exact", grade_level="junior", difficulty_shift=-0.3)
def _sql_count_rows(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(6, 8)
        cities = rng.sample(_CITIES, 3)
        rows = _orders_table(rng, n, cities)
        city = rng.choice(cities)
        thr = rng.randrange(200, 900, 50)
        where = rng.choice([f"amount > {thr}", f"city = '{city}'", f"city = '{city}' AND amount >= {thr}",
                            f"city <> '{city}' AND amount < {thr}"])
        query = f"SELECT COUNT(*) FROM orders\nWHERE {where};"
        tables = {"orders": (["id", "city", "amount"], rows)}
        ans = _sql_eval(tables, query)[0][0]
        if 1 <= ans <= n - 1:
            break
    return Instance(question="Какое число вернёт запрос? Введите число.", answer=str(ans),
                    code=_sql_block(tables, query), language="sql",
                    explanation=f"Условию «{where}» удовлетворяют {ans} строк из {n}.")


@template("common_sql_distinct", title="DISTINCT и число различных значений", competency="SQL: DISTINCT",
          specializations=[], technologies=["sql"], fmt="exact", grade_level="junior", difficulty_shift=-0.1)
def _sql_distinct(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(6, 8)
        cities = rng.sample(_CITIES, rng.randint(4, 5))
        rows = _orders_table(rng, n, cities)
        tables = {"orders": (["id", "city", "amount"], rows)}
        if rng.random() < 0.5:
            query = "SELECT COUNT(DISTINCT city) FROM orders;"
            ans = _sql_eval(tables, query)[0][0]
            question = "Какое число вернёт запрос? Введите число."
            expl = f"В таблице {ans} различных значений city, повторы DISTINCT схлопывает."
        else:
            thr = rng.randrange(200, 800, 50)
            query = f"SELECT DISTINCT city FROM orders\nWHERE amount > {thr};"
            ans = len(_sql_eval(tables, query))
            question = "Сколько строк вернёт запрос? Введите число."
            expl = f"После фильтра amount > {thr} остаются строки, среди них {ans} разных городов."
        if 2 <= ans <= n - 1:
            break
    return Instance(question=question, answer=str(ans), code=_sql_block(tables, query), language="sql",
                    explanation=expl)


@template("common_sql_order_limit", title="ORDER BY и LIMIT", competency="SQL: сортировка и ограничение выборки",
          specializations=[], technologies=["sql"], fmt="exact", grade_level="junior", difficulty_shift=0.0)
def _sql_order_limit(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(6, 7)
        names = rng.sample(_NAMES, n)
        depts = rng.sample(["sales", "dev", "hr", "ops"], 2)
        salaries = rng.sample(range(50, 200, 5), n)
        rows = [(i + 1, names[i], rng.choice(depts), salaries[i] * 1000) for i in range(n)]
        tables = {"employees": (["id", "name", "dept", "salary"], rows)}
        direction = rng.choice(["ASC", "DESC"])
        if rng.random() < 0.5:
            query = f"SELECT name FROM employees\nORDER BY salary {direction}\nLIMIT 1;"
            dept = None
        else:
            dept = rng.choice(depts)
            query = f"SELECT name FROM employees\nWHERE dept = '{dept}'\nORDER BY salary {direction}\nLIMIT 1;"
            if sum(1 for r in rows if r[2] == dept) < 2:
                continue
        res = _sql_eval(tables, query)
        if res:
            break
    ans = res[0][0]
    word = "наименьшей" if direction == "ASC" else "наибольшей"
    scope = f" в отделе {dept}" if dept else ""
    return Instance(question="Какое имя вернёт запрос? Введите имя без кавычек.", answer=str(ans),
                    code=_sql_block(tables, query), language="sql",
                    explanation=f"ORDER BY salary {direction} ставит первой строку с {word} зарплатой{scope}; LIMIT 1 оставляет её одну.")


@template("common_sql_group_having", title="GROUP BY с HAVING", competency="SQL: группировка и фильтрация групп",
          specializations=[], technologies=["sql"], fmt="exact", grade_level="middle", difficulty_shift=-0.3)
def _sql_group_having(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(7, 8)
        cities = rng.sample(_CITIES, 4)
        rows = _orders_table(rng, n, cities)
        tables = {"orders": (["id", "city", "amount"], rows)}
        k = rng.randint(2, 3)
        if rng.random() < 0.5:
            query = f"SELECT city, COUNT(*) AS cnt\nFROM orders\nGROUP BY city\nHAVING COUNT(*) >= {k};"
            expl = f"Групп (городов) с числом заказов не меньше {k} —"
        else:
            thr = rng.randrange(600, 1600, 100)
            query = f"SELECT city, SUM(amount) AS total\nFROM orders\nGROUP BY city\nHAVING SUM(amount) > {thr};"
            expl = f"Групп (городов) с суммой заказов больше {thr} —"
        ans = len(_sql_eval(tables, query))
        groups = len({r[1] for r in rows})
        if 1 <= ans <= groups - 1:
            break
    return Instance(question="Сколько строк вернёт запрос? Введите число.", answer=str(ans),
                    code=_sql_block(tables, query), language="sql", explanation=f"{expl} {ans}; HAVING фильтрует уже группы, а не строки.")


@template("common_sql_left_join", title="LEFT JOIN: строки без пары и размножение строк", competency="SQL: соединения",
          specializations=[], technologies=["sql"], fmt="exact", grade_level="middle", difficulty_shift=0.0)
def _sql_left_join(rng: random.Random) -> Instance:
    while True:
        nu = rng.randint(4, 5)
        names = rng.sample(_NAMES, nu)
        users = [(i + 1, names[i]) for i in range(nu)]
        no = rng.randint(4, 6)
        orders = [(100 + j, rng.randint(1, nu), rng.randrange(100, 900, 100)) for j in range(no)]
        tables = {"users": (["id", "name"], users), "orders": (["id", "user_id", "amount"], orders)}
        kind = rng.randrange(2)
        if kind == 0:
            query = ("SELECT COUNT(*)\nFROM users u\nLEFT JOIN orders o ON o.user_id = u.id\n"
                     "WHERE o.id IS NULL;")
            expl = "LEFT JOIN сохраняет пользователей без заказов, у них поля заказа NULL; условие WHERE оставляет только их."
            lo, hi = 1, nu - 1
        else:
            query = "SELECT COUNT(*)\nFROM users u\nLEFT JOIN orders o ON o.user_id = u.id;"
            expl = "Каждый заказ даёт отдельную строку соединения, а пользователь без заказов — одну строку с NULL."
            lo, hi = no + 1, no + nu
        ans = _sql_eval(tables, query)[0][0]
        if lo <= ans <= hi:
            break
    return Instance(question="Какое число вернёт запрос? Введите число.", answer=str(ans),
                    code=_sql_block(tables, query), language="sql", explanation=expl)


@template("common_sql_null_semantics", title="NULL в условиях и агрегатах", competency="SQL: трёхзначная логика NULL",
          specializations=[], technologies=["sql"], fmt="exact", grade_level="middle", difficulty_shift=0.2)
def _sql_null_semantics(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(6, 8)
        names = rng.sample(_NAMES, n)
        rows = []
        for i in range(n):
            score = None if rng.random() < 0.3 else rng.randint(1, 10)
            rows.append((i + 1, names[i], score))
        nulls = sum(1 for r in rows if r[2] is None)
        if not 1 <= nulls <= n - 2:
            continue
        tables = {"results": (["id", "student", "score"], rows)}
        x = rng.randint(3, 8)
        kind = rng.randrange(4)
        if kind == 0:
            query = f"SELECT COUNT(*) FROM results\nWHERE score <> {x};"
            expl = f"Сравнение NULL <> {x} даёт NULL, а не TRUE, поэтому строки с NULL в выборку не попадают."
        elif kind == 1:
            query = f"SELECT COUNT(*) FROM results\nWHERE score < {x} OR score IS NULL;"
            expl = "Строки с NULL добавляются только явным условием IS NULL."
        elif kind == 2:
            query = "SELECT COUNT(score) FROM results;"
            expl = "COUNT(столбец) считает только непустые значения, в отличие от COUNT(*)."
        else:
            query = f"SELECT COUNT(*) FROM results\nWHERE NOT (score > {x});"
            expl = f"NOT (NULL > {x}) тоже NULL — строки с NULL отсеиваются, хотя интуитивно кажется иначе."
        ans = _sql_eval(tables, query)[0][0]
        if 1 <= ans <= n - 1:
            break
    return Instance(question="Какое число вернёт запрос? Введите число.", answer=str(ans),
                    code=_sql_block(tables, query), language="sql", explanation=expl)


@template("common_sql_index_choice", title="Какой индекс ускорит запрос", competency="SQL: индексы",
          specializations=[], technologies=["sql", "postgresql"], fmt="choice", grade_level="senior", difficulty_shift=-0.2)
def _sql_index_choice(rng: random.Random) -> Instance:
    t = rng.choice(["orders", "events", "payments", "tickets"])
    eq, rngc, other = rng.sample(["status", "customer_id", "region", "type"], 3)
    rc = rng.choice(["created_at", "amount", "updated_at"])
    if rng.random() < 0.6:
        query = f"SELECT *\nFROM {t}\nWHERE {eq} = $1 AND {rc} > $2\nORDER BY {rc};"
        options = [f"CREATE INDEX ON {t} ({eq}, {rc});", f"CREATE INDEX ON {t} ({rc}, {eq});",
                   f"CREATE INDEX ON {t} ({other});", f"CREATE INDEX ON {t} ({rc});",
                   f"CREATE INDEX ON {t} ({eq}, {other});", f"CREATE INDEX ON {t} ({other}, {rc}, {eq});"]
        expl = (f"Составной индекс ({eq}, {rc}): сначала колонка с равенством, затем диапазон — он же даёт порядок "
                f"для ORDER BY {rc}. При обратном порядке колонок диапазон по {rc} идёт первым и равенство по {eq} "
                "не сужает поиск.")
        return _choice(rng, "Запрос медленный, таблица большая. Какой индекс поможет ему сильнее всего?",
                       options, 0, expl, code=query, language="sql")
    col = rng.choice(["email", "login", "sku"])
    query = f"SELECT id\nFROM {t}\nWHERE lower({col}) = lower($1);"
    options = [f"CREATE INDEX ON {t} (lower({col}));", f"CREATE INDEX ON {t} ({col});",
               f"CREATE INDEX ON {t} ({col}, id);", f"CREATE INDEX ON {t} (id);",
               f"CREATE INDEX ON {t} ({other});", f"CREATE UNIQUE INDEX ON {t} (id, {col});"]
    expl = (f"Условие наложено на выражение lower({col}), а не на столбец; обычный индекс по {col} планировщик "
            "использовать не сможет — нужен функциональный индекс по тому же выражению.")
    return _choice(rng, "Запрос медленный, таблица большая. Какой индекс поможет ему сильнее всего?",
                   options, 0, expl, code=query, language="sql")


# ---------------------------------------------------------------------------------------------
# Алгоритмы и структуры данных
# ---------------------------------------------------------------------------------------------

_COMPLEXITY = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)", "O(n³)"]


@template("common_algo_complexity", title="Оценить сложность фрагмента", competency="Алгоритмы: оценка сложности",
          specializations=[], technologies=["algorithms", "python"], fmt="choice", grade_level="junior", difficulty_shift=0.2)
def _algo_complexity(rng: random.Random) -> Instance:
    v = rng.choice(["total", "acc", "count", "steps"])
    i, j, k = rng.choice([("i", "j", "k"), ("a", "b", "c"), ("x", "y", "z")])
    snippets = [
        (f"{v} = 0\nfor {i} in range(n):\n    {v} += {i}", 2),
        (f"{v} = 0\nfor {i} in range(n):\n    for {j} in range(n):\n        {v} += {i} * {j}", 4),
        (f"{v} = 0\n{i} = n\nwhile {i} > 1:\n    {i} //= 2\n    {v} += 1", 1),
        (f"{v} = 0\nfor {i} in range(n):\n    {j} = n\n    while {j} > 1:\n        {j} //= 2\n        {v} += 1", 3),
        (f"{v} = n * (n + 1) // 2", 0),
        (f"{v} = 0\nfor {i} in range(n):\n    for {j} in range(n):\n        for {k} in range(n):\n            {v} += 1", 5),
        (f"{v} = 0\nfor {i} in range(n):\n    {v} += {i}\nfor {j} in range(n):\n    {v} -= {j}", 2),
    ]
    code, correct = rng.choice(snippets)
    return _choice(rng, "Какова временная сложность фрагмента относительно n? Выберите один вариант.",
                   list(_COMPLEXITY), correct,
                   f"Число операций растёт как {_COMPLEXITY[correct]}: учитываем вложенность циклов и деление пополам.",
                   code=code, language="python")


@template("common_algo_stack_queue", title="Стек и очередь: что останется", competency="Структуры данных: стек и очередь",
          specializations=[], technologies=["algorithms", "python"], fmt="exact", grade_level="junior", difficulty_shift=-0.2)
def _algo_stack_queue(rng: random.Random) -> Instance:
    while True:
        is_stack = rng.random() < 0.5
        name = "stack" if is_stack else "queue"
        lines = ["from collections import deque", f"{name} = deque()"] if not is_stack else [f"{name} = []"]
        size = 0
        values = rng.sample(range(1, 30), 6)
        vi = 0
        for _ in range(rng.randint(5, 7)):
            if size >= 1 and rng.random() < 0.4:
                lines.append(f"{name}.pop()" if is_stack else f"{name}.popleft()")
                size -= 1
            else:
                lines.append(f"{name}.append({values[vi]})")
                vi += 1
                size += 1
                if vi >= len(values):
                    break
        if size < 2:
            continue
        lines.append(f"print(*{name})")
        code = "\n".join(lines)
        ans = _run_python(code)
        break
    kind = "стеке (pop снимает последний добавленный)" if is_stack else "очереди (popleft снимает первый добавленный)"
    return Instance(question="Что выведет код? Введите значения через пробел.", answer=ans, code=code, language="python",
                    explanation=f"Речь о {kind}; после всех операций остаются элементы: {ans}.")


@template("common_algo_structure_choice", title="Выбрать структуру данных", competency="Структуры данных: выбор под задачу",
          specializations=[], technologies=["algorithms"], fmt="choice", grade_level="junior", difficulty_shift=0.0)
def _algo_structure_choice(rng: random.Random) -> Instance:
    obj, one = rng.choice([("заказы", "заказ"), ("сообщения", "сообщение"), ("задачи", "задачу"), ("события", "событие")])
    cases = [
        (f"Нужно за O(1) в среднем находить {one} по идентификатору.", "Хеш-таблица (dict)",
         "Поиск по ключу за O(1) в среднем даёт хеш-таблица."),
        (f"{obj.capitalize()} обрабатываются строго в порядке поступления: первым пришёл — первым обработан.", "Очередь (deque)",
         "Порядок FIFO — это очередь."),
        ("Нужна отмена последнего действия: откатываем операции в обратном порядке.", "Стек",
         "Порядок LIFO — это стек."),
        (f"Нужно хранить {obj} упорядоченно по времени и быстро находить ближайшие к заданному моменту.", "Сбалансированное дерево поиска",
         "Упорядоченное хранение с поиском соседей за O(log n) — сбалансированное дерево."),
        (f"Нужно проверять, встречался ли идентификатор раньше, дубли не нужны.", "Множество (set)",
         "Принадлежность без дублей — множество."),
        (f"Нужно постоянно извлекать {one} с наивысшим приоритетом.", "Куча (приоритетная очередь)",
         "Быстрое извлечение максимума/минимума — двоичная куча."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    options = [c[1] for c in cases]
    return _choice(rng, f"{text} Какая структура данных подходит лучше всего?", options, idx, expl)


@template("common_algo_binary_search_steps", title="Сколько итераций сделает бинарный поиск", competency="Алгоритмы: бинарный поиск",
          specializations=[], technologies=["algorithms", "python"], fmt="exact", grade_level="middle", difficulty_shift=0.0)
def _algo_binary_search(rng: random.Random) -> Instance:
    n = rng.randint(7, 10)
    xs = sorted(rng.sample(range(1, 60), n))
    target = rng.choice(xs)
    fn = rng.choice(["search", "find", "locate"])
    code = (f"def {fn}(xs, target):\n"
            "    lo, hi, steps = 0, len(xs) - 1, 0\n"
            "    while lo <= hi:\n"
            "        steps += 1\n"
            "        mid = (lo + hi) // 2\n"
            "        if xs[mid] == target:\n"
            "            return steps\n"
            "        if xs[mid] < target:\n"
            "            lo = mid + 1\n"
            "        else:\n"
            "            hi = mid - 1\n"
            "    return 0\n\n"
            f"xs = {xs}\n"
            f"print({fn}(xs, {target}))")
    ans = _run_python(code)
    return Instance(question="Что выведет код? Введите число.", answer=ans, code=code, language="python",
                    explanation=f"На каждой итерации проверяется середина: {target} найден за {ans} шаг(а/ов).")


@template("common_algo_recursion", title="Вычислить рекурсивную функцию", competency="Алгоритмы: рекурсия",
          specializations=[], technologies=["algorithms", "python"], fmt="exact", grade_level="middle", difficulty_shift=-0.2)
def _algo_recursion(rng: random.Random) -> Instance:
    fn = rng.choice(["f", "g", "calc"])
    kind = rng.randrange(4)
    if kind == 0:
        n = rng.randint(5, 9)
        code = f"def {fn}(n):\n    if n < 2:\n        return n\n    return {fn}(n - 1) + {fn}(n - 2)\n\nprint({fn}({n}))"
        expl = "Это числа Фибоначчи: каждое значение — сумма двух предыдущих."
    elif kind == 1:
        n = rng.randint(1000, 9999)
        code = f"def {fn}(n):\n    if n == 0:\n        return 0\n    return n % 10 + {fn}(n // 10)\n\nprint({fn}({n}))"
        expl = "Функция складывает цифры числа: последняя цифра плюс результат для числа без неё."
    elif kind == 2:
        n = rng.randint(3, 6)
        code = f"def {fn}(n):\n    if n == 0:\n        return 1\n    return 2 * {fn}(n - 1) + 1\n\nprint({fn}({n}))"
        expl = "Рекуррентность даёт 2^n − 1 (как число ходов в ханойской башне)."
    else:
        n = rng.randint(4, 7)
        code = f"def {fn}(n):\n    if n <= 1:\n        return 1\n    return n * {fn}(n - 2)\n\nprint({fn}({n}))"
        expl = "Шаг рекурсии уменьшает n на 2: перемножаются числа одной чётности с n."
    ans = _run_python(code)
    return Instance(question="Что выведет код? Введите число.", answer=ans, code=code, language="python", explanation=expl)


@template("common_algo_sort_stability", title="Устойчивость сортировки", competency="Алгоритмы: сортировка по ключу",
          specializations=[], technologies=["algorithms", "python"], fmt="exact", grade_level="senior", difficulty_shift=-0.3)
def _algo_sort_stability(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(5, 6)
        names = rng.sample(_NAMES, n)
        grades = [rng.randint(1, 3) for _ in range(n)]
        if len(set(grades)) < 2 or len(set(grades)) == n:
            continue
        break
    people = ", ".join(f'("{nm}", {g})' for nm, g in zip(names, grades))
    reverse = rng.random() < 0.5
    rev = ", reverse=True" if reverse else ""
    code = (f"people = [{people}]\n"
            f"people.sort(key=lambda p: p[1]{rev})\n"
            'print(" ".join(p[0] for p in people))')
    ans = _run_python(code)
    expl = ("Сортировка в Python устойчива: элементы с равным ключом сохраняют исходный порядок"
            + (", и reverse=True этого не нарушает (переворачивается порядок ключей, а не равных элементов)." if reverse else "."))
    return Instance(question="Что выведет код? Введите имена через пробел.", answer=ans, code=code, language="python",
                    explanation=expl)


# ---------------------------------------------------------------------------------------------
# Отладка
# ---------------------------------------------------------------------------------------------

@template("common_debug_exception_type", title="Какое исключение возникнет", competency="Отладка: чтение ошибок",
          specializations=[], technologies=["python"], fmt="exact", grade_level="junior", difficulty_shift=0.0)
def _debug_exception(rng: random.Random) -> Instance:
    a, b = rng.randint(2, 9), rng.randint(10, 99)
    key = rng.choice(["x", "y", "z"])
    missing = rng.choice(["w", "q", "k"])
    cases = [
        (f'd = {{"{key}": {a}}}\nprint(d["{missing}"])', "Обращение к отсутствующему ключу словаря даёт KeyError."),
        (f"xs = [{a}, {b}, {a + b}]\nprint(xs[{rng.randint(3, 5)}])", "Индекс за пределами списка даёт IndexError."),
        (f'print("{a}" + {b})', "Сложение строки и числа без приведения типов даёт TypeError."),
        (f"a = {a}\nb = a - {a}\nprint({b} // b)", "Делитель равен нулю — ZeroDivisionError."),
        (f'print(int("{a}{b}x"))', "Строка не является записью числа — ValueError."),
        (f's = "abc"\ns.push("{key}")\nprint(s)', "У строки нет метода push — AttributeError."),
        (f"print(len({b}))", "У int нет длины — len вызывает TypeError."),
    ]
    body, expl = rng.choice(cases)
    indented = "\n".join("    " + ln for ln in body.splitlines())
    code = f"try:\n{indented}\nexcept Exception as e:\n    print(type(e).__name__)"
    ans = _run_python(code)
    return Instance(question="Что выведет код? Введите имя класса исключения.", answer=ans, code=code, language="python",
                    explanation=expl)


# ---------------------------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------------------------

@template("common_git_command", title="Подобрать команду Git", competency="Git: повседневные команды",
          specializations=[], technologies=["git"], fmt="choice", grade_level="junior", difficulty_shift=-0.2)
def _git_command(rng: random.Random) -> Instance:
    br = rng.choice(["feature/login", "fix/payment", "feature/search", "hotfix/timeout"])
    f = rng.choice(["config.py", "README.md", "app.js", "styles.css"])
    cases = [
        ("Отменить последний коммит, оставив его изменения в рабочей копии и индексе.", "git reset --soft HEAD~1",
         "reset --soft сдвигает ветку на коммит назад, не трогая файлы."),
        ("Посмотреть, какие файлы изменены и какие из них ещё не добавлены в индекс.", "git status",
         "Состояние рабочей копии и индекса показывает git status."),
        (f"Создать ветку {br} и сразу переключиться на неё.", f"git switch -c {br}",
         "switch -c (или checkout -b) создаёт ветку и переключается."),
        ("Скачать новые коммиты с сервера, не сливая их в текущую ветку.", "git fetch",
         "fetch только обновляет удалённые ветки; pull ещё и сливает."),
        ("Временно убрать незакоммиченные изменения, чтобы переключиться на другую ветку.", "git stash",
         "stash прячет изменения в отдельное хранилище."),
        (f"Вернуть файл {f} к состоянию последнего коммита, отбросив локальные правки.", f"git restore {f}",
         "restore возвращает файл из HEAD (старый вариант: checkout -- файл)."),
        ("Показать историю коммитов текущей ветки.", "git log",
         "История коммитов — git log."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    pool = [c[1] for c in cases] + ["git commit --amend", "git rebase -i HEAD~3", "git clean -fd", "git pull --rebase"]
    wrong = [c for c in pool if c != correct]
    options = [correct] + rng.sample(wrong, 5)
    return _choice(rng, f"{text} Какая команда это делает?", options, 0, expl)


@template("common_git_rebase_merge", title="Rebase против merge", competency="Git: история и слияния",
          specializations=[], technologies=["git"], fmt="multichoice", grade_level="middle", difficulty_shift=0.0)
def _git_rebase_merge(rng: random.Random) -> Instance:
    f = rng.choice(["feature/cart", "feature/export", "fix/locale", "feature/notify"])
    true_pool = [
        f"`git rebase main` в ветке {f} переписывает её коммиты поверх вершины main — их хеши меняются.",
        f"`git merge {f}` в main при разошедшихся историях создаёт отдельный коммит слияния.",
        f"После rebase уже опубликованной ветки {f} отправить её получится только с `--force-with-lease`.",
        f"`git merge --ff-only {f}` завершится ошибкой, если main ушёл вперёд относительно {f}.",
    ]
    false_pool = [
        f"`git rebase main` создаёт коммит слияния в ветке {f}.",
        f"`git merge {f}` меняет хеши уже существующих коммитов ветки {f}.",
        "После `git rebase` история становится нелинейной, с ветвлениями.",
        "Делать `git rebase` на общей ветке main, с которой работают другие, безопасно.",
    ]
    k = rng.randint(2, 3)
    correct = rng.sample(true_pool, k)
    wrong = rng.sample(false_pool, 6 - k)
    return _multi(rng, "Какие утверждения о rebase и merge верны? Выберите все подходящие.", correct, wrong,
                  "Rebase переписывает коммиты (новые хеши, линейная история, force-push после публикации); "
                  "merge сохраняет хеши и добавляет коммит слияния.")


# ---------------------------------------------------------------------------------------------
# HTTP и REST
# ---------------------------------------------------------------------------------------------

@template("common_http_status", title="Код ответа по ситуации", competency="HTTP: коды состояния",
          specializations=[], technologies=["http"], fmt="choice", grade_level="junior", difficulty_shift=-0.3)
def _http_status(rng: random.Random) -> Instance:
    res = rng.choice(["заказ", "проект", "документ", "профиль"])
    cases = [
        (f"Клиент отправил POST, {res} успешно создан.", "201", "Успешное создание ресурса — 201 Created."),
        ("Запрос пришёл без действительного токена авторизации.", "401", "Нет или недействительна аутентификация — 401."),
        ("Токен действителен, но у пользователя нет прав на операцию.", "403", "Аутентифицирован, но запрещено — 403."),
        (f"Запрошенный {res} не существует.", "404", "Ресурс не найден — 404."),
        (f"{res.capitalize()} удалён, тело ответа пустое.", "204", "Успех без тела — 204 No Content."),
        (f"Обновление {res}а отклонено: версия на сервере новее присланной.", "409", "Конфликт состояния ресурса — 409 Conflict."),
        ("Сервис временно перегружен и просит повторить позже.", "503", "Временная недоступность — 503."),
        ("Тело запроса синтаксически некорректно (невалидный JSON).", "400", "Ошибка в самом запросе — 400 Bad Request."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    pool = ["200", "201", "204", "301", "400", "401", "403", "404", "409", "422", "500", "503"]
    wrong = [c for c in pool if c != correct]
    options = [correct] + rng.sample(wrong, 5)
    return _choice(rng, f"{text} Какой код ответа уместен?", options, 0, expl)


@template("common_http_idempotent_retry", title="Какие запросы можно безопасно повторить", competency="HTTP: идемпотентность методов",
          specializations=[], technologies=["http", "rest"], fmt="multichoice", grade_level="middle", difficulty_shift=-0.1)
def _http_idempotent(rng: random.Random) -> Instance:
    uid = rng.randint(3, 99)
    amt = rng.choice([500, 1200, 2500, 9900])
    idem = [f"GET /users/{uid}", f"PUT /users/{uid} (полная замена профиля)", f"DELETE /users/{uid}", f"HEAD /files/{uid}"]
    non = [f"POST /orders (создание заказа)", f"POST /payments (списание {amt} ₽)", f'PATCH /counters/{uid} {{"inc": 1}}',
           "POST /emails/send"]
    k = rng.randint(2, 3)
    correct = rng.sample(idem, k)
    wrong = rng.sample(non, 6 - k)
    return _multi(rng, "Клиент получил таймаут и не знает, выполнился ли запрос. Какие из запросов можно безопасно "
                       "повторить, потому что они идемпотентны? Выберите все подходящие.", correct, wrong,
                  "GET, HEAD, PUT и DELETE идемпотентны: повтор не меняет итоговое состояние. POST создаёт новый ресурс "
                  "или списание, PATCH с инкрементом меняет значение при каждом вызове.")


@template("common_http_caching", title="Заголовки кеширования", competency="HTTP: кеширование",
          specializations=[], technologies=["http"], fmt="choice", grade_level="senior", difficulty_shift=0.0)
def _http_caching(rng: random.Random) -> Instance:
    age = rng.choice([600, 3600, 86400])
    cases = [
        ("Клиент повторно запрашивает ресурс; сервер хочет ответить «не изменилось» без тела.",
         "Отдавать ETag, клиент шлёт If-None-Match, сервер отвечает 304 Not Modified",
         "Условный запрос по ETag позволяет вернуть 304 без тела."),
        ("Ответ содержит персональные данные и не должен сохраняться ни в одном кеше.",
         "Cache-Control: no-store", "no-store запрещает сохранять ответ где бы то ни было."),
        ("Статический файл с хешем содержимого в имени; можно кешировать год и не перепроверять.",
         "Cache-Control: public, max-age=31536000, immutable", "Хеш в имени делает файл неизменяемым — долгий max-age и immutable."),
        (f"Ответ можно кешировать только в браузере пользователя ({age} с), но не на CDN и прокси.",
         f"Cache-Control: private, max-age={age}", "private разрешает кеш только клиенту, запрещая общие кеши."),
        ("Браузер может хранить ответ, но перед каждым использованием обязан проверить свежесть у сервера.",
         "Cache-Control: no-cache", "no-cache не запрещает хранение, а требует ревалидации перед использованием."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    pool = [c[1] for c in cases] + ["Expires: 0 и удалить ETag", "Pragma: public"]
    wrong = [c for c in pool if c != correct]
    options = [correct] + rng.sample(wrong, 5)
    return _choice(rng, f"{text} Какое решение правильное?", options, 0, expl)


# ---------------------------------------------------------------------------------------------
# ООП и проектирование
# ---------------------------------------------------------------------------------------------

@template("common_oop_solid", title="Какой принцип SOLID нарушен", competency="ООП: принципы проектирования",
          specializations=[], technologies=["oop"], fmt="choice", grade_level="middle", difficulty_shift=0.0)
def _oop_solid(rng: random.Random) -> Instance:
    c = rng.choice(["Order", "Invoice", "Report", "Booking", "Shipment"])
    cases = [
        (f"Класс {c} одновременно считает скидки, пишет в базу и формирует PDF.", "Единственная ответственность (SRP)",
         "У класса несколько причин для изменения — нарушен SRP."),
        (f"Чтобы добавить новый способ оплаты, приходится править цепочку if/elif внутри {c}Service.", "Открытость/закрытость (OCP)",
         "Расширение требует изменения существующего кода — нарушен OCP."),
        (f"Подкласс ReadOnly{c} бросает исключение в методе save(), который у родителя работает.", "Подстановка Лисков (LSP)",
         "Наследник ломает контракт родителя — клиенты не могут подставить его вместо базового класса."),
        (f"Интерфейс {c}Repository содержит двенадцать методов, а большинству реализаций нужны три.", "Разделение интерфейсов (ISP)",
         "Клиентов заставляют зависеть от ненужных методов — нарушен ISP."),
        (f"{c}Service создаёт внутри себя PostgresRepository() напрямую, и подменить хранилище в тестах нельзя.", "Инверсия зависимостей (DIP)",
         "Высокоуровневый модуль зависит от конкретной реализации, а не от абстракции — нарушен DIP."),
        ("Одна и та же проверка формата e-mail скопирована в пять классов.", "Не повторяйся (DRY)",
         "Дублирование логики — нарушение DRY (не входит в SOLID, но проверяется так же)."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    options = [k[1] for k in cases]
    return _choice(rng, f"{text} Какой принцип здесь нарушен?", options, idx, expl)


@template("common_oop_pattern", title="Узнать паттерн по ситуации", competency="ООП: паттерны проектирования",
          specializations=[], technologies=["oop"], fmt="choice", grade_level="middle", difficulty_shift=0.2)
def _oop_pattern(rng: random.Random) -> Instance:
    thing = rng.choice(["Notifier", "Exporter", "PriceCalculator", "Connection", "Parser"])
    cases = [
        (f"Нужен ровно один экземпляр {thing} на процесс и общая точка доступа к нему.", "Одиночка (Singleton)",
         "Один экземпляр с глобальной точкой доступа — Singleton."),
        (f"Какой именно {thing} создать, решает подкласс; базовый класс работает с результатом через общий интерфейс.", "Фабричный метод (Factory Method)",
         "Создание делегируется подклассам — Factory Method."),
        (f"Алгоритм внутри {thing} выбирается во время выполнения и подменяется без изменения клиента.", "Стратегия (Strategy)",
         "Взаимозаменяемые алгоритмы за общим интерфейсом — Strategy."),
        (f"При изменении состояния {thing} нужно уведомлять заранее неизвестное число подписчиков.", "Наблюдатель (Observer)",
         "Подписка на события объекта — Observer."),
        (f"К {thing} нужно добавить логирование и кеширование, оборачивая объект, без наследования и правок класса.", "Декоратор (Decorator)",
         "Динамическое добавление обязанностей через обёртку — Decorator."),
        (f"Сторонняя библиотека возвращает объект с другим интерфейсом, чем ожидает наш код вокруг {thing}.", "Адаптер (Adapter)",
         "Приведение интерфейса к ожидаемому — Adapter."),
        (f"{thing} собирается пошагово из множества необязательных частей, и конструкторов с десятком аргументов хочется избежать.", "Строитель (Builder)",
         "Пошаговая сборка сложного объекта — Builder."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    wrong = [k[1] for k in cases if k[1] != correct]
    options = [correct] + rng.sample(wrong, 5)
    return _choice(rng, f"{text} Какой паттерн описан?", options, 0, expl)


@template("common_oop_mro_output", title="Порядок разрешения методов (MRO)", competency="ООП: множественное наследование",
          specializations=[], technologies=["oop", "python"], fmt="exact", grade_level="senior", difficulty_shift=0.1)
def _oop_mro(rng: random.Random) -> Instance:
    letters = rng.sample(["A", "B", "C", "D", "K", "M", "P", "S"], 4)
    base, left, right, top = letters
    m = rng.choice(["who", "tag", "name"])
    bases = [left, right]
    if rng.random() < 0.5:
        bases.reverse()
    # у одного из средних классов иногда нет вызова super() — цепочка обрывается
    skip = rng.choice([None, None, left, right])

    def body(cls: str, parent_call: bool) -> str:
        if parent_call:
            return f'class {cls}({base}):\n    def {m}(self):\n        return "{cls}" + super().{m}()\n'
        return f'class {cls}({base}):\n    def {m}(self):\n        return "{cls}"\n'

    code = (f'class {base}:\n    def {m}(self):\n        return "{base}"\n\n'
            + body(left, skip != left) + "\n"
            + body(right, skip != right) + "\n"
            + f'class {top}({", ".join(bases)}):\n    def {m}(self):\n        return "{top}" + super().{m}()\n\n'
            + f"print({top}().{m}())")
    ans = _run_python(code)
    expl = (f"MRO для {top}: {top} → {bases[0]} → {bases[1]} → {base}; super() идёт по этому порядку, а не к «родителю» класса"
            + (f". Класс {skip} не вызывает super(), поэтому цепочка на нём обрывается." if skip else "."))
    return Instance(question="Что выведет код? Введите строку без кавычек.", answer=ans, code=code, language="python",
                    explanation=expl)


@template("common_design_cache_tradeoff", title="Кеш и устаревание данных", competency="Проектирование: кеширование",
          specializations=[], technologies=["system_design", "redis"], fmt="choice", grade_level="senior", difficulty_shift=0.2)
def _design_cache(rng: random.Random) -> Instance:
    ent = rng.choice(["цены товаров", "права пользователей", "остатки на складе"])
    ttl = rng.choice([5, 15, 60])
    rps = rng.choice([2000, 5000, 10000])
    kinds = [
        (f"Сервис кеширует {ent} в Redis с TTL {ttl} мин. Бизнес жалуется: после изменения в админке старое значение "
         f"живёт до {ttl} минут. Нагрузка {rps} запросов/с, база такое без кеша не выдержит.",
         "При изменении записи явно инвалидировать (удалять) ключ в кеше, оставив TTL как страховку",
         "Инвалидация по событию убирает окно устаревания, а TTL остаётся защитой от пропущенных событий. Снять кеш нельзя — "
         "база не выдержит; уменьшать TTL до секунд — почти то же, что снять."),
        (f"При рестарте сервиса кеш {ent} пуст, и первые секунды все {rps} запросов/с идут в базу, она падает.",
         "Прогревать кеш при старте и/или защищать базу от лавины одинаковых запросов (single-flight, запрос-лидер)",
         "Проблема «холодного старта» решается прогревом и дедупликацией одновременных промахов, а не увеличением TTL."),
    ]
    idx = rng.randrange(len(kinds))
    text, correct, expl = kinds[idx]
    distractors = [
        "Убрать кеш совсем, чтобы данные всегда были свежими",
        f"Уменьшить TTL до 1 секунды",
        "Перенести кеш в память каждого экземпляра сервиса без синхронизации",
        "Кешировать дольше (сутки), чтобы снизить нагрузку на базу",
        "Перейти с Redis на другую СУБД",
        "Добавить ещё один слой кеша перед Redis с тем же TTL",
    ]
    options = [correct] + rng.sample(distractors, 5)
    return _choice(rng, f"{text} Какое решение разумнее всего?", options, 0, expl)


# ---------------------------------------------------------------------------------------------
# Lead: процессы, код-ревью, технический долг
# ---------------------------------------------------------------------------------------------

@template("common_lead_code_review", title="Решение на код-ревью", competency="Лидерство: код-ревью и качество",
          specializations=[], technologies=["mentoring", "git"], fmt="choice", grade_level="lead", difficulty_shift=-0.2)
def _lead_code_review(rng: random.Random) -> Instance:
    who = rng.choice(["Марата", "Полины", "Глеба", "Инны"])
    files, lines = rng.choice([(38, 2100), (52, 3400), (27, 1800), (64, 4200)])
    mod = rng.choice(["billing", "auth", "export", "scheduler"])
    days = rng.randint(2, 4)
    scenarios = [
        (f"PR от {who}: {files} файлов, {lines} строк — рефакторинг модуля {mod} и новая функция в одном наборе коммитов. "
         f"Релиз через {days} дня, тесты зелёные.",
         "Попросить разделить PR: рефакторинг и новая функциональность отдельно, ревьюить по частям",
         "Большой смешанный PR невозможно проверить осмысленно; разделение снижает риск и ускоряет ревью, даже с учётом срока.",
         ["Одобрить, раз тесты зелёные и релиз скоро", "Отклонить PR целиком и попросить переписать с нуля",
          "Проверить только новую функцию, рефакторинг пропустить", "Слить сейчас, а разбираться после релиза",
          "Переписать спорные места самому и слить"]),
        (f"PR от джуниора {who}: код работает и покрыт тестами, но написан не в принятом в команде стиле и с лишними "
         f"уровнями вложенности в модуле {mod}.",
         "Оставить комментарии с объяснением, почему так принято, и предложить вариант, дав автору исправить самому",
         "Ревью — инструмент обучения: объяснение и самостоятельное исправление растят автора; переписывание за него — нет.",
         ["Переписать код самому и слить, чтобы не тратить время", "Одобрить без замечаний — работает же",
          "Отклонить без комментариев со ссылкой на стайлгайд", "Поставить задачу другому разработчику переделать",
          "Слить и завести тикет на будущее переписывание"]),
        (f"В PR от {who} по модулю {mod} среди {files} файлов есть изменение поведения: пустой список теперь трактуется как "
         f"«все элементы». Тестов на это нет, в описании PR изменение не упомянуто.",
         "Запросить тест на новое поведение и явное описание изменения в PR; обсудить, нужно ли оно вообще",
         "Незадокументированное изменение поведения без тестов — главный риск PR; его нужно сделать явным и покрыть тестом.",
         ["Одобрить: остальные изменения хорошие", "Самому дописать тест и слить", "Отклонить весь PR без объяснений",
          "Слить, а поведение обсудить на ретро", "Попросить убрать все остальные изменения и оставить только это"]),
    ]
    idx = rng.randrange(len(scenarios))
    text, correct, expl, wrong = scenarios[idx]
    return _choice(rng, f"{text} Что сделать ревьюеру?", [correct] + wrong, 0, expl)


@template("common_lead_postmortem", title="Разбор инцидента", competency="Лидерство: процессы после инцидента",
          specializations=[], technologies=["agile", "system_design"], fmt="multichoice", grade_level="lead", difficulty_shift=0.0)
def _lead_postmortem(rng: random.Random) -> Instance:
    svc = rng.choice(["оплаты", "авторизации", "поиска", "уведомлений"])
    mins = rng.choice([25, 40, 90, 140])
    true_pool = [
        "Провести разбор без поиска виноватых: искать системные причины, а не ошибку конкретного человека",
        "Восстановить хронологию: когда проблема началась, когда заметили, когда начали чинить, когда восстановили",
        "У каждого корректирующего действия — владелец и срок, выполнение отслеживается",
        "Зафиксировать, как инцидент обнаружили, и улучшить мониторинг и алерты, если заметили поздно",
    ]
    false_pool = [
        "Определить виновного инженера и зафиксировать это в документе разбора",
        "Не проводить разбор, если клиенты не успели заметить сбой",
        "Закрыть разбор сразу после восстановления сервиса, без плана действий",
        "Ограничить участников разработчиками, не звать дежурных и поддержку",
    ]
    k = rng.randint(2, 3)
    return _multi(rng, f"Сервис {svc} лежал {mins} минут. Какие практики уместны в разборе инцидента (постмортеме)? "
                       "Выберите все подходящие.", rng.sample(true_pool, k), rng.sample(false_pool, 6 - k),
                  "Хороший постмортем — безвинный, с хронологией, конкретными действиями с владельцами и улучшением обнаружения.")


@template("common_lead_tech_debt", title="Технический долг и поставка", competency="Лидерство: приоритизация долга",
          specializations=[], technologies=["agile", "system_design"], fmt="choice", grade_level="lead", difficulty_shift=0.2)
def _lead_tech_debt(rng: random.Random) -> Instance:
    pct = rng.choice([30, 40, 50])
    n = rng.choice([4, 6, 8])
    team = rng.choice(["платежей", "каталога", "CRM", "личного кабинета"])
    text = (f"Команда {team}: около {pct} % времени спринта уходит на починку старых модулей, бизнес ждёт {n} новых "
            f"функций в квартал и не хочет слышать про «рефакторинг».")
    correct = ("Выделить фиксированную долю ёмкости на долг, выбирать его по влиянию на поставку и показывать бизнесу "
               "эффект метриками (время цикла, число инцидентов)")
    wrong = [
        "Остановить разработку функций на квартал и переписать проблемные модули целиком",
        "Не трогать долг, пока что-то не сломается всерьёз",
        "Переписать систему с нуля на новом стеке",
        "Поручить весь долг одному инженеру, остальные делают функции",
        "Закрывать долг переработками по вечерам, не меняя план",
    ]
    return _choice(rng, f"{text} Какой подход разумнее всего?", [correct] + wrong, 0,
                   "Долг гасится постоянно и выборочно — там, где он тормозит поставку, — и это нужно показывать бизнесу "
                   "в его терминах; большие остановки и переписывания с нуля редко окупаются.")
