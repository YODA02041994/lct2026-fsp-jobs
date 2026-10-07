"""Оконные функции (SQLite ≥ 3.25, синтаксис стандартный): ROW_NUMBER для дедупликации и топ-1 в группе,
LAG для сравнения с предыдущей строкой, SUM OVER с явной рамкой для накопительной суммы.
Столбец пользователя назван login: слово USER зарезервировано стандартом SQL и PostgreSQL."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_data_sql_window_dedup_topn", title="Оконные функции: дедупликация, топ-N, LAG и накопительная сумма",
          competency="SQL: оконные функции (ROW_NUMBER, LAG, SUM OVER)",
          specializations=["data"], technologies=["sql"], fmt="exact",
          grade_level="senior", difficulty_shift=0.2)
def _data_sql_window_dedup_topn(rng: random.Random) -> Instance:
    cities = ["Москва", "Казань", "Пермь", "Омск", "Сочи", "Тверь", "Уфа"]
    logins = ["anna", "boris", "vera", "gleb", "dina", "egor", "zhanna", "ivan", "kira", "lev"]
    cols = ["id", "city", "login", "score"]

    while True:
        n_cities = rng.randint(2, 3)
        chosen_cities = rng.sample(cities, n_cities)
        rows = []
        rid = 1
        for city in chosen_cities:
            k = rng.randint(3, 4)
            for _ in range(k):
                u = rng.choice(logins)
                sc = rng.randint(10, 99)
                rows.append((rid, city, u, sc))
                rid += 1
        # гарантируем хотя бы одну повторяющуюся пару (city, login) — это суть дедупликации
        base = rows[0]
        rows.append((rid, base[1], base[2], rng.randint(10, 99)))
        rid += 1
        rng.shuffle(rows)
        tables = {"events": (cols, rows)}

        kind = rng.randrange(4)

        if kind == 0:
            # Сколько строк останется после дедупликации по (city, login) с максимальным score
            query = (
                "WITH ranked AS (\n"
                "  SELECT city, login, score,\n"
                "         ROW_NUMBER() OVER (PARTITION BY city, login ORDER BY score DESC, id ASC) AS rn\n"
                "  FROM events\n"
                ")\n"
                "SELECT COUNT(*) FROM ranked WHERE rn = 1;"
            )
            ans = _sql_eval(tables, query)[0][0]
            if not (1 <= ans <= len(rows) - 1):
                continue
            expl = ("ROW_NUMBER() нумерует строки внутри каждой пары (city, login) по убыванию score; "
                    f"условие rn = 1 оставляет по одной строке на пару, а различных пар здесь {ans} "
                    f"(всего строк {len(rows)}).")
            return Instance(question="Сколько строк вернёт запрос? Введите число.", answer=str(ans),
                            code=_sql_block(tables, query), language="sql", explanation=expl)

        if kind == 1:
            # Топ-1 по score в каждом городе: сумма их score
            query = (
                "WITH ranked AS (\n"
                "  SELECT city, login, score,\n"
                "         ROW_NUMBER() OVER (PARTITION BY city ORDER BY score DESC, id ASC) AS rn\n"
                "  FROM events\n"
                ")\n"
                "SELECT SUM(score) FROM ranked WHERE rn = 1;"
            )
            ans = _sql_eval(tables, query)[0][0]
            if ans is None or ans <= 0:
                continue
            best = {c: max(r[3] for r in rows if r[1] == c) for c in chosen_cities}
            expl = ("ROW_NUMBER() с PARTITION BY city выбирает по одной лучшей строке на город: "
                    + ", ".join(f"{c} — {v}" for c, v in best.items()) + f"; их сумма равна {ans}.")
            return Instance(question="Какое число вернёт запрос? Введите число.", answer=str(ans),
                            code=_sql_block(tables, query), language="sql", explanation=expl)

        if kind == 2:
            # LAG: сколько строк имеют рост относительно предыдущей (по id) строки того же города
            query = (
                "WITH ordered AS (\n"
                "  SELECT city, id, score,\n"
                "         LAG(score) OVER (PARTITION BY city ORDER BY id) AS prev_score\n"
                "  FROM events\n"
                ")\n"
                "SELECT COUNT(*) FROM ordered WHERE prev_score IS NOT NULL AND score > prev_score;"
            )
            ans = _sql_eval(tables, query)[0][0]
            if not (1 <= ans <= len(rows) - 1):
                continue
            expl = ("LAG(score) OVER (PARTITION BY city ORDER BY id) даёт score предыдущей по id строки того же города, "
                    f"для первой строки города — NULL. Строк, у которых score больше предыдущего: {ans}.")
            return Instance(question="Сколько строк вернёт запрос? Введите число.", answer=str(ans),
                            code=_sql_block(tables, query), language="sql", explanation=expl)

        # kind == 3: накопительная сумма по городу в порядке id — значение acc у конкретной строки
        # берём строку, которая не первая в своём городе (иначе окно декоративно) и город с ≥ 3 строками
        candidates = []
        for r in rows:
            same = sorted(x for x in rows if x[1] == r[1])
            pos = [x[0] for x in same].index(r[0])
            if len(same) >= 3 and pos >= 1:
                candidates.append((r, same[:pos + 1]))
        if not candidates:
            continue
        target, prefix = rng.choice(candidates)
        query = (
            "WITH running AS (\n"
            "  SELECT city, id, score,\n"
            "         SUM(score) OVER (PARTITION BY city ORDER BY id\n"
            "                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS acc\n"
            "  FROM events\n"
            ")\n"
            f"SELECT acc FROM running WHERE id = {target[0]};"
        )
        ans = _sql_eval(tables, query)[0][0]
        if ans is None or ans <= 0:
            continue
        expl = (f"Окно накапливает score внутри города {target[1]} в порядке id от начала партиции до текущей строки. "
                f"Для id = {target[0]} это строки с id {', '.join(str(x[0]) for x in prefix)}: "
                f"{' + '.join(str(x[3]) for x in prefix)} = {ans}.")
        return Instance(question="Какое число вернёт запрос? Введите число.", answer=str(ans),
                        code=_sql_block(tables, query), language="sql", explanation=expl)
