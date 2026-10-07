"""Проверяет понимание null-safety, val/var, data class и when в Kotlin для Android."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_mobile_kotlin_null_safety_basics", title="Основы Kotlin в Android: null-safety и объявления",
          competency="Мобильная разработка: основы Kotlin",
          specializations=["mobile"], technologies=["kotlin", "android"], fmt="choice",
          grade_level="junior", difficulty_shift=-0.2)
def _kotlin_basics(rng: random.Random) -> Instance:
    user = rng.choice(["user", "account", "profile", "client", "member"])
    field = rng.choice(["name", "email", "nickname", "title", "login"])
    fallback = rng.choice(["\"гость\"", "\"неизвестно\"", "\"без имени\"", "\"аноним\"", "\"n/a\""])
    num = rng.randint(1, 9)
    val_name = rng.choice(["count", "total", "size", "score", "amount"])
    cls = rng.choice(["User", "Account", "Profile", "Client", "Member"])

    cases = [
        (
            f"Что вернёт выражение, если переменная {user} равна null?\n\nval {field}: String = {user}?.{field} ?: {fallback}",
            fallback,
            [
                "null",
                "Ошибка компиляции: нельзя присвоить null в String",
                "Будет выброшено NullPointerException",
                "Пустая строка \"\"",
                "Строка \"null\"",
            ],
            f"Оператор ?. безопасно обращается к свойству, а ?: подставляет значение по умолчанию, если результат null. Поэтому {field} получает {fallback}.",
        ),
        (
            f"Какой оператор в Kotlin позволяет выполнить обращение к свойству {field} у переменной {user}, которая может быть null, без риска падения?",
            "?.",
            [
                "!!",
                "?:",
                "as?",
                "!!.",
                ".",
            ],
            "Оператор ?. (безопасный вызов) обращается к свойству только если объект не null, иначе возвращает null.",
        ),
        (
            f"Что произойдёт при выполнении кода?\n\nval {user}: String? = null\nval len = {user}!!.length",
            "Будет выброшено исключение NullPointerException",
            [
                "len будет равен 0",
                "len будет равен null",
                "Ошибка компиляции: нельзя применять !! к null",
                "Код выполнится без ошибок, len будет пустой строкой",
                "Будет выброшено исключение IllegalStateException",
            ],
            "Оператор !! (утверждение не-null) приводит тип к не-null и при фактическом null бросает обычный "
            "java.lang.NullPointerException; с Kotlin 1.4 оператор !! бросает именно его, а не KotlinNullPointerException.",
        ),
        (
            f"Какое объявление в Kotlin запрещает повторное присваивание значения переменной {val_name}?",
            "val",
            [
                "var",
                "const",
                "final",
                "let",
                "lateinit",
            ],
            "val создаёт неизменяемую ссылку: после инициализации присвоить новое значение нельзя. var — изменяемая.",
        ),
        (
            f"Что автоматически генерирует компилятор для класса, объявленного как data class {cls}(val {field}: String, val {val_name}: Int)?",
            "equals, hashCode, toString, copy и componentN",
            [
                "только toString и equals",
                "геттеры и сеттеры для всех свойств",
                "конструктор без параметров и билдер",
                "сериализацию в JSON",
                "операторы сравнения <, >, <=",
            ],
            "data class автоматически получает equals, hashCode, toString, copy и функции componentN для деструктуризации.",
        ),
        (
            f"Какой вариант when корректно обработает значение {num} и вернёт строку для чётного числа?",
            f"when ({num} % 2) {{\n    0 -> \"чётное\"\n    else -> \"нечётное\"\n}}",
            [
                f"when ({num} % 2) {{\n    case 0: \"чётное\"\n    default: \"нечётное\"\n}}",
                f"when ({num} % 2) {{\n    0 => \"чётное\"\n    else => \"нечётное\"\n}}",
                f"when ({num} % 2) {{\n    0: return \"чётное\"\n    else: return \"нечётное\"\n}}",
                f"switch ({num} % 2) {{\n    0 -> \"чётное\"\n    else -> \"нечётное\"\n}}",
                f"when ({num} % 2) {{\n    == 0 -> \"чётное\"\n    else -> \"нечётное\"\n}}",
            ],
            "В Kotlin when использует стрелки -> и else; синтаксис case/default и => относятся к другим языкам.",
        ),
        (
            f"Что выведет код?\n\nval {user}: String? = \"{field}\"\nprintln({user}?.length ?: -1)",
            str(len(field)),
            [
                "-1",
                "null",
                "0",
                "Ошибка компиляции",
                f"\"{field}\"",
            ],
            f"Строка не null, поэтому ?. возвращает её длину {len(field)}, а ?: не срабатывает.",
        ),
    ]

    idx = rng.randrange(len(cases))
    question, correct, wrong, expl = cases[idx]
    options = [correct] + wrong
    return _choice(rng, question, options, 0, expl, language="text")
