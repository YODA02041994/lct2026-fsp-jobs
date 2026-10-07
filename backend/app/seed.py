"""Справочники в базе и демонстрационные данные.

    python -m app.seed            # добавить справочники и демо-данные, если их нет
    python -m app.seed --reset    # пересоздать базу целиком

Все кандидаты и компании выдуманы (app/synth.py). Пароль у всех демонстрационных учётных записей — demo12345.
Учётные записи для жюри: candidate.demo@fsp-demo.ru (кандидат с историей ФСП), candidate2.demo@fsp-demo.ru (без истории),
employer.demo@fsp-demo.ru (работодатель).
"""
from __future__ import annotations
import random
import sys
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from .db import SessionLocal, engine, Base
from .catalog import SPECIALIZATIONS
from .models import (Specialization, Template, User, Candidate, CandidateSkill, Consent, TestSession, Employer, Need, Vacancy,
                     ShortTask, FspEvent, FspResult, FspParticipant, Achievement, GradeHistory)
from .security import hash_password
from . import synth

DEMO_PASSWORD = "demo12345"
RANK_VALID_YEARS = {"ms": None, "kms": 3, "r1": 2, "r2": 2, "r3": 2}


def ensure_catalog() -> None:
    from .services.testing.engine import REGISTRY, load_all
    load_all()
    with SessionLocal() as db:
        for code, name, desc, has_bank, order in SPECIALIZATIONS:
            sp = db.get(Specialization, code)
            if not sp:
                db.add(Specialization(code=code, name=name, description=desc, has_bank=has_bank, order=order))
            else:
                sp.name, sp.description, sp.has_bank, sp.order = name, desc, has_bank, order
        for code, t in REGISTRY.items():
            if not db.get(Template, code):
                db.add(Template(code=code, competency=t.competency, specializations=t.specializations, technologies=t.technologies,
                                fmt=t.fmt, grade_level=t.grade_level, difficulty=t.difficulty))
        db.commit()


_DEMO_HASH: str | None = None


def _user(db, email: str, role: str) -> User:
    global _DEMO_HASH
    if _DEMO_HASH is None:
        _DEMO_HASH = hash_password(DEMO_PASSWORD)      # один хэш на все демонстрационные записи: argon2 медленный намеренно
    u = User(email=email, password_hash=_DEMO_HASH, role=role, email_confirmed=True)
    db.add(u)
    db.flush()
    return u


def seed_demo(n_candidates: int = 120, rng_seed: int = 7, honesty: str = "typical") -> dict:
    synth.ONLY_PAST_EVENTS = True       # в демо-данных достижения только по прошедшим событиям календаря
    rng = random.Random(rng_seed)
    events = synth.load_events()
    stats = {"candidates": 0, "employers": 0, "vacancies": 0, "events": 0, "achievements": 0}
    with SessionLocal() as db:
        if db.scalar(select(func.count(Candidate.id)).where(Candidate.synthetic.is_(True))):
            return {"skipped": "демо-данные уже есть"}
        # реестр ФСП: события
        ev_by_number: dict[str, FspEvent] = {}
        for e in events:
            fe = FspEvent(ekp_number=e["ekp_number"], name=e["name"], discipline="product", level=e["level"],
                          date_start=e["date_start"], date_end=e["date_end"], region=e["region"])
            db.add(fe)
            ev_by_number[e["ekp_number"]] = fe
        db.flush()
        stats["events"] = len(events)
        # кандидаты
        cands = synth.make_candidates(n_candidates, rng, events, honesty=honesty)
        now = datetime.now(timezone.utc)
        for sc in cands:
            u = _user(db, f"cand{sc.idx + 1}@fsp-demo.ru", "candidate")
            c = Candidate(user_id=u.id, alias=f"Кандидат № {1000 + u.id}", full_name=sc.full_name, phone=f"+7 9{rng.randint(10, 99)} {rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(10, 99)}",
                          telegram=f"@{sc.full_name.split()[0].lower()}_{sc.idx}", city=sc.city, experience_years=sc.experience_years, roles=sc.roles,
                          soft_skills=sc.soft, about=sc.about, salary_min=sc.salary_min, salary_max=sc.salary_max, work_format=sc.work_format,
                          specialization_code=sc.specialization, claimed_grade=sc.claimed_grade, synthetic=True,
                          last_active_at=now - timedelta(days=rng.choice([0, 1, 2, 5, 10, 20, 40, 90])))
            db.add(c)
            db.flush()
            db.add(Consent(candidate_id=c.id, kind="processing"))
            db.add(Consent(candidate_id=c.id, kind="publication"))
            c.visible_to_employers = True
            # тест: наблюдаемое θ = истинное + шум измерения; грейд — по шкале docs/08
            from .services.testing.engine import grade_from_theta, decide
            theta_obs = sc.theta + rng.gauss(0, 0.35)
            sd = rng.uniform(0.35, 0.55)
            result_grade, decision = decide(theta_obs, sd, sc.claimed_grade)
            final_grade = result_grade if decision in ("confirmed", "suggest_lower") else sc.claimed_grade
            if decision == "suggest_lower" and rng.random() < 0.3:
                final_grade = sc.claimed_grade          # часть кандидатов не согласилась понижаться: грейд остаётся заявленным, но без подтверждения
            finished = now - timedelta(days=rng.randint(1, 120))
            s = TestSession(candidate_id=c.id, specialization_code=sc.specialization, claimed_grade=sc.claimed_grade, declared_skills=sc.declared_stack,
                            status="finished", current_block=2, current_level=sc.claimed_grade, block_size=4, blocks_total=2, theta=round(theta_obs, 3),
                            theta_sd=round(sd, 3), result_grade=result_grade, decision="applied" if decision != "confirmed" else "confirmed",
                            started_at=finished - timedelta(minutes=9), finished_at=finished)
            db.add(s)
            db.flush()
            c.grade = final_grade
            c.grade_changed_at = finished
            db.add(GradeHistory(candidate_id=c.id, session_id=s.id, old_grade=None, new_grade=final_grade, changed_at=finished))
            # навыки: заявленные; подтверждены тестом те, что есть в истинном стеке (с вероятностью) и были проверены
            for sk in sc.declared_stack:
                truly = sk in sc.true_stack
                tested = rng.random() < 0.85           # блоки теста покрывают заявленные технологии (docs/08)
                score = round(rng.uniform(0.6, 1.0), 2) if truly and tested else round(rng.uniform(0.0, 0.45), 2) if tested else None
                db.add(CandidateSkill(candidate_id=c.id, skill=sk, source="profile", confirmed_by_test=bool(score is not None and score >= 0.5), test_score=score))
            # ФСП
            if sc.fsp:
                p = FspParticipant(fsp_id=sc.fsp["fsp_id"], display_name=sc.full_name, region=sc.city, birth_year=rng.randint(1995, 2007),
                                   rank=sc.fsp["rank"], rank_date=sc.fsp["results"][0]["date"] if sc.fsp["rank"] else None)
                db.add(p)
                linked = rng.random() < 0.75          # остальные ещё не связали профиль: достижения только заявленные или по документу
                if linked:
                    c.fsp_id = sc.fsp["fsp_id"]
                    c.fsp_linked_at = now - timedelta(days=rng.randint(1, 60))
                for r in sc.fsp["results"]:
                    fe = ev_by_number.get(r["ekp_number"])
                    db.add(FspResult(event_id=fe.id if fe else None, fsp_participant_id=sc.fsp["fsp_id"], place=r["place"], team=f"команда {rng.randint(1, 40)}"))
                    code, rank = synth.level_for(r["level"], r["place"])
                    trust = "source" if linked else rng.choice(["document", "claimed", "claimed"])
                    db.add(Achievement(candidate_id=c.id, kind="result", title=f"{r['place']}-е место — {r['event_name'][:120]}", discipline=r["discipline"],
                                       level_code=code, event_id=fe.id if fe else None, place=r["place"], date=r["date"], trust_level=trust))
                    stats["achievements"] += 1
                if sc.fsp["rank"]:
                    yrs = RANK_VALID_YEARS[sc.fsp["rank"]]
                    d0 = sc.fsp["results"][0]["date"] or "2025-01-01"
                    valid = None if yrs is None else f"{int(d0[:4]) + yrs}{d0[4:]}"
                    db.add(Achievement(candidate_id=c.id, kind="rank", title=synth.RANK_TITLE[sc.fsp["rank"]] + " по спортивному программированию",
                                       discipline="product", level_code={"ms": "A5", "kms": "A4", "r1": "A3", "r2": "A2", "r3": "A2"}[sc.fsp["rank"]],
                                       date=d0, valid_until=valid, trust_level="source" if linked else "document"))
                    stats["achievements"] += 1
            stats["candidates"] += 1
        # учётные записи для жюри: один кандидат с историей ФСП, один без
        with_fsp = next(c for c in cands if c.fsp and c.fsp["rank"])
        without = next(c for c in cands if not c.fsp)
        for email, sc in (("candidate.demo@fsp-demo.ru", with_fsp), ("candidate2.demo@fsp-demo.ru", without)):
            cand = db.scalar(select(Candidate).join(User).where(User.email == f"cand{sc.idx + 1}@fsp-demo.ru"))
            cand.user.email = email
            cand.grade_changed_at = now - timedelta(days=120)      # жюри сможет сразу пройти тест заново
        # работодатели, потребности, вакансии, короткие задания
        emp_by_name = {}
        for i, (name, desc, industry, city) in enumerate(synth.COMPANIES):
            u = _user(db, "employer.demo@fsp-demo.ru" if i == 0 else f"employer{i + 1}@fsp-demo.ru", "employer")
            e = Employer(user_id=u.id, company_name=name, description=desc, industry=industry, city=city, website=f"https://{name.lower().replace(' ', '')}.example",
                         contact_person="Отдел найма", contact_email=u.email, contact_phone="+7 495 000-00-00", synthetic=True)
            db.add(e)
            db.flush()
            emp_by_name[name] = e
            stats["employers"] += 1
        for n in synth.make_needs(rng):
            e = emp_by_name[n.company]
            db.add(Need(employer_id=e.id, title=n.title, text=n.text, specialization_code=n.specialization, grade=n.grade, stack=n.stack,
                        salary_min=n.salary_min, salary_max=n.salary_max, work_format=n.work_format, city=e.city))
            db.add(Vacancy(employer_id=e.id, title=n.title, description=n.text, specialization_code=n.specialization, grade=n.grade, stack=n.stack,
                           salary_min=n.salary_min, salary_max=n.salary_max, work_format=n.work_format, city=e.city))
            stats["vacancies"] += 1
        tasks = [("Нейрософт", "Оптимизация запроса", "Запрос к таблице приёмов на 10 млн строк выполняется 40 секунд. Опишите, как будете искать причину и что проверите первым.", "backend", ["sql", "postgresql"]),
                 ("Балтик Дата", "Подход к A/B тесту", "Нужно проверить, повышает ли новая карточка товара конверсию. Опишите план эксперимента и как посчитаете результат.", "data", ["statistics", "product_analytics"]),
                 ("ЛогиТех", "Разбор падения интерфейса", "После обновления у части пользователей не открывается карта маршрутов. Как будете локализовать проблему?", "frontend", ["javascript", "http"]),
                 ("ФинКод", "Тест-дизайн формы перевода", "Составьте набор проверок для формы перевода денег между своими счетами (не меньше восьми).", "qa", ["testing_theory"])]
        for comp, title, text, spec, techs in tasks:
            db.add(ShortTask(employer_id=emp_by_name[comp].id, title=title, text=text, specialization_code=spec, technologies=techs))
        db.commit()
    return stats


def main(argv: list[str]) -> None:
    if "--reset" in argv:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        print("база пересоздана")
    else:
        Base.metadata.create_all(engine)
    ensure_catalog()
    print("демо-данные:", seed_demo())


if __name__ == "__main__":
    main(sys.argv[1:])
