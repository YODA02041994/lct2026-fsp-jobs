"""Потребность без грейда и банк без потребности: оценка относительно собственного грейда и доля от достижимого."""
import os, sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.services.matching import score_candidate


def _cand(grade, theta_days=3, skills=("python",), fsp=False, active_days=1):
    now = datetime.now(timezone.utc)
    acts = [SimpleNamespace(hidden=False, status="active", trust_level="source", level_code="A4", discipline="product", title="Призёр")] if fsp else []
    return SimpleNamespace(id=1, specialization_code="backend", grade=grade, claimed_grade=grade,
                           skills=[SimpleNamespace(skill=s, confirmed_by_test=True, test_score=0.9) for s in skills], achievements=acts,
                           last_active_at=now - timedelta(days=active_days), salary_min=None, salary_max=None, work_format=None), (0.3, now - timedelta(days=theta_days))


def test_need_without_grade_scores_each_against_own_grade():
    """Без грейда в потребности кандидат сравнивается со своим подтверждённым грейдом, а не с грейдом по умолчанию:
    у каждого грейда при θ на ожидаемом уровне слагаемое грейда = 1 (раньше junior против «senior по умолчанию» получал 0)."""
    need = {"stack": ["python"], "grade": None}
    expected_theta = {"junior": -1.5, "middle": -0.17, "senior": 1.17, "lead": 2.5}
    for g, th in expected_theta.items():
        c, (_, fin) = _cand(g)
        r = score_candidate(c, need, {}, (th, fin))
        assert r["parts"]["grade"] == 1.0, (g, r["parts"])
        assert r["parts"]["stack"] > 0.8, (g, r["parts"])


def test_bank_without_need_is_share_of_max():
    need = {"stack": [], "grade": None}
    strong, lt_s = _cand("senior", theta_days=1, fsp=True, active_days=0)
    weak, lt_w = _cand("senior", theta_days=400, fsp=False, active_days=120)
    s1 = score_candidate(strong, need, {}, lt_s)
    s2 = score_candidate(weak, need, {}, lt_w)
    assert 0 < s2["score"] < s1["score"] <= 1.0
    assert s1["score"] > 0.5, s1                     # сильный профиль заметно выше середины шкалы
