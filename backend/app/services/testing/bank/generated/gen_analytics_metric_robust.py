"""Расчёт метрики на Python по целым данным: медиана, персентиль без интерполяции, доля с округлением, сравнение конверсий,
межквартильный размах — ответ целым числом или строкой. Данные показаны неотсортированными."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_analytics_metric_robust", title="Расчёт метрики на Python", competency="Аналитика: метрики и устойчивость",
          specializations=["analytics"], technologies=["python", "statistics"], fmt="exact",
          grade_level="senior", difficulty_shift=-0.2)
def _analytics_metric_robust(rng: random.Random) -> Instance:
    kind = rng.randrange(5)
    fn = rng.choice(["metric", "calc", "report", "summary"])

    if kind == 0:
        n = rng.randint(7, 11)
        data = rng.sample(range(1, 60), n)
        code = (
            f"def {fn}(values):\n"
            f"    s = sorted(values)\n"
            f"    k = len(s)\n"
            f"    if k % 2 == 1:\n"
            f"        return s[k // 2]\n"
            f"    return (s[k // 2 - 1] + s[k // 2]) // 2\n\n"
            f"print({fn}({data}))"
        )
        expl = ("Сначала ряд сортируется. Медиана нечётного набора — центральный элемент; "
                "чётного — среднее двух центральных, здесь с целочисленным делением (дробная часть отбрасывается).")
        q = "Что выведет код? Введите число."

    elif kind == 1:
        n = rng.randint(9, 13)
        data = rng.sample(range(1, 100), n)
        p = rng.choice([25, 50, 75])
        code = (
            f"def {fn}(values, p):\n"
            f"    s = sorted(values)\n"
            f"    idx = (len(s) - 1) * p // 100\n"
            f"    return s[idx]\n\n"
            f"print({fn}({data}, {p}))"
        )
        expl = (f"После сортировки берётся элемент с индексом ⌊(n−1)·{p}/100⌋ — «нижний» вариант персентиля без "
                f"интерполяции (в NumPy — method='lower'); это не метод ближайшего ранга ⌈p·n/100⌉, они могут отличаться.")
        q = "Что выведет код? Введите число."

    elif kind == 2:
        total = rng.randint(40, 90)
        good = rng.randint(10, total - 10)
        code = (
            f"total = {total}\n"
            f"good = {good}\n"
            f"print((good * 200 + total) // (2 * total))"
        )
        expl = ("Доля в целых процентах с округлением до ближайшего: (good·200 + total) // (2·total) равно "
                "⌊good·100/total + 0,5⌋ — половина округляется вверх, без плавающей точки.")
        q = "Что выведет код? Введите число."

    elif kind == 3:
        a_n = rng.randint(80, 200)
        a_c = rng.randint(10, a_n - 10)
        b_n = rng.randint(80, 200)
        b_c = rng.randint(10, b_n - 10)
        code = (
            f"a_n, a_c = {a_n}, {a_c}\n"
            f"b_n, b_c = {b_n}, {b_c}\n"
            f"ra = a_c * 10000 // a_n\n"
            f"rb = b_c * 10000 // b_n\n"
            f"if ra > rb:\n"
            f"    print('A')\n"
            f"elif rb > ra:\n"
            f"    print('B')\n"
            f"else:\n"
            f"    print('равно')"
        )
        expl = ("Конверсии сравниваются в сотых долях процента (базисных пунктах) через целочисленное деление, "
                "без плавающей точки; выше та группа, у которой доля a_c/a_n или b_c/b_n больше.")
        q = "Что выведет код? Введите A, B или равно."

    else:
        n = rng.randint(8, 12)
        data = rng.sample(range(1, 80), n)
        code = (
            f"def {fn}(values):\n"
            f"    s = sorted(values)\n"
            f"    k = len(s)\n"
            f"    q1 = s[(k - 1) // 4]\n"
            f"    q3 = s[3 * (k - 1) // 4]\n"
            f"    return q3 - q1\n\n"
            f"print({fn}({data}))"
        )
        expl = ("Межквартильный размах — разность q3 и q1, где q1 = s[(n−1)//4], q3 = s[3(n−1)//4] — элементы "
                "отсортированного ряда без интерполяции («нижний» вариант квартилей).")
        q = "Что выведет код? Введите число."

    ans = _run_python(code)
    return Instance(question=q, answer=ans, code=code, language="python", explanation=expl)
