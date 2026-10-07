#!/usr/bin/env python3
"""Демонстрационное видео «Карьеры ФСП»: сквозной сценарий ТЗ, записанный с настоящего интерфейса.

Chrome без окна снимает поток кадров (Page.startScreencast), ввод идёт посимвольно, клики — событиями мыши по кнопкам.
Переключения между учётными записями вырезаются из записи. ffmpeg собирает видео с подписями шагов, заставкой и
финальной карточкой. Помощники для Chrome и API — из scripts/stand_screenshots.py.

Подготовка (отдельная база, чтобы не трогать рабочую):
    cd backend && rm -f /tmp/fsp_video.db && FSP_DATABASE_URL=sqlite:////tmp/fsp_video.db FSP_SECRET_KEY=video ../.venv/bin/python -m app.seed
    FSP_DATABASE_URL=sqlite:////tmp/fsp_video.db FSP_SECRET_KEY=video FSP_PUBLIC_URL=http://localhost:8013 \\
        ../.venv/bin/uvicorn app.main:app --port 8013

Запуск (системный python3 с websocket-client и Pillow):
    python3 scripts/record_demo.py --base http://localhost:8013 --db /tmp/fsp_video.db
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stand_screenshots as ss  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FONT_BOLD = ROOT / "backend" / "app" / "assets" / "Montserrat-Bold.ttf"
FONT_REG = ROOT / "backend" / "app" / "assets" / "Montserrat-Regular.ttf"
FFMPEG = shutil.which("ffmpeg") or "/opt/anaconda3/bin/ffmpeg"
W, H = 1440, 900

NEED_TITLE = "Бэкенд-разработчик в команду платежей"
NEED_TEXT = ("Ищем middle бэкенд-разработчика в команду платежей: Python, FastAPI, PostgreSQL, Docker, Kafka. "
             "Удалёнка, 200–280 тыс.")
INVITE_TEXT = "Здравствуйте! Приглашаем в команду платежей: сервисы расчётов на Python и FastAPI. Удалённо, наставник на старте."


class Recorder(ss.Chrome):
    """Chrome с записью потока кадров и подписями шагов; время — «чистое», без вырезанных пауз."""

    def __init__(self, port: int, user_data_dir: str, frames: Path):
        super().__init__(port, user_data_dir, W, H)
        self.frames_dir = frames
        self.frames: list[tuple[float, Path]] = []
        self.captions: list[tuple[float, str]] = []
        self.recording = False
        self.paused_total = 0.0
        self.pause_started = time.time()
        self.n = 0

    # --- запись ---
    def now(self) -> float:
        return time.time() - self.paused_total

    def _save_frame(self, data_b64: str) -> None:
        self.n += 1
        path = self.frames_dir / f"f_{self.n:05d}.jpg"
        path.write_bytes(base64.b64decode(data_b64))
        self.frames.append((self.now(), path))

    def _on_event(self, msg: dict) -> None:
        if msg.get("method") == "Page.screencastFrame":
            p = msg["params"]
            if self.recording:
                self._save_frame(p["data"])
            self.seq += 1
            self.ws.send(json.dumps({"id": 10_000_000 + self.seq, "method": "Page.screencastFrameAck", "params": {"sessionId": p["sessionId"]}}))
            return
        super()._on_event(msg)

    def snapshot_frame(self) -> None:
        """Кадр текущего состояния — на стыках после вырезанных пауз, где поток кадров молчит."""
        r = self.send("Page.captureScreenshot", {"format": "jpeg", "quality": 85})
        self._save_frame(r["data"])

    def start(self) -> None:
        self.paused_total += time.time() - self.pause_started
        self.recording = True
        self.send("Page.startScreencast", {"format": "jpeg", "quality": 85, "maxWidth": W, "maxHeight": H, "everyNthFrame": 1})
        self.snapshot_frame()

    def pause(self) -> None:
        self.snapshot_frame()
        self.send("Page.stopScreencast")
        self.recording = False
        self.pause_started = time.time()

    def caption(self, text: str) -> None:
        self.captions.append((self.now(), text))
        print(f"  [{self.now() - self.captions[0][0] if self.captions else 0:6.1f} с] {text}")

    def pump(self, seconds: float) -> None:
        """Ждать, продолжая принимать кадры (вместо time.sleep)."""
        end = time.time() + seconds
        self.ws.settimeout(0.05)
        try:
            while time.time() < end:
                try:
                    msg = json.loads(self.ws.recv())
                except ss.websocket.WebSocketTimeoutException:
                    continue
                self._on_event(msg)
        finally:
            self.ws.settimeout(30)

    # --- действия как у человека ---
    def locate(self, selector: str, text: str | None = None, nth: int = 0):
        js = (f"(() => {{ let els = [...document.querySelectorAll({json.dumps(selector)})]"
              + (f".filter(x => x.textContent.includes({json.dumps(text)}))" if text else "")
              + f"; const el = els[{nth}]; if (!el) return null; el.scrollIntoView({{block: 'center', behavior: 'instant'}});"
              f" const r = el.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }})()")
        return self.eval(js)

    def click(self, selector: str, text: str | None = None, nth: int = 0, wait: float = 0.6) -> None:
        pt = self.locate(selector, text, nth)
        if not pt:
            raise RuntimeError(f"не найден элемент {selector!r} с текстом {text!r}")
        self.pump(0.25)
        x, y = pt
        for t in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1})
        self.pump(wait)

    def type(self, selector: str, text: str, nth: int = 0, delay: float = 0.03) -> None:
        self.eval(f"(() => {{ const el = document.querySelectorAll({json.dumps(selector)})[{nth}]; el.scrollIntoView({{block: 'center'}});"
                  f" el.focus(); if (el.select) el.select(); return 1; }})()")
        for ch in text:
            self.send("Input.insertText", {"text": ch})
            self.pump(delay)
        self.pump(0.3)

    def scroll(self, dy: int, steps: int = 20) -> None:
        for _ in range(steps):
            self.eval(f"window.scrollBy(0, {dy / steps}); 1")
            self.pump(0.03)
        self.pump(0.4)

    def hash(self, route: str) -> None:
        self.eval(f"location.hash = {json.dumps('#' + route)}; 1")
        self.pump(0.3)
        self.settle(10, 0.4)

    def wait_for(self, text: str, timeout: float = 15) -> None:
        end = time.time() + timeout
        while time.time() < end:
            if self.eval(f"document.body.textContent.includes({json.dumps(text)})"):
                return
            self.pump(0.2)
        raise RuntimeError(f"на экране не появилось: {text!r}")


def db_one(db: str, sql: str, args=()):
    con = sqlite3.connect(db)
    try:
        return con.execute(sql, args).fetchone()
    finally:
        con.close()


def login_token(base: str, email: str, password: str = ss.PASSWORD) -> str:
    api = ss.Api(base)
    r = api.call("POST", "/auth/login", {"email": email, "password": password})
    return r["access_token"]


def switch_user(rec: Recorder, base: str, token: str | None, role: str | None, route: str) -> None:
    """Сменить пользователя вне записи: выйти, положить токен, открыть нужный экран."""
    rec.goto(base + "/")
    rec.settle(5)
    rec.eval("localStorage.clear(); 1")
    if token:
        rec.goto("about:blank")
        rec.goto(base + "/#/login")
        rec.settle(5)
        rec.eval(f"localStorage.setItem({ss.TOKEN_KEY!r}, {json.dumps(token)}); localStorage.setItem({ss.ROLE_KEY!r}, {json.dumps(role)}); 1")
    rec.goto("about:blank")
    rec.goto(base + "/#" + route)
    rec.settle(10, 0.8)


def answer_in_ui(rec: Recorder, item: dict, key, correct: bool) -> None:
    fmt = item["payload"].get("format")
    ans = key if correct else ss.wrong_answer(item, key)
    if fmt == "exact":
        rec.type(".test-item input[type=text]", str(ans), delay=0.06)
    elif fmt == "choice":
        rec.click(".test-item label.option", nth=int(ans), wait=0.4)
    else:
        for i in (ans if isinstance(ans, list) else [ans]):
            rec.click(".test-item label.option", nth=int(i), wait=0.3)
    rec.pump(1.2)
    rec.click("form button[type=submit]", "Ответить", wait=1.0)
    rec.settle(6, 0.3)
    if rec.eval("!!document.querySelector('.note-pink button')"):
        rec.pump(1.5)


def card_image(path: Path, title: str, subtitle: str, lines: list[str]) -> None:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), (49, 15, 83))
    d = ImageDraw.Draw(img)
    d.rectangle([110, 300, 126, 420], fill=(255, 0, 83))
    d.text((160, 290), title, font=ImageFont.truetype(str(FONT_BOLD), 68), fill="white")
    d.text((160, 385), subtitle, font=ImageFont.truetype(str(FONT_REG), 32), fill=(255, 214, 228))
    y = 520
    for line in lines:
        d.text((160, y), line, font=ImageFont.truetype(str(FONT_REG), 28), fill=(220, 214, 240))
        y += 48
    img.save(path, quality=95)


def ffmpeg(*args: str) -> None:
    r = subprocess.run([FFMPEG, "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg: " + r.stderr[-1500:])


def assemble(rec: Recorder, work: Path, out: Path) -> None:
    frames = sorted(rec.frames, key=lambda x: x[0])
    t0 = frames[0][0]
    lst = work / "frames.txt"
    with lst.open("w") as f:
        for i, (t, p) in enumerate(frames):
            nxt = frames[i + 1][0] if i + 1 < len(frames) else t + 1.5
            f.write(f"file '{p}'\nduration {max(nxt - t, 1 / 60):.4f}\n")
        f.write(f"file '{frames[-1][1]}'\n")
    main_raw = work / "main_raw.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-vf", f"scale={W}:{H},format=yuv420p", "-r", "30", "-fps_mode", "cfr",
           "-c:v", "libx264", "-preset", "medium", "-crf", "23", str(main_raw))
    total = frames[-1][0] - t0 + 1.5
    # подписи: каждая — до начала следующей
    filters = []
    caps = [(t - t0, txt) for t, txt in rec.captions]
    for i, (start, txt) in enumerate(caps):
        end = caps[i + 1][0] if i + 1 < len(caps) else total
        tf = work / f"cap_{i:02d}.txt"
        tf.write_text(txt, encoding="utf-8")
        filters.append(f"drawtext=fontfile='{FONT_BOLD}':textfile='{tf}':fontsize=30:fontcolor=white:box=1:boxcolor=0x1C1D22@0.78:boxborderw=18:"
                       f"x=(w-text_w)/2:y=h-text_h-44:enable='between(t,{max(start, 0):.2f},{end:.2f})'")
    main_cap = work / "main_cap.mp4"
    ffmpeg("-i", str(main_raw), "-vf", ",".join(filters), "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", str(main_cap))
    # заставка и финал
    title_png, end_png = work / "title.png", work / "end.png"
    card_image(title_png, "Карьера ФСП — найм наоборот", "Работодатель находит кандидата с грейдом, подтверждённым тестом",
               ["Сквозной сценарий: потребность → подборка → приглашение →", "регистрация и тест кандидата → ФСП ID → согласие → контакты"])
    card_image(end_png, "Карьера ФСП", "Тест из заданий с параметрами · подбор с объяснением · ФСП ID",
               ["Прототип: https://docsemenov.ru/fsp/", "Код: github.com/YODA02041994/lct2026-fsp-jobs", "Команда «Пироговский Университет», ЛЦТ-2026, спецтрек ФСП"])
    segs = []
    for png, dur, name in ((title_png, 3.5, "title.mp4"), (end_png, 4.5, "end.mp4")):
        seg = work / name
        ffmpeg("-loop", "1", "-t", str(dur), "-i", str(png), "-vf", f"scale={W}:{H},format=yuv420p,fade=t=in:st=0:d=0.4,fade=t=out:st={dur - 0.4}:d=0.4",
               "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(seg))
        segs.append(seg)
    concat = work / "concat.txt"
    concat.write_text(f"file '{segs[0]}'\nfile '{main_cap}'\nfile '{segs[1]}'\n")
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(out))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://localhost:8013")
    ap.add_argument("--db", default="/tmp/fsp_video.db")
    ap.add_argument("--out", default=str(ROOT / "docs" / "build" / "Карьера_ФСП_демо.mp4"))
    ap.add_argument("--work", default=str(ROOT / "docs" / "build" / "demo"))
    ap.add_argument("--devtools-port", type=int, default=9344)
    args = ap.parse_args()
    base = args.base.rstrip("/")
    work = Path(args.work)
    shutil.rmtree(work, ignore_errors=True)
    (work / "frames").mkdir(parents=True)
    with ss.urllib.request.urlopen(base + "/api/health", timeout=5) as r:
        print("стенд:", r.read().decode())

    emp_token = login_token(base, ss.EMPLOYER)
    rec = Recorder(args.devtools_port, "/tmp/chrome-video", work / "frames")
    stamp = int(time.time())
    try:
        # 1. Работодатель: вход, потребность текстом, подборка, уточнение, приглашение
        switch_user(rec, base, None, None, "/login")
        rec.start()
        rec.caption("Работодатель входит в кабинет")
        rec.type('input[type=email]', ss.EMPLOYER)
        rec.type('input[type=password]', ss.PASSWORD, delay=0.02)
        rec.click("form button.btn-primary", "Войти", wait=1.0)
        rec.settle(10, 1.0)
        rec.caption("Работодатель описывает потребность обычным текстом")
        rec.hash("/employer/needs/new")
        rec.type('input[placeholder^="например"]', NEED_TITLE, delay=0.02)
        rec.type("form textarea", NEED_TEXT, delay=0.018)
        rec.type(".money-range input", "200000", nth=0, delay=0.05)
        rec.type(".money-range input", "280000", nth=1, delay=0.05)
        rec.click("form button.btn-primary", "Сохранить потребность", wait=0.5)
        rec.wait_for("Потребность сохранена")
        rec.settle(6, 0.3)
        rec.caption("Поля распознаны из текста: специализация, грейд, стек, зарплата")
        rec.scroll(260)
        rec.pump(3.0)
        rec.click("button", "Собрать подборку", wait=0.8)
        rec.wait_for("Подборка:")
        rec.settle(10, 0.6)
        rec.caption("Подборка по категориям: оценка — вероятность, что кандидат подходит")
        rec.pump(3.5)
        rec.scroll(330)
        rec.caption("Шесть слагаемых и обоснование: почему кандидат в подборке")
        rec.pump(4.5)
        rec.scroll(-330)
        rec.click("button", "Уточнить фильтры", wait=0.8)
        rec.caption("Уточнение фильтров создаёт новую версию, прежняя сохраняется")
        if rec.locate("button.chip-toggle.on", "Junior"):
            rec.click("button.chip-toggle", "Junior", wait=0.6)
        rec.click("button", "Собрать новую версию", wait=0.8)
        rec.wait_for("Версия 2")
        rec.settle(8, 0.5)
        rec.pump(2.5)
        rec.click("button", "Пригласить", wait=0.8)
        rec.caption("Работодатель сам приглашает кандидата и сразу называет зарплату «от–до»")
        rec.type(".modal textarea", INVITE_TEXT, delay=0.015)
        rec.eval("(() => { const xs = document.querySelectorAll('.modal .money-range input'); "
                 "[['200000', 0], ['280000', 1]].forEach(([v, i]) => { xs[i].value = v; xs[i].dispatchEvent(new Event('input', {bubbles: true})); }); return 1; })()")
        rec.pump(1.2)
        rec.click(".modal button.btn-primary", None, wait=1.0)
        rec.pump(2.0)
        rec.pause()

        # кому ушло приглашение — его откроем в шаге 4
        emp = ss.Api(base); emp.token = emp_token
        inv = sorted(emp.call("GET", "/employers/me/invitations"), key=lambda i: i["id"])[-1]
        invited_cid = inv["candidate"]["candidate_id"]
        invited_email = db_one(args.db, "select u.email from candidate c join user u on u.id = c.user_id where c.id = ?", (invited_cid,))[0]

        # 2. Новый кандидат: регистрация и подтверждение почты
        switch_user(rec, base, None, None, "/register")
        rec.start()
        rec.caption("Кандидат регистрируется сам — почта подтверждается по ссылке")
        email = f"video.candidate{stamp % 10000}@fsp-demo.ru"
        rec.type("form input[type=email]", email)
        rec.type("form input[type=password]", "password123", nth=0, delay=0.02)
        rec.type("form input[type=password]", "password123", nth=1, delay=0.02)
        rec.click("label.check", None, wait=0.4)
        rec.click("form button.btn-primary", "Зарегистрироваться", wait=1.0)
        rec.wait_for("Перейти по ссылке из письма")
        rec.pump(1.5)
        rec.click("button", "Перейти по ссылке из письма", wait=1.0)
        rec.settle(10, 1.0)
        rec.pump(1.5)
        rec.pause()

        # профиль через API (опрос показан на снимках), затем тест в интерфейсе
        cand_token = rec.eval(f"localStorage.getItem({ss.TOKEN_KEY!r})")
        cand = ss.Api(base); cand.token = cand_token
        cand.call("PUT", "/candidates/me", {"full_name": "Илья Демонстрационный", "specialization_code": "backend", "claimed_grade": "middle",
                                            "skills": ["python", "fastapi", "postgresql", "docker"], "salary_min": 200000, "salary_max": 260000,
                                            "work_format": "remote", "city": "Москва"})
        cand.call("POST", "/candidates/me/consents", {"processing": True, "publication": True})
        rec.hash("/candidate/test")
        rec.start()
        rec.caption("Тест на грейд: специализация и заявленный грейд")
        rec.click("label.choice-card", "Бэкенд", wait=0.5)
        rec.click("button.btn-primary", "Дальше", wait=0.7)
        rec.click("label.choice-card", "Middle", wait=0.5)
        rec.click("button.btn-primary", "Дальше", wait=0.7)
        rec.pump(1.5)
        rec.click("button.btn-primary", "Начать тест", wait=1.0)
        rec.wait_for("Задание 1 из")
        rec.settle(6, 0.5)
        rec.caption("Задания с параметрами: у каждого кандидата свои числа и данные")
        sess = next(s for s in cand.call("GET", "/tests/sessions") if s["status"] == "active")
        sess = cand.call("GET", f"/tests/sessions/{sess['id']}")
        keys = ss.answer_keys(args.db, sess["id"])
        block1 = sorted((it for it in sess["items"] if it["block_no"] == 1), key=lambda x: x["order_no"])
        for i, it in enumerate(block1[:3]):
            rec.pump(2.0 if i == 0 else 1.2)
            answer_in_ui(rec, it, keys.get(it["id"]), correct=(i != 1))
        rec.pause()
        # остальное — через API (в записи не показываем), результат — в интерфейсе
        sess = cand.call("GET", f"/tests/sessions/{sess['id']}")
        sess = ss.finish_test(cand, sess, args.db, [4, 3])
        rec.hash(f"/candidate/test/sessions/{sess['id']}")
        rec.start()
        rec.caption("Грейд подтверждён тестом: оценка умения с интервалом и разрез по технологиям")
        rec.pump(3.5)
        rec.scroll(380)
        rec.pump(3.0)
        rec.pause()

        # ФСП ID: издатель-заглушка с тем же протоколом, что Keycloak
        rec.hash("/candidate/achievements")
        rec.start()
        rec.caption("ФСП ID: кандидат связывает профиль через вход по OpenID Connect")
        rec.pump(1.5)
        rec.click("button.btn-primary", "Связать с ФСП ID", wait=1.5)
        rec.wait_for("Войти и разрешить доступ", timeout=15)
        fsp_free = db_one(args.db, "select p.fsp_id from fsp_participant p where p.rank is not null and p.fsp_id not in "
                                   "(select fsp_id from candidate where fsp_id is not null) order by p.fsp_id limit 1")[0]
        on_page = rec.eval(f"!!document.querySelector('input[value={json.dumps(fsp_free)}]')")
        rec.pump(1.5)
        if on_page:
            rec.click(f"input[value={json.dumps(fsp_free)}]", None, wait=0.5)
        else:
            rec.type('input[name="custom_id"]', fsp_free, delay=0.05)
        rec.click("button[type=submit]", None, wait=1.5)
        rec.settle(10, 1.0)
        rec.wait_for("подтверждено источником", timeout=15)
        rec.caption("Достижения из реестра ФСП — с пометкой «подтверждено источником»")
        rec.pump(4.0)
        rec.pause()

        # 3. Приглашённый кандидат принимает приглашение
        switch_user(rec, base, login_token(base, invited_email), "candidate", f"/candidate/invitations/{inv['id']}")
        rec.start()
        rec.caption("Кандидат видит компанию, предложение и вилку — и решает сам")
        rec.pump(3.5)
        rec.click("button.btn-primary", "Принять и открыть контакты", wait=1.2)
        rec.caption("Согласие кандидата открывает контакты — только этому работодателю")
        rec.pump(2.5)
        rec.pause()

        # 4. Работодатель видит контакты
        switch_user(rec, base, emp_token, "employer", "/employer/invitations")
        rec.start()
        rec.caption("У работодателя приглашение «принято», контакты кандидата открыты")
        rec.pump(4.0)
        rec.pause()
    finally:
        issues = list(rec.issues)
        rec.close()
    print(f"кадров: {len(rec.frames)}, подписей: {len(rec.captions)}")
    if issues:
        print("замечания консоли:", *issues[:10], sep="\n  ")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    assemble(rec, work, out)
    files = ROOT / "frontend" / "files"
    files.mkdir(exist_ok=True)
    shutil.copyfile(out, files / out.name)
    dur = subprocess.run([FFMPEG, "-i", str(out)], capture_output=True, text=True).stderr
    print("видео:", out, f"{out.stat().st_size / 1e6:.1f} МБ", next((l.strip() for l in dur.splitlines() if "Duration" in l), ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
