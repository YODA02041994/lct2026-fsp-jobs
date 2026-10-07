"""Проверяет понимание гарантий доставки, идемпотентности, партиционирования и обратного давления в Kafka.

Источники формулировок: kafka.apache.org/43 — design (Message Delivery Semantics), introduction (ключ → партиция),
operations (добавление партиций не перераспределяет данные, но меняет отображение ключа), producer-configs (acks),
javadoc KafkaConsumer (pause/resume, коммит оффсетов).
"""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_backend_lead_kafka_delivery_semantics", title="Kafka: доставка, порядок и идемпотентность",
          competency="Проектирование систем: Kafka и гарантии доставки",
          specializations=["backend"], technologies=["system_design", "kafka"],
          fmt="multichoice", grade_level="lead", difficulty_shift=0.2)
def _kafka_delivery_semantics(rng: random.Random) -> Instance:
    topic = rng.choice(["orders.events", "payments.tx", "users.activity", "inventory.updates", "shipments.track"])
    group = rng.choice(["billing-consumer", "notify-workers", "fraud-detector", "analytics-sink", "audit-writer"])
    svc = rng.choice(["OrderService", "PaymentService", "InventoryService", "NotificationService", "FraudService"])
    partitions = rng.choice([3, 6, 12, 24])
    key_field = rng.choice(["order_id", "user_id", "tenant_id", "account_id", "device_id"])

    true_pool = [
        f"Сообщения с одинаковым ключом {key_field} попадают в одну партицию топика {topic} (пока число партиций "
        "не меняется), поэтому порядок между ними сохраняется.",
        f"При acks=all продюсер {svc} получает подтверждение только после того, как запись приняли все реплики "
        "из ISR (in-sync replicas) партиции.",
        f"Идемпотентность потребителя {group} достигается дедупликацией по уникальному идентификатору события "
        "(event_id) или по паре партиция+оффсет, сохранённым в том же транзакционном хранилище, что и результат обработки.",
        f"Увеличение числа партиций у {topic} не перераспределяет уже записанные сообщения, но меняет отображение "
        f"ключа {key_field} на партицию для новых сообщений.",
        f"Обратное давление в {group} реализуется через ограничение параллелизма обработки и паузу потребления "
        "(pause/resume), а не бесконечную буферизацию.",
        f"Коммит оффсета в {group} до завершения обработки даёт семантику at-most-once для этого сообщения.",
    ]
    false_pool = [
        f"Сообщения с одинаковым ключом {key_field} в {topic} распределяются round-robin по всем партициям, "
        "и порядок между ними не гарантируется.",
        f"acks=0 в {svc} гарантирует, что сообщение записано на все реплики до ответа продюсеру.",
        f"Дедупликация в {group} не нужна, если у продюсера включён enable.idempotence: брокер уже отбрасывает повторы.",
        f"Коммит оффсета в {group} до завершения обработки даёт семантику exactly-once.",
        f"Обратное давление в {group} решается увеличением числа партиций {topic} без изменения кода потребителя.",
        f"Порядок сообщений в {topic} гарантируется глобально по всему топику независимо от партиций.",
    ]

    k = rng.randint(2, 3)
    correct = rng.sample(true_pool, k)
    wrong = rng.sample(false_pool, 6 - k)

    code_lines = [
        f"# Топик: {topic}",
        f"# Партиций: {partitions}, ключ сообщения: {key_field}, партиционер по умолчанию",
        f"# Группа потребителей: {group}",
        f"# Продюсер: {svc}",
        "producer:",
        "  acks: all",
        "  enable.idempotence: true",
        "consumer:",
        "  enable.auto.commit: false",
        "  max.poll.records: 500",
    ]
    code = "\n".join(code_lines)

    question = (
        f"Команда проектирует поток {topic} (ключ {key_field}) для сервиса {svc} и группы {group}. "
        "Какие утверждения о гарантиях доставки, порядке и обратном давлении верны? Выберите все подходящие."
    )
    explanation = (
        "Kafka гарантирует порядок только внутри партиции, а партицию при партиционере по умолчанию выбирает хеш ключа — "
        "ключ держит связанные события вместе, пока не изменилось число партиций (уже записанное при этом не переезжает). "
        "acks=all — подтверждение всеми репликами из ISR. enable.idempotence убирает дубли только при повторах самого "
        "продюсера (брокер сверяет id продюсера и порядковый номер), поэтому потребитель, который может обработать "
        "сообщение повторно, всё равно дедуплицирует — по уникальному идентификатору события, а не по ключу "
        "партиционирования, общему для многих сообщений. Коммит оффсета до обработки — at-most-once, после — "
        "at-least-once; exactly-once требует транзакций. Обратное давление — управление скоростью потребления "
        "(pause/resume, ограничение параллелизма), а не рост числа партиций."
    )
    return _multi(rng, question, correct, wrong, explanation, code=code, language="text")
