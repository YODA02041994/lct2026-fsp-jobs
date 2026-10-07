"""Сводная таблица по категориям через GROUP BY с HAVING: сколько строк вернёт запрос. Порог подбирается под агрегат,
чтобы встречались все четыре агрегата; ключ считается через sqlite3."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


_CATEGORIES = ["Электроника", "Одежда", "Книги", "Продукты", "Игрушки", "Спорт", "Косметика", "Мебель"]
_THRESHOLDS = {
    "SUM(qty)": [8, 10, 12, 15, 18, 20],
    "COUNT(*)": [2, 3, 4],
    "SUM(price)": [500, 600, 800, 1000, 1200],
    "SUM(qty * price)": [1500, 2000, 2500, 3000, 4000],
}


@template("gen_analytics_sql_group_having_count", title="Сколько категорий пройдут HAVING",
          competency="Аналитика: сводные таблицы SQL (GROUP BY, HAVING)",
          specializations=["analytics"], technologies=["sql", "excel"], fmt="exact",
          grade_level="junior", difficulty_shift=0.3)
def _analytics_sql_group_having_count(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(10, 14)
        cats = rng.sample(_CATEGORIES, rng.randint(4, 5))
        rows = []
        for i in range(1, n + 1):
            cat = rng.choice(cats)
            qty = rng.randint(1, 9)
            price = rng.choice([100, 150, 200, 250, 300, 400, 500])
            rows.append((i, cat, qty, price))
        agg = rng.choice(list(_THRESHOLDS))
        thr = rng.choice(_THRESHOLDS[agg])
        query = (
            "SELECT category, " + agg + " AS total\n"
            "FROM sales\n"
            "GROUP BY category\n"
            "HAVING " + agg + " >= " + str(thr) + ";"
        )
        tables = {"sales": (["id", "category", "qty", "price"], rows)}
        res = _sql_eval(tables, query)
        ans = len(res)
        if 1 <= ans <= len(cats) - 1:
            break
    return Instance(
        question="Сколько строк вернёт запрос? Введите число.",
        answer=str(ans),
        code=_sql_block(tables, query),
        language="sql",
        explanation=(
            "GROUP BY собирает строки по категориям (одна строка результата на категорию), HAVING оставляет только "
            "те группы, у которых " + agg + " не меньше " + str(thr) + "; таких категорий " + str(ans) + "."
        ),
    )
