"""Разбор потребности и резюме с внешней моделью: без ключа — только правила; с ответом модели — поля проверяются по справочнику."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.services import llm, need_parser, resume


def test_without_model_rules_only(monkeypatch):
    monkeypatch.setattr(llm, "enabled", lambda: False)
    out = need_parser.parse_full("Senior Python-разработчик, PostgreSQL, Docker, 250-320 тыс.")
    assert out["source"] == "rules" and out["grade"] == "senior" and "python" in out["stack"] and out["salary_min"] == 250000


def test_model_fills_gaps_and_is_validated(monkeypatch):
    monkeypatch.setattr(llm, "enabled", lambda: True)
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {
        "specialization_code": "Mobile", "grade": "Senior+", "stack": ["Kotlin", "Постгрес", "выдуманная-технология", 42],
        "salary_min": 180000, "salary_max": 90000})
    out = need_parser.parse_full("Нужен разработчик приложения под Android в банк, +7 999 123-45-67")
    assert out["source"] == "rules+model"
    assert out["specialization_code"] == "mobile"            # правила нашли «android» → mobile, модель согласна
    assert out["grade"] is None                               # «Senior+» нет в справочнике → отброшено
    assert "kotlin" in out["stack"] and "postgresql" in out["stack"]
    assert "выдуманная-технология" not in out["stack"] and 42 not in out["stack"]
    assert out["salary_min"] is None and out["salary_max"] is None   # min > max → пара отброшена


def test_model_text_is_deidentified(monkeypatch):
    seen = {}
    monkeypatch.setattr(llm, "enabled", lambda: True)

    def fake(messages, **kw):
        seen["text"] = messages[-1]["content"]
        return {"city": "Казань", "experience_years": 4, "skills": ["Go"], "roles": ["бэкенд-разработчик"], "about": "Пишет сервисы на Go."}
    monkeypatch.setattr(llm, "chat_json", fake)
    text = "Иванов Пётр Сергеевич\nТелефон +7 912 345-67-89, почта petr@example.com, @petr_dev\nОпыт 4 года, Go, gRPC"
    parsed = resume.parse_resume(text)
    out = resume.enrich_with_model(text, parsed)
    assert "Иванов" not in seen["text"] and "+7 912" not in seen["text"] and "petr@example.com" not in seen["text"] and "petr_dev" not in seen["text"]
    assert out["full_name"] == "Иванов Пётр Сергеевич"       # ФИО осталось только в локальном разборе
    assert out["city"] == "Казань" and out["experience_years"] == 4.0 and "go" in out["skills"]
    assert out["about"] == "Пишет сервисы на Go." and out["source"] == "rules+model"
