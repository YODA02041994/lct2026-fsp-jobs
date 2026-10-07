"""Разбор журнала на Python: адреса с ошибками 5xx, доля 5xx, ошибки в окне времени, самый частый код ответа.
Каждый вариант — фильтр плюс агрегат; ключ считается исполнением показанного кода, вырожденные ответы (0 или все строки)
отбрасываются."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi

_CODES = ["200", "200", "200", "404", "500", "503", "301", "502"]


def _line(ip: str, h: int, m: int, s: int, code: str) -> str:
    return "%s - - [10/Oct/2024:%02d:%02d:%02d] \"GET /x HTTP/1.1\" %s" % (ip, h, m, s, code)


@template("gen_devops_log_window_analysis", title="Анализ журнала: окно времени и ошибки",
          competency="DevOps: разбор журналов и метрики надёжности",
          specializations=["devops"], technologies=["python", "linux"], fmt="exact",
          grade_level="senior", difficulty_shift=-0.2)
def _log_window(rng: random.Random) -> Instance:
    kind = rng.randrange(4)
    while True:
        ips = list(dict.fromkeys("10.0.%d.%d" % (rng.randint(0, 3), rng.randint(1, 254)) for _ in range(6)))
        n = rng.randint(10, 15)

        if kind == 0:
            # Разные адреса, получившие хотя бы один ответ 5xx
            lines = [_line(rng.choice(ips), rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59), rng.choice(_CODES))
                     for _ in range(n)]
            code = (
                "log = \"\"\"\n" + "\n".join(lines) + "\n\"\"\".strip().splitlines()\n"
                "seen = set()\n"
                "for line in log:\n"
                "    ip = line.split()[0]\n"
                "    st = int(line.split()[-1])\n"
                "    if 500 <= st < 600:\n"
                "        seen.add(ip)\n"
                "print(len(seen))\n"
            )
            expl = "В множество попадают только адреса строк с кодом 5xx, повторы схлопываются; len(seen) — число таких адресов."
            q = "Сколько разных IP-адресов получили хотя бы один ответ с кодом 5xx? Введите число."
            ans = _run_python(code)
            if 1 <= int(ans) <= len(ips) - 1:
                break

        elif kind == 1:
            # Доля ответов 5xx в целых процентах с округлением вниз
            lines = [_line(rng.choice(ips), rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59), rng.choice(_CODES))
                     for _ in range(n)]
            code = (
                "log = \"\"\"\n" + "\n".join(lines) + "\n\"\"\".strip().splitlines()\n"
                "err = 0\n"
                "for line in log:\n"
                "    st = int(line.split()[-1])\n"
                "    if 500 <= st < 600:\n"
                "        err += 1\n"
                "print(err * 100 // len(log))\n"
            )
            expl = "Ошибками сервера считаются только коды 5xx (4xx не входят); доля округляется вниз до целых процентов."
            q = "Какой процент запросов завершился ошибкой сервера (5xx)? Введите целое число процентов."
            ans = _run_python(code)
            if 1 <= int(ans) <= 99:
                break

        elif kind == 2:
            # Ответы с кодом >= 400 в полуоткрытом окне [start, start + window) секунд от начала часа
            start = rng.choice([0, 60, 120, 180, 300])
            window = rng.choice([30, 45, 60, 90])
            secs = sorted(rng.randint(0, 400) for _ in range(n))
            lines = [_line(rng.choice(ips), 0, *divmod(s, 60), rng.choice(_CODES)) for s in secs]
            code = (
                "log = \"\"\"\n" + "\n".join(lines) + "\n\"\"\".strip().splitlines()\n"
                "start = %d\n" % start +
                "window = %d\n" % window +
                "cnt = 0\n"
                "for line in log:\n"
                "    t = line.split('[')[1].split(']')[0].split(':')[1:]\n"
                "    sec = int(t[1]) * 60 + int(t[2])\n"
                "    st = int(line.split()[-1])\n"
                "    if start <= sec < start + window and st >= 400:\n"
                "        cnt += 1\n"
                "print(cnt)\n"
            )
            expl = ("Из квадратных скобок берутся часы, минуты и секунды; t[1] и t[2] — минуты и секунды, они переводятся "
                    "в секунды от начала часа. Окно полуоткрытое: start <= sec < start + window; считаются только коды >= 400.")
            q = "Сколько ответов с кодом 400 и выше попало в окно времени? Введите число."
            ans = _run_python(code)
            if 1 <= int(ans) <= n - 1:
                break

        else:
            # Самый частый код ответа (при равенстве — меньший по числу)
            lines = [_line(rng.choice(ips), rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59), rng.choice(_CODES))
                     for _ in range(n)]
            code = (
                "log = \"\"\"\n" + "\n".join(lines) + "\n\"\"\".strip().splitlines()\n"
                "from collections import Counter\n"
                "c = Counter(line.split()[-1] for line in log)\n"
                "best = min(c.items(), key=lambda kv: (-kv[1], kv[0]))\n"
                "print(best[0])\n"
            )
            expl = "Counter считает частоты кодов; min с ключом (-частота, код) выбирает самый частый, а при равенстве — меньший код."
            q = "Какой код ответа встречается чаще всего (при равенстве — меньший)? Введите код."
            ans = _run_python(code)
            if len({ln.split()[-1] for ln in lines}) >= 3:
                break

    return Instance(question=q, answer=ans, code=code, language="python", explanation=expl)
