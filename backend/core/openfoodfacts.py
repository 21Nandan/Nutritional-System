"""
EATGOOD — Open Food Facts API v3 client.
Reference: https://openfoodfacts.github.io/openfoodfacts-server/api/

- One pooled HTTPS client with strict certificate verification against the certifi
  CA bundle (or SSL_CERT_FILE when set). Verification is never disabled.
- One retry with backoff for timeouts, connection resets and 5xx responses.
- Every failure is returned with a distinct error_code and a plain-language message;
  technical details are only logged.
- Products are mapped without zero-filling missing nutrients, with ODbL attribution.
"""

import logging
import os
import re
import ssl
import threading
import time
from datetime import datetime
from typing import Any

import certifi
import httpx

from backend.config import OFF_BASE_URL, OFF_TIMEOUT_SECONDS, OFF_USER_AGENT
from backend.core.standards_registry import nutrient_flags

logger = logging.getLogger("eatgood.openfoodfacts")

# Open Food Facts' search service (search-a-licious). The older cgi/search.pl endpoint answers
# 503 "unusually high demand" to most clients, so it is not used.
OFF_SEARCH_URL = "https://search.openfoodfacts.org/search"
RETRY_BACKOFF_SECONDS = 0.5

_client: httpx.Client | None = None
_client_lock = threading.Lock()


def build_ssl_context() -> ssl.SSLContext:
    """Strict TLS verification against certifi's CA bundle, or SSL_CERT_FILE if the host sets one."""
    return ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or certifi.where())


def get_client() -> httpx.Client:
    global _client
    with _client_lock:
        if _client is None:
            _client = httpx.Client(
                verify=build_ssl_context(),
                timeout=OFF_TIMEOUT_SECONDS,
                headers={"User-Agent": OFF_USER_AGENT},
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return _client


def _is_tls_error(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, ssl.SSLError):
            return True
        current = current.__cause__ or current.__context__
    return "certificate verify failed" in str(exc).lower()


def _get_with_retry(client: httpx.Client, url: str, params: dict) -> httpx.Response:
    """GET with a single retry on timeouts, connection errors (not TLS) and 5xx responses."""
    for attempt in (1, 2):
        try:
            response = client.get(url, params=params)
        except httpx.TimeoutException:
            if attempt == 2:
                raise
        except httpx.TransportError as exc:
            if attempt == 2 or _is_tls_error(exc):
                raise
        else:
            if response.status_code < 500 or attempt == 2:
                return response
        time.sleep(RETRY_BACKOFF_SECONDS)
    raise AssertionError("unreachable")


ERROR_MESSAGES = {
    "OFF_TIMEOUT": "The product database took too long to answer. Please try again in a moment, or enter the nutrition facts manually.",
    "OFF_TLS_ERROR": "We couldn't open a secure connection to the product database. Please try again later, or enter the nutrition facts manually.",
    "OFF_NETWORK_ERROR": "We couldn't reach the product database right now. Check your connection and try again, or enter the nutrition facts manually.",
    "OFF_RATE_LIMITED": "The product database is receiving too many requests. Please wait a minute and try again.",
    "OFF_UPSTREAM_ERROR": "The product database is having problems right now. Please try again later, or enter the nutrition facts manually.",
    "OFF_BAD_RESPONSE": "The product database sent an answer we couldn't understand. Please try again later, or enter the nutrition facts manually.",
    "OFF_BARCODE_MISMATCH": "The product database returned a different product for this barcode, so we did not use it.",
}


def _error(error_code: str, http_status: int, barcode: str, technical_detail: str) -> dict[str, Any]:
    return {
        "status": "error",
        "error_code": error_code,
        "http_status": http_status,
        "product": None,
        "barcode": barcode,
        "source": "openfoodfacts",
        "message": ERROR_MESSAGES[error_code],
        "technical_detail": technical_detail,
    }


def classify_exception(exc: Exception, barcode: str) -> dict[str, Any]:
    if isinstance(exc, httpx.TimeoutException):
        return _error("OFF_TIMEOUT", 504, barcode, repr(exc))
    if _is_tls_error(exc):
        return _error("OFF_TLS_ERROR", 502, barcode, repr(exc))
    return _error("OFF_NETWORK_ERROR", 502, barcode, repr(exc))


# Documented field selection parameter for Open Food Facts API v3
OFF_REQUEST_FIELDS = (
    "code,product_name,product_name_en,generic_name,generic_name_en,brands,brands_tags,"
    "categories,categories_tags,image_front_url,image_front_small_url,image_url,"
    "ingredients_text,ingredients_text_en,ingredients,nutriments,nutrition_data_per,"
    "nutrition_data_prepared_per,serving_size,serving_quantity,quantity,allergens,"
    "allergens_tags,allergens_hierarchy,traces_tags,additives_tags,additives_original_tags,"
    "nutriscore_grade,nutriscore_score,nova_group,data_quality_tags,completeness,states_tags,misc_tags"
)


UNCATEGORISED = "Uncategorised"


_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Packaged Beverages", ("beverage", "drink", "soda", "juice", "tea", "coffee", "water", "cola", "nectar")),
    ("Breakfast Cereals", ("cereal", "muesli", "granola", "oats", "corn flakes", "porridge")),
    ("Biscuits & Bakery", ("biscuit", "cookie", "cracker", "bakery", "bread", "cake", "toast", "rusk")),
    ("Chocolates & Sweets", ("chocolate", "candy", "candies", "sweet", "confectionery", "confectioneries", "toffee")),
    ("Snacks", ("chip", "snack", "crisp", "namkeen", "popcorn", "nut", "makhana", "bhujia")),
    ("Instant Foods", ("noodle", "instant", "ready to eat", "soup", "pasta", "ramen")),
    ("Dairy", ("dairy", "dairies", "milk", "cheese", "yogurt", "yoghurt", "butter", "curd", "paneer", "ghee")),
    ("Condiments & Spreads", ("sauce", "ketchup", "spread", "jam", "condiment", "mayonnaise", "pickle", "dip")),
]


def _category_for_entry(words: str) -> str | None:
    for category, keywords in _CATEGORY_RULES:
        if any(re.search(rf"\b{re.escape(k)}s?\b", words) for k in keywords):
            return category
    return None


def map_off_category_to_eatgood(categories_str: str | None, categories_tags: list | None) -> str:
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
    # Open Food Facts lists categories from general to specific, and files most plant-based foods
    # (crisps included) under umbrella entries such as "Plant-based foods and beverages". Read the
    # entries from most specific to least and skip the umbrellas, so "beverages" in an umbrella
    # name never turns a snack into a drink.
    entries = [e for e in (categories_str or "").split(",") if e.strip()]
    entries += [t.split(":", 1)[-1] for t in (categories_tags or [])]

    for entry in reversed(entries):
        # Whole-word matching: "chocolates" must not match "cola", nor "steak" match "tea".
        words = re.sub(r"[^a-z]+", " ", entry.lower()).strip()
        if "food" in words and "beverage" in words:
            continue
        category = _category_for_entry(words)
        if category:
            return category

    # Unknown category: never guess. "Uncategorised" has no thresholds, so no grade is given.
    return UNCATEGORISED


def clean_allergens_from_tags(tags: list[str] | None) -> str:
    """Formats Open Food Facts allergen tags (e.g. ['en:milk', 'en:soybeans']) into human-readable text."""
    if not tags:
        return ""
    cleaned = []
    for tag in tags:
        clean = re.sub(r'^[a-z]{2}:', '', str(tag).strip()).replace('-', ' ').title()
        if clean and clean not in cleaned:
            cleaned.append(clean)
    return ", ".join(cleaned)


def format_additives_from_tags(tags: list[str] | None) -> str:
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


def map_off_product_to_eatgood(requested_barcode: str, off_product: dict[str, Any]) -> dict[str, Any]:
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
    def _get_float_val(keys: list[str]) -> float | None:
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
    traces = clean_allergens_from_tags(off_product.get("traces_tags"))
    if traces:
        # Keep cross-contact warnings as a separate "may contain" statement.
        allergens = f"{allergens}. May contain: {traces}" if allergens else f"May contain: {traces}"

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
            "notice": "Community-reported ratings; separate from the EATGOOD assessment."
        },
        "data_source": "Product database (community-contributed)",
        "data_confidence_status": "Community-contributed",
        "retrieved_at": now_iso,
        "openfoodfacts_attribution": "Nutritional and ingredient information retrieved from Open Food Facts under Open Database License (ODbL)."
    }


def fetch_product_from_openfoodfacts(barcode: str, client: httpx.Client | None = None) -> dict[str, Any]:
    """
    Looks up one barcode on Open Food Facts API v3.
    Returns a dict with status 'success' | 'not_found' | 'error'. Errors carry error_code,
    http_status, a plain-language message and a technical_detail for logs only.
    """
    clean_barcode = str(barcode).strip()
    url = f"{OFF_BASE_URL}/{clean_barcode}.json"
    try:
        response = _get_with_retry(client or get_client(), url, {"fields": OFF_REQUEST_FIELDS})
    except httpx.HTTPError as exc:
        logger.warning("Open Food Facts lookup failed for %s: %r", clean_barcode, exc)
        return classify_exception(exc, clean_barcode)

    not_found = {
        "status": "not_found",
        "error_code": "OFF_PRODUCT_NOT_FOUND",
        "http_status": 404,
        "product": None,
        "barcode": clean_barcode,
        "source": "openfoodfacts",
        "message": f"Barcode {clean_barcode} is not in the product database yet. You can add it, or enter the nutrition facts manually.",
    }
    if response.status_code == 404:
        return not_found
    if response.status_code == 429:
        return _error("OFF_RATE_LIMITED", 429, clean_barcode, "HTTP 429")
    if response.status_code >= 500:
        return _error("OFF_UPSTREAM_ERROR", 502, clean_barcode, f"HTTP {response.status_code}")
    if response.status_code != 200:
        return _error("OFF_BAD_RESPONSE", 502, clean_barcode, f"HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        return _error("OFF_BAD_RESPONSE", 502, clean_barcode, "Response body is not JSON")

    if data.get("status") in ("failure",) or data.get("result", {}).get("id") == "product_not_found":
        return not_found
    if data.get("status") not in ("success", "success_with_warnings") or "product" not in data:
        return _error("OFF_BAD_RESPONSE", 502, clean_barcode, f"Unexpected status {data.get('status')!r}")

    raw_prod = data["product"]
    returned_code = str(raw_prod.get("code") or data.get("code") or "").strip()
    if returned_code and returned_code.lstrip("0") != clean_barcode.lstrip("0"):
        return _error("OFF_BARCODE_MISMATCH", 422, clean_barcode, f"Requested {clean_barcode}, received {returned_code}")

    return {
        "status": "success",
        "product": map_off_product_to_eatgood(clean_barcode, raw_prod),
        "barcode": clean_barcode,
        "source": "openfoodfacts",
        "message": "Product found in the product database.",
    }


_OFF_QUERY_CACHE: dict[tuple[str, int, int], tuple[float, list[dict[str, Any]], int | None]] = {}
OFF_QUERY_CACHE_TTL = 300.0  # seconds


def _search_error(error_code: str, http_status: int) -> dict[str, Any]:
    return {
        "status": "error",
        "products": [],
        "count": None,
        "error_code": error_code,
        "http_status": http_status,
        "message": ERROR_MESSAGES[error_code],
    }


def search_openfoodfacts_text(
    query: str, limit: int = 6, client: httpx.Client | None = None, page: int = 1
) -> dict[str, Any]:
    """
    Text search on Open Food Facts, one page of `limit` results. Returns {"status": "ok"|"error",
    "products": [...], "count": total matches or None, "error_code"?, "http_status"?, "message"?}.
    An error is never reported as an empty result.
    """
    clean_q = str(query).strip().lower()
    if len(clean_q) < 2:
        return {"status": "ok", "products": [], "count": 0}

    now = time.time()
    cache_key = (clean_q, page, limit)
    cached = _OFF_QUERY_CACHE.get(cache_key)
    if cached and now - cached[0] < OFF_QUERY_CACHE_TTL:
        return {"status": "ok", "products": cached[1], "count": cached[2]}

    params = {
        "q": clean_q,
        "langs": "en",
        "page": page,
        "page_size": limit,
        "fields": OFF_REQUEST_FIELDS,
    }
    try:
        response = _get_with_retry(client or get_client(), OFF_SEARCH_URL, params)
    except httpx.HTTPError as exc:
        logger.warning("Open Food Facts search failed for %r: %r", clean_q, exc)
        err = classify_exception(exc, "")
        return _search_error(err["error_code"], err["http_status"])

    if response.status_code == 429:
        return _search_error("OFF_RATE_LIMITED", 429)
    if response.status_code != 200:
        return _search_error("OFF_UPSTREAM_ERROR" if response.status_code >= 500 else "OFF_BAD_RESPONSE", 502)
    try:
        body = response.json()
        raw_list = body["hits"]
        count = int(body["count"]) if body.get("count") is not None else None
    except (ValueError, TypeError, AttributeError, KeyError):
        return _search_error("OFF_BAD_RESPONSE", 502)

    mapped_products = []
    for raw in raw_list:
        code = str(raw.get("code") or "").strip()
        p_name = raw.get("product_name") or raw.get("product_name_en")
        if not code or not p_name or not str(p_name).strip():
            continue
        if isinstance(raw.get("brands"), list):
            # The search service returns brands as a list; the product API returns a comma-separated string.
            raw = {**raw, "brands": ", ".join(str(b) for b in raw["brands"])}
        mapped = map_off_product_to_eatgood(code, raw)
        mapped["nutrient_flags"] = nutrient_flags(mapped)
        mapped["is_local"] = False
        mapped["source"] = "Open Food Facts"
        mapped["nutrition_summary"] = {
            "energy_kcal": mapped.get("energy_kcal"),
            "sugars_g": mapped.get("sugars_g"),
            "protein_g": mapped.get("protein_g"),
            "sodium_mg": mapped.get("sodium_mg"),
            "serving_size": mapped.get("serving_size"),
            "serving_size_unit": mapped.get("serving_size_unit", "g"),
        }
        mapped_products.append(mapped)
        if len(mapped_products) >= limit:
            break

    _OFF_QUERY_CACHE[cache_key] = (now, mapped_products, count)
    return {"status": "ok", "products": mapped_products, "count": count}
