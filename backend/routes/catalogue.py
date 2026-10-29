"""Catalogue browsing, search, comparison and alternatives."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.core.assistant import answer_product_question
from backend.core.data_loader import data_loader
from backend.core.nutrition_scoring import run_full_product_assessment
from backend.core.openfoodfacts import search_openfoodfacts_text
from backend.core.rate_limiter import enforce_rate_limit
from backend.core.recommender import get_healthier_alternatives
from backend.core.semantic_search import execute_semantic_search, parse_semantic_intent
from backend.core.standards_registry import CALIBRATED_CATEGORIES, nutrient_flags
from backend.errors import off_unavailable_error, product_not_found_error
from backend.products import OpenFoodFactsUnavailable, resolve_product
from backend.profile import get_request_profile
from backend.schemas import AssistantQuery

logger = logging.getLogger("eatgood.catalogue")
router = APIRouter(prefix="/api")

MAX_PAGE_SIZE = 100


def _is_identifier_query(term: str) -> bool:
    return term.isdigit() or term.lower().startswith("ind_pkg_")


@router.get("/products")
def list_products(
    query: str = "",
    category: str = "All",
    brand: str = "All",
    max_sugars: float | None = None,
    max_sodium: float | None = None,
    max_sat_fat: float | None = None,
    min_fibre: float | None = None,
    min_protein: float | None = None,
    has_image: bool | None = None,
    limit: int = Query(30, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    deduplicate_variants: bool | None = None,
    profile: dict = Depends(get_request_profile),
):
    """Paginated catalogue with keyword search, category and nutrient filters."""
    term = query.strip()
    if term and not _is_identifier_query(term) and category in ("All", ""):
        intent = parse_semantic_intent(term)
        if intent["nutrient_descriptions"] or intent["excluded_allergens"] or (
            intent["category"] and len(term.split()) >= 2
        ):
            return execute_semantic_search(
                query=term, products_df=data_loader.products_df, user_profile=profile, limit=limit, offset=offset
            )

    return data_loader.search_products(
        query=term,
        category=category,
        brand=brand,
        max_sugars=max_sugars,
        max_sodium=max_sodium,
        max_sat_fat=max_sat_fat,
        min_fibre=min_fibre,
        min_protein=min_protein,
        has_image=has_image,
        limit=limit,
        offset=offset,
        deduplicate_variants=bool(term) if deduplicate_variants is None else deduplicate_variants,
    )


@router.get("/products/search")
def search_products(
    q: str = Query("", description="Search keyword or product name"),
    category: str = "All",
    include_external: bool = Query(True, description="Also query Open Food Facts"),
    limit: int = Query(12, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    profile: dict = Depends(get_request_profile),
):
    """Searches the local catalogue first, then Open Food Facts. External failures are reported, not hidden."""
    term = q.strip()
    if term and not _is_identifier_query(term) and category in ("All", ""):
        intent = parse_semantic_intent(term)
        if intent["nutrient_descriptions"] or intent["excluded_allergens"]:
            return execute_semantic_search(
                query=term, products_df=data_loader.products_df, user_profile=profile, limit=limit, offset=offset
            )

    local_res = data_loader.search_products(
        query=term, category=category, limit=limit, offset=offset, deduplicate_variants=bool(term)
    )
    local_prods = local_res["products"]

    external_prods: list[dict] = []
    external: dict[str, Any] = {"status": "skipped"}
    if include_external and len(term) >= 2 and not _is_identifier_query(term):
        external = search_openfoodfacts_text(term, limit=min(limit, 8))
        local_barcodes = set(data_loader.products_df["barcode"].dropna().astype(str).str.strip())
        local_names = {(str(r["brand"]).lower(), str(r["product_name"]).lower()) for r in local_prods}
        for op in external["products"]:
            if str(op.get("barcode") or "").strip() in local_barcodes:
                continue
            if (str(op.get("brand") or "").lower(), str(op.get("product_name") or "").lower()) in local_names:
                continue
            external_prods.append(op)

    merged = local_prods + external_prods
    return {
        "query": term,
        "total": len(merged),
        "local_count": len(local_prods),
        "external_count": len(external_prods),
        "external_status": external["status"],
        "external_error": None
        if external["status"] != "error"
        else {"error_code": external["error_code"], "message": external["message"]},
        "products": merged[:limit],
    }


OFF_SEARCH_PAGE_SIZE = 24


@router.get("/products/search/openfoodfacts")
def search_open_food_facts(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="Product name, brand or keywords"),
    page: int = Query(1, ge=1, le=50),
):
    """Searches the Open Food Facts world database only. A failed search is an HTTP error, never an empty list."""
    enforce_rate_limit(request, "off_search")
    result = search_openfoodfacts_text(q, limit=OFF_SEARCH_PAGE_SIZE, page=page)
    if result["status"] == "error":
        logger.warning("Open Food Facts search unavailable: %s", result["error_code"])
        raise HTTPException(
            status_code=result["http_status"],
            detail={"error_code": result["error_code"], "message": result["message"]},
        )
    count = result["count"]
    return {
        "query": q.strip(),
        "page": page,
        "page_size": OFF_SEARCH_PAGE_SIZE,
        "count": count,
        "has_more": count is not None and page * OFF_SEARCH_PAGE_SIZE < count,
        "products": result["products"],
        "attribution": "Data from Open Food Facts (openfoodfacts.org), available under the Open Database Licence.",
    }


@router.get("/products/categories")
def get_categories():
    cats = sorted(data_loader.products_df["category"].dropna().unique().tolist())
    return {"categories": ["All"] + cats, "calibrated_categories": CALIBRATED_CATEGORIES}


@router.get("/search/semantic")
def search_semantic(
    q: str = Query(..., min_length=1, description="e.g. 'less salty snacks'"),
    limit: int = Query(30, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    profile: dict = Depends(get_request_profile),
):
    return execute_semantic_search(
        query=q, products_df=data_loader.products_df, user_profile=profile, limit=limit, offset=offset
    )


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
    product_id: str, limit: int = Query(4, ge=1, le=12), profile: dict = Depends(get_request_profile)
):
    """Healthier same-category alternatives, excluding anything that conflicts with the profile's allergens."""
    product = _resolve_or_raise(product_id)
    alts = get_healthier_alternatives(product, profile, limit=limit)
    return {
        "product_id": product_id,
        "category": product.get("category"),
        "alternatives": alts["alternatives"],
        "profile_source": profile["profile_source"],
    }


@router.get("/compare")
def compare_products(
    ids: str = Query(..., description="Comma-separated product IDs (2 to 4)"),
    profile: dict = Depends(get_request_profile),
):
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not 2 <= len(id_list) <= 4:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "COMPARE_COUNT", "message": "Choose between 2 and 4 products to compare."},
        )

    compared = []
    for pid in id_list:
        prod = _resolve_or_raise(pid)
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
    return {"user_goal": profile["goal"], "profile_source": profile["profile_source"], "products_compared": compared}


@router.post("/assistant/ask")
def ask_assistant(query: AssistantQuery, profile: dict = Depends(get_request_profile)):
    """Rule-based answers grounded in the product's computed assessment."""
    product = _resolve_or_raise(query.product_id)
    return answer_product_question(product=product, question=query.question, user_profile=profile)
