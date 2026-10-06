"""Шаблоны: данные и машинное обучение — SQL, Python и statistics, pandas (концептуально), статистика, ML-базa.

Ключи exact: SQL — через sqlite3 на показанных таблицах, Python — исполнением фрагмента, остальное — целочисленная
арифметика. pandas в окружении нет, поэтому pandas-задания либо концептуальные (choice), либо считаются по
показанным таблицам (language="text"), а не помечаются исполняемым Python.
"""
from __future__ import annotations
import random

from .base import template, Instance
from .common import _run_python, _sql_eval, _sql_block, _table_lines, _choice, _multi, _NAMES

SPEC = ["data"]
_REGIONS = ["север", "юг", "центр", "восток", "запад"]
_PRODUCTS = ["чай", "кофе", "сок", "вода"]


def _sales_rows(rng: random.Random, n: int, regions: list[str]) -> list[tuple]:
    return [(i + 1, rng.choice(regions), rng.choice(_PRODUCTS), rng.randrange(10, 100, 5)) for i in range(n)]


# ---------------------------------------------------------------------------------------------
# Junior
# ---------------------------------------------------------------------------------------------

@template("data_sql_sum_filter", title="Сумма по условию", competency="SQL: агрегат с фильтром",
          specializations=SPEC, technologies=["sql"], fmt="exact", grade_level="junior", difficulty_shift=-0.3)
def _sql_sum_filter(rng: random.Random) -> Instance:
    while True:
        regions = rng.sample(_REGIONS, 3)
        rows = _sales_rows(rng, rng.randint(6, 8), regions)
        tables = {"sales": (["id", "region", "product", "amount"], rows)}
        region = rng.choice(regions)
        product = rng.choice(_PRODUCTS)
        where = rng.choice([f"region = '{region}'", f"product = '{product}'", f"region = '{region}' AND amount >= {rng.randrange(20, 60, 5)}"])
        agg = rng.choice(["SUM(amount)", "MAX(amount)", "MIN(amount)"])
        query = f"SELECT {agg} FROM sales\nWHERE {where};"
        ans = _sql_eval(tables, query)[0][0]
        matched = len(_sql_eval(tables, f"SELECT * FROM sales WHERE {where}"))
        if ans is not None and matched >= 2:
            break
    return Instance(question="Какое число вернёт запрос? Введите число.", answer=str(ans), code=_sql_block(tables, query),
                    language="sql", explanation=f"Под условие «{where}» попадают {matched} строк; агрегат {agg} считается только по ним.")


@template("data_py_statistics", title="Медиана, мода и размах", competency="Python: модуль statistics",
          specializations=SPEC, technologies=["python", "statistics"], fmt="exact", grade_level="junior", difficulty_shift=-0.1)
def _py_statistics(rng: random.Random) -> Instance:
    var = rng.choice(["xs", "scores", "ages"])
    kind = rng.randrange(3)
    if kind == 0:
        xs = [rng.randint(1, 30) for _ in range(rng.choice([5, 7]))]
        tail, expl = f"print(statistics.median({var}))", "Медиана — средний элемент отсортированного ряда нечётной длины."
    elif kind == 1:
        while True:
            xs = [rng.randint(1, 9) for _ in range(6)]
            counts = {x: xs.count(x) for x in xs}
            top = max(counts.values())
            if top >= 2 and list(counts.values()).count(top) == 1:
                break
        tail, expl = f"print(statistics.mode({var}))", "Мода — самое частое значение; здесь оно единственное."
    else:
        xs = rng.sample(range(3, 60), 6)
        tail, expl = f"print(max({var}) - min({var}))", "Размах — разность максимума и минимума."
    code = f"import statistics\n\n{var} = {xs}\n{tail}"
    return Instance(question="Что выведет код? Введите число.", answer=_run_python(code), code=code, language="python",
                    explanation=expl)


@template("data_stats_outlier", title="Выброс и меры центра", competency="Статистика: описательные статистики",
          specializations=SPEC, technologies=["statistics"], fmt="choice", grade_level="junior", difficulty_shift=0.0)
def _stats_outlier(rng: random.Random) -> Instance:
    base = sorted(rng.sample(range(60, 120, 5), 6))
    big = rng.choice([900, 1200, 2500])
    unit = rng.choice(["тыс. ₽", "минут", "заказов"])
    options = ["Среднее арифметическое", "Медиана", "Мода", "Минимум", "Число наблюдений", "Межквартильный размах"]
    if rng.random() < 0.5:
        q = (f"Значения в выборке ({unit}): {', '.join(map(str, base))}. Добавили одно наблюдение {big}. "
             "Какая статистика изменится сильнее всего?")
        correct, expl = 0, "Среднее тянется за выбросом пропорционально его величине; медиана сдвинется лишь на соседнее значение."
    else:
        q = (f"Значения в выборке ({unit}): {', '.join(map(str, base))}, и одно наблюдение {big} — выброс. "
             "Какую меру центра выбрать как устойчивую к нему?")
        correct, expl = 1, "Медиана зависит только от порядка значений и почти не реагирует на единичный выброс."
    return _choice(rng, q, options, correct, expl)


@template("data_ml_fit_diagnosis", title="Переобучение или недообучение", competency="ML: диагностика модели",
          specializations=SPEC, technologies=["ml"], fmt="choice", grade_level="junior", difficulty_shift=0.1)
def _ml_fit(rng: random.Random) -> Instance:
    model = rng.choice(["градиентный бустинг", "случайный лес", "нейросеть", "дерево решений"])
    options = [
        "Переобучение: упростить модель, добавить регуляризацию или данных, проверить кросс-валидацией",
        "Недообучение: усложнить модель, добавить информативные признаки, дольше обучать",
        "Утечка целевой переменной в признаки: пересобрать признаки",
        "Всё в порядке: модель готова к выкатке без изменений",
        "Нужно уменьшить обучающую выборку, чтобы модель лучше обобщала",
        "Нужно убрать валидационную выборку и оценивать по обучающей",
    ]
    if rng.random() < 0.5:
        tr, te = rng.choice([(0.99, 0.71), (0.98, 0.68), (1.0, 0.74)])
        correct, expl = 0, "Большой разрыв между обучением и отложенной выборкой — признак переобучения."
    else:
        tr, te = rng.choice([(0.62, 0.60), (0.58, 0.57), (0.65, 0.63)])
        correct, expl = 1, "Низкое качество и на обучении, и на отложенной выборке — модель слишком проста или признаков мало."
    q = (f"Модель ({model}) показывает accuracy {tr:.2f} на обучающей выборке и {te:.2f} на отложенной. "
         "Что происходит и что делать?")
    return _choice(rng, q, options, correct, expl)


# ---------------------------------------------------------------------------------------------
# Middle
# ---------------------------------------------------------------------------------------------

@template("data_sql_having_sum", title="Группы с HAVING по сумме", competency="SQL: группировка и HAVING",
          specializations=SPEC, technologies=["sql"], fmt="exact", grade_level="middle", difficulty_shift=-0.2)
def _sql_having(rng: random.Random) -> Instance:
    while True:
        regions = rng.sample(_REGIONS, 4)
        rows = _sales_rows(rng, rng.randint(7, 8), regions)
        tables = {"sales": (["id", "region", "product", "amount"], rows)}
        if rng.random() < 0.5:
            thr = rng.randrange(80, 200, 10)
            query = f"SELECT region, SUM(amount) AS total\nFROM sales\nGROUP BY region\nHAVING SUM(amount) > {thr};"
            expl = f"HAVING оставляет только регионы с суммой больше {thr}."
        else:
            query = "SELECT product, COUNT(DISTINCT region) AS regions\nFROM sales\nGROUP BY product\nHAVING COUNT(DISTINCT region) >= 2;"
            expl = "Для каждого продукта считается число разных регионов; остаются продукты, проданные хотя бы в двух."
        ans = len(_sql_eval(tables, query))
        groups = len({r[1] for r in rows}) if "region," in query else len({r[2] for r in rows})
        if 1 <= ans <= groups - 1:
            break
    return Instance(question="Сколько строк вернёт запрос? Введите число.", answer=str(ans), code=_sql_block(tables, query),
                    language="sql", explanation=expl)


@template("data_sql_join_distinct", title="JOIN и COUNT DISTINCT", competency="SQL: соединения и уникальные значения",
          specializations=SPEC, technologies=["sql"], fmt="exact", grade_level="middle", difficulty_shift=0.0)
def _sql_join_distinct(rng: random.Random) -> Instance:
    while True:
        nc = rng.randint(4, 5)
        names = rng.sample(_NAMES, nc)
        segs = ["b2b", "b2c"]
        customers = [(i + 1, names[i], rng.choice(segs)) for i in range(nc)]
        orders = [(100 + j, rng.randint(1, nc), rng.randrange(100, 900, 100)) for j in range(rng.randint(6, 8))]
        tables = {"customers": (["id", "name", "segment"], customers), "orders": (["id", "customer_id", "amount"], orders)}
        seg = rng.choice(segs)
        distinct = rng.random() < 0.6
        agg = "COUNT(DISTINCT o.customer_id)" if distinct else "COUNT(*)"
        query = (f"SELECT {agg}\nFROM orders o\nJOIN customers c ON c.id = o.customer_id\nWHERE c.segment = '{seg}';")
        ans = _sql_eval(tables, query)[0][0]
        other = _sql_eval(tables, query.replace(agg, "COUNT(*)" if distinct else "COUNT(DISTINCT o.customer_id)"))[0][0]
        if ans and ans != other:
            break
    expl = (f"В сегменте {seg} заказы делали {ans} разных клиентов (всего заказов — {other}); DISTINCT схлопывает повторы клиента."
            if distinct else
            f"JOIN даёт строку на каждый заказ клиента из сегмента {seg}: их {ans} (разных клиентов — {other}).")
    return Instance(question="Какое число вернёт запрос? Введите число.", answer=str(ans), code=_sql_block(tables, query),
                    language="sql", explanation=expl)


@template("data_py_group_aggregate", title="Агрегация по ключу на чистом Python", competency="Python: агрегация данных",
          specializations=SPEC, technologies=["python"], fmt="exact", grade_level="middle", difficulty_shift=-0.1)
def _py_group(rng: random.Random) -> Instance:
    while True:
        regions = rng.sample(_REGIONS, 3)
        rows = [(rng.choice(regions), rng.randrange(10, 100, 10)) for _ in range(rng.randint(6, 7))]
        totals: dict[str, int] = {}
        for r, a in rows:
            totals[r] = totals.get(r, 0) + a
        vals = sorted(totals.values())
        if len(totals) == 3 and vals[-1] != vals[-2]:
            break
    var = rng.choice(["totals", "by_region", "agg"])
    rows_src = ", ".join(f'("{r}", {a})' for r, a in rows)
    kind = rng.randrange(2)
    tail = (f"best = max({var}, key={var}.get)\nprint(best, {var}[best])" if kind == 0
            else f"print(min({var}.values()), len({var}))")
    code = (f"rows = [{rows_src}]\n{var} = {{}}\nfor region, amount in rows:\n"
            f"    {var}[region] = {var}.get(region, 0) + amount\n{tail}")
    q = ("Что выведет код? Введите регион и число через пробел." if kind == 0
         else "Что выведет код? Введите два числа через пробел.")
    expl = ("Словарь накапливает сумму по региону; max с key=dict.get возвращает ключ с наибольшей суммой."
            if kind == 0 else "min по значениям — наименьшая сумма среди регионов, len — число регионов.")
    return Instance(question=q, answer=_run_python(code), code=code, language="python", explanation=expl)


@template("data_ml_confusion_metrics", title="Precision, recall и accuracy по матрице ошибок", competency="ML: метрики классификации",
          specializations=SPEC, technologies=["ml", "statistics"], fmt="exact", grade_level="middle", difficulty_shift=0.0)
def _ml_metrics(rng: random.Random) -> Instance:
    while True:
        tp = rng.randint(4, 18)
        den_p = rng.choice([20, 25, 50])
        den_r = rng.choice([20, 25, 50])
        fp, fn = den_p - tp, den_r - tp
        total = rng.choice([50, 100])
        tn = total - tp - fp - fn
        if fp > 0 and fn > 0 and tn > 0:
            break
    metric = rng.choice(["precision", "recall", "accuracy"])
    val = {"precision": 100 * tp // (tp + fp), "recall": 100 * tp // (tp + fn), "accuracy": 100 * (tp + tn) // total}[metric]
    assert {"precision": 100 * tp % (tp + fp), "recall": 100 * tp % (tp + fn), "accuracy": 100 * (tp + tn) % total}[metric] == 0
    code = "\n".join(_table_lines("матрица ошибок", ["", "предсказано +", "предсказано −"],
                                  [("факт +", tp, fn), ("факт −", fp, tn)], prefix=""))
    expl = {"precision": f"precision = TP / (TP + FP) = {tp} / {tp + fp}.",
            "recall": f"recall = TP / (TP + FN) = {tp} / {tp + fn}.",
            "accuracy": f"accuracy = (TP + TN) / всего = {tp + tn} / {total}."}[metric]
    return Instance(question=f"По матрице ошибок вычислите {metric} в процентах. Введите целое число.", answer=str(val),
                    code=code, language="text", explanation=expl)


@template("data_pandas_groupby_expr", title="Выражение pandas под задачу", competency="pandas: группировка и агрегация",
          specializations=SPEC, technologies=["pandas", "python"], fmt="choice", grade_level="middle", difficulty_shift=-0.1)
def _pandas_groupby(rng: random.Random) -> Instance:
    key, val = rng.choice([("region", "amount"), ("category", "price"), ("city", "revenue"), ("team", "hours")])
    options = [
        f'df.groupby("{key}")["{val}"].sum().sort_values(ascending=False)',
        f'df.groupby("{key}")["{val}"].mean().sort_values(ascending=False)',
        f'df.groupby("{key}").size().sort_values(ascending=False)',
        f'df.groupby("{val}")["{key}"].sum().sort_values()',
        f'df["{val}"].sum().groupby("{key}")',
        f'df.sort_values("{val}").groupby("{key}").first()',
    ]
    task, correct, expl = rng.choice([
        (f"суммарный {val} по каждому {key}, от большего к меньшему", 0, "groupby по ключу, выбор столбца, sum и сортировка по убыванию."),
        (f"средний {val} по каждому {key}, от большего к меньшему", 1, "Та же цепочка, но агрегат mean."),
        (f"число строк по каждому {key}, от большего к меньшему", 2, "size считает строки в каждой группе."),
    ])
    return _choice(rng, f"В DataFrame df есть столбцы {key} и {val}. Какое выражение вернёт {task}?", options, correct, expl)


@template("data_pandas_merge_rows", title="Сколько строк даст merge", competency="pandas: соединение таблиц",
          specializations=SPEC, technologies=["pandas"], fmt="exact", grade_level="middle", difficulty_shift=0.2)
def _pandas_merge(rng: random.Random) -> Instance:
    while True:
        keys_a = [rng.randint(1, 5) for _ in range(rng.randint(4, 5))]
        keys_b = [rng.randint(1, 5) for _ in range(rng.randint(3, 5))]
        cnt_b = {k: keys_b.count(k) for k in set(keys_b)}
        inner = sum(cnt_b.get(k, 0) for k in keys_a)
        left = sum(cnt_b.get(k, 0) or 1 for k in keys_a)
        if inner >= 1 and inner != len(keys_a) and left != inner:
            break
    how = rng.choice(["inner", "left"])
    ans = inner if how == "inner" else left
    a_rows = [(k, rng.randint(10, 99)) for k in keys_a]
    b_rows = [(k, rng.choice(["x", "y", "z"])) for k in keys_b]
    code = "\n".join(_table_lines("a", ["key", "x"], a_rows, prefix="") + [""] + _table_lines("b", ["key", "y"], b_rows, prefix="")
                     + ["", f'pd.merge(a, b, on="key", how="{how}")'])
    expl = ("inner оставляет только совпавшие ключи; строка из a размножается на число совпадений в b."
            if how == "inner" else
            "left сохраняет каждую строку a: с совпадениями — по строке на каждое, без совпадений — одну с NaN.")
    return Instance(question="Сколько строк будет в результате merge? Введите число.", answer=str(ans), code=code,
                    language="text", explanation=expl)


@template("data_stats_pvalue", title="Интерпретация p-value", competency="Статистика: проверка гипотез",
          specializations=SPEC, technologies=["statistics"], fmt="choice", grade_level="middle", difficulty_shift=0.1)
def _stats_pvalue(rng: random.Random) -> Instance:
    alpha = rng.choice([0.05, 0.01])
    p = rng.choice([0.002, 0.03, 0.04, 0.08, 0.2, 0.35])
    metric = rng.choice(["конверсии", "среднего чека", "времени на странице"])
    options = [
        "Отвергаем H0: различие статистически значимо на выбранном уровне",
        "Не отвергаем H0: данных недостаточно, чтобы говорить о различии (это не доказательство равенства)",
        f"Вероятность того, что H0 верна, равна {p}",
        f"Вероятность ошибки первого рода в этом тесте равна {1 - p:.3f}",
        "Эффект обязательно практически значим для бизнеса",
        "Нужно поднять уровень значимости до p, чтобы результат стал значимым",
    ]
    correct = 0 if p < alpha else 1
    expl = (f"p = {p} {'<' if p < alpha else '≥'} α = {alpha}. p-value — вероятность получить такие или более крайние данные "
            "при верной H0, а не вероятность самой H0 и не мера практической значимости.")
    return _choice(rng, f"Сравнение {metric} в двух группах дало p-value = {p} при α = {alpha}. Какой вывод корректен?",
                   options, correct, expl)


# ---------------------------------------------------------------------------------------------
# Senior
# ---------------------------------------------------------------------------------------------

@template("data_sql_window_row_number", title="Оконная функция ROW_NUMBER", competency="SQL: оконные функции",
          specializations=SPEC, technologies=["sql"], fmt="exact", grade_level="senior", difficulty_shift=-0.2)
def _sql_window(rng: random.Random) -> Instance:
    while True:
        regions = rng.sample(_REGIONS, 3)
        n = rng.randint(7, 8)
        names = rng.sample(_NAMES, n)
        amounts = rng.sample(range(10, 100, 5), n)
        rows = [(names[i], rng.choice(regions), amounts[i]) for i in range(n)]
        tables = {"sales": (["seller", "region", "amount"], rows)}
        per_region = {r: sum(1 for x in rows if x[1] == r) for r in regions}
        if min(per_region.values()) < 2:
            continue
        inner = ("SELECT seller, region, amount,\n       ROW_NUMBER() OVER (PARTITION BY region ORDER BY amount DESC) AS rn\n"
                 "FROM sales")
        kind = rng.randrange(2)
        if kind == 0:
            query = f"SELECT COUNT(*) FROM (\n  {inner.replace(chr(10), chr(10) + '  ')}\n) t\nWHERE rn <= 2;"
            ans = _sql_eval(tables, query)[0][0]
            q = "Какое число вернёт запрос? Введите число."
            expl = "ROW_NUMBER нумерует строки внутри каждого региона по убыванию amount; rn <= 2 оставляет до двух лучших продавцов на регион."
        else:
            region = rng.choice(regions)
            query = f"SELECT seller FROM (\n  {inner.replace(chr(10), chr(10) + '  ')}\n) t\nWHERE rn = 1 AND region = '{region}';"
            ans = _sql_eval(tables, query)[0][0]
            q = "Какое имя вернёт запрос? Введите имя без кавычек."
            expl = f"rn = 1 внутри региона {region} — продавец с наибольшим amount в этом регионе."
        break
    return Instance(question=q, answer=str(ans), code=_sql_block(tables, query), language="sql", explanation=expl)


@template("data_ml_leakage", title="Где утечка данных", competency="ML: валидация и утечки",
          specializations=SPEC, technologies=["ml", "scikit_learn"], fmt="choice", grade_level="senior", difficulty_shift=0.0)
def _ml_leakage(rng: random.Random) -> Instance:
    target = rng.choice(["отток", "дефолт", "возврат товара"])
    scenarios = [
        (["Загрузить данные", "StandardScaler().fit_transform на всём датасете", "train_test_split", "Обучить модель на train", "Оценить на test"],
         1, "Скейлер подогнан на всём датасете, включая test: статистики теста протекают в обучение. fit — только на train."),
        (["Загрузить данные", "train_test_split", f"Добавить признак «средний {target} по городу», посчитанный по всему датасету",
          "Обучить модель на train", "Оценить на test"],
         2, "Целевое кодирование по всему датасету использует метки test — утечка целевой переменной."),
        (["Загрузить данные", "train_test_split", "Обучить модель на train", "Подобрать порог и гиперпараметры по качеству на test",
          "Сообщить качество на test как итоговое"],
         3, "Подбор по test превращает его в валидацию; итоговая оценка завышена. Нужна отдельная валидационная выборка или CV."),
        (["Загрузить данные", "Удалить дубликаты строк", "train_test_split (стратифицированный)", "Обучить модель на train", "Оценить на test"],
         None, "Все шаги корректны: дубликаты убраны до разбиения, подгонка только на train."),
    ]
    steps, leak, expl = rng.choice(scenarios)
    code = "\n".join(f"{i + 1}) {s}" for i, s in enumerate(steps))
    options = [f"Шаг {i + 1}" for i in range(5)] + ["Утечки нет"]
    correct = 5 if leak is None else leak
    return _choice(rng, f"Пайплайн модели предсказания ({target}) приведён ниже. На каком шаге возникает утечка данных?",
                   options, correct, expl, code=code, language="text")


@template("data_stats_ab_pitfalls", title="A/B-тест: что делать", competency="Статистика: A/B-эксперименты",
          specializations=SPEC, technologies=["statistics", "product_analytics"], fmt="choice", grade_level="senior", difficulty_shift=0.1)
def _stats_ab(rng: random.Random) -> Instance:
    n = rng.choice([20000, 50000, 80000])
    day = rng.randint(2, 4)
    pct = rng.choice([20, 30, 40])
    split = rng.choice([("60/40", 60), ("57/43", 57), ("65/35", 65)])
    scenarios = [
        (f"Тест рассчитан на {n} пользователей на группу (две недели). На день {day} набрано {pct} % выборки, p-value = 0.04 в пользу B.",
         "Продолжить до запланированного объёма: остановка при первом значимом p («подглядывание») резко повышает долю ложных срабатываний",
         "Множественные проверки по ходу теста без поправки раздувают ошибку первого рода."),
        (f"Пользователей делили 50/50, но по факту в группах {split[0]} ({split[1]} % в A). p-value по метрике = 0.01.",
         "Не доверять результату: проверить механизм рандомизации и сплита (sample ratio mismatch), затем перезапустить",
         "Расхождение долей говорит о сломанной рандомизации; значимость при SRM ничего не значит."),
        (f"Тест завершён по плану ({n} на группу), p-value = 0.45, доверительный интервал эффекта [−0.3 %, +0.4 %].",
         "Зафиксировать отсутствие обнаружимого эффекта на заданной чувствительности и решать по стоимости внедрения",
         "Незначимый результат при достаточной мощности — информация: эффект, если есть, меньше заданного порога."),
    ]
    text, correct, expl = rng.choice(scenarios)
    distractors = [
        "Остановить тест и выкатить B на всех",
        "Сменить метрику на ту, по которой уже есть значимость",
        "Добавить третью группу и продолжить без изменения плана",
        "Объявить B хуже A и откатить",
        "Увеличить α до 0.1, чтобы результат стал значимым",
        "Исключить из анализа пользователей, не совершивших покупку",
    ]
    return _choice(rng, f"{text} Что делать?", [correct] + rng.sample(distractors, 5), 0, expl)


# ---------------------------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------------------------

@template("data_lead_pipeline_idempotent", title="Повторный запуск загрузки", competency="Архитектура данных: идемпотентность пайплайнов",
          specializations=SPEC, technologies=["airflow", "system_design"], fmt="choice", grade_level="lead", difficulty_shift=-0.1)
def _lead_pipeline(rng: random.Random) -> Instance:
    tbl = rng.choice(["fact_orders", "events_daily", "payments_agg"])
    src = rng.choice(["из Kafka", "из CRM", "из платёжного шлюза"])
    text = (f"Ежедневный DAG грузит данные {src} за прошедшие сутки в {tbl} через INSERT. При повторном запуске за прошлое "
            "число (после сбоя источника) строки за этот день задваиваются, и отчёты расходятся.")
    correct = ("Сделать загрузку идемпотентной: запуск параметризован датой и перезаписывает партицию/диапазон за эту дату "
               "(DELETE + INSERT или INSERT OVERWRITE), а не дописывает")
    wrong = [
        "Запретить повторные запуски DAG — пусть пропуски чинят вручную",
        "Добавить DISTINCT во все отчётные запросы поверх таблицы",
        "Увеличить число retries у задачи до 10",
        "Перейти с ежедневной загрузки на ежечасную",
        "Хранить флаг «день загружен» в отдельной таблице и пропускать повторные запуски без перезаписи",
    ]
    return _choice(rng, f"{text} Как исправить правильно?", [correct] + wrong, 0,
                   "Идемпотентный по дате шаг позволяет безопасно перезапускать и бэкфиллить любой день; все остальные варианты "
                   "либо маскируют дубли, либо лишают возможности починить данные.")


@template("data_lead_model_monitoring", title="Мониторинг модели в проде", competency="MLOps: эксплуатация моделей",
          specializations=SPEC, technologies=["ml", "system_design"], fmt="multichoice", grade_level="lead", difficulty_shift=0.1)
def _lead_monitoring(rng: random.Random) -> Instance:
    task = rng.choice(["скоринга заявок", "рекомендаций", "прогноза спроса"])
    months = rng.choice([3, 6, 9])
    true_pool = [
        "Следить за дрейфом распределений входных признаков и предсказаний относительно обучающей выборки",
        "Регулярно сравнивать качество на свежей размеченной выборке с качеством, зафиксированным при приёмке",
        "Логировать версию модели и данных для каждого предсказания, чтобы разбирать инциденты и откатываться",
    ]
    false_pool = [
        "Переобучать модель каждую ночь независимо от метрик — так дрейфа точно не будет",
        "Ограничиться проверкой доступности сервиса (HTTP 200 и задержка)",
        "Отключить логирование предсказаний, чтобы сэкономить на хранении",
        "Считать модель исправной, пока не пожалуются пользователи",
    ]
    k = rng.randint(2, 3)
    return _multi(rng, f"Модель {task} работает в проде {months} месяцев; бизнес жалуется, что «стало хуже», а метрик нет. "
                       "Что должно входить в мониторинг модели? Выберите все подходящие.",
                  rng.sample(true_pool, k), rng.sample(false_pool, 6 - k),
                  "Мониторинг модели — это дрейф данных, качество на свежей разметке и воспроизводимость (версии); доступность "
                  "сервиса — необходимое, но недостаточное условие.")
