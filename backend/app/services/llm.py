"""Внешняя модель через OpenAI-совместимый интерфейс. Необязательна: без ключа все вызовы возвращают None,
и вызывающий код работает правилами. Персональные данные вырезаются до вызова (см. resume.deidentify).
Расход считается и пишется в журнал: токены и примерная стоимость."""
from __future__ import annotations
import json
import logging
import os
import time
import httpx
from ..config import get_settings

log = logging.getLogger("fsp.llm")
PRICE_PER_M = {"input": 0.14, "output": 0.28}      # долларов за миллион токенов, DeepSeek V4.1 Flash, ориентир
_spend = {"calls": 0, "input": 0, "output": 0}


def enabled() -> bool:
    s = get_settings()
    return bool(s.llm_base_url and s.llm_api_key and s.llm_model)


def chat(messages: list[dict], *, json_mode: bool = False, max_tokens: int = 1200, temperature: float = 0.2, timeout: float = 60) -> str | None:
    """→ текст ответа или None при любой ошибке/отсутствии настроек."""
    s = get_settings()
    if not enabled():
        return None
    body = {"model": s.llm_model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
            "thinking": {"type": "disabled"}}     # рассуждения выключены: иначе они съедают лимит токенов
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    t0 = time.time()
    try:
        r = httpx.post(s.llm_base_url.rstrip("/") + "/chat/completions", json=body, timeout=timeout,
                       headers={"Authorization": f"Bearer {s.llm_api_key}", "Content-Type": "application/json"})
        r.raise_for_status()
        d = r.json()
        u = d.get("usage", {})
        _spend["calls"] += 1
        _spend["input"] += u.get("prompt_tokens", 0)
        _spend["output"] += u.get("completion_tokens", 0)
        log.info("llm ok %.1fs in=%s out=%s", time.time() - t0, u.get("prompt_tokens"), u.get("completion_tokens"))
        return d["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        log.warning("llm failed: %s", e)
        return None


def chat_json(messages: list[dict], **kw) -> dict | None:
    txt = chat(messages, json_mode=True, **kw)
    if not txt:
        return None
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        start, end = txt.find("{"), txt.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(txt[start:end + 1])
            except json.JSONDecodeError:
                return None
        return None


def spend() -> dict:
    cost = (_spend["input"] * PRICE_PER_M["input"] + _spend["output"] * PRICE_PER_M["output"]) / 1e6
    return {**_spend, "usd_estimate": round(cost, 4)}
