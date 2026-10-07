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


# --- уточнение внешней моделью (необязательно) ------------------------------------------------------------
# Модель получает текст без телефонов, почты и Telegram и возвращает JSON. Ответ модели — ненадёжный ввод:
# каждое поле проверяется по справочнику (коды технологий, грейды, специализации), остальное отбрасывается.
from . import llm
from .skills_catalog import normalize_skill
from ..catalog import GRADE_TITLE, SPEC_TITLE

_MODEL_PROMPT = (
    "Ты разбираешь описание потребности работодателя в ИТ-специалисте. Верни JSON с полями: "
    "specialization_code (один из: {specs}), grade (один из: junior, middle, senior, lead; null если не ясно), "
    "stack (список технологий, которые требуются, по-английски как принято: PostgreSQL, Kotlin, Kubernetes…; "
    "не добавляй технологии, которых нет в тексте), salary_min и salary_max (рубли в месяц, целые числа или null). "
    "Только JSON, без пояснений."
)


def parse_with_model(text: str) -> dict | None:
    """→ проверенные поля из ответа модели или None (модель не настроена, не ответила, ответ не разобран)."""
    if not llm.enabled():
        return None
    from .resume import deidentify
    clean = deidentify(text or "")[:6000]
    data = llm.chat_json([{"role": "system", "content": _MODEL_PROMPT.format(specs=", ".join(SPEC_TITLE))},
                          {"role": "user", "content": clean}], max_tokens=500)
    if not isinstance(data, dict):
        return None
    out: dict = {}
    sp = data.get("specialization_code")
    if isinstance(sp, str) and sp.strip().lower() in SPEC_TITLE:
        out["specialization_code"] = sp.strip().lower()
    g = data.get("grade")
    if isinstance(g, str) and g.strip().lower() in GRADE_TITLE:
        out["grade"] = g.strip().lower()
    stack = []
    for s in data.get("stack") or []:
        code = normalize_skill(str(s)) if isinstance(s, (str, int)) else None
        if code and code not in stack:
            stack.append(code)
    if stack:
        out["stack"] = stack
    for k in ("salary_min", "salary_max"):
        v = data.get(k)
        if isinstance(v, (int, float)) and 10_000 <= v <= 5_000_000:
            out[k] = int(v)
    if "salary_min" in out and "salary_max" in out and out["salary_min"] > out["salary_max"]:
        out.pop("salary_min"); out.pop("salary_max")
    return out or None


def parse_full(text: str) -> dict:
    """Правила, затем модель: модель заполняет пропуски правил и дополняет стек. Поле source говорит, что сработало."""
    out = parse(text)
    out["source"] = "rules"
    m = parse_with_model(text)
    if not m:
        return out
    for k in ("specialization_code", "grade", "salary_min", "salary_max"):
        if out.get(k) is None and m.get(k) is not None:
            out[k] = m[k]
    for code in m.get("stack") or []:
        if code not in out["stack"]:
            out["stack"].append(code)
    out["source"] = "rules+model"
    return out
