"""Health, readiness and standards endpoints."""

import logging
import sqlite3

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.core.standards_registry import (
    CALIBRATED_CATEGORIES,
    CATEGORY_CALIBRATION_SPECS,
    STANDARDS_REGISTRY,
    STANDARDS_REGISTRY_VERSION,
)
from backend.database import check_db

logger = logging.getLogger("eatgood.meta")
router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    """Liveness: the process is up."""
    return {"status": "ok", "service": "EATGOOD API"}


@router.get("/ready")
def ready():
    """Readiness: the database is reachable. Returns 503 otherwise.

    The product catalogue lives in Open Food Facts; its availability is reported per request.
    """
    checks = {"database": "ok"}
    try:
        check_db()
    except sqlite3.Error as exc:
        logger.error("Readiness check: database unreachable: %r", exc)
        checks["database"] = "unreachable"
    is_ready = all(v == "ok" for v in checks.values())
    body = {"status": "ready" if is_ready else "not_ready", "checks": checks}
    return JSONResponse(status_code=200 if is_ready else 503, content=body)


@router.get("/standards")
def standards():
    return {
        "standards_version": STANDARDS_REGISTRY_VERSION,
        "calibrated_categories": CALIBRATED_CATEGORIES,
        "category_specs": CATEGORY_CALIBRATION_SPECS,
        "total_standards": len(STANDARDS_REGISTRY),
        "standards": STANDARDS_REGISTRY,
    }

