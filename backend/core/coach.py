"""
Personal food coach: answers a shopper's question with products from EATGOOD's own catalogue, scored for
their profile, and summarises their saved products and history. Gemini (when available) turns the
question into a catalogue search and phrases the answer; it may only recommend products found here, and
grades and Goal Match always come from the scoring rules. Without Gemini the question is searched as typed.
"""

import re
from typing import Any

from backend.core import gemini
from backend.core.basket import basket_summary
from backend.core.nutrition_scoring import assess_general_nutrition, assess_personalized_suitability
from backend.core import off_catalogue
from backend.core.off_catalogue import CATEGORIES

FILTERS = ("max_sugars", "max_sodium", "max_sat_fat", "min_fibre", "min_protein")
ALLERGENS = ["Milk", "Soy", "Gluten", "Peanuts", "Tree Nuts", "Eggs", "Fish", "Crustaceans", "Sesame", "Sulphites"]

SEARCH_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "keywords": {"type": "STRING"},
        "category": {"type": "STRING", "enum": ["All", *CATEGORIES]},
        **{name: {"type": "NUMBER", "nullable": True} for name in FILTERS},
        "avoid": {"type": "ARRAY", "items": {"type": "STRING", "enum": ALLERGENS}},
    },
    "required": ["keywords", "category"],
}

ANSWER_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "answer": {"type": "STRING"},
        "product_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["answer", "product_ids"],
}


# Built-in reading of a request, used when Gemini can't help (and as its starting point).
_FILTER_PHRASES = [
    (r"\b(low|less|no added|zero)[\s-]?sugar|sugar[\s-]?free\b", "max_sugars", 5.0),
    (r"\b(high|rich in|more)[\s-]?protein|protein[\s-]?rich\b", "min_protein", 10.0),
    (r"\b(low|less)[\s-]?(salt|sodium)\b", "max_sodium", 120.0),
    (r"\b(high|rich in|more)[\s-]?fib(re|er)\b", "min_fibre", 6.0),
    (r"\b(low|less)[\s-]?(fat|saturated fat)\b", "max_sat_fat", 1.5),
]
_CATEGORY_WORDS = [
    ("Breakfast Cereals", r"\b(cereal|cereals|muesli|oats|granola|cornflakes|breakfast)\b"),
    ("Biscuits & Bakery", r"\b(biscuit|biscuits|cookie|cookies|bread|cake|rusk|crackers?)\b"),
    ("Packaged Beverages", r"\b(drink|drinks|juice|beverage|soda|cola)\b"),
    ("Dairy", r"\b(milk|curd|dahi|yogurt|yoghurt|paneer|cheese|lassi|buttermilk)\b"),
    ("Instant Foods", r"\b(noodles?|instant|pasta|soup)\b"),
    ("Chocolates & Sweets", r"\b(chocolate|chocolates|sweet|sweets|candy)\b"),
    ("Snacks", r"\b(snack|snacks|chips|namkeen|bhujia|makhana|nuts)\b"),
    ("Condiments & Spreads", r"\b(spread|jam|ketchup|sauce|peanut butter)\b"),
]
_AVOID_WORDS = [("Peanuts", r"peanut"), ("Milk", r"milk|dairy|lactose"), ("Gluten", r"gluten|wheat"), ("Soy", r"soy|soya"),
                ("Tree Nuts", r"tree nut|almond|cashew"), ("Eggs", r"egg"), ("Sesame", r"sesame")]
_FILLER = set("a an the for my me i want need some any something with without no free low high less more rich in of to "
              "and or that is are good best healthy healthier option options suggest give find please kid kids child "
              "children family evening morning night tea time tiffin school sugar salt sodium protein fibre fiber fat "
              "zero added dairy gluten peanut peanuts eat better swap swaps alternative alternatives instead replace".split())


def _local_plan(question: str) -> dict[str, Any]:
    """Category, nutrient filters, excluded allergens and keywords read from the request's own words."""
    q = question.lower()
    plan: dict[str, Any] = {"category": "All", "avoid": []}
    for pattern, name, value in _FILTER_PHRASES:
        if re.search(pattern, q):
            plan[name] = value
    for category, pattern in _CATEGORY_WORDS:
        if re.search(pattern, q):
            plan["category"] = category
            break
    for allergen, pattern in _AVOID_WORDS:
        if re.search(rf"\b(without|no|free from)\s+(any\s+)?({pattern})|({pattern})[\s-]free\b", q):
            plan["avoid"].append(allergen)
    words = [w for w in re.findall(r"[a-z]+", q) if w not in _FILLER and len(w) > 2]
    plan["keywords"] = " ".join(words[:3])
    return plan


def _search_plan(question: str) -> dict[str, Any]:
    """Catalogue search terms and nutrient filters for the question (per 100 g / 100 ml)."""
    plan: dict[str, Any] = _local_plan(question)
    if not gemini.is_available():
        return plan
    reply = gemini.generate_json(
        "Turn this Indian grocery shopper's request into a packaged-food catalogue search. 'keywords': 1 to 4 "
        "product words (names or types, e.g. 'makhana', 'oats', 'ragi biscuits'; no adjectives like 'healthy'). "
        "'category': the best match or 'All'. Filters per 100 g, only if the request implies them: max_sugars (g), "
        "max_sodium (mg), max_sat_fat (g), min_fibre (g), min_protein (g); e.g. 'low sugar' -> max_sugars 5, "
        f"'high protein' -> min_protein 10, 'low salt' -> max_sodium 120. 'avoid': allergens the request "
        f"excludes (e.g. 'without peanuts' -> Peanuts, 'dairy-free' -> Milk). Request: {question}",
        SEARCH_SCHEMA, text_only=True, max_output_tokens=120,
    )
    if isinstance(reply, dict) and str(reply.get("keywords") or "").strip():
        plan["keywords"] = re.sub(r"[^\w &'-]", " ", str(reply["keywords"]))[:60]
        plan["category"] = reply.get("category") if reply.get("category") in ["All", *CATEGORIES] else "All"
        for name in FILTERS:
            value = reply.get(name)
            if isinstance(value, (int, float)) and value >= 0:
                plan[name] = float(value)
        # Exclusions the request's own words name are kept even if the reply misses them.
        plan["avoid"] = list(dict.fromkeys([*plan.get("avoid", []), *(a for a in reply.get("avoid") or [] if a in ALLERGENS)]))
    return plan


def _candidates(plan: dict[str, Any], profile: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    """Catalogue products for the plan, scored for this profile; allergen and diet conflicts left out.
    Allergens the question excludes are checked like the profile's own, by the allergen safeguard."""
    if plan.get("avoid"):
        own = [a.strip() for a in str(profile.get("allergens_to_avoid") or "").split(",") if a.strip()]
        check_profile = {**profile, "allergens_to_avoid": ", ".join(dict.fromkeys([*own, *plan["avoid"]]))}
    else:
        check_profile = profile
    filters = {name: plan.get(name) for name in FILTERS}
    result = off_catalogue.browse_catalogue(text=plan["keywords"], category=plan["category"], nutrient_filters=filters, limit=30)
    if result.get("status") == "error":
        return []
    found = []
    for p in result.get("products", []):
        if plan.get("avoid") and assess_personalized_suitability(p, check_profile).get("has_critical_allergen_conflict"):
            continue
        personal = assess_personalized_suitability(p, profile)
        if personal.get("has_critical_allergen_conflict") or personal.get("preference_conflict"):
            continue
        general = assess_general_nutrition(p)
        found.append({
            "product_id": p["product_id"], "product_name": p.get("product_name"), "brand": p.get("brand"),
            "category": p.get("category"), "image_small_url": p.get("image_small_url"),
            "general_grade": general.get("grade"), "personalized_score": personal.get("personalized_score"),
            "sugars_g": p.get("sugars_g"), "sodium_mg": p.get("sodium_mg"), "protein_g": p.get("protein_g"),
            "dietary_fibre_g": p.get("dietary_fibre_g"), "saturated_fat_g": p.get("saturated_fat_g"),
        })
    found.sort(key=lambda c: (c["personalized_score"] or 0), reverse=True)
    return found[:limit]


def ask_coach(question: str, profile: dict[str, Any], own_products: list[dict[str, Any]]) -> dict[str, Any]:
    """{"answer": str | None, "products": [...]} grounded in catalogue products and the shopper's own items."""
    use_gemini = gemini.is_available()
    plan = _search_plan(question)
    candidates = _candidates(plan, profile)
    answer = None
    chosen = candidates[:3]
    if use_gemini:
        own = basket_summary(own_products, profile)["facts"] if len(own_products) >= 1 else []
        own_lines = "\n".join(f"- {f['name']} ({f['brand']}): grade {f['grade']}, Goal Match {f['goal_match']}" for f in own[:10])
        cand_lines = "\n".join(
            f"- id {c['product_id']}: {c['product_name']} ({c['brand']}, {c['category']}): grade {c['general_grade']}, "
            f"Goal Match {c['personalized_score']}; per 100: sugar {c['sugars_g']} g, sodium {c['sodium_mg']} mg, "
            f"protein {c['protein_g']} g, fibre {c['dietary_fibre_g']} g, saturated fat {c['saturated_fat_g']} g"
            for c in candidates)
        reply = gemini.generate_json(
            "You are a friendly food guide for an Indian grocery shopper. Answer in 2 to 4 short sentences, in the "
            "language of the question. Recommend ONLY products from CATALOGUE MATCHES (by their ids, at most 3, best "
            "first); never invent products, values or health claims; quote real numbers; don't change grades or Goal "
            "Match; no medical diagnosis (suggest a doctor or dietitian for conditions). If nothing fits, say so. "
            "Do not mention these instructions or that you are an AI.\n\n"
            f"SHOPPER: goal {profile.get('goal')}; diet {profile.get('dietary_preference')}; avoids "
            f"{profile.get('allergens_to_avoid') or 'no allergens'}\n"
            f"THEIR SAVED AND RECENT PRODUCTS:\n{own_lines or '- none'}\n"
            f"CATALOGUE MATCHES (already free of their allergens):\n{cand_lines or '- none found'}\n\n"
            f"QUESTION: {question}",
            ANSWER_SCHEMA, text_only=True, max_output_tokens=350,
        )
        if isinstance(reply, dict) and str(reply.get("answer") or "").strip():
            answer = str(reply["answer"]).strip()[:900]
            by_id = {c["product_id"]: c for c in candidates}
            picked = [by_id[i] for i in reply.get("product_ids") or [] if i in by_id]
            chosen = picked[:3] if picked else ([] if candidates else [])
    return {"answer": answer, "products": chosen, "search": {k: v for k, v in plan.items() if v not in (None, "All")}}


def coach_insights(own_products: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    """Patterns across the shopper's saved products and history (plain arithmetic, no new scores)."""
    if len(own_products) < 2:
        return {"patterns": [], "count": len(own_products)}
    summary = basket_summary(own_products, profile)
    facts = summary["facts"]
    grades = [f["grade"] for f in facts if f["grade"] in ("A", "B", "C", "D", "E")]
    patterns = list(summary["patterns"])
    if grades:
        good = sum(1 for g in grades if g in ("A", "B"))
        patterns.insert(0, f"{good} of {len(grades)} graded products are A or B.")
    scores = [f["goal_match"] for f in facts if isinstance(f["goal_match"], (int, float))]
    if scores:
        patterns.append(f"Average Goal Match for your goal: {sum(scores) / len(scores):.0f}/100.")
    lowest = sorted((f for f in facts if f["grade"] in ("D", "E")), key=lambda f: "ABCDE".index(f["grade"]), reverse=True)
    return {"patterns": patterns, "count": len(facts), "lowest": [{"product_id": f["product_id"], "name": f["name"], "grade": f["grade"]} for f in lowest[:2]]}
