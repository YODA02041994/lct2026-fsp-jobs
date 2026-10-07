"""Проверка понимания Dockerfile (CMD против ENTRYPOINT, EXPOSE и -p, кэш слоёв) и повседневных команд docker.
Дистракторы подобраны под каждый вопрос. Сверено с docs.docker.com/reference/dockerfile/, /build/cache/optimize/,
/reference/cli/docker/container/attach/."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_devops_docker_cmd_entrypoint", title="Dockerfile и команды docker",
          competency="Docker: CMD, ENTRYPOINT, EXPOSE, повседневные команды",
          specializations=["devops"], technologies=["docker", "linux"],
          fmt="choice", grade_level="junior", difficulty_shift=-0.2)
def _docker_basics(rng: random.Random) -> Instance:
    app = rng.choice(["app.py", "main.py", "server.py", "worker.py"])
    port = rng.choice([3000, 5000, 8000, 8080, 9000])
    img = rng.choice(["myapp:1.0", "web:latest", "api:v2", "svc:dev"])
    cname = rng.choice(["web1", "api1", "svc1", "app1"])
    host_port = rng.choice([p for p in (8080, 9090, 3001, 5001) if p != port])

    def dockerfile(last: str) -> str:
        return (
            "FROM python:3.12-slim\n"
            "WORKDIR /srv\n"
            "COPY requirements.txt .\n"
            "RUN pip install -r requirements.txt\n"
            "COPY . .\n"
            f"EXPOSE {port}\n"
            f"{last}\n"
        )

    cases = [
        (
            f"Контейнер запущен командой ниже. По какому адресу на хосте доступно приложение, "
            f"слушающее порт {port} внутри контейнера?",
            f"http://localhost:{host_port}",
            [
                f"http://localhost:{port}",
                f"http://localhost:{host_port + 1}",
                "На случайном свободном порту хоста: -p сам выбирает порт",
                "Только из других контейнеров: с хоста приложение недоступно",
                "Недоступно, пока не добавлен флаг --network host",
            ],
            "Флаг -p ХОСТ:КОНТЕЙНЕР публикует порт контейнера на указанном порту хоста; первое число — порт хоста.",
            f"docker run -d -p {host_port}:{port} {img}",
        ),
        (
            "Что произойдёт, если запустить `docker run <образ> bash`?",
            "Выполнится bash: аргумент после имени образа заменит CMD",
            [
                f"Выполнится python {app}: CMD имеет приоритет над аргументами docker run",
                f"Выполнится python {app} bash: аргумент добавится к CMD",
                "Контейнер не запустится: CMD и аргументы docker run конфликтуют",
                f"Выполнится bash, а после его выхода — python {app}",
                f"Сначала выполнится python {app}, затем bash в том же контейнере",
            ],
            "CMD задаёт команду по умолчанию; аргументы после имени образа в docker run целиком заменяют её.",
            dockerfile(f'CMD ["python", "{app}"]'),
        ),
        (
            "Что произойдёт, если запустить `docker run <образ> --help`?",
            f"Запустится python {app} --help: аргументы добавляются к ENTRYPOINT",
            [
                "Запустится команда --help: ошибка «executable file not found»",
                "docker run покажет собственную справку по команде docker run",
                f"Запустится python {app} без аргументов: ENTRYPOINT не принимает аргументы docker run",
                "ENTRYPOINT будет заменён на --help, контейнер сразу завершится",
                "Без флага --entrypoint аргументы в контейнер не передаются",
            ],
            "Для ENTRYPOINT в exec-форме аргументы docker run дописываются после его элементов.",
            dockerfile(f'ENTRYPOINT ["python", "{app}"]'),
        ),
        (
            f"В Dockerfile есть строка EXPOSE {port}. Что она делает?",
            "Только документирует порт: при docker run он не публикуется автоматически",
            [
                f"Публикует порт {port} на том же номере на хосте при любом docker run",
                "Публикует порт на случайный порт хоста при любом docker run",
                f"Открывает порт {port} в сетевом фильтре хоста",
                f"Запрещает приложению слушать порты, кроме {port}",
                f"Пробрасывает порт {port} во все контейнеры той же сети",
            ],
            "EXPOSE носит информационный характер; публикация порта делается флагом -p (или -P для всех EXPOSE-портов).",
            dockerfile(f'CMD ["python", "{app}"]'),
        ),
        (
            "Какой файл исключает ненужные файлы из контекста сборки, ускоряя docker build?",
            ".dockerignore",
            [
                ".gitignore — docker build читает его автоматически",
                "Dockerfile.ignore",
                "Флаг docker build --exclude",
                ".dockerexclude",
                "Секция ignore в docker-compose.yml",
            ],
            ".dockerignore перечисляет пути, которые не отправляются в контекст сборки.",
            None,
        ),
        (
            f"Нужно посмотреть уже накопленный вывод (stdout/stderr) работающего контейнера {cname}, "
            "не подключаясь к его процессу. Какая команда это делает?",
            f"docker logs {cname}",
            [
                f"docker attach {cname}",
                f"docker inspect {cname}",
                f"docker exec {cname} cat /var/log/syslog",
                f"docker top {cname}",
                f"docker stats {cname}",
            ],
            "docker logs выводит накопленный stdout/stderr контейнера; docker attach подключает терминал к потокам "
            "процесса и историю не показывает.",
            None,
        ),
        (
            f"Нужно выполнить bash внутри уже запущенного контейнера {cname}. Какая команда подходит?",
            f"docker exec -it {cname} bash",
            [
                f"docker run -it {img} bash",
                f"docker attach {cname}",
                f"docker start -a {cname}",
                f"docker ssh {cname}",
                f"docker exec {cname}",
            ],
            "docker exec запускает новый процесс в работающем контейнере; -it даёт интерактивный терминал. "
            "docker run создал бы новый контейнер, docker attach подключает к уже работающему процессу.",
            None,
        ),
        (
            "Почему COPY requirements.txt и RUN pip install идут до COPY . . ?",
            "Чтобы слой с установкой зависимостей оставался в кэше при изменении кода",
            [
                "Чтобы итоговый образ занимал меньше места",
                "Чтобы COPY . . не перезаписал установленные пакеты",
                "Чтобы pip install выполнялся параллельно с COPY",
                "Так требует синтаксис Dockerfile: RUN должен идти до второго COPY",
                "Чтобы requirements.txt не попал в итоговый образ",
            ],
            "Docker кэширует слои: изменение слоя пересобирает все следующие. Пока requirements.txt не менялся, "
            "слой с pip install берётся из кэша, даже если код изменился.",
            dockerfile(f'CMD ["python", "{app}"]'),
        ),
    ]
    idx = rng.randrange(len(cases))
    q, correct, wrong, expl, code = cases[idx]
    options = [correct] + list(wrong)
    return _choice(rng, q, options, 0, expl, code=code, language="text")
