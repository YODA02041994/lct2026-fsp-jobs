"""Диагностика манифеста Kubernetes: readiness/liveness, requests/limits, селектор, образ latest."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_devops_k8s_manifest_diagnosis", title="Найти причину проблемы в манифесте Kubernetes",
          competency="Kubernetes: диагностика манифеста Deployment/Service",
          specializations=["devops"], technologies=["kubernetes", "docker"], fmt="choice",
          grade_level="middle", difficulty_shift=0.1)
def _k8s_manifest_diagnosis(rng: random.Random) -> Instance:
    app = rng.choice(["payments-api", "orders-api", "auth-service", "search-service", "notify-worker", "billing-api", "catalog-api"])
    port = rng.choice([8080, 8000, 3000, 5000, 9000])
    other = rng.choice([p for p in (8080, 8000, 3000, 5000, 9000) if p != port])
    ns = rng.choice(["prod", "staging", "default"])
    ver = rng.choice(["1.4.2", "2.0.0", "0.9.7"])

    scenarios = [
        (
            f"Pod в статусе CrashLoopBackOff. В логах контейнера: 'server started on :{port}' и дальше тишина.\n"
            f"В манифесте Deployment указано:\n"
            f"  livenessProbe:\n    httpGet:\n      path: /healthz\n      port: {other}\n",
            f"livenessProbe обращается к порту {other}, а приложение слушает {port} — проба всегда падает, "
            f"kubelet перезапускает контейнер.",
            "Порт пробы не совпадает с портом приложения",
            "Приложение не умеет обрабатывать /healthz",
            "Не задан readinessProbe, поэтому pod не становится Ready",
            "Образ собран с тегом latest, поэтому kubelet не может его найти",
            "В контейнере не указан securityContext, поэтому проба запрещена",
        ),
        (
            f"Pod в статусе Running и Ready, но Service {app} не отдаёт трафик: у endpoints сервиса пустой список.\n"
            f"В Deployment метки: app: {app}-v2, а в Service селектор: app: {app}\n",
            "Селектор Service не совпадает с метками pod'ов, поэтому endpoints не наполняются.",
            "Метки pod'ов не совпадают с селектором Service",
            "Service создан в другом namespace, чем Deployment",
            "У pod'ов нет readinessProbe, поэтому они не попадают в endpoints",
            "Порт Service не совпадает с containerPort",
            "kube-proxy не запущен на нодах кластера",
        ),
        (
            f"Pod периодически перезапускается (RESTARTS растёт), хотя приложение отвечает на запросы.\n"
            f"В манифесте:\n"
            f"  livenessProbe:\n    httpGet:\n      path: /healthz\n      port: {port}\n    initialDelaySeconds: 1\n"
            f"    periodSeconds: 2\n    failureThreshold: 1\n",
            "Проба слишком агрессивная: приложение не успевает стартовать/ответить, kubelet убивает контейнер.",
            "livenessProbe настроена слишком агрессивно (малый initialDelaySeconds и failureThreshold=1)",
            "readinessProbe не задана, поэтому pod перезапускается",
            "resources.requests не заданы, поэтому kubelet убивает pod",
            "Образ собран с тегом latest, поэтому pod перезапускается",
            "В containerPort указан неверный порт",
        ),
        (
            f"Pod в статусе Pending, в событиях: '0/3 nodes are available: 3 Insufficient cpu'.\n"
            f"В манифесте:\n"
            f"  resources:\n    requests:\n      cpu: \"4\"\n      memory: \"512Mi\"\n",
            "Запрошено 4 CPU, которых нет ни на одной ноде — планировщик не может разместить pod.",
            "resources.requests.cpu=4 превышает доступные ресурсы нод",
            "Образ собран с тегом latest, поэтому pod не планируется",
            "Не задан nodeSelector, поэтому pod не планируется",
            "livenessProbe не задана, поэтому pod висит в Pending",
            "Service не имеет ClusterIP, поэтому pod не планируется",
        ),
        (
            f"Pod в статусе Running, но не Ready: readinessProbe возвращает 500.\n"
            f"В манифесте:\n"
            f"  readinessProbe:\n    httpGet:\n      path: /ready\n      port: {port}\n"
            f"  livenessProbe:\n    httpGet:\n      path: /healthz\n      port: {port}\n",
            "Приложение отвечает 500 на /ready — readinessProbe не проходит, pod исключается из endpoints.",
            "readinessProbe получает 500 на /ready, поэтому pod не становится Ready",
            "livenessProbe и readinessProbe используют один и тот же порт",
            "Образ собран с тегом latest, поэтому pod не становится Ready",
            "Не задан initialDelaySeconds, поэтому pod не становится Ready",
            "Service не имеет селектора, поэтому pod не становится Ready",
        ),
        (
            f"Pod в статусе ImagePullBackOff: 'manifest for {app}:latest not found'.\n"
            f"В манифесте: image: {app}:latest\n",
            "Тег latest не найден в реестре (или образ не собран/не запушен) — kubelet не может скачать образ.",
            "Образ с тегом latest отсутствует в реестре",
            "kubelet не поддерживает тег latest",
            "В манифесте не указан imagePullPolicy: Always",
            "Не задан imagePullSecret, поэтому образ не скачивается",
            "Deployment находится в другом namespace, поэтому образ не скачивается",
        ),
        (
            f"Pod в статусе Running, но приложение падает с OOMKilled.\n"
            f"В манифесте:\n"
            f"  resources:\n    requests:\n      memory: \"128Mi\"\n    limits:\n      memory: \"128Mi\"\n",
            "Лимит памяти равен 128Mi, и приложение его превышает — ядро убивает контейнер (OOMKilled).",
            "resources.limits.memory слишком мал для приложения",
            "resources.requests.memory должен быть больше limits.memory",
            "Образ собран с тегом latest, поэтому приложение падает",
            "livenessProbe не задана, поэтому приложение падает",
            "Service не имеет ClusterIP, поэтому приложение падает",
        ),
    ]
    idx = rng.randrange(len(scenarios))
    ctx, expl, correct, *wrong = scenarios[idx]
    code = (
        f"apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {app}\n  namespace: {ns}\n"
        f"spec:\n  replicas: 2\n  template:\n    spec:\n      containers:\n      - name: {app}\n"
        f"        image: {app}:{ver}\n"
    )
    options = [correct] + wrong
    question = (
        f"В кластере Kubernetes namespace {ns} развёрнут сервис {app}. "
        f"Ниже — выдержка из манифеста и симптом. Что является причиной проблемы?"
    )
    return _choice(rng, question, options, 0, expl, code=ctx, language="text")
