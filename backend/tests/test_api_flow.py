"""Сквозной сценарий ТЗ: регистрация → тест → категория → подборка работодателя → приглашение → контакты."""
from tests.conftest import register_and_confirm


def test_register_requires_confirmation(client):
    r = client.post("/api/v1/auth/register", json={"email": "u1@example.com", "password": "password123", "role": "candidate"})
    assert r.status_code == 201 and r.json()["confirm_required"]
    r = client.post("/api/v1/auth/login", json={"email": "u1@example.com", "password": "password123"})
    assert r.status_code == 403
    r = client.post("/api/v1/auth/register", json={"email": "u1@example.com", "password": "password123", "role": "candidate"})
    assert r.status_code == 409


def test_catalog_public(client):
    r = client.get("/api/v1/catalog")
    assert r.status_code == 200
    d = r.json()
    assert {"backend", "frontend", "data", "qa"} <= {s["code"] for s in d["specializations"]}
    assert abs(sum(d["weights"].values()) - 1.0) < 1e-6


def test_candidate_test_flow(client):
    h = register_and_confirm(client, "cand@example.com", "candidate")
    r = client.put("/api/v1/candidates/me", headers=h, json={"full_name": "Тест Тестов", "skills": ["Python", "postgres", "docker"], "salary_min": 100000, "salary_max": 150000})
    assert r.status_code == 200
    assert {s["skill"] for s in r.json()["skills"]} == {"python", "postgresql", "docker"}
    r = client.post("/api/v1/tests/sessions", headers=h, json={"specialization_code": "backend", "claimed_grade": "middle", "declared_skills": ["python", "sql"]})
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["status"] == "active" and len(s["items"]) == 3
    for it in s["items"]:
        assert "answer" not in it["payload"] and "answer_key" not in it
        r = client.post(f"/api/v1/tests/sessions/{s['id']}/answer", headers=h, json={"item_id": it["id"], "answer": "0"})
        assert r.status_code == 200 and "correct" not in r.json()
    r = client.post(f"/api/v1/tests/sessions/{s['id']}/next", headers=h)
    assert r.status_code == 200
    s = r.json()
    assert s["current_block"] == 2 and len(s["items"]) == 6
    for it in s["items"][3:]:
        client.post(f"/api/v1/tests/sessions/{s['id']}/answer", headers=h, json={"item_id": it["id"], "answer": "0"})
    r = client.post(f"/api/v1/tests/sessions/{s['id']}/next", headers=h)
    s = r.json()
    assert s["status"] == "finished" and s["result"]["result_grade"] in ("junior", "middle", "senior", "lead")
    assert s["result"]["decision"] in ("confirmed", "suggest_lower", "suggest_higher")
    me = client.get("/api/v1/candidates/me", headers=h).json()
    assert me["claimed_grade"] == "middle"
    # повторный сеанс сразу после — только если грейд не менялся или это предложение
    r = client.get("/api/v1/tests/options", headers=h)
    assert r.status_code == 200


def test_employer_selection_invitation_contacts(client):
    he = register_and_confirm(client, "emp@example.com", "employer")
    client.put("/api/v1/employers/me", headers=he, json={"company_name": "ООО Тест", "description": "тестовая компания"})
    r = client.post("/api/v1/needs", headers=he, json={"title": "Бэкенд", "text": "Нужен middle бэкенд на Python, FastAPI, PostgreSQL. 150-200 тыс.", "work_format": "remote"})
    assert r.status_code == 201, r.text
    need = r.json()["need"]
    assert need["specialization_code"] == "backend" and need["grade"] == "middle" and "python" in need["stack"] and need["salary_min"] == 150000
    r = client.post(f"/api/v1/needs/{need['id']}/selection", headers=he, json={})
    assert r.status_code == 201, r.text
    sel = r.json()
    v1 = sel["versions"][0]
    assert v1["categories"] and v1["results"]
    top = v1["results"][0]
    assert top["contacts_unlocked"] is False and "contacts" not in top and "full_name" not in top
    assert top["explanation"] and set(top["parts"]) == {"stack", "grade", "strength", "fsp", "activity", "conditions"}
    scores = [x["score"] for x in v1["results"]]
    assert scores == sorted(scores, reverse=True)
    r = client.post(f"/api/v1/selections/{sel['id']}/refine", headers=he, json={"filters": {"grades": ["middle"]}})
    sel2 = r.json()
    assert len(sel2["versions"]) == 2 and all(x["category"]["grade"] == "middle" for x in sel2["versions"][1]["results"])
    cid = top["candidate_id"]
    r = client.post("/api/v1/invitations", headers=he, json={"candidate_id": cid, "message": "Приглашаем на позицию бэкенд-разработчика", "salary_min": 150000, "salary_max": 200000, "contact_method": "почта hr@test.ru"})
    assert r.status_code == 201, r.text
    inv = r.json()
    assert inv["status"] == "sent" and "contacts" not in inv
    r = client.post("/api/v1/invitations", headers=he, json={"candidate_id": cid, "message": "Дубль приглашения для проверки", "salary_min": 1, "salary_max": 2, "contact_method": "x@y.z"})
    assert r.status_code == 409
    r = client.post("/api/v1/invitations", headers=he, json={"candidate_id": cid, "message": "Проверка зарплатной вилки на ошибку", "salary_min": 300000, "salary_max": 200000, "contact_method": "x@y.z"})
    assert r.status_code == 422
    # кандидат отвечает
    from app.db import SessionLocal
    from app.models import Candidate
    with SessionLocal() as db:
        email = db.get(Candidate, cid).user.email
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "demo12345"})
    hc = {"Authorization": f"Bearer {r.json()['access_token']}"}
    invs = client.get("/api/v1/candidates/me/invitations", headers=hc).json()
    assert invs[0]["id"] == inv["id"] and invs[0]["salary_min"] == 150000 and invs[0]["company_name"] == "ООО Тест"
    client.post(f"/api/v1/invitations/{inv['id']}/view", headers=hc)
    r = client.post(f"/api/v1/invitations/{inv['id']}/respond", headers=hc, json={"decision": "accept"})
    assert r.json()["status"] == "accepted"
    card = client.get(f"/api/v1/candidates/{cid}/card", headers=he).json()
    assert card["contacts_unlocked"] is True and card["contacts"]["full_name"]
    # другой работодатель контактов не видит
    he2 = register_and_confirm(client, "emp2@example.com", "employer")
    card2 = client.get(f"/api/v1/candidates/{cid}/card", headers=he2).json()
    assert card2["contacts_unlocked"] is False and "contacts" not in card2
    # кандидат не может смотреть чужие приглашения и кабинет работодателя
    assert client.get("/api/v1/employers/me", headers=hc).status_code == 403
    assert client.get("/api/v1/candidates/search", headers=hc).status_code == 403


def test_vacancy_apply_and_bank_search(client):
    he = register_and_confirm(client, "emp3@example.com", "employer")
    client.put("/api/v1/employers/me", headers=he, json={"company_name": "Банк кандидатов"})
    r = client.post("/api/v1/vacancies", headers=he, json={"title": "Аналитик данных", "description": "SQL, Python, pandas, A/B тесты", "specialization_code": "data", "grade": "middle", "salary_min": 150000, "salary_max": 200000})
    assert r.status_code == 201, r.text
    vac = r.json()
    assert "sql" in vac["stack"] and "pandas" in vac["stack"]
    r = client.get(f"/api/v1/vacancies/{vac['id']}/test-preview", headers=he)
    assert r.status_code == 200 and r.json()["technologies"]
    r = client.get("/api/v1/candidates/search", headers=he, params={"specialization_code": "data", "fsp_only": "true"})
    assert r.status_code == 200
    for c in r.json():
        assert c["category"]["specialization_code"] == "data" and c["contacts_unlocked"] is False
    hc = register_and_confirm(client, "cand2@example.com", "candidate")
    r = client.post(f"/api/v1/vacancies/{vac['id']}/apply", headers=hc, json={"message": "Хочу к вам"})
    assert r.status_code == 201
    apps = client.get(f"/api/v1/vacancies/{vac['id']}/applications", headers=he).json()
    assert apps and apps[0]["candidate"]["contacts_unlocked"] is True


def test_privacy_requires_publication_consent(client):
    h = register_and_confirm(client, "priv@example.com", "candidate")
    r = client.put("/api/v1/candidates/me/privacy", headers=h, json={"visible_to_employers": True})
    assert r.status_code == 409
    client.post("/api/v1/candidates/me/consents", headers=h, json={"processing": True, "publication": True})
    r = client.put("/api/v1/candidates/me/privacy", headers=h, json={"visible_to_employers": True, "salary": False})
    assert r.status_code == 200 and r.json()["visible_to_employers"] and r.json()["privacy"]["salary"] is False
    r = client.post("/api/v1/candidates/me/consents", headers=h, json={"publication": False})
    assert r.json()["visible_to_employers"] is False


def test_fsp_mock_link_imports_achievements(client):
    h = register_and_confirm(client, "fsp@example.com", "candidate")
    r = client.get("/api/v1/fsp/link/start", headers=h)
    assert r.status_code == 200 and r.json()["mock"]
    url = r.json()["redirect_url"]
    state = url.split("state=")[1].split("&")[0]
    page = client.get(url.replace("http://localhost:8000", "", 1))
    assert page.status_code == 200 and "FSP-" in page.text
    from app.db import SessionLocal
    from app.models import FspParticipant, Candidate
    from sqlalchemy import select
    with SessionLocal() as db:
        linked = set(db.scalars(select(Candidate.fsp_id).where(Candidate.fsp_id.is_not(None))).all())
        p = next(x for x in db.scalars(select(FspParticipant).where(FspParticipant.rank.is_not(None))).all() if x.fsp_id not in linked)
    r = client.post("/api/v1/fsp/mock/authorize", data={"state": state, "redirect_uri": "http://testserver/api/v1/fsp/callback", "fsp_id": p.fsp_id}, follow_redirects=False)
    assert r.status_code == 303
    cb = r.headers["location"].replace("http://testserver", "")
    r = client.get(cb, follow_redirects=False)
    assert r.status_code == 303 and "fsp=linked" in r.headers["location"]
    acts = client.get("/api/v1/candidates/me/achievements", headers=h).json()
    assert acts and all(a["trust_level"] == "source" for a in acts)
    me = client.get("/api/v1/candidates/me", headers=h).json()
    assert me["fsp_id"] == p.fsp_id
    r = client.post("/api/v1/fsp/unlink", headers=h)
    assert r.json()["fsp_id"] is None
