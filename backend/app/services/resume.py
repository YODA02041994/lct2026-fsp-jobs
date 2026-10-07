"""Разбор резюме из PDF правилами: ФИО, контакты, город, стаж, технологии, роли, гибкие навыки.

Персональные данные (ФИО, телефон, почта, Telegram) извлекаются только локально. Внешней модели, если она настроена,
передаётся текст уже без них (см. deidentify)."""
from __future__ import annotations
import io
import re
from pdfminer.high_level import extract_text
from .skills_catalog import extract_skills
from ..synth import CITIES, ROLES, SOFT

PHONE_RE = re.compile(r"(\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
TG_RE = re.compile(r"(?:t\.me/|@)([A-Za-z][A-Za-z0-9_]{4,31})")
EXP_RE = re.compile(r"(?:опыт\w*|стаж\w*)[^\d\n]{0,30}(\d{1,2}(?:[.,]\d)?)\s*(?:лет|год|года|\+)", re.I)
NAME_RE = re.compile(r"^([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?)\s+([А-ЯЁ][а-яё]+)(?:\s+([А-ЯЁ][а-яё]+))?$")


def pdf_text(data: bytes) -> str:
    try:
        return extract_text(io.BytesIO(data)) or ""
    except Exception:
        return ""


def deidentify(text: str) -> str:
    t = PHONE_RE.sub("[телефон]", text)
    t = EMAIL_RE.sub("[почта]", t)
    t = TG_RE.sub("[telegram]", t)
    for line in text.splitlines()[:6]:
        if NAME_RE.match(line.strip()):
            t = t.replace(line.strip(), "[ФИО]")
    return t


def parse_resume(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out = {"full_name": "", "phone": "", "telegram": "", "email": "", "city": "", "experience_years": None, "skills": [], "roles": [], "soft_skills": [], "about": ""}
    for l in lines[:8]:
        m = NAME_RE.match(l)
        if m and not out["full_name"]:
            out["full_name"] = " ".join(x for x in m.groups() if x)
            break
    m = PHONE_RE.search(text)
    if m:
        out["phone"] = m.group(0).strip()
    m = EMAIL_RE.search(text)
    if m:
        out["email"] = m.group(0)
    m = TG_RE.search(text)
    if m:
        out["telegram"] = "@" + m.group(1)
    for city in CITIES:
        if city.lower() in text.lower():
            out["city"] = city
            break
    m = EXP_RE.search(text)
    if m:
        out["experience_years"] = float(m.group(1).replace(",", "."))
    out["skills"] = extract_skills(text)
    low = text.lower()
    out["roles"] = [r for r in ROLES if r in low][:3]
    out["soft_skills"] = [s for s in SOFT if s.split()[0] in low][:4]
    body = [l for l in lines if not PHONE_RE.search(l) and not EMAIL_RE.search(l) and not NAME_RE.match(l)]
    out["about"] = " ".join(body)[:600]
    return out


# --- уточнение внешней моделью (необязательно) ------------------------------------------------------------
from . import llm
from .skills_catalog import normalize_skill

_MODEL_PROMPT = (
    "Ты разбираешь обезличенное резюме ИТ-специалиста (ФИО и контакты заменены метками). Верни JSON с полями: "
    "city (город, строка или null), experience_years (число лет коммерческого опыта или null), "
    "skills (список технологий из текста по-английски как принято: PostgreSQL, Kotlin…; ничего не добавляй от себя), "
    "roles (до 3 ролей, например «бэкенд-разработчик»), soft_skills (до 4 гибких навыков), "
    "about (краткое описание опыта до 400 знаков, без имён и контактов, на русском). Только JSON."
)


def enrich_with_model(text: str, parsed: dict) -> dict:
    """Дополняет разбор правилами ответом модели. Модель видит текст после deidentify; поля проверяются."""
    if not llm.enabled():
        return parsed
    data = llm.chat_json([{"role": "system", "content": _MODEL_PROMPT}, {"role": "user", "content": deidentify(text)[:8000]}], max_tokens=700)
    if not isinstance(data, dict):
        return parsed
    out = dict(parsed)
    city = data.get("city")
    if not out.get("city") and isinstance(city, str) and 1 < len(city.strip()) <= 40:
        out["city"] = city.strip()
    exp = data.get("experience_years")
    if out.get("experience_years") is None and isinstance(exp, (int, float)) and 0 <= exp <= 50:
        out["experience_years"] = float(exp)
    for s in data.get("skills") or []:
        code = normalize_skill(str(s))
        if code and code not in out["skills"]:
            out["skills"].append(code)
    for k, cap in (("roles", 3), ("soft_skills", 4)):
        vals = [str(v).strip()[:60] for v in (data.get(k) or []) if isinstance(v, str) and v.strip()]
        merged = list(out.get(k) or [])
        for v in vals:
            if v not in merged:
                merged.append(v)
        out[k] = merged[:cap]
    about = data.get("about")
    if isinstance(about, str) and about.strip():
        about = deidentify(about.strip())            # на случай, если модель вернула что-то похожее на контакт
        for pat in (PHONE_RE, EMAIL_RE):
            if pat.search(about):
                about = ""
                break
        if about:
            out["about"] = about[:600]
    out["source"] = "rules+model"
    return out
