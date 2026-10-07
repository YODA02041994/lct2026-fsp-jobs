"""Подключение к базе. SQLite для разработки и тестов, PostgreSQL в контейнерах и на стенде."""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from .config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = get_settings().database_url
    kw = {}
    if url.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False}
        # SQLite не создаёт папки сам: на свежем клоне backend/data/ нет (она в .gitignore) — создаём
        path = url.split("sqlite:///", 1)[-1]
        if path and path != ":memory:" and not path.startswith("file:"):
            os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    eng = create_engine(url, pool_pre_ping=True, **kw)
    if url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def _fk(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return eng


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    from . import models  # noqa: F401  регистрация таблиц
    Base.metadata.create_all(engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
