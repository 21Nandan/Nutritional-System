"""
EATGOOD — Centralized Configuration Management
Loads environment variables safely with sensible defaults for local development,
testing, and production environments.
"""

import os
from typing import List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Environment mode
ENVIRONMENT = os.environ.get("EATGOOD_ENV", os.environ.get("ENVIRONMENT", "development")).lower()
DEBUG = os.environ.get("EATGOOD_DEBUG", "false" if ENVIRONMENT == "production" else "true").lower() in ["1", "true", "yes"]

# Server settings
HOST = os.environ.get("EATGOOD_HOST", "127.0.0.1")
PORT = int(os.environ.get("EATGOOD_PORT", "8000"))

# Allowed CORS Origins
_DEFAULT_CORS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
custom_cors = os.environ.get("EATGOOD_CORS_ORIGINS")
if custom_cors:
    CORS_ORIGINS: List[str] = [origin.strip() for origin in custom_cors.split(",") if origin.strip()]
else:
    CORS_ORIGINS: List[str] = _DEFAULT_CORS

# Security & Upload Constraints
MAX_UPLOAD_SIZE_MB = int(os.environ.get("EATGOOD_MAX_UPLOAD_MB", "10"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]
ALLOWED_IMAGE_MIME_TYPES = ["image/png", "image/jpeg", "image/webp"]

# Upload Directory Configuration (Serverless / Read-Only Filesystem Safe)
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    UPLOAD_DIR = "/tmp/eatgood_uploads"
else:
    UPLOAD_DIR = os.environ.get("EATGOOD_UPLOAD_DIR", os.path.join(BASE_DIR, "data", "uploads"))

# Open Food Facts API v3 Configuration
OFF_BASE_URL = os.environ.get("OFF_BASE_URL", "https://world.openfoodfacts.org/api/v3/product")
OFF_USER_AGENT = os.environ.get(
    "OFF_USER_AGENT",
    "EATGOOD-NutritionScanner/1.0 (local-desktop; dev@eatgood.local)"
)
OFF_TIMEOUT_SECONDS = float(os.environ.get("OFF_TIMEOUT_SECONDS", "8.0"))
OFF_CACHE_TTL_HOURS = int(os.environ.get("OFF_CACHE_TTL_HOURS", "168"))  # 7 days

# Rate Limiting Configuration
RATE_LIMIT_ENABLED = os.environ.get("EATGOOD_RATE_LIMIT", "true").lower() in ["1", "true", "yes"]
RATE_LIMIT_OCR_RPM = int(os.environ.get("RATE_LIMIT_OCR_RPM", "20"))
RATE_LIMIT_OFF_RPM = int(os.environ.get("RATE_LIMIT_OFF_RPM", "45"))
RATE_LIMIT_CONTRIB_RPM = int(os.environ.get("RATE_LIMIT_CONTRIB_RPM", "30"))
