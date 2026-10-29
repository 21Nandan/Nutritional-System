"""Health, readiness, dataset, standards and data-quality endpoints."""

import logging
import sqlite3

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.core.data_loader import data_loader
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
    """Liveness: the process is up and the catalogue loaded at startup (startup fails otherwise)."""
    return {"status": "ok", "service": "EATGOOD API", "products_count": len(data_loader.products_df)}


@router.get("/ready")
def ready():
    """Readiness: catalogue non-empty and database reachable. Returns 503 otherwise."""
    checks = {"catalogue": "ok", "database": "ok"}
    if len(data_loader.products_df) == 0:
        checks["catalogue"] = "empty"
    try:
        check_db()
    except sqlite3.Error as exc:
        logger.error("Readiness check: database unreachable: %r", exc)
        checks["database"] = "unreachable"
    is_ready = all(v == "ok" for v in checks.values())
    body = {"status": "ready" if is_ready else "not_ready", "checks": checks, "products_count": len(data_loader.products_df)}
    return JSONResponse(status_code=200 if is_ready else 503, content=body)


@router.get("/dataset")
def dataset():
    return {**data_loader.dataset_info(), "standards_version": STANDARDS_REGISTRY_VERSION}


@router.get("/standards")
def standards():
    return {
        "standards_version": STANDARDS_REGISTRY_VERSION,
        "calibrated_categories": CALIBRATED_CATEGORIES,
        "category_specs": CATEGORY_CALIBRATION_SPECS,
        "total_standards": len(STANDARDS_REGISTRY),
        "standards": STANDARDS_REGISTRY,
    }


@router.get("/audit")
def audit():
    return data_loader.get_audit_metrics()
