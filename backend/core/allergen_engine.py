"""
EATGOOD — Allergen & Additive Assessment Engine (Layer 3)
Analyzes available ingredients, additives, and allergen declarations.
Distinguishes confirmed presence, warnings, potential matches, and unknown statuses.
Enforces hard safety exclusions without fabricating toxicology claims.
"""

import re
from typing import Any

# Allergen groups. "keywords" are matched as whole words/phrases in ingredients and
# declarations; "exclusions" are phrases removed first because they contain a keyword
# without containing the allergen (e.g. "coconut milk", "cocoa butter").
# fssai_mandate: listed in FSSAI Labelling & Display Regulations 2020, Schedule on allergens
# (cereals containing gluten, crustaceans, milk, eggs, fish, peanuts, tree nuts, soybeans, sulphites).
MAJOR_ALLERGENS: dict[str, dict[str, Any]] = {
    "Milk": {
        "keywords": [
            "milk", "milk solids", "milk powder", "skimmed milk", "milk fat", "dairy", "butter", "butter oil",
            "buttermilk", "cheese", "whey", "casein", "caseinate", "lactose", "curd", "paneer", "dahi",
            "cream", "ghee", "khoa", "khoya", "malai", "yoghurt", "yogurt",
        ],
        "exclusions": [
            "coconut milk", "almond milk", "soy milk", "soya milk", "oat milk", "rice milk", "cocoa butter",
            "peanut butter", "nut butter", "shea butter", "cream of tartar", "milk thistle", "coconut cream",
        ],
        "fssai_mandate": True,
    },
    "Soy": {
        "keywords": ["soy", "soya", "soybean", "soybeans", "soy lecithin", "soya lecithin", "edamame", "tofu"],
        "exclusions": [],
        "possible": ["lecithin", "ins 322", "e322"],
        "possible_exclusions": ["sunflower lecithin", "lecithin (sunflower)", "rapeseed lecithin"],
        "fssai_mandate": True,
    },
    "Gluten": {
        "keywords": [
            "gluten", "wheat", "maida", "atta", "barley", "malt", "malt extract", "rye", "semolina", "suji",
            "sooji", "rava", "dalia", "spelt", "seitan", "wheat flour",
        ],
        "exclusions": ["buckwheat", "gluten free", "gluten-free"],
        "fssai_mandate": True,
    },
    "Peanuts": {
        "keywords": ["peanut", "peanuts", "groundnut", "groundnuts", "monkey nut", "arachis", "moongphali", "mungfali"],
        "exclusions": [],
        "fssai_mandate": True,
    },
    "Tree Nuts": {
        "keywords": [
            "tree nut", "tree nuts", "almond", "almonds", "cashew", "cashews", "walnut", "walnuts", "pistachio",
            "pistachios", "hazelnut", "hazelnuts", "pecan", "pecans", "brazil nut", "macadamia", "pine nut",
            "badam", "kaju", "akhrot", "pista", "chironji",
        ],
        "exclusions": [],
        "fssai_mandate": True,
    },
    "Eggs": {
        "keywords": ["egg", "eggs", "egg powder", "albumin", "albumen", "egg yolk", "egg white", "lysozyme", "ovalbumin"],
        "exclusions": ["eggplant", "eggless"],
        "fssai_mandate": True,
    },
    "Fish": {
        "keywords": ["fish", "cod", "salmon", "tuna", "anchovy", "anchovies", "sardine", "fish sauce", "isinglass"],
        "exclusions": [],
        "fssai_mandate": True,
    },
    "Crustaceans": {
        "keywords": ["crustacean", "crustaceans", "shrimp", "shrimps", "prawn", "prawns", "crab", "lobster", "krill"],
        "exclusions": [],
        "fssai_mandate": True,
    },
    "Sesame": {
        "keywords": ["sesame", "til", "tahini", "gingelly"],
        "exclusions": [],
        "fssai_mandate": False,
    },
    "Sulphites": {
        "keywords": [
            "sulphite", "sulphites", "sulfite", "sulfites", "sulphur dioxide", "sulfur dioxide",
            "sodium metabisulphite", "potassium metabisulphite", "ins 220", "ins 221", "ins 222", "ins 223", "ins 224",
        ],
        "exclusions": [],
        "fssai_mandate": True,
    },
}

# Generic words on labels that point at more than one group. "May contain nuts" is treated
# as a warning for both peanuts and tree nuts, because the label does not say which.
GENERIC_TERMS = {"nut": ["Peanuts", "Tree Nuts"], "nuts": ["Peanuts", "Tree Nuts"]}

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
    "INS 338": {"name": "Phosphoric Acid", "class": "Acidity Regulator", "note": "Permitted acidulant commonly used in colas and beverages under FSSAI statutory limits."},
    "INS 407": {"name": "Carrageenan", "class": "Thickener & Stabilizer", "note": "Seaweed-derived polysaccharide gelling agent."},
    "INS 415": {"name": "Xanthan Gum", "class": "Thickener & Stabilizer", "note": "Fermentation-derived plant gum providing emulsion stability."},
    "INS 440": {"name": "Pectin", "class": "Gelling Agent", "note": "Naturally occurring fruit polysaccharide used in jams and confectionery."},
    "INS 412": {"name": "Guar Gum", "class": "Thickener & Stabilizer", "note": "Plant-derived hydrocolloid from guar beans."},
    "INS 471": {"name": "Mono- and Di-glycerides of Fatty Acids", "class": "Emulsifier", "note": "Standard food-grade lipid emulsifier."},
    "INS 500": {"name": "Sodium Carbonates", "class": "Acidity Regulator & Raising Agent", "note": "Mineral leavening agent permitted under FSSAI."},
    "INS 500(i)": {"name": "Sodium Carbonate", "class": "Raising Agent", "note": "Washing soda; mineral acidity regulator."},
    "INS 500(ii)": {"name": "Sodium Bicarbonate", "class": "Raising Agent", "note": "Baking soda; safe mineral leavening agent."},
    "INS 503(ii)": {"name": "Ammonium Bicarbonate", "class": "Raising Agent", "note": "Baker's ammonia; standard biscuit leavener."}
}

_MAY_CONTAIN_PATTERN = re.compile(
    r"(may\s+contain|may\s+also\s+contain|traces?\s+of|processed\s+in\s+a\s+facility|manufactured\s+in\s+a\s+facility|same\s+(?:facility|line))",
    re.IGNORECASE,
)
_EMPTY_DECLARATIONS = {"", "nan", "none", "none declared", "not declared", "n/a"}


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", text) is not None


def _strip_phrases(text: str, phrases: list) -> str:
    for phrase in phrases:
        text = re.sub(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", " ", text)
    return text


def _match(text: str, info: dict) -> str | None:
    cleaned = _strip_phrases(text, info["exclusions"])
    for kw in info["keywords"]:
        if _contains_phrase(cleaned, kw):
            return kw
    return None


def _match_possible(text: str, info: dict) -> str | None:
    cleaned = _strip_phrases(text, info.get("possible_exclusions", []))
    for kw in info.get("possible", []):
        if _contains_phrase(cleaned, kw):
            return kw
    return None


_SPECIFIC_NUT_PHRASES = ["tree nuts", "tree nut", "peanuts", "peanut", "groundnuts", "groundnut", "monkey nut",
                         "brazil nut", "pine nut", "nutmeg", "coconut"]


def _generic_groups(text: str) -> list[str]:
    """Groups implied by a bare 'nut'/'nuts' that is not part of a more specific name."""
    cleaned = _strip_phrases(text, _SPECIFIC_NUT_PHRASES)
    return [g for term, groups in GENERIC_TERMS.items() if _contains_phrase(cleaned, term) for g in groups]


def _split_declaration(declaration: str) -> tuple[str, str]:
    """Splits a declaration into (contains_text, may_contain_text)."""
    match = _MAY_CONTAIN_PATTERN.search(declaration)
    if not match:
        return declaration, ""
    return declaration[: match.start()], declaration[match.start():]


def canonical_user_allergens(user_allergens: list[str]) -> tuple[list[str], list[str]]:
    """Maps profile entries to allergen groups. Returns (known_groups, custom_terms)."""
    known: list[str] = []
    custom: list[str] = []
    for entry in user_allergens:
        term = entry.strip().lower()
        if not term or term == "none":
            continue
        group = next(
            (name for name, info in MAJOR_ALLERGENS.items() if term == name.lower() or term in info["keywords"]),
            None,
        )
        if group is not None:
            known.append(group)
        elif term in GENERIC_TERMS:
            known.extend(GENERIC_TERMS[term])
        else:
            custom.append(term)
    return sorted(set(known)), sorted(set(custom))


def analyze_allergens(ingredients: str, allergens_declared: str, user_allergens_to_avoid: list[str] | None = None):
    """
    Checks a product's allergen declaration and ingredients against the major allergen groups
    and the user's own list. Missing information is never treated as safe.

    Status levels, most to least certain:
      "Confirmed Allergen"                  named in the "contains" part of the declaration
      "Ingredient Match (Requires Review)"  an ingredient word belongs to the group
      "Advisory Warning (May Contain)"      named in a "may contain / traces of" statement
      "Possible Source (Check Label)"       an ingredient that is often, but not always, from the group
    Any of these counts as a conflict with the user's profile.
    """
    known_user, custom_user = canonical_user_allergens(user_allergens_to_avoid or [])

    ing_text = str(ingredients or "").lower()
    decl_text = str(allergens_declared or "").lower().strip()
    has_declaration = decl_text not in _EMPTY_DECLARATIONS
    has_ingredients = ing_text.strip() not in ("", "nan")
    contains_text, may_contain_text = _split_declaration(decl_text) if has_declaration else ("", "")

    generic_may = _generic_groups(may_contain_text)
    generic_contains = _generic_groups(contains_text)

    allergen_results = []
    user_conflicts = []

    for allergen, info in MAJOR_ALLERGENS.items():
        evidence = []
        status = None
        severity = "low"

        declared_kw = _match(contains_text, info) or (allergen.lower() if _contains_phrase(contains_text, allergen.lower()) else None)
        if declared_kw or allergen in generic_contains:
            status, severity = "Confirmed Allergen", "high"
            evidence.append(f"Declared on label ('{declared_kw or 'nuts'}')")
        ingredient_kw = _match(ing_text, info) if has_ingredients else None
        if ingredient_kw:
            evidence.append(f"Ingredient '{ingredient_kw}' belongs to this group")
            if status is None:
                status, severity = "Ingredient Match (Requires Review)", "medium"
        may_kw = _match(may_contain_text, info) or (allergen.lower() if _contains_phrase(may_contain_text, allergen.lower()) else None)
        if may_kw or allergen in generic_may:
            evidence.append(f"Label says it may contain '{may_kw or 'nuts'}'")
            if status is None:
                status, severity = "Advisory Warning (May Contain)", "medium"
        possible_kw = _match_possible(ing_text, info) if has_ingredients else None
        if possible_kw and status is None:
            status, severity = "Possible Source (Check Label)", "medium"
            evidence.append(f"'{possible_kw}' is often made from {allergen.lower()}; the label does not say which source")

        if status is None:
            continue
        conflicts_user = allergen in known_user
        if conflicts_user:
            user_conflicts.append({"allergen": allergen, "status": status, "evidence": evidence})
        allergen_results.append(
            {"allergen": allergen, "status": status, "severity": severity, "evidence": evidence, "conflicts_user": conflicts_user}
        )

    for term in custom_user:
        in_contains = _contains_phrase(contains_text, term)
        in_ingredients = has_ingredients and _contains_phrase(ing_text, term)
        in_may = _contains_phrase(may_contain_text, term)
        if not (in_contains or in_ingredients or in_may):
            continue
        status = (
            "Confirmed Allergen" if in_contains
            else "Ingredient Match (Requires Review)" if in_ingredients
            else "Advisory Warning (May Contain)"
        )
        evidence = [f"'{term}' appears in the {'declaration' if in_contains or in_may else 'ingredients'}"]
        user_conflicts.append({"allergen": term.title(), "status": status, "evidence": evidence})
        allergen_results.append(
            {"allergen": term.title(), "status": status, "severity": "high" if in_contains else "medium",
             "evidence": evidence, "conflicts_user": True}
        )

    if not has_declaration and not has_ingredients:
        data_completeness = "Unknown — Verification Required"
    elif not has_declaration:
        data_completeness = "Partial (No Formal Allergen Box, Ingredients Only)"
    else:
        data_completeness = "Complete"

    allergen_status_unknown = not has_declaration and not has_ingredients
    user_has_allergens = bool(known_user or custom_user)
    return {
        "data_completeness": data_completeness,
        "allergen_status_unknown": allergen_status_unknown,
        "user_allergen_check_incomplete": user_has_allergens and allergen_status_unknown,
        "detected_allergens": allergen_results,
        "user_conflicts": user_conflicts,
        "has_critical_conflict": len(user_conflicts) > 0,
        "disclaimer": "Not finding an allergen in the text is NOT proof the product is free of it. Always check the pack.",
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
