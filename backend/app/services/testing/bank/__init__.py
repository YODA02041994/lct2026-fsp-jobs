"""Банк шаблонов. Модули регистрируют шаблоны при импорте."""
from .base import REGISTRY, TemplateSpec, Instance, template, shuffle_options, check_answer, instance_to_payload, GRADE_DIFFICULTY  # noqa: F401


def load_all() -> dict:
    from . import common, backend, frontend, data, qa  # noqa: F401
    return REGISTRY
