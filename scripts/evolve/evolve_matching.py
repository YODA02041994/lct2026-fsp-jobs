#!/usr/bin/env python3
"""Эволюция формулы подбора: модель переписывает EVOLVE-BLOCK, доверенная фитнес-функция оценивает на сохранённых мирах.

Принцип (как в ShinkaEvolve/OpenEvolve): LLM — оператор мутации, фитнес — программа, а не мнение модели.
Обучающие миры — зёрна 11 и 12, отложенный — 13: улучшение засчитывается только если оно видно и на отложенном.

    python scripts/evolve/evolve_matching.py --generations 6 --children 4
"""
from __future__ import annotations
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import llm_client  # noqa: E402
from fitness_matching import load_worlds, load_score, evaluate, keyword_baseline  # noqa: E402

FORBIDDEN = re.compile(r"\b(import|open|exec|eval|compile|__import__|globals|locals|getattr|setattr|os\.|sys\.|subprocess)\b")
IDEAS = [
    "сделай покрытие стека нелинейным: отсутствие одной из двух–трёх ключевых технологий должно резко снижать оценку",
    "учитывай θ относительно порога грейда потребности, а не абсолютное значение",
    "уменьши вес активности и условий, если они мешают точности",
    "заявленная без проверки технология должна весить больше, когда у кандидата высокое θ, и меньше при низком",
    "добавь штраф, если подтверждённых тестом технологий нет вовсе",
    "учитывай долю требуемого стека, покрытую подтверждёнными технологиями, отдельно от общего покрытия",
    "сделай пересечение зарплат градуированным (насколько велико пересечение), а не бинарным",
    "грейд: соседний грейд ниже требуемого штрафуй сильнее, чем соседний выше",
    "комбинируй слагаемые мультипликативно для «обязательных» (стек, грейд) и аддитивно для остальных",
    "ограничь вклад достижений ФСП так, чтобы он не перебивал стек, но решал ничью",
    "различай grade (подтверждённый тестом) и claimed_grade (заявленный): расхождение — признак приукрашивания, снижай доверие к заявленным технологиям",
    "учитывай давность теста theta_days: старое θ должно весить меньше, чем свежее",
    "учитывай широту подтверждённых технологий вне требуемого стека как слабый признак силы кандидата",
    "упрости формулу: убери слагаемые, которые не помогают, и перераспредели их вес",
    "при длинном стеке потребности (6+ технологий) считай покрытие мягче: вес каждой недостающей технологии меньше",
    "сделай силу профиля нелинейной: разница между θ = 0,5 и θ = 1,5 должна значить больше, чем между −2 и −1",
    "ворота стек×грейд: попробуй другие коэффициенты (например 0,35+0,65·stack) или мягкую степень вместо произведения",
    "учитывай число подтверждённых тестом технологий в абсолюте (3 подтверждённые из 8 — сильнее, чем 1 из 2)",
    "проваленная тестом технология должна штрафовать сильнее, чем просто отсутствие",
]
SYSTEM = """Ты улучшаешь функцию ранжирования кандидатов для платформы подбора ИТ-специалистов.
Контракт: функция score(cand, need) -> (total: float, parts: dict). Доступны имена GRADES (список грейдов junior<middle<senior<lead),
SPEC_DISCIPLINE, LEVEL_SCORE и модуль math. Нельзя импортировать модули, читать файлы, использовать exec/eval.
Функция должна быть чистой и детерминированной, работать на любых значениях полей (None допустимы).
cand = {spec, grade, claimed_grade, skills: {код: {confirmed: bool, tested: bool, score: float|None}}, theta: float|None,
theta_days: int|None, fsp: [{level: 'A1'..'A5', discipline}], active_days: int, salary_min, salary_max, work_format}
need = {spec, grade, stack: [коды], salary_min, salary_max, work_format}
Качество измеряется долей релевантных кандидатов в топ-5/топ-10 и nDCG@10 на трёх мирах, где резюме кандидатов
честные, типичные или приукрашенные; истина скрыта (истинные навыки), наблюдаются только признаки выше.
Верни ТОЛЬКО код на Python между строками «# EVOLVE-BLOCK-START» и «# EVOLVE-BLOCK-END», без пояснений."""


def block(src: str) -> str:
    i, j = src.index("# EVOLVE-BLOCK-START"), src.index("# EVOLVE-BLOCK-END")
    return src[i: j + len("# EVOLVE-BLOCK-END")]


def validate_and_eval(code: str, worlds_train, path: str, train_seeds=(11, 12)) -> dict | None:
    if FORBIDDEN.search(code) or "def score(" not in code:
        return None
    header = '"""Кандидат формулы (создан эволюцией)."""\n'
    open(path, "w", encoding="utf-8").write(header + code + "\n")
    # оценка в отдельном процессе с лимитом времени — защита от зацикливания
    try:
        out = subprocess.run([sys.executable, "-c", f"""
import sys, json; sys.path.insert(0, {HERE!r})
from fitness_matching import load_worlds, load_score, evaluate
w = load_worlds({os.path.join(ROOT, 'data', 'evolve')!r}, seeds={train_seeds!r})
print(json.dumps(evaluate(load_score({path!r}), w)))
"""], capture_output=True, text=True, timeout=120)
        if out.returncode != 0:
            return None
        return json.loads(out.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, IndexError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=6)
    ap.add_argument("--children", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "evolve", "run"))
    ap.add_argument("--start", default=None, help="файл с EVOLVE-BLOCK, с которого начинать (по умолчанию score_baseline.py)")
    ap.add_argument("--train-seeds", default="11,12", help="зёрна обучающих миров")
    ap.add_argument("--hold-seeds", default="13", help="зёрна отложенных миров (только для контроля, не для отбора)")
    ap.add_argument("--patience", type=int, default=0, help="остановиться, если лучший по обучению не улучшался столько поколений (0 — не останавливаться)")
    args = ap.parse_args()
    start_path = args.start or os.path.join(HERE, "score_baseline.py")
    os.makedirs(args.out, exist_ok=True)
    worlds_dir = os.path.join(ROOT, "data", "evolve")
    train_seeds = [int(x) for x in args.train_seeds.split(",")]; hold_seeds = [int(x) for x in args.hold_seeds.split(",")]
    train = load_worlds(worlds_dir, seeds=train_seeds); hold = load_worlds(worlds_dir, seeds=hold_seeds)
    print(f"обучение: зёрна {train_seeds} ({len(train)} миров); отложенный: {hold_seeds} ({len(hold)} миров)")
    base_src = open(start_path, encoding="utf-8").read()
    base_code = block(base_src)
    base_fit = evaluate(load_score(start_path), train)
    base_hold = evaluate(load_score(start_path), hold)
    kw_train = evaluate(keyword_baseline, train); kw_hold = evaluate(keyword_baseline, hold)
    log = open(os.path.join(args.out, "log.jsonl"), "a", encoding="utf-8")
    pop = [{"id": "base", "code": base_code, "fit": base_fit, "hold": base_hold}]
    print(f"базовая: train {base_fit['fitness']:.4f} (P@5 {base_fit['p5']:.2f}, nDCG {base_fit['ndcg']:.2f}) | holdout {base_hold['fitness']:.4f} | слова резюме train {kw_train['fitness']:.4f} hold {kw_hold['fitness']:.4f}")
    rng = random.Random(42)
    counter = 0
    best_seen, stale = pop[0]["fit"]["fitness"], 0
    for g in range(1, args.generations + 1):
        parents = sorted(pop, key=lambda x: -x["fit"]["fitness"])[:3]
        children = []
        for ci in range(args.children):
            parent = parents[min(ci, len(parents) - 1)] if ci < 2 else rng.choice(parents)
            ideas = rng.sample(IDEAS, 2)
            per = "\n".join(f"  {k}: P@5 {v['p5']:.2f}, P@10 {v['p10']:.2f}, nDCG {v['ndcg']:.2f}" for k, v in parent["fit"]["per_world"].items())
            user = (f"Текущая программа (fitness {parent['fit']['fitness']:.4f}; по мирам:\n{per}\n):\n\n{parent['code']}\n\n"
                    f"Предложи улучшенный вариант. Идеи для этой попытки: {ideas[0]}; {ideas[1]}. "
                    f"Сохрани структуру parts с ключами stack, grade, strength, fsp, activity, conditions (значения 0…1).")
            try:
                txt = llm_client.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], max_tokens=3000, temperature=0.8)
            except Exception as e:  # noqa: BLE001
                print("модель:", e); continue
            code = llm_client.extract_code(txt)
            if "# EVOLVE-BLOCK-START" in code and "# EVOLVE-BLOCK-END" in code:
                code = block(code)
            counter += 1
            cid = f"g{g}c{ci}"
            fit = validate_and_eval(code, train, os.path.join(args.out, f"cand_{cid}.py"), train_seeds)
            rec = {"id": cid, "parent": parent["id"], "ideas": ideas, "ok": fit is not None, "fitness": fit["fitness"] if fit else None}
            log.write(json.dumps(rec, ensure_ascii=False) + "\n"); log.flush()
            if fit:
                hold_fit = evaluate(load_score(os.path.join(args.out, f"cand_{cid}.py")), hold)
                children.append({"id": cid, "code": code, "fit": fit, "hold": hold_fit})
                print(f"  {cid} ← {parent['id']}: train {fit['fitness']:.4f} | holdout {hold_fit['fitness']:.4f}  ({ideas[0][:50]}…)")
            else:
                print(f"  {cid} ← {parent['id']}: отклонён валидатором")
        pop = sorted(pop + children, key=lambda x: -x["fit"]["fitness"])[:6]
        best = pop[0]
        print(f"поколение {g}: лучший {best['id']} train {best['fit']['fitness']:.4f} holdout {best['hold']['fitness']:.4f}; расход ${llm_client.cost_usd()}", flush=True)
        if best["fit"]["fitness"] > best_seen + 1e-4:
            best_seen, stale = best["fit"]["fitness"], 0
        else:
            stale += 1
            if args.patience and stale >= args.patience:
                print(f"плато: {stale} поколений без улучшения — остановка", flush=True)
                break
    best = pop[0]
    open(os.path.join(args.out, "best.py"), "w", encoding="utf-8").write('"""Лучшая формула по итогам эволюции."""\n' + best["code"] + "\n")
    summary = {"base": {"train": base_fit["fitness"], "hold": base_hold["fitness"]}, "best": {"id": best["id"], "train": best["fit"]["fitness"], "hold": best["hold"]["fitness"],
               "per_world_hold": best["hold"]["per_world"]}, "keyword_baseline": {"train": kw_train["fitness"], "hold": kw_hold["fitness"]},
               "llm_calls": counter, "cost_usd": llm_client.cost_usd(), "spend": llm_client.SPEND}
    json.dump(summary, open(os.path.join(args.out, "summary.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
