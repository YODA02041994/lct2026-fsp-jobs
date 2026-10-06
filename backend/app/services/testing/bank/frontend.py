"""Шаблоны: фронтенд — JavaScript, TypeScript, HTML, CSS, React.

Ключи exact-заданий считаются в Python той же логикой, что у JavaScript/CSS: берутся только однозначные
конструкции (map/filter/reduce, замыкания, spread, порядок микро- и макрозадач, specificity, box model).
В выводе — числа и строки через join, без массивов и плавающих чисел.
"""
from __future__ import annotations
import random

from .base import template, Instance
from .common import _choice, _multi, _COLORS

SPEC = ["frontend"]


# ---------------------------------------------------------------------------------------------
# JavaScript: junior
# ---------------------------------------------------------------------------------------------

@template("frontend_js_filter_map", title="filter и map", competency="JavaScript: методы массивов",
          specializations=SPEC, technologies=["javascript"], fmt="exact", grade_level="junior", difficulty_shift=-0.3)
def _js_filter_map(rng: random.Random) -> Instance:
    while True:
        nums = rng.sample(range(1, 20), 6)
        k = rng.choice([2, 3, 10])
        t = rng.randint(5, 12)
        pred_js, pred_py, pred_text = rng.choice([
            ("x % 2 === 0", lambda x: x % 2 == 0, "чётные"),
            ("x % 2 !== 0", lambda x: x % 2 != 0, "нечётные"),
            (f"x > {t}", lambda x, t=t: x > t, f"больше {t}"),
        ])
        map_js, map_py = rng.choice([(f"x * {k}", lambda x, k=k: x * k), (f"x + {k}", lambda x, k=k: x + k)])
        kept = [map_py(x) for x in nums if pred_py(x)]
        if 2 <= len(kept) <= 4:
            break
    var = rng.choice(["nums", "values", "items"])
    code = (f"const {var} = [{', '.join(map(str, nums))}];\n"
            f"const result = {var}\n"
            f"  .filter(x => {pred_js})\n"
            f"  .map(x => {map_js});\n"
            'console.log(result.join(","));')
    ans = ",".join(map(str, kept))
    return Instance(question="Что выведет код? Введите значения через запятую без пробелов.", answer=ans, code=code,
                    language="javascript",
                    explanation=f"filter оставляет {pred_text} элементы, map применяет {map_js} к каждому, join склеивает запятой.")


@template("frontend_js_reduce", title="reduce с начальным значением", competency="JavaScript: reduce",
          specializations=SPEC, technologies=["javascript"], fmt="exact", grade_level="junior", difficulty_shift=-0.1)
def _js_reduce(rng: random.Random) -> Instance:
    nums = rng.sample(range(1, 12), rng.randint(3, 4))
    init = rng.choice([0, 1, 10, 100])
    t = rng.randint(3, 8)
    kinds = [
        ("acc + x", init, sum(nums) + init, "Сумма элементов плюс начальное значение."),
        ("acc * x", 1 if init == 0 else init, None, "Произведение элементов, умноженное на начальное значение."),
        ("Math.max(acc, x)", init, max([init] + nums), "Максимум среди начального значения и элементов."),
        (f"acc + (x > {t} ? 1 : 0)", 0, sum(1 for x in nums if x > t), f"Считается число элементов больше {t}."),
    ]
    body, start, val, expl = rng.choice(kinds)
    if val is None:
        val = start
        for x in nums:
            val *= x
    var = rng.choice(["items", "nums", "scores"])
    code = (f"const {var} = [{', '.join(map(str, nums))}];\n"
            f"const total = {var}.reduce((acc, x) => {body}, {start});\n"
            "console.log(total);")
    return Instance(question="Что выведет код? Введите число.", answer=str(val), code=code, language="javascript",
                    explanation=expl)


@template("frontend_js_equality", title="== против ===", competency="JavaScript: приведение типов при сравнении",
          specializations=SPEC, technologies=["javascript"], fmt="multichoice", grade_level="junior", difficulty_shift=0.2)
def _js_equality(rng: random.Random) -> Instance:
    n = rng.randint(2, 9)
    true_pool = [f'"{n}" == {n}', "null == undefined", '0 == ""', '"" == false', 'typeof null === "object"',
                 f'"{n}" === String({n})', f"{n} === {n}.0"]
    false_pool = [f'"{n}" === {n}', "null === undefined", '0 === ""', "NaN === NaN", "NaN == NaN",
                  f'"{n}" === "{n} "', "undefined === null", f"{n} == {n + 1}"]
    k = rng.randint(2, 3)
    correct = rng.sample(true_pool, k)
    wrong = rng.sample(false_pool, 6 - k)
    return _multi(rng, "Какие из выражений вернут true? Выберите все подходящие.", correct, wrong,
                  "== приводит типы (строка к числу, null к undefined, пустая строка к 0), === сравнивает без приведения; "
                  "NaN не равен ничему, даже себе; typeof null — историческое «object».")


@template("frontend_css_box_width", title="Ширина элемента и box-sizing", competency="CSS: блочная модель",
          specializations=SPEC, technologies=["css"], fmt="exact", grade_level="junior", difficulty_shift=0.0)
def _css_box(rng: random.Random) -> Instance:
    width = rng.choice([200, 240, 300, 320])
    pad = rng.choice([8, 10, 12, 16, 20])
    border = rng.choice([1, 2, 3, 4])
    margin = rng.choice([10, 15, 20])
    sizing = rng.choice(["content-box", "border-box"])
    cls = rng.choice(["card", "panel", "tile"])
    code = (f".{cls} {{\n  box-sizing: {sizing};\n  width: {width}px;\n  padding: {pad}px;\n"
            f"  border: {border}px solid #333;\n  margin: {margin}px;\n}}")
    total = width + 2 * pad + 2 * border if sizing == "content-box" else width
    expl = (f"При content-box width задаёт только содержимое: {width} + 2×{pad} + 2×{border} = {total}."
            if sizing == "content-box" else
            f"При border-box width уже включает padding и border, поэтому рамка занимает ровно {width}px.")
    return Instance(question=f"Какую ширину в пикселях займёт элемент .{cls} от внешнего края рамки до внешнего края "
                             "рамки (margin не учитывать)? Введите число.", answer=str(total), code=code, language="css",
                    explanation=expl + " Margin в ширину рамки не входит.")


@template("frontend_css_flex", title="Свойство flex под задачу", competency="CSS: flexbox",
          specializations=SPEC, technologies=["css"], fmt="choice", grade_level="junior", difficulty_shift=-0.2)
def _css_flex(rng: random.Random) -> Instance:
    gap = rng.choice([8, 12, 16, 24])
    cases = [
        ("расположить дочерние элементы по центру главной оси (по горизонтали)", "justify-content: center;",
         "Главная ось в row — горизонталь; выравнивание по ней задаёт justify-content."),
        ("выровнять дочерние элементы по центру поперечной оси (по вертикали)", "align-items: center;",
         "Поперечную ось в row задаёт align-items."),
        ("переносить элементы на новую строку, когда они не помещаются", "flex-wrap: wrap;",
         "Перенос включает flex-wrap: wrap."),
        ("выстроить элементы в колонку сверху вниз", "flex-direction: column;",
         "Направление главной оси меняет flex-direction."),
        (f"сделать расстояние {gap}px между элементами без внешних отступов у крайних", f"gap: {gap}px;",
         "gap задаёт промежутки только между элементами."),
        ("прижать первый элемент к левому краю, последний — к правому, промежутки между остальными равные",
         "justify-content: space-between;", "space-between раздвигает крайние элементы к краям контейнера."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    options = [c[1] for c in cases]
    return _choice(rng, f"Контейнер объявлен как display: flex (направление row). Нужно {text}. Какое свойство добавить?",
                   options, idx, expl, code=".row {\n  display: flex;\n}", language="css")


@template("frontend_html_semantic", title="Семантический тег", competency="HTML: семантика",
          specializations=SPEC, technologies=["html"], fmt="choice", grade_level="junior", difficulty_shift=-0.3)
def _html_semantic(rng: random.Random) -> Instance:
    cases = [
        ("блок основной навигации по сайту со ссылками на разделы", "<nav>", "Навигационные ссылки — nav."),
        ("основное содержимое страницы, уникальное для неё (одно на страницу)", "<main>", "Главное содержимое — main."),
        ("самостоятельная запись блога, которую можно опубликовать отдельно", "<article>", "Самостоятельная единица содержимого — article."),
        ("боковая колонка с материалами, косвенно связанными с основным текстом", "<aside>", "Косвенно связанное содержимое — aside."),
        ("шапка страницы с логотипом и заголовком", "<header>", "Вводная часть — header."),
        ("подвал с контактами и копирайтом", "<footer>", "Завершающая часть — footer."),
        ("иллюстрация с подписью, на которую ссылаются из текста", "<figure>", "Иллюстрация с подписью — figure (+ figcaption)."),
        ("дата публикации в машиночитаемом виде", "<time>", "Дата и время — time с атрибутом datetime."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    wrong = [c[1] for c in cases if c[1] != correct]
    return _choice(rng, f"Нужно разметить {text}. Какой тег подходит лучше всего?", [correct] + rng.sample(wrong, 5), 0,
                   expl + " Семантические теги лучше div для доступности и поиска.")


@template("frontend_html_form_attrs", title="Атрибуты форм", competency="HTML: формы",
          specializations=SPEC, technologies=["html"], fmt="choice", grade_level="junior", difficulty_shift=0.0)
def _html_forms(rng: random.Random) -> Instance:
    n = rng.choice([3, 5, 8])
    cases = [
        ("поле нельзя оставить пустым при отправке формы", 'required', "required запрещает отправку с пустым полем."),
        (f"в поле можно ввести не больше {n} символов", f'maxlength="{n}"', "maxlength ограничивает длину ввода."),
        ("браузер должен проверить, что введён адрес e-mail", 'type="email"', "type=email включает встроенную валидацию адреса."),
        ("показать подсказку серым текстом внутри пустого поля", 'placeholder="…"', "Подсказка в пустом поле — placeholder."),
        ("поле отображается, но его нельзя редактировать, а значение отправляется с формой", 'readonly', "readonly: не редактируется, но отправляется (в отличие от disabled)."),
        ("поле нельзя редактировать и его значение не отправляется с формой", 'disabled', "disabled исключает поле из отправки."),
        ("связать подпись с полем так, чтобы клик по подписи ставил фокус в поле", '<label for="id">', "label с for по id поля связывает подпись и поле."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    wrong = [c[1] for c in cases if c[1] != correct]
    return _choice(rng, f"Нужно, чтобы {text}. Что использовать?", [correct] + rng.sample(wrong, 5), 0, expl)


# ---------------------------------------------------------------------------------------------
# JavaScript / CSS / TS / React: middle
# ---------------------------------------------------------------------------------------------

@template("frontend_js_closure_counters", title="Независимые замыкания", competency="JavaScript: замыкания",
          specializations=SPEC, technologies=["javascript"], fmt="exact", grade_level="middle", difficulty_shift=-0.2)
def _js_closures(rng: random.Random) -> Instance:
    s1, s2 = rng.sample([1, 2, 3, 5, 10], 2)
    na, nb = rng.randint(1, 3), rng.randint(1, 3)
    a, b = rng.choice([("a", "b"), ("inc", "dec"), ("first", "second")])
    calls = [f"{a}();"] * na + [f"{b}();"] * nb
    rng.shuffle(calls)
    code = ("function makeCounter(step) {\n  let count = 0;\n  return () => {\n    count += step;\n    return count;\n  };\n}\n"
            f"const {a} = makeCounter({s1});\nconst {b} = makeCounter({s2});\n"
            + "\n".join(calls) + "\n"
            f"console.log({a}(), {b}());")
    va = s1 * (na + 1)
    vb = s2 * (nb + 1)
    return Instance(question="Что выведет код? Введите два числа через пробел.", answer=f"{va} {vb}", code=code,
                    language="javascript",
                    explanation=f"У каждого счётчика своё замыкание count: {a} вызван {na + 1} раз с шагом {s1}, "
                                f"{b} — {nb + 1} раз с шагом {s2}.")


@template("frontend_js_var_let_timeout", title="var и let в цикле с setTimeout", competency="JavaScript: область видимости",
          specializations=SPEC, technologies=["javascript"], fmt="exact", grade_level="middle", difficulty_shift=0.0)
def _js_var_let(rng: random.Random) -> Instance:
    n = rng.randint(3, 4)
    kw = rng.choice(["var", "let"])
    k = rng.choice([1, 2, 10])
    expr = "i" if k == 1 else f"i * {k}"
    code = ("const out = [];\n"
            f"for ({kw} i = 0; i < {n}; i++) {{\n"
            f"  setTimeout(() => out.push({expr}), 0);\n"
            "}\n"
            'setTimeout(() => console.log(out.join(",")), 50);')
    if kw == "var":
        vals = [n * k] * n
        expl = f"var — одна переменная на всю функцию; к моменту срабатывания таймеров цикл завершился и i = {n}."
    else:
        vals = [i * k for i in range(n)]
        expl = "let создаёт отдельную привязку i для каждой итерации, и каждая стрелка помнит своё значение."
    return Instance(question="Что выведет код? Введите значения через запятую без пробелов.", answer=",".join(map(str, vals)),
                    code=code, language="javascript", explanation=expl)


@template("frontend_js_object_spread", title="Слияние объектов через spread", competency="JavaScript: объекты и spread",
          specializations=SPEC, technologies=["javascript"], fmt="exact", grade_level="middle", difficulty_shift=-0.1)
def _js_spread(rng: random.Random) -> Instance:
    keys = rng.sample(["a", "b", "c", "d", "e"], 4)
    base = {keys[0]: rng.randint(1, 9), keys[1]: rng.randint(1, 9), keys[2]: rng.randint(1, 9)}
    patch = {keys[1]: rng.randint(10, 99), keys[3]: rng.randint(10, 99)}
    extra_key = rng.choice([keys[0], keys[3]])
    extra_val = rng.randint(100, 999)
    order = rng.choice(["base_patch", "patch_base"])

    def js_obj(d: dict) -> str:
        return "{ " + ", ".join(f"{k}: {v}" for k, v in d.items()) + " }"

    merged: dict = {}
    if order == "base_patch":
        merged.update(base)
        merged.update(patch)
        spread = "...base, ...patch"
    else:
        merged.update(patch)
        merged.update(base)
        spread = "...patch, ...base"
    merged[extra_key] = extra_val
    ask = rng.choice([keys[1], extra_key])
    code = (f"const base = {js_obj(base)};\nconst patch = {js_obj(patch)};\n"
            f"const merged = {{ {spread}, {extra_key}: {extra_val} }};\n"
            f"console.log(merged.{ask}, Object.keys(merged).length);")
    ans = f"{merged[ask]} {len(merged)}"
    return Instance(question="Что выведет код? Введите два числа через пробел.", answer=ans, code=code, language="javascript",
                    explanation="При spread позднее свойство перекрывает раннее, явное свойство в конце — самое позднее; "
                                "ключи не дублируются, поэтому их число равно числу уникальных имён.")


_SPECIFICITY = [
    ("p", (0, 0, 1)), (".text", (0, 1, 0)), ("#note", (1, 0, 0)), ("p.text", (0, 1, 1)),
    (".text.big", (0, 2, 0)), (".box p", (0, 1, 1)), ("div p", (0, 0, 2)), (".box .text", (0, 2, 0)),
    ("#note.text", (1, 1, 0)), ("div .big", (0, 1, 1)),
]


@template("frontend_css_specificity", title="Специфичность селекторов", competency="CSS: каскад и специфичность",
          specializations=SPEC, technologies=["css"], fmt="exact", grade_level="middle", difficulty_shift=0.2)
def _css_specificity(rng: random.Random) -> Instance:
    rules = rng.sample(_SPECIFICITY, 4)
    colors = rng.sample(_COLORS, 4)
    best = max(range(4), key=lambda i: (rules[i][1], i))   # при равной специфичности побеждает позднее правило
    code = "\n".join(f"{sel} {{ color: {col}; }}" for (sel, _), col in zip(rules, colors))
    html = '<div class="box"><p id="note" class="text big">Текст</p></div>'
    spec = rules[best][1]
    ties = sum(1 for r in rules if r[1] == spec) > 1
    expl = (f"Специфичность (id, классы, теги): побеждает {rules[best][0]} с {spec}"
            + ("; при равной специфичности применяется правило, объявленное позже." if ties else "."))
    return Instance(question=f"Для разметки {html} заданы правила ниже. Какого цвета будет текст абзаца? "
                             "Введите название цвета как в CSS.", answer=colors[best], code=code, language="css",
                    explanation=expl)


@template("frontend_ts_utility_types", title="Утилитарные типы TypeScript", competency="TypeScript: система типов",
          specializations=SPEC, technologies=["typescript"], fmt="choice", grade_level="middle", difficulty_shift=0.0)
def _ts_utility(rng: random.Random) -> Instance:
    t = rng.choice(["User", "Order", "Product", "Ticket"])
    a, b = rng.sample(["id", "name", "email", "price", "status"], 2)
    cases = [
        (f"все поля {t} стали необязательными", f"Partial<{t}>", "Partial делает каждое поле необязательным."),
        (f"тип только с полями `{a}` и `{b}` из {t}", f'Pick<{t}, "{a}" | "{b}">', "Pick выбирает перечисленные поля."),
        (f"тип со всеми полями {t}, кроме `{a}`", f'Omit<{t}, "{a}">', "Omit исключает перечисленные поля."),
        (f"все поля {t}, включая необязательные, стали обязательными", f"Required<{t}>", "Required снимает знак ? со всех полей."),
        (f"поля {t} нельзя переприсваивать после создания", f"Readonly<{t}>", "Readonly помечает поля как только для чтения."),
        (f"словарь: ключи — строки, значения — {t}", f"Record<string, {t}>", "Record<K, V> описывает объект-словарь."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    options = [c[1] for c in cases]
    return _choice(rng, f"Есть интерфейс {t}. Нужен тип, в котором {text}. Какой утилитарный тип это даёт?",
                   options, idx, expl)


@template("frontend_react_useeffect_deps", title="Когда выполняется useEffect", competency="React: эффекты и зависимости",
          specializations=SPEC, technologies=["react", "javascript"], fmt="choice", grade_level="middle", difficulty_shift=0.1)
def _react_effect(rng: random.Random) -> Instance:
    a, b = rng.sample(["count", "query", "userId", "page", "filter"], 2)
    deps, correct, expl = rng.choice([
        (f"[{a}]", f"После первого рендера и после каждого рендера, в котором изменился {a}",
         f"Эффект с зависимостями запускается после монтирования и когда меняется любая зависимость — здесь только {a}."),
        ("[]", "Только после первого рендера (монтирования)", "Пустой массив зависимостей — эффект один раз после монтирования."),
        ("", "После каждого рендера компонента", "Без массива зависимостей эффект выполняется после каждого рендера."),
        (f"[{a}, {b}]", f"После первого рендера и после каждого рендера, где изменился {a} или {b}",
         "Любая изменившаяся зависимость из списка перезапускает эффект."),
    ])
    sep = ", " if deps else ""
    code = ("useEffect(() => {\n"
            f"  document.title = `${{{a}}} / ${{{b}}}`;\n"
            f"}}{sep}{deps});")
    pool = [
        f"После первого рендера и после каждого рендера, в котором изменился {a}",
        "Только после первого рендера (монтирования)",
        "После каждого рендера компонента",
        f"После первого рендера и после каждого рендера, где изменился {a} или {b}",
        "Синхронно до рендера, при каждом вызове компонента",
        "Только при размонтировании компонента",
        f"Только когда изменился {b}",
    ]
    wrong = [p for p in pool if p != correct]
    return _choice(rng, "Когда выполнится эффект?", [correct] + rng.sample(wrong, 5), 0, expl, code=code, language="javascript")


# ---------------------------------------------------------------------------------------------
# Senior
# ---------------------------------------------------------------------------------------------

@template("frontend_js_event_loop_order", title="Порядок вывода: синхронный код, промисы, таймеры",
          competency="JavaScript: цикл событий", specializations=SPEC, technologies=["javascript", "async"], fmt="exact",
          grade_level="senior", difficulty_shift=-0.1)
def _js_event_loop(rng: random.Random) -> Instance:
    labels = rng.sample(["A", "B", "C", "D", "E", "F"], 5)
    # типы: sync, timeout, micro (then), micro-chain (then().then())
    kinds = ["sync", "sync", "timeout", "micro", rng.choice(["micro", "timeout", "chain"])]
    rng.shuffle(kinds)
    lines, sync, micro, micro2, macro = [], [], [], [], []
    for lab, kind in zip(labels, kinds):
        if kind == "sync":
            lines.append(f'console.log("{lab}");')
            sync.append(lab)
        elif kind == "timeout":
            lines.append(f'setTimeout(() => console.log("{lab}"), 0);')
            macro.append(lab)
        elif kind == "micro":
            lines.append(f'Promise.resolve().then(() => console.log("{lab}"));')
            micro.append(lab)
        else:
            lines.append(f'Promise.resolve().then(() => {{}}).then(() => console.log("{lab}"));')
            micro2.append(lab)
    # микрозадачи: первые .then в порядке регистрации, затем вторые звенья цепочек
    order = sync + micro + micro2 + macro
    code = "\n".join(lines)
    return Instance(question="В каком порядке появятся строки в консоли? Введите буквы через пробел.", answer=" ".join(order),
                    code=code, language="javascript",
                    explanation="Сначала весь синхронный код, затем очередь микрозадач (обработчики промисов, цепочки — по звеньям), "
                                "и только потом макрозадачи setTimeout, даже с задержкой 0.")


@template("frontend_js_sort_default", title="Сортировка чисел без компаратора", competency="JavaScript: сортировка",
          specializations=SPEC, technologies=["javascript"], fmt="exact", grade_level="senior", difficulty_shift=-0.3)
def _js_sort(rng: random.Random) -> Instance:
    while True:
        nums = rng.sample([1, 5, 9, 10, 12, 25, 30, 100, 200, 7], 5)
        if sorted(nums) != sorted(nums, key=str):
            break
    var = rng.choice(["nums", "ids", "sizes"])
    kind = rng.choice(["default", "default", "asc", "desc"])
    if kind == "default":
        call, res = f"{var}.sort();", sorted(nums, key=str)
        expl = "Без компаратора sort сравнивает элементы как строки (лексикографически), поэтому 100 оказывается перед 25."
    elif kind == "asc":
        call, res = f"{var}.sort((a, b) => a - b);", sorted(nums)
        expl = "Компаратор a − b даёт числовую сортировку по возрастанию."
    else:
        call, res = f"{var}.sort((a, b) => b - a);", sorted(nums, reverse=True)
        expl = "Компаратор b − a даёт числовую сортировку по убыванию."
    code = f"const {var} = [{', '.join(map(str, nums))}];\n{call}\nconsole.log({var}.join(\",\"));"
    return Instance(question="Что выведет код? Введите значения через запятую без пробелов.", answer=",".join(map(str, res)),
                    code=code, language="javascript", explanation=expl)


@template("frontend_react_state_batching", title="Обновления состояния в одном обработчике", competency="React: состояние и батчинг",
          specializations=SPEC, technologies=["react", "javascript"], fmt="exact", grade_level="senior", difficulty_shift=0.1)
def _react_batching(rng: random.Random) -> Instance:
    base = rng.randint(0, 9)
    step = rng.choice([1, 2, 5])
    while True:
        kinds = [rng.choice(["direct", "fn"]) for _ in range(3)]
        if "direct" in kinds and "fn" in kinds:
            break
    pending = base
    lines = []
    for kind in kinds:
        if kind == "direct":
            lines.append(f"    setCount(count + {step});")
            pending = base + step            # count в замыкании — значение на момент рендера
        else:
            lines.append(f"    setCount(c => c + {step});")
            pending = pending + step
    code = ("function Counter() {\n"
            f"  const [count, setCount] = useState({base});\n"
            "  function handleClick() {\n"
            + "\n".join(lines) + "\n"
            "  }\n"
            "  return <button onClick={handleClick}>{count}</button>;\n"
            "}")
    return Instance(question="Начальное значение count показано в коде. Какое число отобразится на кнопке после одного клика "
                             "(React 18)? Введите число.", answer=str(pending), code=code, language="javascript",
                    explanation=f"Обновления в одном обработчике батчатся. setCount(count + {step}) использует count из замыкания "
                                f"({base}) и ставит в очередь фиксированное значение, затирая накопленное; функциональная форма "
                                "c => c + step применяется к текущему значению очереди.")


# ---------------------------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------------------------

@template("frontend_lead_bundle_perf", title="Большой бандл и медленная загрузка", competency="Архитектура фронтенда: производительность",
          specializations=SPEC, technologies=["react", "webpack"], fmt="choice", grade_level="lead", difficulty_shift=-0.2)
def _lead_bundle(rng: random.Random) -> Instance:
    size = rng.choice([2.8, 3.5, 4.2])
    lcp = rng.choice([5.1, 6.4, 7.8])
    page = rng.choice(["каталога", "входа", "ленты", "корзины"])
    pct = rng.choice([70, 80, 90])
    text = (f"SPA на React: один бандл {size} МБ, LCP на мобильных {lcp} с. {pct} % пользователей открывают только страницу "
            f"{page}, остальные экраны (админка, отчёты, редактор) грузятся вместе с ней.")
    correct = ("Разделить бандл по маршрутам (React.lazy + динамический import), подгружать редкие экраны по требованию, "
               "проанализировать состав бандла и замерить LCP снова")
    wrong = [
        "Переписать приложение на другой фреймворк — он быстрее",
        "Включить gzip на сервере и на этом остановиться",
        "Отключить source maps в продакшене — бандл станет втрое меньше",
        "Инлайнить весь JavaScript в HTML, чтобы сэкономить запросы",
        "Увеличить ресурсы сервера, отдающего статику",
    ]
    return _choice(rng, f"{text} Что сделать в первую очередь?", [correct] + wrong, 0,
                   "Разделение кода по маршрутам убирает из первой загрузки то, что большинству не нужно; это измеримо и "
                   "дёшево по сравнению с переписыванием. Сжатие полезно, но не решает проблему объёма исполняемого кода.")


@template("frontend_lead_state_architecture", title="Когда нужен глобальный стор", competency="Архитектура фронтенда: состояние",
          specializations=SPEC, technologies=["react", "system_design"], fmt="multichoice", grade_level="lead", difficulty_shift=0.1)
def _lead_state(rng: random.Random) -> Instance:
    n = rng.choice([12, 20, 35])
    true_pool = [
        "Выносить в общее состояние то, что нужно многим несвязанным частям дерева: текущий пользователь, права, тема",
        "Серверные данные с кешированием и инвалидацией держать в специализированном слое (React Query/SWR), а не в сторе",
        "Начинать с локального состояния компонента и поднимать его выше только по необходимости",
    ]
    false_pool = [
        "Любое состояние формы сразу класть в глобальный стор, чтобы было единообразно",
        "Глобальный стор обязателен в любом React-приложении с самого начала",
        "Если проп передаётся на два уровня вниз — это уже повод завести Redux",
        f"Все {n} экранов должны читать состояние только из одного объекта store",
    ]
    k = rng.randint(2, 3)
    return _multi(rng, f"Команда спорит, нужен ли глобальный стор в приложении из {n} экранов. Какие утверждения отражают "
                       "разумный подход к состоянию? Выберите все подходящие.", rng.sample(true_pool, k), rng.sample(false_pool, 6 - k),
                  "Глобальное состояние — для действительно общих данных; серверный кеш — в отдельном слое; остальное живёт "
                  "локально. Преждевременный стор добавляет связность и шаблонный код без пользы.")
