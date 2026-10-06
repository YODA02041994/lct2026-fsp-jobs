"""Mock-сервер для проверки фронтенда без бэкенда.

Запуск:  python3 frontend/mock/server.py          (порт 8001, можно задать первым аргументом)
Отдаёт статику из frontend/ и API по docs/API_контракт.md на /api/v1 (и на /fsp/api/v1 — для проверки префикса).
Только стандартная библиотека. Данные в памяти, выдуманные, сбрасываются при перезапуске.

Демонстрационные учётные записи (пароль у всех: demo):
  candidate@demo.ru   — кандидат с пройденным тестом, связью с ФСП, приглашениями и откликами
  newbie@demo.ru      — кандидат без теста и без истории ФСП (пустые состояния)
  employer@demo.ru    — работодатель с потребностью, подборкой из двух версий, вакансиями и заданиями
  pending@demo.ru     — почта не подтверждена (вход даёт 403)
"""
from __future__ import annotations

import json
import mimetypes
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent          # frontend/
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("application/json", ".json")


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") if dt else None


def days(n: int) -> datetime:
    return now() + timedelta(days=n)


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


# ---------------------------------------------------------------- справочники
SPECIALIZATIONS = [
    ("backend", "Бэкенд-разработка", "серверная логика, API, базы данных", True),
    ("frontend", "Фронтенд-разработка", "интерфейсы в браузере", True),
    ("fullstack", "Фулстек-разработка", "бэкенд и фронтенд", False),
    ("mobile", "Мобильная разработка", "Android, iOS, кроссплатформенные приложения", False),
    ("data", "Данные и машинное обучение", "аналитика данных, инженерия данных, модели", True),
    ("devops", "DevOps и эксплуатация", "инфраструктура, сборка, развёртывание, наблюдаемость", False),
    ("qa", "Тестирование", "ручное и автоматизированное тестирование", True),
    ("analytics", "Аналитика", "системный и бизнес-анализ, продуктовая аналитика", False),
    ("security", "Информационная безопасность", "защита приложений и инфраструктуры", False),
]
GRADES = [
    ("junior", "Junior", "до года опыта или стажёр"),
    ("middle", "Middle", "от года до трёх лет, самостоятельные задачи"),
    ("senior", "Senior", "от трёх лет, ведёт сложные задачи и проектирует"),
    ("lead", "Lead", "руководит разработкой и командой"),
]
GRADE_ORDER = [g[0] for g in GRADES]
WORK_FORMATS = [("office", "Офис"), ("remote", "Удалённо"), ("hybrid", "Гибрид")]
SKILLS = [
    ("python", "Python", "lang"), ("java", "Java", "lang"), ("kotlin", "Kotlin", "lang"), ("go", "Go", "lang"),
    ("javascript", "JavaScript", "lang"), ("typescript", "TypeScript", "lang"), ("csharp", "C#", "lang"),
    ("cpp", "C++", "lang"), ("php", "PHP", "lang"), ("swift", "Swift", "lang"), ("bash", "Bash", "lang"),
    ("sql", "SQL", "data"), ("postgresql", "PostgreSQL", "db"), ("mysql", "MySQL", "db"), ("clickhouse", "ClickHouse", "db"),
    ("mongodb", "MongoDB", "db"), ("redis", "Redis", "db"), ("kafka", "Kafka", "infra"), ("rabbitmq", "RabbitMQ", "infra"),
    ("docker", "Docker", "infra"), ("kubernetes", "Kubernetes", "infra"), ("linux", "Linux", "infra"), ("git", "Git", "tools"),
    ("ci_cd", "CI/CD", "infra"), ("nginx", "nginx", "infra"), ("terraform", "Terraform", "infra"), ("rest", "REST API", "web"),
    ("grpc", "gRPC", "web"), ("fastapi", "FastAPI", "framework"), ("django", "Django", "framework"), ("flask", "Flask", "framework"),
    ("spring", "Spring", "framework"), ("nodejs", "Node.js", "framework"), ("react", "React", "framework"), ("vue", "Vue", "framework"),
    ("angular", "Angular", "framework"), ("html", "HTML", "web"), ("css", "CSS", "web"), ("webpack", "Webpack", "tools"),
    ("pandas", "pandas", "data"), ("numpy", "NumPy", "data"), ("scikit_learn", "scikit-learn", "ml"), ("pytorch", "PyTorch", "ml"),
    ("ml", "Машинное обучение", "ml"), ("nlp", "Обработка языка", "ml"), ("statistics", "Статистика", "data"),
    ("spark", "Spark", "data"), ("airflow", "Airflow", "data"), ("pytest", "pytest", "qa"), ("selenium", "Selenium", "qa"),
    ("playwright", "Playwright", "qa"), ("postman", "Postman", "qa"), ("jmeter", "JMeter", "qa"),
    ("system_analysis", "Системный анализ", "analytics"), ("bpmn", "BPMN", "analytics"), ("powerbi", "Power BI", "analytics"),
]
SKILL_NAME = {c: n for c, n, _ in SKILLS}
SKILL_NAME["algorithms"] = "Алгоритмы"
SKILL_SYNONYMS = {
    "python": ["python", "питон", "python3"], "fastapi": ["fastapi"], "django": ["django", "drf"], "postgresql": ["postgres", "postgresql"],
    "sql": ["sql"], "redis": ["redis"], "kafka": ["kafka", "кафка"], "docker": ["docker", "докер"], "kubernetes": ["kubernetes", "k8s"],
    "react": ["react", "реакт", "next.js"], "vue": ["vue", "nuxt"], "typescript": ["typescript", "ts"], "javascript": ["javascript", "js"],
    "go": ["golang", " go "], "java": ["java", "джава"], "spring": ["spring"], "pytorch": ["pytorch", "torch"], "pandas": ["pandas"],
    "ml": ["машинн", "ml ", "нейросет"], "airflow": ["airflow"], "spark": ["spark"], "clickhouse": ["clickhouse"],
    "pytest": ["pytest", "юнит"], "selenium": ["selenium"], "playwright": ["playwright"], "grpc": ["grpc"], "rest": ["rest", "api"],
    "linux": ["linux"], "ci_cd": ["ci/cd", "gitlab ci", "github actions"], "nginx": ["nginx"], "git": ["git"],
    "css": ["css", "вёрстк"], "html": ["html"], "nodejs": ["node"], "statistics": ["статист", "a/b"],
}
WEIGHTS = {"stack": 0.35, "grade": 0.25, "strength": 0.20, "fsp": 0.10, "activity": 0.05, "conditions": 0.05}
TEST_CFG = {"block_size": 4, "blocks": 2, "item_seconds": 90}
SPEC_TITLE = {c: n for c, n, *_ in SPECIALIZATIONS}
GRADE_TITLE = {c: t for c, t, _ in GRADES}


def category(spec: str | None, grade: str | None) -> dict | None:
    if not spec or not grade:
        return None
    return {"specialization_code": spec, "grade": grade, "title": f"{SPEC_TITLE[spec]} · {GRADE_TITLE[grade]}"}


def extract_stack(text: str) -> list[str]:
    low = f" {text.lower()} "
    found = []
    for code, words in SKILL_SYNONYMS.items():
        if any(w in low for w in words):
            found.append(code)
    return found


# ---------------------------------------------------------------- данные
DB: dict = {"users": {}, "candidates": {}, "employers": {}, "achievements": [], "sessions": {}, "invitations": [],
            "vacancies": [], "applications": [], "short_tasks": [], "short_answers": [], "needs": [], "selections": [],
            "fsp_states": {}, "confirm_tokens": {}}
SEQ = {"user": 0, "candidate": 0, "employer": 0, "achievement": 0, "session": 0, "item": 0, "invitation": 0, "vacancy": 0,
       "application": 0, "short_task": 0, "short_answer": 0, "need": 0, "selection": 0, "version": 0}


def nid(kind: str) -> int:
    SEQ[kind] += 1
    return SEQ[kind]


def add_user(email: str, role: str, confirmed: bool = True, password: str = "demo") -> dict:
    u = {"id": nid("user"), "email": email, "password": password, "role": role, "email_confirmed": confirmed}
    DB["users"][u["id"]] = u
    return u


def add_candidate(user: dict, **kw) -> dict:
    c = {
        "id": nid("candidate"), "user_id": user["id"], "alias": f"Кандидат № {1000 + SEQ['candidate']}",
        "full_name": "", "phone": "", "telegram": "", "city": "", "experience_years": None, "roles": [], "soft_skills": [],
        "about": "", "salary_min": None, "salary_max": None, "work_format": None, "specialization_code": None,
        "claimed_grade": None, "grade": None, "grade_changed_at": None, "grade_change_available_at": None,
        "fsp_id": None, "fsp_linked_at": None, "visible_to_employers": True,
        "privacy": {"achievements": True, "city": True, "salary": True, "fsp_link": True},
        "consents": {"processing": False, "publication": False},
        "skills": [], "last_test_id": None, "last_active_at": iso(days(-1)), "email": user["email"],
    }
    c.update(kw)
    DB["candidates"][c["id"]] = c
    return c


def skill(code: str, confirmed: bool = False, score: float | None = None, source: str = "profile") -> dict:
    return {"skill": code, "name": SKILL_NAME.get(code, code), "source": source, "confirmed_by_test": confirmed, "test_score": score}


def add_achievement(cand: dict, **kw) -> dict:
    a = {"id": nid("achievement"), "candidate_id": cand["id"], "kind": "result", "title": "", "discipline": "", "level_code": "A1",
         "place": None, "date": "", "valid_until": None, "trust_level": "claimed", "status": "active", "hidden": False, "event": None}
    a.update(kw)
    DB["achievements"].append(a)
    return a


def seed() -> None:
    rnd = random.Random(7)
    # --- работодатель
    emp_user = add_user("employer@demo.ru", "employer")
    emp = {"id": nid("employer"), "user_id": emp_user["id"], "company_name": "Лаборатория данных «Вектор»",
           "description": "Разрабатываем сервисы аналитики для розничных сетей: витрины данных, прогноз спроса, API для партнёров.",
           "industry": "Разработка ПО, аналитика данных", "website": "https://vektor.example", "city": "Москва",
           "contact_person": "Ирина Соколова", "contact_email": "hr@vektor.example", "contact_phone": "+7 495 000-00-00"}
    DB["employers"][emp["id"]] = emp
    emp2_user = add_user("hr@severnoe.example", "employer")
    emp2 = {"id": nid("employer"), "user_id": emp2_user["id"], "company_name": "Северное ПО", "description": "Промышленная автоматизация.",
            "industry": "Промышленность", "website": "", "city": "Санкт-Петербург", "contact_person": "Олег Крылов",
            "contact_email": "job@severnoe.example", "contact_phone": ""}
    DB["employers"][emp2["id"]] = emp2

    # --- кандидат с полным профилем
    u1 = add_user("candidate@demo.ru", "candidate")
    c1 = add_candidate(
        u1, full_name="Иванов Пётр Сергеевич", phone="+7 912 000-11-22", telegram="@petr_dev", city="Казань", experience_years=3,
        roles=["бэкенд-разработчик", "наставник стажёров"], soft_skills=["коммуникация", "самостоятельность", "наставничество"],
        about="Пишу сервисы на Python: FastAPI, PostgreSQL, очереди. Участвую в соревнованиях по продуктовому программированию.",
        salary_min=180_000, salary_max=240_000, work_format="hybrid", specialization_code="backend", claimed_grade="middle",
        grade="middle", grade_changed_at=iso(days(-20)), grade_change_available_at=iso(days(70)),
        fsp_id="FSP-2023-104211", fsp_linked_at=iso(days(-30)), consents={"processing": True, "publication": True},
        skills=[skill("python", True, 0.9, "test"), skill("fastapi", True, 0.75, "test"), skill("postgresql", True, 0.8, "test"),
                skill("sql", True, 1.0, "test"), skill("redis"), skill("docker"), skill("git"), skill("kafka", False, 0.25, "test")],
    )
    add_achievement(c1, kind="rank", title="Кандидат в мастера спорта", discipline="продуктовое программирование", level_code="A4",
                    date="2025-11-12", valid_until="2028-11-12", trust_level="source",
                    event={"name": "Чемпионат России по спортивному программированию", "ekp_number": "ЕКП 24-1187", "level": "всероссийский"})
    add_achievement(c1, kind="result", title="Кубок Республики Татарстан", discipline="продуктовое программирование", level_code="A3", place=2,
                    date="2025-05-18", trust_level="source", event={"name": "Кубок Республики Татарстан", "ekp_number": "ЕКП 25-0412", "level": "региональный"})
    add_achievement(c1, kind="result", title="Финалист хакатона «Цифровой прорыв»", discipline="программирование продуктовое", level_code="A2",
                    place=7, date="2024-10-02", trust_level="document")
    add_achievement(c1, kind="other", title="Призёр внутреннего хакатона университета", discipline="алгоритмическое программирование",
                    level_code="A1", place=3, date="2023-04-10", trust_level="claimed")
    add_achievement(c1, kind="result", title="Участие в отборочном этапе (устаревшая запись)", discipline="алгоритмическое программирование",
                    level_code="A1", date="2022-02-01", valid_until="2024-02-01", trust_level="document", status="expired", hidden=True)

    # --- кандидат без теста и без ФСП
    u2 = add_user("newbie@demo.ru", "candidate")
    add_candidate(u2, full_name="", consents={"processing": True, "publication": False})

    # --- почта не подтверждена
    add_user("pending@demo.ru", "candidate", confirmed=False)

    # --- банк синтетических кандидатов
    bank = [
        ("backend", "middle", ["python", "django", "postgresql", "redis", "docker"], ["python", "postgresql"], True, "Москва", 170_000, 220_000, "remote"),
        ("backend", "senior", ["python", "fastapi", "postgresql", "kafka", "kubernetes", "grpc"], ["python", "fastapi", "kafka"], True, "Санкт-Петербург", 280_000, 350_000, "hybrid"),
        ("backend", "junior", ["python", "flask", "sql", "git"], ["python"], False, "Нижний Новгород", 80_000, 110_000, "office"),
        ("backend", "middle", ["go", "postgresql", "docker", "grpc"], ["go", "postgresql"], False, "Екатеринбург", 190_000, 240_000, "remote"),
        ("backend", "senior", ["java", "spring", "kafka", "postgresql"], ["java", "spring"], True, "Москва", 300_000, 380_000, "office"),
        ("backend", "lead", ["python", "fastapi", "postgresql", "kafka", "kubernetes"], ["python", "postgresql"], True, "Москва", 350_000, 450_000, "hybrid"),
        ("frontend", "middle", ["javascript", "typescript", "react", "css"], ["javascript", "react"], False, "Казань", 150_000, 200_000, "remote"),
        ("frontend", "senior", ["typescript", "vue", "webpack", "css", "html"], ["typescript", "vue"], True, "Москва", 260_000, 320_000, "hybrid"),
        ("data", "middle", ["python", "pandas", "sql", "scikit_learn", "airflow"], ["python", "sql", "pandas"], True, "Новосибирск", 180_000, 230_000, "remote"),
        ("data", "senior", ["python", "pytorch", "spark", "clickhouse", "ml"], ["python", "pytorch"], False, "Москва", 300_000, 400_000, "remote"),
        ("qa", "middle", ["pytest", "selenium", "python", "postman"], ["pytest", "python"], False, "Самара", 120_000, 160_000, "hybrid"),
        ("devops", "middle", ["linux", "docker", "kubernetes", "ci_cd", "terraform"], ["linux", "docker"], True, "Пермь", 200_000, 250_000, "remote"),
    ]
    for i, (spec, grade, skills, confirmed, fsp, city, smin, smax, fmt) in enumerate(bank):
        u = add_user(f"bank{i}@demo.ru", "candidate")
        c = add_candidate(
            u, full_name=f"Тестовый Кандидат {i + 1}", phone=f"+7 900 000-00-{10 + i:02d}", telegram=f"@bank_{i + 1}",
            city=city, experience_years={"junior": 1, "middle": 2, "senior": 5, "lead": 8}[grade], specialization_code=spec, claimed_grade=grade,
            grade=grade, grade_changed_at=iso(days(-rnd.randint(5, 80))), consents={"processing": True, "publication": True},
            salary_min=smin, salary_max=smax, work_format=fmt, fsp_id=f"FSP-2024-10{i:02d}" if fsp else None,
            fsp_linked_at=iso(days(-rnd.randint(10, 200))) if fsp else None, last_active_at=iso(days(-rnd.randint(0, 40))),
            skills=[skill(s, s in confirmed, round(rnd.uniform(0.6, 1.0), 2) if s in confirmed else None, "test" if s in confirmed else "profile") for s in skills],
        )
        c["_strength"] = round(rnd.uniform(0.45, 0.95), 2)
        if fsp:
            lvl = rnd.choice(["A2", "A3", "A4"])
            add_achievement(c, kind="result", title={"A2": "Призёр регионального этапа", "A3": "1 место на кубке региона", "A4": "КМС"}[lvl],
                            discipline="продуктовое программирование", level_code=lvl, place=rnd.randint(1, 3),
                            date="2025-0%d-1%d" % (rnd.randint(1, 9), rnd.randint(0, 9)), trust_level="source",
                            event={"name": "Соревнование ФСП", "ekp_number": "ЕКП 25-%04d" % rnd.randint(100, 999), "level": "региональный"})
    c1["_strength"] = 0.82
    # завершённый сеанс теста у демо-кандидата (история и «последний тест» в профиле)
    sess = {"id": nid("session"), "candidate_id": c1["id"], "specialization_code": "backend", "claimed_grade": "middle",
            "declared_skills": ["python", "sql", "fastapi", "postgresql", "kafka"], "status": "active", "current_block": 1, "current_level": "middle",
            "_items": [], "result": None, "started_at": iso(days(-20))}
    DB["sessions"][sess["id"]] = sess
    new_block(sess, "middle")
    for i, it in enumerate(sess["_items"]):
        it["answered"] = True; it["correct"] = i != 2; it["issued_at"] = time.time() - 10**6
    sess["current_block"] = 2; sess["current_level"] = "senior"
    new_block(sess, "senior")
    for i, it in enumerate(sess["_items"][4:]):
        it["answered"] = True; it["correct"] = i % 2 == 0; it["issued_at"] = time.time() - 10**6
    saved_skills = [dict(s) for s in c1["skills"]]
    finish_session(sess, c1)
    sess["finished_at"] = iso(days(-20))
    c1["skills"] = saved_skills
    c1["grade"], c1["grade_changed_at"], c1["grade_change_available_at"] = "middle", iso(days(-20)), iso(days(70))

    # --- вакансии работодателя
    v1 = add_vacancy(emp, title="Бэкенд-разработчик (Python)", description="Нужен разработчик на Python и FastAPI: сервисы витрин данных, PostgreSQL, очереди Kafka, Docker. Код-ревью, тесты pytest.",
                     specialization_code="backend", grade="middle", stack=["python", "fastapi", "postgresql", "kafka", "docker"],
                     salary_min=180_000, salary_max=250_000, work_format="hybrid", city="Москва")
    v2 = add_vacancy(emp, title="Инженер данных", description="Пайплайны на Airflow и Spark, витрины в ClickHouse, Python и SQL.",
                     specialization_code="data", grade="senior", stack=["python", "airflow", "spark", "clickhouse", "sql"],
                     salary_min=280_000, salary_max=360_000, work_format="remote", city="Москва")
    add_vacancy(emp2, title="Фронтенд-разработчик (Vue)", description="Интерфейсы для промышленной аналитики: Vue, TypeScript, графики, адаптивная вёрстка.",
                specialization_code="frontend", grade="middle", stack=["vue", "typescript", "css"], salary_min=150_000, salary_max=210_000,
                work_format="office", city="Санкт-Петербург")
    add_vacancy(emp2, title="Инженер по тестированию", description="Автотесты на pytest и Playwright, тестирование API в Postman.",
                specialization_code="qa", grade="junior", stack=["pytest", "playwright", "postman"], salary_min=90_000, salary_max=130_000,
                work_format="hybrid", city="Санкт-Петербург")

    # --- приглашения кандидату c1 (от двух работодателей)
    bank_cands = [c for c in DB["candidates"].values() if c["email"].startswith("bank")]
    add_invitation(emp, c1, "Ищем бэкенд-разработчика в команду витрин данных. Понравился подтверждённый стек и КМС.", 200_000, 240_000,
                   "Telegram", vacancy=v1, status="viewed", sent=days(-3), viewed=days(-2))
    add_invitation(emp2, c1, "Предлагаем позицию в отделе автоматизации. Релокация в Санкт-Петербург, помощь с переездом.", 190_000, 230_000,
                   "Почта", status="sent", sent=days(-1))
    add_invitation(emp, bank_cands[1], "Приглашаем на позицию Senior Python-разработчика.", 300_000, 350_000, "Телефон", vacancy=v1,
                   status="accepted", sent=days(-6), viewed=days(-5), responded=days(-4))
    add_invitation(emp, bank_cands[3], "Нужен Go-разработчик для сервиса интеграций.", 200_000, 240_000, "Telegram",
                   status="declined", sent=days(-8), viewed=days(-7), responded=days(-7))

    # --- отклики
    add_application(c1, v2, "Хочу расти в инженерию данных: есть опыт с SQL и Python, Airflow изучаю.", status="viewed")
    add_application(bank_cands[0], v1, "Пять лет на Django, готов перейти на FastAPI.", status="sent")
    add_application(bank_cands[8], v2, "Делаю пайплайны на Airflow два года.", status="accepted")

    # --- короткие задания
    t1 = add_short_task(emp, "Как бы вы ускорили медленный отчёт?", "Отчёт по продажам строится 40 секунд запросом к PostgreSQL с пятью JOIN. Опишите, с чего начнёте разбор и какие варианты ускорения рассмотрите.",
                        "backend", ["postgresql", "sql"])
    t2 = add_short_task(emp, "Очередь событий: потеря сообщений", "Сервис читает события из Kafka и иногда теряет их при перезапуске. Какие причины проверите первыми?",
                        "backend", ["kafka", "python"])
    add_short_answer(t1, bank_cands[0], "Снял бы EXPLAIN ANALYZE, посмотрел индексы по полям JOIN и фильтрам, затем материализованная витрина.", score=4)
    add_short_answer(t1, bank_cands[1], "План запроса, индексы, партиционирование по дате, кэш результата на 5 минут.")
    add_short_answer(t2, c1, "Проверю, когда делается commit смещения: до или после обработки; настройки enable.auto.commit; группу потребителей.", score=5)

    # --- потребность и подборка из двух версий
    need = add_need(emp, "Бэкенд-разработчик в команду витрин", "Нужен бэкенд на Python (FastAPI), PostgreSQL, Kafka, Docker. Команда делает витрины данных для розницы, высокая нагрузка на чтение.",
                    "backend", "middle", ["python", "fastapi", "postgresql", "kafka", "docker"], 180_000, 250_000, "hybrid", "Москва")
    sel = build_selection(need, {}, WEIGHTS)
    refine_selection(sel, {"specialization_code": "backend", "grades": ["middle", "senior"], "skills": ["python", "fastapi"], "fsp_only": True}, WEIGHTS)
    add_need(emp, "Инженер данных (Airflow, Spark)", "Нужен инженер данных: Airflow, Spark, ClickHouse, Python, SQL. Удалённо.",
             "data", "senior", ["python", "airflow", "spark", "clickhouse", "sql"], 280_000, 360_000, "remote", "Москва")


def add_vacancy(emp: dict, **kw) -> dict:
    v = {"id": nid("vacancy"), "employer_id": emp["id"], "company_name": emp["company_name"], "title": "", "description": "",
         "specialization_code": None, "grade": None, "stack": [], "salary_min": None, "salary_max": None, "work_format": None, "city": "",
         "status": "open", "created_at": iso(days(-random.randint(1, 20)))}
    v.update(kw)
    DB["vacancies"].append(v)
    return v


def add_invitation(emp: dict, cand: dict, message: str, smin: int, smax: int, contact: str, vacancy: dict | None = None, status: str = "sent",
                   sent=None, viewed=None, responded=None, selection_version_id=None) -> dict:
    inv = {"id": nid("invitation"), "employer_id": emp["id"], "candidate_id": cand["id"], "company_name": emp["company_name"], "message": message,
           "salary_min": smin, "salary_max": smax, "contact_method": contact, "vacancy_id": vacancy["id"] if vacancy else None,
           "selection_version_id": selection_version_id, "status": status, "sent_at": iso(sent or now()), "viewed_at": iso(viewed),
           "responded_at": iso(responded)}
    DB["invitations"].append(inv)
    return inv


def add_application(cand: dict, vac: dict, message: str, status: str = "sent") -> dict:
    a = {"id": nid("application"), "candidate_id": cand["id"], "vacancy_id": vac["id"], "message": message, "status": status,
         "created_at": iso(days(-random.randint(0, 5)))}
    DB["applications"].append(a)
    return a


def add_short_task(emp: dict, title: str, text: str, spec: str | None, techs: list[str]) -> dict:
    t = {"id": nid("short_task"), "employer_id": emp["id"], "company_name": emp["company_name"], "title": title, "text": text,
         "specialization_code": spec, "technologies": techs, "created_at": iso(days(-random.randint(0, 10)))}
    DB["short_tasks"].append(t)
    return t


def add_short_answer(task: dict, cand: dict, answer: str, score: int | None = None) -> dict:
    a = {"id": nid("short_answer"), "task_id": task["id"], "candidate_id": cand["id"], "answer": answer, "employer_score": score,
         "created_at": iso(days(-random.randint(0, 3)))}
    DB["short_answers"].append(a)
    return a


def add_need(emp: dict, title: str, text: str, spec, grade, stack, smin, smax, fmt, city) -> dict:
    n = {"id": nid("need"), "employer_id": emp["id"], "title": title, "text": text, "specialization_code": spec, "grade": grade, "stack": stack,
         "salary_min": smin, "salary_max": smax, "work_format": fmt, "city": city, "created_at": iso(now()), "selection_id": None}
    DB["needs"].append(n)
    return n


# ---------------------------------------------------------------- подбор
def candidate_card(c: dict, need: dict | None, weights: dict, employer: dict | None) -> dict | None:
    """Карточка кандидата по формуле docs/07 (упрощённо, но с теми же шестью слагаемыми)."""
    if not c["grade"] or not c["consents"]["publication"] or not c["visible_to_employers"]:
        return None
    skills = {s["skill"]: s for s in c["skills"]}
    stack_need = (need or {}).get("stack") or []
    if stack_need:
        got = sum(1.0 if skills[s]["confirmed_by_test"] else 0.3 for s in stack_need if s in skills)
        stack = got / len(stack_need)
        matched = [s for s in stack_need if s in skills]
        conf = [s for s in matched if skills[s]["confirmed_by_test"]]
        stack_text = f"совпало {len(matched)} из {len(stack_need)} технологий, подтверждено тестом {len(conf)}"
    else:
        stack, stack_text = 0.0, ""
    if need and need.get("grade"):
        d = abs(GRADE_ORDER.index(need["grade"]) - GRADE_ORDER.index(c["grade"]))
        grade = 1.0 if d == 0 else 0.5 if d == 1 else 0.0
    else:
        grade = 0.0
    strength = c.get("_strength", 0.7)
    ach = [a for a in DB["achievements"] if a["candidate_id"] == c["id"] and not a["hidden"] and a["status"] == "active" and a["trust_level"] in ("source", "document")]
    fsp = max([{"A1": 0.2, "A2": 0.4, "A3": 0.6, "A4": 0.8, "A5": 1.0}.get(a["level_code"], 0.2) for a in ach], default=0.0)
    active_days = (now() - datetime.fromisoformat(c["last_active_at"])).days
    activity = 1.0 if active_days <= 7 else 0.5 if active_days <= 30 else 0.1
    if need and need.get("salary_min") and c["salary_min"]:
        overlap = min(need["salary_max"] or 10**9, c["salary_max"] or 10**9) >= max(need["salary_min"], c["salary_min"])
        conditions = (0.7 if overlap else 0.2) + (0.3 if need.get("work_format") == c["work_format"] else 0.0)
    else:
        conditions = 0.0
    parts = {"stack": round(stack, 2), "grade": round(grade, 2), "strength": round(strength, 2), "fsp": round(fsp, 2),
             "activity": round(activity, 2), "conditions": round(min(conditions, 1.0), 2)}
    score = round(sum(parts[k] * weights.get(k, WEIGHTS[k]) for k in parts), 3)
    expl = []
    if stack_text:
        expl.append(stack_text)
    expl.append(f"грейд {GRADE_TITLE[c['grade']]} подтверждён тестом ({round(strength * 100)} %)")
    if ach:
        best = max(ach, key=lambda a: a["level_code"])
        expl.append(f"{best['title']}, {'подтверждено источником' if best['trust_level'] == 'source' else 'по документу'}")
    expl.append("активен на этой неделе" if active_days <= 7 else f"активность {active_days} дн. назад")
    unlocked = False
    if employer:
        unlocked = any(i["candidate_id"] == c["id"] and i["employer_id"] == employer["id"] and i["status"] == "accepted" for i in DB["invitations"]) or \
            any(a["candidate_id"] == c["id"] and vac_by_id(a["vacancy_id"])["employer_id"] == employer["id"] for a in DB["applications"])
    card = {
        "candidate_id": c["id"], "alias": c["alias"], "category": category(c["specialization_code"], c["grade"]), "score": score, "parts": parts,
        "explanation": "; ".join(expl),
        "skills": [{"skill": s["skill"], "name": s["name"], "confirmed_by_test": s["confirmed_by_test"]} for s in c["skills"]],
        "achievements_summary": (", ".join(a["title"] for a in ach[:2]) if c["privacy"]["achievements"] else "скрыто настройками приватности") if ach else "достижений ФСП нет",
        "fsp_linked": bool(c["fsp_id"]) and c["privacy"]["fsp_link"],
        "city": c["city"] if c["privacy"]["city"] else None,
        "salary_min": c["salary_min"] if c["privacy"]["salary"] else None,
        "salary_max": c["salary_max"] if c["privacy"]["salary"] else None,
        "work_format": c["work_format"], "contacts_unlocked": unlocked,
    }
    if unlocked:
        card["contacts"] = {"full_name": c["full_name"], "phone": c["phone"], "telegram": c["telegram"], "email": c["email"]}
    return card


def vac_by_id(vid: int) -> dict:
    for v in DB["vacancies"]:
        if v["id"] == vid:
            return v
    raise ApiError(404, "Вакансия не найдена")


def rank(need: dict | None, filters: dict, weights: dict, employer: dict | None) -> list[dict]:
    cards = []
    for c in DB["candidates"].values():
        card = candidate_card(c, need, weights, employer)
        if not card:
            continue
        if filters.get("specialization_code") and card["category"]["specialization_code"] != filters["specialization_code"]:
            continue
        if filters.get("grades") and card["category"]["grade"] not in filters["grades"]:
            continue
        if filters.get("grade") and card["category"]["grade"] != filters["grade"]:
            continue
        if filters.get("skills") and not all(any(s["skill"] == k for s in card["skills"]) for k in filters["skills"]):
            continue
        if filters.get("fsp_only") and not card["fsp_linked"]:
            continue
        if filters.get("city") and (card["city"] or "").lower() != filters["city"].lower():
            continue
        if filters.get("salary_max") and card["salary_min"] and card["salary_min"] > int(filters["salary_max"]):
            continue
        if filters.get("q"):
            q = filters["q"].lower()
            hay = " ".join([card["alias"], card["category"]["title"], card["explanation"]] + [s["name"] for s in card["skills"]]).lower()
            if q not in hay:
                continue
        cards.append(card)
    cards.sort(key=lambda k: -k["score"])
    return cards


def categories_of(cards: list[dict]) -> list[dict]:
    acc: dict[tuple, list] = {}
    for k in cards:
        key = (k["category"]["specialization_code"], k["category"]["grade"])
        acc.setdefault(key, []).append(k["score"])
    out = [{"specialization_code": s, "grade": g, "title": category(s, g)["title"], "count": len(v), "avg_score": round(sum(v) / len(v), 2)} for (s, g), v in acc.items()]
    out.sort(key=lambda x: (-x["count"], -x["avg_score"]))
    return out


def build_selection(need: dict, filters: dict, weights: dict) -> dict:
    emp = DB["employers"][need["employer_id"]]
    sel = {"id": nid("selection"), "need_id": need["id"], "employer_id": emp["id"], "versions": []}
    DB["selections"].append(sel)
    need["selection_id"] = sel["id"]
    base = {"specialization_code": need["specialization_code"], "grades": None, "skills": None, "fsp_only": False, "city": None, "salary_max": None}
    base.update({k: v for k, v in filters.items() if v not in (None, "", [])})
    add_version(sel, base, weights)
    return sel


def add_version(sel: dict, filters: dict, weights: dict) -> dict:
    need = next(n for n in DB["needs"] if n["id"] == sel["need_id"])
    emp = DB["employers"][sel["employer_id"]]
    f = {k: v for k, v in filters.items() if v not in (None, "", [], False)}
    # категории: основная и соседние по грейду, если грейд не задан фильтром
    cards = rank(need, f, weights, emp)
    if need.get("grade") and not f.get("grades"):
        i = GRADE_ORDER.index(need["grade"])
        near = {GRADE_ORDER[j] for j in (i - 1, i, i + 1) if 0 <= j < len(GRADE_ORDER)}
        cards = [c for c in cards if c["category"]["grade"] in near]
    ver = {"id": nid("version"), "version_no": len(sel["versions"]) + 1, "filters": f, "weights": weights, "created_at": iso(now()),
           "categories": categories_of(cards), "results": cards}
    sel["versions"].append(ver)
    return ver


def refine_selection(sel: dict, filters: dict, weights: dict) -> dict:
    """Фильтры — полный набор для новой версии (null/пусто = без ограничения)."""
    add_version(sel, filters, weights or sel["versions"][-1]["weights"])
    return sel


# ---------------------------------------------------------------- тест
LEVEL_TITLE = GRADE_TITLE


def gen_item(rnd: random.Random, level: str, techs: list[str], order: int) -> tuple[dict, dict]:
    """Экземпляр задания по шаблону со случайными параметрами. Возвращает (payload, ключ)."""
    kinds = []
    if "python" in techs or not techs:
        kinds.append("py_out")
    if "sql" in techs or "postgresql" in techs or "clickhouse" in techs or "mysql" in techs:
        kinds.append("sql_count")
    if "javascript" in techs or "typescript" in techs or "react" in techs or "vue" in techs:
        kinds.append("js_out")
    kinds += ["complexity", "bugline", "practice"]
    kind = kinds[order % len(kinds)]
    if kind == "py_out":
        a, b, n = rnd.randint(2, 9), rnd.randint(1, 5), rnd.randint(3, 6)
        name = rnd.choice(["total", "acc", "result"])
        code = f"{name} = {a}\nfor i in range({n}):\n    if i % 2 == 0:\n        {name} += i * {b}\nprint({name})"
        ans = a + sum(i * b for i in range(n) if i % 2 == 0)
        return ({"title": "Предсказать вывод кода", "competency": "чтение кода", "technologies": ["python"], "format": "exact",
                 "question": "Что напечатает программа?", "code": code, "language": "python", "options": None}, {"answer": str(ans)})
    if kind == "sql_count":
        rows = [(i, rnd.choice(["Москва", "Казань", "Пермь"]), rnd.randint(10, 90)) for i in range(1, rnd.randint(5, 8))]
        thr = rnd.choice([30, 50, 70])
        city = rnd.choice(["Москва", "Казань"])
        table = "id | city   | amount\n" + "\n".join(f"{i:<2} | {c:<6} | {a}" for i, c, a in rows)
        ans = sum(1 for _, c, a in rows if c == city and a > thr)
        return ({"title": "Запрос к данным", "competency": "SQL", "technologies": ["sql"], "format": "exact",
                 "question": f"Сколько строк вернёт запрос?\nSELECT * FROM orders WHERE city = '{city}' AND amount > {thr};",
                 "code": table, "language": "text", "options": None}, {"answer": str(ans)})
    if kind == "js_out":
        arr = [rnd.randint(1, 9) for _ in range(4)]
        k = rnd.randint(2, 4)
        code = f"const xs = {arr};\nconst r = xs.filter(x => x % {k} === 0).length;\nconsole.log(r);"
        return ({"title": "Предсказать вывод кода", "competency": "чтение кода", "technologies": ["javascript"], "format": "exact",
                 "question": "Что выведет console.log?", "code": code, "language": "javascript", "options": None},
                {"answer": str(sum(1 for x in arr if x % k == 0))})
    if kind == "complexity":
        opts = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)"]
        variant = rnd.choice([("бинарный поиск в отсортированном массиве", 1), ("один проход по массиву с подсчётом суммы", 2),
                              ("два вложенных цикла по n элементов", 4), ("сортировка слиянием", 3)])
        rnd.shuffle(opts)
        return ({"title": "Оценить сложность", "competency": "алгоритмы", "technologies": ["algorithms"], "format": "choice",
                 "question": f"Какова временная сложность: {variant[0]}?", "code": None, "language": None, "options": opts},
                {"answer": opts.index(["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)"][variant[1]])})
    if kind == "bugline":
        lines = ["def avg(xs):", "    total = 0", "    for x in xs:", "        total += x", "    return total / len(xs) + 1"]
        return ({"title": "Найти ошибку", "competency": "отладка", "technologies": ["python"], "format": "choice",
                 "question": "Функция должна возвращать среднее арифметическое. В какой строке ошибка?", "code": "\n".join(f"{i + 1}  {l}" for i, l in enumerate(lines)),
                 "language": "python", "options": [f"строка {i + 1}" for i in range(len(lines))]}, {"answer": 4})
    opts = ["писать тесты на граничные случаи", "отключить проверку типов, чтобы код проходил", "делать небольшие изменения с понятными сообщениями",
            "хранить пароли в репозитории для удобства", "проводить код-ревью перед слиянием"]
    idx = list(range(len(opts)))
    rnd.shuffle(idx)
    opts2 = [opts[i] for i in idx]
    correct = sorted(idx.index(i) for i in (0, 2, 4))
    return ({"title": "Выбор практик", "competency": "процессы разработки", "technologies": ["git"], "format": "multichoice",
             "question": "Какие практики помогают поддерживать качество кода в команде? Выберите все подходящие.", "code": None, "language": None,
             "options": opts2}, {"answer": correct})


def new_block(sess: dict, level: str) -> None:
    rnd = random.Random(sess["id"] * 100 + sess["current_block"])
    techs = [s for s in sess["declared_skills"] if s in SKILL_NAME]
    for k in range(TEST_CFG["block_size"]):
        payload, key = gen_item(rnd, level, techs, k + (sess["current_block"] - 1) * 2)
        sess["_items"].append({"id": nid("item"), "block_no": sess["current_block"], "order_no": k + 1, "level": level, "payload": payload,
                               "key": key, "answer": None, "correct": None, "issued_at": time.time(), "shown_at": None, "answered": False})


def current_item(sess: dict) -> dict | None:
    """Первое неотвеченное задание текущего блока; таймер стартует, когда оно становится текущим."""
    for it in sess["_items"]:
        if it["block_no"] == sess["current_block"] and not it["answered"]:
            if it.get("shown_at") is None:
                it["shown_at"] = time.time()
            return it
    return None


def session_view(sess: dict) -> dict:
    items = []
    cur = current_item(sess)
    for it in sess["_items"]:
        if it["answered"]:
            left = 0
        elif cur is not None and it["id"] == cur["id"]:
            left = max(0, TEST_CFG["item_seconds"] - int(time.time() - it["shown_at"]))
        else:
            left = TEST_CFG["item_seconds"]
        items.append({"id": it["id"], "block_no": it["block_no"], "order_no": it["order_no"], "level": it["level"], "payload": it["payload"],
                      "answered": it["answered"], "seconds_left": left})
    return {"id": sess["id"], "status": sess["status"], "specialization_code": sess["specialization_code"], "claimed_grade": sess["claimed_grade"],
            "current_block": sess["current_block"], "blocks_total": TEST_CFG["blocks"], "block_size": TEST_CFG["block_size"],
            "current_level": sess["current_level"], "items": items, "result": sess.get("result"), "started_at": sess["started_at"],
            "finished_at": sess.get("finished_at")}


def session_short(sess: dict) -> dict:
    r = sess.get("result") or {}
    return {"id": sess["id"], "status": sess["status"], "specialization_code": sess["specialization_code"], "claimed_grade": sess["claimed_grade"],
            "result_grade": r.get("result_grade"), "decision": r.get("decision"), "theta": r.get("theta"), "theta_sd": r.get("theta_sd"),
            "correct_total": r.get("correct_total"), "items_total": r.get("items_total"), "started_at": sess["started_at"],
            "finished_at": sess.get("finished_at"), "applied": sess.get("applied", False)}


def check(fmt: str, key, given) -> bool:
    try:
        if fmt == "exact":
            return str(key).strip().lower() == str(given).strip().lower()
        if fmt == "choice":
            return int(key) == int(given)
        if fmt == "multichoice":
            return sorted(int(x) for x in key) == sorted(int(x) for x in given)
    except (TypeError, ValueError):
        return False
    return False


def finish_session(sess: dict, cand: dict) -> None:
    items = sess["_items"]
    correct = sum(1 for i in items if i["correct"])
    share = correct / len(items)
    theta = round(-2.5 + 4.0 * share + 0.5 * GRADE_ORDER.index(sess["claimed_grade"]) - 0.75, 2)
    sd = round(0.35 + 0.3 * (1 - abs(share - 0.5) * 2), 2)
    thresholds = [("lead", 1.0), ("senior", 0.0), ("middle", -1.0), ("junior", -2.0)]
    result_grade = "junior"
    for g, t in thresholds:
        if theta >= t:
            result_grade = g
            break
    ci, ri = GRADE_ORDER.index(sess["claimed_grade"]), GRADE_ORDER.index(result_grade)
    if ri < ci:
        decision = "suggest_lower"
    elif ri > ci or (ci < 3 and theta - sd >= dict(thresholds)[GRADE_ORDER[ci + 1]]):
        decision = "suggest_higher"
    else:
        decision = "confirmed"
    by_tech: dict[str, list] = {}
    for i in items:
        for t in i["payload"]["technologies"]:
            by_tech.setdefault(t, [0, 0])
            by_tech[t][1] += 1
            by_tech[t][0] += 1 if i["correct"] else 0
    can_change = not cand["grade_change_available_at"] or datetime.fromisoformat(cand["grade_change_available_at"]) <= now()
    sess["status"] = "finished"
    sess["finished_at"] = iso(now())
    sess["result"] = {"theta": theta, "theta_sd": sd, "result_grade": result_grade, "decision": decision, "correct_total": correct,
                      "items_total": len(items), "by_technology": [{"skill": k, "name": SKILL_NAME.get(k, k), "correct": v[0], "total": v[1]} for k, v in by_tech.items()],
                      "can_apply": decision != "confirmed" and can_change, "grade_change_available_at": cand["grade_change_available_at"]}
    # первый тест или подтверждение: грейд и категория присваиваются сразу
    if not cand["grade"]:
        cand["grade"] = sess["claimed_grade"] if decision != "suggest_lower" else sess["claimed_grade"]
        cand["grade_changed_at"] = iso(now())
        cand["grade_change_available_at"] = iso(days(90))
    cand["specialization_code"] = sess["specialization_code"]
    cand["claimed_grade"] = sess["claimed_grade"]
    cand["last_test_id"] = sess["id"]
    cand["last_active_at"] = iso(now())
    # подтверждение технологий тестом
    for t, (c, n) in by_tech.items():
        if t in SKILL_NAME:
            existing = next((s for s in cand["skills"] if s["skill"] == t), None)
            conf = c / n >= 0.5
            if existing:
                existing.update({"confirmed_by_test": conf, "test_score": round(c / n, 2), "source": "test"})
            else:
                cand["skills"].append(skill(t, conf, round(c / n, 2), "test"))
    for s in sess["declared_skills"]:
        if s in SKILL_NAME and not any(x["skill"] == s for x in cand["skills"]):
            cand["skills"].append(skill(s))


# ---------------------------------------------------------------- представления
def candidate_view(c: dict) -> dict:
    last = DB["sessions"].get(c["last_test_id"]) if c["last_test_id"] else None
    out = {k: v for k, v in c.items() if not k.startswith("_") and k not in ("user_id", "last_test_id", "last_active_at", "email")}
    out["category"] = None
    if c["specialization_code"] and c["grade"]:
        cat = category(c["specialization_code"], c["grade"])
        out["category"] = {"specialization": cat["specialization_code"], "grade": cat["grade"], "title": cat["title"]}
    out["last_test"] = session_short(last) if last else None
    out["email"] = c["email"]
    return out


def achievement_view(a: dict) -> dict:
    return {k: v for k, v in a.items() if k != "candidate_id"}


def invitation_candidate_view(i: dict) -> dict:
    vac = next((v for v in DB["vacancies"] if v["id"] == i["vacancy_id"]), None)
    return {"id": i["id"], "status": i["status"], "company_name": i["company_name"], "message": i["message"], "salary_min": i["salary_min"],
            "salary_max": i["salary_max"], "contact_method": i["contact_method"], "vacancy": {"id": vac["id"], "title": vac["title"]} if vac else None,
            "sent_at": i["sent_at"], "viewed_at": i["viewed_at"], "responded_at": i["responded_at"]}


def invitation_employer_view(i: dict) -> dict:
    c = DB["candidates"][i["candidate_id"]]
    vac = next((v for v in DB["vacancies"] if v["id"] == i["vacancy_id"]), None)
    out = {"id": i["id"], "candidate": {"candidate_id": c["id"], "alias": c["alias"]}, "status": i["status"], "message": i["message"],
           "salary_min": i["salary_min"], "salary_max": i["salary_max"], "contact_method": i["contact_method"],
           "vacancy": {"id": vac["id"], "title": vac["title"]} if vac else None, "sent_at": i["sent_at"], "viewed_at": i["viewed_at"],
           "responded_at": i["responded_at"]}
    if i["status"] == "accepted":
        out["contacts"] = {"full_name": c["full_name"], "phone": c["phone"], "telegram": c["telegram"], "email": c["email"]}
    return out


def vacancy_short(v: dict) -> dict:
    return {k: v[k] for k in ("id", "title", "company_name", "specialization_code", "grade", "stack", "salary_min", "salary_max", "work_format", "city", "created_at", "status")}


def vacancy_full(v: dict) -> dict:
    out = vacancy_short(v)
    out["description"] = v["description"]
    return out


def application_candidate_view(a: dict) -> dict:
    v = vac_by_id(a["vacancy_id"])
    return {"id": a["id"], "vacancy": {"id": v["id"], "title": v["title"], "company_name": v["company_name"], "salary_min": v["salary_min"], "salary_max": v["salary_max"]},
            "status": a["status"], "message": a["message"], "created_at": a["created_at"]}


def short_task_candidate_view(t: dict, cand: dict) -> dict:
    ans = next((a for a in DB["short_answers"] if a["task_id"] == t["id"] and a["candidate_id"] == cand["id"]), None)
    return {"id": t["id"], "title": t["title"], "text": t["text"], "company_name": t["company_name"], "technologies": t["technologies"],
            "answered": ans is not None, "employer_score": ans["employer_score"] if ans else None, "answer": ans["answer"] if ans else None,
            "created_at": t["created_at"]}


def short_task_employer_view(t: dict) -> dict:
    answers = []
    for a in DB["short_answers"]:
        if a["task_id"] != t["id"]:
            continue
        c = DB["candidates"][a["candidate_id"]]
        answers.append({"id": a["id"], "candidate": {"candidate_id": c["id"], "alias": c["alias"]}, "answer": a["answer"],
                        "employer_score": a["employer_score"], "created_at": a["created_at"]})
    return {"id": t["id"], "title": t["title"], "text": t["text"], "specialization_code": t["specialization_code"], "technologies": t["technologies"],
            "created_at": t["created_at"], "answers": answers}


def selection_view(sel: dict) -> dict:
    return {"id": sel["id"], "need_id": sel["need_id"], "versions": sel["versions"]}


def need_view(n: dict) -> dict:
    return {k: v for k, v in n.items() if k != "employer_id"}


# ---------------------------------------------------------------- маршруты API
ROUTES: list[tuple[str, re.Pattern, callable]] = []


def route(method: str, pattern: str):
    def deco(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn))
        return fn
    return deco


class Ctx:
    def __init__(self, handler: "Handler", query: dict, body):
        self.h = handler
        self.query = query
        self.body = body if isinstance(body, dict) else {}
        self.raw_body = body
        self.user = None
        auth = handler.headers.get("Authorization", "")
        if auth.startswith("Bearer tok-"):
            try:
                self.user = DB["users"].get(int(auth.split("tok-")[1]))
            except ValueError:
                self.user = None

    def require(self, role: str | None = None) -> dict:
        if not self.user:
            raise ApiError(401, "Нужно войти в систему")
        if role and self.user["role"] != role:
            raise ApiError(403, "Этот раздел доступен только для роли «%s»" % ("кандидат" if role == "candidate" else "работодатель"))
        return self.user

    def candidate(self) -> dict:
        u = self.require("candidate")
        return next(c for c in DB["candidates"].values() if c["user_id"] == u["id"])

    def employer(self) -> dict:
        u = self.require("employer")
        return next(e for e in DB["employers"].values() if e["user_id"] == u["id"])

    def need(self, *fields):
        for f in fields:
            if self.body.get(f) in (None, "", []):
                raise ApiError(422, f"Не заполнено обязательное поле «{f}»")


def money_check(body: dict) -> None:
    smin, smax = body.get("salary_min"), body.get("salary_max")
    if smin in (None, "") or smax in (None, ""):
        raise ApiError(422, "Укажите зарплату «от» и «до» в рублях")
    if int(smin) > int(smax):
        raise ApiError(422, "Зарплата «от» не может быть больше зарплаты «до»")


@route("GET", "/catalog")
def catalog(ctx: Ctx, m):
    return {"specializations": [{"code": c, "name": n, "description": d, "has_bank": b} for c, n, d, b in SPECIALIZATIONS],
            "grades": [{"code": c, "title": t, "description": d} for c, t, d in GRADES],
            "work_formats": [{"code": c, "title": t} for c, t in WORK_FORMATS],
            "skills": [{"code": c, "name": n, "group": g} for c, n, g in SKILLS], "weights": WEIGHTS, "test": TEST_CFG, "demo_mode": True,
            "demo_accounts": [{"email": "candidate@demo.ru", "password": "demo", "title": "кандидат с тестом и историей ФСП"},
                              {"email": "newbie@demo.ru", "password": "demo", "title": "кандидат без теста и без истории ФСП"},
                              {"email": "employer@demo.ru", "password": "demo", "title": "работодатель с подборкой"}]}


@route("POST", "/auth/register")
def register(ctx: Ctx, m):
    ctx.need("email", "password", "role")
    email = ctx.body["email"].strip().lower()
    if "@" not in email:
        raise ApiError(422, "Введите корректный адрес электронной почты")
    if len(ctx.body["password"]) < 6:
        raise ApiError(422, "Пароль должен быть не короче 6 символов")
    if ctx.body["role"] not in ("candidate", "employer"):
        raise ApiError(422, "Роль должна быть «candidate» или «employer»")
    if any(u["email"] == email for u in DB["users"].values()):
        raise ApiError(409, "Пользователь с такой почтой уже зарегистрирован")
    u = add_user(email, ctx.body["role"], confirmed=False, password=ctx.body["password"])
    if u["role"] == "candidate":
        add_candidate(u)
    else:
        e = {"id": nid("employer"), "user_id": u["id"], "company_name": "", "description": "", "industry": "", "website": "", "city": "",
             "contact_person": "", "contact_email": email, "contact_phone": ""}
        DB["employers"][e["id"]] = e
    token = f"confirm-{u['id']}-{random.randint(1000, 9999)}"
    DB["confirm_tokens"][token] = u["id"]
    prefix = ctx.h.prefix
    return {"user_id": u["id"], "email": email, "role": u["role"], "confirm_required": True, "demo_confirm_url": f"{prefix}/#/confirm?token={token}"}


@route("GET", "/auth/confirm")
def confirm(ctx: Ctx, m):
    token = ctx.query.get("token")
    uid = DB["confirm_tokens"].get(token)
    if not uid:
        raise ApiError(400, "Ссылка подтверждения недействительна или уже использована")
    u = DB["users"][uid]
    u["email_confirmed"] = True
    del DB["confirm_tokens"][token]
    return {"ok": True, "access_token": f"tok-{u['id']}", "role": u["role"]}


@route("POST", "/auth/login")
def login(ctx: Ctx, m):
    ctx.need("email", "password")
    email = ctx.body["email"].strip().lower()
    u = next((u for u in DB["users"].values() if u["email"] == email), None)
    if not u or u["password"] != ctx.body["password"]:
        raise ApiError(401, "Неверная почта или пароль")
    if not u["email_confirmed"]:
        raise ApiError(403, "Почта не подтверждена. Перейдите по ссылке из письма")
    return {"access_token": f"tok-{u['id']}", "role": u["role"], "user_id": u["id"]}


@route("GET", "/auth/me")
def me(ctx: Ctx, m):
    u = ctx.require()
    return {"user_id": u["id"], "email": u["email"], "role": u["role"], "email_confirmed": u["email_confirmed"]}


# --- кандидат
@route("GET", "/candidates/me")
def cand_me(ctx: Ctx, m):
    return candidate_view(ctx.candidate())


@route("PUT", "/candidates/me")
def cand_update(ctx: Ctx, m):
    c = ctx.candidate()
    allowed = ("full_name", "phone", "telegram", "city", "experience_years", "roles", "soft_skills", "about", "salary_min", "salary_max",
               "work_format", "specialization_code", "claimed_grade")
    if ctx.body.get("salary_min") not in (None, "") and ctx.body.get("salary_max") not in (None, "") and int(ctx.body["salary_min"]) > int(ctx.body["salary_max"]):
        raise ApiError(422, "Зарплата «от» не может быть больше зарплаты «до»")
    for k in allowed:
        if k in ctx.body:
            c[k] = ctx.body[k]
    if "skills" in ctx.body:
        new = []
        for raw in ctx.body["skills"]:
            code = next((cd for cd, n, _ in SKILLS if raw.strip().lower() in (cd, n.lower())), None) or raw.strip()
            old = next((s for s in c["skills"] if s["skill"] == code), None)
            new.append(old or {"skill": code, "name": SKILL_NAME.get(code, raw.strip()), "source": "profile", "confirmed_by_test": False, "test_score": None})
        c["skills"] = new
    c["last_active_at"] = iso(now())
    return candidate_view(c)


@route("PUT", "/candidates/me/privacy")
def cand_privacy(ctx: Ctx, m):
    c = ctx.candidate()
    for k in ("achievements", "city", "salary", "fsp_link"):
        if k in ctx.body:
            c["privacy"][k] = bool(ctx.body[k])
    if "visible_to_employers" in ctx.body:
        c["visible_to_employers"] = bool(ctx.body["visible_to_employers"])
    return candidate_view(c)


@route("POST", "/candidates/me/consents")
def cand_consents(ctx: Ctx, m):
    c = ctx.candidate()
    for k in ("processing", "publication"):
        if k in ctx.body:
            c["consents"][k] = bool(ctx.body[k])
    return candidate_view(c)


@route("POST", "/candidates/me/resume")
def cand_resume(ctx: Ctx, m):
    c = ctx.candidate()
    ctype = ctx.h.headers.get("Content-Type", "")
    if "multipart/form-data" not in ctype:
        raise ApiError(422, "Ожидается файл PDF в поле «file» (multipart/form-data)")
    raw = ctx.raw_body if isinstance(ctx.raw_body, (bytes, bytearray)) else b""
    if b"%PDF" not in raw[:4096] and b"application/pdf" not in raw[:4096]:
        raise ApiError(422, "Файл не похож на PDF")
    parsed = {"full_name": "Смирнова Анна Олеговна", "phone": "+7 921 555-77-88", "telegram": "@anna_codes", "city": "Санкт-Петербург",
              "experience_years": 2, "skills": ["Python", "Django", "PostgreSQL", "Docker", "Git"], "roles": ["бэкенд-разработчик"],
              "soft_skills": ["работа в команде", "обучаемость"], "about": "Два года разрабатываю сервисы на Django, пишу тесты, веду документацию."}
    apply = ctx.query.get("apply") == "1"
    applied = False
    for k, v in parsed.items():
        if k == "skills":
            if apply or not c["skills"]:
                c["skills"] = [skill(next((cd for cd, n, _ in SKILLS if s.lower() in (cd, n.lower())), s)) for s in v]
                applied = True
            continue
        if apply or c.get(k) in (None, "", []):
            c[k] = v
            applied = True
    return {"parsed": parsed, "applied": applied}


@route("GET", "/candidates/me/profile.pdf")
def cand_pdf(ctx: Ctx, m):
    c = ctx.candidate()
    text = f"Karyera FSP - profile {c['alias']} ({c['full_name'] or 'bez imeni'})".encode("latin-1", "replace")
    content = b"BT /F1 14 Tf 40 760 Td (" + text.replace(b"(", b"").replace(b")", b"") + b") Tj ET"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    pdf += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return ("application/pdf", pdf, {"Content-Disposition": 'attachment; filename="profile.pdf"'})


@route("GET", "/candidates/me/achievements")
def cand_achievements(ctx: Ctx, m):
    c = ctx.candidate()
    return [achievement_view(a) for a in DB["achievements"] if a["candidate_id"] == c["id"]]


@route("POST", "/candidates/me/achievements")
def cand_add_achievement(ctx: Ctx, m):
    c = ctx.candidate()
    ctx.need("kind", "title", "discipline", "date")
    a = add_achievement(c, kind=ctx.body["kind"], title=ctx.body["title"], discipline=ctx.body["discipline"], date=ctx.body["date"],
                        place=ctx.body.get("place"), trust_level="claimed", level_code="A1")
    return achievement_view(a)


@route("PATCH", r"/candidates/me/achievements/(\d+)")
def cand_patch_achievement(ctx: Ctx, m):
    c = ctx.candidate()
    a = next((a for a in DB["achievements"] if a["id"] == int(m.group(1)) and a["candidate_id"] == c["id"]), None)
    if not a:
        raise ApiError(404, "Запись не найдена")
    a["hidden"] = bool(ctx.body.get("hidden"))
    return achievement_view(a)


@route("GET", "/fsp/link/start")
def fsp_start(ctx: Ctx, m):
    c = ctx.candidate()
    state = f"st-{c['id']}-{random.randint(1000, 9999)}"
    DB["fsp_states"][state] = c["id"]
    return {"redirect_url": f"{ctx.h.prefix}/api/v1/fsp/mock/login?state={state}"}


@route("GET", "/fsp/mock/login")
def fsp_mock_login(ctx: Ctx, m):
    state = ctx.query.get("state", "")
    if state not in DB["fsp_states"]:
        return ("text/html; charset=utf-8", "<p>Недействительный state</p>".encode(), {})
    html = f"""<!doctype html><html lang="ru"><meta charset="utf-8"><title>ФСП ID — демонстрационный вход</title>
    <body style="font-family:sans-serif;max-width:520px;margin:60px auto;padding:0 16px;color:#1C1D22">
    <h1 style="color:#310F53">ФСП ID <small style="font-weight:400;color:#8A83D1">демонстрационный издатель</small></h1>
    <p>Это заглушка внешнего входа. Выберите тестового участника, чтобы связать его историю с профилем.</p>
    <p><a style="display:block;padding:12px;border:1px solid #8A83D1;border-radius:10px;margin:8px 0;color:#310F53" href="{ctx.h.prefix}/api/v1/fsp/callback?code=p1&state={state}">Участник FSP-2023-104211 — КМС, 2 место Кубка Татарстана</a>
    <a style="display:block;padding:12px;border:1px solid #8A83D1;border-radius:10px;margin:8px 0;color:#310F53" href="{ctx.h.prefix}/api/v1/fsp/callback?code=p2&state={state}">Участник FSP-2025-200017 — II разряд, региональный этап</a>
    <a style="display:block;padding:12px;border:1px solid #ccc;border-radius:10px;margin:8px 0;color:#555" href="{ctx.h.prefix}/#/candidate/achievements">Отмена</a></p></body></html>"""
    return ("text/html; charset=utf-8", html.encode(), {})


@route("GET", "/fsp/callback")
def fsp_callback(ctx: Ctx, m):
    state = ctx.query.get("state", "")
    cid = DB["fsp_states"].pop(state, None)
    if not cid:
        raise ApiError(400, "Недействительный state")
    c = DB["candidates"][cid]
    code = ctx.query.get("code")
    c["fsp_id"] = "FSP-2023-104211" if code == "p1" else "FSP-2025-200017"
    c["fsp_linked_at"] = iso(now())
    if not any(a["candidate_id"] == cid and a["trust_level"] == "source" for a in DB["achievements"]):
        if code == "p1":
            add_achievement(c, kind="rank", title="Кандидат в мастера спорта", discipline="продуктовое программирование", level_code="A4",
                            date="2025-11-12", valid_until="2028-11-12", trust_level="source",
                            event={"name": "Чемпионат России по спортивному программированию", "ekp_number": "ЕКП 24-1187", "level": "всероссийский"})
        else:
            add_achievement(c, kind="rank", title="II спортивный разряд", discipline="алгоритмическое программирование", level_code="A2",
                            date="2025-03-20", valid_until="2027-03-20", trust_level="source",
                            event={"name": "Региональный этап чемпионата", "ekp_number": "ЕКП 25-0330", "level": "региональный"})
    return ("redirect", f"{ctx.h.prefix}/#/candidate/profile?fsp=linked", {})


@route("POST", "/fsp/unlink")
def fsp_unlink(ctx: Ctx, m):
    c = ctx.candidate()
    c["fsp_id"] = None
    c["fsp_linked_at"] = None
    for a in DB["achievements"]:
        if a["candidate_id"] == c["id"] and a["trust_level"] == "source":
            a["status"] = "revoked"
    return candidate_view(c)


@route("GET", "/tests/options")
def test_options(ctx: Ctx, m):
    c = ctx.candidate()
    avail = c["grade_change_available_at"]
    can = not avail or datetime.fromisoformat(avail) <= now()
    return {"specializations": [{"code": s, "name": n, "description": d, "has_bank": b} for s, n, d, b in SPECIALIZATIONS],
            "grades": [{"code": s, "title": t, "description": d} for s, t, d in GRADES], "can_change_grade": can, "grade_change_available_at": avail,
            "current_grade": c["grade"], "current_specialization": c["specialization_code"]}


@route("POST", "/tests/sessions")
def test_start(ctx: Ctx, m):
    c = ctx.candidate()
    ctx.need("specialization_code", "claimed_grade")
    if ctx.body["specialization_code"] not in SPEC_TITLE or ctx.body["claimed_grade"] not in GRADE_TITLE:
        raise ApiError(422, "Неизвестная специализация или грейд")
    active = next((s for s in DB["sessions"].values() if s["candidate_id"] == c["id"] and s["status"] == "active"), None)
    if active:
        return session_view(active)
    sess = {"id": nid("session"), "candidate_id": c["id"], "specialization_code": ctx.body["specialization_code"], "claimed_grade": ctx.body["claimed_grade"],
            "declared_skills": [s.lower() for s in ctx.body.get("declared_skills") or []], "status": "active", "current_block": 1,
            "current_level": ctx.body["claimed_grade"], "_items": [], "result": None, "started_at": iso(now())}
    DB["sessions"][sess["id"]] = sess
    new_block(sess, sess["current_level"])
    return session_view(sess)


def get_session(ctx: Ctx, sid: str) -> tuple[dict, dict]:
    c = ctx.candidate()
    sess = DB["sessions"].get(int(sid))
    if not sess or sess["candidate_id"] != c["id"]:
        raise ApiError(404, "Сеанс теста не найден")
    return sess, c


@route("GET", r"/tests/sessions/(\d+)")
def test_get(ctx: Ctx, m):
    sess, _ = get_session(ctx, m.group(1))
    return session_view(sess)


@route("POST", r"/tests/sessions/(\d+)/answer")
def test_answer(ctx: Ctx, m):
    sess, _ = get_session(ctx, m.group(1))
    if sess["status"] != "active":
        raise ApiError(409, "Сеанс уже завершён")
    item = next((i for i in sess["_items"] if i["id"] == ctx.body.get("item_id")), None)
    if not item:
        raise ApiError(404, "Задание не найдено")
    if item["answered"]:
        raise ApiError(409, "На это задание уже дан ответ")
    current_item(sess)   # фиксирует момент показа, если ответ пришёл до запроса сеанса
    expired = time.time() - (item.get("shown_at") or time.time()) > TEST_CFG["item_seconds"] + 5
    item["answer"] = ctx.body.get("answer")
    item["correct"] = (not expired) and check(item["payload"]["format"], item["key"]["answer"], item["answer"])
    item["answered"] = True
    block_done = all(i["answered"] for i in sess["_items"] if i["block_no"] == sess["current_block"])
    return {"item_id": item["id"], "accepted": True, "block_done": block_done, "session_status": sess["status"]}


@route("POST", r"/tests/sessions/(\d+)/next")
def test_next(ctx: Ctx, m):
    sess, c = get_session(ctx, m.group(1))
    if sess["status"] != "active":
        return session_view(sess)
    block_items = [i for i in sess["_items"] if i["block_no"] == sess["current_block"]]
    if not all(i["answered"] for i in block_items):
        raise ApiError(409, "Сначала ответьте на все задания блока")
    if sess["current_block"] >= TEST_CFG["blocks"]:
        finish_session(sess, c)
        return session_view(sess)
    share = sum(1 for i in block_items if i["correct"]) / len(block_items)
    li = GRADE_ORDER.index(sess["current_level"])
    li = min(li + 1, 3) if share > 0.5 else max(li - 1, 0)
    sess["current_level"] = GRADE_ORDER[li]
    sess["current_block"] += 1
    new_block(sess, sess["current_level"])
    return session_view(sess)


@route("GET", "/tests/sessions")
def test_history(ctx: Ctx, m):
    c = ctx.candidate()
    return [session_short(s) for s in sorted(DB["sessions"].values(), key=lambda s: -s["id"]) if s["candidate_id"] == c["id"]]


@route("POST", r"/tests/sessions/(\d+)/apply")
def test_apply(ctx: Ctx, m):
    sess, c = get_session(ctx, m.group(1))
    r = sess.get("result")
    if not r or not r["can_apply"]:
        raise ApiError(409, "Смена грейда по этому тесту недоступна")
    c["grade"] = r["result_grade"] if r["decision"] == "suggest_lower" else GRADE_ORDER[min(GRADE_ORDER.index(c["grade"]) + 1, 3)]
    c["grade_changed_at"] = iso(now())
    c["grade_change_available_at"] = iso(days(90))
    r["can_apply"] = False
    r["grade_change_available_at"] = c["grade_change_available_at"]
    sess["applied"] = True
    return candidate_view(c)


@route("GET", "/candidates/me/invitations")
def cand_invitations(ctx: Ctx, m):
    c = ctx.candidate()
    return [invitation_candidate_view(i) for i in sorted(DB["invitations"], key=lambda i: i["sent_at"], reverse=True) if i["candidate_id"] == c["id"]]


@route("POST", r"/invitations/(\d+)/view")
def inv_view(ctx: Ctx, m):
    c = ctx.candidate()
    i = next((i for i in DB["invitations"] if i["id"] == int(m.group(1)) and i["candidate_id"] == c["id"]), None)
    if not i:
        raise ApiError(404, "Приглашение не найдено")
    if i["status"] == "sent":
        i["status"] = "viewed"
        i["viewed_at"] = iso(now())
    return invitation_candidate_view(i)


@route("POST", r"/invitations/(\d+)/respond")
def inv_respond(ctx: Ctx, m):
    c = ctx.candidate()
    i = next((i for i in DB["invitations"] if i["id"] == int(m.group(1)) and i["candidate_id"] == c["id"]), None)
    if not i:
        raise ApiError(404, "Приглашение не найдено")
    if i["status"] in ("accepted", "declined"):
        raise ApiError(409, "Ответ на это приглашение уже дан")
    d = ctx.body.get("decision")
    if d not in ("accept", "decline"):
        raise ApiError(422, "decision должен быть accept или decline")
    i["status"] = "accepted" if d == "accept" else "declined"
    i["responded_at"] = iso(now())
    if not i["viewed_at"]:
        i["viewed_at"] = i["responded_at"]
    return invitation_candidate_view(i)


@route("GET", "/vacancies")
def vacancies(ctx: Ctx, m):
    out = [v for v in DB["vacancies"] if v["status"] == "open"]
    q = ctx.query
    if q.get("specialization"):
        out = [v for v in out if v["specialization_code"] == q["specialization"]]
    if q.get("grade"):
        out = [v for v in out if v["grade"] == q["grade"]]
    if q.get("skill"):
        out = [v for v in out if q["skill"] in v["stack"]]
    if q.get("q"):
        s = q["q"].lower()
        out = [v for v in out if s in (v["title"] + " " + v["company_name"] + " " + v["description"]).lower()]
    return [vacancy_short(v) for v in sorted(out, key=lambda v: v["created_at"], reverse=True)]


@route("GET", r"/vacancies/(\d+)")
def vacancy(ctx: Ctx, m):
    return vacancy_full(vac_by_id(int(m.group(1))))


@route("POST", r"/vacancies/(\d+)/apply")
def vacancy_apply(ctx: Ctx, m):
    c = ctx.candidate()
    v = vac_by_id(int(m.group(1)))
    if any(a["candidate_id"] == c["id"] and a["vacancy_id"] == v["id"] for a in DB["applications"]):
        raise ApiError(409, "Вы уже откликнулись на эту вакансию")
    a = add_application(c, v, ctx.body.get("message", ""))
    a["created_at"] = iso(now())
    c["last_active_at"] = iso(now())
    return application_candidate_view(a)


@route("GET", "/candidates/me/applications")
def cand_applications(ctx: Ctx, m):
    c = ctx.candidate()
    return [application_candidate_view(a) for a in DB["applications"] if a["candidate_id"] == c["id"]]


@route("GET", "/candidates/me/short-tasks")
def cand_short_tasks(ctx: Ctx, m):
    c = ctx.candidate()
    return [short_task_candidate_view(t, c) for t in DB["short_tasks"] if not t["specialization_code"] or t["specialization_code"] == c["specialization_code"] or c["specialization_code"] is None]


@route("POST", r"/short-tasks/(\d+)/answer")
def short_task_answer(ctx: Ctx, m):
    c = ctx.candidate()
    t = next((t for t in DB["short_tasks"] if t["id"] == int(m.group(1))), None)
    if not t:
        raise ApiError(404, "Задание не найдено")
    if not (ctx.body.get("answer") or "").strip():
        raise ApiError(422, "Ответ не может быть пустым")
    if any(a["task_id"] == t["id"] and a["candidate_id"] == c["id"] for a in DB["short_answers"]):
        raise ApiError(409, "Ответ на это задание уже отправлен")
    a = add_short_answer(t, c, ctx.body["answer"].strip())
    a["created_at"] = iso(now())
    c["last_active_at"] = iso(now())
    return short_task_candidate_view(t, c)


# --- работодатель
@route("GET", "/employers/me")
def emp_me(ctx: Ctx, m):
    e = ctx.employer()
    return {k: v for k, v in e.items() if k != "user_id"}


@route("PUT", "/employers/me")
def emp_update(ctx: Ctx, m):
    e = ctx.employer()
    for k in ("company_name", "description", "industry", "website", "city", "contact_person", "contact_email", "contact_phone"):
        if k in ctx.body:
            e[k] = ctx.body[k]
    if not e["company_name"].strip():
        raise ApiError(422, "Укажите название компании")
    for coll in (DB["vacancies"], DB["invitations"], DB["short_tasks"]):
        for x in coll:
            if x["employer_id"] == e["id"]:
                x["company_name"] = e["company_name"]
    return {k: v for k, v in e.items() if k != "user_id"}


@route("POST", "/needs")
def need_create(ctx: Ctx, m):
    e = ctx.employer()
    ctx.need("title", "text")
    money_check(ctx.body)
    extracted_stack = extract_stack(ctx.body["text"])
    stack = ctx.body.get("stack") or extracted_stack
    spec = ctx.body.get("specialization_code") or ("backend" if {"python", "fastapi", "django", "go", "java"} & set(extracted_stack) else
                                                   "frontend" if {"react", "vue", "typescript", "css"} & set(extracted_stack) else
                                                   "data" if {"pandas", "pytorch", "spark", "airflow"} & set(extracted_stack) else None)
    grade = ctx.body.get("grade") or ("senior" if "senior" in ctx.body["text"].lower() or "опытн" in ctx.body["text"].lower() else "middle")
    n = add_need(e, ctx.body["title"], ctx.body["text"], spec, grade, stack, int(ctx.body["salary_min"]), int(ctx.body["salary_max"]),
                 ctx.body.get("work_format"), ctx.body.get("city"))
    return {"need": need_view(n), "extracted": {"specialization_code": spec, "grade": grade, "stack": extracted_stack}}


@route("GET", "/needs")
def needs_list(ctx: Ctx, m):
    e = ctx.employer()
    return [need_view(n) for n in DB["needs"] if n["employer_id"] == e["id"]]


@route("POST", r"/needs/(\d+)/selection")
def need_selection(ctx: Ctx, m):
    e = ctx.employer()
    n = next((n for n in DB["needs"] if n["id"] == int(m.group(1)) and n["employer_id"] == e["id"]), None)
    if not n:
        raise ApiError(404, "Потребность не найдена")
    existing = next((s for s in DB["selections"] if s["need_id"] == n["id"]), None)
    if existing:
        return selection_view(existing)
    weights = {**WEIGHTS, **(ctx.body.get("weights") or {})}
    return selection_view(build_selection(n, {}, weights))


@route("POST", r"/selections/(\d+)/refine")
def selection_refine(ctx: Ctx, m):
    e = ctx.employer()
    s = next((s for s in DB["selections"] if s["id"] == int(m.group(1)) and s["employer_id"] == e["id"]), None)
    if not s:
        raise ApiError(404, "Подборка не найдена")
    filters = ctx.body.get("filters") or {}
    weights = ctx.body.get("weights")
    return selection_view(refine_selection(s, filters, {**WEIGHTS, **weights} if weights else None))


@route("GET", r"/selections/(\d+)")
def selection_get(ctx: Ctx, m):
    e = ctx.employer()
    s = next((s for s in DB["selections"] if s["id"] == int(m.group(1)) and s["employer_id"] == e["id"]), None)
    if not s:
        raise ApiError(404, "Подборка не найдена")
    return selection_view(s)


@route("GET", "/selections")
def selections_list(ctx: Ctx, m):
    e = ctx.employer()
    return [selection_view(s) for s in DB["selections"] if s["employer_id"] == e["id"]]


@route("GET", "/candidates/search")
def cand_search(ctx: Ctx, m):
    e = ctx.employer()
    q = ctx.query
    filters = {"specialization_code": q.get("specialization_code"), "grade": q.get("grade"),
               "skills": [s for s in (q.get("skills") or "").split(",") if s], "fsp_only": q.get("fsp_only") in ("1", "true"), "q": q.get("q")}
    return rank(None, filters, WEIGHTS, e)


@route("GET", r"/candidates/(\d+)/card")
def cand_card(ctx: Ctx, m):
    e = ctx.employer()
    c = DB["candidates"].get(int(m.group(1)))
    card = candidate_card(c, None, WEIGHTS, e) if c else None
    if not card:
        raise ApiError(404, "Кандидат не найден или скрыт настройками")
    return card


@route("POST", "/invitations")
def inv_create(ctx: Ctx, m):
    e = ctx.employer()
    ctx.need("candidate_id", "message", "contact_method")
    money_check(ctx.body)
    c = DB["candidates"].get(int(ctx.body["candidate_id"]))
    if not c:
        raise ApiError(404, "Кандидат не найден")
    vac = None
    if ctx.body.get("vacancy_id"):
        vac = vac_by_id(int(ctx.body["vacancy_id"]))
        if vac["employer_id"] != e["id"]:
            raise ApiError(403, "Это не ваша вакансия")
    if any(i["candidate_id"] == c["id"] and i["employer_id"] == e["id"] and i["status"] in ("sent", "viewed") for i in DB["invitations"]):
        raise ApiError(409, "У этого кандидата уже есть ваше приглашение без ответа")
    i = add_invitation(e, c, ctx.body["message"], int(ctx.body["salary_min"]), int(ctx.body["salary_max"]), ctx.body["contact_method"], vacancy=vac,
                       selection_version_id=ctx.body.get("selection_version_id"))
    return invitation_employer_view(i)


@route("GET", "/employers/me/invitations")
def emp_invitations(ctx: Ctx, m):
    e = ctx.employer()
    return [invitation_employer_view(i) for i in sorted(DB["invitations"], key=lambda i: i["sent_at"], reverse=True) if i["employer_id"] == e["id"]]


@route("POST", "/vacancies")
def vacancy_create(ctx: Ctx, m):
    e = ctx.employer()
    ctx.need("title", "description")
    money_check(ctx.body)
    v = add_vacancy(e, title=ctx.body["title"], description=ctx.body["description"], specialization_code=ctx.body.get("specialization_code"),
                    grade=ctx.body.get("grade"), stack=ctx.body.get("stack") or extract_stack(ctx.body["description"]),
                    salary_min=int(ctx.body["salary_min"]), salary_max=int(ctx.body["salary_max"]), work_format=ctx.body.get("work_format"),
                    city=ctx.body.get("city") or "")
    v["created_at"] = iso(now())
    return vacancy_full(v)


@route("PUT", r"/vacancies/(\d+)")
def vacancy_update(ctx: Ctx, m):
    e = ctx.employer()
    v = vac_by_id(int(m.group(1)))
    if v["employer_id"] != e["id"]:
        raise ApiError(403, "Это не ваша вакансия")
    body = {**v, **{k: ctx.body[k] for k in ("title", "description", "specialization_code", "grade", "stack", "salary_min", "salary_max", "work_format", "city", "status") if k in ctx.body}}
    money_check(body)
    v.update(body)
    v["salary_min"], v["salary_max"] = int(v["salary_min"]), int(v["salary_max"])
    return vacancy_full(v)


@route("GET", "/employers/me/vacancies")
def emp_vacancies(ctx: Ctx, m):
    e = ctx.employer()
    out = []
    for v in DB["vacancies"]:
        if v["employer_id"] == e["id"]:
            d = vacancy_full(v)
            d["applications_count"] = sum(1 for a in DB["applications"] if a["vacancy_id"] == v["id"])
            out.append(d)
    return out


@route("GET", r"/vacancies/(\d+)/applications")
def vacancy_applications(ctx: Ctx, m):
    e = ctx.employer()
    v = vac_by_id(int(m.group(1)))
    if v["employer_id"] != e["id"]:
        raise ApiError(403, "Это не ваша вакансия")
    out = []
    for a in DB["applications"]:
        if a["vacancy_id"] == v["id"]:
            c = DB["candidates"][a["candidate_id"]]
            card = candidate_card(c, None, WEIGHTS, e) or {"candidate_id": c["id"], "alias": c["alias"], "category": None, "skills": [], "contacts_unlocked": True,
                                                            "contacts": {"full_name": c["full_name"], "phone": c["phone"], "telegram": c["telegram"], "email": c["email"]}}
            out.append({"id": a["id"], "candidate": card, "message": a["message"], "status": a["status"], "created_at": a["created_at"]})
    return out


@route("PATCH", r"/applications/(\d+)")
def application_patch(ctx: Ctx, m):
    e = ctx.employer()
    a = next((a for a in DB["applications"] if a["id"] == int(m.group(1))), None)
    if not a or vac_by_id(a["vacancy_id"])["employer_id"] != e["id"]:
        raise ApiError(404, "Отклик не найден")
    st = ctx.body.get("status")
    if st not in ("viewed", "accepted", "declined"):
        raise ApiError(422, "Недопустимый статус")
    a["status"] = st
    return {"id": a["id"], "status": a["status"]}


@route("POST", "/short-tasks")
def short_task_create(ctx: Ctx, m):
    e = ctx.employer()
    ctx.need("title", "text")
    t = add_short_task(e, ctx.body["title"], ctx.body["text"], ctx.body.get("specialization_code"), ctx.body.get("technologies") or extract_stack(ctx.body["text"]))
    t["created_at"] = iso(now())
    return short_task_employer_view(t)


@route("GET", "/employers/me/short-tasks")
def emp_short_tasks(ctx: Ctx, m):
    e = ctx.employer()
    return [short_task_employer_view(t) for t in DB["short_tasks"] if t["employer_id"] == e["id"]]


@route("PATCH", r"/short-task-answers/(\d+)")
def short_answer_patch(ctx: Ctx, m):
    e = ctx.employer()
    a = next((a for a in DB["short_answers"] if a["id"] == int(m.group(1))), None)
    if not a:
        raise ApiError(404, "Ответ не найден")
    score = ctx.body.get("employer_score")
    if not isinstance(score, int) or not 1 <= score <= 5:
        raise ApiError(422, "Оценка — целое число от 1 до 5")
    a["employer_score"] = score
    return {"id": a["id"], "employer_score": score}


@route("GET", r"/vacancies/(\d+)/test-preview")
def vacancy_test_preview(ctx: Ctx, m):
    e = ctx.employer()
    v = vac_by_id(int(m.group(1)))
    if v["employer_id"] != e["id"]:
        raise ApiError(403, "Это не ваша вакансия")
    techs = v["stack"] or extract_stack(v["description"])
    rnd = random.Random(v["id"])
    items = [gen_item(rnd, v["grade"] or "middle", techs, k)[0] for k in range(4)]
    return {"technologies": techs, "items": items}


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "FspMock/0.1"
    prefix = ""

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    def _send_json(self, status: int, data) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        target = (ROOT / path.lstrip("/")).resolve()
        if ROOT not in target.parents and target != ROOT:
            self._send_json(403, {"detail": "Доступ запрещён"})
            return
        if target.is_dir() or not target.exists():
            # неизвестный путь — отдаём index.html (приложение само разберёт hash)
            target = ROOT / "index.html"
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("text/javascript", "application/json"):
            ctype += "; charset=utf-8"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _handle(self, method: str) -> None:
        parts = urlsplit(self.path)
        path = parts.path
        self.prefix = ""
        if path == "/fsp" or path.startswith("/fsp/"):
            self.prefix = "/fsp"
            path = path[4:] or "/"
        if not path.startswith("/api/v1/"):
            if method == "GET":
                self._serve_static(path)
            else:
                self._send_json(405, {"detail": "Метод не поддерживается"})
            return
        api_path = path[len("/api/v1"):]
        query = {k: v[-1] for k, v in parse_qs(parts.query).items()}
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        body = raw
        if raw and "application/json" in self.headers.get("Content-Type", ""):
            try:
                body = json.loads(raw.decode())
            except json.JSONDecodeError:
                self._send_json(400, {"detail": "Некорректный JSON"})
                return
        # маленькая задержка, чтобы было видно состояния загрузки
        time.sleep(0.15)
        for m, pattern, fn in ROUTES:
            match = pattern.match(api_path)
            if match and m == method:
                try:
                    result = fn(Ctx(self, query, body), match)
                except ApiError as e:
                    self._send_json(e.status, {"detail": e.detail})
                    return
                except Exception as e:  # noqa: BLE001 — в mock показываем ошибку как есть
                    import traceback
                    traceback.print_exc()
                    self._send_json(500, {"detail": f"Внутренняя ошибка mock-сервера: {e}"})
                    return
                if isinstance(result, tuple):
                    ctype, data, headers = result
                    if ctype == "redirect":
                        self.send_response(302)
                        self.send_header("Location", data)
                        self.end_headers()
                        return
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    for k, v in headers.items():
                        self.send_header(k, v)
                    self.end_headers()
                    self.wfile.write(data)
                    return
                self._send_json(200, result)
                return
        if any(p.match(api_path) for _, p, _ in ROUTES):
            self._send_json(405, {"detail": "Метод не поддерживается для этого адреса"})
        else:
            self._send_json(404, {"detail": f"Адрес {api_path} не найден"})

    def do_GET(self):
        self._handle("GET")

    def do_HEAD(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_PATCH(self):
        self._handle("PATCH")

    def do_DELETE(self):
        self._handle("DELETE")


def main() -> None:
    seed()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Mock-сервер «Карьера ФСП»: http://localhost:{PORT}/  (API: /api/v1, с префиксом: http://localhost:{PORT}/fsp/)")
    print("Учётные записи: candidate@demo.ru, newbie@demo.ru, employer@demo.ru — пароль demo; pending@demo.ru — почта не подтверждена")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
