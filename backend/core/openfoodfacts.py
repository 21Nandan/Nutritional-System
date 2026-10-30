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
from backend.core.nutrition_validator import parse_float_safe
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
    "nutriscore_grade,nutriscore_score,nova_group,data_quality_tags,completeness,states_tags,misc_tags,"
    "countries_tags"
)


UNCATEGORISED = "Uncategorised"
# Alcoholic drinks are not graded or listed anywhere in EATGOOD.
ALCOHOLIC = "Alcoholic Drinks"
_ALCOHOL_TAGS = {
    "en:alcoholic-beverages", "en:beers", "en:wines", "en:spirits", "en:ciders", "en:liqueurs",
    "en:whiskies", "en:vodkas", "en:rums", "en:gins", "en:sparkling-wines", "en:meads",
}


def is_alcoholic(off_product: dict[str, Any]) -> bool:
    """True for a record tagged as an alcoholic drink, or stating more than 0.5% alcohol."""
    if _ALCOHOL_TAGS & set(off_product.get("categories_tags") or []):
        return True
    alcohol = (off_product.get("nutriments") or {}).get("alcohol_100g")
    try:
        return float(alcohol) > 0.5
    except (TypeError, ValueError):
        return False

_MASS_UNITS_IN_G = {"g": 1.0, "mg": 0.001, "µg": 0.000001, "μg": 0.000001, "mcg": 0.000001}


_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    # Checked first so "Peanut butters" is a spread, not dairy butter.
    ("Condiments & Spreads", ("peanut butter", "nut butter")),
    # Also checked before drinks: buttermilk, lassi and other milk drinks are graded with Dairy, like milk.
    ("Dairy", ("buttermilk", "lassi", "chaas", "chaach", "chhach", "dairy drink", "milk drink", "yogurt drink",
               "yoghurt drink", "flavoured milk", "flavored milk", "milkshake", "milk shake")),
    ("Packaged Beverages", ("beverage", "drink", "soda", "juice", "tea", "coffee", "water", "cola", "nectar")),
    ("Breakfast Cereals", ("breakfast cereal", "cereal bar", "cereal flake", "muesli", "granola", "oats", "oat flake",
                           "corn flakes", "porridge")),
    ("Biscuits & Bakery", ("biscuit", "cookie", "cracker", "bakery", "bread", "cake", "toast", "rusk")),
    ("Chocolates & Sweets", ("chocolate", "candy", "candies", "sweet", "confectionery", "confectioneries", "toffee")),
    ("Snacks", ("chip", "snack", "crisp", "namkeen", "popcorn", "nut", "makhana", "bhujia")),
    ("Instant Foods", ("noodle", "instant", "ready to eat", "ready to cook", "ready meal", "prepared meal", "soup",
                       "pasta", "ramen")),
    ("Dairy", ("dairy", "dairies", "milk", "cheese", "yogurt", "yoghurt", "butter", "curd", "dahi", "paneer", "ghee")),
    ("Condiments & Spreads", ("sauce", "ketchup", "spread", "jam", "condiment", "mayonnaise", "pickle", "dip")),
]

# Used only when a record's categories give no EATGOOD category: words that name the type of food on
# their own. Words that also appear in other kinds of product names ("milk" in milk chocolate and milk
# biscuits, "cheese" in cheese snacks, "butter" in peanut butter, "chocolate" in chocolate cookies) are
# left out, and a name matching more than one category is not categorised.
_NAME_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Packaged Beverages", ("juice", "soda", "cola", "soft drink", "energy drink")),
    ("Breakfast Cereals", ("cornflakes", "corn flakes", "muesli", "granola", "oats")),
    ("Biscuits & Bakery", ("biscuit", "cookie", "cracker", "rusk")),
    ("Snacks", ("chip", "crisp", "namkeen", "bhujia", "popcorn", "makhana", "nachos")),
    ("Instant Foods", ("noodle", "ramen", "instant soup")),
    ("Dairy", ("yogurt", "yoghurt", "dahi")),
]


def _matches(words: str, keywords: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(k)}s?\b", words) for k in keywords)


def _category_for_entry(words: str) -> str | None:
    for category, keywords in _CATEGORY_RULES:
        if _matches(words, keywords):
            return category
    return None


def category_from_product_name(product_name: str | None) -> str | None:
    """The category a product name states unambiguously ("... Instant Noodles"), else None."""
    words = re.sub(r"[^a-z]+", " ", str(product_name or "").lower()).strip()
    found = {category for category, keywords in _NAME_RULES if _matches(words, keywords)}
    return found.pop() if len(found) == 1 else None


def map_off_category_to_eatgood(
    categories_str: str | None, categories_tags: list | None, product_name: str | None = None
) -> str:
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
        # "Dairy by-products" and similar name what a food is made from, not the type of food:
        # some crisps carry it, and it must not make them Dairy.
        if re.search(r"\bby products?\b", words):
            continue
        # The plain "Meals" entry (ready meals and other convenience dishes); "meal replacements" and
        # similar longer names are not included.
        category = "Instant Foods" if words in ("meal", "meals") else _category_for_entry(words)
        if category:
            return category

    # No category from the record's categories: use the product name only if it names the type of
    # food unambiguously. Otherwise never guess: "Uncategorised" has no thresholds, so no grade is given.
    return category_from_product_name(product_name) or UNCATEGORISED


def _sold_in_india(countries_tags: list | None) -> bool | None:
    if not countries_tags:
        return None
    return "en:india" in countries_tags


def _specific_category_name(categories_tags: list | None) -> str:
    """The most specific English category tag as words ("en:potato-crisps" -> "Potato crisps")."""
    for tag in reversed(categories_tags or []):
        if str(tag).startswith("en:"):
            return str(tag)[3:].replace("-", " ").capitalize()
    return "Packaged food"


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

    # An unknown serving size stays unknown: per-serving values can't be converted without it.

    # Product Name
    product_name = (
        off_product.get("product_name") or
        off_product.get("product_name_en") or
        off_product.get("generic_name") or
        off_product.get("generic_name_en") or
        f"Product {requested_barcode}"
    ).strip()

    # Category determination
    category = ALCOHOLIC if is_alcoholic(off_product) else map_off_category_to_eatgood(
        off_product.get("categories"),
        off_product.get("categories_tags"),
        product_name,
    )

    # Measurement basis. Open Food Facts states values as entered on the label (keys without a suffix,
    # on the label's basis, nutrition_data_per) and, whenever it can, recalculated per 100 g/ml (keys
    # ending in _100g). The _100g values are used when present, so the basis is per 100 g/ml whatever
    # the label's own basis; mixing the two would convert per-100 g values a second time.
    nutrition_data_per = str(off_product.get("nutrition_data_per") or "").lower().strip()
    has_per_100 = any(k.endswith("_100g") and v not in (None, "") for k, v in nutriments.items())
    label_per_serving = "serving" in nutrition_data_per and not has_per_100
    if label_per_serving:
        measurement_basis = "per serving"
    elif "100ml" in nutrition_data_per or category == "Packaged Beverages":
        measurement_basis = "per 100ml"
        serving_size_unit = "ml"
    else:
        measurement_basis = "per 100g"

    def _keys(*names: str) -> list[str]:
        """Lookup keys for a nutrient: the _100g values, plus the label's values when those are
        on the same basis (not per serving while _100g values are used)."""
        keys = [f"{n}_100g" for n in names]
        if not (has_per_100 and "serving" in nutrition_data_per):
            keys += list(names) + [f"{n}_value" for n in names]
        return keys

    # Open Food Facts units: _100g values and values without a suffix are in grams (energy in kJ,
    # "energy-kcal" in kcal); _value keys are as typed from the label, in the unit named by <name>_unit
    # (Indian labels often give sodium in mg). Missing or unreadable values stay None, never 0.
    def _nutrient(*names: str, units: dict[str, float] | None = None) -> float | None:
        units = units or _MASS_UNITS_IN_G
        for key in _keys(*names):
            value = parse_float_safe(nutriments.get(key))
            if value is None:
                continue
            if key.endswith("_value"):
                unit = str(nutriments.get(key[:-len("_value")] + "_unit") or "").strip().lower()
                if unit not in units:
                    continue  # unit not stated or not understood: don't guess it
                value *= units[unit]
            return value
        return None

    def _rounded(value: float | None, digits: int = 2, scale: float = 1.0) -> float | None:
        return None if value is None else round(value * scale, digits)

    # Energy (kcal): kcal values first, then kJ converted (1 kcal = 4.184 kJ).
    energy_kcal = _rounded(_nutrient("energy-kcal", units={"kcal": 1.0}), 1)
    if energy_kcal is None:
        kj = _nutrient("energy-kj", "energy", units={"kj": 1.0, "kcal": 4.184})
        energy_kcal = _rounded(kj, 1, 1 / 4.184)

    protein_g = _rounded(_nutrient("proteins", "protein"))
    carbohydrates_g = _rounded(_nutrient("carbohydrates"))
    sugars_g = _rounded(_nutrient("sugars"))
    added_sugars_g = _rounded(_nutrient("added-sugars"))
    total_fat_g = _rounded(_nutrient("fat", "total-fat"))
    saturated_fat_g = _rounded(_nutrient("saturated-fat", "saturated_fat"))
    trans_fat_g = _rounded(_nutrient("trans-fat", "trans_fat"))
    dietary_fibre_g = _rounded(_nutrient("fiber", "fibre"))

    # Sodium (mg), or from salt: salt (g) = sodium (g) x 2.5.
    sodium_mg = _rounded(_nutrient("sodium"), 1, 1000.0)
    if sodium_mg is None:
        sodium_mg = _rounded(_nutrient("salt"), 1, 1000.0 / 2.5)

    cholesterol_mg = _rounded(_nutrient("cholesterol"), 1, 1000.0)

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
        "sub_category": _specific_category_name(off_product.get("categories_tags")),
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
        "image_small_url": off_product.get("image_front_small_url") or image_url,
        # Sold in India only on evidence: Open Food Facts lists India among the countries where the
        # product is sold. None when the record has no country information (never guessed from the
        # brand or the barcode prefix).
        "sold_in_india": _sold_in_india(off_product.get("countries_tags")),
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


_OFF_QUERY_CACHE: dict[tuple[str, int, int, str | None], tuple[float, list[dict[str, Any]], int | None]] = {}
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


# Characters with a meaning in the search service's query syntax. Removed from visitor text so a
# search for "lay's (salted)" is plain words, never a malformed or altered query.
_QUERY_SYNTAX_CHARS = re.compile(r'[+\-&|!(){}\[\]^"~*?:\\/<>=]')
# Apostrophes are dropped rather than spaced: "lay's" is searched as "lays".
_APOSTROPHES = re.compile(r"['\u2019]")


def clean_search_text(text: str) -> str:
    """Visitor text reduced to plain lower-case words (operators like AND/OR are lower-cased too)."""
    return " ".join(_QUERY_SYNTAX_CHARS.sub(" ", _APOSTROPHES.sub("", str(text))).lower().split())


def search_openfoodfacts(
    query: str, limit: int = 24, page: int = 1, sort_by: str | None = None, client: httpx.Client | None = None
) -> dict[str, Any]:
    """
    One page of Open Food Facts search results for a query in the search service's syntax
    (plain words plus field filters such as countries_tags:"en:india"). Returns
    {"status": "ok"|"error", "products": [...], "count": total matches or None,
    "error_code"?, "http_status"?, "message"?}. An error is never reported as an empty result.
    """
    now = time.time()
    cache_key = (query, page, limit, sort_by)
    cached = _OFF_QUERY_CACHE.get(cache_key)
    if cached and now - cached[0] < OFF_QUERY_CACHE_TTL:
        return {"status": "ok", "products": cached[1], "count": cached[2]}

    params: dict[str, Any] = {
        "q": query,
        "langs": "en",
        "page": page,
        "page_size": limit,
        "fields": OFF_REQUEST_FIELDS,
    }
    if sort_by:
        params["sort_by"] = sort_by
    try:
        response = _get_with_retry(client or get_client(), OFF_SEARCH_URL, params)
    except httpx.HTTPError as exc:
        logger.warning("Open Food Facts search failed for %r: %r", query, exc)
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
        if is_alcoholic(raw):
            continue
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


def search_openfoodfacts_text(
    query: str, limit: int = 6, client: httpx.Client | None = None, page: int = 1
) -> dict[str, Any]:
    """Plain-text search (any product, any country). Short or empty text returns no results."""
    clean_q = clean_search_text(query)
    if len(clean_q) < 2:
        return {"status": "ok", "products": [], "count": 0}
    return search_openfoodfacts(clean_q, limit=limit, page=page, client=client)
