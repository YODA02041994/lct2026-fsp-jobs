#!/usr/bin/env python3
"""Проверка сквозного сценария ТЗ по HTTP против запущенного сервиса (после `docker compose up` или на стенде).

    python3 scripts/smoke_http.py                         # http://localhost:8080
    python3 scripts/smoke_http.py --base http://localhost:8000

Шаги: здоровье и справочники → регистрация кандидата с подтверждением почты → профиль, согласия, видимость → тест на грейд
(все блоки) → связь с ФСП ID у издателя-заглушки и импорт достижений → вход демо-работодателя → потребность текстом →
подборка, уточнение (версия 2) → приглашение новому кандидату → кандидат принимает → контакты открыты работодателю, но не
другим → вакансия и отклик. Создаёт тестовые записи с уникальной почтой; ничего не удаляет. Только стандартная библиотека Python.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OK, FAIL = "✓", "✗"
results: list[tuple[str, bool, str]] = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def call(base, method, path, token=None, body=None, form=None, follow=True):
    url = path if path.startswith("http") else base.rstrip("/") + path
    data, headers = None, {}
    if body is not None:
        data = json.dumps(body).encode(); headers["Content-Type"] = "application/json"
    if form is not None:
        data = urllib.parse.urlencode(form).encode(); headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=60) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(raw) if raw[:1] in "{[" else raw), dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return e.code, payload, dict(e.headers)


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"{OK if cond else FAIL} {name}" + (f" — {detail}" if detail else ""), flush=True)
    return bool(cond)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--employer", default="employer.demo@fsp-demo.ru")
    ap.add_argument("--password", default="demo12345")
    args = ap.parse_args()
    b = args.base
    stamp = int(time.time())
    api = "/api/v1"

    st, h, _ = call(b, "GET", "/api/health")
    check("сервис отвечает", st == 200 and h.get("status") == "ok", f"шаблонов {h.get('templates')}, демо-режим {h.get('demo_mode')}")
    st, cat, _ = call(b, "GET", f"{api}/catalog")
    check("справочники", st == 200 and len(cat.get("specializations", [])) >= 8, f"{len(cat.get('specializations', []))} специализаций")

    # кандидат
    email = f"smoke{stamp}@fsp-demo.ru"
    st, reg, _ = call(b, "POST", f"{api}/auth/register", body={"email": email, "password": "password123", "role": "candidate"})
    check("регистрация кандидата", st == 201 and reg.get("confirm_required"))
    token_c = None
    m = re.search(r"token=([\w\-]+)", reg.get("demo_confirm_url") or "")
    if check("ссылка подтверждения (демо-режим без SMTP)", m):
        st, conf, _ = call(b, "GET", f"{api}/auth/confirm?token={m.group(1)}")
        token_c = conf.get("access_token") if st == 200 else None
        check("почта подтверждена, вход выполнен", token_c)
    if not token_c:
        return finish()
    st, me, _ = call(b, "PUT", f"{api}/candidates/me", token_c, body={"full_name": "Проверка Сценария", "specialization_code": "backend", "claimed_grade": "middle",
                                                                  "skills": ["python", "postgresql", "docker"], "salary_min": 180000, "salary_max": 240000, "work_format": "remote"})
    check("профиль заполнен", st == 200, f"навыки: {', '.join(s['skill'] for s in me.get('skills', []))}" if st == 200 else str(me)[:120])
    st, _, _ = call(b, "POST", f"{api}/candidates/me/consents", token_c, body={"processing": True, "publication": True})
    st2, priv, _ = call(b, "PUT", f"{api}/candidates/me/privacy", token_c, body={"visible_to_employers": True})
    check("согласия и видимость работодателям", st == 200 and st2 == 200 and priv.get("visible_to_employers"))

    st, s, _ = call(b, "POST", f"{api}/tests/sessions", token_c, body={"specialization_code": "backend", "claimed_grade": "middle", "declared_skills": ["python", "postgresql", "docker"]})
    if check("тест начат", st == 201, f"заданий в блоке: {len(s.get('items', []))}" if st == 201 else str(s)[:160]):
        answered = set()
        for _ in range(6):
            for it in s["items"]:
                if it["id"] in answered:
                    continue
                call(b, "POST", f"{api}/tests/sessions/{s['id']}/answer", token_c, body={"item_id": it["id"], "answer": "0"})
                answered.add(it["id"])
            st, s, _ = call(b, "POST", f"{api}/tests/sessions/{s['id']}/next", token_c)
            if s.get("status") == "finished":
                break
        r = s.get("result") or {}
        check("тест завершён, грейд выставлен", s.get("status") == "finished" and r.get("result_grade"),
              f"заданий {len(answered)}, грейд {r.get('result_grade')}, θ = {r.get('theta')}, решение {r.get('decision')}")

    st, ls, _ = call(b, "GET", f"{api}/fsp/link/start", token_c)
    if check("ФСП ID: начало входа", st == 200 and ls.get("redirect_url")):
        url = ls["redirect_url"]
        state = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["state"][0]
        redirect_uri = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["redirect_uri"][0]
        page_path = url[url.index("/api/"):] if "/api/" in url else url
        st, page, _ = call(b, "GET", page_path)
        ids = re.findall(r"FSP-\d+", page if isinstance(page, str) else "")
        m_action = re.search(r'<form method="post" action="([^"]+)"', page if isinstance(page, str) else "")
        action_path = urllib.parse.urlparse(urllib.parse.urljoin(b.rstrip("/") + page_path, m_action.group(1))).path if m_action else ""
        check("ФСП ID: форма входа отправляется на верный адрес (как в браузере)", action_path.endswith("/api/v1/fsp/mock/authorize"), action_path)
        linked = False
        for fid in ids[:15]:
            st, _, hdr = call(b, "POST", action_path or f"{api}/fsp/mock/authorize", form={"state": state, "redirect_uri": redirect_uri, "fsp_id": fid}, follow=False)
            loc = hdr.get("location") or hdr.get("Location") or ""
            if st == 303 and loc:
                st2, _, hdr2 = call(b, "GET", loc[loc.index("/api/"):] if "/api/" in loc else loc, follow=False)
                loc2 = hdr2.get("location") or hdr2.get("Location") or ""
                if "fsp=linked" in loc2:
                    linked = True
                    break
        check("ФСП ID связан у издателя-заглушки", linked, f"участников на странице входа: {len(ids)}")
        st, acts, _ = call(b, "GET", f"{api}/candidates/me/achievements", token_c)
        check("достижения импортированы с уровнем «подтверждено источником»", st == 200 and acts and all(a["trust_level"] == "source" for a in acts),
              f"{len(acts) if isinstance(acts, list) else 0} записей")

    # работодатель
    st, lg, _ = call(b, "POST", f"{api}/auth/login", body={"email": args.employer, "password": args.password})
    token_e = lg.get("access_token") if st == 200 else None
    if not check("вход демо-работодателя", token_e):
        return finish()
    st, nd, _ = call(b, "POST", f"{api}/needs", token_e, body={"title": "Проверка: бэкенд в платежи", "text": "Ищем middle бэкенд-разработчика: Python, FastAPI, PostgreSQL, Docker, Kafka. 200–280 тыс., удалёнка.", "work_format": "remote"})
    need = nd.get("need", {}) if st == 201 else {}
    check("потребность разобрана из текста", st == 201 and need.get("grade") == "middle" and "python" in need.get("stack", []),
          f"{need.get('specialization_code')} / {need.get('grade')} / {', '.join(need.get('stack', []))} / {need.get('salary_min')}–{need.get('salary_max')}")
    st, sel, _ = call(b, "POST", f"{api}/needs/{need.get('id')}/selection", token_e, body={})
    v1 = (sel.get("versions") or [{}])[0] if st == 201 else {}
    res = v1.get("results") or []
    check("подборка с обоснованием", st == 201 and res and res[0].get("explanation") and "contacts" not in res[0],
          f"кандидатов {len(res)}, лучший {round(res[0]['score'] * 100) if res else '—'} из 100" if res else str(sel)[:120])
    if res:
        st, sel2, _ = call(b, "POST", f"{api}/selections/{sel['id']}/refine", token_e, body={"filters": {"grades": ["middle"]}})
        check("уточнение подборки сохраняет версии", st in (200, 201) and len(sel2.get("versions", [])) == 2)
    st, mine, _ = call(b, "GET", f"{api}/candidates/me", token_c)
    cid = mine.get("id")
    st, inv, _ = call(b, "POST", f"{api}/invitations", token_e, body={"candidate_id": cid, "message": "Проверка сценария: приглашаем на собеседование",
                                                                     "salary_min": 200000, "salary_max": 280000, "contact_method": "почта hr@example.org"})
    check("приглашение с зарплатой отправлено", st == 201 and inv.get("status") == "sent" and "contacts" not in inv, str(inv)[:120] if st != 201 else "")
    if st == 201:
        st, invs, _ = call(b, "GET", f"{api}/candidates/me/invitations", token_c)
        check("кандидат видит приглашение и вилку", st == 200 and any(i["id"] == inv["id"] and i["salary_min"] == 200000 for i in invs))
        call(b, "POST", f"{api}/invitations/{inv['id']}/view", token_c)
        st, rsp, _ = call(b, "POST", f"{api}/invitations/{inv['id']}/respond", token_c, body={"decision": "accept"})
        check("кандидат принял приглашение", st == 200 and rsp.get("status") == "accepted")
        st, card, _ = call(b, "GET", f"{api}/candidates/{cid}/card", token_e)
        check("контакты открыты пригласившему работодателю", st == 200 and card.get("contacts_unlocked") and card.get("contacts", {}).get("email") == email)
        e2 = f"smoke-emp{stamp}@fsp-demo.ru"
        st, reg2, _ = call(b, "POST", f"{api}/auth/register", body={"email": e2, "password": "password123", "role": "employer"})
        m2 = re.search(r"token=([\w\-]+)", reg2.get("demo_confirm_url") or "")
        st, conf2, _ = call(b, "GET", f"{api}/auth/confirm?token={m2.group(1)}") if m2 else (0, {}, {})
        st, card2, _ = call(b, "GET", f"{api}/candidates/{cid}/card", conf2.get("access_token"))
        check("другому работодателю контакты закрыты", st == 200 and not card2.get("contacts_unlocked") and "contacts" not in card2)
    st, _, _ = call(b, "GET", f"{api}/candidates/search", token_c)
    check("кандидату закрыт кабинет работодателя (403)", st == 403)
    st, vac, _ = call(b, "POST", f"{api}/vacancies", token_e, body={"title": "Проверка: аналитик данных", "description": "SQL, Python, pandas", "specialization_code": "data",
                                                                    "grade": "middle", "salary_min": 150000, "salary_max": 200000})
    if check("вакансия опубликована", st == 201, ", ".join(vac.get("stack", [])) if st == 201 else str(vac)[:100]):
        st, _, _ = call(b, "POST", f"{api}/vacancies/{vac['id']}/apply", token_c, body={"message": "Проверка отклика"})
        check("классический отклик кандидата", st == 201)
    return finish()


def finish():
    bad = [n for n, ok, _ in results if not ok]
    print(f"\nитого: {len(results) - len(bad)} из {len(results)} шагов прошли" + (f"; не прошли: {', '.join(bad)}" if bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
