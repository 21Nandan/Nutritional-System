"""
EATGOOD — Centralized configuration.
Every setting is read once from the environment and validated at import time,
so a misconfigured deployment fails at startup instead of on the first request.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def _load_local_env_file(path: Path) -> None:
    """Locally, read KEY=value lines from .env (git-ignored) without overriding real environment variables.
    On Vercel the variables come from the project settings instead."""
    if IS_SERVERLESS or not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env_file(BASE_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in ("1", "true", "yes"):
        return True
    if value in ("0", "false", "no"):
        return False
    raise RuntimeError(f"Environment variable {name} must be true/false, got {raw!r}")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be a number, got {raw!r}") from exc


ENVIRONMENT = os.environ.get("EATGOOD_ENV", "development").lower()
if ENVIRONMENT not in ("development", "test", "production"):
    raise RuntimeError(f"EATGOOD_ENV must be development, test or production, got {ENVIRONMENT!r}")

# SQLite only holds caches and unmoderated user contributions (no personal data).
# The serverless filesystem is read-only except /tmp, and /tmp is per-instance and ephemeral.
# Vercel only allows writes under /tmp; no personal data is stored there.
_SERVERLESS_DB = "/tmp/eatgood_app.db"  # noqa: S108  # nosec B108
DB_PATH = Path(os.environ.get("EATGOOD_DB_PATH") or (_SERVERLESS_DB if IS_SERVERLESS else DATA_DIR / "eatgood_app.db"))

# Allowed CORS origins. The production frontend is served from the same origin as the API,
# so cross-origin access is only needed for the local Vite dev server.
_DEFAULT_CORS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_custom_cors = os.environ.get("EATGOOD_CORS_ORIGINS")
CORS_ORIGINS: list[str] = (
    [origin.strip() for origin in _custom_cors.split(",") if origin.strip()] if _custom_cors else _DEFAULT_CORS
)
if "*" in CORS_ORIGINS:
    raise RuntimeError("EATGOOD_CORS_ORIGINS must list explicit origins; '*' is not allowed.")


# Open Food Facts API v3
OFF_BASE_URL = os.environ.get("OFF_BASE_URL", "https://world.openfoodfacts.org/api/v3/product")
OFF_USER_AGENT = os.environ.get(
    "OFF_USER_AGENT",
    "EATGOOD/1.1 (+https://github.com/21Nandan/Nutritional-System)",
)
OFF_TIMEOUT_SECONDS = _env_float("OFF_TIMEOUT_SECONDS", 8.0)
OFF_CACHE_TTL_HOURS = _env_int("OFF_CACHE_TTL_HOURS", 168)

# Rate limiting (requests per minute per client IP, per server instance)
RATE_LIMIT_ENABLED = _env_bool("EATGOOD_RATE_LIMIT", True)
RATE_LIMIT_OFF_SEARCH_RPM = _env_int("RATE_LIMIT_OFF_SEARCH_RPM", 60)  # search-as-you-type
RATE_LIMIT_OFF_RPM = _env_int("RATE_LIMIT_OFF_RPM", 45)
RATE_LIMIT_CONTRIB_RPM = _env_int("RATE_LIMIT_CONTRIB_RPM", 30)
RATE_LIMIT_AI_RPM = _env_int("RATE_LIMIT_AI_RPM", 6)

# Google Gemini (optional; without a key every feature uses its non-Gemini fallback). Defaults suit the
# free tier: Flash-Lite reads photos and answers questions (about 2 s per photo, and it read labels and
# claims as well as Flash in testing, while Flash was often overloaded), with a daily cap on calls.
# The "-latest" aliases follow Google's current models, so a retired version doesn't break the app.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-flash-lite-latest")
# Used when the main model times out or is overloaded (it then rests for a few minutes).
GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.1-flash-lite")
GEMINI_DAILY_LIMIT = _env_int("GEMINI_DAILY_LIMIT", 200)
GEMINI_COOLDOWN_SECONDS = _env_int("GEMINI_COOLDOWN_SECONDS", 60)
GEMINI_TIMEOUT_SECONDS = _env_float("GEMINI_TIMEOUT_SECONDS", 6.0)  # two tries still fit Vercel's 15 s limit
