"""
Google Gemini, called only from the server (the key never reaches the browser).

Gemini reads things (label photos, claim photos) and phrases answers; it never scores. Every caller
has a non-Gemini fallback, and generate_json() returns None instead of raising, so a missing key,
an outage or a used-up quota quietly falls back.

Built for the free tier's limits: results are cached by input, replies are short with thinking off,
a daily budget caps calls, and a "too many requests" reply pauses Gemini for a while.
"""

import base64
import hashlib
import json
import logging
import threading
import time
from typing import Any

import httpx

from backend.config import (
    GEMINI_API_KEY,
    GEMINI_COOLDOWN_SECONDS,
    GEMINI_DAILY_LIMIT,
    GEMINI_FALLBACK_MODEL,
    GEMINI_MODEL,
    GEMINI_TEXT_MODEL,
    GEMINI_TIMEOUT_SECONDS,
)

logger = logging.getLogger("eatgood")

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
CACHE_TTL_SECONDS = 24 * 3600
CACHE_MAX_ITEMS = 500

_lock = threading.Lock()
_cache: dict[str, tuple[float, Any]] = {}
_budget = {"day": "", "used": 0}
_paused_until = 0.0
# Models resting after timeouts or overload (model -> time), and how long they rest.
_model_rest_until: dict[str, float] = {}
MODEL_REST_SECONDS = 300
# Models that reject the thinking setting (lite models don't think anyway); learned on first use.
_no_thinking_config: set[str] = set()


def is_available() -> bool:
    """Whether a call could be made now (key set, not paused, budget left)."""
    if not GEMINI_API_KEY:
        return False
    with _lock:
        _roll_day()
        return time.time() >= _paused_until and _budget["used"] < GEMINI_DAILY_LIMIT


def _roll_day() -> None:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if _budget["day"] != today:
        _budget.update(day=today, used=0)


def _cache_get(key: str) -> Any:
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
            return hit[1]
        _cache.pop(key, None)
        return None


def _cache_put(key: str, value: Any) -> None:
    with _lock:
        if len(_cache) >= CACHE_MAX_ITEMS:
            _cache.pop(next(iter(_cache)))  # oldest first
        _cache[key] = (time.time(), value)


def _models_to_try(primary: str) -> list[str]:
    """The model first, then the backup; a model resting after timeouts or overload is skipped."""
    now = time.time()
    order = list(dict.fromkeys([primary, GEMINI_FALLBACK_MODEL]))
    return [m for m in order if m and _model_rest_until.get(m, 0) <= now] or order[-1:]


def _call(model: str, parts: list[dict[str, Any]], schema: dict[str, Any], max_output_tokens: int,
          client: httpx.Client | None) -> tuple[str, Any]:
    """("ok", parsed reply) or (reason, None), reason being "rate_limited", "slow" or "failed"."""
    config: dict[str, Any] = {
        "temperature": 0.1,
        "maxOutputTokens": max_output_tokens,
        "responseMimeType": "application/json",
        "responseSchema": schema,
    }
    if model not in _no_thinking_config:
        config["thinkingConfig"] = {"thinkingBudget": 0}  # thinking would use up the short reply budget
    body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": config}
    try:
        http = client or httpx.Client(timeout=GEMINI_TIMEOUT_SECONDS)
        try:
            url, headers = API_URL.format(model=model), {"x-goog-api-key": GEMINI_API_KEY}
            response = http.post(url, json=body, headers=headers)
            if response.status_code == 400 and "thinkingConfig" in config:
                # This model doesn't accept the thinking setting: retry once without it, and remember.
                _no_thinking_config.add(model)
                config.pop("thinkingConfig")
                response = http.post(url, json=body, headers=headers)
        finally:
            if client is None:
                http.close()
    except httpx.TimeoutException:
        return "slow", None
    except httpx.HTTPError as exc:
        logger.warning("gemini request failed: %s", type(exc).__name__)
        return "failed", None
    if response.status_code == 429:
        return "rate_limited", None
    if response.status_code in (500, 503, 504):
        return "slow", None
    if response.status_code != 200:
        logger.warning("gemini returned HTTP %s", response.status_code)
        return "failed", None
    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return "ok", json.loads(text)
    except (ValueError, KeyError, IndexError, TypeError):
        logger.warning("gemini reply was not the expected JSON")
        return "failed", None


def image_part(image_b64: str, mime_type: str) -> dict[str, Any]:
    return {"inline_data": {"mime_type": mime_type, "data": image_b64}}


def generate_json(
    prompt: str,
    schema: dict[str, Any],
    *,
    image: dict[str, Any] | None = None,
    text_only: bool = False,
    max_output_tokens: int = 512,
    client: httpx.Client | None = None,
) -> Any:
    """Gemini's reply parsed as JSON matching schema, or None when Gemini can't be used or fails."""
    if not GEMINI_API_KEY:
        return None
    primary = GEMINI_TEXT_MODEL if text_only else GEMINI_MODEL
    key_material = json.dumps([text_only, prompt, schema, image["inline_data"]["data"] if image else None], sort_keys=True)
    cache_key = hashlib.sha256(key_material.encode()).hexdigest()
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    global _paused_until
    with _lock:
        _roll_day()
        if time.time() < _paused_until or _budget["used"] >= GEMINI_DAILY_LIMIT:
            return None
        _budget["used"] += 1

    parts: list[dict[str, Any]] = [{"text": prompt}]
    if image:
        parts.append(image)
    result = None
    for model in _models_to_try(primary):
        outcome, result = _call(model, parts, schema, max_output_tokens, client)
        if outcome == "ok":
            break
        if outcome == "rate_limited":
            with _lock:
                _paused_until = time.time() + GEMINI_COOLDOWN_SECONDS
            logger.warning("gemini rate limited; pausing for %ss", GEMINI_COOLDOWN_SECONDS)
            return None
        if outcome == "slow":
            # Timed out or overloaded: rest this model for a while and try the backup straight away.
            with _lock:
                _model_rest_until[model] = time.time() + MODEL_REST_SECONDS
            logger.warning("gemini model %s slow or overloaded; resting it for %ss", model, MODEL_REST_SECONDS)
            continue
        return None  # bad request or unexpected reply: the caller falls back
    if result is None:
        return None
    _cache_put(cache_key, result)
    return result


def decode_image(image_b64: str) -> bytes | None:
    """The image bytes, or None if the text isn't valid base64."""
    try:
        return base64.b64decode(image_b64, validate=True)
    except ValueError:
        return None
