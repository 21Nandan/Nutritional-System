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
