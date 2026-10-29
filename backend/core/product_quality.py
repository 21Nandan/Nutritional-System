"""
EATGOOD — product data quality, search eligibility and ranking.

One deterministic set of rules used wherever lists of products are shown (catalogue pages,
product search, healthier alternatives), whatever the source of the records:

1. Eligibility: a product is listed only if its key nutrition data is usable. Missing values are
   never treated as zero; values that contradict each other or are physically impossible make a
   record ineligible (same checks as grading, nutrition_validator).
2. Relevance to the search text comes first: exact name, name prefix, whole words, word starts,
   close spellings (typos), brand.
3. Among similarly relevant products, better records rank higher: nutrition completeness,
   ingredient and allergen information, product identity (barcode check digit, name, brand) and
   evidence of sale in India.
4. Duplicate records (same barcode, or same brand, name and nutrition values) are merged,
   keeping the most complete one.
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from backend.core.barcode_utils import validate_barcode
from backend.core.nutrition_validator import parse_float_safe, validate_and_normalize_nutrition

# The core nutrition panel declared on Indian packaged foods (energy, protein, carbohydrate, sugars,
# total fat, saturated fat, sodium). A product needs energy and may miss at most MAX_MISSING_ESSENTIAL
# of the others.
ESSENTIAL_FIELDS = (
    "energy_kcal", "protein_g", "carbohydrates_g", "sugars_g", "total_fat_g", "saturated_fat_g", "sodium_mg",
)
# Often absent from labels; their absence never makes a product ineligible.
OPTIONAL_FIELDS = ("dietary_fibre_g", "added_sugars_g", "trans_fat_g", "cholesterol_mg")
MAX_MISSING_ESSENTIAL = 3

# Relevance bands: products are ordered by band first, so a weak match can never outrank a strong
# one because of better data. Within a band, data quality decides.
RELEVANCE_BAND_SIZE = 20
_FUZZY_WORD = 0.8  # similarity at which a word counts as a likely misspelling


def _present(value: Any) -> bool:
    return parse_float_safe(value) is not None


def _words(text: Any) -> list[str]:
    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", plain.replace("'", "").replace("’", ""))


def assess_record(product: dict[str, Any]) -> dict[str, Any]:
    """Completeness, validity and identity facts about one product record."""
    validation = validate_and_normalize_nutrition(product, mandatory_fields=list(ESSENTIAL_FIELDS))
    missing_essential = [f for f in ESSENTIAL_FIELDS if not _present(product.get(f))]
    present_optional = [f for f in OPTIONAL_FIELDS if _present(product.get(f))]
    has_ingredients = bool(str(product.get("ingredients") or "").strip())
    has_allergen_info = bool(str(product.get("allergens_declared") or "").strip())

    reasons = []
    if validation["contradictions"]:
        reasons.append("invalid nutrition values")
    if not _present(product.get("energy_kcal")):
        reasons.append("energy not stated")
    if len(missing_essential) > MAX_MISSING_ESSENTIAL:
        reasons.append(f"{len(missing_essential)} of {len(ESSENTIAL_FIELDS)} key nutrition values missing")
    if not _words(product.get("product_name")):
        reasons.append("no product name")

    essential_share = (len(ESSENTIAL_FIELDS) - len(missing_essential)) / len(ESSENTIAL_FIELDS)
    optional_share = len(present_optional) / len(OPTIONAL_FIELDS)
    barcode = validate_barcode(str(product.get("barcode") or ""), strict=False)
    brand = str(product.get("brand") or "").strip()
    identity = (
        0.5 * bool(barcode["is_valid"] and barcode["check_digit_valid"])
        + 0.25 * bool(brand and brand.lower() not in ("unknown brand", "unknown"))
        + 0.25 * (len(" ".join(_words(product.get("product_name")))) >= 4)
    )
    # Weights add up to 1: nutrition matters most, then ingredients/allergens, identity, market.
    quality = (
        0.45 * essential_share
        + 0.10 * optional_share
        + 0.10 * has_ingredients
        + 0.10 * has_allergen_info
        + 0.15 * identity
        + 0.10 * (product.get("sold_in_india") is True)
    )
    return {
        "eligible": not reasons,
        "ineligible_reasons": reasons,
        "missing_essential": missing_essential,
        "completeness": round(essential_share * 0.8 + optional_share * 0.2, 3),
        "quality": round(quality, 4),
        "identity_confidence": identity,
    }


def relevance(product: dict[str, Any], query: str) -> int:
    """0–100: how well the product's name and brand match the search text (0 = no text match)."""
    q_words = _words(query)
    if not q_words:
        return 0
    name_words = _words(product.get("product_name"))
    brand_words = _words(product.get("brand"))
    text_words = name_words + brand_words
    name = " ".join(name_words)
    q = " ".join(q_words)
    if not text_words:
        return 0
    if name == q or " ".join(brand_words + name_words) == q:
        return 100
    if name.startswith(q):
        return 90

    def word_score(w: str, is_last: bool) -> float:
        # A word found in the product name counts more than one found only in the brand, so
        # "kurkure" ranks products named "Kurkure ..." above other products of that brand.
        for words, weight in ((name_words, 1.0), (brand_words, 0.8)):
            if w in words:
                return weight
        for words, weight in ((name_words, 0.85), (brand_words, 0.7)):
            if is_last and any(t.startswith(w) for t in words):
                return weight  # word still being typed
        if len(w) >= 4:
            for words, weight in ((name_words, 0.7), (brand_words, 0.6)):
                if words and max(SequenceMatcher(None, w, t).ratio() for t in words) >= _FUZZY_WORD:
                    return weight  # likely misspelling
        return 0.0

    scores = [word_score(w, i == len(q_words) - 1) for i, w in enumerate(q_words)]
    matched = sum(1 for s in scores if s > 0)
    if matched == 0:
        return 0
    coverage = sum(scores) / len(q_words)
    brand_bonus = 5 if any(w in brand_words for w in q_words) else 0
    # All words matched (exactly or nearly): 50–85. Some words matched: up to 45.
    base = 50 + 30 * coverage if matched == len(q_words) else 45 * coverage
    return int(min(base + brand_bonus, 89))


def _identity_key(product: dict[str, Any]) -> tuple:
    nutrition = tuple(parse_float_safe(product.get(f)) for f in ESSENTIAL_FIELDS)
    return (" ".join(_words(product.get("brand"))), " ".join(_words(product.get("product_name"))), nutrition)


def rank_products(products: list[dict[str, Any]], query: str = "") -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Eligible, de-duplicated products in a deterministic order, plus counts of what was removed.

    Order: relevance band (all equal without search text), then data quality, then exact
    relevance, then the original order (the search service's own relevance or popularity).
    """
    scored = []
    removed = {"ineligible": 0, "duplicates": 0}
    for position, product in enumerate(products):
        facts = assess_record(product)
        if not facts["eligible"]:
            removed["ineligible"] += 1
            continue
        scored.append((product, facts, relevance(product, query), position))

    best: dict[tuple, tuple] = {}
    order: list[tuple] = []
    for item in scored:
        product, facts = item[0], item[1]
        barcode = str(product.get("barcode") or "").lstrip("0")
        keys: list[tuple[str, Any]] = [("barcode", barcode)] if barcode else []
        keys.append(("record", _identity_key(product)))
        existing = next((best[k] for k in keys if k in best), None)
        if existing is None:
            order.append(item)
            for k in keys:
                best[k] = item
            continue
        removed["duplicates"] += 1
        if facts["quality"] > existing[1]["quality"]:
            order[order.index(existing)] = item
            for k in keys:
                best[k] = item

    order.sort(key=lambda it: (-(it[2] // RELEVANCE_BAND_SIZE), -it[1]["quality"], -it[2], it[3]))
    ranked = []
    for product, facts, rel, _ in order:
        ranked.append({**product, "data_completeness_score": facts["completeness"], "search_relevance": rel})
    return ranked, removed
