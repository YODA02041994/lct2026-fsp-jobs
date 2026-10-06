"""Зависимости FastAPI: текущий пользователь и проверка роли."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, Candidate, Employer
from .security import read_access_token

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Нужен вход")
    data = read_access_token(creds.credentials)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Токен недействителен")
    user = db.get(User, int(data["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    if not user.email_confirmed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Адрес почты не подтверждён")
    return user


def current_candidate(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Candidate:
    if user.role != "candidate" or user.candidate is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Доступно только кандидату")
    return user.candidate


def current_employer(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Employer:
    if user.role != "employer" or user.employer is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Доступно только работодателю")
    return user.employer
