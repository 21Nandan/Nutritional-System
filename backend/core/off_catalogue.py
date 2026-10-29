"""
EATGOOD — product catalogue backed by the Open Food Facts search service.

Builds search-service queries for the catalogue page (category, country, nutrient limits,
photo filter, natural-language intents like "low sugar biscuits") and for healthier
alternatives. Query syntax checked against search.openfoodfacts.org on 2026-10-29:
field filters, AND / OR / NOT, parentheses and [min TO max] ranges on nutriments.* work;
`_exists_` does not.
"""

from typing import Any

from backend.core.openfoodfacts import clean_search_text, search_openfoodfacts
from backend.core.semantic_search import CATEGORY_SYNONYMS, parse_semantic_intent

# The catalogue's categories as search-service filters. A product found through one of these is
# still assigned its EATGOOD category by map_off_category_to_eatgood, from its own tags.
CATEGORY_FILTERS: dict[str, str] = {
    "Snacks": 'categories_tags:"en:salty-snacks"',
    "Breakfast Cereals": 'categories_tags:"en:breakfast-cereals"',
    "Biscuits & Bakery": '(categories_tags:"en:biscuits-and-cakes" OR categories_tags:"en:breads")',
    "Chocolates & Sweets": '(categories_tags:"en:chocolates" OR categories_tags:"en:confectioneries")',
    "Instant Foods": '(categories_tags:"en:instant-noodles" OR categories_tags:"en:noodles" OR categories_tags:"en:soups")',
    "Dairy": 'categories_tags:"en:dairies"',
    "Condiments & Spreads": '(categories_tags:"en:condiments" OR categories_tags:"en:spreads" OR categories_tags:"en:sauces")',
    "Packaged Beverages": '(categories_tags:"en:beverages" AND NOT categories_tags:"en:alcoholic-beverages")',
}
CATEGORIES = list(CATEGORY_FILTERS)

INDIA = 'countries_tags:"en:india"'
# Only products with a stated energy value: entries without nutrition facts can't be assessed.
HAS_NUTRITION = "nutriments.energy-kcal_100g:[0 TO 1000]"
HAS_PHOTO = 'states_tags:"en:front-photo-selected"'
POPULAR_FIRST = "-unique_scans_n"
# The search service pages through at most this many results.
MAX_RESULT_WINDOW = 10_000

# Allergen tags used to drop products that declare an allergen the query excludes.
ALLERGEN_TAGS = {
    "peanuts": "en:peanuts",
    "gluten": "en:gluten",
    "dairy": "en:milk",
    "soy": "en:soybeans",
    "egg": "en:eggs",
}

def _nutrient_ranges(filters: dict[str, float | None]) -> list[str]:
    """Nutrient limits as ranges on the per-100 g/ml values (sodium is stored in grams there)."""
    ranges = []
    if filters.get("max_sugars") is not None:
        ranges.append(f"nutriments.sugars_100g:[0 TO {filters['max_sugars']}]")
    max_sodium = filters.get("max_sodium")
    if max_sodium is not None:
        ranges.append(f"nutriments.sodium_100g:[0 TO {max_sodium / 1000}]")
    if filters.get("max_sat_fat") is not None:
        ranges.append(f"nutriments.saturated-fat_100g:[0 TO {filters['max_sat_fat']}]")
    if filters.get("min_fibre") is not None:
        ranges.append(f"nutriments.fiber_100g:[{filters['min_fibre']} TO 100]")
    if filters.get("min_protein") is not None:
        ranges.append(f"nutriments.proteins_100g:[{filters['min_protein']} TO 100]")
    if filters.get("max_kcal") is not None:
        ranges.append(f"nutriments.energy-kcal_100g:[0 TO {filters['max_kcal']}]")
    return ranges


def build_catalogue_query(
    text: str = "",
    category: str = "All",
    india_only: bool = True,
    nutrient_filters: dict[str, float | None] | None = None,
    has_image: bool = False,
) -> tuple[str, dict[str, Any] | None]:
    """The search-service query for a catalogue view, and the interpreted intent if the text had one."""
    words = clean_search_text(text)
    filters = dict(nutrient_filters or {})
    excluded: list[str] = []
    interpreted = None

    intent = parse_semantic_intent(words) if words else None
    if intent and (intent["nutrient_filters"] or intent["excluded_allergens"]):
        # "low sugar biscuits without peanuts": the category, limits and exclusions become filters,
        # and the remaining words are searched as text.
        if category in ("All", "") and intent["category"]:
            category = intent["category"]
        for key, value in intent["nutrient_filters"].items():
            filters.setdefault(key, value)
        excluded = intent["excluded_allergens"]
        words = " ".join(t for t in intent["keyword_tokens"] if t not in _category_words(category))
        interpreted = {
            "category": intent["category"],
            "nutrient_focus": intent["nutrient_descriptions"],
            "excluded_allergens": excluded,
            "keywords": words.split(),
        }

    clauses = [words] if words else []
    if india_only:
        clauses.append(INDIA)
    if category not in ("All", ""):
        if category not in CATEGORY_FILTERS:
            raise ValueError(f"Unknown category: {category}")
        clauses.append(CATEGORY_FILTERS[category])
    clauses.append(HAS_NUTRITION)
    clauses += _nutrient_ranges(filters)
    if has_image:
        clauses.append(HAS_PHOTO)
    clauses += [f'NOT allergens_tags:"{ALLERGEN_TAGS[a]}"' for a in excluded if a in ALLERGEN_TAGS]
    return " AND ".join(clauses), interpreted


def _category_words(category: str) -> set[str]:
    return {w for syn in CATEGORY_SYNONYMS.get(category, []) for w in syn.split()}


def browse_catalogue(
    text: str = "",
    category: str = "All",
    india_only: bool = True,
    nutrient_filters: dict[str, float | None] | None = None,
    has_image: bool = False,
    limit: int = 30,
    page: int = 1,
) -> dict[str, Any]:
    """One catalogue page. Text searches are ranked by relevance, plain browsing by popularity."""
    query, interpreted = build_catalogue_query(text, category, india_only, nutrient_filters, has_image)
    sort = None if clean_search_text(text) else POPULAR_FIRST
    result = search_openfoodfacts(query, limit=limit, page=page, sort_by=sort)
    result["interpreted_intent"] = interpreted
    return result


def alternative_candidates(product: dict[str, Any], limit: int = 40) -> dict[str, Any]:
    """Popular products sold in India from the same EATGOOD category, for healthier alternatives."""
    category = product.get("category")
    if category not in CATEGORY_FILTERS:
        return {"status": "ok", "products": [], "count": 0}
    query = " AND ".join([INDIA, CATEGORY_FILTERS[category], HAS_NUTRITION])
    result = search_openfoodfacts(query, limit=limit, page=1, sort_by=POPULAR_FIRST)
    if result["status"] == "ok":
        own = str(product.get("barcode") or "")
        # The search filter is broader than the EATGOOD category (e.g. "salty snacks" includes
        # crackers graded as bakery), so keep only products assigned the same category.
        result["products"] = [
            p for p in result["products"] if p.get("category") == category and str(p.get("barcode")) != own
        ]
    return result
