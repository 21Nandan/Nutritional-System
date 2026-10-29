"""
EATGOOD — product catalogue backed by the Open Food Facts search service.

Builds search-service queries for the catalogue page (category, country, nutrient limits,
photo filter, natural-language intents like "low sugar biscuits") and for healthier
alternatives. Query syntax checked against search.openfoodfacts.org on 2026-10-29:
field filters, AND / OR / NOT, parentheses and [min TO max] ranges on nutriments.* work;
`_exists_` does not.
"""

import re
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
) -> tuple[list[str], str, dict[str, Any] | None]:
    """The words to search for, the filter clause, and the interpreted intent if the text had one."""
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

    clauses = []
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
    return words.split(), " AND ".join(clauses), interpreted


def compose_query(words: list[str], filter_clause: str) -> str:
    """Search words followed by the filters.

    The search service mishandles "two words AND filter" (checked 2026-10-29: "dairy milk AND
    countries_tags:..." finds nothing), while words separated from the filters by a space are
    searched as text and the filters still apply.
    """
    return f"{' '.join(words)} {filter_clause}".strip()


def _category_words(category: str) -> set[str]:
    return {w for syn in CATEGORY_SYNONYMS.get(category, []) for w in syn.split()}


# How many products a partial-word search looks through (the search service has no prefix search).
PARTIAL_WORD_POOL = 100
# A last word shorter than this is treated as still being typed ("cadbury da").
MIN_COMPLETE_WORD = 3
_BARCODE = re.compile(r"^\d{8,14}$")


def _starts_word(product: dict[str, Any], prefix: str) -> bool:
    text = clean_search_text(f"{product.get('product_name') or ''} {product.get('brand') or ''}")
    return any(word.startswith(prefix) for word in text.split())


def browse_catalogue(
    text: str = "",
    category: str = "All",
    india_only: bool = True,
    nutrient_filters: dict[str, float | None] | None = None,
    has_image: bool = False,
    limit: int = 30,
    page: int = 1,
) -> dict[str, Any]:
    """One catalogue page.

    Text searches are ranked by relevance, plain browsing by popularity. A barcode is looked up
    exactly. When the last word looks unfinished, or the full words find nothing, the complete
    words are searched and results are kept if a word of their name or brand starts with the last
    word, so "cadbury da" finds "Cadbury Dairy Milk".
    """
    words, filter_clause, interpreted = build_catalogue_query(text, category, india_only, nutrient_filters, has_image)
    if len(words) == 1 and _BARCODE.match(words[0]):
        result = search_openfoodfacts(f'code:"{words[0]}"', limit=limit, page=page)
        result.update(interpreted_intent=None, match_mode="barcode")
        return result

    sort = None if words else POPULAR_FIRST
    prefix_search = len(words) > 1 and len(words[-1]) < MIN_COMPLETE_WORD
    if not prefix_search:
        result = search_openfoodfacts(compose_query(words, filter_clause), limit=limit, page=page, sort_by=sort)
        no_match = result["status"] == "ok" and result.get("count") == 0
        if not (words and no_match):
            result.update(interpreted_intent=interpreted, match_mode="words")
            return result

    head, prefix = words[:-1], words[-1]
    pool = search_openfoodfacts(
        compose_query(head, filter_clause), limit=PARTIAL_WORD_POOL, page=1, sort_by=None if head else POPULAR_FIRST
    )
    if pool["status"] == "error":
        return pool
    matches = [p for p in pool["products"] if _starts_word(p, prefix)]
    start = (page - 1) * limit
    return {
        "status": "ok",
        "products": matches[start:start + limit],
        "count": len(matches),
        "interpreted_intent": interpreted,
        "match_mode": "partial",
        "searched_pool": len(pool["products"]),
    }


def alternative_candidates(product: dict[str, Any], limit: int = 40) -> dict[str, Any]:
    """Popular products sold in India from the same EATGOOD category, for healthier alternatives."""
    category = product.get("category")
    if category not in CATEGORY_FILTERS:
        return {"status": "ok", "products": [], "count": 0}
    query = " AND ".join([INDIA, CATEGORY_FILTERS[category], HAS_NUTRITION])  # filters only, no words
    result = search_openfoodfacts(query, limit=limit, page=1, sort_by=POPULAR_FIRST)
    if result["status"] == "ok":
        own = str(product.get("barcode") or "")
        # The search filter is broader than the EATGOOD category (e.g. "salty snacks" includes
        # crackers graded as bakery), so keep only products assigned the same category.
        result["products"] = [
            p for p in result["products"] if p.get("category") == category and str(p.get("barcode")) != own
        ]
    return result
