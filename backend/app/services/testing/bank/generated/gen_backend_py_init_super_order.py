"""Порядок вызова __init__ и super(): ромб MRO, перезапись атрибута до super(), __slots__ и __dict__, super() в property.

Ключ всегда считается через _run_python(code). Источники: docs.python.org — built-in super() (MRO, кооперативное
множественное наследование), Data model → __slots__ (слоты складываются по MRO; без __slots__ в потомке появляется __dict__).
"""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_backend_py_init_super_order", title="Порядок вызова __init__ и super()",
          competency="Python: классы, наследование, property, __slots__",
          specializations=["backend"], technologies=["python", "oop"],
          fmt="exact", grade_level="senior", difficulty_shift=0.2)
def _py_init_super_order(rng: random.Random) -> Instance:
    base = rng.choice(["Base", "Node", "Entity", "Unit"])
    mid, mid2 = rng.sample(["Middle", "Layer", "Wrapper", "Adapter", "Mixin"], 2)
    leaf = rng.choice(["Leaf", "Child", "Final", "Top"])
    n = rng.randint(2, 5)
    m = rng.choice([x for x in range(2, 9) if x != n])
    k = rng.randint(1, 4)
    kind = rng.randrange(5)

    if kind == 0:
        # ромб: оба средних класса зовут super(), базовый __init__ выполняется один раз, порядок задаёт MRO
        first, second = (mid, mid2) if rng.random() < 0.5 else (mid2, mid)
        code = (
            f"class {base}:\n"
            f"    def __init__(self):\n"
            f"        self.log = ['{base}']\n"
            f"\n"
            f"class {mid}({base}):\n"
            f"    def __init__(self):\n"
            f"        super().__init__()\n"
            f"        self.log.append('{mid}')\n"
            f"\n"
            f"class {mid2}({base}):\n"
            f"    def __init__(self):\n"
            f"        super().__init__()\n"
            f"        self.log.append('{mid2}')\n"
            f"\n"
            f"class {leaf}({first}, {second}):\n"
            f"    def __init__(self):\n"
            f"        super().__init__()\n"
            f"        self.log.append('{leaf}')\n"
            f"\n"
            f"print(' '.join({leaf}().log))"
        )
        question = "Что выведет код? Введите имена через пробел в порядке вывода."
        expl = (f"MRO ромба: {leaf} → {first} → {second} → {base}. super() передаёт вызов следующему по MRO, а не "
                f"«родителю», поэтому {first} вызывает {second}, а не {base}; тело {base} выполняется один раз и первым, "
                f"затем дописывают себя {second}, {first} и {leaf}.")
    elif kind == 1:
        code = (
            f"class {base}:\n"
            f"    def __init__(self, v):\n"
            f"        self.v = v\n"
            f"        print('{base}', v)\n"
            f"\n"
            f"class {mid}({base}):\n"
            f"    def __init__(self, v):\n"
            f"        print('{mid} start', v)\n"
            f"        super().__init__(v + {n})\n"
            f"        print('{mid} end', self.v)\n"
            f"\n"
            f"obj = {mid}({n})\n"
            f"print('total', obj.v)"
        )
        question = "Что выведет код? Введите все строки вывода подряд через пробел (слова и числа)."
        expl = (f"Сначала печатается начало конструктора {mid} с исходным {n}, затем конструктор {base} уже с {n + n}, "
                f"затем конец {mid}, где self.v равен {n + n}; итоговая строка — total {n + n}.")
    elif kind == 2:
        with_slots = rng.random() < 0.5
        leaf_slots = f"    __slots__ = ('b',)\n" if with_slots else ""
        code = (
            f"class {base}:\n"
            f"    __slots__ = ('a',)\n"
            f"    def __init__(self):\n"
            f"        self.a = {n}\n"
            f"\n"
            f"class {leaf}({base}):\n"
            f"{leaf_slots}"
            f"    def __init__(self):\n"
            f"        super().__init__()\n"
            f"        self.b = self.a * 2\n"
            f"\n"
            f"obj = {leaf}()\n"
            f"print(hasattr(obj, '__dict__'), obj.a + obj.b)"
        )
        question = "Что выведет код? Введите два значения через пробел."
        if with_slots:
            expl = (f"Слоты складываются по MRO: у {leaf} доступны и a, и b, а __dict__ не создаётся, пока все классы "
                    f"в цепочке объявляют __slots__ — hasattr даёт False; сумма a + b = {n} + {2 * n} = {3 * n}.")
        else:
            expl = (f"{leaf} не объявляет __slots__, поэтому у экземпляра появляется обычный __dict__ (hasattr — True), "
                    f"и b хранится в нём, а a — в слоте родителя; сумма a + b = {n} + {2 * n} = {3 * n}.")
    elif kind == 3:
        code = (
            f"class {base}:\n"
            f"    def __init__(self):\n"
            f"        self._x = {n}\n"
            f"    @property\n"
            f"    def x(self):\n"
            f"        return self._x * 10\n"
            f"\n"
            f"class {leaf}({base}):\n"
            f"    @property\n"
            f"    def x(self):\n"
            f"        return super().x + {m}\n"
            f"\n"
            f"obj = {leaf}()\n"
            f"print(obj.x)"
        )
        question = "Что выведет код? Введите число."
        expl = (f"Переопределённое свойство обращается к родительскому через super().x — super() работает и с дескрипторами. "
                f"Базовое x возвращает _x * 10 = {n * 10}, наследник прибавляет {m}: {n * 10 + m}.")
    else:
        code = (
            f"class {base}:\n"
            f"    def __init__(self):\n"
            f"        self.size = {n}\n"
            f"\n"
            f"class {leaf}({base}):\n"
            f"    def __init__(self):\n"
            f"        self.size = {m}\n"
            f"        super().__init__()\n"
            f"        self.total = self.size + {k}\n"
            f"\n"
            f"obj = {leaf}()\n"
            f"print(obj.size, obj.total)"
        )
        question = "Что выведет код? Введите два числа через пробел."
        expl = (f"Присваивание self.size = {m} сделано до super().__init__(), и базовый конструктор его перезаписывает "
                f"значением {n}; total считается уже от {n}: {n} + {k} = {n + k}.")

    ans = _run_python(code)
    return Instance(question=question, answer=ans, code=code, language="python", explanation=expl)
