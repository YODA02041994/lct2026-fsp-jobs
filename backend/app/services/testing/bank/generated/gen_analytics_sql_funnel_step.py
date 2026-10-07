"""Воронка на SQL: таблица событий пользователей (часть шагов повторяется), запрос с подзапросом или GROUP BY/HAVING —
отвал на шаге, когорта по дню первого шага, повторы событий, число пройденных шагов. Ключ считается через sqlite3."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi

_STEPS = ["view", "cart", "checkout", "paid"]


@template("gen_analytics_sql_funnel_step", title="Воронка на SQL: сколько дошло до шага",
          competency="Продуктовая аналитика: воронка и удержание",
          specializations=["analytics"], technologies=["sql", "product_analytics"],
          fmt="exact", grade_level="middle", difficulty_shift=0.1)
def _analytics_sql_funnel_step(rng: random.Random) -> Instance:
    while True:
        n_users = rng.randint(5, 7)
        uids = rng.sample(range(101, 999), n_users)
        rows: list[tuple] = []
        for u in uids:
            depth = rng.randint(1, len(_STEPS))          # каждый пользователь проходит префикс шагов
            for i in range(depth):
                rows.append((u, _STEPS[i], rng.randint(1, 5)))
                if i <= 1 and rng.random() < 0.35:      # просмотр и корзину часть пользователей повторяет
                    rows.append((u, _STEPS[i], rng.randint(1, 5)))
        tables = {"events": (["user_id", "step", "day"], rows)}
        kind = rng.randrange(4)
        if kind == 0:
            j = rng.randrange(1, len(_STEPS) - 1)
            b, nxt = _STEPS[j], _STEPS[j + 1]
            query = (f"SELECT COUNT(DISTINCT user_id) FROM events\n"
                     f"WHERE step = '{b}'\n"
                     f"  AND user_id NOT IN (SELECT user_id FROM events WHERE step = '{nxt}');")
            expl = (f"Отвал на шаге: пользователи, у которых есть «{b}», но нет «{nxt}». "
                    f"DISTINCT нужен, потому что событие «{b}» у пользователя может повторяться.")
        elif kind == 1:
            b = rng.choice(_STEPS[1:])
            d = rng.randint(2, 4)
            query = (f"SELECT COUNT(DISTINCT user_id) FROM events\n"
                     f"WHERE step = '{b}'\n"
                     f"  AND user_id IN (SELECT user_id FROM events WHERE step = 'view' AND day <= {d});")
            expl = (f"Когорта: пользователи с просмотром не позже дня {d}, дошедшие до «{b}» (в любой день). "
                    f"Подзапрос отбирает когорту, внешний запрос считает уникальных пользователей шага.")
        elif kind == 2:
            t = rng.choice(_STEPS[:2])
            query = (f"SELECT COUNT(*) FROM (\n"
                     f"  SELECT user_id FROM events\n"
                     f"  WHERE step = '{t}'\n"
                     f"  GROUP BY user_id\n"
                     f"  HAVING COUNT(*) > 1\n"
                     f");")
            expl = (f"Внутренний запрос оставляет пользователей, у которых событие «{t}» встречается больше одного раза; "
                    f"внешний COUNT(*) считает таких пользователей, а не события.")
        else:
            kk = rng.randint(2, 4)
            query = (f"SELECT COUNT(*) FROM (\n"
                     f"  SELECT user_id FROM events\n"
                     f"  GROUP BY user_id\n"
                     f"  HAVING COUNT(DISTINCT step) >= {kk}\n"
                     f");")
            expl = (f"Для каждого пользователя считается число разных шагов (повторы одного шага DISTINCT схлопывает); "
                    f"остаются прошедшие не меньше {kk} шагов, внешний запрос считает их число.")
        ans = _sql_eval(tables, query)[0][0]
        if ans is None:
            continue
        if 1 <= ans <= n_users - 1:
            break
    return Instance(question="Какое число вернёт запрос? Введите число.",
                    answer=str(ans),
                    code=_sql_block(tables, query), language="sql",
                    explanation=expl)
