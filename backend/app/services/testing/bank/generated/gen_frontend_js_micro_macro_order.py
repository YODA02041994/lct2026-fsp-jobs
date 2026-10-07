"""Порядок микрозадач и макрозадач при комбинации Promise, async/await, queueMicrotask и setTimeout.

Метки вывода — нейтральные буквы, чтобы имя не подсказывало тип задачи. Ключ проверяется исполнением в node
(scripts/evolve/validate_candidate.py). Источник: developer.mozilla.org — HTML DOM API, Microtask guide.
"""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_frontend_js_micro_macro_order", title="Порядок микрозадач и макрозадач",
          competency="JavaScript: очередь задач (Promise, setTimeout)",
          specializations=["frontend"], technologies=["javascript"],
          fmt="exact", grade_level="senior", difficulty_shift=0.0)
def _js_micro_macro(rng: random.Random) -> Instance:
    a, b, c, d = rng.sample(["A", "B", "C", "D", "E", "F", "G", "H"], 4)
    kinds = [
        # 0: Promise.then -> setTimeout
        (f"console.log('{a}');\n"
         f"setTimeout(() => console.log('{c}'), 0);\n"
         f"Promise.resolve().then(() => console.log('{b}'));\n"
         f"console.log('{d}');",
         f"{a} {d} {b} {c}",
         "Сначала выполняется весь синхронный код, затем очередь микрозадач (обработчики Promise), и только потом "
         "макрозадачи (setTimeout), даже с задержкой 0."),
        # 1: вложенный then внутри then
        (f"console.log('{a}');\n"
         f"setTimeout(() => console.log('{c}'), 0);\n"
         f"Promise.resolve().then(() => {{\n"
         f"  console.log('{b}');\n"
         f"  Promise.resolve().then(() => console.log('{d}'));\n"
         f"}});",
         f"{a} {b} {d} {c}",
         "Микрозадача, поставленная из микрозадачи, выполняется в том же проходе очереди — до любой макрозадачи; "
         "setTimeout дожидается, пока очередь микрозадач опустеет."),
        # 2: два setTimeout + Promise
        (f"setTimeout(() => console.log('{a}'), 0);\n"
         f"Promise.resolve().then(() => console.log('{b}'));\n"
         f"setTimeout(() => console.log('{c}'), 0);\n"
         f"Promise.resolve().then(() => console.log('{d}'));",
         f"{b} {d} {a} {c}",
         "Сначала все микрозадачи в порядке постановки, затем макрозадачи в порядке постановки — очередь таймеров "
         "не перемешивается с очередью микрозадач."),
        # 3: async/await + setTimeout
        (f"async function main() {{\n"
         f"  console.log('{a}');\n"
         f"  await null;\n"
         f"  console.log('{b}');\n"
         f"}}\n"
         f"setTimeout(() => console.log('{c}'), 0);\n"
         f"main();\n"
         f"console.log('{d}');",
         f"{a} {d} {b} {c}",
         "Тело async-функции до первого await выполняется синхронно; продолжение после await — микрозадача, поэтому "
         "оно идёт после оставшегося синхронного кода, но до setTimeout."),
        # 4: Promise.all + then
        (f"console.log('{a}');\n"
         f"Promise.all([Promise.resolve(1), Promise.resolve(2)]).then(() => console.log('{b}'));\n"
         f"setTimeout(() => console.log('{c}'), 0);\n"
         f"Promise.resolve().then(() => console.log('{d}'));",
         f"{a} {d} {b} {c}",
         "Promise.all подписывается на каждый элемент через then и завершается только после их обработчиков — на это "
         "уходит несколько тиков микрозадач, поэтому его then срабатывает позже обычного then, но всё равно до setTimeout."),
        # 5: queueMicrotask + setTimeout + then
        (f"console.log('{a}');\n"
         f"queueMicrotask(() => console.log('{b}'));\n"
         f"setTimeout(() => console.log('{c}'), 0);\n"
         f"Promise.resolve().then(() => console.log('{d}'));",
         f"{a} {b} {d} {c}",
         "queueMicrotask и обработчик then попадают в одну очередь микрозадач и выполняются в порядке постановки — "
         "до макрозадачи setTimeout."),
    ]
    code, expected, expl = kinds[rng.randrange(len(kinds))]
    return Instance(question="Что выведет код? Введите буквы через пробел в порядке вывода.",
                    answer=expected, code=code, language="javascript", explanation=expl)
