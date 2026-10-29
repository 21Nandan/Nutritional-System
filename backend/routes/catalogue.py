"""Catalogue browsing and search (Open Food Facts), assessments, comparison and alternatives."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.core.assistant import answer_product_question
from backend.core.nutrition_scoring import (
    assess_general_nutrition,
    assess_personalized_suitability,
    run_full_product_assessment,
)
from backend.core.off_catalogue import (
    CATEGORIES,
    MAX_RESULT_WINDOW,
    SEARCH_POOL,
    alternative_candidates,
    browse_catalogue,
)
from backend.core.openfoodfacts import search_openfoodfacts_text
from backend.core.product_quality import rank_products
from backend.core.rate_limiter import enforce_rate_limit
from backend.core.recommender import get_healthier_alternatives
from backend.core.standards_registry import CALIBRATED_CATEGORIES, nutrient_flags
from backend.errors import off_unavailable_error, product_not_found_error
from backend.products import OpenFoodFactsUnavailable, resolve_product
from backend.profile import get_request_profile
from backend.schemas import AssistantQuery

logger = logging.getLogger("eatgood.catalogue")
router = APIRouter(prefix="/api")

MAX_PAGE_SIZE = 100


def _off_error(result: dict[str, Any]) -> HTTPException:
    logger.warning("Open Food Facts search unavailable: %s", result["error_code"])
    return HTTPException(
        status_code=result["http_status"],
        detail={"error_code": result["error_code"], "message": result["message"]},
    )


@router.get("/products")
def list_products(
    request: Request,
    query: str = Query("", max_length=100),
    category: str = "All",
    india_only: bool = Query(True, description="Only products sold in India"),
    max_sugars: float | None = Query(None, ge=0),
    max_sodium: float | None = Query(None, ge=0),
    max_sat_fat: float | None = Query(None, ge=0),
    min_fibre: float | None = Query(None, ge=0),
    min_protein: float | None = Query(None, ge=0),
    has_image: bool = False,
    limit: int = Query(30, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    profile: dict = Depends(get_request_profile),
):
    """The catalogue: products from Open Food Facts with search, category and nutrient filters.

    A failed search is an HTTP error, never an empty page.
    """
    if offset % limit:
        raise HTTPException(status_code=400, detail={"error_code": "BAD_OFFSET", "message": "offset must be a multiple of limit."})
    if offset + limit > MAX_RESULT_WINDOW:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "PAGE_TOO_DEEP", "message": f"Only the first {MAX_RESULT_WINDOW:,} results can be browsed. Narrow the search instead."},
        )
    if category not in ("All", "") and category not in CATEGORIES:
        raise HTTPException(status_code=400, detail={"error_code": "UNKNOWN_CATEGORY", "message": f"Unknown category: {category}"})
    enforce_rate_limit(request, "off_search")
    result = browse_catalogue(
        text=query,
        category=category,
        india_only=india_only,
        nutrient_filters={
            "max_sugars": max_sugars,
            "max_sodium": max_sodium,
            "max_sat_fat": max_sat_fat,
            "min_fibre": min_fibre,
            "min_protein": min_protein,
        },
        has_image=has_image,
        limit=limit,
        page=offset // limit + 1,
    )
    if result["status"] == "error":
        raise _off_error(result)
    count = result["count"]
    return {
        "query": query.strip(),
        "total": min(count, MAX_RESULT_WINDOW) if count is not None else len(result["products"]),
        "total_is_capped": count is not None and count >= MAX_RESULT_WINDOW,
        "products": [_with_scores(p, profile) for p in result["products"]],
        "interpreted_intent": result["interpreted_intent"],
        "match_mode": result["match_mode"],
        "searched_pool": result.get("searched_pool"),
        "pool_limited": result.get("pool_limited", False),
        "total_is_estimate": result.get("total_is_estimate", False),
        "profile_source": profile["profile_source"],
    }


def _with_scores(product: dict[str, Any], profile: dict) -> dict[str, Any]:
    """A listing item plus its grade and Goal Match, from the same functions as the product page."""
    general = assess_general_nutrition(product)
    personal = assess_personalized_suitability(product, profile)
    return {
        **product,
        "general_grade": general["grade"],
        "grade_reason": general["grade_reason"],
        "grade_note": general["grade_note"],
        "personalized_score": personal["personalized_score"],
        "has_allergen_conflict": personal["has_critical_allergen_conflict"],
    }


OFF_SEARCH_PAGE_SIZE = 24


@router.get("/products/search/openfoodfacts")
def search_open_food_facts(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="Product name, brand or keywords"),
    page: int = Query(1, ge=1, le=50),
):
    """Searches the Open Food Facts world database. The first SEARCH_POOL results are filtered and
    ranked like the catalogue (product_quality.rank_products) and paged locally. A failed search is
    an HTTP error, never an empty list."""
    enforce_rate_limit(request, "off_search")
    result = search_openfoodfacts_text(q, limit=SEARCH_POOL, page=1)
    if result["status"] == "error":
        raise _off_error(result)
    ranked, _ = rank_products(result["products"], q)
    start = (page - 1) * OFF_SEARCH_PAGE_SIZE
    return {
        "query": q.strip(),
        "page": page,
        "page_size": OFF_SEARCH_PAGE_SIZE,
        "count": len(ranked),
        "has_more": start + OFF_SEARCH_PAGE_SIZE < len(ranked),
        "pool_limited": (result.get("count") or 0) > SEARCH_POOL,
        "products": ranked[start:start + OFF_SEARCH_PAGE_SIZE],
        "attribution": "Data from Open Food Facts (openfoodfacts.org), available under the Open Database Licence.",
    }


@router.get("/products/categories")
def get_categories():
    return {"categories": ["All", *CATEGORIES], "calibrated_categories": CALIBRATED_CATEGORIES}


def _resolve_or_raise(product_id: str) -> dict:
    try:
        product = resolve_product(product_id)
    except OpenFoodFactsUnavailable as exc:
        raise off_unavailable_error(exc.result) from exc
    if product is None:
        raise product_not_found_error(product_id)
    return product


@router.get("/products/{product_id}")
def get_product_assessment(product_id: str, profile: dict = Depends(get_request_profile)):
    """Full three-layer assessment of one product for the requesting visitor's profile."""
    product = _resolve_or_raise(product_id)
    assessment = run_full_product_assessment(product, profile)
    assessment["profile_source"] = profile["profile_source"]
    return assessment


@router.get("/alternatives/{product_id}")
def get_alternatives(
    product_id: str,
    request: Request,
    limit: int = Query(4, ge=1, le=12),
    profile: dict = Depends(get_request_profile),
):
    """Healthier same-category alternatives, excluding anything that conflicts with the profile's allergens."""
    product = _resolve_or_raise(product_id)
    enforce_rate_limit(request, "off_search")
    candidates = alternative_candidates(product)
    if candidates["status"] == "error":
        raise _off_error(candidates)
    alts = get_healthier_alternatives(product, profile, candidates["products"], limit=limit)
    return {
        "product_id": product_id,
        "category": product.get("category"),
        "alternatives": alts["alternatives"],
        "profile_source": profile["profile_source"],
    }


@router.get("/compare")
def compare_products(
    ids: str = Query(..., description="Comma-separated product IDs (1 to 4)"),
    profile: dict = Depends(get_request_profile),
):
    """Products side by side. An ID that can't be loaded is listed in `unavailable` with the
    reason, so one stale or missing product never hides the others."""
    id_list = list(dict.fromkeys(i.strip() for i in ids.split(",") if i.strip()))
    if not 1 <= len(id_list) <= 4:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "COMPARE_COUNT", "message": "Choose between 2 and 4 products to compare."},
        )

    compared = []
    unavailable = []
    for pid in id_list:
        try:
            prod = _resolve_or_raise(pid)
        except HTTPException as exc:
            detail: dict[str, Any] = exc.detail if isinstance(exc.detail, dict) else {}
            unavailable.append({
                "product_id": pid,
                "error_code": detail.get("error_code", "PRODUCT_UNAVAILABLE"),
                "message": detail.get("message", "This product couldn't be loaded."),
                "retryable": exc.status_code != 404,
            })
            continue
        assessment = run_full_product_assessment(prod, profile)
        compared.append(
            {
                "product_id": prod["product_id"],
                "product_name": prod["product_name"],
                "brand": prod.get("brand"),
                "category": prod.get("category"),
                "image_url": prod.get("image_url"),
                "image_small_url": prod.get("image_small_url"),
                "measurement_basis": prod.get("measurement_basis"),
                "data_confidence_status": prod.get("data_confidence_status"),
                "energy_kcal": prod.get("energy_kcal"),
                "carbohydrates_g": prod.get("carbohydrates_g"),
                "sugars_g": prod.get("sugars_g"),
                "added_sugars_g": prod.get("added_sugars_g"),
                "protein_g": prod.get("protein_g"),
                "total_fat_g": prod.get("total_fat_g"),
                "saturated_fat_g": prod.get("saturated_fat_g"),
                "sodium_mg": prod.get("sodium_mg"),
                "dietary_fibre_g": prod.get("dietary_fibre_g"),
                "general_grade": assessment["layer1_general"].get("grade", "N/A"),
                "grade_reason": assessment["layer1_general"].get("grade_reason"),
                "grade_note": assessment["layer1_general"].get("grade_note"),
                "personalized_score": assessment["layer2_personalized"]["personalized_score"],
                "allergen_conflicts": assessment["layer2_personalized"]["allergen_conflicts"],
                "has_allergen_conflict": assessment["layer2_personalized"]["has_critical_allergen_conflict"],
                # Unknown allergen information must never read as "no alerts".
                "allergen_status_unknown": assessment["layer3_allergens"]["allergen_status_unknown"],
                "user_allergen_check_incomplete": assessment["layer3_allergens"]["user_allergen_check_incomplete"],
                # Same category thresholds as the grade and the catalogue's red values.
                "nutrient_flags": nutrient_flags(prod),
                "ingredients": prod.get("ingredients"),
            }
        )
    return {
        "user_goal": profile["goal"],
        "profile_source": profile["profile_source"],
        "products_compared": compared,
        "unavailable": unavailable,
    }


@router.post("/assistant/ask")
def ask_assistant(query: AssistantQuery, profile: dict = Depends(get_request_profile)):
    """Rule-based answers grounded in the product's computed assessment."""
    product = _resolve_or_raise(query.product_id)
    return answer_product_question(product=product, question=query.question, user_profile=profile)
