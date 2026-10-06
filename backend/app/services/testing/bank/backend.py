"""Шаблоны: бэкенд — Python, FastAPI, REST, PostgreSQL, асинхронность, Docker.

Ключи exact-заданий с кодом на Python считаются исполнением фрагмента (_run_python), SQL — через sqlite3 (_sql_eval).
"""
from __future__ import annotations
import random

from .base import template, Instance
from .common import _run_python, _sql_eval, _sql_block, _choice, _multi, _NAMES, _CITIES

SPEC = ["backend"]


# ---------------------------------------------------------------------------------------------
# Python: чтение кода (junior)
# ---------------------------------------------------------------------------------------------

@template("backend_py_dict_count", title="Подсчёт через словарь", competency="Python: словари и подсчёт",
          specializations=SPEC, technologies=["python"], fmt="exact", grade_level="junior", difficulty_shift=-0.3)
def _py_dict_count(rng: random.Random) -> Instance:
    tokens = rng.sample(["get", "post", "put", "delete", "patch"], 3)
    words = [rng.choice(tokens) for _ in range(rng.randint(7, 10))]
    var = rng.choice(["counts", "stats", "freq"])
    if rng.random() < 0.5:
        target = rng.choice(words)
        tail = f'print({var}["{target}"])'
        expl = f"Словарь накапливает число вхождений каждого слова; у «{target}» оно равно ответу."
    else:
        tail = f"print(len({var}))"
        expl = "len словаря — число различных ключей, то есть различных слов."
    code = (f'words = "{" ".join(words)}".split()\n'
            f"{var} = {{}}\n"
            "for w in words:\n"
            f"    {var}[w] = {var}.get(w, 0) + 1\n"
            f"{tail}")
    return Instance(question="Что выведет код? Введите число.", answer=_run_python(code), code=code, language="python",
                    explanation=expl)


@template("backend_py_slicing", title="Срезы списка", competency="Python: срезы",
          specializations=SPEC, technologies=["python"], fmt="exact", grade_level="junior", difficulty_shift=-0.2)
def _py_slicing(rng: random.Random) -> Instance:
    xs = rng.sample(range(1, 20), rng.randint(6, 7))
    var = rng.choice(["xs", "nums", "data"])
    a = rng.randint(1, 2)
    b = rng.randint(a + 2, len(xs) - 1)
    slices = [
        (f"{var}[{a}:{b}]", f"Срез берёт элементы с индекса {a} до {b} (правая граница не включается)."),
        (f"{var}[::-1]", "Шаг −1 перебирает список с конца."),
        (f"{var}[::2]", "Шаг 2 берёт каждый второй элемент, начиная с нулевого."),
        (f"{var}[-3:]", "Отрицательный старт отсчитывает от конца: последние три элемента."),
        (f"{var}[:-2]", "Отрицательный стоп отбрасывает два последних элемента."),
        (f"{var}[{a}::2]", f"Старт {a}, шаг 2 — каждый второй элемент начиная с индекса {a}."),
    ]
    sl, expl = rng.choice(slices)
    code = f"{var} = {xs}\nprint(*{sl})"
    return Instance(question="Что выведет код? Введите значения через пробел.", answer=_run_python(code), code=code,
                    language="python", explanation=expl)


@template("backend_py_string_ops", title="Методы строк", competency="Python: строки",
          specializations=SPEC, technologies=["python"], fmt="exact", grade_level="junior", difficulty_shift=0.0)
def _py_string_ops(rng: random.Random) -> Instance:
    words = rng.sample(["data", "api", "cache", "queue", "token", "user", "order"], rng.randint(3, 4))
    sep = rng.choice([",", ";", " "])
    s = sep.join(words)
    var = rng.choice(["s", "text", "line"])
    kinds = [
        (f'print(len({var}.split("{sep}")))', "split делит строку по разделителю; элементов столько же, сколько слов."),
        (f'print("-".join({var}.split("{sep}")).upper())', "split разбивает по разделителю, join склеивает через дефис, upper поднимает регистр."),
        (f'print({var}.replace("{sep}", "").count("a"))', "После удаления разделителей считается число букв a."),
        (f'print({var}.split("{sep}")[-1][::-1])', "Последнее слово после split переворачивается срезом с шагом −1."),
        (f'print({var}.title().split("{sep}")[0])', "title делает заглавной первую букву каждого слова, берём первое."),
    ]
    tail, expl = rng.choice(kinds)
    code = f'{var} = "{s}"\n{tail}'
    return Instance(question="Что выведет код? Введите значение без кавычек.", answer=_run_python(code), code=code,
                    language="python", explanation=expl)


@template("backend_rest_design", title="REST: метод и путь по действию", competency="REST: проектирование ресурсов",
          specializations=SPEC, technologies=["rest", "http"], fmt="choice", grade_level="junior", difficulty_shift=0.0)
def _rest_design(rng: random.Random) -> Instance:
    res, sub = rng.choice([("users", "orders"), ("projects", "tasks"), ("teams", "members"), ("courses", "lessons")])
    uid = rng.randint(2, 99)
    cases = [
        (f"получить список {sub} элемента {res} с id={uid}", f"GET /{res}/{uid}/{sub}",
         "Вложенный ресурс читается GET по иерархическому пути."),
        (f"изменить одно поле элемента {res} с id={uid}, остальные не трогать", f"PATCH /{res}/{uid}",
         "Частичное обновление — PATCH на адрес ресурса."),
        (f"полностью заменить представление элемента {res} с id={uid}", f"PUT /{res}/{uid}",
         "Полная замена — PUT на адрес ресурса."),
        (f"создать новый элемент {res}", f"POST /{res}", "Создание — POST на коллекцию; id назначает сервер."),
        (f"удалить элемент {res} с id={uid}", f"DELETE /{res}/{uid}", "Удаление — DELETE на адрес ресурса."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    pool = [c[1] for c in cases] + [f"GET /get{res.capitalize()}?id={uid}", f"POST /{res}/{uid}/delete", f"GET /{res}/{uid}/update"]
    wrong = [p for p in pool if p != correct]
    return _choice(rng, f"Нужно {text}. Какой запрос соответствует соглашениям REST?", [correct] + rng.sample(wrong, 5), 0, expl)


@template("backend_docker_compose_dns", title="Адрес сервиса внутри docker compose", competency="Docker: сеть compose",
          specializations=SPEC, technologies=["docker"], fmt="choice", grade_level="junior", difficulty_shift=0.2)
def _docker_compose_dns(rng: random.Random) -> Instance:
    svc = rng.choice(["db", "postgres", "database"])
    host_port = rng.choice([5433, 15432, 54320])
    api = rng.choice(["api", "backend", "web"])
    compose = (f"services:\n  {api}:\n    build: .\n    depends_on: [{svc}]\n"
               f"  {svc}:\n    image: postgres:16\n    ports:\n      - \"{host_port}:5432\"")
    correct = f"{svc}:5432"
    wrong = [f"localhost:5432", f"localhost:{host_port}", f"{svc}:{host_port}", f"127.0.0.1:{host_port}", f"{api}:5432"]
    return _choice(rng, f"Какой host:port должен быть в строке подключения к базе внутри контейнера {api}?",
                   [correct] + wrong, 0,
                   f"Внутри сети compose сервисы доступны по имени сервиса и внутреннему порту: {svc}:5432. "
                   f"Проброс {host_port}:5432 нужен только для подключения с хоста; localhost в контейнере — сам контейнер.",
                   code=compose, language="text")


# ---------------------------------------------------------------------------------------------
# Python: чтение кода (middle)
# ---------------------------------------------------------------------------------------------

@template("backend_py_mutable_default", title="Изменяемое значение по умолчанию", competency="Python: аргументы по умолчанию",
          specializations=SPEC, technologies=["python"], fmt="exact", grade_level="middle", difficulty_shift=-0.2)
def _py_mutable_default(rng: random.Random) -> Instance:
    fn = rng.choice(["add", "push", "collect"])
    vals = rng.sample(range(1, 50), 4)
    fixed = rng.random() < 0.35
    if fixed:
        head = (f"def {fn}(item, bucket=None):\n    if bucket is None:\n        bucket = []\n"
                "    bucket.append(item)\n    return bucket\n\n")
        expl = "С bucket=None каждый вызов без аргумента получает новый список, поэтому в нём один элемент."
    else:
        head = f"def {fn}(item, bucket=[]):\n    bucket.append(item)\n    return bucket\n\n"
        expl = "Список по умолчанию создаётся один раз при определении функции и накапливает элементы между вызовами."
    calls = [f"{fn}({vals[0]})", f"{fn}({vals[1]})"]
    if rng.random() < 0.5:
        calls.append(f"{fn}({vals[2]}, [])")
        expl += " Вызов с явным списком на общий список не влияет."
    tail = f"print(len({fn}({vals[3]})))" if rng.random() < 0.5 else f'print(*{fn}({vals[3]}))'
    code = head + "\n".join(calls) + "\n" + tail
    q = "Что выведет код? " + ("Введите число." if tail.startswith("print(len") else "Введите значения через пробел.")
    return Instance(question=q, answer=_run_python(code), code=code, language="python", explanation=expl)


@template("backend_py_closure_late_binding", title="Замыкания в цикле", competency="Python: замыкания и позднее связывание",
          specializations=SPEC, technologies=["python"], fmt="exact", grade_level="middle", difficulty_shift=0.0)
def _py_closure(rng: random.Random) -> Instance:
    n = rng.randint(3, 4)
    k = rng.choice([2, 3, 5, 10])
    var = rng.choice(["fs", "funcs", "handlers"])
    bind = rng.random() < 0.4
    lam = f"lambda i=i: i * {k}" if bind else f"lambda: i * {k}"
    code = (f"{var} = []\nfor i in range({n}):\n    {var}.append({lam})\n"
            f'print(" ".join(str(f()) for f in {var}))')
    expl = ("Значение i зафиксировано аргументом по умолчанию в момент создания лямбды — каждая помнит своё i."
            if bind else
            f"Лямбды ссылаются на одну переменную i, которая после цикла равна {n - 1}; все вызовы дают одно значение.")
    return Instance(question="Что выведет код? Введите значения через пробел.", answer=_run_python(code), code=code,
                    language="python", explanation=expl)


@template("backend_py_generator", title="Генератор и next", competency="Python: генераторы и итераторы",
          specializations=SPEC, technologies=["python"], fmt="exact", grade_level="middle", difficulty_shift=0.1)
def _py_generator(rng: random.Random) -> Instance:
    while True:
        xs = rng.sample(range(1, 20), rng.randint(5, 6))
        cond = rng.choice(["x % 2 == 1", "x % 2 == 0", "x > 7", "x < 12"])
        mul = rng.choice([2, 3, 10])
        kept = [x for x in xs if eval(cond, {"x": x})]
        if len(kept) >= 3:
            break
    fn = rng.choice(["gen", "produce", "evens"])
    code = (f"def {fn}(items):\n    for x in items:\n        if {cond}:\n            yield x * {mul}\n\n"
            f"g = {fn}({xs})\nfirst = next(g)\nprint(first, sum(g))")
    return Instance(question="Что выведет код? Введите два числа через пробел.", answer=_run_python(code), code=code,
                    language="python",
                    explanation=f"next забирает первый подходящий элемент ({kept[0]} × {mul}); sum проходит оставшиеся — "
                                "генератор не начинает сначала.")


@template("backend_py_try_finally_order", title="Порядок try/except/else/finally", competency="Python: обработка исключений",
          specializations=SPEC, technologies=["python"], fmt="exact", grade_level="middle", difficulty_shift=0.3)
def _py_try_order(rng: random.Random) -> Instance:
    mode = rng.choice(["ok", "error", "early_return"])
    arg = 0 if mode == "error" else rng.randint(1, 9)
    early = "        if x == 1:\n            return log\n" if mode == "early_return" else ""
    if mode == "early_return":
        arg = 1
    fn = rng.choice(["run", "handle", "process"])
    code = ("log = []\n\n"
            f"def {fn}(x):\n"
            "    try:\n"
            '        log.append("try")\n'
            + early +
            "        value = 10 // x\n"
            "    except ZeroDivisionError:\n"
            '        log.append("except")\n'
            "    else:\n"
            '        log.append("else")\n'
            "    finally:\n"
            '        log.append("finally")\n'
            "    return log\n\n"
            f"{fn}({arg})\n"
            'print("-".join(log))')
    expl = {
        "ok": "Без исключения выполняются try, затем else, затем finally.",
        "error": "При делении на ноль срабатывает except, else пропускается, finally выполняется всегда.",
        "early_return": "return внутри try прерывает блок: else не выполняется, но finally выполняется всё равно.",
    }[mode]
    return Instance(question="Что выведет код? Введите строку без кавычек.", answer=_run_python(code), code=code,
                    language="python", explanation=expl)


@template("backend_sql_join_group", title="JOIN с группировкой", competency="SQL: соединение и агрегаты",
          specializations=SPEC, technologies=["sql", "postgresql"], fmt="exact", grade_level="middle", difficulty_shift=0.0)
def _sql_join_group(rng: random.Random) -> Instance:
    while True:
        nu = rng.randint(4, 5)
        names = rng.sample(_NAMES, nu)
        cities = rng.sample(_CITIES, 3)
        users = [(i + 1, names[i], rng.choice(cities)) for i in range(nu)]
        no = rng.randint(6, 8)
        orders = [(100 + j, rng.randint(1, nu), rng.randrange(100, 900, 100), rng.choice(["paid", "paid", "new"]))
                  for j in range(no)]
        tables = {"users": (["id", "name", "city"], users), "orders": (["id", "user_id", "amount", "status"], orders)}
        kind = rng.randrange(2)
        if kind == 0:
            query = ("SELECT u.city, COUNT(*) AS cnt\nFROM orders o\nJOIN users u ON u.id = o.user_id\n"
                     "WHERE o.status = 'paid'\nGROUP BY u.city;")
            ans = len(_sql_eval(tables, query))
            q = "Сколько строк вернёт запрос? Введите число."
            expl = "После JOIN и фильтра по статусу остаются оплаченные заказы; строк в результате столько, сколько разных городов у их покупателей."
            ok = 1 <= ans <= 3
        else:
            city = rng.choice(cities)
            query = (f"SELECT SUM(o.amount)\nFROM orders o\nJOIN users u ON u.id = o.user_id\n"
                     f"WHERE u.city = '{city}' AND o.status = 'paid';")
            ans = _sql_eval(tables, query)[0][0]
            q = "Какое число вернёт запрос? Введите число."
            expl = f"Суммируются только оплаченные заказы пользователей из города {city}."
            ok = ans is not None and ans > 0
        if ok:
            break
    return Instance(question=q, answer=str(ans), code=_sql_block(tables, query), language="sql", explanation=expl)


@template("backend_fastapi_status", title="Что ответит FastAPI", competency="FastAPI: валидация и маршрутизация",
          specializations=SPEC, technologies=["fastapi", "rest"], fmt="choice", grade_level="middle", difficulty_shift=-0.1)
def _fastapi_status(rng: random.Random) -> Instance:
    res = rng.choice(["items", "books", "tickets"])
    model = res[:-1].capitalize()
    code = (f"class {model}(BaseModel):\n    name: str\n    qty: int\n\n"
            f'@app.post("/{res}", status_code=201)\n'
            f"def create(item: {model}):\n"
            "    return item\n\n"
            f'@app.get("/{res}/{{item_id}}")\n'
            "def get_one(item_id: int):\n"
            "    if item_id > 100:\n"
            "        raise HTTPException(status_code=404)\n"
            '    return {"id": item_id}')
    cases = [
        (f'POST /{res} с телом {{"name": "x", "qty": "many"}}', "422",
         "Pydantic не может привести «many» к int — FastAPI возвращает 422 Unprocessable Entity с описанием ошибки."),
        (f'POST /{res} с телом {{"name": "x", "qty": 3}}', "201", "Валидное тело; status_code=201 задан в декораторе."),
        (f"GET /{res}/abc", "422", "Параметр пути объявлен int; строка «abc» не проходит валидацию — 422."),
        (f"GET /{res}/{rng.randint(101, 500)}", "404", "Обработчик сам поднимает HTTPException(404)."),
        (f"PUT /{res}/5", "405", "Путь существует, но метод PUT для него не объявлен — 405 Method Not Allowed."),
        (f"GET /{res}", "405", f"Для пути /{res} объявлен только POST; GET на него — 405, а не 404."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    options = ["200", "201", "400", "404", "405", "422", "500"]
    options.remove(correct)
    return _choice(rng, f"Какой код ответа вернёт приложение на запрос {text}?", [correct] + rng.sample(options, 5), 0,
                   expl, code=code, language="python")


@template("backend_docker_layer_cache", title="Кеш слоёв Dockerfile", competency="Docker: сборка образа",
          specializations=SPEC, technologies=["docker"], fmt="choice", grade_level="middle", difficulty_shift=0.0)
def _docker_layers(rng: random.Random) -> Instance:
    if rng.random() < 0.5:
        deps, install, run = "requirements.txt", "RUN pip install -r requirements.txt", 'CMD ["python", "main.py"]'
        base = "python:3.12-slim"
    else:
        deps, install, run = "package.json", "RUN npm ci", 'CMD ["node", "server.js"]'
        base = "node:20-alpine"
    code = f"FROM {base}\nWORKDIR /app\nCOPY . .\n{install}\n{run}"
    correct = f"Сначала COPY {deps} и {install.split()[1]} install зависимостей, затем COPY . . — слой с зависимостями будет браться из кеша"
    correct = f"Скопировать сначала только {deps}, выполнить {install}, и лишь потом COPY . ."
    wrong = [
        "Собирать с флагом --no-cache, чтобы сборка была воспроизводимой",
        f"Добавить .dockerignore и больше ничего не менять",
        f"Поставить {install} перед COPY . ., ничего не копируя заранее",
        "Перейти на более тяжёлый базовый образ с предустановленными пакетами",
        f"Перенести установку зависимостей в {run.split()[0]}, чтобы она шла при запуске контейнера",
    ]
    return _choice(rng, "При любом изменении исходников зависимости ставятся заново, сборка долгая. Как исправить Dockerfile?",
                   [correct] + wrong, 0,
                   f"Слои кешируются сверху вниз до первого изменившегося. Если скопировать {deps} и установить зависимости "
                   "до копирования всего кода, этот слой инвалидируется только при изменении списка зависимостей.",
                   code=code, language="text")


# ---------------------------------------------------------------------------------------------
# Senior
# ---------------------------------------------------------------------------------------------

@template("backend_async_gather_order", title="Порядок результатов asyncio.gather", competency="Асинхронность: asyncio",
          specializations=SPEC, technologies=["async", "python"], fmt="exact", grade_level="senior", difficulty_shift=-0.2)
def _async_gather(rng: random.Random) -> Instance:
    ks = rng.sample([1, 2, 3, 4], 3)
    mul = rng.choice([10, 100, 7])
    fn = rng.choice(["work", "fetch", "job"])
    code = ("import asyncio\n\n"
            f"async def {fn}(n):\n"
            "    await asyncio.sleep(0.01 * n)\n"
            f"    return n * {mul}\n\n"
            "async def main():\n"
            f"    results = await asyncio.gather({', '.join(f'{fn}({k})' for k in ks)})\n"
            '    print(" ".join(str(r) for r in results))\n\n'
            "asyncio.run(main())")
    return Instance(question="Что выведет код? Введите значения через пробел.", answer=_run_python(code), code=code,
                    language="python",
                    explanation="gather возвращает результаты в порядке переданных корутин, а не в порядке их завершения, "
                                "хотя завершаются они в порядке длительности sleep.")


@template("backend_py_decorator_order", title="Порядок применения декораторов", competency="Python: декораторы",
          specializations=SPEC, technologies=["python"], fmt="exact", grade_level="senior", difficulty_shift=0.0)
def _py_decorators(rng: random.Random) -> Instance:
    t1, t2 = rng.sample(["b", "i", "u", "em", "s"], 2)
    text = rng.choice(["hi", "ok", "go", "api"])
    fn = rng.choice(["show", "render", "wrap"])
    if rng.random() < 0.5:
        code = ("def tag(name):\n"
                "    def deco(fn):\n"
                "        def wrapper(text):\n"
                '            return f"<{name}>{fn(text)}</{name}>"\n'
                "        return wrapper\n"
                "    return deco\n\n"
                f'@tag("{t1}")\n@tag("{t2}")\n'
                f"def {fn}(text):\n    return text\n\n"
                f'print({fn}("{text}"))')
        expl = (f"Декораторы применяются снизу вверх: сначала tag(\"{t2}\") оборачивает функцию, затем tag(\"{t1}\") — "
                f"поэтому внешний тег {t1}.")
    else:
        code = ("def shout(fn):\n"
                "    def wrapper(text):\n"
                "        return fn(text).upper()\n"
                "    return wrapper\n\n"
                "def exclaim(fn):\n"
                "    def wrapper(text):\n"
                '        return fn(text) + "!"\n'
                "    return wrapper\n\n"
                f'@{rng.choice(["shout", "exclaim"])}\n')
        first = code.splitlines()[-1][1:]
        second = "exclaim" if first == "shout" else "shout"
        code += f"@{second}\ndef {fn}(text):\n    return text\n\nprint({fn}(\"{text}\"))"
        expl = (f"Ближайший к функции декоратор ({second}) применяется первым, внешний ({first}) — к результату. "
                "Порядок меняет регистр восклицательного знака? Нет, но меняет, что к чему применяется: upper() к строке с «!» или «!» к строке в верхнем регистре.")
        expl = (f"Ближайший к функции декоратор ({second}) применяется первым, внешний ({first}) — к его результату; "
                "итоговая строка собирается изнутри наружу.")
    return Instance(question="Что выведет код? Введите строку без кавычек.", answer=_run_python(code), code=code,
                    language="python", explanation=expl)


@template("backend_pg_isolation", title="Уровни изоляции PostgreSQL", competency="PostgreSQL: транзакции",
          specializations=SPEC, technologies=["postgresql"], fmt="choice", grade_level="senior", difficulty_shift=0.1)
def _pg_isolation(rng: random.Random) -> Instance:
    tbl = rng.choice(["accounts", "inventory", "bookings"])
    cases = [
        (f"Транзакция дважды читает одну строку {tbl} и получает разные значения: между чтениями другая транзакция "
         "закоммитила UPDATE. Какой минимальный уровень изоляции в PostgreSQL это исключает?", "REPEATABLE READ",
         "Неповторяющееся чтение исключается начиная с REPEATABLE READ — транзакция видит снимок на момент начала."),
        ("Какой уровень изоляции используется в PostgreSQL по умолчанию?", "READ COMMITTED",
         "По умолчанию — READ COMMITTED: каждый оператор видит данные, закоммиченные до его начала."),
        (f"Нужно, чтобы параллельные транзакции над {tbl} были эквивалентны некоторому последовательному порядку; "
         "приложение готово ловить ошибку сериализации и повторять. Какой уровень выбрать?", "SERIALIZABLE",
         "Полную эквивалентность последовательному выполнению даёт только SERIALIZABLE (SSI в PostgreSQL)."),
        ("Приложение запросило уровень READ UNCOMMITTED. Как поведёт себя PostgreSQL?", "Как READ COMMITTED",
         "В PostgreSQL READ UNCOMMITTED принимается, но работает как READ COMMITTED — «грязного» чтения нет вообще."),
        (f"Транзакция повторяет SELECT ... WHERE amount > 100 по {tbl} и во второй раз видит новые строки, вставленные "
         "другой транзакцией. Какой минимальный уровень в PostgreSQL это исключает?", "REPEATABLE READ",
         "В PostgreSQL фантомное чтение исключается уже на REPEATABLE READ благодаря снимку, а не только на SERIALIZABLE."),
    ]
    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]
    pool = ["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE", "Как READ COMMITTED",
            "Ни один — нужна явная блокировка SELECT ... FOR UPDATE", "SNAPSHOT (отдельный уровень PostgreSQL)"]
    wrong = [p for p in pool if p != correct]
    return _choice(rng, text, [correct] + rng.sample(wrong, 5), 0, expl)


@template("backend_async_blocking_call", title="Блокирующий вызов в async-обработчике", competency="Асинхронность: цикл событий",
          specializations=SPEC, technologies=["async", "fastapi"], fmt="choice", grade_level="senior", difficulty_shift=0.0)
def _async_blocking(rng: random.Random) -> Instance:
    secs = rng.choice([3, 5, 8])
    kinds = [
        ("    data = requests.get(URL, timeout=30).json()\n    return data",
         "Использовать асинхронный HTTP-клиент (httpx.AsyncClient с await) либо объявить обработчик как def, чтобы он выполнялся в пуле потоков",
         "requests блокирует поток, в котором крутится цикл событий; остальные корутины не получают управления."),
        (f"    time.sleep({secs})\n    return {{\"status\": \"ok\"}}",
         "Заменить на await asyncio.sleep(...) либо объявить обработчик как def, чтобы он выполнялся в пуле потоков",
         f"time.sleep({secs}) усыпляет поток цикла событий целиком — все запросы ждут {secs} секунд."),
        ("    rows = cursor.execute(SQL).fetchall()  # синхронный драйвер\n    return rows",
         "Перейти на асинхронный драйвер (await conn.fetch(...)) либо объявить обработчик как def, чтобы он выполнялся в пуле потоков",
         "Синхронный запрос к базе блокирует цикл событий на время ожидания ответа."),
    ]
    body, correct, expl = rng.choice(kinds)
    code = f'@app.get("/report")\nasync def report():\n{body}'
    wrong = [
        "Увеличить число воркеров uvicorn — этого достаточно",
        "Добавить await перед блокирующим вызовом",
        "Обернуть вызов в asyncio.create_task(...)",
        "Поменять декоратор на @app.post",
        "Добавить @lru_cache на обработчик",
    ]
    return _choice(rng, "Под нагрузкой все запросы к сервису замирают, пока выполняется этот обработчик. Как исправить?",
                   [correct] + wrong, 0, expl + " Блокирующую работу нужно убрать из цикла событий: асинхронный аналог или пул потоков.",
                   code=code, language="python")


@template("backend_pg_count_null_agg", title="COUNT(*), COUNT(col) и агрегаты с NULL", competency="PostgreSQL: агрегаты и NULL",
          specializations=SPEC, technologies=["sql", "postgresql"], fmt="exact", grade_level="senior", difficulty_shift=-0.3)
def _pg_null_agg(rng: random.Random) -> Instance:
    while True:
        n = rng.randint(6, 8)
        rows = []
        for i in range(n):
            discount = None if rng.random() < 0.35 else rng.choice([0, 5, 10, 15, 20])
            rows.append((i + 1, rng.randrange(100, 900, 100), discount))
        nulls = sum(1 for r in rows if r[2] is None)
        if not 1 <= nulls <= n - 2:
            continue
        tables = {"orders": (["id", "amount", "discount"], rows)}
        kind = rng.randrange(3)
        if kind == 0:
            query = "SELECT COUNT(*) - COUNT(discount) FROM orders;"
            expl = "COUNT(*) считает все строки, COUNT(discount) — только с непустой скидкой; разница равна числу NULL."
        elif kind == 1:
            query = "SELECT SUM(amount) FROM orders\nWHERE discount IS NULL;"
            expl = "Строки с NULL отбираются только через IS NULL; суммируются их amount."
        else:
            query = "SELECT COUNT(*) FROM orders\nWHERE COALESCE(discount, 0) = 0;"
            expl = "COALESCE заменяет NULL на 0, поэтому считаются и строки без скидки, и со скидкой 0."
        ans = _sql_eval(tables, query)[0][0]
        if ans and ans > 0:
            break
    return Instance(question="Какое число вернёт запрос? Введите число.", answer=str(ans), code=_sql_block(tables, query),
                    language="sql", explanation=expl)


# ---------------------------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------------------------

@template("backend_lead_api_breaking_change", title="Изменение контракта API", competency="Проектирование API: совместимость",
          specializations=SPEC, technologies=["rest", "system_design"], fmt="choice", grade_level="lead", difficulty_shift=-0.1)
def _lead_api_change(rng: random.Random) -> Instance:
    old, new = rng.choice([("user_name", "display_name"), ("price", "amount_minor"), ("created", "created_at"), ("phone", "phone_e164")])
    res = rng.choice(["orders", "profiles", "invoices"])
    months = rng.choice([3, 6, 9])
    text = (f"В ответе GET /{res} поле `{old}` нужно заменить на `{new}` с другим форматом. API используют мобильные "
            f"приложения, которые пользователи обновляют месяцами; известно, что старые версии живут до {months} месяцев.")
    correct = (f"Добавить `{new}` рядом с `{old}`, пометить старое поле устаревшим в документации и заголовке ответа, "
               f"следить по метрикам за его использованием и удалить после периода поддержки")
    wrong = [
        f"Переименовать поле сразу — клиенты обновятся по ошибкам",
        "Объявить новую мажорную версию API ради одного поля и перевести всех клиентов за неделю",
        f"Оставить `{old}`, но молча поменять формат его значения",
        "Сделать изменение только в staging и не выкатывать в прод до следующего года",
        "Заменить поле и сообщить об этом в чате команды мобильной разработки",
    ]
    return _choice(rng, f"{text} Как провести изменение?", [correct] + wrong, 0,
                   "Аддитивное изменение с периодом устаревания сохраняет совместимость: старые клиенты продолжают работать, "
                   "новые переходят на новое поле, а удаление делается по данным об использовании.")


@template("backend_lead_idempotency_retries", title="Повторы запросов и дубли платежей", competency="Проектирование API: надёжность",
          specializations=SPEC, technologies=["rest", "system_design"], fmt="multichoice", grade_level="lead", difficulty_shift=0.1)
def _lead_idempotency(rng: random.Random) -> Instance:
    pct = rng.choice([0.5, 1, 2])
    op = rng.choice([("POST /payments", "платежей"), ("POST /orders", "заказов"), ("POST /transfers", "переводов")])
    true_pool = [
        "Принимать от клиента ключ идемпотентности (Idempotency-Key) и на повтор с тем же ключом возвращать прежний результат",
        "Хранить ключ идемпотентности с результатом в базе с уникальным ограничением, чтобы гонка двух повторов не создала два объекта",
        "Договориться с клиентами о повторах с экспоненциальной задержкой и тем же ключом, а не с новым",
    ]
    false_pool = [
        "Запретить клиентам любые повторы запросов",
        f"Перевести операцию на GET, потому что GET идемпотентен",
        "Увеличить таймаут на клиенте до 5 минут и считать проблему решённой",
        "Перед созданием искать похожий объект по сумме и времени «примерно за последнюю минуту»",
    ]
    k = rng.randint(2, 3)
    return _multi(rng, f"Из-за сетевых таймаутов около {pct} % {op[0]} приводят к дублям {op[1]}: клиент повторяет запрос, "
                       "не зная, прошёл ли первый. Какие меры решают проблему? Выберите все подходящие.",
                  rng.sample(true_pool, k), rng.sample(false_pool, 6 - k),
                  "Идемпотентность POST обеспечивается ключом от клиента и уникальным ограничением на сервере; повторы "
                  "остаются допустимыми и безопасными. Запреты повторов и эвристики по сумме проблему не решают.")
