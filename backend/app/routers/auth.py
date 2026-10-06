"""Регистрация с подтверждением почты, вход, текущий пользователь."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..db import get_db
from ..deps import current_user
from ..models import User, EmailToken, Candidate, Employer
from ..schemas import RegisterIn, LoginIn, TokenOut
from ..security import hash_password, verify_password, make_access_token, random_token
from ..services.email_service import send_email
from ..services.audit import log

router = APIRouter(prefix="/auth", tags=["auth"])


def _confirm_url(token: str, request: Request | None = None) -> str:
    """Ссылка подтверждения: на стенде — публичный адрес из настроек; локально — адрес, с которого пришёл запрос."""
    s = get_settings()
    base = s.public_url.rstrip("/")
    if request is not None and base == "http://localhost:8000":
        base = f"{request.url.scheme}://{request.url.netloc}"
    return f"{base}{s.root_path}/#/confirm?token={token}"


@router.post("/register", status_code=201, responses={409: {"description": "Почта уже зарегистрирована"}})
def register(data: RegisterIn, request: Request, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Эта почта уже зарегистрирована")
    user = User(email=email, password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.flush()
    if data.role == "candidate":
        db.add(Candidate(user_id=user.id, alias=f"Кандидат № {1000 + user.id}"))
    else:
        db.add(Employer(user_id=user.id))
    token = random_token()
    db.add(EmailToken(user_id=user.id, token=token, purpose="confirm",
                      expires_at=datetime.now(timezone.utc) + timedelta(days=2)))
    log(db, user.id, "register", "user", user.id, role=data.role)
    db.commit()
    url = _confirm_url(token, request)
    sent = send_email(email, "Подтверждение почты — Карьера ФСП",
                      f"Здравствуйте! Чтобы подтвердить адрес и войти, перейдите по ссылке:\n{url}\n\nЕсли вы не регистрировались, просто не отвечайте на письмо.")
    out = {"user_id": user.id, "email": email, "role": data.role, "confirm_required": True}
    if not sent:
        out["demo_confirm_url"] = url
        out["demo_note"] = "Почтовый сервер не настроен: ссылка подтверждения показана здесь (демонстрационный режим)."
    return out


@router.get("/confirm", responses={400: {"description": "Токен недействителен или устарел"}})
def confirm(token: str, db: Session = Depends(get_db)):
    et = db.scalar(select(EmailToken).where(EmailToken.token == token, EmailToken.purpose == "confirm"))
    if not et or et.used or et.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ссылка недействительна или устарела")
    user = db.get(User, et.user_id)
    user.email_confirmed = True
    et.used = True
    log(db, user.id, "email_confirmed", "user", user.id)
    db.commit()
    return {"ok": True, "access_token": make_access_token(user.id, user.role), "role": user.role, "user_id": user.id}


@router.post("/login", response_model=TokenOut, responses={401: {"description": "Неверная пара почта — пароль"}, 403: {"description": "Почта не подтверждена"}})
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверная почта или пароль")
    if not user.email_confirmed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Сначала подтвердите почту по ссылке из письма")
    return TokenOut(access_token=make_access_token(user.id, user.role), role=user.role, user_id=user.id)


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"user_id": user.id, "email": user.email, "role": user.role, "email_confirmed": user.email_confirmed}
