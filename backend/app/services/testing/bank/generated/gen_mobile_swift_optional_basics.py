"""Проверяет понимание основ Swift в iOS: опционалы, guard let, let/var, структуры против классов."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_mobile_swift_optional_basics", title="Основы Swift: опционалы и объявления",
          competency="Swift: опционалы, let/var, guard let, структуры против классов",
          specializations=["mobile"], technologies=["swift", "ios"],
          fmt="choice", grade_level="junior", difficulty_shift=-0.2)
def _swift_optional_basics(rng: random.Random) -> Instance:
    name = rng.choice(["user", "profile", "account", "session", "order", "ticket", "device"])
    field = rng.choice(["email", "nickname", "token", "phone", "avatar", "city", "bio"])
    kind = rng.randrange(7)

    if kind == 0:
        code = (
            f"var {name}: String? = \"value\"\n"
            f"var {field}: String = {name}\n"
            f"print({field})"
        )
        question = "Что произойдёт при компиляции этого кода?"
        options = [
            "Ошибка компиляции: нельзя присвоить String? переменной типа String без разворачивания.",
            "Код скомпилируется, но при запуске будет падение из-за nil.",
            "Код скомпилируется и выведет \"value\".",
            "Код скомпилируется, но выведет \"Optional(\"value\")\".",
            "Компилятор автоматически подставит значение по умолчанию и выведет пустую строку.",
        ]
        correct = 0
        expl = ("Swift не делает неявного разворачивания: String? и String — разные типы, "
                "поэтому присваивание без ! или if let/guard let не компилируется.")
        return _choice(rng, question, options, correct, expl, code=code, language="text")

    if kind == 1:
        code = (
            f"var {name}: String? = nil\n"
            f"if let {field} = {name} {{\n"
            f"    print(\"{field} = \\({field})\")\n"
            f"}} else {{\n"
            f"    print(\"нет значения\")\n"
            f"}}"
        )
        question = "Что выведет этот код?"
        options = [
            "нет значения",
            f"{field} = nil",
            "nil",
            "Ошибка компиляции: if let можно применять только к необязательному типу.",
            "Пустую строку.",
        ]
        correct = 0
        expl = ("if let выполняет первый блок только когда опционал не nil; здесь значение nil, "
                "поэтому идёт ветка else.")
        return _choice(rng, question, options, correct, expl, code=code, language="text")

    if kind == 2:
        code = (
            f"struct {name.capitalize()} {{\n"
            f"    var {field}: String\n"
            f"}}\n"
            f"var a = {name.capitalize()}({field}: \"one\")\n"
            f"var b = a\n"
            f"b.{field} = \"two\"\n"
            f"print(a.{field}, b.{field})"
        )
        question = "Что выведет этот код?"
        options = [
            "one two",
            "two two",
            "one one",
            "two one",
            "Ошибка компиляции: структуры нельзя копировать.",
        ]
        correct = 0
        expl = ("Структуры в Swift — value-типы: при присваивании создаётся копия, "
                "поэтому изменение b не влияет на a.")
        return _choice(rng, question, options, correct, expl, code=code, language="text")

    if kind == 3:
        code = (
            f"class {name.capitalize()} {{\n"
            f"    var {field}: String\n"
            f"    init({field}: String) {{ self.{field} = {field} }}\n"
            f"}}\n"
            f"let a = {name.capitalize()}({field}: \"one\")\n"
            f"let b = a\n"
            f"b.{field} = \"two\"\n"
            f"print(a.{field}, b.{field})"
        )
        question = "Что выведет этот код?"
        options = [
            "two two",
            "one two",
            "one one",
            "two one",
            "Ошибка компиляции: let не позволяет менять свойства.",
        ]
        correct = 0
        expl = ("Классы — reference-типы: a и b ссылаются на один объект, "
                "поэтому изменение через b видно и через a. let запрещает переприсваивать ссылку, но не менять свойства.")
        return _choice(rng, question, options, correct, expl, code=code, language="text")

    if kind == 4:
        code = (
            f"func load() -> String? {{\n"
            f"    return nil\n"
            f"}}\n\n"
            f"func show() {{\n"
            f"    guard let {field} = load() else {{\n"
            f"        print(\"нет\")\n"
            f"        return\n"
            f"    }}\n"
            f"    print({field})\n"
            f"}}\n"
            f"show()"
        )
        question = "Что выведет этот код?"
        options = [
            "нет",
            "nil",
            "Пустую строку.",
            "Ошибка компиляции: guard let требует else с break.",
            "Код не скомпилируется: return недопустим внутри guard.",
        ]
        correct = 0
        expl = ("guard let разворачивает опционал, а при nil выполняет блок else, который обязан выйти из текущей "
                "области: здесь return завершает функцию show(), поэтому печатается \"нет\".")
        return _choice(rng, question, options, correct, expl, code=code, language="text")

    if kind == 5:
        code = (
            f"var {name}: String? = \"abc\"\n"
            f"print({name}?.count ?? 0)"
        )
        question = "Что выведет этот код?"
        options = [
            "3",
            "Optional(3)",
            "0",
            "nil",
            "Ошибка компиляции: у String? нет свойства count.",
        ]
        correct = 0
        expl = ("Оператор ?. вызывает count только если значение не nil; здесь оно есть, "
                "результат Int? разворачивается через ?? 0 и печатается 3.")
        return _choice(rng, question, options, correct, expl, code=code, language="text")

    code = (
        f"let {name}: String? = nil\n"
        f"let {field} = {name}!\n"
        f"print({field})"
    )
    question = "Что произойдёт при выполнении этого кода?"
    options = [
        "Программа аварийно завершится (fatal error: unexpectedly found nil while unwrapping an Optional value).",
        "Переменная получит значение по умолчанию.",
        "Код не скомпилируется: нельзя применять ! к nil.",
        "Оператор ! вернёт пустую строку.",
        "Оператор ! выбросит ошибку, которую можно поймать через do/catch.",
    ]
    correct = 0
    expl = ("Принудительное разворачивание (!) значения nil — ошибка времени выполнения, программа аварийно "
            "завершается; поэтому ! применяют только когда значение точно не nil.")
    return _choice(rng, question, options, correct, expl, code=code, language="text")
