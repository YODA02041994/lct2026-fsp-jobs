"""Оконные функции и CTE: окно не схлопывает строки, ROW_NUMBER/RANK/LAG внутри партиции, фильтр по окну через CTE.

Ключ считается через _sql_eval (sqlite3); конструкции стандартные и одинаково работают в PostgreSQL.
Источники: postgresql.org/docs/current/tutorial-window.html (окно сохраняет строки; фильтровать по результату окна
можно только из подзапроса/CTE), functions-window.html (row_number, rank с пропусками, lag → NULL без предыдущей строки).
"""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_backend_sql_window_cte_group", title="Оконные функции, CTE и GROUP BY в два уровня",
          competency="SQL: аналитические запросы с оконными функциями и CTE",
          specializations=["backend"], technologies=["sql", "postgresql"],
          fmt="exact", grade_level="senior", difficulty_shift=0.2)
def _sql_window_cte_group(rng: random.Random) -> Instance:
    kind = rng.randrange(6)
    for _ in range(300):
        if kind == 0:
            # ROW_NUMBER: лучший результат каждой команды, затем сумма этих максимумов
            n = rng.randint(7, 9)
            groups = rng.sample(["sales", "support", "dev", "qa", "ops"], 3)
            rows = [(i + 1, rng.choice(groups), rng.randint(10, 99)) for i in range(n)]
            tables = {"tasks": (["id", "team", "score"], rows)}
            query = (
                "WITH ranked AS (\n"
                "  SELECT team, score,\n"
                "         ROW_NUMBER() OVER (PARTITION BY team ORDER BY score DESC, id) AS rn\n"
                "  FROM tasks\n"
                ")\n"
                "SELECT SUM(score) FROM ranked WHERE rn = 1;"
            )
            ans = _sql_eval(tables, query)[0][0]
            ok = len({r[1] for r in rows}) >= 2
            expl = ("ROW_NUMBER нумерует строки внутри каждой команды по убыванию score; rn = 1 оставляет лучший результат "
                    "каждой команды, а внешний SUM складывает эти максимумы — по одному на команду.")
        elif kind == 1:
            # SUM OVER PARTITION: элементы больше половины суммы своей группы
            n = rng.randint(7, 9)
            groups = ["A", "B", "C"]
            rows = [(i + 1, rng.choice(groups), rng.randint(5, 40)) for i in range(n)]
            tables = {"items": (["id", "grp", "val"], rows)}
            query = (
                "WITH agg AS (\n"
                "  SELECT grp, val,\n"
                "         SUM(val) OVER (PARTITION BY grp) AS total\n"
                "  FROM items\n"
                ")\n"
                "SELECT COUNT(*) FROM agg WHERE val * 2 > total;"
            )
            ans = _sql_eval(tables, query)[0][0]
            ok = 1 <= ans <= n - 1
            expl = ("SUM(val) OVER (PARTITION BY grp) приписывает каждой строке сумму всей её группы, не схлопывая строки; "
                    "условие val * 2 > total оставляет элементы, которые больше половины суммы своей группы "
                    "(единственный элемент группы проходит всегда).")
        elif kind == 2:
            # COUNT OVER PARTITION: считаем события (строки) пользователей с двумя и более событиями, а не пользователей
            n = rng.randint(8, 9)
            users = ["u1", "u2", "u3", "u4", "u5", "u6"]
            rows = [(i + 1, rng.choice(users), rng.choice(["login", "click", "view", "buy"])) for i in range(n)]
            tables = {"events": (["id", "user_id", "kind"], rows)}
            query = (
                "WITH per_user AS (\n"
                "  SELECT user_id, kind,\n"
                "         COUNT(*) OVER (PARTITION BY user_id) AS cnt\n"
                "  FROM events\n"
                ")\n"
                "SELECT COUNT(*) FROM per_user WHERE cnt >= 2;"
            )
            ans = _sql_eval(tables, query)[0][0]
            ok = 1 <= ans <= n - 1
            expl = ("COUNT(*) OVER (PARTITION BY user_id) не группирует строки: каждая строка получает число событий своего "
                    "пользователя. Поэтому внешний COUNT считает события (строки) пользователей с двумя и более событиями, "
                    "а не самих пользователей — в отличие от GROUP BY ... HAVING COUNT(*) >= 2.")
        elif kind == 3:
            # LAG: сколько раз значение выросло относительно предыдущего внутри региона
            n = rng.randint(7, 9)
            groups = rng.sample(["north", "south", "west"], 3)
            rows = [(i + 1, rng.choice(groups), rng.randint(1, 20)) for i in range(n)]
            tables = {"metrics": (["id", "region", "value"], rows)}
            query = (
                "WITH ordered AS (\n"
                "  SELECT region, value,\n"
                "         LAG(value) OVER (PARTITION BY region ORDER BY id) AS prev\n"
                "  FROM metrics\n"
                ")\n"
                "SELECT COUNT(*) FROM ordered WHERE prev IS NOT NULL AND value > prev;"
            )
            ans = _sql_eval(tables, query)[0][0]
            ok = 1 <= ans <= n - 1
            expl = ("LAG берёт предыдущее значение внутри региона по порядку id; у первой строки региона предыдущего нет "
                    "(NULL), она отсеивается. Считаем строки, где текущее значение больше предыдущего в том же регионе.")
        elif kind == 4:
            # SUM OVER PARTITION по месяцам: считаем заказы (строки) в месяцах с суммой больше порога, а не месяцы
            n = rng.randint(8, 9)
            groups = ["jan", "feb", "mar", "apr"]
            rows = [(i + 1, rng.choice(groups), rng.randint(10, 80)) for i in range(n)]
            tables = {"orders": (["id", "month", "amount"], rows)}
            thr = rng.choice([60, 80, 100, 120])
            query = (
                "WITH totals AS (\n"
                "  SELECT month, amount,\n"
                "         SUM(amount) OVER (PARTITION BY month) AS s\n"
                "  FROM orders\n"
                ")\n"
                f"SELECT COUNT(*) FROM totals WHERE s > {thr};"
            )
            ans = _sql_eval(tables, query)[0][0]
            ok = 1 <= ans <= n - 1
            expl = (f"SUM(amount) OVER (PARTITION BY month) приписывает каждому заказу сумму его месяца, строки остаются "
                    f"отдельными. Внешний COUNT считает заказы (строки) в месяцах с суммой больше {thr}, а не число таких "
                    "месяцев — это дал бы GROUP BY month HAVING SUM(amount) > порога.")
        else:
            # RANK с пропусками: ранг 1 получают все строки с максимумом группы (ничьи)
            n = rng.randint(7, 9)
            groups = rng.sample(["x", "y", "z"], 3)
            rows = [(i + 1, rng.choice(groups), rng.randint(1, 5)) for i in range(n)]
            tables = {"scores": (["id", "grp", "points"], rows)}
            query = (
                "WITH ranked AS (\n"
                "  SELECT grp, points,\n"
                "         RANK() OVER (PARTITION BY grp ORDER BY points DESC) AS rk\n"
                "  FROM scores\n"
                ")\n"
                "SELECT COUNT(*) FROM ranked WHERE rk = 1;"
            )
            ans = _sql_eval(tables, query)[0][0]
            ok = ans > len({r[1] for r in rows})      # хотя бы одна ничья — иначе ответ равен числу групп
            expl = ("RANK присваивает ранг 1 всем строкам с максимальным points в своей группе (ничьи делят ранг, следующий "
                    "ранг пропускается), поэтому строк с rk = 1 больше, чем групп, если максимум повторяется.")
        if ok:
            break

    return Instance(
        question="Что вернёт следующий запрос? Введите число.",
        answer=str(ans),
        code=_sql_block(tables, query),
        language="sql",
        explanation=expl,
    )
