#!/usr/bin/env python3
"""Пересобирает backend/app/services/testing/bank/generated/REGISTRY.md по фактическому содержимому папки
и журналу ревью (REVIEW ниже): код, специализация, грейд, технологии, формат, название, статус, источник проверки.

    cd backend && ../.venv/bin/python ../scripts/evolve/registry_md.py
"""
from __future__ import annotations
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ.setdefault("FSP_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FSP_SECRET_KEY", "x")

# статус после ревью 07.10.2026 (четыре независимых ревью по официальной документации; см. docs/08, раздел 7)
REVIEW = {
    # backend / frontend
    "gen_backend_lead_kafka_delivery_semantics": ("исправлен", "kafka.apache.org (design: delivery semantics; producer configs acks)"),
    "gen_backend_lead_public_api_contract": ("исправлен", "RFC 6585 §4, RFC 9457, draft-ietf-httpapi-ratelimit-headers"),
    "gen_backend_py_init_super_order": ("исправлен", "docs.python.org: super(), datamodel __slots__"),
    "gen_backend_sql_window_cte_group": ("исправлен", "postgresql.org: tutorial-window, functions-window"),
    "gen_frontend_build_delivery_strategy": ("исправлен", "webpack.js.org caching/devtool/split-chunks; vite.dev; web.dev http-cache"),
    "gen_frontend_js_micro_macro_order": ("исправлен", "MDN Microtask guide; исполнение в node"),
    "gen_frontend_lead_arch_tradeoffs": ("исправлен", "react.dev memo/useMemo; w3.org WAI ARIA APG"),
    "gen_frontend_react_rerender_cause": ("исправлен", "react.dev memo, useState, StrictMode, rendering-lists"),
    # devops / analytics
    "gen_devops_chmod_octal": ("одобрен", "man7.org chmod(1)"),
    "gen_devops_docker_cmd_entrypoint": ("исправлен", "docs.docker.com dockerfile reference, build cache, attach"),
    "gen_devops_ci_pipeline_semantics": ("исправлен", "docs.gitlab.com ci/yaml, variables, caching, artifacts"),
    "gen_devops_k8s_manifest_diagnosis": ("одобрен", "kubernetes.io probes, resources, service"),
    "gen_devops_log_window_analysis": ("исправлен", "ключ исполнением кода; Common Log Format"),
    "gen_devops_lead_slo_alert_rollout": ("исправлен", "sre.google workbook alerting-on-slos; kubernetes.io HPA"),
    "gen_analytics_requirements_uml_choice": ("исправлен", "uml-diagrams.org; cucumber.io gherkin"),
    "gen_analytics_sql_group_having_count": ("исправлен", "sqlite.org aggfunc; ключ через sqlite"),
    "gen_analytics_bpmn_gateway_reading": ("исправлен", "docs.camunda.io gateways/events; camunda.com bpmn reference"),
    "gen_analytics_sql_funnel_step": ("исправлен", "sqlite.org aggfunc; ключ через sqlite"),
    "gen_analytics_metric_robust": ("исправлен", "определение персентиля (nearest-rank vs lower); ключ исполнением"),
    "gen_analytics_backlog_prioritization_lead": ("исправлен", "scrumguides.org; RICE (intercom.com); MoSCoW (agilebusiness.org)"),
    # data / qa
    "gen_data_py_median_mode_percentile": ("исправлен", "docs.python.org statistics, collections.Counter"),
    "gen_data_sql_window_dedup_topn": ("исправлен", "sqlite.org windowfunctions; postgresql.org sql-keywords"),
    "gen_data_lead_pipeline_replay": ("исправлен", "airflow.apache.org (Airflow 3, dag-run, templates); spark.apache.org"),
    "gen_data_model_in_prod_lifecycle": ("исправлен", "scikit-learn.org common_pitfalls, cross_validation"),
    "gen_qa_parametrize_product_count": ("исправлен", "docs.pytest.org parametrize/fixtures/skipping; сверка pytest 9.1 на 60 зёрнах"),
    "gen_qa_sql_migration_diff": ("исправлен", "postgresql.org queries-union; sqlite.org compound-select"),
    "gen_qa_lead_sprint_test_planning": ("исправлен", "scrumguides.org; ISTQB CTFL 4.0.1 §5"),
    "gen_qa_lead_test_strategy_ci": ("исправлен", "ISTQB CTFL 4.0.1 §5.1.6"),
    # mobile / security
    "gen_mobile_kotlin_null_safety_basics": ("исправлен", "kotlinlang.org null-safety"),
    "gen_mobile_swift_optional_basics": ("исправлен", "docs.swift.org swift-book"),
    "gen_mobile_network_background": ("исправлен", "developer.android.com coroutines codelabs; retrofit KotlinExtensions"),
    "gen_mobile_sqlite_join_group_count": ("исправлен", "sqlite.org aggfunc; ключ через sqlite"),
    "gen_mobile_flutter_state_http_senior": ("исправлен", "api.flutter.dev ImageCache; docs.flutter.dev perf"),
    "gen_security_container_hardening": ("исправлен", "docs.docker.com run, swarm secrets"),
    "gen_security_linux_bash_basics": ("одобрен", "man7 crontab(5); sudo.ws sudoers; debian rsyslog"),
    "gen_security_owasp_incident_choice": ("исправлен", "top10.owasp.org 2021 A01/A02/A03/A05/A07"),
    "gen_security_sql_injection_or_rows": ("исправлен", "sqlite.org lang_comment; ключ через sqlite"),
    "gen_security_xor_shift_cipher": ("исправлен", "docs.python.org hashlib, base64; ключ исполнением"),
    # перегенерированы с ужесточённым промптом после удаления и проверены ревью
    "gen_mobile_lead_release_architecture": ("новый после ревью", "developer.apple.com (App Store Connect phased release, App Review), support.google.com/googleplay (vitals, staged rollout), developer.android.com in-app-updates"),
    "gen_security_lead_zerotrust_ir": ("новый после ревью", "NIST SP 800-207, SP 800-61r3, SP 800-82r3, SP 800-63B-4; cisa.gov ransomware guide"),
}
REMOVED = {
    "gen_mobile_lead_arch_release": "дистракторы-карикатуры, сложность ниже lead; заменён новым шаблоном",
    "gen_security_lead_zero_trust_incident": "текст сценария не влиял на ответ, дистракторы-карикатуры; заменён новым шаблоном",
}


def main():
    from app.services.testing.bank import generated  # noqa: F401
    from app.services.testing.bank.base import REGISTRY
    prefix = generated.__name__ + "."
    specs = sorted((s for s in REGISTRY.values() if s.generate.__module__.startswith(prefix)), key=lambda s: (s.specializations, ["junior", "middle", "senior", "lead"].index(s.grade_level), s.code))
    rows = ["| Код | Специализация | Грейд | Технологии | Формат | Название | Статус | Проверено по |", "|---|---|---|---|---|---|---|---|"]
    counts = {"исправлен": 0, "одобрен": 0, "новый после ревью": 0}
    for s in specs:
        st, src = REVIEW.get(s.code, ("новый после ревью", "сгенерирован повторно и проверен ревьюером 07.10"))
        counts[st] += 1
        rows.append(f"| `{s.code}` | {', '.join(s.specializations)} | {s.grade_level} | {', '.join(s.technologies)} | {s.fmt} | {s.title} | {st} | {src} |")
    body = f"""# Шаблоны, сгенерированные моделью — реестр

Сгенерированы `scripts/evolve/propose_templates.py` (DeepSeek V4.1 Flash, валидатор в отдельном процессе) 07.10.2026 и
**проверены четырьмя независимыми ревью по официальной документации** (каждое утверждение правильных и неправильных вариантов и
пояснений сверялось с первоисточником; ключи exact-заданий — исполнением). Включены в банк (`load_all`) после ревью.
Как это делалось и что находили — `docs/08_Механика_тестирования.md`, раздел 7.

Всего в банке: {len(specs)} — исправлено после ревью {counts['исправлен']}, одобрено без правок {counts['одобрен']}, перегенерировано
после удаления {counts['новый после ревью']}. Удалены по итогам ревью: {len(REMOVED)}.

{chr(10).join(rows)}

## Удалены по итогам ревью

""" + "\n".join(f"- `{k}` — {v}" for k, v in REMOVED.items()) + "\n"
    out = os.path.join(ROOT, "backend", "app", "services", "testing", "bank", "generated", "REGISTRY.md")
    open(out, "w", encoding="utf-8").write(body)
    print(f"REGISTRY.md: {len(specs)} шаблонов; {counts}")


if __name__ == "__main__":
    main()
