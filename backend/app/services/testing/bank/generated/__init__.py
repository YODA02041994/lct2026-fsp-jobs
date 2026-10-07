"""Шаблоны, предложенные моделью (scripts/evolve/propose_templates.py). Статус — черновик до просмотра человеком.

Пакет импортирует все модули своей папки, кроме начинающихся с «_» (служебные файлы и кандидаты на проверке),
поэтому удаление файла шаблона после просмотра ничего не ломает. В боевой банк эти шаблоны попадают только после
строки `from . import generated  # noqa: F401` в load_all() (bank/__init__.py) — пока её нет, кандидаты их не видят.
Реестр принятых — REGISTRY.md рядом.
"""
from __future__ import annotations
import importlib
import pkgutil

MODULES: list[str] = []
for _m in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
    if not _m.name.startswith("_"):
        importlib.import_module(f"{__name__}.{_m.name}")
        MODULES.append(_m.name)
