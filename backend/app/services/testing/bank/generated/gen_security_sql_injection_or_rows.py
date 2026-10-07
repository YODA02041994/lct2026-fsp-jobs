"""Сколько строк вернёт SQL-запрос после инъекции: тождество, обрезание комментарием `--`, добавление условия по колонке."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _table_lines, _choice, _multi


@template("gen_security_sql_injection_or_rows", title="SQL-инъекция: сколько строк вернёт запрос",
          competency="Основы ИБ: SQL-инъекция через OR",
          specializations=["security"], technologies=["security_basics", "sql"],
          fmt="exact", grade_level="middle", difficulty_shift=0.0)
def _sql_injection_or_rows(rng: random.Random) -> Instance:
    # (таблица, колонки, список категорий третьей колонки)
    tables_pool = [
        ("users", ["id", "login", "role"], ["user", "admin", "support"]),
        ("accounts", ["id", "owner", "status"], ["active", "blocked", "closed"]),
        ("tickets", ["id", "reporter", "status"], ["open", "closed", "pending"]),
        ("orders", ["id", "customer", "state"], ["new", "paid", "shipped"]),
    ]
    names = ["anna", "boris", "vera", "gleb", "dasha", "egor", "inna", "kirill", "lena", "marat", "nina", "oleg"]

    while True:
        tname, cols, cats = rng.choice(tables_pool)
        field, catcol = cols[1], cols[2]
        n = rng.randint(6, 9)
        logins = rng.sample(names, n)
        cat_a, cat_b = rng.sample(cats, 2)
        values = [rng.choice([cat_a, cat_a, cat_b]) for _ in range(n)]
        rows = [(i + 1, logins[i], values[i]) for i in range(n)]
        tables = {tname: (cols, rows)}

        kind = rng.randrange(3)
        if kind == 0:
            payload = rng.choice(["' OR '1'='1", "' OR 'a'='a", "' OR 1=1 OR '"])
            expl = (f"Из-за конкатенации условие становится {field} = '' OR <всегда истинно>: фильтр отключается, "
                    f"поэтому запрос возвращает все {n} строк таблицы.")
        elif kind == 1:
            k = rng.randint(2, n - 1)
            payload = f"' OR id <= {k} -- "
            expl = (f"Инъекция добавляет OR id <= {k}, а `--` делает остаток строки (включая кавычку) комментарием; "
                    f"условие истинно для строк с id не больше {k} — их {k}.")
        else:
            cat = cat_a
            cnt = values.count(cat)
            payload = f"' OR {catcol} = '{cat}"
            expl = (f"Инъекция добавляет OR {catcol} = '{cat}'; введённый логин не совпадает ни с одной строкой, "
                    f"но к выборке добавляются все строки с {catcol} = '{cat}' — их {cnt}.")

        # Запрос, который получится после конкатенации (одной строкой, чтобы комментарий `--` работал до конца строки).
        effective = f"SELECT id FROM {tname} WHERE {field} = '{payload}'"
        ans = len(_sql_eval(tables, effective + ";"))
        if 1 <= ans <= n:
            break

    code_lines = [
        "# Фрагмент серверного кода (Python + SQLite).",
        "# Значение из поля ввода подставляется в SQL-запрос конкатенацией:",
        "",
        f"table = {tname!r}",
        f"field = {field!r}",
        f"user_input = {payload!r}",
        "",
        "query = \"SELECT id FROM \" + table + \" WHERE \" + field + \" = '\" + user_input + \"'\"",
        "",
        "# --- содержимое таблицы (сам текст query не показан) ---",
    ]
    code = "\n".join(code_lines) + "\n" + "\n".join(_table_lines(tname, cols, rows))

    return Instance(
        question=(
            "Ниже фрагмент серверного кода: значение из поля ввода подставляется в SQL-запрос конкатенацией "
            f"(без параметризации). Пользователь ввёл строку {payload!r}.\n"
            "Сколько строк вернёт получившийся запрос? Соберите запрос мысленно. Введите число."
        ),
        answer=str(ans),
        code=code,
        language="sql",
        explanation=expl,
    )
