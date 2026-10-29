"""
EATGOOD — Open Food Facts API v3 Integration Service
Connects to the official Open Food Facts product-by-barcode API v3.
Adheres to Open Food Facts API Documentation & Terms of Service:
- Reference: https://openfoodfacts.github.io/openfoodfacts-server/api/
- Exact barcode match verification (rejects mismatched product returns).
- Meaningful User-Agent string.
- Targeted field selection.
- Clear ODbL attribution.
- Resilient network timeout and rate limit handling.
- Comprehensive nutritional normalization without silent zero-fills.
"""

import logging
import re
import ssl
from datetime import datetime
from typing import Dict, Any, Optional, List
import httpx
import certifi

logger = logging.getLogger("eatgood.openfoodfacts")

OPENFOODFACTS_BASE_URL = "https://world.openfoodfacts.org/api/v3/product"
DEFAULT_USER_AGENT = "EATGOOD-NutritionScanner/1.0 (local-desktop; dev@eatgood.local)"
REQUEST_TIMEOUT_SECONDS = 8.0

def get_httpx_ssl_context() -> ssl.SSLContext:
    """Creates an SSL context strictly enforcing certificate verification against certifi CA bundle."""
    return ssl.create_default_context(cafile=certifi.where())

def get_httpx_client(timeout: float) -> httpx.Client:
    """
    Instantiates an HTTPX client strictly enforcing certificate verification
    against Mozilla's trusted CA bundle via certifi.
    """
    return httpx.Client(verify=get_httpx_ssl_context(), timeout=timeout)

# Documented field selection parameter for Open Food Facts API v3
OFF_REQUEST_FIELDS = (
    "code,product_name,product_name_en,generic_name,generic_name_en,brands,brands_tags,"
    "categories,categories_tags,image_front_url,image_front_small_url,image_url,"
    "ingredients_text,ingredients_text_en,ingredients,nutriments,nutrition_data_per,"
    "nutrition_data_prepared_per,serving_size,serving_quantity,quantity,allergens,"
    "allergens_tags,allergens_hierarchy,additives_tags,additives_original_tags,"
    "nutriscore_grade,nutriscore_score,nova_group,data_quality_tags,completeness,states_tags,misc_tags"
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

    if any(k in combined for k in ["beverage", "drink", "soda", "juice", "tea", "coffee", "water", "cola"]):
        return "Packaged Beverages"
    elif any(k in combined for k in ["cereal", "muesli", "granola", "oats", "corn flakes", "porridge"]):
        return "Breakfast Cereals"
    elif any(k in combined for k in ["biscuit", "cookie", "cracker", "bakery", "bread", "cake", "toast", "rusk"]):
        return "Biscuits & Bakery"
    elif any(k in combined for k in ["chocolate", "candy", "sweet", "confectionery", "toffee"]):
        return "Chocolates & Sweets"
    elif any(k in combined for k in ["chip", "snack", "crisp", "namkeen", "popcorn", "nuts", "makhana", "bhujia"]):
        return "Snacks"
    elif any(k in combined for k in ["noodle", "instant", "ready-to-eat", "soup", "pasta", "ramen"]):
        return "Instant Foods"
    elif any(k in combined for k in ["dairy", "milk", "cheese", "yogurt", "butter", "curd", "paneer", "ghee"]):
        return "Dairy"
    elif any(k in combined for k in ["sauce", "ketchup", "spread", "jam", "condiment", "mayonnaise", "pickle", "dip"]):
        return "Condiments & Spreads"

    # Default to Snacks for packaged dry goods
    return "Snacks"


def clean_allergens_from_tags(tags: Optional[List[str]]) -> str:
    """Formats Open Food Facts allergen tags (e.g. ['en:milk', 'en:soybeans']) into human-readable text."""
    if not tags:
        return ""
    cleaned = []
    for tag in tags:
        clean = re.sub(r'^[a-z]{2}:', '', str(tag).strip()).replace('-', ' ').title()
        if clean and clean not in cleaned:
            cleaned.append(clean)
    return ", ".join(cleaned)


def format_additives_from_tags(tags: Optional[List[str]]) -> str:
    """Converts European E-numbers (e.g. 'en:e150d', 'en:e322') into statutory INS format ('INS 150d, INS 322')."""
    if not tags:
        return ""
    ins_list = []
    for tag in tags:
        m = re.search(r'e([0-9]+[a-z]*(?:\([iIvVxX]+\))?)', str(tag).lower())
        if m:
            code = f"INS {m.group(1)}"
            if code not in ins_list:
                ins_list.append(code)
    return ", ".join(ins_list)


def map_off_product_to_eatgood(requested_barcode: str, off_product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms raw Open Food Facts API v3 product payload into
    EATGOOD's standardized product schema.
    Strictly preserves numeric integrity, distinguishes absent from zero,
    and captures source-reported indicators separately from EATGOOD calculations.
    """
    nutriments = off_product.get("nutriments", {}) or {}

    # Serving size & unit extraction
    serving_str = str(off_product.get("serving_size") or "")
    serving_quantity = off_product.get("serving_quantity")
    serving_size = None
    serving_size_unit = "g"

    if serving_quantity is not None:
        try:
            serving_size = round(float(serving_quantity), 1)
        except (ValueError, TypeError):
            pass

    if serving_size is None and serving_str:
        srv_match = re.search(r'([0-9.]+)\s*(g|ml|gm|l)', serving_str, re.IGNORECASE)
        if srv_match:
            try:
                serving_size = float(srv_match.group(1))
                unit_str = srv_match.group(2).lower()
                serving_size_unit = "ml" if "ml" in unit_str or unit_str == "l" else "g"
            except (ValueError, TypeError):
                pass

    if serving_size is None:
        serving_size = 100.0  # Standard fallback serving

    # Category determination
    category = map_off_category_to_eatgood(
        off_product.get("categories"),
        off_product.get("categories_tags")
    )

    # Measurement basis determination (per 100g vs per 100ml vs per serving)
    nutrition_data_per = str(off_product.get("nutrition_data_per") or "").lower().strip()
    if "100ml" in nutrition_data_per or category == "Packaged Beverages":
        measurement_basis = "per 100ml"
        serving_size_unit = "ml"
    elif "serving" in nutrition_data_per:
        measurement_basis = "per serving"
    else:
        measurement_basis = "per 100g"

    # Energy (kcal) parsing with kJ conversion fallback
    energy_kcal = None
    for k in ["energy-kcal_100g", "energy-kcal", "energy-kcal_value"]:
        val = nutriments.get(k)
        if val is not None:
            try:
                energy_kcal = round(float(val), 1)
                break
            except (ValueError, TypeError):
                pass

    if energy_kcal is None:
        # Check energy-kj
        for k in ["energy-kj_100g", "energy-kj", "energy-kj_value"]:
            val = nutriments.get(k)
            if val is not None:
                try:
                    energy_kcal = round(float(val) / 4.184, 1)
                    break
                except (ValueError, TypeError):
                    pass

    if energy_kcal is None:
        # Check raw energy key
        val = nutriments.get("energy_100g") or nutriments.get("energy")
        unit = str(nutriments.get("energy_unit", "")).lower()
        if val is not None:
            try:
                f_val = float(val)
                if unit in ["kcal", "calories"]:
                    energy_kcal = round(f_val, 1)
                else:
                    energy_kcal = round(f_val / 4.184, 1)
            except (ValueError, TypeError):
                pass

    # Safe float parser checking multiple key variants without silent zero fills
    def _get_float_val(keys: List[str]) -> Optional[float]:
        for k in keys:
            v = nutriments.get(k)
            if v is not None:
                try:
                    return round(float(v), 2)
                except (ValueError, TypeError):
                    pass
        return None

    # Protein (checks both 'proteins' and 'protein')
    protein_g = _get_float_val([
        "proteins_100g", "protein_100g", "proteins", "protein",
        "proteins_value", "protein_value"
    ])

    # Carbohydrates
    carbohydrates_g = _get_float_val([
        "carbohydrates_100g", "carbohydrates", "carbohydrates_value"
    ])

    # Sugars
    sugars_g = _get_float_val([
        "sugars_100g", "sugars", "sugars_value"
    ])

    # Added Sugars
    added_sugars_g = _get_float_val([
        "added-sugars_100g", "added-sugars", "added-sugars_value"
    ])

    # Total Fat
    total_fat_g = _get_float_val([
        "fat_100g", "total-fat_100g", "fat", "total-fat", "fat_value"
    ])

    # Saturated Fat
    saturated_fat_g = _get_float_val([
        "saturated-fat_100g", "saturated_fat_100g", "saturated-fat", "saturated-fat_value"
    ])

    # Trans Fat
    trans_fat_g = _get_float_val([
        "trans-fat_100g", "trans_fat_100g", "trans-fat", "trans-fat_value"
    ])

    # Dietary Fibre
    dietary_fibre_g = _get_float_val([
        "fiber_100g", "fibre_100g", "fiber", "fibre", "fiber_value", "fibre_value"
    ])

    # Sodium (mg) with careful unit handling and salt fallback
    sodium_mg = None
    sodium_raw = nutriments.get("sodium_100g")
    if sodium_raw is None:
        sodium_raw = nutriments.get("sodium")
    if sodium_raw is not None:
        try:
            val = float(sodium_raw)
            unit = str(nutriments.get("sodium_unit", "")).lower()
            if unit == "mg":
                sodium_mg = round(val, 1)
            else:
                # Default OFF representation for sodium is in grams
                sodium_mg = round(val * 1000.0, 1)
        except (ValueError, TypeError):
            pass

    if sodium_mg is None:
        salt_raw = nutriments.get("salt_100g") or nutriments.get("salt")
        if salt_raw is not None:
            try:
                # salt (g) = sodium (g) * 2.5 => sodium (mg) = (salt / 2.5) * 1000
                val = float(salt_raw)
                unit = str(nutriments.get("salt_unit", "")).lower()
                if unit == "mg":
                    sodium_mg = round(val / 2.5, 1)
                else:
                    sodium_mg = round((val / 2.5) * 1000.0, 1)
            except (ValueError, TypeError):
                pass

    # Cholesterol (mg)
    cholesterol_mg = None
    chol_raw = nutriments.get("cholesterol_100g") or nutriments.get("cholesterol")
    if chol_raw is not None:
        try:
            val = float(chol_raw)
            unit = str(nutriments.get("cholesterol_unit", "")).lower()
            cholesterol_mg = round(val if unit == "mg" else val * 1000.0, 1)
        except (ValueError, TypeError):
            pass

    # Product Name
    product_name = (
        off_product.get("product_name") or
        off_product.get("product_name_en") or
        off_product.get("generic_name") or
        off_product.get("generic_name_en") or
        f"Product {requested_barcode}"
    ).strip()

    # Brand
    brand_raw = off_product.get("brands")
    if not brand_raw and off_product.get("brands_tags"):
        brand_raw = off_product["brands_tags"][0].replace("-", " ").title()
    brand = (brand_raw or "Unknown Brand").split(",")[0].strip()

    # Ingredients
    ingredients = (
        off_product.get("ingredients_text") or
        off_product.get("ingredients_text_en") or
        None
    )

    # Allergens
    allergens = off_product.get("allergens")
    if not allergens and off_product.get("allergens_tags"):
        allergens = clean_allergens_from_tags(off_product.get("allergens_tags"))

    # Additives in statutory INS notation
    additives_text = format_additives_from_tags(off_product.get("additives_tags"))

    # Product Image URL
    image_url = (
        off_product.get("image_front_url") or
        off_product.get("image_front_small_url") or
        off_product.get("image_url")
    )

    # Source-reported indicators (distinct from EATGOOD calculations)
    nutriscore_raw = off_product.get("nutriscore_grade")
    nutriscore_grade = (
        str(nutriscore_raw).upper()
        if nutriscore_raw and str(nutriscore_raw).lower() not in ["unknown", "not-applicable"]
        else None
    )

    nova_raw = off_product.get("nova_group")
    nova_group = int(nova_raw) if nova_raw is not None and str(nova_raw).isdigit() else None

    completeness_raw = off_product.get("completeness")
    completeness = round(float(completeness_raw), 2) if completeness_raw is not None else None

    now_iso = datetime.now().isoformat()

    return {
        "product_id": f"OFF_{requested_barcode}",
        "product_name": product_name,
        "brand": brand,
        "category": category,
        "sub_category": "Community Sourced Packaging",
        "barcode": str(requested_barcode),
        "serving_size": serving_size,
        "serving_size_unit": serving_size_unit,
        "measurement_basis": measurement_basis,
        "energy_kcal": energy_kcal,
        "carbohydrates_g": carbohydrates_g,
        "sugars_g": sugars_g,
        "added_sugars_g": added_sugars_g,
        "protein_g": protein_g,
        "total_fat_g": total_fat_g,
        "saturated_fat_g": saturated_fat_g,
        "trans_fat_g": trans_fat_g,
        "sodium_mg": sodium_mg,
        "cholesterol_mg": cholesterol_mg,
        "dietary_fibre_g": dietary_fibre_g,
        "ingredients": ingredients,
        "allergens_declared": allergens,
        "additives": additives_text,
        "image_url": image_url,
        "quantity": off_product.get("quantity"),
        "source_indicators": {
            "nutriscore_grade": nutriscore_grade,
            "nutriscore_score": off_product.get("nutriscore_score"),
            "nova_group": nova_group,
            "data_completeness": completeness,
            "notice": "Source-reported metrics from Open Food Facts community database; distinct from EATGOOD calculated assessment."
        },
        "data_source": "Open Food Facts (v3 API)",
        "data_confidence_status": "Community Sourced (Open Food Facts)",
        "retrieved_at": now_iso,
        "openfoodfacts_attribution": "Nutritional and ingredient information retrieved from Open Food Facts under Open Database License (ODbL)."
    }


def fetch_product_from_openfoodfacts(
    barcode: str,
    client: Optional[httpx.Client] = None
) -> Dict[str, Any]:
    """
    Queries Open Food Facts API v3 for a single barcode.
    Verifies exact product identity match on code.
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
        client = get_httpx_client(REQUEST_TIMEOUT_SECONDS)
        close_client = True

    try:
        response = client.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and "product" in data:
                raw_prod = data["product"]
                returned_code = str(raw_prod.get("code") or data.get("code") or "").strip()

                # Exact barcode match verification (protects against accidental variant mismatches)
                if returned_code and returned_code.lstrip("0") != clean_barcode.lstrip("0"):
                    logger.warning(
                        f"Barcode identity mismatch: requested {clean_barcode}, received {returned_code}"
                    )
                    return {
                        "status": "error",
                        "error_code": "OFF_BARCODE_MISMATCH",
                        "http_status": 422,
                        "product": None,
                        "barcode": clean_barcode,
                        "source": "openfoodfacts",
                        "message": f"External API returned product code '{returned_code}' which does not match requested '{clean_barcode}'.",
                        "technical_detail": f"Requested {clean_barcode}, received {returned_code}"
                    }

                standardized = map_off_product_to_eatgood(clean_barcode, raw_prod)
                return {
                    "status": "success",
                    "product": standardized,
                    "barcode": clean_barcode,
                    "source": "openfoodfacts",
                    "message": "Product retrieved successfully from Open Food Facts."
                }
            elif data.get("status") == "failure" or data.get("result", {}).get("id") == "product_not_found":
                return {
                    "status": "not_found",
                    "error_code": "OFF_PRODUCT_NOT_FOUND",
                    "http_status": 404,
                    "product": None,
                    "barcode": clean_barcode,
                    "source": "openfoodfacts",
                    "message": f"Barcode {clean_barcode} was not found in the Open Food Facts database. You can add it directly or enter nutrition facts manually."
                }

        elif response.status_code == 404:
            return {
                "status": "not_found",
                "error_code": "OFF_PRODUCT_NOT_FOUND",
                "http_status": 404,
                "product": None,
                "barcode": clean_barcode,
                "source": "openfoodfacts",
                "message": f"Barcode {clean_barcode} was not found in the Open Food Facts database. You can add it directly or enter nutrition facts manually."
            }

        elif response.status_code == 429:
            logger.warning(f"Open Food Facts API rate limit exceeded for barcode {clean_barcode}")
            return {
                "status": "error",
                "error_code": "OFF_RATE_LIMITED",
                "http_status": 429,
                "product": None,
                "barcode": clean_barcode,
                "source": "openfoodfacts",
                "message": "Open Food Facts rate limit reached. Please wait a few moments before trying again, or enter nutrition facts manually.",
                "technical_detail": "HTTP 429 Too Many Requests"
            }

        elif response.status_code >= 500:
            logger.warning(f"Open Food Facts API upstream server error {response.status_code} for barcode {clean_barcode}")
            return {
                "status": "error",
                "error_code": "OFF_UPSTREAM_ERROR",
                "http_status": 502,
                "product": None,
                "barcode": clean_barcode,
                "source": "openfoodfacts",
                "message": "Open Food Facts servers are currently experiencing issues. Please try again later or enter details manually.",
                "technical_detail": f"HTTP {response.status_code}"
            }

        else:
            return {
                "status": "error",
                "error_code": "OFF_UPSTREAM_ERROR",
                "http_status": 502,
                "product": None,
                "barcode": clean_barcode,
                "source": "openfoodfacts",
                "message": "Couldn't reach the Open Food Facts database right now. Check your connection, try again, or enter nutrition facts manually.",
                "technical_detail": f"Unexpected HTTP status {response.status_code}"
            }

    except httpx.TimeoutException as e:
        logger.warning(f"Open Food Facts query timed out for barcode {clean_barcode}: {e}")
        return {
            "status": "error",
            "error_code": "OFF_TIMEOUT",
            "http_status": 504,
            "product": None,
            "barcode": clean_barcode,
            "source": "openfoodfacts",
            "message": "Request to Open Food Facts timed out. Check your internet connection or try again shortly.",
            "technical_detail": str(e)
        }
    except Exception as e:
        err_str = str(e).lower()
        is_tls = isinstance(e, (ssl.SSLError, ssl.SSLCertVerificationError)) or "certificate" in err_str or "ssl" in err_str or "tls" in err_str
        if is_tls:
            logger.error(f"Open Food Facts TLS/SSL verification error for barcode {clean_barcode}: {e}")
            return {
                "status": "error",
                "error_code": "OFF_TLS_ERROR",
                "http_status": 502,
                "product": None,
                "barcode": clean_barcode,
                "source": "openfoodfacts",
                "message": "Unable to verify secure connection to Open Food Facts. Check your system certificates or enter nutrition facts manually.",
                "technical_detail": str(e)
            }
        else:
            logger.error(f"Open Food Facts network/connection error for barcode {clean_barcode}: {e}")
            return {
                "status": "error",
                "error_code": "OFF_NETWORK_ERROR",
                "http_status": 502,
                "product": None,
                "barcode": clean_barcode,
                "source": "openfoodfacts",
                "message": "Couldn't reach the Open Food Facts database right now. Check your connection, try again, or search our catalogue / enter nutrition facts manually.",
                "technical_detail": str(e)
            }
    finally:
        if close_client:
            client.close()


import time

_OFF_QUERY_CACHE: Dict[str, Any] = {}
OFF_QUERY_CACHE_TTL = 300.0  # 5 minutes cache

def search_openfoodfacts_text(
    query: str,
    limit: int = 6,
    client: Optional[httpx.Client] = None
) -> List[Dict[str, Any]]:
    """
    Discovers packaged products from official Open Food Facts search API.
    Normalizes parameters, parses results into EATGOOD product schema,
    caches successful returns in SQLite, and gracefully recovers on network/rate-limit issues.
    """
    clean_q = str(query).strip().lower()
    if not clean_q or len(clean_q) < 2:
        return []

    now = time.time()
    if clean_q in _OFF_QUERY_CACHE:
        cached_time, cached_items = _OFF_QUERY_CACHE[clean_q]
        if now - cached_time < OFF_QUERY_CACHE_TTL:
            return cached_items[:limit]

    close_client = False
    if client is None:
        # Fast 4.5s timeout with certifi CA bundle so external API delays never block local search
        client = get_httpx_client(4.5)
        close_client = True

    endpoints = [
        "https://world.openfoodfacts.net/cgi/search.pl",
        "https://world.openfoodfacts.org/cgi/search.pl"
    ]

    params = {
        "search_terms": clean_q,
        "search_simple": "1",
        "action": "process",
        "json": "1",
        "page_size": max(limit, 8),
        "fields": OFF_REQUEST_FIELDS
    }
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    mapped_products = []

    for ep in endpoints:
        try:
            resp = client.get(ep, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                raw_list = data.get("products", [])
                for raw in raw_list:
                    code = str(raw.get("code") or "").strip()
                    if not code:
                        continue
                    p_name = raw.get("product_name") or raw.get("product_name_en")
                    if not p_name or not str(p_name).strip():
                        continue

                    mapped = map_off_product_to_eatgood(code, raw)
                    mapped["is_local"] = False
                    mapped["source"] = "Open Food Facts"
                    mapped["nutrition_summary"] = {
                        "energy_kcal": mapped.get("energy_kcal"),
                        "sugars_g": mapped.get("sugars_g"),
                        "protein_g": mapped.get("protein_g"),
                        "sodium_mg": mapped.get("sodium_mg"),
                        "serving_size": mapped.get("serving_size"),
                        "serving_size_unit": mapped.get("serving_size_unit", "g")
                    }

                    # Cache in external_products_cache SQLite table
                    try:
                        from backend.database import cache_barcode_product
                        cache_barcode_product(code, mapped, source="openfoodfacts", status="success", ttl_hours=168)
                    except Exception:
                        pass

                    mapped_products.append(mapped)
                    if len(mapped_products) >= limit:
                        break
                if mapped_products:
                    break
            elif resp.status_code == 429:
                logger.warning(f"Open Food Facts search rate limited for '{clean_q}'")
                break
        except httpx.TimeoutException:
            logger.warning(f"Open Food Facts search timed out on {ep} for '{clean_q}'")
            continue
        except Exception as e:
            logger.warning(f"Open Food Facts search failed on {ep}: {e}")
            continue

    if close_client:
        try:
            client.close()
        except Exception:
            pass

    _OFF_QUERY_CACHE[clean_q] = (now, mapped_products)
    return mapped_products[:limit]
