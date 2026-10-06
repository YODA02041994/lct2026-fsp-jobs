"""Шаблоны: тестирование — теория тестирования, pytest, API-тесты, SQL для тестировщика, Selenium/Playwright.

Ключи exact: SQL — через sqlite3, остальное — целочисленный подсчёт по показанным данным.
"""
from __future__ import annotations
import math
import random

from .base import template, Instance
from .common import _sql_eval, _sql_block, _choice, _multi, _number_options, _NAMES

SPEC = ["qa"]


# ---------------------------------------------------------------------------------------------
# Junior
# ---------------------------------------------------------------------------------------------

@template("qa_theory_equivalence_classes", title="Классы эквивалентности и границы", competency="Тест-дизайн: классы эквивалентности",
          specializations=SPEC, technologies=["testing_theory"], fmt="exact", grade_level="junior", difficulty_shift=-0.3)
def _qa_classes(rng: random.Random) -> Instance:
    field = rng.choice(["Возраст", "Количество товара", "Скидка, %", "Число участников"])
    a = rng.choice([1, 5, 10, 18])
    b = a + rng.choice([20, 50, 82])
    while True:
        vals = rng.sample(list(range(a - 3, a + 3)) + list(range(b - 2, b + 4)) + [(a + b) // 2], 7)
        invalid = sum(1 for v in vals if v < a or v > b)
        if 2 <= invalid <= 5:
            break
    rng.shuffle(vals)
    return Instance(question=f"Поле «{field}» принимает целые значения от {a} до {b} включительно. Подготовлены тестовые "
                             f"значения: {', '.join(map(str, vals))}. Сколько из них относятся к невалидным классам "
                             "эквивалентности? Введите число.", answer=str(invalid),
                    explanation=f"Невалидны значения меньше {a} и больше {b}; границы {a} и {b} входят в валидный класс.")


@template("qa_theory_full_combinations", title="Полный перебор комбинаций", competency="Тест-дизайн: комбинаторика",
          specializations=SPEC, technologies=["testing_theory"], fmt="exact", grade_level="junior", difficulty_shift=0.0)
def _qa_full_comb(rng: random.Random) -> Instance:
    params = rng.sample([("браузер", [2, 3, 4]), ("ОС", [2, 3]), ("язык интерфейса", [2, 3, 5]), ("тип аккаунта", [2, 3]),
                         ("способ оплаты", [3, 4])], 3)
    counts = [rng.choice(c) for _, c in params]
    total = math.prod(counts)
    desc = ", ".join(f"{p} — {k} значения" if k < 5 else f"{p} — {k} значений" for (p, _), k in zip(params, counts))
    return Instance(question=f"Параметры формы: {desc}. Сколько тест-кейсов нужно для полного перебора всех комбинаций "
                             "значений? Введите число.", answer=str(total),
                    explanation=f"Полный перебор — произведение числа значений: {' × '.join(map(str, counts))} = {total}.")


@template("qa_theory_test_types", title="Вид тестирования по описанию", competency="Теория тестирования: виды тестов",
          specializations=SPEC, technologies=["testing_theory"], fmt="choice", grade_level="junior", difficulty_shift=-0.2)
def _qa_types(rng: random.Random) -> Instance:
    feat = rng.choice(["оплаты", "регистрации", "поиска", "экспорта отчётов"])
    cases = [
        ("Быстрая проверка, что сборка вообще запускается и ключевые функции доступны, перед подробным тестированием.", "Дымовое (smoke)",
         "Smoke — поверхностная проверка работоспособности сборки."),
        (f"После исправления дефекта в модуле {feat} перепроверяют, не сломалось ли то, что раньше работало, по всему продукту.", "Регрессионное",
         "Регрессия — проверка, что изменения не сломали существующее."),
        (f"После исправления дефекта проверяют узко именно функцию {feat}, без прогона всего набора.", "Санитарное (sanity)",
         "Sanity — узкая проверка конкретной исправленной области."),
        ("Заказчик проверяет, что система соответствует требованиям и готова к использованию.", "Приёмочное",
         "Приёмочное тестирование подтверждает соответствие требованиям заказчика."),
        (f"Тестировщик без заранее написанных кейсов изучает функцию {feat}, одновременно проектируя и выполняя проверки.", "Исследовательское",
         "Исследовательское — одновременное изучение, проектирование и выполнение тестов."),
        (f"Проверяют, как сервис {feat} ведёт себя при тысяче одновременных пользователей.", "Нагрузочное",
         "Нагрузочное — поведение под заданной нагрузкой."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    options = [c[1] for c in cases]
    return _choice(rng, f"{text} Как называется такой вид тестирования?", options, idx, expl)


@template("qa_theory_bug_report", title="Что обязательно в баг-репорте", competency="Тестовая документация: баг-репорт",
          specializations=SPEC, technologies=["testing_theory"], fmt="multichoice", grade_level="junior", difficulty_shift=-0.1)
def _qa_bug_report(rng: random.Random) -> Instance:
    where = rng.choice(["в корзине", "на странице оплаты", "в профиле", "в фильтре каталога"])
    true_pool = ["Шаги воспроизведения", "Ожидаемый и фактический результат", "Окружение: версия сборки, браузер или ОС",
                 "Серьёзность и приоритет"]
    false_pool = ["Имя разработчика, виноватого в ошибке", "Обязательное предложение, как исправить код",
                  "Полный лог всех действий тестировщика за день", "Оценка качества работы команды"]
    k = rng.randint(2, 3)
    return _multi(rng, f"Найден дефект {where}. Что обязательно должно быть в баг-репорте? Выберите все подходящие.",
                  rng.sample(true_pool, k), rng.sample(false_pool, 6 - k),
                  "Баг-репорт должен позволить воспроизвести и оценить дефект: шаги, ожидание/факт, окружение, серьёзность. "
                  "Поиск виноватых и предложения по коду — не его задача.")


@template("qa_pytest_parametrize_count", title="Сколько тестов соберёт pytest", competency="pytest: параметризация",
          specializations=SPEC, technologies=["pytest", "python"], fmt="choice", grade_level="junior", difficulty_shift=0.1)
def _qa_parametrize(rng: random.Random) -> Instance:
    na, nb, nn = rng.randint(2, 4), rng.randint(2, 3), rng.randint(2, 5)
    a_vals = ", ".join(map(str, rng.sample(range(1, 20), na)))
    b_vals = ", ".join(f'"{c}"' for c in rng.sample(["x", "y", "z", "w"], nb))
    n_vals = ", ".join(map(str, range(nn)))
    plain = rng.random() < 0.5
    code = ("import pytest\n\n"
            f'@pytest.mark.parametrize("a", [{a_vals}])\n'
            f'@pytest.mark.parametrize("b", [{b_vals}])\n'
            "def test_pair(a, b):\n    assert a and b\n\n"
            f'@pytest.mark.parametrize("n", [{n_vals}])\n'
            "def test_single(n):\n    assert n >= 0\n")
    if plain:
        code += "\ndef test_plain():\n    assert True\n"
    total = na * nb + nn + (1 if plain else 0)
    wrong_typical = [na + nb + nn + (1 if plain else 0), na * nb * nn, na * nb + nn + (0 if plain else 1), 3 if plain else 2]
    options, correct = _number_options(rng, total, wrong_typical)
    return _choice(rng, "Сколько тестов соберёт pytest из этого файла?", options, correct,
                   f"Два параметризатора перемножаются: {na} × {nb} = {na * nb}; плюс {nn} у test_single"
                   + (" и один обычный тест." if plain else "."), code=code, language="python")


@template("qa_api_expected_status", title="Ожидаемый код ответа в API-тесте", competency="Тестирование API: коды ответов",
          specializations=SPEC, technologies=["postman", "rest"], fmt="choice", grade_level="junior", difficulty_shift=-0.2)
def _qa_api_status(rng: random.Random) -> Instance:
    res = rng.choice(["orders", "users", "tickets"])
    oid = rng.randint(1000, 9999)
    cases = [
        (f"GET /{res}/{oid}, ресурс существует", "200", "Успешное чтение — 200."),
        (f"GET /{res}/{oid}, такого ресурса нет", "404", "Нет ресурса — 404."),
        (f"POST /{res} с валидным телом", "201", "Создание — 201 Created."),
        (f"DELETE /{res}/{oid}, успешно, тело пустое", "204", "Успех без тела — 204."),
        (f"GET /{res} без токена авторизации", "401", "Нет аутентификации — 401."),
        (f"POST /{res} с телом, которое не проходит валидацию схемы", "422", "Ошибка валидации в типичных REST-фреймворках — 422 (или 400)."),
        (f"PATCH /{res}, когда для коллекции разрешены только GET и POST", "405", "Метод не поддерживается — 405."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    pool = ["200", "201", "204", "400", "401", "403", "404", "405", "422", "500"]
    wrong = [p for p in pool if p != correct and not (correct == "422" and p == "400")]
    return _choice(rng, f"В тесте проверяется запрос: {text}. Какой код ответа ожидать?", [correct] + rng.sample(wrong, 5), 0, expl)


@template("qa_sql_test_data", title="Проверить тестовые данные запросом", competency="SQL для тестировщика: выборка",
          specializations=SPEC, technologies=["sql"], fmt="exact", grade_level="junior", difficulty_shift=0.0)
def _qa_sql_data(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(7, 8)
        rows = [(i + 1, rng.choice(["open", "closed", "in_progress"]), rng.choice(["low", "high"]), rng.randint(1, 30))
                for i in range(n)]
        tables = {"tickets": (["id", "status", "priority", "age_days"], rows)}
        st = rng.choice(["open", "closed", "in_progress"])
        kind = rng.randrange(3)
        if kind == 0:
            query = f"SELECT COUNT(*) FROM tickets\nWHERE status = '{st}' AND priority = 'high';"
            expl = f"Считаются тикеты со статусом {st} и высоким приоритетом."
        elif kind == 1:
            d = rng.randint(7, 20)
            query = f"SELECT COUNT(*) FROM tickets\nWHERE status <> 'closed' AND age_days > {d};"
            expl = f"Незакрытые тикеты старше {d} дней."
        else:
            query = "SELECT COUNT(*) FROM tickets\nWHERE status IN ('open', 'in_progress');"
            expl = "IN эквивалентно OR по перечисленным статусам."
        ans = _sql_eval(tables, query)[0][0]
        if 1 <= ans <= n - 1:
            break
    return Instance(question="Какое число вернёт запрос? Введите число.", answer=str(ans), code=_sql_block(tables, query),
                    language="sql", explanation=expl)


# ---------------------------------------------------------------------------------------------
# Middle
# ---------------------------------------------------------------------------------------------

@template("qa_pytest_fixture_scope", title="Сколько раз создастся фикстура", competency="pytest: фикстуры и области действия",
          specializations=SPEC, technologies=["pytest", "python"], fmt="choice", grade_level="middle", difficulty_shift=0.0)
def _qa_fixture_scope(rng: random.Random) -> Instance:
    modules = rng.randint(2, 4)
    per_module = [rng.randint(2, 5) for _ in range(modules)]
    total_tests = sum(per_module)
    scope = rng.choice(["function", "module", "session"])
    name = rng.choice(["db", "client", "browser"])
    code = (f'@pytest.fixture(scope="{scope}")\n'
            f"def {name}():\n    conn = connect()\n    yield conn\n    conn.close()")
    calls = {"function": total_tests, "module": modules, "session": 1}[scope]
    desc = ", ".join(f"test_{chr(97 + i)}.py — {k}" for i, k in enumerate(per_module))
    options, correct = _number_options(rng, calls, [total_tests, modules, 1, total_tests * modules])
    expl = {"function": "scope=function — фикстура создаётся заново для каждого теста.",
            "module": "scope=module — один экземпляр на модуль, сколько модулей — столько созданий.",
            "session": "scope=session — один экземпляр на весь прогон."}[scope]
    return _choice(rng, f"Фикстура {name} (в conftest.py) используется тестами в {modules} модулях; число тестов по "
                        f"модулям: {desc}. Сколько раз выполнится connect() за один прогон?", options, correct, expl,
                   code=code, language="python")


@template("qa_sql_duplicates", title="Найти дубликаты запросом", competency="SQL для тестировщика: проверка уникальности",
          specializations=SPEC, technologies=["sql"], fmt="exact", grade_level="middle", difficulty_shift=-0.1)
def _qa_sql_dupes(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(7, 8)
        base = rng.sample(["ann", "bob", "eva", "kir", "lev", "oli"], 4)
        emails = [f"{rng.choice(base)}@test.ru" for _ in range(n)]
        rows = [(i + 1, rng.choice(_NAMES), emails[i]) for i in range(n)]
        tables = {"users": (["id", "name", "email"], rows)}
        if rng.random() < 0.6:
            query = "SELECT email, COUNT(*) AS cnt\nFROM users\nGROUP BY email\nHAVING COUNT(*) > 1;"
            ans = len(_sql_eval(tables, query))
            q = "Сколько строк вернёт запрос? Введите число."
            expl = "Каждая строка результата — e-mail, встречающийся больше одного раза."
            hi = len(set(emails)) - 1
        else:
            query = "SELECT COUNT(*) - COUNT(DISTINCT email) FROM users;"
            ans = _sql_eval(tables, query)[0][0]
            q = "Какое число вернёт запрос? Введите число."
            expl = "Разность всех строк и уникальных e-mail — число «лишних» (повторных) строк."
            hi = n - 2
        if 1 <= ans <= hi:
            break
    return Instance(question=q, answer=str(ans), code=_sql_block(tables, query), language="sql", explanation=expl)


@template("qa_locator_stability", title="Устойчивый локатор", competency="Автотесты UI: локаторы",
          specializations=SPEC, technologies=["selenium", "playwright"], fmt="choice", grade_level="middle", difficulty_shift=-0.2)
def _qa_locator(rng: random.Random) -> Instance:
    testid = rng.choice(["checkout-submit", "login-button", "save-profile", "add-to-cart"])
    gen_cls = "css-" + "".join(rng.choice("abcdef0123456789") for _ in range(6))
    gen_id = "btn-" + "".join(rng.choice("0123456789abcdef") for _ in range(4))
    label = rng.choice(["Оформить", "Войти", "Сохранить", "В корзину"])
    pos = rng.randint(2, 5)
    code = f'<button class="btn btn-primary {gen_cls}" id="{gen_id}" data-testid="{testid}">{label}</button>'
    correct = f'[data-testid="{testid}"]'
    wrong = [f".{gen_cls}", f"#{gen_id}", f"//div/button[{pos}]", ".btn.btn-primary", f'text="{label}"']
    return _choice(rng, "Какой локатор для кнопки наиболее устойчив к изменениям вёрстки, стилей и локализации?",
                   [correct] + wrong, 0,
                   "data-testid добавлен специально для тестов и не меняется при правках стилей, генерируемых классов/id, "
                   "положения в DOM и перевода текста.", code=code, language="html")


@template("qa_flaky_wait", title="Нестабильный тест из-за ожидания", competency="Автотесты UI: синхронизация",
          specializations=SPEC, technologies=["playwright", "selenium"], fmt="choice", grade_level="middle", difficulty_shift=0.0)
def _qa_flaky(rng: random.Random) -> Instance:
    btn = rng.choice(["Сохранить", "Отправить", "Оплатить"])
    msg = rng.choice(["Изменения сохранены", "Заявка отправлена", "Платёж принят"])
    pct = rng.choice([10, 20, 30])
    text = (f"Тест нажимает «{btn}» и сразу проверяет текст уведомления «{msg}». Примерно в {pct} % прогонов падает: "
            "уведомления в этот момент ещё нет, через секунду оно появляется.")
    correct = ("Явно дождаться условия — появления/видимости уведомления (expect(...).toBeVisible(), WebDriverWait с "
               "expected_conditions) — и только потом проверять текст")
    wrong = [
        "Добавить sleep(5) после клика",
        "Настроить автоматический перезапуск упавшего теста до трёх раз",
        "Убрать проверку уведомления — главное, что клик прошёл",
        "Увеличить глобальный таймаут всего прогона",
        "Запускать тесты только последовательно, без параллельности",
    ]
    return _choice(rng, f"{text} Как исправить правильно?", [correct] + wrong, 0,
                   "Причина — гонка между действием и проверкой; её устраняет ожидание конкретного условия. Фиксированные паузы "
                   "и перезапуски маскируют проблему и замедляют прогон.")


@template("qa_theory_severity_priority", title="Серьёзность и приоритет", competency="Теория тестирования: оценка дефекта",
          specializations=SPEC, technologies=["testing_theory"], fmt="choice", grade_level="middle", difficulty_shift=0.1)
def _qa_severity(rng: random.Random) -> Instance:
    days = rng.randint(1, 3)
    cases = [
        (f"Опечатка в названии компании на главной странице; релиз через {days} дн.", "Низкая серьёзность, высокий приоритет",
         "Функциональность не затронута (низкая серьёзность), но репутационно важно и срочно (высокий приоритет)."),
        ("Оплата падает у всех пользователей на последнем шаге.", "Критическая серьёзность, высокий приоритет",
         "Блокирует ключевой сценарий у всех — критично и срочно."),
        ("Приложение закрывается при открытии редко используемого раздела настроек, доступного 1 % пользователей.", "Высокая серьёзность, низкий приоритет",
         "Падение — высокая серьёзность, но редкий сценарий можно починить позже."),
        ("Кнопка на внутренней странице смещена на 2 px относительно макета.", "Низкая серьёзность, низкий приоритет",
         "Косметика без влияния на работу и без срочности."),
        ("Экспорт отчёта работает, но на больших данных занимает 40 секунд вместо 5; жалоб мало.", "Средняя серьёзность, средний приоритет",
         "Функция работает, но деградирует; чинить в плановом порядке."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    options = [c[1] for c in cases] + ["Критическая серьёзность, низкий приоритет"]
    return _choice(rng, f"{text} Как оценить дефект?", options, idx, expl)


@template("qa_api_response_checks", title="Что проверять в API-тесте", competency="Тестирование API: проверки ответа",
          specializations=SPEC, technologies=["postman", "rest"], fmt="multichoice", grade_level="middle", difficulty_shift=-0.1)
def _qa_api_checks(rng: random.Random) -> Instance:
    res = rng.choice(["orders", "bookings", "invoices"])
    ms = rng.choice([137, 212, 348])
    true_pool = [
        "Код ответа — 201",
        "Схему тела ответа: обязательные поля и их типы",
        f"Что созданный объект действительно читается через GET /{res}/{{id}} с теми же данными",
        "Что в теле ответа значения соответствуют отправленным (кроме генерируемых сервером)",
    ]
    false_pool = [
        f"Что ответ пришёл ровно за {ms} мс",
        f"Что id созданного объекта равен жёстко заданному числу",
        "Что в заголовке Server указана версия nginx",
        "Что тело ответа совпадает байт в байт с сохранённым год назад эталоном",
    ]
    k = rng.randint(2, 3)
    return _multi(rng, f"Пишется автотест на успешный POST /{res}. Что в нём стоит проверять? Выберите все подходящие.",
                  rng.sample(true_pool, k), rng.sample(false_pool, 6 - k),
                  "Проверяются контракт (код, схема, соответствие данных) и результат (объект создан). Точное время, "
                  "конкретные id и побайтовые эталоны делают тест хрупким без пользы.")


# ---------------------------------------------------------------------------------------------
# Senior
# ---------------------------------------------------------------------------------------------

@template("qa_pairwise_lower_bound", title="Нижняя граница попарного покрытия", competency="Тест-дизайн: pairwise",
          specializations=SPEC, technologies=["testing_theory"], fmt="exact", grade_level="senior", difficulty_shift=-0.1)
def _qa_pairwise(rng: random.Random) -> Instance:
    names = rng.sample(["браузер", "ОС", "язык интерфейса", "тип аккаунта", "способ оплаты", "валюта"], 4)
    while True:
        counts = [rng.randint(2, 6) for _ in range(4)]
        srt = sorted(counts, reverse=True)
        if srt[0] != srt[1] or srt[1] != srt[2]:
            break
    full = math.prod(counts)
    bound = srt[0] * srt[1]
    desc = ", ".join(f"{n} — {k}" for n, k in zip(names, counts))
    return Instance(question=f"Параметры (число значений): {desc}. Полный перебор даёт {full} комбинаций. Каково минимально "
                             "возможное число тестов для попарного (pairwise) покрытия, то есть нижняя граница? Введите число.",
                    answer=str(bound),
                    explanation=f"Каждая пара значений двух самых «широких» параметров должна встретиться хотя бы раз: "
                                f"{srt[0]} × {srt[1]} = {bound}. Это нижняя граница; реальные наборы могут быть чуть больше.")


@template("qa_api_contract_testing", title="Тестирование до готовности бэкенда", competency="Тестирование API: контракты и моки",
          specializations=SPEC, technologies=["postman", "rest"], fmt="choice", grade_level="senior", difficulty_shift=0.0)
def _qa_contract(rng: random.Random) -> Instance:
    weeks = rng.randint(2, 4)
    svc = rng.choice(["платежей", "доставки", "уведомлений"])
    text = (f"Фронтенд и автотесты готовы, а сервис {svc} бэкенд допишет только через {weeks} недели; OpenAPI-спецификация "
            "согласована и подписана обеими командами.")
    correct = ("Поднять мок-сервер по OpenAPI-спецификации, писать и гонять тесты против него, а контракт проверять "
               "контрактными тестами на обеих сторонах при появлении реального сервиса")
    wrong = [
        f"Ждать {weeks} недели и начать тестирование после готовности сервиса",
        "Тестировать на проде соседней команды, у которой похожий сервис",
        "Захардкодить в тестах ожидаемые ответы и не проверять их против сервиса вообще",
        "Попросить бэкенд выкатить недоделанный сервис в прод для тестов",
        "Отменить автотесты API и проверить всё вручную после релиза",
    ]
    return _choice(rng, f"{text} Как организовать тестирование?", [correct] + wrong, 0,
                   "Согласованный контракт позволяет работать параллельно: моки по спецификации для разработки тестов и "
                   "контрактные тесты, чтобы реальный сервис не разошёлся со спецификацией.")


# ---------------------------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------------------------

@template("qa_lead_test_pyramid", title="Медленный и хрупкий набор e2e", competency="Стратегия тестирования: пирамида",
          specializations=SPEC, technologies=["testing_theory", "ci_cd"], fmt="choice", grade_level="lead", difficulty_shift=-0.1)
def _qa_lead_pyramid(rng: random.Random) -> Instance:
    n = rng.choice([600, 900, 1400])
    hours = rng.choice([3, 4, 6])
    every = rng.choice([3, 4])
    text = (f"В проекте {n} e2e-тестов через браузер, прогон {hours} ч, падает каждый {every}-й прогон из-за "
            "нестабильности; юнит- и интеграционных тестов почти нет. Релизы задерживаются.")
    correct = ("Перенести проверки бизнес-логики на уровень юнит- и интеграционных тестов, оставить e2e для ключевых "
               "сквозных сценариев, нестабильные тесты — в карантин с задачами на починку")
    wrong = [
        "Купить больше агентов CI, чтобы прогон занимал час, и ничего не менять в наборе",
        "Удалить все e2e-тесты и перейти на ручное регрессионное тестирование",
        "Включить автоперезапуск упавших тестов до пяти раз",
        f"Запретить релизы, пока все {n} тестов не станут стабильными",
        "Писать e2e-тесты только силами разработчиков вместо QA",
    ]
    return _choice(rng, f"{text} Какую стратегию выбрать?", [correct] + wrong, 0,
                   "Пирамида тестирования: быстрые и дешёвые проверки внизу, немного e2e наверху; нестабильность чинится, "
                   "а не маскируется перезапусками и дополнительным железом.")


@template("qa_lead_flaky_policy", title="Политика работы с нестабильными тестами", competency="Процессы QA: качество автотестов",
          specializations=SPEC, technologies=["testing_theory", "ci_cd"], fmt="multichoice", grade_level="lead", difficulty_shift=0.1)
def _qa_lead_flaky(rng: random.Random) -> Instance:
    pct = rng.choice([5, 8, 12])
    true_pool = [
        "Карантин: нестабильный тест помечается, исключается из блокирующего прогона, на него заводится задача со сроком",
        "Собирать статистику стабильности по каждому тесту и держать её на виду у команды",
        "Искать и устранять причины: неявные ожидания, общие тестовые данные, зависимость от порядка",
    ]
    false_pool = [
        "Автоматически перезапускать любой упавший тест до пяти раз без разбора",
        "Удалять любой тест, который упал дважды",
        "Навсегда запретить параллельный запуск тестов",
        "Считать красный прогон нормой и сливать по решению автора PR",
    ]
    k = rng.randint(2, 3)
    return _multi(rng, f"Около {pct} % прогонов CI красные из-за нестабильных тестов, разработчики перестали обращать "
                       "внимание на результат. Какие меры входят в здоровую политику? Выберите все подходящие.",
                  rng.sample(true_pool, k), rng.sample(false_pool, 6 - k),
                  "Нестабильность измеряют, изолируют (карантин со сроком) и чинят по причинам; слепые перезапуски и "
                  "удаление тестов разрушают доверие к набору.")
