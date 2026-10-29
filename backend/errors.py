"""Consistent error responses: {"detail": {"error_code": ..., "message": ...}} with a plain-language message."""

import logging
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger("eatgood.errors")


def product_not_found_error(product_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"error_code": "PRODUCT_NOT_FOUND", "message": f"We couldn't find a product with the ID {product_id!r}."},
    )


def off_unavailable_error(result: dict[str, Any]) -> HTTPException:
    """Maps an Open Food Facts failure to an HTTP error. Technical detail is logged, never returned."""
    logger.warning("Open Food Facts unavailable: code=%s detail=%s", result["error_code"], result.get("technical_detail"))
    return HTTPException(
        status_code=result["http_status"],
        detail={"error_code": result["error_code"], "message": result["message"], "barcode": result.get("barcode")},
    )
