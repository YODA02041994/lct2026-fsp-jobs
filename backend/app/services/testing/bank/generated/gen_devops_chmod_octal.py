"""Проверяет понимание прав доступа в Linux: восьмеричная запись chmod и владельцы chown."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_devops_chmod_octal", title="Права доступа chmod", competency="Linux: права доступа",
          specializations=["devops"], technologies=["bash", "linux"], fmt="choice",
          grade_level="junior", difficulty_shift=-0.2)
def _devops_chmod(rng: random.Random) -> Instance:
    user = rng.choice(["alice", "bob", "carol", "dave", "erin", "frank"])
    group = rng.choice(["devs", "ops", "web", "data", "qa"])
    fname = rng.choice(["deploy.sh", "run.sh", "backup.sh", "start.sh", "build.sh"])

    cases = [
        ("владелец читает и пишет, группа читает, остальные не имеют доступа",
         "chmod 640 " + fname,
         "Первая цифра задаёт права владельца, вторая — группы, третья — остальных. 6 это чтение и запись, 4 это только чтение, 0 это отсутствие прав."),
        ("владелец читает, пишет и исполняет, группа читает и исполняет, остальные читают и исполняют",
         "chmod 755 " + fname,
         "Цифра 7 означает чтение, запись и исполнение, цифра 5 означает чтение и исполнение без записи. Такой режим типичен для исполняемого скрипта."),
        ("владелец имеет полный доступ, группа и остальные — никакого",
         "chmod 700 " + fname,
         "Цифра 7 даёт владельцу чтение, запись и исполнение, а нули снимают все права у группы и остальных."),
        ("все могут читать и писать, но никто не может исполнять",
         "chmod 666 " + fname,
         "Цифра 6 означает чтение и запись без исполнения, и она выставлена для владельца, группы и остальных."),
        ("владелец читает и пишет, группа и остальные только читают",
         "chmod 644 " + fname,
         "Цифра 6 даёт владельцу чтение и запись, а цифра 4 даёт группе и остальным только чтение."),
        ("владелец читает и исполняет, группа и остальные не имеют доступа",
         "chmod 500 " + fname,
         "Цифра 5 означает чтение и исполнение без записи, нули закрывают доступ для группы и остальных."),
        ("владелец читает и пишет, группа читает и пишет, остальные только читают",
         "chmod 664 " + fname,
         "Две цифры 6 дают чтение и запись владельцу и группе, цифра 4 оставляет остальным только чтение."),
    ]
    idx = rng.randrange(len(cases))
    descr, correct, expl = cases[idx]

    pool = [
        "chmod 640 " + fname,
        "chmod 755 " + fname,
        "chmod 700 " + fname,
        "chmod 666 " + fname,
        "chmod 644 " + fname,
        "chmod 500 " + fname,
        "chmod 664 " + fname,
        "chmod 777 " + fname,
        "chmod 600 " + fname,
        "chmod 750 " + fname,
    ]
    wrong = [c for c in pool if c != correct]
    options = [correct] + rng.sample(wrong, 5)

    question = (
        f"Файл {fname} принадлежит пользователю {user} и группе {group}. "
        f"Требуется режим: {descr}. Какая команда это сделает?"
    )
    return _choice(rng, question, options, 0, expl)
