"""Проверяет понимание JOIN/GROUP BY в локальной базе Android-приложения (SQLite/Room)"""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_mobile_sqlite_join_group_count", title="Что вернёт запрос к локальной базе",
          competency="Мобильная разработка: SQLite/Room, JOIN и GROUP BY",
          specializations=["mobile"], technologies=["sql", "android"], fmt="exact",
          grade_level="middle", difficulty_shift=0.1)
def _mobile_sqlite_join_group(rng: random.Random) -> Instance:
    users = ["Анна", "Борис", "Вера", "Глеб", "Дина", "Егор", "Жанна", "Игорь"]
    n_users = rng.randint(3, 4)
    picked_users = rng.sample(users, n_users)

    n_msgs = rng.randint(10, 13)
    chat_ids = rng.sample(range(10, 99), 4)

    user_rows = [(i + 1, picked_users[i]) for i in range(n_users)]
    msg_rows = []
    for mid in range(1, n_msgs + 1):
        uid = rng.randint(1, n_users)
        cid = rng.choice(chat_ids)
        msg_rows.append((mid, uid, cid))

    tables = {
        "users": (["id", "name"], user_rows),
        "messages": (["id", "user_id", "chat_id"], msg_rows),
    }

    kind = rng.randrange(5)

    if kind == 0:
        # сколько сообщений у конкретного пользователя
        target = rng.choice(picked_users)
        query = (
            "SELECT COUNT(*) FROM messages m\n"
            "JOIN users u ON u.id = m.user_id\n"
            f"WHERE u.name = '{target}';"
        )
        expl = f"JOIN связывает сообщения с пользователем «{target}», COUNT считает только его строки."
    elif kind == 1:
        # сколько различных чатов у пользователя
        target = rng.choice(picked_users)
        query = (
            "SELECT COUNT(DISTINCT m.chat_id) FROM messages m\n"
            "JOIN users u ON u.id = m.user_id\n"
            f"WHERE u.name = '{target}';"
        )
        expl = f"DISTINCT убирает повторы: считаются уникальные chat_id у «{target}»."
    elif kind == 2:
        # сколько пользователей писали в конкретный чат
        target_chat = rng.choice(chat_ids)
        query = (
            "SELECT COUNT(DISTINCT m.user_id) FROM messages m\n"
            f"WHERE m.chat_id = {target_chat};"
        )
        expl = f"Считаются уникальные авторы сообщений в чате {target_chat}."
    elif kind == 3:
        # сколько сообщений в чате с максимальным числом сообщений у конкретного пользователя
        target = rng.choice(picked_users)
        query = (
            "SELECT COUNT(*) FROM messages m\n"
            "JOIN users u ON u.id = m.user_id\n"
            f"WHERE u.name = '{target}' AND m.chat_id IN (\n"
            "    SELECT chat_id FROM messages GROUP BY chat_id\n"
            "    HAVING COUNT(*) >= 2\n"
            ");"
        )
        expl = (f"Считаются сообщения «{target}» только в тех чатах, где всего не меньше двух сообщений: "
                "подзапрос отбирает такие чаты, внешний COUNT считает строки пользователя среди них.")
    else:
        # самый активный чат: сколько сообщений у чата с максимальным количеством
        query = (
            "SELECT MAX(c) FROM (\n"
            "    SELECT COUNT(*) AS c FROM messages\n"
            "    GROUP BY chat_id\n"
            ");"
        )
        expl = "Подзапрос группирует сообщения по чату, MAX берёт наибольшее значение счётчика."

    rows = _sql_eval(tables, query)
    ans = rows[0][0]

    # гарантируем содержательный ответ
    if ans is None or ans == 0 or ans == n_msgs:
        # перегенерируем один раз с другими данными
        return _mobile_sqlite_join_group(rng)

    return Instance(
        question="Приложение хранит данные в SQLite. Что вернёт запрос? Введите число.",
        answer=str(ans),
        code=_sql_block(tables, query),
        language="sql",
        explanation=expl,
    )
