"""Модель данных. Описание сущностей — docs/06_Архитектура.md, раздел 4."""
from __future__ import annotations
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator
from .db import Base


class TZDateTime(TypeDecorator):
    """Дата-время всегда с часовым поясом UTC: SQLite возвращает наивные значения, Postgres — со смещением."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


def now() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    candidate = "candidate"
    employer = "employer"
    operator = "operator"


GRADES = ["junior", "middle", "senior", "lead"]
GRADE_TITLES = {"junior": "Junior", "middle": "Middle", "senior": "Senior", "lead": "Lead"}
WORK_FORMATS = ["office", "remote", "hybrid"]
INVITATION_STATUSES = ["sent", "viewed", "accepted", "declined"]
APPLICATION_STATUSES = ["sent", "viewed", "accepted", "declined"]
TRUST_LEVELS = ["source", "document", "claimed"]          # подтверждено источником / документом / заявлено


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    candidate: Mapped["Candidate | None"] = relationship(back_populates="user", uselist=False)
    employer: Mapped["Employer | None"] = relationship(back_populates="user", uselist=False)


class EmailToken(Base):
    __tablename__ = "email_token"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(20))      # confirm / reset
    expires_at: Mapped[datetime] = mapped_column(TZDateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Specialization(Base):
    __tablename__ = "specialization"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    has_bank: Mapped[bool] = mapped_column(Boolean, default=False)   # есть ли свои шаблоны заданий
    order: Mapped[int] = mapped_column(Integer, default=0)


class Candidate(Base):
    __tablename__ = "candidate"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), unique=True)
    alias: Mapped[str] = mapped_column(String(40), default="")        # «Кандидат № 1042» — видно работодателю до контакта
    full_name: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    telegram: Mapped[str] = mapped_column(String(80), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    experience_years: Mapped[float] = mapped_column(Float, default=0)
    roles: Mapped[list] = mapped_column(JSON, default=list)           # роли в команде
    soft_skills: Mapped[list] = mapped_column(JSON, default=list)
    about: Mapped[str] = mapped_column(Text, default="")
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_format: Mapped[str] = mapped_column(String(20), default="")
    specialization_code: Mapped[str | None] = mapped_column(ForeignKey("specialization.code"), nullable=True)
    claimed_grade: Mapped[str | None] = mapped_column(String(20), nullable=True)   # что заявил в опросе
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)           # подтверждённый тестом
    grade_changed_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    fsp_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    fsp_linked_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    visible_to_employers: Mapped[bool] = mapped_column(Boolean, default=False)
    privacy: Mapped[dict] = mapped_column(JSON, default=lambda: {"achievements": True, "city": True, "salary": True, "fsp_link": True})
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=now, onupdate=now)
    last_active_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)   # демонстрационная запись
    user: Mapped[User] = relationship(back_populates="candidate")
    skills: Mapped[list["CandidateSkill"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    achievements: Mapped[list["Achievement"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    consents: Mapped[list["Consent"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")


class CandidateSkill(Base):
    __tablename__ = "candidate_skill"
    __table_args__ = (UniqueConstraint("candidate_id", "skill"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id", ondelete="CASCADE"), index=True)
    skill: Mapped[str] = mapped_column(String(60))                    # каноническое имя технологии
    source: Mapped[str] = mapped_column(String(20), default="profile")  # profile / resume / test
    confirmed_by_test: Mapped[bool] = mapped_column(Boolean, default=False)
    test_score: Mapped[float | None] = mapped_column(Float, nullable=True)   # доля верных по технологии
    candidate: Mapped[Candidate] = relationship(back_populates="skills")


class Consent(Base):
    __tablename__ = "consent"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))       # processing / publication
    text_version: Mapped[str] = mapped_column(String(20), default="1.0")
    given_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    revoked_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    candidate: Mapped[Candidate] = relationship(back_populates="consents")


class Template(Base):
    """Шаблон задания. Экземпляры порождаются генератором по зерну (docs/08)."""
    __tablename__ = "template"
    code: Mapped[str] = mapped_column(String(60), primary_key=True)
    competency: Mapped[str] = mapped_column(String(60))
    specializations: Mapped[list] = mapped_column(JSON, default=list)   # [] — общий для всех
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    fmt: Mapped[str] = mapped_column(String(20))                        # exact / choice / multichoice
    grade_level: Mapped[str] = mapped_column(String(20))
    difficulty: Mapped[float] = mapped_column(Float)                    # b в модели Раша
    status: Mapped[str] = mapped_column(String(20), default="approved")  # draft / approved
    answered: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)


class TestSession(Base):
    __tablename__ = "test_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id", ondelete="CASCADE"), index=True)
    specialization_code: Mapped[str] = mapped_column(ForeignKey("specialization.code"))
    claimed_grade: Mapped[str] = mapped_column(String(20))
    declared_skills: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active")   # active / finished / expired
    current_block: Mapped[int] = mapped_column(Integer, default=1)
    current_level: Mapped[str] = mapped_column(String(20))
    block_size: Mapped[int] = mapped_column(Integer, default=4)
    blocks_total: Mapped[int] = mapped_column(Integer, default=2)
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    theta_sd: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(30), nullable=True)   # confirmed / suggest_lower / suggest_higher / applied
    started_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    items: Mapped[list["TestItem"]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="TestItem.order_no")


class TestItem(Base):
    __tablename__ = "test_item"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("test_session.id", ondelete="CASCADE"), index=True)
    template_code: Mapped[str] = mapped_column(ForeignKey("template.code"))
    seed: Mapped[int] = mapped_column(Integer)
    block_no: Mapped[int] = mapped_column(Integer)
    order_no: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSON)          # вопрос без ответа
    answer_key: Mapped[dict] = mapped_column(JSON)       # правильный ответ — наружу не отдаётся
    candidate_answer: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    answered_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    session: Mapped[TestSession] = relationship(back_populates="items")


class GradeHistory(Base):
    __tablename__ = "grade_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("test_session.id"), nullable=True)
    old_grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_grade: Mapped[str] = mapped_column(String(20))
    changed_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)


class Employer(Base):
    __tablename__ = "employer"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), unique=True)
    company_name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    industry: Mapped[str] = mapped_column(String(120), default="")
    website: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    contact_person: Mapped[str] = mapped_column(String(200), default="")
    contact_email: Mapped[str] = mapped_column(String(255), default="")
    contact_phone: Mapped[str] = mapped_column(String(40), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    user: Mapped[User] = relationship(back_populates="employer")


class Need(Base):
    """Потребность работодателя: из неё строится подборка."""
    __tablename__ = "need"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text, default="")
    specialization_code: Mapped[str | None] = mapped_column(ForeignKey("specialization.code"), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stack: Mapped[list] = mapped_column(JSON, default=list)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_format: Mapped[str] = mapped_column(String(20), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)


class Selection(Base):
    __tablename__ = "selection"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer.id", ondelete="CASCADE"), index=True)
    need_id: Mapped[int | None] = mapped_column(ForeignKey("need.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    versions: Mapped[list["SelectionVersion"]] = relationship(back_populates="selection", cascade="all, delete-orphan", order_by="SelectionVersion.version_no")


class SelectionVersion(Base):
    __tablename__ = "selection_version"
    id: Mapped[int] = mapped_column(primary_key=True)
    selection_id: Mapped[int] = mapped_column(ForeignKey("selection.id", ondelete="CASCADE"), index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    results: Mapped[list] = mapped_column(JSON, default=list)     # [{candidate_id, score, parts, explanation}]
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    selection: Mapped[Selection] = relationship(back_populates="versions")


class Vacancy(Base):
    __tablename__ = "vacancy"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    specialization_code: Mapped[str | None] = mapped_column(ForeignKey("specialization.code"), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stack: Mapped[list] = mapped_column(JSON, default=list)
    salary_min: Mapped[int] = mapped_column(Integer)
    salary_max: Mapped[int] = mapped_column(Integer)
    work_format: Mapped[str] = mapped_column(String(20), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(20), default="open")   # open / closed
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=now, onupdate=now)


class Invitation(Base):
    __tablename__ = "invitation"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id", ondelete="CASCADE"), index=True)
    selection_version_id: Mapped[int | None] = mapped_column(ForeignKey("selection_version.id"), nullable=True)
    vacancy_id: Mapped[int | None] = mapped_column(ForeignKey("vacancy.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    salary_min: Mapped[int] = mapped_column(Integer)
    salary_max: Mapped[int] = mapped_column(Integer)
    contact_method: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="sent")
    sent_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    viewed_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)


class Application(Base):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("vacancy_id", "candidate_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancy.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="sent")
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=now, onupdate=now)


class ShortTask(Base):
    __tablename__ = "short_task"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    specialization_code: Mapped[str | None] = mapped_column(ForeignKey("specialization.code"), nullable=True)
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)


class ShortTaskAnswer(Base):
    __tablename__ = "short_task_answer"
    __table_args__ = (UniqueConstraint("task_id", "candidate_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("short_task.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id", ondelete="CASCADE"), index=True)
    answer: Mapped[str] = mapped_column(Text)
    employer_score: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 1–5
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)


class FspEvent(Base):
    """Имитация реестра ФСП: событие из календаря."""
    __tablename__ = "fsp_event"
    id: Mapped[int] = mapped_column(primary_key=True)
    ekp_number: Mapped[str] = mapped_column(String(32), default="")
    name: Mapped[str] = mapped_column(String(300))
    discipline: Mapped[str] = mapped_column(String(40))     # product / algorithmic / security / robotics / uav
    level: Mapped[str] = mapped_column(String(30))          # russia_championship / russia_cup / district / regional / federal_event
    date_start: Mapped[str] = mapped_column(String(10))
    date_end: Mapped[str] = mapped_column(String(10))
    region: Mapped[str] = mapped_column(String(80), default="")


class FspResult(Base):
    __tablename__ = "fsp_result"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("fsp_event.id", ondelete="CASCADE"), index=True)
    fsp_participant_id: Mapped[str] = mapped_column(String(64), index=True)
    place: Mapped[int] = mapped_column(Integer)
    team: Mapped[str] = mapped_column(String(120), default="")
    points: Mapped[float | None] = mapped_column(Float, nullable=True)


class FspParticipant(Base):
    """Учётная запись в имитации ФСП ID: кто есть в реестре."""
    __tablename__ = "fsp_participant"
    fsp_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200))     # выдуманное имя
    region: Mapped[str] = mapped_column(String(80), default="")
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank: Mapped[str | None] = mapped_column(String(20), nullable=True)      # ms / kms / r1 / r2 / r3 / None
    rank_date: Mapped[str | None] = mapped_column(String(10), nullable=True)


class Achievement(Base):
    __tablename__ = "achievement"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))          # rank / result / team / rating / other
    title: Mapped[str] = mapped_column(String(300))
    discipline: Mapped[str] = mapped_column(String(40), default="")
    level_code: Mapped[str] = mapped_column(String(10), default="A1")   # A1..A5 — docs/05, раздел 2.5
    event_id: Mapped[int | None] = mapped_column(ForeignKey("fsp_event.id"), nullable=True)
    place: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date: Mapped[str] = mapped_column(String(10), default="")
    valid_until: Mapped[str | None] = mapped_column(String(10), nullable=True)
    trust_level: Mapped[str] = mapped_column(String(20), default="claimed")
    status: Mapped[str] = mapped_column(String(20), default="active")   # active / expired / revoked
    document_name: Mapped[str] = mapped_column(String(200), default="")
    document_sha256: Mapped[str] = mapped_column(String(64), default="")
    signature: Mapped[str] = mapped_column(String(200), default="")
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)
    candidate: Mapped[Candidate] = relationship(back_populates="achievements")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    subject_type: Mapped[str] = mapped_column(String(40), default="")
    subject_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=now)


Index("ix_candidate_category", Candidate.specialization_code, Candidate.grade)
