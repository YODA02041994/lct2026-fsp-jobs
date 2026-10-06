"""Разбор текста потребности или вакансии: технологии, грейд, специализация — по словарю и правилам."""
import re
from .skills_catalog import extract_skills, GROUPS

GRADE_HINTS = [
    ("lead", r"\b(lead|лид|тимлид|руководител[ья]|team ?lead|head of)\b"),
    ("senior", r"\b(senior|сеньор|синьор|старш\w+|от 3 лет|от 4 лет|от 5 лет|5\+ лет|3\+ лет)\b"),
    ("junior", r"\b(junior|джун\w*|младш\w+|стаж[её]р\w*|без опыта|до года|intern|начинающ\w+)\b"),
    ("middle", r"\b(middle|мидл\w*|1-3 года|от года|от 2 лет|2\+ лет)\b"),
]
SPEC_HINTS = [
    ("frontend", r"\b(frontend|фронтенд|front-end|вёрстк|верстк|react|vue|angular|интерфейс\w*)\b"),
    ("mobile", r"\b(mobile|мобильн\w+|android|ios|flutter|react native)\b"),
    ("data", r"\b(data|данн\w+|ml|машинн\w+ обучен\w*|аналитик\w* данных|data scientist|data engineer|дата)\b"),
    ("devops", r"\b(devops|sre|эксплуатац\w*|инфраструктур\w*|kubernetes|k8s|ci/cd)\b"),
    ("qa", r"\b(qa|тестировщ\w+|тестирован\w+|автотест\w*)\b"),
    ("security", r"\b(безопасност\w+|security|appsec|пентест\w*)\b"),
    ("analytics", r"\b(системн\w+ аналитик\w*|бизнес-аналитик\w*|продуктов\w+ аналитик\w*|аналитик\w*)\b"),
    ("backend", r"\b(backend|бэкенд|back-end|серверн\w+|api|python|java|go|golang|c#|php|node)\b"),
]
SALARY_RE = re.compile(r"(\d{2,3})\s?(?:000|тыс\.?|к)?\s*(?:[-–—]|до)\s*(\d{2,3})\s?(?:000|тыс\.?|к)", re.I)


def parse(text: str) -> dict:
    t = text or ""
    low = t.lower()
    out = {"stack": extract_skills(t), "grade": None, "specialization_code": None, "salary_min": None, "salary_max": None}
    for g, pat in GRADE_HINTS:
        if re.search(pat, low, re.I):
            out["grade"] = g
            break
    for sp, pat in SPEC_HINTS:
        if re.search(pat, low, re.I):
            out["specialization_code"] = sp
            break
    if not out["specialization_code"] and out["stack"]:
        groups = [GROUPS.get(s) for s in out["stack"]]
        if "qa" in groups:
            out["specialization_code"] = "qa"
        elif groups.count("ml") + groups.count("data") >= 2:
            out["specialization_code"] = "data"
        elif any(s in ("react", "vue", "angular", "html", "css", "javascript", "typescript") for s in out["stack"]):
            out["specialization_code"] = "frontend"
        else:
            out["specialization_code"] = "backend"
    m = SALARY_RE.search(low)
    if m:
        out["salary_min"], out["salary_max"] = int(m.group(1)) * 1000, int(m.group(2)) * 1000
    return out
