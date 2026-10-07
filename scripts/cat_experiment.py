"""Эксперимент: адаптивный выбор каждого задания по текущей оценке θ (CAT) против блоков. Та же модель ответа, что в валидации.
Итог (docs/08, «Почему блоки»): выигрыша нет. Запуск: python scripts/cat_experiment.py"""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.environ.setdefault("FSP_DATABASE_URL", "sqlite:///:memory:"); os.environ.setdefault("FSP_SECRET_KEY", "cat")
from app.services.testing.engine import REGISTRY, load_all, eap, grade_from_theta, decide, GRADES, pick_templates, next_level_after_block
from app import synth
load_all()
SPEC_BANK = {"backend", "frontend", "data", "qa"}

def p_correct(theta, code, rng):
    t = REGISTRY[code]; p = 1 / (1 + math.exp(-(theta - t.difficulty)))
    if t.fmt in ("choice", "multichoice"):
        inst = t.generate(random.Random(rng.randrange(1, 10**9))); n = len(inst.options or []) or 5
        g = 1 / n if t.fmt == "choice" else 1 / (n * 2); p = g + (1 - g) * p
    return rng.random() < p

def eligible(spec, skills):
    out = []
    for code, t in REGISTRY.items():
        spec_match = spec in t.specializations; common = not t.specializations
        if spec_match or common:
            out.append((code, 2 if spec_match and (set(skills) & set(t.technologies)) else 1 if spec_match else 0))
    return out

def run_cat(theta, spec, claimed, skills, rng, n_items=10, sd_stop=0.0):
    from app.services.testing.engine import GRADE_DIFFICULTY
    th = GRADE_DIFFICULTY[claimed]; sd = 1.0; used = set(); resp = []
    pool = eligible(spec, skills)
    for i in range(n_items):
        # кандидаты: ближайшие по сложности к текущей оценке, приоритет своей специализации и заявленных технологий
        cands = [(abs(REGISTRY[c].difficulty - th) - 0.25 * pr + rng.uniform(0, 0.15), c) for c, pr in pool if c not in used]
        cands.sort(); code = cands[0][1]; used.add(code)
        ok = p_correct(theta, code, rng); resp.append((REGISTRY[code].difficulty, ok))
        th, sd = eap(resp)
        if sd_stop and sd < sd_stop and i >= 7: break
    return th, sd, len(resp)

def run_blocks(theta, spec, claimed, skills, rng, bs=5, nb=2):
    level = claimed; used = set(); resp = []
    for b in range(1, nb + 1):
        codes = pick_templates(spec, level, skills, bs, rng, exclude=used, has_bank=True); used |= set(codes)
        corr = 0
        for c in codes:
            ok = p_correct(theta, c, rng); corr += ok; resp.append((REGISTRY[c].difficulty, ok))
        out = next_level_after_block(level, corr, len(codes), b, nb)
        if out.next_level is None: break
        level = out.next_level
    th, sd = eap(resp); return th, sd, len(resp)

rng = random.Random(5); events = synth.load_events()
cands = [c for c in synth.make_candidates(300, rng, events) if c.specialization in SPEC_BANK]
for name, fn in (("блоки 2×5", lambda c, r: run_blocks(c.theta, c.specialization, c.claimed_grade, c.declared_stack, r)),
                 ("CAT 10 заданий", lambda c, r: run_cat(c.theta, c.specialization, c.claimed_grade, c.declared_stack, r)),
                 ("CAT 8–12, стоп sd<0,45", lambda c, r: run_cat(c.theta, c.specialization, c.claimed_grade, c.declared_stack, r, 12, 0.45)),
                 ("CAT 15", lambda c, r: run_cat(c.theta, c.specialization, c.claimed_grade, c.declared_stack, r, 15))):
    exact = agree = 0; err = 0; items = 0; adj = 0
    for c in cands:
        r = random.Random(c.idx * 31 + 7)
        t1, s1, n1 = fn(c, r); t2, s2, n2 = fn(c, r)
        g1, g2 = grade_from_theta(t1), grade_from_theta(t2)
        exact += g1 == c.true_grade; adj += abs(GRADES.index(g1) - GRADES.index(c.true_grade)) <= 1
        agree += g1 == g2; err += abs(t1 - c.theta); items += n1
    n = len(cands)
    print(f"{name:26} точно {exact/n:.2f}  ±1 {adj/n:.2f}  согласованность {agree/n:.2f}  |θ̂−θ| {err/n:.2f}  заданий {items/n:.1f}")
