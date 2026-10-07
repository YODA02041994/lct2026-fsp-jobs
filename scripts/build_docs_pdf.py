#!/usr/bin/env python3
"""Собирает сопроводительную документацию по восьми разделам ТЗ (п. 3.4) из рабочих документов репозитория.

    python3 scripts/build_docs_pdf.py            # → docs/10_Документация_к_сдаче.md, docs/build/Документация.html,
                                                 #   docs/Документация_Карьера_ФСП.pdf (+ копия в frontend/files/ для стенда)

Markdown → HTML делает пакет markdown; HTML → PDF — Google Chrome без окна (на этом Маке стартует несколько минут), запасной путь — fpdf2 (ключ --fpdf).
"""
from __future__ import annotations
import datetime as dt
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REPO = "https://github.com/YODA02041994/lct2026-fsp-jobs"
STAND = "https://docsemenov.ru/fsp/"


def read(name: str) -> str:
    return open(os.path.join(DOCS, name), encoding="utf-8").read()


def body_of(md: str, shift: int = 1, drop_h1: bool = True, only_sections: list[str] | None = None, skip_sections: list[str] | None = None) -> str:
    """Тело документа без заголовка первого уровня; все заголовки опускаются на shift уровней.
    only_sections / skip_sections — номера разделов второго уровня («## 5. …») для выборочного включения."""
    lines = md.splitlines()
    out, keep, in_code = [], True, False
    for ln in lines:
        if ln.startswith("```"):
            in_code = not in_code
            if keep:
                out.append(ln)
            continue
        if not in_code and ln.startswith("# ") and drop_h1:
            continue
        m = re.match(r"^(#{2,6})\s+(\d+)\.", ln) if not in_code else None
        if m and (only_sections is not None or skip_sections is not None) and len(m.group(1)) == 2:
            num = m.group(2)
            keep = (only_sections is None or num in only_sections) and (skip_sections is None or num not in skip_sections)
        if not keep:
            continue
        if not in_code and ln.startswith("#"):
            ln = "#" * shift + ln
        out.append(ln)
    return "\n".join(out).strip() + "\n"


def openapi_table() -> str:
    sys.path.insert(0, os.path.join(ROOT, "backend"))
    os.environ.setdefault("FSP_DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("FSP_SECRET_KEY", "docs")
    from app.main import app  # noqa: E402
    spec = app.openapi()
    rows = ["| Метод | Путь | Назначение | Раздел |", "|---|---|---|---|"]
    n = 0
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            summary = op.get("summary") or (op.get("description") or "").split("\n")[0]
            tags = ", ".join(op.get("tags") or [])
            rows.append(f"| `{method.upper()}` | `{path}` | {summary} | {tags} |")
            n += 1
    return f"Всего операций: {n}. Полная схема со всеми запросами, ответами и кодами ошибок — `/api/openapi.json`, интерактивная документация — `/api/docs`.\n\n" + "\n".join(rows) + "\n"


PURPOSE = {
    "fastapi": "веб-каркас API, автоматическая схема OpenAPI", "uvicorn": "ASGI-сервер", "SQLAlchemy": "ORM и работа с базой",
    "pydantic": "проверка данных запросов и ответов", "pydantic-settings": "настройки из переменных окружения и .env",
    "argon2-cffi": "хэширование паролей (Argon2id)", "PyJWT": "токены доступа (JWT, HS256)", "python-multipart": "загрузка файлов (резюме PDF)",
    "httpx": "обращения к внешним сервисам: ФСП ID (OIDC), внешняя модель", "fpdf2": "PDF-профиль кандидата", "pdfminer.six": "извлечение текста из PDF-резюме",
    "psycopg": "драйвер PostgreSQL", "email-validator": "проверка адресов электронной почты",
}


def libraries_table() -> str:
    rows = ["| Компонент | Версия | Лицензия | Назначение |", "|---|---|---|---|",
            "| Python | 3.12 | PSF | язык бэкенда |",
            "| PostgreSQL (образ `postgres:16-alpine`) | 16 | PostgreSQL | хранение данных на стенде и в Docker; локально без Docker — SQLite из стандартной библиотеки |",
            "| nginx (образ `nginx:1.27-alpine`) | 1.27 | BSD-2 | раздача фронтенда и проксирование API |",
            "| Vue (`frontend/vendor/vue.esm-browser.prod.js`) | 3.5.43 | MIT | фронтенд, без сборки (ES-модули) |",
            "| Montserrat (`frontend/vendor/fonts`, `backend/app/assets`) | — | OFL 1.1 | шрифт интерфейса, PDF-профиля и документации |",
            "| Docker Compose | v2 | Apache-2.0 | запуск трёх контейнеров одной командой |"]
    for ln in open(os.path.join(ROOT, "backend", "requirements.txt"), encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)(\[[^\]]+\])?\s*([=>]=)\s*([^\s;]+)", ln)
        if not m:
            continue
        name, extra, op, ver = m.group(1), m.group(2) or "", m.group(3), m.group(4)
        lic = {"fastapi": "MIT", "uvicorn": "BSD-3", "SQLAlchemy": "MIT", "pydantic": "MIT", "pydantic-settings": "MIT", "argon2-cffi": "MIT",
               "PyJWT": "MIT", "python-multipart": "Apache-2.0", "httpx": "BSD-3", "fpdf2": "LGPL-3.0", "pdfminer.six": "MIT", "psycopg": "LGPL-3.0",
               "email-validator": "Unlicense"}.get(name, "")
        rows.append(f"| {name}{extra} | {'' if op == '==' else '≥ '}{ver} | {lic} | {PURPOSE.get(name, '')} |")
    rows.append("| DeepSeek V4.1 Flash (внешняя модель, необязательна) | API | — | разбор резюме и потребности по обезличенному тексту; без ключа — правила |")
    return "\n".join(rows) + "\n"


TABLE_FONT = 7.8
ASSETS = os.path.join(ROOT, "backend", "app", "assets")
MONO = "/System/Library/Fonts/Supplemental/Courier New.ttf"
FALLBACK = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"   # греческие буквы и символы, которых нет в Montserrat


def _prepare_html(html: str) -> str:
    """Подгонка HTML под write_html fpdf2: ширины колонок по длине текста, мелкий шрифт в таблицах, без оглавления markdown."""
    html = re.sub(r'<div class="toc">.*?</div>\s*', "", html, flags=re.S)
    def fix_table(m):
        t = m.group(0)
        rows = re.findall(r"<tr>(.*?)</tr>", t, flags=re.S)
        cols = [re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, flags=re.S) for r in rows]
        n = max((len(c) for c in cols), default=0)
        if not n:
            return t
        lens = [max(len(re.sub(r"<[^>]+>", "", c[k])) if k < len(c) else 0 for c in cols) for k in range(n)]
        lens = [min(max(x, 6), 90) for x in lens]
        tot = sum(lens)
        widths = [max(8, round(100 * x / tot)) for x in lens]
        widths[-1] = 100 - sum(widths[:-1])
        head = re.search(r"<thead>(.*?)</thead>", t, flags=re.S)
        if head:
            k = iter(widths)
            def add_w(mm):
                return f'<th width="{next(k)}%"' + mm.group(1)
            new_head = re.sub(r"<th(>|\s)", add_w, head.group(1))
            t = t.replace(head.group(1), new_head)
        t = re.sub(r"<t([dh])([^>]*)>(.*?)</t[dh]>", lambda mm: f"<t{mm.group(1)}{mm.group(2)}>" + re.sub(r"<[^>]+>", "", mm.group(3)) + f"</t{mm.group(1)}>", t, flags=re.S)
        t = re.sub(r"<td([^>]*)>", lambda mm: f"<td{mm.group(1)}><font size=\"{TABLE_FONT}\">", t)
        t = t.replace("</td>", "</font></td>")
        t = re.sub(r"<th([^>]*)>", lambda mm: f"<th{mm.group(1)}><font size=\"{TABLE_FONT}\">", t)
        t = t.replace("</th>", "</font></th>")
        return t.replace("<table>", '<table border="1" width="100%">')
    html = re.sub(r"<table>.*?</table>", fix_table, html, flags=re.S)
    html = html.replace("<pre><code>", "<pre>").replace("</code></pre>", "</pre>")
    html = re.sub(r'<pre class="[^"]*">', "<pre>", html)
    return html


def write_html_file(md: str) -> str:
    import markdown  # noqa: E402
    html_body = markdown.markdown(md, extensions=["tables", "fenced_code", "toc", "sane_lists"], extension_configs={"toc": {"toc_depth": "2-3", "title": "Содержание"}})
    fonts = os.path.relpath(os.path.join(ROOT, "frontend", "vendor", "fonts"), os.path.join(DOCS, "build"))
    css = """
@font-face { font-family: 'Montserrat'; src: url('%(f)s/montserrat-cyrillic.woff2') format('woff2'); unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; }
@font-face { font-family: 'Montserrat'; src: url('%(f)s/montserrat-cyrillic-ext.woff2') format('woff2'); unicode-range: U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F; }
@font-face { font-family: 'Montserrat'; src: url('%(f)s/montserrat-latin-ext.woff2') format('woff2'); unicode-range: U+0000-00FF, U+0100-02BA, U+2000-206F, U+2070-209F, U+20A0-20CF, U+2122, U+2190-21FF, U+2200-22FF, U+25A0-25FF, U+2600-26FF; }
@page { size: A4; margin: 16mm 15mm 18mm 15mm; }
html { font-family: 'Montserrat', 'Helvetica Neue', Arial, sans-serif; font-size: 10.2pt; line-height: 1.42; color: #1C1D22; }
body { margin: 0; }
h1 { font-size: 22pt; color: #310F53; border-bottom: 3px solid #FF0053; padding-bottom: 6px; margin: 0 0 14px; }
h2 { font-size: 16pt; color: #310F53; page-break-before: always; border-left: 6px solid #FF0053; padding-left: 10px; margin: 0 0 12px; }
h3 { font-size: 12.5pt; color: #520978; margin: 18px 0 6px; }
h4 { font-size: 10.8pt; color: #520978; margin: 14px 0 4px; }
p { margin: 0 0 7px; }
a { color: #520978; text-decoration: none; }
table { border-collapse: collapse; width: 100%%; margin: 6px 0 12px; font-size: 8.6pt; }
th, td { border: 1px solid #d9d3e3; padding: 3px 6px; vertical-align: top; text-align: left; word-wrap: break-word; }
th { background: #FFD6E4; color: #310F53; }
tr { page-break-inside: avoid; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.6pt; background: #f4f2f8; padding: 0 3px; border-radius: 3px; }
pre { background: #f4f2f8; border: 1px solid #e3ddee; padding: 8px 10px; font-size: 8.4pt; white-space: pre-wrap; word-wrap: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
ul, ol { margin: 0 0 8px 0; padding-left: 22px; }
li { margin-bottom: 2px; }
blockquote { border-left: 4px solid #8A83D1; margin: 8px 0; padding: 2px 10px; color: #444; }
.toc { background: #faf8fd; border: 1px solid #e3ddee; padding: 10px 16px; margin: 10px 0 16px; }
.toc ul { list-style: none; padding-left: 14px; }
.toc > ul { padding-left: 0; }
.toc .toctitle { font-weight: 700; color: #310F53; }
""" % {"f": fonts}
    html = f"<!doctype html><html lang='ru'><head><meta charset='utf-8'><title>Карьера ФСП — сопроводительная документация</title><style>{css}</style></head><body>{html_body}</body></html>"
    html_path = os.path.join(DOCS, "build", "Документация.html")
    open(html_path, "w", encoding="utf-8").write(html)
    return html_path


def render_pdf(md: str, pdf_path: str) -> None:
    import markdown  # noqa: E402
    from fpdf import FPDF, FontFace  # noqa: E402

    class Doc(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font("Montserrat", size=7.5)
            self.set_text_color(120, 120, 130)
            self.cell(0, 6, f"Карьера ФСП — сопроводительная документация · стр. {self.page_no()}", align="C")

    pdf = Doc(format="A4")
    pdf.set_margins(16, 16, 16)
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_font("Montserrat", "", os.path.join(ASSETS, "Montserrat-Regular.ttf"))
    pdf.add_font("Montserrat", "B", os.path.join(ASSETS, "Montserrat-Bold.ttf"))
    pdf.add_font("CourierNew", "", MONO)
    if os.path.exists(FALLBACK):
        pdf.add_font("ArialUnicode", "", FALLBACK)
        pdf.set_fallback_fonts(["ArialUnicode"])
    pdf.set_font("Montserrat", size=9.6)
    styles = {
        "h1": FontFace(family="Montserrat", emphasis="BOLD", size_pt=20, color=(49, 15, 83)),
        "h2": FontFace(family="Montserrat", emphasis="BOLD", size_pt=15, color=(49, 15, 83)),
        "h3": FontFace(family="Montserrat", emphasis="BOLD", size_pt=11.5, color=(82, 9, 120)),
        "h4": FontFace(family="Montserrat", emphasis="BOLD", size_pt=10, color=(82, 9, 120)),
        "code": FontFace(family="CourierNew", size_pt=8.4, color=(49, 15, 83)),
        "pre": FontFace(family="CourierNew", size_pt=8, color=(28, 29, 34), fill_color=(244, 242, 248)),
        "a": FontFace(family="Montserrat", color=(82, 9, 120)),
        "blockquote": FontFace(family="Montserrat", color=(70, 70, 80)),
    }
    # оглавление своими руками: разделы второго уровня
    sections = re.split(r"\n(?=## )", md)
    toc = [re.match(r"## (.+)", sec).group(1) for sec in sections[1:]]
    sections[0] = sections[0].replace("[TOC]", "**Содержание**\n\n" + "\n".join(f"{k + 1}. {t}" for k, t in enumerate(toc)) + "\n")
    for k, sec in enumerate(sections):
        if k > 0:
            pdf.add_page()
        elif pdf.page == 0:
            pdf.add_page()
        html = markdown.markdown(sec, extensions=["tables", "fenced_code", "sane_lists"])
        pdf.write_html(_prepare_html(html), tag_styles=styles, ul_bullet_char="•")
    pdf.output(pdf_path)


def openapi_ops() -> int:
    sys.path.insert(0, os.path.join(ROOT, "backend"))
    os.environ.setdefault("FSP_DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("FSP_SECRET_KEY", "docs")
    from app.main import app  # noqa: E402
    return sum(1 for ops in app.openapi()["paths"].values() for m in ops if m in ("get", "post", "put", "patch", "delete"))


def main():
    today = dt.date.today().strftime("%d.%m.%Y")
    n_ops = openapi_ops()
    n_tests = 645
    parts = []
    parts.append(f"""# Карьера ФСП — сопроводительная документация

**Платформа подбора ИТ-специалистов с обратной механикой найма и подтверждённым профилем достижений участника ФСП.**
Решение задачи специального трека Федерации спортивного программирования на хакатоне «Лидеры цифровой трансформации 2026».
Команда «Пироговский Университет». Документ собран {today}.

| | |
|---|---|
| Репозиторий (открытый код) | {REPO} |
| Развёрнутый прототип | {STAND} |
| Интерактивное описание API (OpenAPI) | {STAND}api/docs |
| Учётные записи для проверки | кандидат с историей ФСП `candidate.demo@fsp-demo.ru`, кандидат без истории `candidate2.demo@fsp-demo.ru`, работодатель `employer.demo@fsp-demo.ru`; пароль у всех `demo12345` (показаны и на экране входа) |

Документ построен по пункту 3.4 ТЗ: восемь обязательных разделов в том же порядке. Рабочие документы, из которых он собран,
лежат в репозитории в папке `docs/`; собирается командой `python3 scripts/build_docs_pdf.py`.

[TOC]

## 0. Решение в двух абзацах

Работодатель не публикует вакансию и не ждёт откликов: он описывает потребность (текст плюс специализация, грейд, стек,
зарплата) и получает подборку кандидатов из категории «специализация × грейд», где грейд **подтверждён тестом**, а не
самоописанием. У каждого кандидата в подборке — оценка соответствия с шестью объяснимыми слагаемыми и обоснование одной
строкой. Работодатель сам направляет приглашение с вилкой зарплаты; контакты кандидата открываются только после его согласия.
Подборка хранится версиями: уточнение фильтров не теряет прежний результат.

Кандидат регистрируется, заполняет опрос, при желании загружает резюме (PDF), проходит тест на грейд из параметризованных
заданий (у каждого свой экземпляр — утечка ответов бессмысленна) и получает категорию. Профиль можно связать с ФСП ID
(OpenID Connect, совместимо с Keycloak): из реестра подтягиваются подтверждённые достижения с уровнем доверия; кандидат
без истории ФСП проходит тот же путь, и его профиль обрабатывается корректно. Дополнительно: отклики на вакансии, короткие
регулярные задания, PDF-профиль, приглашения со статусами, журнал действий.

Ключевые числа на {today}: {n_ops} операций API в OpenAPI; банк из 136 параметризованных шаблонов заданий для восьми специализаций;
{n_tests} автотестов; на контрольных синтетических мирах с реалистичным тестом подбор даёт
P@5 0,77–0,97 против 0,65–0,83 у подбора по словам резюме и держит преимущество на восьми вариантах генератора;
прототип развёрнут и работает на стенде.
""")
    parts.append("## 1. Функциональная и компонентная архитектура\n\n" + body_of(read("06_Архитектура.md"), skip_sections=["5"]))
    parts.append("## 2. Механика тестирования кандидатов и её устойчивость к распространению заданий\n\n" + body_of(read("08_Механика_тестирования.md")))
    parts.append("## 3. Механика подбора и логика категоризации кандидатов\n\n" + body_of(read("07_Механика_подбора.md")))
    parts.append("## 4. Процедура валидации решения и её результаты\n\n" + body_of(read("09_Валидация.md")))
    fsp = f"""## 5. Схема интеграции с реестром ФСП

### 5.1. Что реализовано в прототипе

1. В профиле кандидата — кнопка «Связать с ФСП ID». Она начинает вход по OpenID Connect у издателя, адрес которого задаётся
   настройками (`FSP_FSP_OIDC_ISSUER`, `FSP_FSP_OIDC_CLIENT_ID`, `FSP_FSP_OIDC_CLIENT_SECRET`). Без настроек работает встроенный
   издатель-заглушка (`/api/v1/fsp/mock/login`), который ведёт себя как Keycloak: страница входа, код авторизации, обмен кода
   на токены, `sub` = ФСП ID.
2. После возврата (`/api/v1/fsp/callback`) сервис связывает учётную запись с ФСП ID и запрашивает результаты участника
   в реестре. В прототипе реестр имитируется внутри базы: события взяты из Единого календарного плана Минспорта
   (146 записей, `backend/app/data/ekp_events.json`), результаты участников — синтетические.
3. Каждый результат превращается в запись о достижении по модели раздела 5.3: тип, уровень A1–A5, дисциплина, событие с номером
   в календаре, место, срок действия (звания бессрочно, КМС три года, разряды два года), **уровень доверия «подтверждено
   источником»**. Записи, загруженные кандидатом документом, получают уровень «подтверждено документом», введённые вручную —
   «заявлено участником»; интерфейс эти уровни не смешивает, а в ранжировании учитываются только первые два.
4. Кандидат без истории ФСП видит в профиле раздел «История ФСП отсутствует»; слагаемое достижений в подборе равно нулю,
   остальные слагаемые работают — путь кандидата ничем не отличается.
5. Связь можно разорвать (`/api/v1/fsp/unlink`); записи из реестра при этом скрываются, а не удаляются из журнала.

### 5.2. Что меняется при подключении настоящего реестра

| Компонент | Прототип | Боевое подключение |
|---|---|---|
| Издатель ФСП ID | встроенная заглушка, тот же протокол | Keycloak ФСП: `https://sso.fsp-russia.ru/realms/fsp/.well-known/openid-configuration` — меняются только три настройки |
| Источник результатов | имитация реестра в базе | API реестра ФСП (по ФСП ID → список результатов с номерами событий) |
| Сверка события | номер события ищется в загруженном календаре | запрос к календарю Минспорта (`get_ekp`) по номеру |
| Подтверждение разрядов и званий | норма по месту и уровню соревнования | приказ органа, присвоившего разряд; при наличии открытого реестра — ссылка |

Схема записи о достижении и уровни доверия не меняются, поэтому фронтенд и подбор правок не требуют.

""" + body_of(read("04_Профиль_достижений_ФСП.md"), shift=1, only_sections=["7", "8"]).replace("### 7.", "### 5.3.").replace("### 8.", "### 5.4.") + "\n" + body_of(read("06_Архитектура.md"), only_sections=["5"]).replace("### 5. Интеграция с реестром ФСП (схема для документации)", "### 5.5. Сводка")
    parts.append(fsp)
    parts.append("## 6. Описание API\n\n### 6.1. Перечень операций\n\n" + openapi_table() + "\n### 6.2. Контракт для фронтенда\n\n" + body_of(read("API_контракт.md"), shift=2))
    parts.append("## 7. Используемые библиотеки и компоненты\n\n" + libraries_table() + """
Все компоненты — открытое программное обеспечение с разрешительными лицензиями; код решения открыт, не скомпилирован и не
обфусцирован. Внешняя языковая модель необязательна: без ключа разбор резюме и потребностей выполняется правилами, а подбор и
тестирование от неё не зависят вовсе.
""")
    parts.append(f"""## 8. Пошаговая инструкция по сборке, развёртыванию и локальному запуску

### 8.1. Требования

- Вариант с Docker: Docker 24+ с Compose v2. Вариант без Docker: Python 3.12.
- Около 1 ГБ оперативной памяти; после установки зависимостей интернет не нужен (Vue и шрифты лежат в репозитории).
- Сеть: порт 8080 (Docker) или 8000 (без Docker).

### 8.2. Запуск в Docker (три контейнера: PostgreSQL, API, nginx)

```bash
git clone {REPO}.git
cd lct2026-fsp-jobs
docker compose up --build
```

Через минуту откройте http://localhost:8080. При старте контейнер `api` создаёт таблицы и наполняет базу демонстрационными
данными (120 синтетических кандидатов, 12 потребностей, учётные записи для проверки — пароль `demo12345`); повторный запуск
данные не дублирует. Остановка — `docker compose down`, полный сброс базы — `docker compose down -v`.

### 8.3. Запуск без Docker

```bash
./run.sh dev        # создаёт .venv, ставит зависимости, наполняет SQLite демо-данными, поднимает API на :8000 (другой порт: PORT=8015 ./run.sh dev)
./run.sh test       # автотесты (pytest ставится из backend/requirements-dev.txt)
./run.sh smoke      # сквозной сценарий ТЗ по HTTP против запущенного сервиса, 24 шага (BASE=http://localhost:8000 для запуска без Docker)
./run.sh seed --reset   # пересоздать демонстрационные данные
```

Фронтенд раздаётся самим API с корня (http://localhost:8000), интерактивная документация — http://localhost:8000/api/docs,
проверка состояния — http://localhost:8000/api/health.

### 8.4. Настройки

Все настройки — переменные окружения с префиксом `FSP_` (можно в файле `.env`, образец — `.env.example`):

| Переменная | Значение по умолчанию | Назначение |
|---|---|---|
| `FSP_DATABASE_URL` | `sqlite:///./data/fsp.db` | адрес базы; для PostgreSQL `postgresql+psycopg://user:pass@host:5432/db` |
| `FSP_SECRET_KEY` | — (обязательно сменить) | ключ подписи токенов |
| `FSP_PUBLIC_URL`, `FSP_ROOT_PATH` | `http://localhost:8000`, пусто | внешний адрес и префикс пути (на стенде `/fsp`) |
| `FSP_SMTP_*` | пусто | почта для подтверждения регистрации; без SMTP ссылка подтверждения показывается на экране (демонстрационный режим) |
| `FSP_LLM_BASE_URL`, `FSP_LLM_API_KEY`, `FSP_LLM_MODEL` | пусто | внешняя модель (OpenAI-совместимый API) для разбора резюме и потребностей; без ключа — правила |
| `FSP_TEST_BLOCK_SIZE`, `FSP_TEST_BLOCKS`, `FSP_TEST_ITEM_SECONDS` | 5, 2, 90 | длина теста: заданий в блоке, блоков, секунд на задание |
| `FSP_GRADE_CHANGE_COOLDOWN_DAYS` | 90 | как часто можно менять подтверждённый грейд |
| `FSP_FSP_OIDC_ISSUER`, `FSP_FSP_OIDC_CLIENT_ID`, `FSP_FSP_OIDC_CLIENT_SECRET` | пусто | ФСП ID по OpenID Connect; пусто — встроенный издатель-заглушка |

### 8.5. Развёртывание на сервере (как сделан стенд)

1. Python 3.12, PostgreSQL 16; создать роль и базу `fsp`.
2. Код в `/opt/fsp/repo`, окружение `/opt/fsp/venv` (`pip install -r backend/requirements.txt`), настройки в `/opt/fsp/.env`
   (`FSP_DATABASE_URL`, `FSP_SECRET_KEY`, `FSP_PUBLIC_URL=https://домен`, `FSP_ROOT_PATH=/fsp`).
3. Служба systemd: `ExecStartPre=/opt/fsp/venv/bin/python -m app.seed` (таблицы и демо-данные), затем
   `uvicorn app.main:app --host 127.0.0.1 --port 8891 --root-path /fsp`, `WorkingDirectory=/opt/fsp/repo/backend`, `EnvironmentFile=/opt/fsp/.env`.
4. nginx: `location ^~ /fsp/api/` — прокси на `127.0.0.1:8891` с заголовком `X-Forwarded-Prefix /fsp`;
   `location ^~ /fsp/` — `alias /opt/fsp/repo/frontend/` с `try_files $uri $uri/ /fsp/index.html`.
5. Обновление: обновить код, `systemctl restart fsp-api`; проверка — `curl https://домен/fsp/api/health`
   (ответ `{{"status":"ok","templates":136,"demo_mode":true,"model":true}}`).

### 8.6. Проверка сквозного сценария после запуска

Автоматически: `./run.sh smoke` проходит весь путь ниже по HTTP (24 шага) и печатает итог; проверено на свежем клоне репозитория
в Docker и без Docker 07.10.2026. Вручную:

1. Войти работодателем (`employer.demo@fsp-demo.ru`), открыть «Потребности» → одну из готовых → «Подборка»: карточки с оценкой,
   слагаемыми и обоснованием; уточнить фильтры → появится вторая версия подборки; отправить приглашение.
2. Зарегистрировать нового кандидата (ссылка подтверждения показывается на экране, SMTP не нужен), заполнить опрос, пройти тест
   (10 заданий, около десяти минут), получить категорию; связать профиль с ФСП ID через издателя-заглушку — появятся достижения.
3. Войти кандидатом `candidate.demo@fsp-demo.ru` → «Приглашения» → принять: у работодателя откроются контакты.
4. Автотесты: `./run.sh test` → `645 passed` (ставит pytest из `backend/requirements-dev.txt`).

### 8.7. Сборка документации и презентации

`python3 scripts/build_docs_pdf.py` собирает этот документ (Markdown → HTML → PDF через Google Chrome без окна);
`python3 scripts/build_deck.py` собирает презентацию из шаблона организатора.

## Приложение. Использование искусственного интеллекта

""" + body_of(read("../README.md"), only_sections=None, drop_h1=True).split("## Использование ИИ", 1)[1].strip().replace("\n## ", "\n### ") + "\n")
    md = "\n\n".join(parts)
    md_path = os.path.join(DOCS, "10_Документация_к_сдаче.md")
    open(md_path, "w", encoding="utf-8").write(md)

    pdf_path = os.path.join(DOCS, "Документация_Карьера_ФСП.pdf")
    html_path = write_html_file(md)
    if os.path.exists(CHROME) and "--fpdf" not in sys.argv:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions", "--hide-scrollbars",
               "--user-data-dir=/tmp/chrome-docs-build", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", "file://" + html_path]
        # Chrome плодит дочерние процессы, которые держат каналы вывода, поэтому вывод не перехватываем, а по тайм-ауту гасим всю группу
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            proc.wait(timeout=900)   # на этом Маке Chrome стартует очень долго
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(proc.pid, signal.SIGKILL)
    if not os.path.exists(pdf_path):
        print("Chrome не отрисовал — запасной путь fpdf2")
        render_pdf(md, pdf_path)
    shutil.copyfile(pdf_path, os.path.join(ROOT, "frontend", "files", "Документация_Карьера_ФСП.pdf"))
    print(f"markdown: {md_path} ({len(md)} знаков)\npdf: {pdf_path} ({os.path.getsize(pdf_path) // 1024} КБ) + копия в frontend/files/")


if __name__ == "__main__":
    main()
