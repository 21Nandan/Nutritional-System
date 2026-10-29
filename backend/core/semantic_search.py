"""
EATGOOD — natural-language search intents.
Turns phrases like "low sugar biscuits" into a category, nutrient limits and allergen
exclusions, which off_catalogue applies as search filters.

Examples of handled intents:
- "Less salty snacks for evening" -> Category Snacks, low sodium <= 350mg
- "Breakfast cereal with more fibre" -> Category Breakfast Cereals, high fibre >= 6g
- "High protein snacks without peanuts" -> Category Snacks, high protein >= 8g, exclude peanut
- "Low sugar biscuits" -> Category Biscuits & Bakery, low sugar <= 5g
"""

import re
from typing import Any

CATEGORY_SYNONYMS: dict[str, list[str]] = {
    "Snacks": ["snack", "snacks", "namkeen", "chips", "crisps", "bhujia", "mixture", "sev", "wafers"],
    "Breakfast Cereals": ["cereal", "cereals", "corn flakes", "muesli", "oats", "granola", "breakfast"],
    "Biscuits & Bakery": ["biscuit", "biscuits", "cookie", "cookies", "cracker", "crackers", "rusk", "bakery", "bread", "cake"],
    "Packaged Beverages": ["beverage", "beverages", "drink", "drinks", "juice", "tea", "coffee", "shake", "soda"],
    "Dairy": ["dairy", "milk", "butter", "cheese", "yogurt", "curd", "paneer", "dahi"],
    "Instant Foods": ["noodles", "instant", "soup", "pasta", "ready to eat", "maggi"],
    "Chocolates & Sweets": ["chocolate", "chocolates", "sweet", "sweets", "candy", "mithai", "toffee"],
    "Condiments & Spreads": ["sauce", "ketchup", "spread", "jam", "pickle", "chutney", "mayonnaise"],
}

NUTRIENT_INTENT_PATTERNS: list[dict[str, Any]] = [
    {
        "key": "low_sodium",
        "patterns": [r"\b(less|low|lower|reduced|not\s+too|little)\s+(salty|salt|sodium)\b", r"\blow\s+sodium\b", r"\bless\s+salt\b"],
        "max_sodium": 350.0,
        "description": "Low Sodium (<= 350 mg / 100g)"
    },
    {
        "key": "high_fibre",
        "patterns": [r"\b(more|high|higher|rich\s+in|extra|with)\s+(fibre|fiber)\b", r"\bhigh\s+(fibre|fiber)\b"],
        "min_fibre": 5.0,
        "description": "High Fibre (>= 5 g / 100g)"
    },
    {
        "key": "high_protein",
        "patterns": [r"\b(more|high|higher|rich\s+in|extra)\s+protein\b", r"\bprotein\s+rich\b", r"\bprotein\s+snack\b"],
        "min_protein": 8.0,
        "description": "High Protein (>= 8 g / 100g)"
    },
    {
        "key": "low_sugar",
        "patterns": [r"\b(less|low|lower|reduced|no|zero|without)\s+sugar\b", r"\bsugar\s*free\b", r"\blow\s+sugar\b"],
        "max_sugars": 6.0,
        "description": "Low Sugar (<= 6 g / 100g)"
    },
    {
        "key": "low_fat",
        "patterns": [r"\b(less|low|lower|reduced|not)\s+(oily|fat|saturated\s+fat)\b", r"\blow\s+fat\b", r"\blight\b"],
        "max_sat_fat": 3.0,
        "description": "Low Saturated Fat (<= 3 g / 100g)"
    },
    {
        "key": "low_calorie",
        "patterns": [r"\b(low|less|lower)\s+(calorie|cal|calories)\b", r"\blow\s+cal\b", r"\bdiet\b"],
        "max_kcal": 250.0,
        "description": "Moderate Calories (<= 250 kcal / 100g)"
    }
]

ALLERGEN_EXCLUSION_PATTERNS: list[dict[str, Any]] = [
    {
        "allergen": "peanuts",
        "patterns": [r"\b(without|no|free\s+from|zero)\s+peanuts?\b", r"\bpeanut\s*free\b"],
        "forbidden_terms": ["peanut", "groundnut", "arachis"]
    },
    {
        "allergen": "gluten",
        "patterns": [r"\b(without|no|free\s+from)\s+gluten\b", r"\bgluten\s*free\b"],
        "forbidden_terms": ["gluten", "wheat", "barley", "rye", "maida"]
    },
    {
        "allergen": "dairy",
        "patterns": [r"\b(without|no|free\s+from)\s+(dairy|milk)\b", r"\bdairy\s*free\b", r"\bvegan\b"],
        "forbidden_terms": ["milk", "dairy", "cheese", "butter", "whey", "casein", "lactose"]
    },
    {
        "allergen": "soy",
        "patterns": [r"\b(without|no|free\s+from)\s+soy(a)?\b", r"\bsoy\s*free\b"],
        "forbidden_terms": ["soy", "soya", "soybean"]
    },
    {
        "allergen": "egg",
        "patterns": [r"\b(without|no|free\s+from)\s+eggs?\b", r"\beggless\b"],
        "forbidden_terms": ["egg", "albumin", "ovoglobulin"]
    }
]

def parse_semantic_intent(query: str) -> dict[str, Any]:
    """
    Parses a natural language search query into structured constraints.
    """
    clean_q = query.strip().lower()
    intent: dict[str, Any] = {
        "original_query": query,
        "category": None,
        "nutrient_filters": {},
        "nutrient_descriptions": [],
        "excluded_allergens": [],
        "forbidden_terms": [],
        "keyword_tokens": []
    }

    # 1. Detect Category
    for cat_name, synonyms in CATEGORY_SYNONYMS.items():
        for syn in synonyms:
            if re.search(r"\b" + re.escape(syn) + r"\b", clean_q):
                intent["category"] = cat_name
                break
        if intent["category"]:
            break

    # 2. Detect Nutrient Intents
    for n_intent in NUTRIENT_INTENT_PATTERNS:
        for pat in n_intent["patterns"]:
            if re.search(pat, clean_q):
                intent["nutrient_descriptions"].append(n_intent["description"])
                if "max_sodium" in n_intent:
                    intent["nutrient_filters"]["max_sodium"] = n_intent["max_sodium"]
                if "min_fibre" in n_intent:
                    intent["nutrient_filters"]["min_fibre"] = n_intent["min_fibre"]
                if "min_protein" in n_intent:
                    intent["nutrient_filters"]["min_protein"] = n_intent["min_protein"]
                if "max_sugars" in n_intent:
                    intent["nutrient_filters"]["max_sugars"] = n_intent["max_sugars"]
                if "max_sat_fat" in n_intent:
                    intent["nutrient_filters"]["max_sat_fat"] = n_intent["max_sat_fat"]
                if "max_kcal" in n_intent:
                    intent["nutrient_filters"]["max_kcal"] = n_intent["max_kcal"]
                break

    # 3. Detect Allergen / Negative exclusions
    for a_excl in ALLERGEN_EXCLUSION_PATTERNS:
        for pat in a_excl["patterns"]:
            if re.search(pat, clean_q):
                intent["excluded_allergens"].append(a_excl["allergen"])
                intent["forbidden_terms"].extend(a_excl["forbidden_terms"])
                break

    # 4. Extract remaining keywords for token matching
    # Remove recognized stop words & matched patterns
    token_q = clean_q
    for n_intent in NUTRIENT_INTENT_PATTERNS:
        for pat in n_intent["patterns"]:
            token_q = re.sub(pat, " ", token_q)
    for a_excl in ALLERGEN_EXCLUSION_PATTERNS:
        for pat in a_excl["patterns"]:
            token_q = re.sub(pat, " ", token_q)

    tokens = re.findall(r"\b[a-z]{3,}\b", token_q)
    stop_words = {"for", "the", "and", "with", "without", "from", "that", "this", "some", "good", "best", "give", "find", "show", "items", "products"}
    intent["keyword_tokens"] = [t for t in tokens if t not in stop_words]

    return intent
