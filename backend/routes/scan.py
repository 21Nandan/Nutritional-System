"""Barcode lookup, manual assessment and user contributions."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.core.barcode_utils import validate_barcode
from backend.core.nutrition_scoring import run_full_product_assessment
from backend.core.rate_limiter import enforce_rate_limit
from backend.database import get_user_contribution_by_barcode, record_user_contribution
from backend.errors import off_unavailable_error
from backend.products import NUTRIENT_FIELDS, UNVERIFIED_CONTRIBUTION_STATUS, contribution_to_product, fetch_off_product
from backend.profile import get_request_profile
from backend.schemas import ManualNutritionInput, ProductContributionRequest

logger = logging.getLogger("eatgood.scan")
router = APIRouter(prefix="/api")


def _found(source: str, product: dict, profile: dict, val: dict, message: str) -> dict:
    assessment = run_full_product_assessment(product, profile)
    assessment["profile_source"] = profile["profile_source"]
    return {
        "status": "found",
        "source": source,
        "barcode": val["normalized"],
        "barcode_format": val["format"],
        "check_digit_valid": val["check_digit_valid"],
        "product": product,
        "assessment": assessment,
        "data_confidence_status": product.get("data_confidence_status"),
        "openfoodfacts_attribution": product.get("openfoodfacts_attribution"),
        "message": message,
    }


@router.get("/products/barcode/{barcode}")
def lookup_barcode(barcode: str, request: Request, profile: dict = Depends(get_request_profile)):
    """Unmoderated user contribution → Open Food Facts (cached, then live)."""
    enforce_rate_limit(request, "off_barcode")

    val = validate_barcode(barcode, strict=False)
    if not val["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_BARCODE",
                "barcode": barcode,
                "message": val["error"] or "That doesn't look like a valid barcode. Check the digits and try again.",
            },
        )
    code = val["normalized"]

    contribution = get_user_contribution_by_barcode(code)
    if contribution is not None:
        product = contribution_to_product(contribution)
        return _found(
            "user_contributed",
            product,
            profile,
            val,
            f"Found '{product['product_name']}' from a user contribution. It has not been reviewed, so check it against the pack.",
        )

    result = fetch_off_product(code)
    if result["status"] == "success":
        return _found("openfoodfacts", result["product"], profile, val, "Product found in the product database.")
    if result["status"] == "not_found":
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "OFF_PRODUCT_NOT_FOUND",
                "barcode": code,
                "barcode_format": val["format"],
                "check_digit_valid": val["check_digit_valid"],
                "message": f"Barcode {code} isn't in the product database yet.",
            },
        )
    raise off_unavailable_error(result)


@router.post("/products/assess")
def assess_custom_food(payload: ManualNutritionInput, profile: dict = Depends(get_request_profile)):
    """Assesses values the user typed in."""
    product = payload.model_dump()
    product["product_id"] = "CUSTOM_SCAN"
    product["data_source"] = "Entered or confirmed by you"
    product["data_confidence_status"] = "User-confirmed values"
    assessment = run_full_product_assessment(product, profile)
    assessment["is_custom"] = True
    assessment["raw_input"] = product
    assessment["profile_source"] = profile["profile_source"]
    return assessment


@router.post("/products/contribute")
def contribute_product(payload: ProductContributionRequest, request: Request):
    """Stores an unlisted product as an unreviewed contribution."""
    enforce_rate_limit(request, "contribution")

    val = validate_barcode(payload.barcode, strict=False)
    if not val["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_BARCODE", "message": val["error"] or "That doesn't look like a valid barcode."},
        )
    code = val["normalized"]

    data = payload.model_dump()
    sub_id = record_user_contribution(
        {
            **data,
            "barcode": code,
            "nutrition_data": {key: data[key] for key in NUTRIENT_FIELDS},
        }
    )
    return {
        "status": "success",
        "submission_id": sub_id,
        "barcode": code,
        "review_status": "pending_review",
        "data_confidence_status": UNVERIFIED_CONTRIBUTION_STATUS,
        "message": f"Thanks! '{payload.product_name}' was saved.",
    }
