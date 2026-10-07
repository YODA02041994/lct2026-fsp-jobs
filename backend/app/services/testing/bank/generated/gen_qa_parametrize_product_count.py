"""Сколько тестов соберёт и выполнит pytest: стекирование parametrize на функции, классе и модуле (pytestmark),
pytest.param с маркером skip, область действия фикстур (function / class / module), порядок идентификаторов.

Кандидату показывается тестовый модуль как есть (language="text": он ничего не печатает, поэтому
исполнением через _run_python ключ не проверить). Ключ считается по документированным правилам pytest
(docs.pytest.org: how-to/parametrize, how-to/fixtures#scope, how-to/skipping) и при ревью сверен с реальным
pytest 9.1 на 30 зёрнах: число собранных, выполненных, вызовов каждой фикстуры и идентификаторы.
Правила: параметры перемножаются (метод × класс × модуль); экземпляр с маркером skip собирается, но не
выполняется и фикстуры для него не создаются; фикстура module создаётся один раз, class — по разу на класс,
function — на каждый выполненный тест; в идентификаторе первым идёт ближайший к функции параметр,
он же перебирается медленнее всего.
"""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi

_ENVS = [["dev", "prod"], ["sqlite", "pg"], ["ru", "en"]]
_FORMATS = ["csv", "xml", "json", "pdf"]
_CLASSES = ["TestOrders", "TestReports", "TestInvoices"]
_METHODS = ["test_export", "test_render", "test_build"]
_FIXTURES = [("db", "cache", "client"), ("conn", "registry", "session"), ("engine", "store", "api")]


@template("gen_qa_parametrize_product_count", title="Сколько тестов соберёт pytest: параметризация, skip и фикстуры",
          competency="pytest: параметризация, маркеры и область действия фикстур",
          specializations=["qa"], technologies=["python", "pytest"], fmt="exact",
          grade_level="senior", difficulty_shift=0.2)
def _qa_parametrize_product_count(rng: random.Random) -> Instance:
    kind = rng.randrange(4)
    f_mod, f_cls, f_fn = rng.choice(_FIXTURES)
    cls_name = rng.choice(_CLASSES)
    method = rng.choice(_METHODS)

    env = rng.choice(_ENVS) if rng.random() < 0.5 else None           # модульный pytestmark
    m = len(env) if env else 1
    ev = ", env" if env else ""                                       # параметр модуля должен быть в сигнатуре каждого теста
    a_vals = list(range(1, rng.randint(2, 3) + 1))                      # параметр класса
    b_vals = rng.sample(_FORMATS, rng.randint(2, 3))                    # параметр метода
    skip = 1 if kind in (1, 2) or rng.random() < 0.6 else 0             # pytest.param(..., marks=skip)
    skip_pos = rng.randrange(len(b_vals)) if skip else -1
    second_class = rng.random() < 0.5
    x_vals = rng.sample([10, 20, 30, 40], rng.randint(2, 3))           # дальний декоратор функции
    y_vals = list(range(1, rng.randint(2, 3) + 1))                      # ближний декоратор функции

    a, b, x, y = len(a_vals), len(b_vals), len(x_vals), len(y_vals)
    u = 1 if second_class else 0
    collected = m * (a * b + a + u + x * y)
    skipped = m * a * skip
    executed = collected - skipped
    fixture_calls = {f_mod: 1, f_cls: 1 + u, f_fn: m * (a * (b - skip) + u + x * y)}

    b_items = []
    for i, v in enumerate(b_vals):
        b_items.append(f'pytest.param("{v}", marks=pytest.mark.skip(reason="not ready"))' if i == skip_pos else f'"{v}"')
    lines = ["import pytest", ""]
    if env:
        lines += [f'pytestmark = pytest.mark.parametrize("env", {env!r})', "", ""]
    lines += [
        '@pytest.fixture(scope="module")',
        f"def {f_mod}():",
        "    return object()",
        "", "",
        '@pytest.fixture(scope="class")',
        f"def {f_cls}():",
        "    return {}",
        "", "",
        "@pytest.fixture",
        f"def {f_fn}({f_mod}):",
        "    return object()",
        "", "",
        f'@pytest.mark.parametrize("a", {a_vals!r})',
        f"class {cls_name}:",
        f'    @pytest.mark.parametrize("fmt", [{", ".join(b_items)}])',
        f"    def {method}(self, a, fmt{ev}, {f_fn}, {f_cls}):",
        "        assert a",
        "",
        f"    def test_list(self, a{ev}, {f_cls}):",
        "        assert a",
    ]
    if second_class:
        lines += ["", "", "class TestUsers:", f"    def test_me(self{ev}, {f_cls}, {f_fn}):", "        assert True"]
    lines += [
        "", "",
        f'@pytest.mark.parametrize("x", {x_vals!r})',
        f'@pytest.mark.parametrize("y", {y_vals!r})',
        f"def test_total(x, y{ev}, {f_fn}):",
        "    assert x + y",
    ]
    code = "\n".join(lines)

    mod_note = f" и модульный pytestmark умножает всё на {m}" if env else ""
    skip_note = (f" (в том числе {skipped} с маркером skip: pytest.param с marks=skip собирается, но не выполняется)"
                 if skip else "")
    parts = [f"{cls_name}.{method}: {a}·{b} = {a * b}", f"{cls_name}.test_list: {a}"]
    if second_class:
        parts.append("TestUsers.test_me: 1")
    parts.append(f"test_total: {x}·{y} = {x * y}")
    breakdown = ", ".join(parts)

    if kind == 0:
        q = "Сколько тестов соберёт pytest для этого модуля (включая пропущенные)? Введите число."
        expl = (f"Параметры перемножаются: класс × метод, а стек декораторов на функции — произведение. "
                f"{breakdown}{mod_note}. Итого собрано {collected}{skip_note}.")
        return Instance(question=q, answer=str(collected), code=code, language="text", explanation=expl)

    if kind == 1:
        q = "Сколько тестов pytest выполнит (пропущенные не считаются)? Введите число."
        expl = (f"Собрано {collected} ({breakdown}{mod_note}). Экземпляры {method} со значением fmt под "
                f"pytest.param(..., marks=skip) — по одному на каждое значение a{' и env' if env else ''}, "
                f"то есть {skipped} — собираются, но пропускаются. Выполнено {collected} − {skipped} = {executed}.")
        return Instance(question=q, answer=str(executed), code=code, language="text", explanation=expl)

    if kind == 2:
        name = rng.choice([f_mod, f_cls, f_fn])
        ans = fixture_calls[name]
        if name == f_mod:
            expl = (f"Фикстура {name} объявлена со scope=\"module\": создаётся один раз при первом запросе и живёт до "
                    f"конца модуля, сколько бы тестов (и параметров) её ни использовали — через {f_fn} её запрашивают "
                    f"{fixture_calls[f_fn]} выполненных тестов.")
        elif name == f_cls:
            expl = (f"Фикстура {name} объявлена со scope=\"class\": по одному экземпляру на каждый класс, где она запрошена "
                    f"({'два класса' if second_class else 'один класс'}), независимо от числа параметризованных методов. "
                    f"Итого {ans}.")
        else:
            expl = (f"Фикстура {name} функциональная (scope по умолчанию): создаётся для каждого выполненного теста, "
                    f"который её запрашивает. Пропущенные экземпляры ({skipped}) до создания фикстур не доходят. "
                    f"{cls_name}.{method}: {m}·{a}·({b} − {skip}) = {m * a * (b - skip)}"
                    + (f", TestUsers.test_me: {m}" if second_class else "")
                    + f", test_total: {m}·{x}·{y} = {m * x * y}. Итого {ans}.")
        q = f"Сколько раз pytest создаст фикстуру {name} за прогон этого модуля? Введите число."
        return Instance(question=q, answer=str(ans), code=code, language="text", explanation=expl)

    # kind == 3: идентификатор k-го собранного экземпляра test_total
    ids = []
    for yv in y_vals:                      # ближний декоратор — первый в id, меняется медленнее всего
        for xv in x_vals:                  # дальний декоратор
            for ev in (env or [None]):     # модульный параметр — последний в id, меняется быстрее всех
                ids.append(f"test_total[{yv}-{xv}" + (f"-{ev}]" if ev else "]"))
    k = rng.randint(2, min(4, len(ids)))
    ans = ids[k - 1]
    q = (f"Какой идентификатор получит {k}-й по порядку сбора экземпляр test_total? Введите так, как печатает "
         "pytest --collect-only, без имени файла (вида test_total[...]).")
    expl = ("В идентификаторе параметры идут от ближайшего к функции декоратора к дальнему" +
            (", затем модульный env" if env else "") +
            "; ближайший параметр (y) перебирается медленнее всего, дальний (x) — быстрее" +
            (", env — быстрее всех" if env else "") +
            f". Порядок: {', '.join(ids[:k])}. {k}-й — {ans}.")
    return Instance(question=q, answer=ans, code=code, language="text", explanation=expl)
