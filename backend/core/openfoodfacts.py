"""
EATGOOD — Open Food Facts API v3 Integration Service
Connects to the official Open Food Facts product-by-barcode API v3.
Adheres to Open Food Facts Terms of Service:
- Meaningful User-Agent string.
- Targeted field selection.
- Clear ODbL attribution.
- Resilient network timeout handling.
- Graceful handling of missing or incomplete fields.
"""

import logging
import re
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger("eatgood.openfoodfacts")

OPENFOODFACTS_BASE_URL = "https://world.openfoodfacts.org/api/v3/product"
DEFAULT_USER_AGENT = "EATGOOD-NutritionScanner/1.0 (local-desktop; dev@eatgood.local)"
REQUEST_TIMEOUT_SECONDS = 8.0

# Relevant fields to request to minimize bandwidth and rate-limit footprint
OFF_REQUEST_FIELDS = (
    "code,product_name,product_name_en,brands,categories,categories_tags,"
    "image_front_url,image_front_small_url,ingredients_text,ingredients_text_en,"
    "nutriments,serving_size,serving_quantity,allergens,allergens_tags,quantity,labels"
)

def map_off_category_to_eatgood(categories_str: Optional[str], categories_tags: Optional[list]) -> str:
    """
    Maps Open Food Facts category strings into EATGOOD primary categories:
    - Snacks
    - Breakfast Cereals
    - Packaged Beverages
    - Dairy
    - Instant Foods
    - Chocolates & Sweets
    - Condiments & Spreads
    - Biscuits & Bakery
    """
    text = (categories_str or "").lower()
    tags = " ".join(categories_tags or []).lower()
    combined = f"{text} {tags}"

    if any(k in combined for k in ["beverage", "drink", "soda", "juice", "tea", "coffee", "water"]):
        return "Packaged Beverages"
    elif any(k in combined for k in ["cereal", "muesli", "granola", "oats", "corn flakes"]):
        return "Breakfast Cereals"
    elif any(k in combined for k in ["biscuit", "cookie", "cracker", "bakery", "bread", "cake"]):
        return "Biscuits & Bakery"
    elif any(k in combined for k in ["chocolate", "candy", "sweet", "confectionery"]):
        return "Chocolates & Sweets"
    elif any(k in combined for k in ["chip", "snack", "crisp", "namkeen", "popcorn", "nuts"]):
        return "Snacks"
    elif any(k in combined for k in ["noodle", "instant", "ready-to-eat", "soup"]):
        return "Instant Foods"
    elif any(k in combined for k in ["dairy", "milk", "cheese", "yogurt", "butter", "curd"]):
        return "Dairy"
    elif any(k in combined for k in ["sauce", "ketchup", "spread", "jam", "condiment", "mayonnaise"]):
        return "Condiments & Spreads"

    return "Snacks"  # Safe default fallback category


def map_off_product_to_eatgood(barcode: str, off_product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms raw Open Food Facts API v3 product payload into
    EATGOOD's standardized product schema.
    """
    nutriments = off_product.get("nutriments", {}) or {}

    # Serving size & unit
    serving_str = off_product.get("serving_size") or ""
    serving_size = 100.0
    serving_size_unit = "g"

    srv_match = re.search(r'([0-9.]+)\s*(g|ml|gm)', serving_str, re.IGNORECASE)
    if srv_match:
        try:
            serving_size = float(srv_match.group(1))
            serving_size_unit = "ml" if "ml" in srv_match.group(2).lower() else "g"
        except ValueError:
            pass

    # Measurement basis
    category = map_off_category_to_eatgood(
        off_product.get("categories"),
        off_product.get("categories_tags")
    )
    measurement_basis = "per 100ml" if category == "Packaged Beverages" else "per 100g"

    # Energy (kcal)
    energy_kcal = nutriments.get("energy-kcal_100g")
    if energy_kcal is None:
        energy_kcal = nutriments.get("energy-kcal")
    if energy_kcal is None and "energy-kj_100g" in nutriments:
        try:
            energy_kcal = round(float(nutriments["energy-kj_100g"]) / 4.184, 1)
        except (ValueError, TypeError):
            pass

    # Sodium (mg)
    sodium_mg = None
    if "sodium_100g" in nutriments and nutriments["sodium_100g"] is not None:
        try:
            # Open Food Facts stores sodium in grams per 100g
            sodium_mg = round(float(nutriments["sodium_100g"]) * 1000.0, 1)
        except (ValueError, TypeError):
            pass
    elif "salt_100g" in nutriments and nutriments["salt_100g"] is not None:
        try:
            # salt (g) = sodium (g) * 2.5 => sodium (mg) = (salt / 2.5) * 1000
            sodium_mg = round((float(nutriments["salt_100g"]) / 2.5) * 1000.0, 1)
        except (ValueError, TypeError):
            pass

    # Safe float parser
    def _get_float(key: str) -> Optional[float]:
        val = nutriments.get(f"{key}_100g")
        if val is None:
            val = nutriments.get(key)
        if val is not None:
            try:
                return round(float(val), 2)
            except (ValueError, TypeError):
                return None
        return None

    product_name = (
        off_product.get("product_name") or
        off_product.get("product_name_en") or
        f"Product {barcode}"
    ).strip()

    brand = (off_product.get("brands") or "Unknown Brand").split(",")[0].strip()

    ingredients = (
        off_product.get("ingredients_text") or
        off_product.get("ingredients_text_en") or
        None
    )

    allergens = off_product.get("allergens") or None
    image_url = off_product.get("image_front_url") or off_product.get("image_front_small_url")

    return {
        "product_id": f"OFF_{barcode}",
        "product_name": product_name,
        "brand": brand,
        "category": category,
        "sub_category": "Retail Packaging",
        "barcode": str(barcode),
        "serving_size": serving_size,
        "serving_size_unit": serving_size_unit,
        "measurement_basis": measurement_basis,
        "energy_kcal": energy_kcal,
        "carbohydrates_g": _get_float("carbohydrates"),
        "sugars_g": _get_float("sugars"),
        "added_sugars_g": _get_float("added-sugars"),
        "protein_g": _get_float("protein"),
        "total_fat_g": _get_float("fat"),
        "saturated_fat_g": _get_float("saturated-fat"),
        "trans_fat_g": _get_float("trans-fat"),
        "sodium_mg": sodium_mg,
        "dietary_fibre_g": _get_float("fiber"),
        "ingredients": ingredients,
        "allergens_declared": allergens,
        "image_url": image_url,
        "data_source": "Open Food Facts (External Community Database)",
        "data_confidence_status": "Community Sourced (Open Food Facts)",
        "openfoodfacts_attribution": "Nutritional and ingredient information from Open Food Facts under Open Database License (ODbL)."
    }


def fetch_product_from_openfoodfacts(
    barcode: str,
    client: Optional[httpx.Client] = None
) -> Dict[str, Any]:
    """
    Queries Open Food Facts API v3 for a single barcode.
    Returns:
        status: 'success' | 'not_found' | 'error'
        product: Optional[dict]
        message: str
        barcode: str
    """
    clean_barcode = str(barcode).strip()
    url = f"{OPENFOODFACTS_BASE_URL}/{clean_barcode}.json"
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    params = {"fields": OFF_REQUEST_FIELDS}

    close_client = False
    if client is None:
        client = httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)
        close_client = True

    try:
        response = client.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and "product" in data:
                standardized = map_off_product_to_eatgood(clean_barcode, data["product"])
                return {
                    "status": "success",
                    "product": standardized,
                    "barcode": clean_barcode,
                    "source": "openfoodfacts",
                    "message": "Product retrieved successfully from Open Food Facts."
                }
            elif data.get("status") == "failure":
                return {
                    "status": "not_found",
                    "product": None,
                    "barcode": clean_barcode,
                    "source": "openfoodfacts",
                    "message": f"Barcode {clean_barcode} not found in Open Food Facts database."
                }

        elif response.status_code == 404:
            return {
                "status": "not_found",
                "product": None,
                "barcode": clean_barcode,
                "source": "openfoodfacts",
                "message": f"Barcode {clean_barcode} not found in Open Food Facts database."
            }

        elif response.status_code == 429:
            logger.warning(f"Open Food Facts API rate limit exceeded for barcode {clean_barcode}")
            return {
                "status": "error",
                "product": None,
                "barcode": clean_barcode,
                "source": "openfoodfacts",
                "message": "Open Food Facts rate limit reached. Please try again shortly or use manual entry."
            }

        else:
            return {
                "status": "error",
                "product": None,
                "barcode": clean_barcode,
                "source": "openfoodfacts",
                "message": f"Open Food Facts API returned unexpected HTTP status {response.status_code}."
            }

    except httpx.TimeoutException:
        logger.warning(f"Open Food Facts query timed out for barcode {clean_barcode}")
        return {
            "status": "error",
            "product": None,
            "barcode": clean_barcode,
            "source": "openfoodfacts",
            "message": "Connection to Open Food Facts timed out. You can proceed with manual entry."
        }
    except Exception as e:
        logger.error(f"Open Food Facts API error: {e}")
        return {
            "status": "error",
            "product": None,
            "barcode": clean_barcode,
            "source": "openfoodfacts",
            "message": f"Unable to reach Open Food Facts: {str(e)}"
        }
    finally:
        if close_client:
            client.close()
