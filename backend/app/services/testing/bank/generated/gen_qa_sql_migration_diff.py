"""Сверка данных после миграции: какие расхождения ловит конкретный запрос.

В новой таблице три вида расхождений со старой: изменённое значение amount, пропавшая строка, лишняя строка.
Запросы различаются направлением (old EXCEPT new / new EXCEPT old), условием соединения (по id или по id и amount)
и обработкой NULL (NULL <> x не истинно). Кандидат должен понять, какие именно расхождения считает запрос,
а не сравнивать таблицы «вообще». Симметрическая разность собирается через два CTE: в SQLite составные операторы
левоассоциативны, скобки вокруг операндов не допускаются, EXCEPT ALL нет."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_qa_sql_migration_diff", title="Расхождения после миграции данных",
          competency="SQL: сверка данных после миграции",
          specializations=["qa"], technologies=["sql", "testing_theory"],
          fmt="exact", grade_level="senior", difficulty_shift=0.2)
def _qa_sql_migration_diff(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(6, 8)
        ids = sorted(rng.sample(range(100, 999), n))
        src_amounts = [rng.randrange(100, 900, 10) for _ in range(n)]

        # расхождения: обязательно по одному каждого вида, плюс 0–1 случайное
        n_diff = rng.randint(3, 4)
        kinds = ["value", "missing", "extra"] + [rng.choice(["value", "missing", "extra"]) for _ in range(n_diff - 3)]
        rng.shuffle(kinds)
        diff_idx = rng.sample(range(n), n_diff)
        changed, missing, extra = [], [], []
        dst_rows = []
        for i in range(n):
            if i in diff_idx:
                k = kinds[diff_idx.index(i)]
                if k == "value":
                    dst_rows.append((ids[i], src_amounts[i] + rng.choice([20, 50, 100])))
                    changed.append(ids[i])
                    continue
                if k == "missing":
                    missing.append(ids[i])
                    continue
                extra_id = rng.randint(1000, 1999)
                extra.append(extra_id)
                dst_rows.append((extra_id, rng.randrange(100, 900, 10)))
            dst_rows.append((ids[i], src_amounts[i]))
        src_rows = [(ids[i], src_amounts[i]) for i in range(n)]
        rng.shuffle(dst_rows)
        tables = {"old_payments": (["id", "amount"], src_rows), "new_payments": (["id", "amount"], dst_rows)}
        c, mi, ex = len(changed), len(missing), len(extra)
        summary = (f"Расхождения: изменён amount — id {', '.join(map(str, changed))} ({c}); "
                   f"пропали — id {', '.join(map(str, missing))} ({mi}); лишние в новой — id {', '.join(map(str, extra))} ({ex}).")

        mode = rng.choice(["old_except_new", "new_except_old", "join_missing", "join_changed", "symmetric", "ids"])

        if mode == "old_except_new":
            query = ("SELECT COUNT(*) FROM (\n"
                     "  SELECT id, amount FROM old_payments\n"
                     "  EXCEPT\n"
                     "  SELECT id, amount FROM new_payments\n"
                     ");")
            expl = (f"{summary} old EXCEPT new по паре (id, amount) возвращает строки старой таблицы, которых нет в новой "
                    f"в точности: изменённые ({c}) и пропавшие ({mi}); лишние строки новой таблицы в эту сторону не видны. "
                    f"Итого {c + mi}.")
        elif mode == "new_except_old":
            query = ("SELECT COUNT(*) FROM (\n"
                     "  SELECT id, amount FROM new_payments\n"
                     "  EXCEPT\n"
                     "  SELECT id, amount FROM old_payments\n"
                     ");")
            expl = (f"{summary} new EXCEPT old считает строки новой таблицы без точной пары в старой: изменённые ({c}) и "
                    f"лишние ({ex}); пропавшие строки в эту сторону не видны. Итого {c + ex}.")
        elif mode == "join_missing":
            query = ("SELECT COUNT(*) FROM old_payments o\n"
                     "LEFT JOIN new_payments n ON n.id = o.id\n"
                     "WHERE n.id IS NULL;")
            expl = (f"{summary} Соединение только по id: строка старой таблицы остаётся без пары лишь когда её id нет в новой, "
                    f"изменённые суммы при таком условии находят пару. Считаются только пропавшие: {mi}.")
        elif mode == "join_changed":
            query = ("SELECT COUNT(*) FROM old_payments o\n"
                     "LEFT JOIN new_payments n ON n.id = o.id\n"
                     "WHERE n.amount <> o.amount;")
            expl = (f"{summary} Соединение по id, фильтр по неравенству сумм: для пропавших строк n.amount = NULL, а сравнение "
                    f"NULL <> x не истинно, поэтому они отбрасываются WHERE. Считаются только изменённые: {c}.")
        elif mode == "symmetric":
            query = ("WITH gone AS (\n"
                     "  SELECT id, amount FROM old_payments\n"
                     "  EXCEPT\n"
                     "  SELECT id, amount FROM new_payments\n"
                     "),\n"
                     "came AS (\n"
                     "  SELECT id, amount FROM new_payments\n"
                     "  EXCEPT\n"
                     "  SELECT id, amount FROM old_payments\n"
                     ")\n"
                     "SELECT (SELECT COUNT(*) FROM gone) + (SELECT COUNT(*) FROM came);")
            expl = (f"{summary} Симметрическая разность: изменённая строка попадает в обе части (старая версия в gone, "
                    f"новая в came), пропавшая — только в gone, лишняя — только в came: {c}·2 + {mi} + {ex} = {2 * c + mi + ex}.")
        else:
            direction = rng.choice(["old", "new"])
            if direction == "old":
                query = ("SELECT id FROM old_payments\n"
                         "EXCEPT\n"
                         "SELECT id FROM new_payments\n"
                         "ORDER BY id;")
                expl = (f"{summary} EXCEPT только по id: изменённые суммы не видны (id совпадает), остаются id, которых нет "
                        f"в новой таблице, — пропавшие строки, по возрастанию.")
            else:
                query = ("SELECT id FROM new_payments\n"
                         "EXCEPT\n"
                         "SELECT id FROM old_payments\n"
                         "ORDER BY id;")
                expl = (f"{summary} EXCEPT только по id в сторону новой таблицы: остаются id, которых не было в старой, — "
                        f"лишние строки, по возрастанию.")

        rows = _sql_eval(tables, query)
        if mode == "ids":
            if not rows:
                continue
            answer = ",".join(str(r[0]) for r in rows)
            question = ("Старая и новая таблицы платежей после миграции приведены ниже. Какие id вернёт запрос? "
                        "Введите их через запятую без пробелов в том порядке, в каком их вернёт запрос.")
        else:
            ans = rows[0][0]
            if not (1 <= ans <= n + 2):
                continue
            answer = str(ans)
            question = ("Старая и новая таблицы платежей после миграции приведены ниже. Какое число вернёт запрос? "
                        "Введите число.")
        return Instance(question=question, answer=answer, code=_sql_block(tables, query), language="sql",
                        explanation=expl)
