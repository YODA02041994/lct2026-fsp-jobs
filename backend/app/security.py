"""Пароли (argon2), JWT, одноразовые токены."""
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from .config import get_settings

_ph = PasswordHasher()


def hash_password(p: str) -> str:
    return _ph.hash(p)


def verify_password(p: str, h: str) -> bool:
    try:
        return _ph.verify(h, p)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def make_access_token(user_id: int, role: str) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(hours=s.access_token_hours)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, s.secret_key, algorithm="HS256")


def read_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def random_token(n: int = 32) -> str:
    return secrets.token_urlsafe(n)
