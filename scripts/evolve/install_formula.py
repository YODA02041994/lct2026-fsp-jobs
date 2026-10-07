#!/usr/bin/env python3
"""Устанавливает формулу подбора из файла эволюции в боевой код — одной командой, без ручного переноса.

    python scripts/evolve/install_formula.py data/evolve/run3/best.py --ref best_2026-10-07b --note "заход 3, особь g12c0"

1. Берёт EVOLVE-BLOCK из файла.
2. Пишет backend/app/services/matching_formula.py: тот же код плюс параметр weights (работодатель может переопределить веса).
3. DEFAULT_WEIGHTS в backend/app/catalog.py = WEIGHTS формулы.
4. Копирует эталон в scripts/evolve/<ref>.py — по нему scripts/evolve/check_port.py сверяет боевой код.
"""
from __future__ import annotations
import argparse
import ast
import datetime as dt
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

HEADER = '''"""Формула подбора — EVOLVE-BLOCK, установленный scripts/evolve/install_formula.py
из {src} ({note}, {date}). Эталон для сверки: scripts/evolve/{ref}.py.

Не править руками: изменения делаются эволюцией (scripts/evolve/evolve_matching.py) и повторной установкой.
Вход: cand и need — словари наблюдаемых признаков (см. matching.candidate_features и matching.need_features),
weights — переопределение весов работодателем. Выход: (сырой итог, слагаемые 0…1).
"""
from __future__ import annotations
import math  # noqa: F401  (доступен формуле)
from ..models import GRADES  # noqa: F401

LEVEL_SCORE = {{"A1": 0.2, "A2": 0.4, "A3": 0.6, "A4": 0.8, "A5": 1.0}}
# какая дисциплина спортивного программирования ближе к специализации
SPEC_DISCIPLINE = {{"backend": {{"algorithmic", "product"}}, "frontend": {{"product"}}, "fullstack": {{"product"}}, "mobile": {{"product"}},
                   "data": {{"algorithmic", "product"}}, "devops": {{"product", "security"}}, "qa": {{"product"}}, "analytics": {{"product"}},
                   "security": {{"security"}}}}

'''


def block(src: str) -> str:
    i, j = src.index("# EVOLVE-BLOCK-START"), src.index("# EVOLVE-BLOCK-END")
    return src[i: j + len("# EVOLVE-BLOCK-END")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--ref", required=True, help="имя эталона в scripts/evolve/ без .py")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    src = open(args.source, encoding="utf-8").read()
    code = block(src)
    m = re.search(r"^WEIGHTS\s*=\s*(\{.*\})\s*$", code, re.M)
    if not m:
        raise SystemExit("в блоке нет строки WEIGHTS = {...}")
    weights = ast.literal_eval(m.group(1))
    if "def score(cand, need):" not in code:
        raise SystemExit("ожидалась сигнатура def score(cand, need):")
    head, body = code.split("def score(cand, need):", 1)
    body = body.replace('WEIGHTS["', 'w["')
    code2 = head + "def score(cand, need, weights=None):\n    w = {**WEIGHTS, **(weights or {})}" + body
    compile(code2, "matching_formula", "exec")
    out = os.path.join(ROOT, "backend", "app", "services", "matching_formula.py")
    rel_src = os.path.relpath(os.path.abspath(args.source), ROOT)
    open(out, "w", encoding="utf-8").write(HEADER.format(src=rel_src, note=args.note or "без пометки", date=dt.date.today().isoformat(), ref=args.ref) + code2 + "\n")
    cat = os.path.join(ROOT, "backend", "app", "catalog.py")
    s = open(cat, encoding="utf-8").read()
    s2, n = re.subn(r"^DEFAULT_WEIGHTS = \{.*$", "DEFAULT_WEIGHTS = " + repr(weights) + f"   # веса формулы подбора ({args.ref}), ставит install_formula.py", s, flags=re.M)
    if n != 1:
        raise SystemExit("в catalog.py не найдена строка DEFAULT_WEIGHTS")
    open(cat, "w", encoding="utf-8").write(s2)
    ref_path = os.path.join(HERE, args.ref + ".py")
    if os.path.abspath(args.source) != os.path.abspath(ref_path):
        shutil.copyfile(args.source, ref_path)
        txt = open(ref_path, encoding="utf-8").read()
        if txt.startswith('"""Лучшая формула по итогам эволюции."""'):
            txt = txt.replace('"""Лучшая формула по итогам эволюции."""',
                              f'"""Эталон формулы подбора: {args.note or args.ref}. Установлен в backend/app/services/matching_formula.py '
                              f'командой install_formula.py {dt.date.today().isoformat()}; сверка — check_port.py."""', 1)
            open(ref_path, "w", encoding="utf-8").write(txt)
    print(f"установлено: {out}\nвеса: {weights}\nэталон: {ref_path}")


if __name__ == "__main__":
    main()
