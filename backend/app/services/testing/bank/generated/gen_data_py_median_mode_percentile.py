"""Медиана, мода и персентиль по целым данным: тонкости стандартной библиотеки (statistics, Counter).

Проверяется не арифметика, а знание документированного поведения: median_low/median_high на чётном числе
элементов, mode() при нескольких модах (с Python 3.8 — первая встреченная), порядок Counter.most_common()
при равных частотах (порядок первого появления), персентиль методом ближайшего ранга с округлением вверх.
Все ответы — целые числа или строки из целых; плавающих чисел в ключе нет.
"""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


def _unique_others(rng: random.Random, exclude: set[int], k: int, lo: int = 0, hi: int = 30) -> list[int]:
    """k различных чисел из [lo, hi], не входящих в exclude."""
    return rng.sample([x for x in range(lo, hi + 1) if x not in exclude], k)


@template("gen_data_py_median_mode_percentile", title="Медиана, мода и персентиль по целым данным",
          competency="Статистика: медиана, мода, персентиль",
          specializations=["data"], technologies=["python", "statistics"],
          fmt="exact", grade_level="senior", difficulty_shift=0.2)
def _gen_data_py_median_mode_percentile(rng: random.Random) -> Instance:
    fn = rng.choice(["stat", "summary", "report", "agg"])
    kind = rng.randrange(5)

    if kind == 0:
        # median_low / median_high на чётном числе элементов: две центральные различаются
        n = rng.choice([6, 8])
        while True:
            data = rng.sample(range(0, 40), n)
            s = sorted(data)
            if s[n // 2 - 1] != s[n // 2]:
                break
        code = (
            f"from statistics import median_low, median_high\n\n"
            f"def {fn}(xs):\n"
            f"    return f'{{median_low(xs)}} {{median_high(xs)}}'\n\n"
            f"print({fn}({data!r}))"
        )
        expl = ("При чётном числе элементов median_low возвращает меньшее из двух центральных значений, "
                "median_high — большее; оба всегда являются элементами выборки, в отличие от median(), "
                "который вернул бы их среднее (плавающее число).")
        ans = _run_python(code)
        return Instance(question="Что выведет код? Введите два числа через пробел.", answer=ans, code=code,
                        language="python", explanation=expl)

    if kind == 1:
        # mode() при двух модах: с Python 3.8 возвращается первая встреченная в данных
        freq = rng.choice([2, 3])
        a, b = rng.sample(range(1, 20), 2)
        others = _unique_others(rng, {a, b}, rng.choice([2, 3]), 0, 25)
        data = [a] * freq + [b] * freq + others
        rng.shuffle(data)
        code = (
            f"from statistics import mode\n\n"
            f"def {fn}(xs):\n"
            f"    return mode(xs)\n\n"
            f"print({fn}({data!r}))"
        )
        first = next(x for x in data if x in (a, b))
        expl = (f"В данных две моды ({a} и {b}) с одинаковой частотой {freq}. С Python 3.8 statistics.mode() "
                f"при нескольких модах возвращает первую встреченную в исходных данных — здесь {first}; "
                "до 3.8 такой вызов бросал StatisticsError.")
        ans = _run_python(code)
        return Instance(question="Что выведет код (Python 3.12)? Введите число.", answer=ans, code=code,
                        language="python", explanation=expl)

    if kind == 2:
        # Counter.most_common при равных частотах: порядок первого появления
        top = rng.randint(1, 15)
        ties = rng.sample([x for x in range(0, 30) if x != top], 3)
        singles = _unique_others(rng, {top, *ties}, 2, 0, 30)
        data = [top] * 3 + [t for t in ties for _ in range(2)] + singles
        rng.shuffle(data)
        code = (
            f"from collections import Counter\n\n"
            f"def {fn}(xs):\n"
            f"    c = Counter(xs)\n"
            f"    return ' '.join(str(k) for k, _ in c.most_common(3))\n\n"
            f"print({fn}({data!r}))"
        )
        order = []
        for x in data:
            if x in ties and x not in order:
                order.append(x)
        expl = (f"most_common сортирует по убыванию частоты: первым идёт {top} (3 раза). Значения {', '.join(map(str, ties))} "
                f"встречаются по 2 раза, и при равной частоте порядок — по первому появлению в данных: "
                f"{order[0]}, затем {order[1]}.")
        ans = _run_python(code)
        return Instance(question="Что выведет код? Введите три числа через пробел.", answer=ans, code=code,
                        language="python", explanation=expl)

    if kind == 3:
        # Персентиль методом ближайшего ранга: k = ceil(p * n / 100), берётся k-й по возрастанию элемент
        n = rng.choice([8, 10, 12])
        data = rng.sample(range(10, 100), n)
        p = rng.choice([20, 25, 30, 40, 60, 75, 90])
        code = (
            f"def {fn}(xs, p):\n"
            f"    ys = sorted(xs)\n"
            f"    k = (p * len(ys) + 99) // 100\n"
            f"    return ys[k - 1]\n\n"
            f"print({fn}({data!r}, {p}))"
        )
        k = (p * n + 99) // 100
        expl = (f"Метод ближайшего ранга: k = ceil(p·n/100) = ceil({p}·{n}/100) = {k}; выражение (p·n + 99) // 100 — "
                f"это и есть округление вверх в целых. Ответ — {k}-й по возрастанию элемент (индекс {k - 1}).")
        ans = _run_python(code)
        return Instance(question="Что выведет код? Введите число.", answer=ans, code=code,
                        language="python", explanation=expl)

    # kind == 4: multimode — все моды в порядке первого появления
    freq = rng.choice([2, 3])
    modes = rng.sample(range(1, 25), 3)
    others = _unique_others(rng, set(modes), 2, 0, 30)
    data = [m for m in modes for _ in range(freq)] + others
    rng.shuffle(data)
    code = (
        f"from statistics import multimode\n\n"
        f"def {fn}(xs):\n"
        f"    return ' '.join(map(str, multimode(xs)))\n\n"
        f"print({fn}({data!r}))"
    )
    expl = (f"multimode возвращает все значения с наибольшей частотой ({freq}) списком в порядке их первого появления "
            "в данных, а не по возрастанию.")
    ans = _run_python(code)
    return Instance(question="Что выведет код? Введите три числа через пробел.", answer=ans, code=code,
                    language="python", explanation=expl)
