# Шаблоны, сгенерированные моделью — реестр

Сгенерированы `scripts/evolve/propose_templates.py` (DeepSeek V4.1 Flash, валидатор в отдельном процессе) 07.10.2026 и
**проверены четырьмя независимыми ревью по официальной документации** (каждое утверждение правильных и неправильных вариантов и
пояснений сверялось с первоисточником; ключи exact-заданий — исполнением). Включены в банк (`load_all`) после ревью.
Как это делалось и что находили — `docs/08_Механика_тестирования.md`, раздел 7.

Всего в банке: 40 — исправлено после ревью 35, одобрено без правок 3, перегенерировано
после удаления 2. Удалены по итогам ревью: 2.

| Код | Специализация | Грейд | Технологии | Формат | Название | Статус | Проверено по |
|---|---|---|---|---|---|---|---|
| `gen_analytics_requirements_uml_choice` | analytics | junior | system_analysis, uml | choice | Требования и выбор UML-диаграммы | исправлен | uml-diagrams.org; cucumber.io gherkin |
| `gen_analytics_sql_group_having_count` | analytics | junior | sql, excel | exact | Сколько категорий пройдут HAVING | исправлен | sqlite.org aggfunc; ключ через sqlite |
| `gen_analytics_bpmn_gateway_reading` | analytics | middle | bpmn, system_analysis | choice | Чтение схемы BPMN и выбор шлюза | исправлен | docs.camunda.io gateways/events; camunda.com bpmn reference |
| `gen_analytics_sql_funnel_step` | analytics | middle | sql, product_analytics | exact | Воронка на SQL: сколько дошло до шага | исправлен | sqlite.org aggfunc; ключ через sqlite |
| `gen_analytics_metric_robust` | analytics | senior | python, statistics | exact | Расчёт метрики на Python | исправлен | определение персентиля (nearest-rank vs lower); ключ исполнением |
| `gen_analytics_backlog_prioritization_lead` | analytics | lead | system_analysis, agile | multichoice | Приоритизация бэклога и изменения требований | исправлен | scrumguides.org; RICE (intercom.com); MoSCoW (agilebusiness.org) |
| `gen_backend_py_init_super_order` | backend | senior | python, oop | exact | Порядок вызова __init__ и super() | исправлен | docs.python.org: super(), datamodel __slots__ |
| `gen_backend_sql_window_cte_group` | backend | senior | sql, postgresql | exact | Оконные функции, CTE и GROUP BY в два уровня | исправлен | postgresql.org: tutorial-window, functions-window |
| `gen_backend_lead_kafka_delivery_semantics` | backend | lead | system_design, kafka | multichoice | Kafka: доставка, порядок и идемпотентность | исправлен | kafka.apache.org (design: delivery semantics; producer configs acks) |
| `gen_backend_lead_public_api_contract` | backend | lead | rest, system_design | choice | Контракт публичного REST API | исправлен | RFC 6585 §4, RFC 9457, draft-ietf-httpapi-ratelimit-headers |
| `gen_data_py_median_mode_percentile` | data | senior | python, statistics | exact | Медиана, мода и персентиль по целым данным | исправлен | docs.python.org statistics, collections.Counter |
| `gen_data_sql_window_dedup_topn` | data | senior | sql | exact | Оконные функции: дедупликация, топ-N, LAG и накопительная сумма | исправлен | sqlite.org windowfunctions; postgresql.org sql-keywords |
| `gen_data_lead_pipeline_replay` | data | lead | airflow, spark | choice | Повторная загрузка данных за прошлое | исправлен | airflow.apache.org (Airflow 3, dag-run, templates); spark.apache.org |
| `gen_data_model_in_prod_lifecycle` | data | lead | ml, system_design | multichoice | Модель в проде: дрейф, утечка, мониторинг, A/B | исправлен | scikit-learn.org common_pitfalls, cross_validation |
| `gen_devops_chmod_octal` | devops | junior | bash, linux | choice | Права доступа chmod | одобрен | man7.org chmod(1) |
| `gen_devops_docker_cmd_entrypoint` | devops | junior | docker, linux | choice | Dockerfile и команды docker | исправлен | docs.docker.com dockerfile reference, build cache, attach |
| `gen_devops_ci_pipeline_semantics` | devops | middle | ci_cd, git | multichoice | Поведение CI-конвейера | исправлен | docs.gitlab.com ci/yaml, variables, caching, artifacts |
| `gen_devops_k8s_manifest_diagnosis` | devops | middle | kubernetes, docker | choice | Найти причину проблемы в манифесте Kubernetes | одобрен | kubernetes.io probes, resources, service |
| `gen_devops_log_window_analysis` | devops | senior | python, linux | exact | Анализ журнала: окно времени и ошибки | исправлен | ключ исполнением кода; Common Log Format |
| `gen_devops_lead_slo_alert_rollout` | devops | lead | kubernetes, prometheus | multichoice | SLO, алерты и стратегии выката | исправлен | sre.google workbook alerting-on-slos; kubernetes.io HPA |
| `gen_frontend_js_micro_macro_order` | frontend | senior | javascript | exact | Порядок микрозадач и макрозадач | исправлен | MDN Microtask guide; исполнение в node |
| `gen_frontend_react_rerender_cause` | frontend | senior | react, javascript | choice | Причина лишних перерисовок React | исправлен | react.dev memo, useState, StrictMode, rendering-lists |
| `gen_frontend_build_delivery_strategy` | frontend | lead | webpack, javascript | choice | Стратегия сборки и доставки | исправлен | webpack.js.org caching/devtool/split-chunks; vite.dev; web.dev http-cache |
| `gen_frontend_lead_arch_tradeoffs` | frontend | lead | typescript, react | multichoice | Архитектурные компромиссы фронтенда | исправлен | react.dev memo/useMemo; w3.org WAI ARIA APG |
| `gen_mobile_kotlin_null_safety_basics` | mobile | junior | kotlin, android | choice | Основы Kotlin в Android: null-safety и объявления | исправлен | kotlinlang.org null-safety |
| `gen_mobile_swift_optional_basics` | mobile | junior | swift, ios | choice | Основы Swift: опционалы и объявления | исправлен | docs.swift.org swift-book |
| `gen_mobile_network_background` | mobile | middle | android, rest | multichoice | Сетевой слой Android: корутины и Retrofit | исправлен | developer.android.com coroutines codelabs; retrofit KotlinExtensions |
| `gen_mobile_sqlite_join_group_count` | mobile | middle | sql, android | exact | Что вернёт запрос к локальной базе | исправлен | sqlite.org aggfunc; ключ через sqlite |
| `gen_mobile_flutter_state_http_senior` | mobile | senior | flutter, http | choice | Flutter: состояние, списки и сетевые ошибки | исправлен | api.flutter.dev ImageCache; docs.flutter.dev perf |
| `gen_mobile_lead_release_architecture` | mobile | lead | android, ios | multichoice | Релизы и совместимость Android/iOS | новый после ревью | developer.apple.com (App Store Connect phased release, App Review), support.google.com/googleplay (vitals, staged rollout), developer.android.com in-app-updates |
| `gen_qa_parametrize_product_count` | qa | senior | python, pytest | exact | Сколько тестов соберёт pytest: параметризация, skip и фикстуры | исправлен | docs.pytest.org parametrize/fixtures/skipping; сверка pytest 9.1 на 60 зёрнах |
| `gen_qa_sql_migration_diff` | qa | senior | sql, testing_theory | exact | Расхождения после миграции данных | исправлен | postgresql.org queries-union; sqlite.org compound-select |
| `gen_qa_lead_sprint_test_planning` | qa | lead | testing_theory, agile | choice | Планирование тестирования в спринте | исправлен | scrumguides.org; ISTQB CTFL 4.0.1 §5 |
| `gen_qa_lead_test_strategy_ci` | qa | lead | testing_theory, ci_cd | multichoice | Стратегия тестирования и пороги качества в CI | исправлен | ISTQB CTFL 4.0.1 §5.1.6 |
| `gen_security_linux_bash_basics` | security | junior | linux, bash | choice | Основы Linux и Bash для ИБ | одобрен | man7 crontab(5); sudo.ws sudoers; debian rsyslog |
| `gen_security_owasp_incident_choice` | security | junior | security_basics, networking | choice | Класс уязвимости по описанию инцидента | исправлен | top10.owasp.org 2021 A01/A02/A03/A05/A07 |
| `gen_security_sql_injection_or_rows` | security | middle | security_basics, sql | exact | SQL-инъекция: сколько строк вернёт запрос | исправлен | sqlite.org lang_comment; ключ через sqlite |
| `gen_security_xor_shift_cipher` | security | middle | python, cryptography | exact | Свойства XOR, ROT13, base64 и хеша | исправлен | docs.python.org hashlib, base64; ключ исполнением |
| `gen_security_container_hardening` | security | senior | security_basics, docker | multichoice | Безопасность контейнеров и секретов | исправлен | docs.docker.com run, swarm secrets |
| `gen_security_lead_zerotrust_ir` | security | lead | security_basics, networking | multichoice | Сегментация, нулевое доверие и реагирование на инцидент | новый после ревью | NIST SP 800-207, SP 800-61r3, SP 800-82r3, SP 800-63B-4; cisa.gov ransomware guide |

## Удалены по итогам ревью

- `gen_mobile_lead_arch_release` — дистракторы-карикатуры, сложность ниже lead; заменён новым шаблоном
- `gen_security_lead_zero_trust_incident` — текст сценария не влиял на ответ, дистракторы-карикатуры; заменён новым шаблоном
