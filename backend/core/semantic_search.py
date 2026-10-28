"""
EATGOOD — Semantic Food Search Engine
Translates natural language user intents into structured nutritional constraints,
category filters, allergen exclusions, and hybrid BM25/nutrient-ranked results.

Examples of handled intents:
- "Less salty snacks for evening" -> Category Snacks, low sodium <= 350mg, ranked by sodium
- "Breakfast cereal with more fibre" -> Category Breakfast Cereals, high fibre >= 6g, ranked by fibre
- "High protein snacks without peanuts" -> Category Snacks, high protein >= 8g, exclude peanut
- "Low sugar biscuits" -> Category Biscuits & Bakery, low sugar <= 5g
"""

import re
import math
from typing import Dict, Any, List, Optional
import pandas as pd

CATEGORY_SYNONYMS = {
    "Snacks": ["snack", "snacks", "namkeen", "chips", "crisps", "bhujia", "mixture", "sev", "wafers"],
    "Breakfast Cereals": ["cereal", "cereals", "corn flakes", "muesli", "oats", "granola", "breakfast"],
    "Biscuits & Bakery": ["biscuit", "biscuits", "cookie", "cookies", "cracker", "crackers", "rusk", "bakery", "bread", "cake"],
    "Beverages": ["beverage", "beverages", "drink", "drinks", "juice", "tea", "coffee", "shake", "soda"],
    "Dairy": ["dairy", "milk", "butter", "cheese", "yogurt", "curd", "paneer", "dahi"],
    "Instant Foods": ["noodles", "instant", "soup", "pasta", "ready to eat", "maggi"],
    "Edible Oils & Fats": ["oil", "oils", "ghee", "fat", "fats", "cooking oil"],
    "Staples & Grains": ["staples", "rice", "dal", "flour", "atta", "wheat", "grain", "grains", "pulses"]
}

NUTRIENT_INTENT_PATTERNS = [
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

ALLERGEN_EXCLUSION_PATTERNS = [
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

def parse_semantic_intent(query: str) -> Dict[str, Any]:
    """
    Parses a natural language search query into structured constraints.
    """
    clean_q = query.strip().lower()
    intent = {
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

def execute_semantic_search(
    query: str,
    products_df: pd.DataFrame,
    user_profile: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Executes intent-based semantic search with hybrid ranking.
    """
    if products_df is None or products_df.empty:
        return {"total": 0, "products": [], "intent": {}}

    intent = parse_semantic_intent(query)
    df = products_df.copy()

    # Apply strict negative allergen exclusions from query
    if intent["forbidden_terms"]:
        for term in intent["forbidden_terms"]:
            term_l = term.lower()
            df = df[
                ~df["ingredients"].astype(str).str.lower().str.contains(r"\b" + re.escape(term_l) + r"\b", na=False) &
                ~df["allergens_declared"].astype(str).str.lower().str.contains(r"\b" + re.escape(term_l) + r"\b", na=False)
            ]

    # Also apply active user profile allergen exclusions
    if user_profile and user_profile.get("allergens_to_avoid"):
        u_allgs = [a.strip().lower() for a in user_profile["allergens_to_avoid"].split(",") if a.strip()]
        for u_a in u_allgs:
            if u_a not in ["none", ""]:
                df = df[
                    ~df["ingredients"].astype(str).str.lower().str.contains(r"\b" + re.escape(u_a) + r"\b", na=False) &
                    ~df["allergens_declared"].astype(str).str.lower().str.contains(r"\b" + re.escape(u_a) + r"\b", na=False)
                ]

    # Filter Category if detected
    if intent["category"]:
        cat_matches = df[df["category"].str.lower() == intent["category"].lower()]
        if not cat_matches.empty:
            df = cat_matches

    # Calculate Hybrid Score for each candidate
    scored_items = []
    
    for idx, row in df.iterrows():
        p_dict = row.to_dict()
        score = 50.0  # Base score
        explanations = []

        # 1. Nutrient Intent Scoring
        nf = intent["nutrient_filters"]
        
        # Sodium check
        if "max_sodium" in nf:
            s_val = p_dict.get("sodium_mg")
            if pd.notna(s_val):
                s_float = float(s_val)
                if s_float <= nf["max_sodium"]:
                    score += 25.0
                    explanations.append(f"Low sodium ({int(s_float)}mg/100g)")
                elif s_float <= nf["max_sodium"] * 1.5:
                    score += 10.0
                else:
                    score -= 15.0
            else:
                score -= 5.0

        # Fibre check
        if "min_fibre" in nf:
            f_val = p_dict.get("dietary_fibre_g")
            if pd.notna(f_val):
                f_float = float(f_val)
                if f_float >= nf["min_fibre"]:
                    score += 25.0
                    explanations.append(f"High fibre ({f_float}g/100g)")
                elif f_float >= nf["min_fibre"] * 0.7:
                    score += 10.0
                else:
                    score -= 10.0

        # Protein check
        if "min_protein" in nf:
            p_val = p_dict.get("protein_g")
            if pd.notna(p_val):
                p_float = float(p_val)
                if p_float >= nf["min_protein"]:
                    score += 25.0
                    explanations.append(f"High protein ({p_float}g/100g)")
                elif p_float >= nf["min_protein"] * 0.7:
                    score += 10.0
                else:
                    score -= 10.0

        # Sugar check
        if "max_sugars" in nf:
            sg_val = p_dict.get("sugars_g")
            if pd.notna(sg_val):
                sg_float = float(sg_val)
                if sg_float <= nf["max_sugars"]:
                    score += 25.0
                    explanations.append(f"Low sugar ({sg_float}g/100g)")
                elif sg_float <= nf["max_sugars"] * 1.5:
                    score += 10.0
                else:
                    score -= 15.0

        # Saturated fat check
        if "max_sat_fat" in nf:
            sf_val = p_dict.get("saturated_fat_g")
            if pd.notna(sf_val):
                sf_float = float(sf_val)
                if sf_float <= nf["max_sat_fat"]:
                    score += 20.0
                    explanations.append(f"Low saturated fat ({sf_float}g/100g)")
                else:
                    score -= 10.0

        # 2. Text Keyword Token Matching
        if intent["keyword_tokens"]:
            text_corpus = f"{p_dict.get('product_name', '')} {p_dict.get('brand', '')} {p_dict.get('category', '')} {p_dict.get('sub_category', '')} {p_dict.get('ingredients', '')}".lower()
            matched_tokens = [t for t in intent["keyword_tokens"] if t in text_corpus]
            if matched_tokens:
                score += len(matched_tokens) * 15.0
                explanations.append(f"Keyword match: {', '.join(matched_tokens)}")
            else:
                score -= 10.0

        # 3. Active User Profile Match Bonus
        if user_profile:
            u_goal = user_profile.get("goal", "")
            if "Reduce Sugar" in u_goal and pd.notna(p_dict.get("sugars_g")) and float(p_dict["sugars_g"]) <= 6.0:
                score += 10.0
            if "Reduce Sodium" in u_goal and pd.notna(p_dict.get("sodium_mg")) and float(p_dict["sodium_mg"]) <= 350.0:
                score += 10.0
            if "Increase Fibre" in u_goal and pd.notna(p_dict.get("dietary_fibre_g")) and float(p_dict["dietary_fibre_g"]) >= 5.0:
                score += 10.0
            if "Increase Protein" in u_goal and pd.notna(p_dict.get("protein_g")) and float(p_dict["protein_g"]) >= 8.0:
                score += 10.0

        # Format explanation
        if not explanations:
            if intent["category"]:
                explanations.append(f"Matches category '{intent['category']}'")
            else:
                explanations.append("Catalogue match")

        p_dict["semantic_score"] = round(min(max(score, 5.0), 99.0), 1)
        p_dict["semantic_reason"] = " • ".join(explanations)
        clean_item = {k: (None if pd.isna(v) else v) for k, v in p_dict.items()}
        scored_items.append(clean_item)

    # Sort descending by semantic score
    scored_items.sort(key=lambda x: x["semantic_score"], reverse=True)

    total_matches = len(scored_items)
    paginated = scored_items[offset: offset + limit]

    return {
        "query": query,
        "interpreted_intent": {
            "category": intent["category"],
            "nutrient_focus": intent["nutrient_descriptions"],
            "excluded_allergens": intent["excluded_allergens"],
            "keywords": intent["keyword_tokens"]
        },
        "total": total_matches,
        "products": paginated
    }
