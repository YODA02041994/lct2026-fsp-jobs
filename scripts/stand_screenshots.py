#!/usr/bin/env python3
"""Снимки экранов «Карьеры ФСП» для презентации и документации.

Запускает Google Chrome без окна, через протокол DevTools открывает страницы локально запущенного
стенда и сохраняет PNG 1440×900 в docs/screens/ (рядом — уменьшенные JPEG для просмотра).
Данные для «живых» экранов (подборка, приглашения, сеанс теста, новая потребность) создаются через API
и форму интерфейса. Повторный запуск не дублирует подборку и приглашения; новая потребность и сеанс
теста создаются каждый раз (после смены грейда тест 90 дней недоступен — тогда снимаются только
результат и история по последнему сеансу).

Подготовка (отдельная база, чтобы не трогать рабочую):
    cd backend && FSP_DATABASE_URL=sqlite:////tmp/fsp_screens.db FSP_SECRET_KEY=screens ../.venv/bin/python -m app.seed
    FSP_DATABASE_URL=sqlite:////tmp/fsp_screens.db FSP_SECRET_KEY=screens ../.venv/bin/uvicorn app.main:app --port 8011

Запуск (системный python3 с модулем websocket-client; в .venv его нет):
    python3 scripts/stand_screenshots.py --base http://127.0.0.1:8011 --db /tmp/fsp_screens.db

Порт 8011 выбран потому, что на 8010 на этом Маке висел посторонний uvicorn со старым кодом.
Ключи ответов для автопрохождения теста читаются прямо из SQLite (--db): число верных ответов
по блокам задаётся --test-correct (по умолчанию «3,2» при заявленном Middle — тест подтверждает грейд).
Без базы задания отвечаются первым вариантом, и результат будет случайным.
"""
from __future__ import annotations

import argparse
import base64
import json
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import websocket  # websocket-client
except ImportError:  # pragma: no cover
    sys.exit("Нужен модуль websocket-client: python3 -m pip install websocket-client")

ROOT = Path(__file__).resolve().parents[1]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PASSWORD = "demo12345"                      # пароль всех демонстрационных учётных записей (backend/app/seed.py)
CANDIDATE = "candidate.demo@fsp-demo.ru"    # кандидат с историей ФСП
EMPLOYER = "employer.demo@fsp-demo.ru"      # работодатель с потребностями
OTHER_EMPLOYERS = ["employer2@fsp-demo.ru", "employer3@fsp-demo.ru"]
TOKEN_KEY, ROLE_KEY = "fsp_token", "fsp_role"   # ключи localStorage из frontend/api.js


# --- API стенда -------------------------------------------------------------------------------------------

class ApiError(RuntimeError):
    def __init__(self, status: int, text: str):
        super().__init__(f"HTTP {status}: {text}")
        self.status = status


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/") + "/api/v1"
        self.token: str | None = None

    def call(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode()
        except urllib.error.HTTPError as e:
            raise ApiError(e.code, f"{method} {path} → {e.read().decode()[:300]}") from None
        return json.loads(text) if text else None

    def login(self, email: str) -> dict:
        r = self.call("POST", "/auth/login", {"email": email, "password": PASSWORD})
        self.token = r["access_token"]
        return r


# --- Chrome через DevTools --------------------------------------------------------------------------------

class Chrome:
    def __init__(self, port: int, user_data_dir: str, width: int, height: int):
        shutil.rmtree(user_data_dir, ignore_errors=True)
        self.proc = subprocess.Popen(
            [CHROME, "--headless=new", "--disable-gpu", f"--remote-debugging-port={port}", f"--user-data-dir={user_data_dir}",
             f"--window-size={width},{height}", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        page = None
        for _ in range(150):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as r:
                    targets = json.load(r)
                page = next((t for t in targets if t.get("type") == "page"), None)
                if page:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not page:
            self.close()
            raise RuntimeError("Chrome не ответил на порту DevTools")
        self.ws = websocket.create_connection(page["webSocketDebuggerUrl"], suppress_origin=True)
        self.ws.settimeout(30)
        self.seq = 0
        self.events: list[str] = []
        self.issues: list[str] = []          # исключения, ошибки консоли и сети
        for m in ("Page.enable", "Runtime.enable", "Log.enable"):
            self.send(m)
        self.send("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})

    def send(self, method: str, params: dict | None = None) -> dict:
        self.seq += 1
        mid = self.seq
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self._on_event(msg)

    def _on_event(self, msg: dict) -> None:
        m = msg.get("method")
        p = msg.get("params", {})
        if m == "Runtime.exceptionThrown":
            d = p.get("exceptionDetails", {})
            self.issues.append("исключение: " + (d.get("exception", {}).get("description") or d.get("text", ""))[:300])
        elif m == "Runtime.consoleAPICalled" and p.get("type") in ("error", "warning"):
            text = " ".join(str(a.get("value", a.get("description", ""))) for a in p.get("args", []))
            self.issues.append(f"console.{p['type']}: {text[:300]}")
        elif m == "Log.entryAdded" and p.get("entry", {}).get("level") in ("error", "warning"):
            e = p["entry"]
            self.issues.append(f"{e.get('source')}: {e.get('text')} {e.get('url', '')}"[:300])
        elif m:
            self.events.append(m)

    def wait_event(self, name: str, timeout: float = 15) -> bool:
        if name in self.events:
            self.events.remove(name)
            return True
        self.ws.settimeout(timeout)
        end = time.time() + timeout
        try:
            while time.time() < end:
                try:
                    msg = json.loads(self.ws.recv())
                except websocket.WebSocketTimeoutException:
                    return False
                if msg.get("method") == name:
                    return True
                self._on_event(msg)
        finally:
            self.ws.settimeout(30)
        return False

    def goto(self, url: str) -> None:
        self.events.clear()
        self.send("Page.navigate", {"url": url})
        self.wait_event("Page.loadEventFired", 15)

    def eval(self, expression: str, await_promise: bool = False):
        r = self.send("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": await_promise})
        if "exceptionDetails" in r:
            raise RuntimeError("JS: " + json.dumps(r["exceptionDetails"], ensure_ascii=False)[:400])
        return r.get("result", {}).get("value")

    def settle(self, timeout: float = 10, extra: float = 0.7) -> None:
        """Дождаться, пока приложение загрузит данные: нет спиннеров и «Загрузка…», в #app есть разметка."""
        end = time.time() + timeout
        while time.time() < end:
            busy = self.eval("!!document.querySelector('.boot, .spinner') || !document.querySelector('#app *')")
            if not busy:
                break
            time.sleep(0.15)
        time.sleep(extra)

    def wait_text(self, text: str, timeout: float = 12) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self.eval(f"document.body.textContent.includes({json.dumps(text)})"):
                return True
            time.sleep(0.2)
        return False

    def click_text(self, selector: str, text: str) -> bool:
        return bool(self.eval(
            f"(() => {{ const b = [...document.querySelectorAll({json.dumps(selector)})]"
            f".find(x => x.textContent.includes({json.dumps(text)})); if (!b) return false; b.click(); return true; }})()"))

    def set_value(self, selector: str, value: str, index: int = 0) -> None:
        """Ввести значение в поле как пользователь: v-model слушает событие input. Между полями нужен тик Vue."""
        self.eval(f"(() => {{ const el = document.querySelectorAll({json.dumps(selector)})[{index}]; "
                  f"el.value = {json.dumps(value)}; el.dispatchEvent(new Event('input', {{ bubbles: true }})); return 1; }})()")
        time.sleep(0.12)

    def shot(self, path: Path, full_page: bool = False) -> None:
        params: dict = {"format": "png"}
        if full_page:
            m = self.send("Page.getLayoutMetrics")
            size = m.get("cssContentSize") or m["contentSize"]
            params.update({"captureBeyondViewport": True,
                           "clip": {"x": 0, "y": 0, "width": size["width"], "height": size["height"], "scale": 1}})
        r = self.send("Page.captureScreenshot", params)
        path.write_bytes(base64.b64decode(r["data"]))

    def close(self) -> None:
        try:
            self.send("Browser.close")
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


# --- сценарий ---------------------------------------------------------------------------------------------

class Shooter:
    def __init__(self, chrome: Chrome, base: str, out: Path):
        self.chrome, self.base, self.out = chrome, base, out
        self.manifest: list[tuple[str, str, str, list[str]]] = []

    def session(self, token: str | None, role: str | None) -> None:
        """Сменить пользователя: сначала выйти и перезагрузить приложение, потом положить токен и роль в localStorage.

        Если подменить токен на открытой странице кабинета, её запросы уйдут уже с чужим токеном (403 в журнале сервера)."""
        self.chrome.goto(self.base + "/")
        self.chrome.settle(5)                      # дать прежнему кабинету догрузиться, иначе его запросы уйдут без токена (401)
        self.chrome.eval("localStorage.clear(); 1")
        if token:
            self.chrome.goto("about:blank")
            self.chrome.goto(self.base + "/#/login")
            self.chrome.settle(5)
            self.chrome.eval(f"localStorage.setItem({TOKEN_KEY!r}, {json.dumps(token)}); localStorage.setItem({ROLE_KEY!r}, {json.dumps(role)}); 1")

    def open(self, route: str) -> None:
        # смена только hash не перезагружает страницу: идём через about:blank, чтобы store перечитал localStorage
        self.chrome.goto("about:blank")
        self.chrome.goto(self.base + "/#" + route)
        self.chrome.settle()

    def capture(self, name: str, route: str, caption: str, before=None, full_page: bool = False) -> Path:
        start = len(self.chrome.issues)
        self.open(route)
        if before:
            before()
        on_page = self.chrome.eval("[...document.querySelectorAll('.state-error, .note-err, .toast.err, .toast.warn')].map(e => e.textContent.trim()).filter(Boolean)")
        png = self.out / f"{name}.png"
        self.chrome.shot(png, full_page=full_page)
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "70", "--resampleWidth", "1200", str(png), "--out", str(png.with_suffix(".jpg"))],
                       check=True, capture_output=True)
        issues = self.chrome.issues[start:] + [f"на экране: {t[:160]}" for t in (on_page or [])]
        self.manifest.append((png.name, route, caption, issues))
        print(f"  {png.name:34s} {route:40s} {caption}" + (f"  !! {len(issues)} замеч." if issues else ""))
        return png


def prepare_employer(api: Api, candidate_id: int) -> dict:
    """Подборка по первой потребности и приглашение демо-кандидату — если их ещё нет."""
    needs = api.call("GET", "/needs")
    need = next((n for n in needs if n["specialization_code"] == "backend"), needs[0])
    sel = next((s for s in api.call("GET", "/selections") if s["need_id"] == need["id"]), None)
    if not sel:
        sel = api.call("POST", f"/needs/{need['id']}/selection", {})
    sel_full = api.call("GET", f"/selections/{sel['id']}")
    if not sel_full["versions"] or not sel_full["versions"][-1]["results"]:
        raise RuntimeError("Подборка пуста — проверьте демо-данные")
    inv = next((i for i in api.call("GET", "/employers/me/invitations") if i["candidate"]["candidate_id"] == candidate_id), None)
    if not inv:
        inv = api.call("POST", "/invitations", {
            "candidate_id": candidate_id, "salary_min": 120000, "salary_max": 150000, "contact_method": "Telegram",
            "message": "Здравствуйте! Мы строим платформу для работы с медицинскими данными и ищем фронтенд-разработчика "
                       "в команду личного кабинета пациента. Ваш подтверждённый тестом стек (Vue, TypeScript, REST) — ровно то, "
                       "что нужно. Удалённый формат, гибкий график, наставник на первые три месяца."})
    return {"need": need, "selection_id": sel["id"], "invitation": inv}


def prepare_other_invitations(base: str, candidate_id: int) -> None:
    """Ещё два приглашения от других компаний, чтобы список кандидата не был из одной строки."""
    texts = [("Электронная почта", 110000, 140000, "Приглашаем на позицию фронтенд-разработчика в продуктовую команду интернет-магазина: Vue, TypeScript, "
                                                   "REST. Гибридный формат, офис в центре, обучение за счёт компании."),
             ("Телефон", 100000, 130000, "Ищем разработчика интерфейсов для панели мониторинга перевозок. Понравилось, что технологии "
                                        "подтверждены тестом, а не только заявлены. Готовы обсуждать условия.")]
    for email, (method, lo, hi, msg) in zip(OTHER_EMPLOYERS, texts):
        api = Api(base)
        try:
            api.login(email)
        except ApiError:
            continue
        if any(i["candidate"]["candidate_id"] == candidate_id for i in api.call("GET", "/employers/me/invitations")):
            continue
        api.call("POST", "/invitations", {"candidate_id": candidate_id, "salary_min": lo, "salary_max": hi, "contact_method": method, "message": msg})


def answer_keys(db: str | None, session_id: int) -> dict[int, object]:
    if not db or not Path(db).exists():
        return {}
    con = sqlite3.connect(db)
    try:
        return {iid: json.loads(key)["answer"] for iid, key in con.execute("select id, answer_key from test_item where session_id = ?", (session_id,))}
    finally:
        con.close()


def wrong_answer(item: dict, key=None):
    """Заведомо неверный ответ в формате задания (а без ключа — просто первый вариант)."""
    fmt = item["payload"].get("format")
    if fmt == "multichoice":
        return [0] if key != [0] else [1]
    if fmt == "choice":
        return 0 if key != 0 else 1
    return "0" if str(key).strip() != "0" else "1"


def finish_test(api: Api, sess: dict, db: str | None, correct_per_block: list[int]) -> dict:
    """Ответить на все задания сеанса через API и завершить его.

    С ключами из базы в каждом блоке первые N заданий отвечаются верно, остальные — неверно (N из --test-correct)."""
    while sess["status"] == "active":
        keys = answer_keys(db, sess["id"])
        block = sorted((it for it in sess["items"] if it["block_no"] == sess["current_block"] and not it["answered"]), key=lambda x: x["order_no"])
        n_ok = correct_per_block[min(sess["current_block"] - 1, len(correct_per_block) - 1)] if keys else 0
        for i, it in enumerate(block):
            key = keys.get(it["id"])
            answer = key if (key is not None and i < n_ok) else wrong_answer(it, key)
            api.call("POST", f"/tests/sessions/{sess['id']}/answer", {"item_id": it["id"], "answer": answer})
        sess = api.call("POST", f"/tests/sessions/{sess['id']}/next")
    return sess


NEED_TITLE = "Бэкенд-разработчик в команду биллинга"
NEED_TEXT = ("Ищем бэкенд-разработчика от 2 лет опыта в команду биллинга. Пишем сервисы расчёта и выставления счетов, "
             "обрабатываем события из Kafka и храним всё в PostgreSQL. Стек: Python, FastAPI, PostgreSQL, Docker, Kafka, Redis. "
             "Работаем удалённо, созвоны два раза в неделю. Зарплата 180–240 тыс. ₽ до вычета налогов.")


def fill_need_form(chrome: Chrome) -> None:
    chrome.set_value('input[placeholder^="например"]', NEED_TITLE)
    chrome.set_value("form textarea", NEED_TEXT)
    chrome.set_value(".money-range input", "180000", 0)
    chrome.set_value(".money-range input", "240000", 1)
    time.sleep(0.3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8011", help="адрес локального стенда")
    ap.add_argument("--db", default="/tmp/fsp_screens.db", help="SQLite стенда — ключи ответов для автопрохождения теста")
    ap.add_argument("--out", default=str(ROOT / "docs" / "screens"), help="куда класть снимки")
    ap.add_argument("--devtools-port", type=int, default=9333)
    ap.add_argument("--user-data-dir", default="/tmp/chrome-screens")
    ap.add_argument("--size", default="1440x900")
    ap.add_argument("--test-claimed", default="middle", choices=["junior", "middle", "senior", "lead"], help="заявленный грейд в тесте")
    ap.add_argument("--test-correct", default="3,2", help="верных ответов по блокам, например «3,2» или «5,5»")
    args = ap.parse_args()
    width, height = (int(x) for x in args.size.lower().split("x"))
    correct_per_block = [int(x) for x in args.test_correct.split(",")]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("[0-9][0-9]_*.png")) + list(out.glob("[0-9][0-9]_*.jpg")):
        old.unlink()

    with urllib.request.urlopen(args.base.rstrip("/") + "/api/health", timeout=5) as r:
        print("стенд:", r.read().decode())

    # --- данные через API ---
    cand = Api(args.base)
    cand.login(CANDIDATE)
    me = cand.call("GET", "/candidates/me")
    emp = Api(args.base)
    emp.login(EMPLOYER)
    prepared = prepare_employer(emp, me["id"])
    prepare_other_invitations(args.base, me["id"])
    inv_id = prepared["invitation"]["id"]
    sel_id = prepared["selection_id"]
    print(f"кандидат id={me['id']} ({me['alias']}), подборка {sel_id} по потребности «{prepared['need']['title']}», приглашение {inv_id}")

    chrome = Chrome(args.devtools_port, args.user_data_dir, width, height)
    s = Shooter(chrome, args.base, out)
    try:
        # (а) экран входа
        s.session(None, None)
        s.capture("01_login", "/login", "Экран входа с демонстрационными учётными записями")

        # (б) кабинет кандидата — до теста: завершение теста пересчитывает подтверждённые навыки и может сменить грейд
        s.session(cand.token, "candidate")
        s.capture("02_candidate_profile", "/candidate/profile", "Профиль кандидата: основное, категория, ФСП ID")
        s.capture("03_candidate_profile_full", "/candidate/profile", "Профиль целиком (вся страница): стек с отметками «подтверждено тестом»", full_page=True)
        s.capture("04_candidate_skills", "/candidate/skills", "Навыки: подтверждённые тестом и заявленные")
        s.capture("05_candidate_achievements", "/candidate/achievements", "Достижения ФСП с уровнем доверия (подтверждено источником)")

        # (ж) приглашение: карточка с кнопками «Принять / Отклонить», затем принятие через API
        s.capture("06_candidate_invitation", f"/candidate/invitations/{inv_id}", "Приглашение работодателя: зарплата и компания видны до согласия")
        inv_now = cand.call("GET", "/candidates/me/invitations")
        if next(i for i in inv_now if i["id"] == inv_id)["status"] in ("sent", "viewed"):
            cand.call("POST", f"/invitations/{inv_id}/respond", {"decision": "accept"})
        s.capture("07_candidate_invitations", "/candidate/invitations", "Список приглашений кандидата со статусами")
        s.capture("08_candidate_overview", "/candidate", "Обзор кабинета кандидата: категория, тест, приглашения, «что дальше»")

        # (д) кабинет работодателя
        s.session(emp.token, "employer")
        s.capture("09_employer_overview", "/employer", "Обзор кабинета работодателя")
        s.capture("10_employer_needs", "/employer/needs", "Потребности и подборки")
        s.capture("11_employer_selection", f"/employer/selections/{sel_id}", "Подборка по потребности: категории, карточки, слагаемые оценки и обоснование")
        s.capture("12_employer_bank", "/employer/bank", "Банк кандидатов")

        # (е) новая потребность: заполненная форма и распознанные поля после сохранения
        s.capture("13_employer_need_form", "/employer/needs/new", "Создание потребности: описание свободным текстом", before=lambda: fill_need_form(chrome))

        def submit_need():
            fill_need_form(chrome)
            if not chrome.click_text("form button.btn-primary", "Сохранить потребность"):
                raise RuntimeError("Кнопка «Сохранить потребность» не найдена")
            if not chrome.wait_text("Потребность сохранена"):
                err = chrome.eval("[...document.querySelectorAll('.note-err, .field-error')].map(e => e.textContent.trim()).join('; ')")
                raise RuntimeError(f"Потребность не сохранилась: {err or 'форма не отправилась'}")
            chrome.settle()
        s.capture("14_employer_need_parsed", "/employer/needs/new", "Потребность сохранена: распознанные специализация, грейд и технологии", before=submit_need)

        # (ж) контакты открыты после принятия приглашения
        s.capture("15_employer_invitations", "/employer/invitations", "Приглашения работодателя: контакты кандидата после принятия")

        # (в) тест: сеанс через API, страница теста, кнопка «Продолжить тест»
        s.session(cand.token, "candidate")
        sess = None
        try:
            sess = cand.call("POST", "/tests/sessions", {"specialization_code": me["specialization_code"] or "frontend",
                                                          "claimed_grade": args.test_claimed,
                                                          "declared_skills": [k["skill"] for k in me["skills"]]})
        except ApiError as e:
            if e.status != 409:
                raise
            print("новый сеанс теста недоступен (смена грейда раз в 90 дней) — снимаю последний завершённый:", e)

        if sess and sess["status"] == "active":
            def resume():
                if not chrome.click_text("button", "Продолжить тест"):
                    raise RuntimeError("Кнопка «Продолжить тест» не найдена")
                chrome.settle()
                time.sleep(0.8)
            s.capture("16_test_question", "/candidate/test", "Тест на грейд: задание с таймером и индикатором прогресса", before=resume)
            sess = finish_test(cand, sess, args.db, correct_per_block)
            res = sess.get("result") or {}
            print(f"тест завершён: {res.get('result_grade')} / {res.get('decision')}, верно {res.get('correct_total')} из {res.get('items_total')}")
        if not sess:
            finished = [x for x in cand.call("GET", "/tests/sessions") if x["status"] == "finished"]
            sess = finished[0] if finished else None

        # (г) результат и история
        if sess:
            s.capture("17_test_result", f"/candidate/test/sessions/{sess['id']}", "Результат теста: грейд, шкала умения θ, подтверждение по технологиям")
        s.capture("18_test_history", "/candidate/test/history", "История тестов кандидата")
    finally:
        chrome.close()

    print("\nСнимки:", out)
    problems = [(f, r, i) for f, r, _, i in s.manifest if i]
    if problems:
        print("\nЗамечания по экранам:")
        for f, r, issues in problems:
            for i in issues:
                print(f"  {f} ({r}): {i}")
    else:
        print("Ошибок в консоли и на экранах не замечено.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
