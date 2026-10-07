#!/usr/bin/env python3
"""Сверка установки: боевая score_candidate (backend) против эталона эволюции (аргумент — файл эталона) на сохранённом мире.

Собирает из признаков мира объекты, похожие на ORM-кандидата, и сравнивает итоги с точностью до множителя шкалы.
    cd backend && ../.venv/bin/python ../scripts/evolve/check_port.py ../scripts/evolve/<эталон>.py
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ.setdefault("FSP_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FSP_SECRET_KEY", "check")
from fitness_matching import load_worlds, load_score  # noqa: E402
from app.services.matching import score_candidate  # noqa: E402

LEVEL_TITLE = {"A1": "участие", "A2": "финал", "A3": "призёр", "A4": "победитель", "A5": "чемпион"}


def to_obj(f: dict):
    now = datetime.now(timezone.utc)
    skills = [SimpleNamespace(skill=k, confirmed_by_test=v["confirmed"], test_score=v["score"]) for k, v in f["skills"].items()]
    acts = [SimpleNamespace(hidden=False, status="active", trust_level="source", level_code=a["level"], discipline=a["discipline"], title=LEVEL_TITLE[a["level"]])
            for a in f["fsp"]]
    return SimpleNamespace(id=f["id"], specialization_code=f["spec"], grade=f["grade"], claimed_grade=f["claimed_grade"], skills=skills, achievements=acts,
                           last_active_at=now - timedelta(days=f["active_days"]), salary_min=f["salary_min"], salary_max=f["salary_max"], work_format=f["work_format"])


def main():
    ref_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "best_2026-10-07.py")
    ref = load_score(ref_path)
    worlds = load_worlds(os.path.join(ROOT, "data", "evolve"), seeds=[14])
    now = datetime.now(timezone.utc)
    worst, n, order_mismatch = 0.0, 0, 0
    for w in worlds:
        for need in w["needs"]:
            nd = {"specialization_code": need["spec"], "grade": need["grade"], "stack": need["stack"], "salary_min": need["salary_min"],
                  "salary_max": need["salary_max"], "work_format": need["work_format"]}
            prod, et = [], []
            for f in w["candidates"]:
                lt = (f["theta"], now - timedelta(days=f["theta_days"])) if f["theta"] is not None else None
                p = score_candidate(to_obj(f), nd, {}, lt)["raw_score"]
                e = round(ref(f, need)[0], 4)                           # сырой итог: то же округление, что в боевом коде
                worst = max(worst, abs(p - e)); n += 1
                prod.append((-p, f["id"])); et.append((-e, f["id"]))
            if [x[1] for x in sorted(prod)[:10]] != [x[1] for x in sorted(et)[:10]]:
                order_mismatch += 1
    print(f"пар кандидат—потребность: {n}; наибольшее расхождение итогов: {worst:.4f}; "
          f"потребностей с иным топ-10: {order_mismatch}")


if __name__ == "__main__":
    main()
