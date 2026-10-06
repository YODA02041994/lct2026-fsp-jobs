"""Словарь технологий: канонический код, название, синонимы (нижний регистр), группа.
Единый для банка заданий, профилей кандидатов и потребностей работодателей."""
import re

# (код, название, [синонимы], группа)
SKILLS: list[tuple[str, str, list[str], str]] = [
    ("python", "Python", ["python3", "питон", "пайтон"], "lang"),
    ("java", "Java", ["джава"], "lang"),
    ("kotlin", "Kotlin", ["котлин"], "lang"),
    ("go", "Go", ["golang", "го"], "lang"),
    ("javascript", "JavaScript", ["js", "es6", "ecmascript", "джаваскрипт"], "lang"),
    ("typescript", "TypeScript", ["ts", "тайпскрипт"], "lang"),
    ("csharp", "C#", ["c#", ".net", "dotnet", "asp.net", "си шарп"], "lang"),
    ("cpp", "C++", ["c++", "си++", "cpp"], "lang"),
    ("c", "C", ["язык c", "си"], "lang"),
    ("php", "PHP", ["laravel", "symfony"], "lang"),
    ("rust", "Rust", ["раст"], "lang"),
    ("swift", "Swift", ["свифт"], "lang"),
    ("scala", "Scala", [], "lang"),
    ("ruby", "Ruby", ["rails", "ruby on rails"], "lang"),
    ("bash", "Bash", ["shell", "sh", "zsh", "командная строка"], "lang"),
    ("sql", "SQL", ["sql-запросы", "скл", "sql запросы"], "data"),
    ("postgresql", "PostgreSQL", ["postgres", "постгрес", "psql"], "db"),
    ("mysql", "MySQL", ["mariadb"], "db"),
    ("clickhouse", "ClickHouse", ["кликхаус"], "db"),
    ("mongodb", "MongoDB", ["mongo", "монго"], "db"),
    ("redis", "Redis", ["редис"], "db"),
    ("elasticsearch", "Elasticsearch", ["opensearch", "эластик"], "db"),
    ("kafka", "Kafka", ["apache kafka", "кафка"], "infra"),
    ("rabbitmq", "RabbitMQ", ["amqp", "рэббит"], "infra"),
    ("docker", "Docker", ["докер", "docker compose", "docker-compose"], "infra"),
    ("kubernetes", "Kubernetes", ["k8s", "кубер", "кубернетес", "helm"], "infra"),
    ("linux", "Linux", ["линукс", "ubuntu", "debian", "centos"], "infra"),
    ("git", "Git", ["гит", "github", "gitlab", "gitflow"], "tools"),
    ("ci_cd", "CI/CD", ["ci/cd", "ci cd", "gitlab ci", "github actions", "jenkins", "teamcity"], "infra"),
    ("nginx", "nginx", ["энджинкс"], "infra"),
    ("terraform", "Terraform", ["терраформ", "iac"], "infra"),
    ("ansible", "Ansible", ["ансибл"], "infra"),
    ("prometheus", "Prometheus", ["прометеус", "metrics"], "infra"),
    ("grafana", "Grafana", ["графана"], "infra"),
    ("aws", "AWS", ["amazon web services"], "cloud"),
    ("yandex_cloud", "Yandex Cloud", ["яндекс облако", "яндекс.облако", "yandex.cloud"], "cloud"),
    ("vk_cloud", "VK Cloud", ["vk cloud"], "cloud"),
    ("http", "HTTP", ["https", "протокол http"], "web"),
    ("rest", "REST API", ["rest", "restful", "rest api", "api"], "web"),
    ("graphql", "GraphQL", [], "web"),
    ("grpc", "gRPC", ["protobuf", "grpc"], "web"),
    ("websocket", "WebSocket", ["websockets", "веб-сокеты"], "web"),
    ("fastapi", "FastAPI", ["фастапи"], "framework"),
    ("django", "Django", ["джанго", "drf", "django rest framework"], "framework"),
    ("flask", "Flask", ["фласк"], "framework"),
    ("aiohttp", "aiohttp", [], "framework"),
    ("spring", "Spring", ["spring boot", "спринг"], "framework"),
    ("nodejs", "Node.js", ["node", "node.js", "nodejs", "express", "nestjs", "нода"], "framework"),
    ("react", "React", ["reactjs", "react.js", "реакт", "next.js", "nextjs", "redux"], "framework"),
    ("vue", "Vue", ["vue.js", "vuejs", "nuxt", "вью"], "framework"),
    ("angular", "Angular", ["ангуляр"], "framework"),
    ("svelte", "Svelte", ["sveltekit"], "framework"),
    ("html", "HTML", ["html5", "вёрстка", "верстка"], "web"),
    ("css", "CSS", ["css3", "scss", "sass", "less", "tailwind", "styled-components"], "web"),
    ("webpack", "Webpack", ["vite", "сборка фронтенда", "bundler", "rollup", "esbuild"], "tools"),
    ("pandas", "pandas", ["пандас"], "data"),
    ("numpy", "NumPy", ["нампай"], "data"),
    ("scikit_learn", "scikit-learn", ["sklearn", "scikit learn"], "ml"),
    ("pytorch", "PyTorch", ["torch", "пайторч"], "ml"),
    ("tensorflow", "TensorFlow", ["keras", "тензорфлоу"], "ml"),
    ("ml", "Машинное обучение", ["machine learning", "ml", "мл", "deep learning", "нейросети", "нейронные сети", "llm"], "ml"),
    ("nlp", "Обработка языка", ["nlp", "обработка естественного языка", "nlu", "transformers"], "ml"),
    ("cv", "Компьютерное зрение", ["computer vision", "opencv", "cv", "детекция", "сегментация"], "ml"),
    ("statistics", "Статистика", ["статистика", "a/b тесты", "ab-тесты", "а/б тесты", "математическая статистика", "теория вероятностей"], "data"),
    ("spark", "Spark", ["pyspark", "apache spark", "спарк"], "data"),
    ("airflow", "Airflow", ["apache airflow", "эйрфлоу", "etl", "elt"], "data"),
    ("dbt", "dbt", [], "data"),
    ("hadoop", "Hadoop", ["hdfs", "hive"], "data"),
    ("excel", "Excel", ["эксель", "google sheets", "гугл таблицы"], "analytics"),
    ("tableau", "Tableau", ["табло"], "analytics"),
    ("powerbi", "Power BI", ["power bi", "datalens", "superset", "metabase", "bi"], "analytics"),
    ("product_analytics", "Продуктовая аналитика", ["продуктовая аналитика", "amplitude", "метрики продукта", "unit-экономика", "юнит-экономика", "воронки"], "analytics"),
    ("system_analysis", "Системный анализ", ["системный анализ", "требования", "тз", "постановка задач", "спецификации"], "analytics"),
    ("uml", "UML", ["диаграммы uml", "sequence diagram"], "analytics"),
    ("bpmn", "BPMN", ["бизнес-процессы", "нотация bpmn"], "analytics"),
    ("pytest", "pytest", ["unittest", "юнит-тесты", "unit tests", "unit-тесты"], "qa"),
    ("selenium", "Selenium", ["селениум", "webdriver"], "qa"),
    ("playwright", "Playwright", ["cypress", "плейрайт"], "qa"),
    ("postman", "Postman", ["постман", "insomnia", "тестирование api"], "qa"),
    ("jmeter", "JMeter", ["нагрузочное тестирование", "k6", "locust", "gatling"], "qa"),
    ("testing_theory", "Теория тестирования", ["тест-дизайн", "тест-кейсы", "тестовая документация", "тест кейсы", "чек-листы", "баг-репорты", "istqb"], "qa"),
    ("android", "Android", ["андроид", "jetpack compose"], "mobile"),
    ("ios", "iOS", ["swiftui", "uikit", "айос"], "mobile"),
    ("flutter", "Flutter", ["dart", "флаттер"], "mobile"),
    ("react_native", "React Native", ["react-native"], "mobile"),
    ("security_basics", "Основы ИБ", ["информационная безопасность", "owasp", "уязвимости", "pentest", "пентест", "безопасность приложений", "appsec"], "security"),
    ("cryptography", "Криптография", ["шифрование", "tls", "pki", "сертификаты"], "security"),
    ("networking", "Сети", ["tcp/ip", "tcp", "dns", "сетевые протоколы", "vpn", "маршрутизация"], "infra"),
    ("algorithms", "Алгоритмы", ["алгоритмы", "структуры данных", "сложность алгоритмов", "big o", "олимпиадное программирование"], "cs"),
    ("oop", "ООП", ["объектно-ориентированное программирование", "oop", "solid", "паттерны", "design patterns", "шаблоны проектирования"], "cs"),
    ("system_design", "Проектирование систем", ["system design", "архитектура", "микросервисы", "высоконагруженные системы", "highload", "масштабирование"], "cs"),
    ("async", "Асинхронность", ["asyncio", "многопоточность", "concurrency", "параллелизм", "потоки"], "cs"),
    ("agile", "Agile", ["scrum", "скрам", "kanban", "канбан", "jira"], "process"),
    ("mentoring", "Наставничество", ["менторство", "руководство командой", "тимлид", "управление командой", "лидерство"], "process"),
]

CODES = {s[0] for s in SKILLS}
NAMES = {s[0]: s[1] for s in SKILLS}
GROUPS = {s[0]: s[3] for s in SKILLS}

# обратный индекс: синоним → код (многословные синонимы раньше коротких)
_SYN: list[tuple[str, str]] = []
for code, name, syns, _ in SKILLS:
    for s in {name.lower(), code.replace("_", " "), *syns}:
        _SYN.append((s.lower(), code))
_SYN.sort(key=lambda x: -len(x[0]))
_PATTERNS = [(re.compile(r"(?<![\w#+.])" + re.escape(s) + r"(?![\w#+])", re.I), code) for s, code in _SYN if len(s) >= 2]


def extract_skills(text: str) -> list[str]:
    """Коды технологий, упомянутых в тексте, в порядке первого появления."""
    if not text:
        return []
    found: dict[str, int] = {}
    for pat, code in _PATTERNS:
        m = pat.search(text)
        if m and code not in found:
            found[code] = m.start()
    return [c for c, _ in sorted(found.items(), key=lambda x: x[1])]


def normalize_skill(s: str) -> str | None:
    """Код по произвольному написанию, либо None."""
    s = (s or "").strip().lower()
    if not s:
        return None
    if s in CODES:
        return s
    for syn, code in _SYN:
        if s == syn:
            return code
    return None


def skill_name(code: str) -> str:
    return NAMES.get(code, code)
