"""Синтетический мир: кандидаты с истинными навыками, работодатели, потребности, имитация реестра ФСП.

Используется сидером (демонстрационные данные) и скриптами валидации (истина известна, наблюдаемые данные — производные).
Все имена выдуманы; совпадения с реальными людьми случайны.
"""
from __future__ import annotations
import json
import os
import random
from dataclasses import dataclass, field

GRADES = ["junior", "middle", "senior", "lead"]
GRADE_THETA = {"junior": -1.6, "middle": -0.5, "senior": 0.6, "lead": 1.5}      # центры распределений умения
SPEC_STACK = {
    "backend": ["python", "sql", "postgresql", "docker", "git", "rest", "fastapi", "django", "redis", "kafka", "linux", "async", "go", "java", "http"],
    "frontend": ["javascript", "typescript", "html", "css", "react", "vue", "git", "webpack", "rest", "http", "nodejs"],
    "fullstack": ["python", "javascript", "typescript", "react", "sql", "postgresql", "docker", "git", "rest", "fastapi", "nodejs", "html", "css"],
    "mobile": ["kotlin", "android", "swift", "ios", "flutter", "git", "rest", "sql", "http"],
    "data": ["python", "sql", "pandas", "numpy", "statistics", "ml", "scikit_learn", "pytorch", "spark", "airflow", "clickhouse", "git", "powerbi"],
    "devops": ["linux", "docker", "kubernetes", "ci_cd", "terraform", "ansible", "prometheus", "grafana", "bash", "nginx", "networking", "git", "python"],
    "qa": ["testing_theory", "pytest", "selenium", "playwright", "postman", "sql", "python", "git", "rest", "jmeter"],
    "analytics": ["sql", "system_analysis", "uml", "bpmn", "product_analytics", "excel", "powerbi", "python", "statistics", "agile"],
    "security": ["security_basics", "cryptography", "networking", "linux", "python", "docker", "bash", "sql"],
}
SPEC_WEIGHTS = {"backend": 22, "frontend": 16, "fullstack": 10, "mobile": 7, "data": 14, "devops": 8, "qa": 11, "analytics": 7, "security": 5}
GRADE_WEIGHTS = {"junior": 35, "middle": 38, "senior": 20, "lead": 7}
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург", "Нижний Новгород", "Томск", "Самара", "Пермь", "Воронеж"]
FIRST = ["Алексей", "Мария", "Иван", "Дарья", "Никита", "Анна", "Егор", "Полина", "Артём", "Ксения", "Дмитрий", "Елена", "Михаил", "Ольга",
         "Кирилл", "Светлана", "Тимур", "Алина", "Роман", "Юлия", "Глеб", "Вероника", "Павел", "Татьяна", "Сергей", "Наталья"]
LAST_M = ["Смирнов", "Иванов", "Кузнецов", "Попов", "Соколов", "Лебедев", "Козлов", "Новиков", "Морозов", "Волков", "Фёдоров", "Орлов",
          "Макаров", "Зайцев", "Беляев", "Громов", "Тихонов", "Крылов", "Жуков", "Белов"]
FEMALE = {"Мария", "Дарья", "Анна", "Полина", "Ксения", "Елена", "Ольга", "Светлана", "Алина", "Юлия", "Вероника", "Татьяна", "Наталья"}
ROLES = ["разработчик", "ведущий разработчик", "тимлид", "архитектор", "инженер данных", "аналитик", "тестировщик", "DevOps-инженер", "стажёр"]
SOFT = ["работа в команде", "наставничество", "коммуникация с заказчиком", "самоорганизация", "документирование", "код-ревью", "планирование", "презентация результатов"]
COMPANIES = [
    ("Нейрософт", "Разработка медицинских информационных систем", "медицина", "Москва"),
    ("Балтик Дата", "Платформа аналитики для ритейла", "ритейл", "Санкт-Петербург"),
    ("ЛогиТех", "Логистические сервисы и маршрутизация", "логистика", "Казань"),
    ("СтройЦифра", "Цифровизация строительного контроля", "строительство", "Екатеринбург"),
    ("ФинКод", "Финансовые сервисы и платежи", "финансы", "Москва"),
    ("Эдуланд", "Образовательная платформа для школ", "образование", "Новосибирск"),
]
DISCIPLINES = ["product", "algorithmic", "security", "robotics", "uav"]
DISC_TITLE = {"product": "продуктовое программирование", "algorithmic": "алгоритмическое программирование", "security": "программирование систем ИБ",
              "robotics": "программирование робототехники", "uav": "программирование БАС"}
LEVEL_PLACES = {   # уровень события → место → код уровня достижения и разряд (docs/04, раздел 3)
    "russia_championship": [(1, "A5", "ms"), (4, "A4", "kms"), (9, "A3", "r1"), (20, "A1", None)],
    "russia_cup": [(3, "A4", "kms"), (8, "A3", "r1"), (20, "A1", None)],
    "russia_junior": [(1, "A4", "kms"), (8, "A3", "r1"), (20, "A1", None)],
    "district": [(2, "A3", "r1"), (4, "A2", "r2"), (8, "A2", "r3"), (20, "A1", None)],
    "federal_event": [(2, "A2", "r2"), (6, "A2", "r3"), (20, "A1", None)],
    "all_russian": [(2, "A2", "r2"), (6, "A2", "r3"), (20, "A1", None)],
}
RANK_TITLE = {"ms": "мастер спорта", "kms": "кандидат в мастера спорта", "r1": "I спортивный разряд", "r2": "II спортивный разряд", "r3": "III спортивный разряд"}


def weighted(rng: random.Random, weights: dict) -> str:
    items = list(weights)
    return rng.choices(items, weights=[weights[i] for i in items])[0]


@dataclass
class SynthCandidate:
    idx: int
    full_name: str
    female: bool
    city: str
    specialization: str
    true_grade: str
    theta: float
    true_stack: list[str]
    declared_stack: list[str]          # что кандидат написал в профиле (неполный и с лишним)
    claimed_grade: str                 # что заявил (иногда завышает)
    experience_years: float
    salary_min: int
    salary_max: int
    work_format: str
    fsp: dict | None = None            # {"fsp_id", "results": [...], "rank": ...} либо None — без истории
    roles: list[str] = field(default_factory=list)
    soft: list[str] = field(default_factory=list)
    about: str = ""


def _salary(spec: str, grade: str, rng: random.Random) -> tuple[int, int]:
    base = {"junior": 90, "middle": 180, "senior": 300, "lead": 380}[grade]
    k = {"data": 1.1, "devops": 1.1, "security": 1.1, "qa": 0.8, "analytics": 0.85}.get(spec, 1.0)
    lo = int(base * k * rng.uniform(0.85, 1.05)) * 1000
    return lo, int(lo * rng.uniform(1.2, 1.45) / 1000) * 1000


def make_candidates(n: int, rng: random.Random, events: list[dict], honesty: str = "typical") -> list[SynthCandidate]:
    """honesty: 'honest' — резюме почти правдивы; 'typical' — часть технологий приписана, грейд нередко завышен;
    'inflated' — сильное приукрашивание (рынок, где резюме не проверяют)."""
    H = {"honest": dict(keep=0.9, extra_p=0.15, extra_n=(1, 1), over=0.08, under=0.05),
         "typical": dict(keep=0.8, extra_p=0.55, extra_n=(1, 3), over=0.25, under=0.05),
         "inflated": dict(keep=0.75, extra_p=0.8, extra_n=(2, 4), over=0.4, under=0.03),
         "extreme": dict(keep=0.7, extra_p=0.95, extra_n=(3, 5), over=0.6, under=0.02)}[honesty]   # extreme — только для проверки устойчивости
    out = []
    used = set()
    for i in range(n):
        spec = weighted(rng, SPEC_WEIGHTS)
        grade = weighted(rng, GRADE_WEIGHTS)
        theta = rng.gauss(GRADE_THETA[grade], 0.45)
        pool = SPEC_STACK[spec]
        k = {"junior": (3, 5), "middle": (5, 8), "senior": (7, 10), "lead": (7, 11)}[grade]
        true_stack = rng.sample(pool, min(len(pool), rng.randint(*k)))
        declared = [s for s in true_stack if rng.random() < H["keep"]]
        if rng.random() < H["extra_p"]:                          # приписанные технологии
            others = [s for s in pool if s not in true_stack] or pool
            for extra in rng.sample(others, min(len(others), rng.randint(*H["extra_n"]))):
                if extra not in declared:
                    declared.append(extra)
        gi = GRADES.index(grade)
        claimed = GRADES[min(gi + 1, 3)] if rng.random() < H["over"] else GRADES[max(gi - 1, 0)] if rng.random() < H["under"] else grade
        for attempt in range(1000):
            first = rng.choice(FIRST)
            female = first in FEMALE
            last = rng.choice(LAST_M) + ("а" if female else "")
            name = f"{first} {last}" + (f" {attempt}" if attempt > 600 else "")
            if name not in used:
                used.add(name)
                break
        exp = {"junior": rng.uniform(0, 1.2), "middle": rng.uniform(1, 3.5), "senior": rng.uniform(3, 8), "lead": rng.uniform(5, 12)}[grade]
        lo, hi = _salary(spec, grade, rng)
        c = SynthCandidate(i, name, female, rng.choice(CITIES), spec, grade, round(theta, 3), true_stack, declared, claimed,
                           round(exp, 1), lo, hi, rng.choice(["remote", "hybrid", "office", "remote"]))
        c.roles = rng.sample(ROLES, rng.randint(1, 2))
        c.soft = rng.sample(SOFT, rng.randint(2, 4))
        c.about = f"{'Специализируюсь' if not female else 'Специализируюсь'} на направлении «{spec}», опыт {c.experience_years} лет. " \
                  f"Основные технологии: {', '.join(true_stack[:4])}."
        # история ФСП: у 45 % кандидатов; сильнее у сильных
        if rng.random() < 0.45 + 0.15 * gi:
            c.fsp = make_fsp_history(rng, i, events, theta)
        out.append(c)
    return out


ONLY_PAST_EVENTS = False   # демо-сид ставит True: достижения только по уже прошедшим событиям; валидационные миры — как раньше


def make_fsp_history(rng: random.Random, idx: int, events: list[dict], theta: float) -> dict:
    if ONLY_PAST_EVENTS:
        import datetime as _dt
        today = _dt.date.today().isoformat()
        events = [e for e in events if str(e.get("date_start", ""))[:10] <= today] or events
    fsp_id = f"FSP-{100000 + idx * 7 + rng.randint(0, 6)}"
    n_ev = rng.choice([1, 1, 2, 2, 3])
    results = []
    best_rank = None
    for _ in range(n_ev):
        ev = rng.choice(events)
        # сильные чаще занимают высокие места
        place = max(1, int(rng.expovariate(0.5 + max(theta, -1.5) * 0.4) * 3) + 1)
        results.append({"ekp_number": ev["ekp_number"], "event_name": ev["name"], "level": ev["level"], "date": ev["date_start"], "place": place,
                        "discipline": rng.choice(["product", "product", "algorithmic", "security"])})
        for upto, code, rank in LEVEL_PLACES.get(ev["level"], LEVEL_PLACES["all_russian"]):
            if place <= upto:
                if rank and (best_rank is None or ["r3", "r2", "r1", "kms", "ms"].index(rank) > ["r3", "r2", "r1", "kms", "ms"].index(best_rank)):
                    best_rank = rank
                break
    return {"fsp_id": fsp_id, "results": results, "rank": best_rank}


def level_for(level: str, place: int) -> tuple[str, str | None]:
    for upto, code, rank in LEVEL_PLACES.get(level, LEVEL_PLACES["all_russian"]):
        if place <= upto:
            return code, rank
    return "A1", None


def load_events() -> list[dict]:
    p = os.path.join(os.path.dirname(__file__), "data", "ekp_events.json")
    return json.load(open(p, encoding="utf-8"))


@dataclass
class SynthNeed:
    company: str
    title: str
    text: str
    specialization: str
    grade: str
    stack: list[str]
    salary_min: int
    salary_max: int
    work_format: str


NEED_TEMPLATES = [
    ("backend", "middle", "Бэкенд-разработчик в команду платежей", "Ищем бэкенд-разработчика уровня middle на Python: FastAPI, PostgreSQL, Docker, очереди Kafka. Команда делает платёжный шлюз, важны аккуратность с данными и тесты."),
    ("backend", "senior", "Senior Go/Python разработчик", "Нужен senior разработчик на Go или Python для высоконагруженного сервиса: Redis, PostgreSQL, Kubernetes, Linux. Проектирование API и наставничество."),
    ("frontend", "junior", "Junior фронтенд-разработчик", "Стажёр или junior на фронтенд: JavaScript, TypeScript, React, вёрстка HTML/CSS. Поддержка интерфейса личного кабинета."),
    ("frontend", "middle", "Фронтенд-разработчик Vue", "Middle фронтенд: Vue, TypeScript, REST, сборка Webpack/Vite, Git. Делаем интерфейсы для аналитиков."),
    ("data", "middle", "Аналитик данных", "Аналитик данных: SQL, Python, pandas, статистика и A/B тесты, ClickHouse. Строим отчётность для продукта."),
    ("data", "senior", "ML-инженер", "Senior ML-инженер: PyTorch, scikit-learn, Python, Spark, Airflow. Рекомендательные модели в проде."),
    ("qa", "middle", "Инженер по тестированию (автоматизация)", "Тестировщик с автоматизацией: pytest, Playwright или Selenium, Postman, SQL, тест-дизайн. Веб-приложение и API."),
    ("devops", "senior", "DevOps-инженер", "Senior DevOps: Kubernetes, Terraform, CI/CD, Prometheus, Grafana, Linux, Docker. Инфраструктура в Yandex Cloud."),
    ("mobile", "middle", "Android-разработчик", "Middle Android-разработчик: Kotlin, Android, REST, SQL. Мобильное приложение для водителей."),
    ("analytics", "middle", "Системный аналитик", "Системный аналитик: сбор требований, UML, BPMN, SQL, работа с разработчиками по Agile."),
    ("security", "middle", "Специалист по безопасности приложений", "AppSec: основы ИБ, OWASP, криптография, Linux, Docker, Python для автоматизации проверок."),
    ("fullstack", "senior", "Фулстек-разработчик", "Senior фулстек: Python (FastAPI), TypeScript, React, PostgreSQL, Docker, REST. Малая команда, много ответственности."),
]


def make_needs(rng: random.Random) -> list[SynthNeed]:
    out = []
    for i, (spec, grade, title, text) in enumerate(NEED_TEMPLATES):
        from .services.skills_catalog import extract_skills
        stack = extract_skills(text)
        lo, hi = _salary(spec, grade, rng)
        out.append(SynthNeed(COMPANIES[i % len(COMPANIES)][0], title, text, spec, grade, stack, lo, hi, rng.choice(["remote", "hybrid", "office"])))
    return out


REL_OVERLAP = 0.5        # правило релевантности: доля требуемого стека в истинном стеке (варианты генератора — scripts/evolve/features.py --variant)
REL_GRADE_SPAN = 1       # допустимая разница истинного грейда и грейда потребности


def relevant(need: SynthNeed, c: SynthCandidate) -> bool:
    """Истинная релевантность пары по скрытым данным (docs/07, раздел 5)."""
    if c.specialization != need.specialization and not (need.specialization == "fullstack" and c.specialization in ("backend", "frontend")):
        return False
    if abs(GRADES.index(c.true_grade) - GRADES.index(need.grade)) > REL_GRADE_SPAN:
        return False
    if need.stack:
        overlap = len(set(need.stack) & set(c.true_stack)) / len(need.stack)
        if overlap < REL_OVERLAP:
            return False
    return c.salary_min <= need.salary_max
