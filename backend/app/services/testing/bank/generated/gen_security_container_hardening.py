"""Проверяет понимание безопасного запуска контейнеров и управления секретами в Docker."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_security_container_hardening", title="Безопасность контейнеров и секретов",
          competency="Безопасность контейнеров и секретов",
          specializations=["security"], technologies=["security_basics", "docker"],
          fmt="multichoice", grade_level="senior", difficulty_shift=0.2)
def _security_container_hardening(rng: random.Random) -> Instance:
    svc = rng.choice(["billing-api", "auth-service", "orders-worker", "notify-gateway", "reports-cron"])
    img = rng.choice(["registry.local/app:1.7.3", "registry.local/svc:2024.11", "app:latest"])
    uid = rng.choice([10001, 10002, 65532, 1000])
    port = rng.choice([8080, 8443, 9000])
    net = rng.choice(["backend-net", "internal-net", "svc-mesh"])
    secret = rng.choice(["DB_PASSWORD", "JWT_SIGNING_KEY", "STRIPE_API_KEY", "REDIS_AUTH"])
    mount = rng.choice(["/run/secrets", "/var/run/secrets", "/etc/secrets"])

    true_pool = [
        f"В Dockerfile для {svc} стоит `USER {uid}` — процесс не работает от root, и компрометация не даёт прав root в контейнере.",
        f"Секрет {secret} передаётся в {svc} через `--mount type=bind,src=...,dst={mount}/{secret.lower()},readonly` или Docker secrets, а не через `ENV`.",
        f"Образ {img} перед деплоем проверяется сканером (Trivy/Grype) — сборка падает при найденных CRITICAL/HIGH CVE.",
        f"Контейнер {svc} запускается с `--read-only` и `--tmpfs /tmp` — корневая файловая система недоступна для записи.",
        f"Контейнер {svc} подключён только к пользовательской сети {net} вместе с нужными ему сервисами, а не к общей сети со всеми контейнерами.",
        f"Контейнеру {svc} сброшены capabilities (`--cap-drop=ALL`) и запрещено повышение прав (`--security-opt=no-new-privileges`).",
    ]
    false_pool = [
        f"Секрет {secret} безопасно хранить в образе как `ENV {secret}=...` — переменные видны только процессу внутри контейнера.",
        f"Запуск {svc} от root оправдан: это упрощает установку пакетов и монтирование томов во время работы.",
        f"Достаточно один раз просканировать образ {img} при сборке — дальше повторное сканирование не нужно, даже если базовый слой обновился.",
        f"Сеть `--network host` для {svc} безопаснее пользовательской сети {net}, потому что убирает лишний сетевой слой.",
        f"`--read-only` для {svc} несовместимо с монтированием секретов: файлы секретов требуют записи в корень ФС.",
        f"Порт {port} достаточно опубликовать на `0.0.0.0` — доступ извне контролируется только правилами приложения.",
    ]

    k = rng.randint(2, 3)
    correct = rng.sample(true_pool, k)
    wrong = rng.sample(false_pool, 6 - k)

    question = (
        f"Сервис {svc} собирается из образа {img} и слушает порт {port}. "
        "Какие меры действительно повышают безопасность контейнера и секретов? "
        "Выберите все подходящие."
    )
    explanation = (
        "Запуск не от root, секреты вне образа (bind-mount/Docker secrets), скан образа на CVE, "
        "read-only корень с tmpfs, сброс capabilities и изоляция в отдельной сети снижают поверхность атаки; "
        "секреты в ENV/образе, root, host-сеть и публикация на 0.0.0.0 без контроля — небезопасны."
    )
    return _multi(rng, question, correct, wrong, explanation)
