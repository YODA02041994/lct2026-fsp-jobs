"""Справочники: специализации, грейды, форматы работы, веса подбора."""
SPECIALIZATIONS = [
    ("backend", "Бэкенд-разработка", "серверная логика, API, базы данных", True, 1),
    ("frontend", "Фронтенд-разработка", "интерфейсы в браузере", True, 2),
    ("fullstack", "Фулстек-разработка", "бэкенд и фронтенд", False, 3),
    ("mobile", "Мобильная разработка", "Android, iOS, кроссплатформенные приложения", False, 4),
    ("data", "Данные и машинное обучение", "аналитика данных, инженерия данных, модели", True, 5),
    ("devops", "DevOps и эксплуатация", "инфраструктура, сборка, развёртывание, наблюдаемость", False, 6),
    ("qa", "Тестирование", "ручное и автоматизированное тестирование", True, 7),
    ("analytics", "Аналитика", "системный и бизнес-анализ, продуктовая аналитика", False, 8),
    ("security", "Информационная безопасность", "защита приложений и инфраструктуры", False, 9),
]
GRADES = [
    ("junior", "Junior", "до года опыта или стажёр"),
    ("middle", "Middle", "от года до трёх лет, самостоятельные задачи"),
    ("senior", "Senior", "от трёх лет, ведёт сложные задачи и проектирует"),
    ("lead", "Lead", "руководит разработкой и командой"),
]
WORK_FORMATS = [("office", "Офис"), ("remote", "Удалённо"), ("hybrid", "Гибрид")]
DEFAULT_WEIGHTS = {'stack': 0.44, 'grade': 0.24, 'strength': 0.14, 'fsp': 0.05, 'activity': 0.05, 'conditions': 0.08}   # веса формулы подбора (best_2026-10-07b), ставит install_formula.py
GRADE_TITLE = {c: t for c, t, _ in GRADES}
SPEC_TITLE = {c: n for c, n, *_ in SPECIALIZATIONS}


def category_title(spec: str | None, grade: str | None) -> str:
    if not spec or not grade:
        return "категория не определена"
    return f"{SPEC_TITLE.get(spec, spec)} · {GRADE_TITLE.get(grade, grade)}"
