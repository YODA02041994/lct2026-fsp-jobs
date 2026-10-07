"""Проверяет понимание поведения конвейера GitLab CI: needs, кэш по файлам, артефакты, маскирование переменных,
правила запуска по веткам и тегам, allow_failure. Утверждения привязаны к конкретным job показанного .gitlab-ci.yml.
Сверено с docs.gitlab.com/ci/yaml/, /ci/caching/, /ci/jobs/job_artifacts/, /ci/variables/, /ci/variables/predefined_variables/."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_devops_ci_pipeline_semantics", title="Поведение CI-конвейера",
          competency="CI/CD: стадии, кэш, артефакты, триггеры",
          specializations=["devops"], technologies=["ci_cd", "git"], fmt="multichoice",
          grade_level="middle", difficulty_shift=0.1)
def _ci_pipeline(rng: random.Random) -> Instance:
    branch = rng.choice(["main", "develop", "release-2.7"])
    tag = rng.choice(["v1.4.0", "v2.0.1", "v0.9.3"])
    lockfile = rng.choice(["package-lock.json", "requirements.txt", "go.sum", "poetry.lock"])
    artifact = rng.choice(["dist/app.jar", "build/app.zip", "target/app.bin"])
    secret = rng.choice(["DB_PASSWORD", "API_TOKEN", "REGISTRY_KEY"])
    env = rng.choice(["production", "staging"])
    expire = rng.choice(["1 week", "3 days", "1 month"])

    # Тема -> (верное утверждение, неверное утверждение). В один экземпляр тема попадает не более одного раза.
    topics = [
        (  # needs
            "Job `test` с `needs: [build]` стартует сразу после успешного завершения `build`, не дожидаясь "
            "завершения остальных job предыдущих стадий; если `build` упадёт, `test` будет пропущен.",
            "Job `test` с `needs: [build]` запустится одновременно с `build`: `needs` задаёт только порядок "
            "отображения job в графе конвейера.",
        ),
        (  # cache
            f"Ключ кэша job `test` — SHA от содержимого `{lockfile}`: пока файл не меняется, кэш переиспользуется "
            f"между конвейерами; после правки файла ключ другой и кэш промахивается.",
            f"Кэш job `test` гарантированно доступен на любом раннере проекта без настройки распределённого кэша "
            f"(S3/NFS), потому что GitLab хранит кэш на своём сервере вместе с артефактами.",
        ),
        (  # artifacts
            f"Артефакт `{artifact}` из job `build` скачивается в job следующих стадий (и в `test` через `needs`) "
            f"и доступен для скачивания в интерфейсе GitLab после завершения job, пока не истёк `expire_in: {expire}`.",
            f"Артефакт `{artifact}` существует только внутри job `build` и удаляется сразу после его завершения; "
            f"другим job он недоступен.",
        ),
        (  # masked variable
            f"Если переменная `{secret}` помечена как masked, её значение в журнале job заменяется на `[MASKED]`, "
            f"но это не гарантия: вывод в изменённом виде (например, с экранированием) не маскируется.",
            f"`echo ${secret}` в `script` безопасен: GitLab гарантированно вырезает из журнала значение "
            f"переменной в любом виде, включая экранированный и закодированный.",
        ),
        (  # tag rule
            f"Job `release` с `rules: - if: $CI_COMMIT_TAG` запускается в конвейере тега `{tag}` и не запускается "
            f"при пуше в ветку `{branch}`: в конвейере ветки `$CI_COMMIT_TAG` пуста.",
            f"Job `release` с `rules: - if: $CI_COMMIT_TAG` выполнится и при пуше в ветку `{branch}`, если имя "
            f"ветки начинается с `v`, как у тега.",
        ),
        (  # branch rule
            f"Job `deploy` с `rules: - if: $CI_COMMIT_BRANCH == \"{branch}\"` не запустится в конвейере тега "
            f"`{tag}`: переменная `$CI_COMMIT_BRANCH` в конвейерах тегов недоступна.",
            f"Job `deploy` с `rules: - if: $CI_COMMIT_BRANCH == \"{branch}\"` запустится и в конвейере тега "
            f"`{tag}`, потому что тег указывает на коммит из ветки `{branch}`.",
        ),
        (  # allow_failure
            "Падение job `lint` с `allow_failure: true` не блокирует конвейер: конвейер считается успешным, "
            "а job отмечается оранжевым предупреждением.",
            "При падении job `lint` конвейер получает статус failed, как и при падении любого другого job; "
            "`allow_failure: true` влияет только на уведомления.",
        ),
    ]

    k = rng.randint(2, 3)
    order = list(range(len(topics)))
    rng.shuffle(order)
    correct = [topics[i][0] for i in order[:k]]
    wrong = [topics[i][1] for i in order[k:6]]

    code = (
        "stages: [build, test, deploy]\n\n"
        "build:\n"
        "  stage: build\n"
        "  script: [\"make build\"]\n"
        "  artifacts:\n"
        f"    paths: [\"{artifact}\"]\n"
        f"    expire_in: {expire}\n\n"
        "test:\n"
        "  stage: test\n"
        "  needs: [build]\n"
        "  script: [\"make test\"]\n"
        "  cache:\n"
        "    key:\n"
        f"      files: [{lockfile}]\n"
        "    paths: [\".cache/\"]\n\n"
        "lint:\n"
        "  stage: test\n"
        "  allow_failure: true\n"
        "  script: [\"make lint\"]\n\n"
        "deploy:\n"
        "  stage: deploy\n"
        "  rules:\n"
        f"    - if: $CI_COMMIT_BRANCH == \"{branch}\"\n"
        f"  script: [\"./deploy.sh\"]   # пароль читает из ${secret} — masked-переменная проекта\n"
        f"  environment: {env}\n\n"
        "release:\n"
        "  stage: deploy\n"
        "  rules:\n"
        "    - if: $CI_COMMIT_TAG\n"
        "  script: [\"make release\"]\n"
    )

    question = (
        f"Ниже файл .gitlab-ci.yml проекта. Разработчики пушат в ветку `{branch}` и ставят теги вида `{tag}`. "
        "Какие утверждения о поведении конвейера верны? Выберите все подходящие."
    )
    explanation = (
        "`needs` запускает job сразу после завершения зависимостей, а при их падении job пропускается. "
        f"`cache:key:files` считает SHA от содержимого `{lockfile}`; кэш хранится на раннере и без распределённого "
        "хранилища между раннерами не разделяется. Артефакты хранятся на сервере GitLab, скачиваются в следующие "
        "стадии и доступны в интерфейсе до `expire_in`. Masked-переменная выводится как `[MASKED]`, но маскирование "
        "не гарантия. `$CI_COMMIT_BRANCH` недоступна в конвейерах тегов, `$CI_COMMIT_TAG` есть только в них. "
        "`allow_failure: true` оставляет конвейер успешным с предупреждением."
    )
    return _multi(rng, question, correct, wrong, explanation, code=code, language="text")
