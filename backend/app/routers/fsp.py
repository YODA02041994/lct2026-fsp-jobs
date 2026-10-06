"""Связь профиля с ФСП ID по OpenID Connect и импорт достижений из реестра.

Настоящий издатель (Keycloak ФСП) задаётся переменными FSP_FSP_OIDC_*; без них работает встроенный издатель-заглушка
с тем же протоколом: страница входа → код → обмен кода на идентификатор участника. Данные реестра — имитация (app/synth.py).
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..db import get_db
from ..deps import current_candidate
from ..models import Candidate, FspParticipant, FspResult, FspEvent, Achievement
from ..security import random_token
from ..services.views import candidate_profile, achievement_view
from ..services.audit import log
from .. import synth

router = APIRouter(prefix="/fsp", tags=["fsp"])
_codes: dict[str, str] = {}      # код → fsp_id (заглушка; живёт в памяти процесса)
RANK_LEVEL = {"ms": "A5", "kms": "A4", "r1": "A3", "r2": "A2", "r3": "A2"}
RANK_VALID_YEARS = {"ms": None, "kms": 3, "r1": 2, "r2": 2, "r3": 2}


def _state(candidate_id: int) -> str:
    s = get_settings()
    return jwt.encode({"cid": candidate_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "n": random_token(8)}, s.secret_key, algorithm="HS256")


def _read_state(state: str) -> int:
    try:
        return int(jwt.decode(state, get_settings().secret_key, algorithms=["HS256"])["cid"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Состояние запроса недействительно")


def _base(request: Request) -> str:
    s = get_settings()
    return f"{s.public_url.rstrip('/')}{s.root_path}"


@router.get("/link/start")
def link_start(request: Request, c: Candidate = Depends(current_candidate)):
    s = get_settings()
    state = _state(c.id)
    redirect_uri = f"{_base(request)}/api/v1/fsp/callback"
    if s.fsp_oidc_issuer:
        disc = httpx.get(s.fsp_oidc_issuer.rstrip("/") + "/.well-known/openid-configuration", timeout=10).json()
        url = disc["authorization_endpoint"] + "?" + urlencode({"response_type": "code", "client_id": s.fsp_oidc_client_id,
                                                                  "redirect_uri": redirect_uri, "scope": "openid profile", "state": state})
        return {"redirect_url": url, "issuer": s.fsp_oidc_issuer, "mock": False}
    return {"redirect_url": f"{_base(request)}/api/v1/fsp/mock/login?" + urlencode({"state": state, "redirect_uri": redirect_uri}),
            "issuer": "встроенный издатель-заглушка", "mock": True}


@router.get("/mock/login", response_class=HTMLResponse, include_in_schema=False)
def mock_login(state: str, redirect_uri: str, db: Session = Depends(get_db)):
    _read_state(state)
    parts = db.scalars(select(FspParticipant).order_by(FspParticipant.fsp_id).limit(12)).all()
    rows = "".join(f'<label class="row"><input type="radio" name="fsp_id" value="{p.fsp_id}" {"checked" if i == 0 else ""}> '
                   f'<b>{p.fsp_id}</b> — {p.display_name}, {p.region}{", " + synth.RANK_TITLE[p.rank] if p.rank else ""}</label>' for i, p in enumerate(parts))
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>ФСП ID — вход (демонстрация)</title>
<style>body{{font-family:system-ui,sans-serif;background:#310F53;color:#1C1D22;margin:0;padding:32px}}
.card{{max-width:640px;margin:0 auto;background:#fff;border-radius:16px;padding:28px 32px}}h1{{color:#310F53;font-size:22px;margin:0 0 6px}}
.note{{color:#666;font-size:14px;margin-bottom:18px}}.row{{display:block;padding:8px 10px;border:1px solid #eee;border-radius:10px;margin:6px 0;cursor:pointer}}
button{{background:#FF0053;color:#fff;border:0;border-radius:10px;padding:12px 20px;font-size:16px;font-weight:600;cursor:pointer;margin-top:12px}}
input[type=text]{{padding:10px;border:1px solid #ccc;border-radius:8px;width:60%}}</style></head><body><div class="card">
<h1>Единый вход ФСП ID</h1><div class="note">Это встроенный издатель-заглушка: он повторяет протокол OpenID Connect, которым будет пользоваться Keycloak ФСП.
Выберите тестового участника реестра или введите идентификатор.</div>
<form method="post" action="mock/authorize"><input type="hidden" name="state" value="{state}"><input type="hidden" name="redirect_uri" value="{redirect_uri}">
{rows}<div style="margin-top:12px"><input type="text" name="custom_id" placeholder="или свой FSP-ID, например FSP-100007"></div>
<button type="submit">Войти и разрешить доступ к достижениям</button></form></div></body></html>"""


@router.post("/mock/authorize", include_in_schema=False)
def mock_authorize(state: str = Form(...), redirect_uri: str = Form(...), fsp_id: str = Form(""), custom_id: str = Form("")):
    _read_state(state)
    chosen = (custom_id or fsp_id or "").strip()
    if not chosen:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Не выбран участник")
    code = random_token(12)
    _codes[code] = chosen
    return RedirectResponse(f"{redirect_uri}?code={code}&state={state}", status_code=303)


def import_achievements(db: Session, c: Candidate, fsp_id: str) -> int:
    """Записи реестра → достижения с уровнем «подтверждено источником». Повторный импорт не плодит дубли."""
    p = db.get(FspParticipant, fsp_id)
    added = 0
    existing_titles = {a.title for a in c.achievements}
    results = db.scalars(select(FspResult).where(FspResult.fsp_participant_id == fsp_id)).all()
    for r in results:
        ev = db.get(FspEvent, r.event_id) if r.event_id else None
        title = f"{r.place}-е место — {(ev.name if ev else 'соревнование ФСП')[:120]}"
        code, _ = synth.level_for(ev.level if ev else "all_russian", r.place)
        if title in existing_titles:
            for a in c.achievements:
                if a.title == title and a.trust_level != "source":
                    a.trust_level = "source"
            continue
        db.add(Achievement(candidate_id=c.id, kind="result", title=title, discipline=ev.discipline if ev else "product", level_code=code,
                           event_id=ev.id if ev else None, place=r.place, date=ev.date_start if ev else "", trust_level="source"))
        added += 1
    if p and p.rank:
        title = synth.RANK_TITLE[p.rank] + " по спортивному программированию"
        yrs = RANK_VALID_YEARS[p.rank]
        d0 = p.rank_date or "2025-01-01"
        valid = None if yrs is None else f"{int(d0[:4]) + yrs}{d0[4:]}"
        if title not in existing_titles:
            db.add(Achievement(candidate_id=c.id, kind="rank", title=title, discipline="product", level_code=RANK_LEVEL[p.rank], date=d0,
                               valid_until=valid, trust_level="source"))
            added += 1
        else:
            for a in c.achievements:
                if a.title == title:
                    a.trust_level = "source"
    return added


@router.get("/callback", include_in_schema=False)
def callback(code: str, state: str, request: Request, db: Session = Depends(get_db)):
    cid = _read_state(state)
    c = db.get(Candidate, cid)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Кандидат не найден")
    s = get_settings()
    if s.fsp_oidc_issuer:
        disc = httpx.get(s.fsp_oidc_issuer.rstrip("/") + "/.well-known/openid-configuration", timeout=10).json()
        tok = httpx.post(disc["token_endpoint"], data={"grant_type": "authorization_code", "code": code, "client_id": s.fsp_oidc_client_id,
                                                        "client_secret": s.fsp_oidc_client_secret, "redirect_uri": f"{_base(request)}/api/v1/fsp/callback"}, timeout=10).json()
        claims = jwt.decode(tok["id_token"], options={"verify_signature": False})   # подпись проверяется у издателя после настройки ключей
        fsp_id = claims.get("preferred_username") or claims["sub"]
    else:
        fsp_id = _codes.pop(code, None)
        if not fsp_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Код недействителен")
    other = db.scalar(select(Candidate).where(Candidate.fsp_id == fsp_id, Candidate.id != c.id))
    if other:
        return RedirectResponse(f"{_base(request)}/#/candidate/achievements?fsp=taken", status_code=303)
    c.fsp_id = fsp_id
    c.fsp_linked_at = datetime.now(timezone.utc)
    added = import_achievements(db, c, fsp_id)
    log(db, c.user_id, "fsp_linked", "candidate", c.id, fsp_id=fsp_id, imported=added)
    db.commit()
    return RedirectResponse(f"{_base(request)}/#/candidate/achievements?fsp=linked&imported={added}", status_code=303)


@router.post("/unlink")
def unlink(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    c.fsp_id = None
    c.fsp_linked_at = None
    for a in c.achievements:
        if a.trust_level == "source":
            a.trust_level = "claimed"
    log(db, c.user_id, "fsp_unlinked", "candidate", c.id)
    db.commit()
    db.refresh(c)
    return candidate_profile(c, db)


@router.get("/registry/status")
def registry_status(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    """Что известно реестру о связанном участнике (для экрана достижений)."""
    if not c.fsp_id:
        return {"linked": False, "message": "История ФСП отсутствует: профиль не связан с ФСП ID"}
    p = db.get(FspParticipant, c.fsp_id)
    n = len(db.scalars(select(FspResult).where(FspResult.fsp_participant_id == c.fsp_id)).all())
    return {"linked": True, "fsp_id": c.fsp_id, "in_registry": p is not None, "results": n,
            "rank": synth.RANK_TITLE.get(p.rank) if p and p.rank else None,
            "message": "" if p else "Связь установлена, но в реестре записей об этом участнике нет — достижения можно подтвердить документом"}
