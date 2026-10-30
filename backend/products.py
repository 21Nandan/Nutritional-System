"""
EATGOOD — Product resolution shared by the route modules.

Lookup order for an identifier: unmoderated user contribution → Open Food Facts
(cache, then live).
"""

from typing import Any

from backend.config import OFF_CACHE_TTL_HOURS
from backend.core.barcode_utils import clean_barcode
from backend.core.openfoodfacts import fetch_product_from_openfoodfacts
from backend.core.standards_registry import nutrient_flags
from backend.database import cache_barcode_product, get_cached_lookup, get_user_contribution_by_barcode

UNVERIFIED_CONTRIBUTION_STATUS = "User submitted (not reviewed)"
NEGATIVE_CACHE_TTL_HOURS = 2

NUTRIENT_FIELDS = [
    "energy_kcal",
    "carbohydrates_g",
    "sugars_g",
    "added_sugars_g",
    "protein_g",
    "total_fat_g",
    "saturated_fat_g",
    "trans_fat_g",
    "sodium_mg",
    "dietary_fibre_g",
]


def contribution_to_product(contribution: dict[str, Any]) -> dict[str, Any]:
    nutrition = contribution["nutrition_data"]
    code = clean_barcode(contribution["barcode"])
    return {
        "product_id": f"USER_SUB_{code}",
        "barcode": code,
        "product_name": contribution["product_name"],
        "brand": contribution.get("brand") or "Unknown brand",
        "category": contribution["category"],
        # Older contributions were stored with a "User contributed" placeholder; it is not shown.
        "sub_category": None if contribution.get("sub_category") in (None, "", "User contributed") else contribution["sub_category"],
        "serving_size": contribution.get("serving_size"),
        "serving_size_unit": contribution.get("serving_size_unit"),
        "measurement_basis": contribution["measurement_basis"],
        **{key: nutrition.get(key) for key in NUTRIENT_FIELDS},
        "ingredients": contribution.get("ingredients"),
        "allergens_declared": contribution.get("allergens_declared"),
        "data_source": "User contribution (pending review)",
        "data_confidence_status": UNVERIFIED_CONTRIBUTION_STATUS,
        "review_status": contribution["review_status"],
    }


def fetch_off_product(barcode: str) -> dict[str, Any]:
    """Returns the Open Food Facts lookup result, using and filling the cache on success."""
    cached = get_cached_lookup(barcode)
    if cached is not None and cached["status"] == "success":
        return {"status": "success", "product": cached["product"], "cached": True}
    if cached is not None and cached["status"] == "not_found":
        return {"status": "not_found", "error_code": "OFF_PRODUCT_NOT_FOUND", "cached": True}
    result = fetch_product_from_openfoodfacts(barcode)
    if result["status"] == "success":
        cache_barcode_product(barcode, result["product"], status="success", ttl_hours=OFF_CACHE_TTL_HOURS)
    elif result["status"] == "not_found":
        cache_barcode_product(barcode, None, status="not_found", ttl_hours=NEGATIVE_CACHE_TTL_HOURS)
    return result


def with_saved_record(product: dict[str, Any]) -> dict[str, Any]:
    """A search result with the product's saved current record in place of the search copy, when one is cached.

    The search service works from an older copy of Open Food Facts, so a value added since (trans fat,
    say) would grade a card differently from the product page, which uses the current record.
    """
    cached = get_cached_lookup(clean_barcode(product.get("barcode") or ""))
    if cached is None or cached["status"] != "success" or not cached["product"]:
        return product
    merged = {**product, **cached["product"]}
    merged["nutrient_flags"] = nutrient_flags(merged)
    if "nutrition_summary" in product:
        merged["nutrition_summary"] = {
            **product["nutrition_summary"],
            **{key: merged.get(key) for key in ("energy_kcal", "sugars_g", "protein_g", "sodium_mg")},
        }
    return merged


def cached_product(product_id: str) -> dict[str, Any] | None:
    """A catalogue product the server already has saved (no network call), or None."""
    code = clean_barcode(product_id.removeprefix("OFF_"))
    cached = get_cached_lookup(code) if code.isdigit() else None
    return cached["product"] if cached and cached["status"] == "success" else None


def resolve_product(product_id: str) -> dict[str, Any] | None:
    """Resolves a product identifier to a product dict, or None when nothing matches.

    Raises OpenFoodFactsUnavailable when the identifier needs Open Food Facts and it fails.
    """
    if product_id.startswith("USER_SUB_"):
        contribution = get_user_contribution_by_barcode(product_id.removeprefix("USER_SUB_"))
        return contribution_to_product(contribution) if contribution else None

    code = product_id.removeprefix("OFF_").strip()
    if not code.isdigit():
        return None

    contribution = get_user_contribution_by_barcode(code)
    if contribution is not None:
        return contribution_to_product(contribution)

    result = fetch_off_product(code)
    if result["status"] == "success":
        return result["product"]
    if result["status"] == "not_found":
        return None
    raise OpenFoodFactsUnavailable(result)


class OpenFoodFactsUnavailable(Exception):
    def __init__(self, result: dict[str, Any]):
        super().__init__(result.get("technical_detail") or result["error_code"])
        self.result = result
