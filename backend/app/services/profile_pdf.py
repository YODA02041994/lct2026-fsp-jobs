"""Стандартизированный PDF-профиль кандидата (fpdf2, шрифт Montserrat с кириллицей)."""
from __future__ import annotations
import os
from fpdf import FPDF
from ..catalog import category_title, GRADE_TITLE
from .skills_catalog import skill_name
from .views import TRUST_TITLE

ASSETS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


def build_profile_pdf(profile: dict, achievements: list[dict], include_contacts: bool = True) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    reg = os.path.join(ASSETS, "Montserrat-Regular.ttf")
    bold = os.path.join(ASSETS, "Montserrat-Bold.ttf")
    if os.path.exists(reg):
        pdf.add_font("M", "", reg)
        pdf.add_font("M", "B", bold if os.path.exists(bold) else reg)
        font = "M"
    else:
        font = "helvetica"
    pdf.set_text_color(0x31, 0x0F, 0x53)
    pdf.set_font(font, "B", 18)
    pdf.cell(0, 10, profile.get("full_name") or profile.get("alias") or "Профиль кандидата", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font, "", 11)
    pdf.set_text_color(0x1C, 0x1D, 0x22)
    cat = profile.get("category")
    pdf.cell(0, 7, f"Категория: {cat['title'] if cat else 'не определена'} · Карьера ФСП", new_x="LMARGIN", new_y="NEXT")
    if include_contacts:
        contacts = ", ".join(x for x in [profile.get("email"), profile.get("phone"), profile.get("telegram")] if x)
        if contacts:
            pdf.cell(0, 7, f"Контакты: {contacts}", new_x="LMARGIN", new_y="NEXT")
    rows = [("Город", profile.get("city") or "—"), ("Стаж, лет", str(profile.get("experience_years") or 0)),
            ("Роли", ", ".join(profile.get("roles") or []) or "—"), ("Формат работы", profile.get("work_format") or "—"),
            ("Зарплатные ожидания", f"{profile.get('salary_min') or '—'} – {profile.get('salary_max') or '—'} ₽")]
    pdf.ln(3)
    for k, v in rows:
        pdf.set_font(font, "B", 10); pdf.cell(48, 7, k)
        pdf.set_font(font, "", 10); pdf.multi_cell(0, 7, v, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font(font, "B", 12); pdf.cell(0, 8, "Технологии", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font, "", 10)
    conf = [skill_name(s["skill"]) for s in profile.get("skills", []) if s.get("confirmed_by_test")]
    decl = [skill_name(s["skill"]) for s in profile.get("skills", []) if not s.get("confirmed_by_test")]
    pdf.multi_cell(0, 6, "Подтверждено тестом: " + (", ".join(conf) or "—"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 6, "Заявлено: " + (", ".join(decl) or "—"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font(font, "B", 12); pdf.cell(0, 8, "Достижения ФСП", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font, "", 10)
    vis = [a for a in achievements if not a.get("hidden") and a.get("status") == "active"]
    if not vis:
        pdf.multi_cell(0, 6, "История ФСП отсутствует" if not profile.get("fsp_id") else "Подтверждённых достижений нет", new_x="LMARGIN", new_y="NEXT")
    for a in vis:
        pdf.multi_cell(0, 6, f"• {a['title']} — {a.get('date') or ''} ({TRUST_TITLE.get(a['trust_level'], a['trust_level'])})", new_x="LMARGIN", new_y="NEXT")
    if profile.get("about"):
        pdf.ln(2)
        pdf.set_font(font, "B", 12); pdf.cell(0, 8, "О себе", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(font, "", 10); pdf.multi_cell(0, 6, profile["about"], new_x="LMARGIN", new_y="NEXT")
    if profile.get("soft_skills"):
        pdf.ln(1)
        pdf.set_font(font, "", 10); pdf.multi_cell(0, 6, "Гибкие навыки: " + ", ".join(profile["soft_skills"]), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font(font, "", 8); pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5, "Профиль сформирован платформой «Карьера ФСП». Грейд подтверждён тестированием; достижения с пометкой «подтверждено источником» сверены с реестром ФСП.", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
