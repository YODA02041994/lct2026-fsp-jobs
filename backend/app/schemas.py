"""Схемы запросов и ответов (Pydantic)."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(candidate|employer)$")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    role: str
    user_id: int
    token_type: str = "bearer"


class CandidateUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    telegram: str | None = None
    city: str | None = None
    experience_years: float | None = Field(default=None, ge=0, le=60)
    roles: list[str] | None = None
    soft_skills: list[str] | None = None
    about: str | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    work_format: str | None = None
    skills: list[str] | None = None


class PrivacyIn(BaseModel):
    achievements: bool | None = None
    city: bool | None = None
    salary: bool | None = None
    fsp_link: bool | None = None
    visible_to_employers: bool | None = None


class ConsentsIn(BaseModel):
    processing: bool | None = None
    publication: bool | None = None


class AchievementIn(BaseModel):
    kind: str = Field(pattern="^(rank|result|team|rating|other)$")
    title: str = Field(min_length=3, max_length=300)
    discipline: str = ""
    date: str = ""
    place: int | None = None
    document_name: str = ""


class SessionStart(BaseModel):
    specialization_code: str
    claimed_grade: str = Field(pattern="^(junior|middle|senior|lead)$")
    declared_skills: list[str] = []


class AnswerIn(BaseModel):
    item_id: int
    answer: Any


class EmployerUpdate(BaseModel):
    company_name: str | None = None
    description: str | None = None
    industry: str | None = None
    website: str | None = None
    city: str | None = None
    contact_person: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class NeedIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    text: str = ""
    specialization_code: str | None = None
    grade: str | None = None
    stack: list[str] | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    work_format: str | None = None
    city: str | None = None


class SelectionFilters(BaseModel):
    specialization_code: str | None = None
    grades: list[str] | None = None
    skills: list[str] | None = None
    fsp_only: bool | None = None
    city: str | None = None
    salary_max: int | None = None


class SelectionIn(BaseModel):
    weights: dict[str, float] | None = None


class RefineIn(BaseModel):
    filters: SelectionFilters = SelectionFilters()
    weights: dict[str, float] | None = None


class InvitationIn(BaseModel):
    candidate_id: int
    message: str = Field(min_length=10)
    salary_min: int = Field(ge=0)
    salary_max: int = Field(ge=0)
    contact_method: str = Field(min_length=3)
    vacancy_id: int | None = None
    selection_version_id: int | None = None


class RespondIn(BaseModel):
    decision: str = Field(pattern="^(accept|decline)$")


class VacancyIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    specialization_code: str | None = None
    grade: str | None = None
    stack: list[str] | None = None
    salary_min: int = Field(ge=0)
    salary_max: int = Field(ge=0)
    work_format: str = ""
    city: str = ""
    status: str | None = None


class ApplyIn(BaseModel):
    message: str = ""


class ApplicationStatusIn(BaseModel):
    status: str = Field(pattern="^(viewed|accepted|declined)$")


class ShortTaskIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    text: str = Field(min_length=5)
    specialization_code: str | None = None
    technologies: list[str] | None = None


class ShortTaskAnswerIn(BaseModel):
    answer: str = Field(min_length=1)


class ScoreIn(BaseModel):
    employer_score: int = Field(ge=1, le=5)
