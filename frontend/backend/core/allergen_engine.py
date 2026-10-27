"""
EATGOOD — Allergen & Additive Assessment Engine (Layer 3)
Analyzes available ingredients, additives, and allergen declarations.
Distinguishes confirmed presence, warnings, potential matches, and unknown statuses.
Enforces hard safety exclusions without fabricating toxicology claims.
"""

import re

MAJOR_ALLERGENS = {
    "Milk": {
        "keywords": ["milk", "dairy", "butter", "cheese", "whey", "casein", "lactose", "curd", "paneer", "dahi", "cream", "ghee", "milk solids", "skimmed milk"],
        "fssai_mandate": True
    },
    "Soy": {
        "keywords": ["soy", "soya", "soybean", "soy lecithin", "edamame", "hydrolysed vegetable protein (soy)", "tofu"],
        "fssai_mandate": True
    },
    "Gluten": {
        "keywords": ["gluten", "wheat", "maida", "atta", "barley", "malt", "rye", "oats (non-certified)", "semolina", "suji", "rava"],
        "fssai_mandate": True
    },
    "Peanuts": {
        "keywords": ["peanut", "peanuts", "groundnut", "groundnuts", "monkey nut", "arachis"],
        "fssai_mandate": True
    },
    "Tree Nuts": {
        "keywords": ["almond", "almonds", "cashew", "cashews", "walnut", "walnuts", "pistachio", "pistachios", "hazelnut", "hazelnuts", "pecan", "brazil nut", "badam", "kaju", "akhrot", "pista"],
        "fssai_mandate": True
    },
    "Eggs": {
        "keywords": ["egg", "eggs", "egg powder", "albumin", "egg yolk", "lysozyme", "ovalbumin"],
        "fssai_mandate": True
    },
    "Fish": {
        "keywords": ["fish", "cod", "salmon", "tuna", "anchovy", "gelatin (fish)", "isinglass"],
        "fssai_mandate": True
    },
    "Crustaceans": {
        "keywords": ["crustacean", "crustaceans", "shrimp", "prawn", "crab", "lobster", "krill"],
        "fssai_mandate": True
    },
    "Sesame": {
        "keywords": ["sesame", "til", "tahini", "sesame seeds", "sesame oil"],
        "fssai_mandate": False
    },
    "Sulphites": {
        "keywords": ["sulphite", "sulfite", "sulphur dioxide", "sodium metabisulphite", "ins 220", "ins 221", "ins 222", "ins 223", "ins 224"],
        "fssai_mandate": True
    }
}

ADDITIVE_KNOWLEDGE_BASE = {
    "INS 621": {"name": "Monosodium Glutamate (MSG)", "class": "Flavour Enhancer", "note": "Permitted food additive under FSSAI and Codex. Produces savory umami taste."},
    "INS 627": {"name": "Disodium Guanylate", "class": "Flavour Enhancer", "note": "Synergistic umami enhancer commonly paired with inosinate."},
    "INS 631": {"name": "Disodium Inosinate", "class": "Flavour Enhancer", "note": "Nucleotide flavour enhancer naturally occurring in foods."},
    "INS 635": {"name": "Disodium 5'-Ribonucleotides", "class": "Flavour Enhancer", "note": "Standard umami combination additive."},
    "INS 102": {"name": "Tartrazine", "class": "Synthetic Food Colour (Yellow 5)", "note": "Permitted synthetic food colour subject to maximum statutory limits."},
    "INS 110": {"name": "Sunset Yellow FCF", "class": "Synthetic Food Colour (Yellow 6)", "note": "Permitted synthetic food colour with regulated maximum levels."},
    "INS 122": {"name": "Carmoisine / Azorubine", "class": "Synthetic Food Colour (Red 3)", "note": "Permitted synthetic food colour in India."},
    "INS 150d": {"name": "Caramel IV (Sulphite Ammonia Caramel)", "class": "Food Colour", "note": "Widely used brown colourant in colas and baked goods."},
    "INS 211": {"name": "Sodium Benzoate", "class": "Preservative (Antimicrobial)", "note": "Permitted preservative under FSSAI limits; inhibits mould and yeast in acidic foods."},
    "INS 260": {"name": "Acetic Acid", "class": "Acidity Regulator", "note": "Standard vinegar component; food-grade preservative."},
    "INS 322": {"name": "Lecithin (Soy / Sunflower)", "class": "Emulsifier", "note": "Natural lipid emulsifier; flag as Soy allergen when soy-derived."},
    "INS 330": {"name": "Citric Acid", "class": "Acidity Regulator & Antioxidant", "note": "Standard organic acid found in citrus fruits."},
    "INS 412": {"name": "Guar Gum", "class": "Thickener & Stabilizer", "note": "Plant-derived hydrocolloid from guar beans."},
    "INS 471": {"name": "Mono- and Di-glycerides of Fatty Acids", "class": "Emulsifier", "note": "Standard food-grade lipid emulsifier."},
    "INS 500(ii)": {"name": "Sodium Bicarbonate", "class": "Raising Agent", "note": "Baking soda; safe mineral leavening agent."},
    "INS 503(ii)": {"name": "Ammonium Bicarbonate", "class": "Raising Agent", "note": "Baker's ammonia; standard biscuit leavener."}
}

def analyze_allergens(ingredients: str, allergens_declared: str, user_allergens_to_avoid: list = None):
    """
    Evaluates allergens present in a product against declared labels and user requirements.
    Never assumes safety when allergen information is missing!
    """
    if user_allergens_to_avoid is None:
        user_allergens_to_avoid = []

    user_allgs_normalized = [a.strip().lower() for a in user_allergens_to_avoid if a.strip() and a.lower() != "none"]

    ing_text = str(ingredients or "").lower()
    decl_text = str(allergens_declared or "").lower()

    # Distinguish status
    has_declaration = bool(decl_text.strip() and decl_text.strip() != "none declared" and decl_text.strip() != "nan")
    has_ingredients = bool(ing_text.strip() and ing_text.strip() != "nan")

    allergen_results = []
    user_conflicts = []

    for allergen, info in MAJOR_ALLERGENS.items():
        allg_lower = allergen.lower()
        confirmed = False
        warning = False
        ingredient_match = False
        matched_terms = []

        # 1. Check explicit declaration
        if has_declaration:
            if allg_lower in decl_text or (allg_lower == "gluten" and "wheat" in decl_text):
                confirmed = True
                matched_terms.append("Declared on label")
            elif "may contain" in decl_text and allg_lower in decl_text:
                warning = True
                matched_terms.append("Cross-contact advisory declaration")

        # 2. Check ingredient keywords
        if has_ingredients:
            for kw in info["keywords"]:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, ing_text):
                    ingredient_match = True
                    matched_terms.append(f"Found keyword '{kw}' in ingredients")
                    break

        # Synthesize status for this allergen
        if confirmed:
            status = "Confirmed Allergen"
            severity = "high"
        elif ingredient_match:
            status = "Ingredient Match (Requires Review)"
            severity = "medium"
        elif warning:
            status = "Advisory Warning (May Contain)"
            severity = "medium"
        else:
            status = "Not Detected in Available Text"
            severity = "low"

        is_user_conflict = False
        if allg_lower in user_allgs_normalized or (allg_lower == "gluten" and "wheat" in user_allgs_normalized):
            if status in ["Confirmed Allergen", "Ingredient Match (Requires Review)", "Advisory Warning (May Contain)"]:
                is_user_conflict = True
                user_conflicts.append({
                    "allergen": allergen,
                    "status": status,
                    "evidence": matched_terms
                })

        if status != "Not Detected in Available Text":
            allergen_results.append({
                "allergen": allergen,
                "status": status,
                "severity": severity,
                "evidence": matched_terms,
                "conflicts_user": is_user_conflict
            })

    # Handling missing or ambiguous allergen information
    data_completeness = "Complete"
    if not has_declaration and not has_ingredients:
        data_completeness = "Unknown — Verification Required"
    elif not has_declaration:
        data_completeness = "Partial (No Formal Allergen Box, Ingredients Only)"

    return {
        "data_completeness": data_completeness,
        "allergen_status_unknown": not has_declaration and not has_ingredients,
        "detected_allergens": allergen_results,
        "user_conflicts": user_conflicts,
        "has_critical_conflict": len(user_conflicts) > 0,
        "disclaimer": "Allergen absence in text is NOT proof of safety. Always verify package markings for cross-contact notices."
    }

def analyze_additives(ingredients: str, additives_declared: str = ""):
    """
    Parses additive INS codes and attaches authoritative Codex/FSSAI context.
    """
    text = f"{ingredients or ''} {additives_declared or ''}"
    ins_matches = re.findall(r'INS\s*([0-9]+[a-zA-Z]?(?:\([iIvVxX]+\))?)', text, re.IGNORECASE)
    
    unique_ins = list(set([f"INS {m.strip()}" for m in ins_matches]))
    additives_found = []

    for ins in sorted(unique_ins):
        info = ADDITIVE_KNOWLEDGE_BASE.get(ins, {
            "name": f"Food Additive {ins}",
            "class": "Regulated Food Additive",
            "note": "Referenced in FSSAI Food Safety and Standards (Food Products Standards and Food Additives) Regulations."
        })
        additives_found.append({
            "code": ins,
            "name": info["name"],
            "functional_class": info["class"],
            "regulatory_context": info["note"],
            "authority": "FSSAI / Codex Alimentarius"
        })

    return {
        "total_additives_detected": len(additives_found),
        "additives_list": additives_found,
        "summary": f"{len(additives_found)} permitted additives detected with regulatory context."
    }
