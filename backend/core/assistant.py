"""
EATGOOD — rule-based product Q&A.

Answers come only from the product's stated values, the category limits used for the grade
(standards_registry), the deterministic assessment and the visitor's profile. No language model
is involved and no value is invented: a missing value is reported as "not stated", never as 0.

Answers are returned as structured text, not Markdown: a short conclusion, optional details and
an optional disclaimer. Each is a list of parts, where {"value": ...} marks a number worth
highlighting and {"text": ...} is plain text. The client styles values; it never parses markup.
"""

import re
from typing import Any

import pandas as pd

from backend.core.allergen_engine import analyze_allergens
from backend.core.nutrition_scoring import run_full_product_assessment
from backend.core.standards_registry import get_category_spec

DISCLAIMER_MEDICAL = (
    "This is general information from the label, not clinical medical advice. "
    "If you manage a health condition, ask your doctor or dietitian how this food fits your plan."
)
DISCLAIMER_ALLERGEN = (
    "Not finding an allergen in the label text is not proof that it is absent. "
    "Always check the pack, including any 'may contain' warning."
)
WHO_DAILY_SODIUM_MG = 2000  # WHO guideline: less than 2,000 mg sodium a day for adults

Part = dict[str, str]

# Words in a question mapped to the allergen name the allergen engine understands.
ALLERGEN_WORDS = {
    "peanut": "Peanuts", "gluten": "Gluten", "celiac": "Gluten", "coeliac": "Gluten", "wheat": "Gluten",
    "dairy": "Milk", "lactose": "Milk", "milk": "Milk", "soy": "Soy", "soya": "Soy", "egg": "Egg",
    "tree nut": "Tree Nuts", "almond": "Tree Nuts", "cashew": "Tree Nuts", "sesame": "Sesame",
    "fish": "Fish", "shellfish": "Shellfish", "mustard": "Mustard",
}
DEFAULT_PROFILE = {"goal": "Balanced Choices", "dietary_preference": "No preference", "allergens_to_avoid": ""}


def _t(text: str) -> Part:
    return {"text": text}


def _v(text: str) -> Part:
    return {"value": text}


def _missing(value: Any) -> bool:
    return value is None or value == "" or (isinstance(value, float) and pd.isna(value))


def _num(product: dict[str, Any], key: str) -> float | None:
    """A stated nutrient value as a number, or None when the label does not state it."""
    value = product.get(key)
    if value is None or _missing(value):
        return None
    return float(value)


def _basis(product: dict[str, Any]) -> str | None:
    """'per 100 g', 'per 100 ml', 'per serving' or None when the label does not say."""
    b = str(product.get("measurement_basis") or "").lower().replace(" ", "")
    if "100ml" in b:
        return "per 100 ml"
    if "100g" in b:
        return "per 100 g"
    if "serving" in b:
        return "per serving"
    return None


def _amount(key: str, value: Any, basis: str | None) -> str:
    unit = "mg" if key.endswith("_mg") else ("kcal" if key == "energy_kcal" else "g")
    num = float(value)
    shown = f"{round(num):,}" if unit in ("mg", "kcal") else f"{round(num, 1):g}"
    return f"{shown} {unit}" + (f" {basis}" if basis else " (basis not stated)")


def _same_basis(spec: dict[str, Any] | None, product_basis: str | None) -> bool:
    """Category limits are set per 100 g or per 100 ml; they only apply to labels on that basis."""
    if not spec:
        return False
    reference = "per 100 ml" if "100ml" in spec["reference_basis"].replace(" ", "") else "per 100 g"
    return product_basis == reference


def _limit(spec: dict[str, Any] | None, product_basis: str | None, key: str) -> float | None:
    """The category limit for a nutrient, only when it applies to the same basis as the label."""
    if not spec or key not in spec.get("thresholds", {}) or not _same_basis(spec, product_basis):
        return None
    return spec["thresholds"][key]


def _plain(paragraph: list[Part]) -> str:
    return "".join(p.get("text") or p.get("value") or "" for p in paragraph)


def _nutrient_answer(
    product: dict[str, Any], spec: dict[str, Any] | None, key: str, label: str, cite_label: str
) -> tuple[list[Part], list[list[Part]], str]:
    """Conclusion and details for one nutrient against the category limit, if one applies."""
    basis = _basis(product)
    value = _num(product, key)
    name = product.get("product_name", "This product")
    if value is None:
        return [_t(f"The label does not state {label}, so we can't judge it.")], [], f"{cite_label}: not stated"
    amount = _amount(key, value, basis)
    citation = f"{cite_label}: {amount}"
    limit = _limit(spec, basis, key)
    if limit is None:
        reason = (
            "We have no limit for this category"
            if not spec or key not in spec.get("thresholds", {})
            else "The category limit is set per 100 g or 100 ml, and this label uses a different basis"
        )
        return [_t(f"{name} has "), _v(amount), _t(f" {label}.")], [[_t(f"{reason}, so it isn't rated as high or low.")]], citation
    limit_text = _amount(key, limit, basis)
    if value > limit:
        conclusion = [_t(f"This is high in {label} for its category: "), _v(amount), _t(".")]
    else:
        verb = "are" if label.endswith("s") else "is"
        conclusion = [_t(f"{label.capitalize()} {verb} within the limit for its category: "), _v(amount), _t(".")]
    details = [[_t(f"The limit we use for {product.get('category')} is "), _v(limit_text),
                _t(", the same limit used for the grade.")]]
    return conclusion, details, citation


def answer_product_question(
    product: dict[str, Any],
    question: str,
    user_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_q = question.strip().lower()
    profile = user_profile or DEFAULT_PROFILE
    assessment = run_full_product_assessment(product, profile)
    layer1 = assessment.get("layer1_general", {})
    layer2 = assessment.get("layer2_personalized", {})
    layer3 = assessment.get("layer3_allergens", {})

    p_name = product.get("product_name", "this product")
    brand = product.get("brand", "Unknown")
    cat = product.get("category", "General Food")
    spec = get_category_spec(cat)
    basis = _basis(product)
    goal = layer2.get("user_goal", profile.get("goal", "Balanced Choices"))
    grade = layer1.get("grade", "N/A")
    score = layer2.get("personalized_score")
    ings = product.get("ingredients")
    declared = product.get("allergens_declared")

    conclusion: list[Part] = []
    details: list[list[Part]] = []
    disclaimer: str | None = None
    citations: list[str] = []

    def stated(key: str, label: str) -> str:
        value = product.get(key)
        return f"{label}: {'not stated' if _missing(value) else _amount(key, value, basis)}"

    if any(w in clean_q for w in ["diabet", "sugar", "insulin", "glycemic", "glucose"]):
        conclusion, details, cite = _nutrient_answer(product, spec, "sugars_g", "total sugars", "Total Sugars")
        citations.append(cite)
        if not _missing(product.get("added_sugars_g")):
            details.append([_t("Added sugars: "), _v(_amount("added_sugars_g", product["added_sugars_g"], basis)), _t(".")])
        fibre = product.get("dietary_fibre_g")
        details.append([_t("Dietary fibre: "), _v(_amount("dietary_fibre_g", fibre, basis)), _t(".")] if not _missing(fibre)
                       else [_t("Dietary fibre is not stated on the label.")])
        citations.append(stated("dietary_fibre_g", "Dietary Fibre"))
        disclaimer = DISCLAIMER_MEDICAL

    elif re.search(r"blood pressure|hypertension|\bbp\b|salt|sodium", clean_q):
        conclusion, details, cite = _nutrient_answer(product, spec, "sodium_mg", "sodium", "Sodium")
        citations.append(cite)
        sodium = _num(product, "sodium_mg")
        if sodium is not None and basis in ("per 100 g", "per 100 ml"):
            share = round(sodium / WHO_DAILY_SODIUM_MG * 100)
            details.append([_t(f"{basis.removeprefix('per ').capitalize()} gives "), _v(f"{share}%"),
                            _t(f" of the WHO adult maximum of {WHO_DAILY_SODIUM_MG:,} mg sodium a day.")])
        disclaimer = DISCLAIMER_MEDICAL

    elif any(w in clean_q for w in ["allerg", *ALLERGEN_WORDS]):
        target = next((name for word, name in ALLERGEN_WORDS.items() if word in clean_q), None)
        citations.append(f"Declared allergens: {declared or 'not stated'}")
        citations.append(f"Ingredients: {(str(ings)[:100] + ('…' if len(str(ings)) > 100 else '')) if ings else 'not stated'}")
        profile_conflicts = [c.get("allergen", "") for c in layer3.get("user_conflicts", [])]
        if profile_conflicts:
            conclusion = [_t("Not suitable for your profile: the label lists "), _v(", ".join(profile_conflicts)), _t(".")]
        if target:
            check = analyze_allergens(str(ings or ""), str(declared or ""), [target])
            if check["user_conflicts"]:
                status = check["user_conflicts"][0]["status"]
                line = [_t(f"{target} appears on the label ({status.lower()}).")]
            elif check["allergen_status_unknown"]:
                line = [_t(f"The label gives no ingredients or allergen declaration, so we can't tell whether it contains {target.lower()}.")]
            else:
                line = [_t(f"{target} is not listed in the ingredients or the allergen declaration.")]
            if conclusion:
                details.append(line)
            else:
                conclusion = line
        elif not conclusion:
            allergens = str(profile.get("allergens_to_avoid") or "").strip()
            if layer3.get("allergen_status_unknown"):
                conclusion = [_t("The label gives no ingredients or allergen declaration, so we can't check it for allergens.")]
            elif allergens:
                conclusion = [_t("None of your allergens ("), _v(allergens), _t(") were found in the label text.")]
            else:
                conclusion = [_t("You haven't set any allergens in your profile. Add them there to have every product checked.")]
        details.append([_t("Declared allergens: "), _v(str(declared)), _t(".")] if declared
                       else [_t("The label has no allergen declaration.")])
        disclaimer = DISCLAIMER_ALLERGEN

    elif any(w in clean_q for w in ["why", "score", "grade", "rating", "how good", "bad", "healthy"]):
        citations += [f"General Grade: {grade}", f"Goal Match: {score if score is not None else 'N/A'}/100", f"Goal: {goal}"]
        conclusion = [_t("It has grade "), _v(str(grade)), _t(" and a Goal Match of "),
                      _v(f"{score}/100" if score is not None else "N/A"), _t(f" for your goal ({goal}).")]
        if grade == "N/A" and layer1.get("explanation"):
            details.append([_t(str(layer1["explanation"]))])
        for reason in (layer1.get("concerns") or [])[:2] + (layer1.get("strengths") or [])[:1]:
            details.append([_t(f"Grade: {reason}")])
        for rule in (layer2.get("rules_applied") or [])[:2]:
            details.append([_t(f"Goal Match: {rule}")])
        if layer2.get("has_critical_allergen_conflict"):
            details.append([_t("Goal Match is 0 because the product contains an allergen from your profile.")])
        disclaimer = "The grade compares the label with limits for its category; it is not a medical rating."

    elif any(w in clean_q for w in ["protein", "muscle", "workout", "gym", "bodybuilding"]):
        protein = _num(product, "protein_g")
        citations.append(stated("protein_g", "Protein"))
        if protein is None:
            conclusion = [_t("The label does not state protein, so we can't judge it.")]
        else:
            amount = _amount("protein_g", protein, basis)
            bench = (spec or {}).get("positive_benchmarks", {})
            same_basis = _same_basis(spec, basis)
            high, source = bench.get("protein_high_g"), bench.get("protein_source_g")
            if same_basis and high is not None and protein >= high:
                conclusion = [_t("It is high in protein: "), _v(amount), _t(".")]
                details.append([_t(f"That meets the {high:g} g level used for 'high protein' in this category.")])
            elif same_basis and source is not None and protein >= source:
                conclusion = [_t("It is a source of protein: "), _v(amount), _t(".")]
                details.append([_t(f"That meets the {source:g} g level used for 'source of protein' in this category.")])
            elif same_basis and source is not None:
                conclusion = [_t("It is not a source of protein: "), _v(amount), _t(".")]
                details.append([_t(f"That is below the {source:g} g level used for 'source of protein' in this category.")])
            else:
                conclusion = [_t(f"{p_name} has "), _v(amount), _t(" protein.")]

    else:
        conclusion = [_t(f"{p_name} by {brand} ({cat}) has grade "), _v(str(grade)), _t(" and a Goal Match of "),
                      _v(f"{score}/100" if score is not None else "N/A"), _t(f" for your goal ({goal}).")]
        for key, label in [("energy_kcal", "Energy"), ("sugars_g", "Total Sugars"), ("sodium_mg", "Sodium"), ("protein_g", "Protein")]:
            citations.append(stated(key, label))
        for key, label in [("sugars_g", "sugars"), ("sodium_mg", "sodium"), ("saturated_fat_g", "saturated fat")]:
            limit = _limit(spec, basis, key)
            value = _num(product, key)
            if limit is not None and value is not None and value > limit:
                details.append([_t(f"{label.capitalize()} is above the category limit: "), _v(_amount(key, value, basis)),
                                _t(f" (limit {_amount(key, limit, basis)}).")])
        details.append([_t("Ask about sugar, sodium, protein, allergens or the score for a specific answer.")])

    answer_text = "\n\n".join(_plain(p) for p in [conclusion, *details] if p)
    if disclaimer:
        answer_text += f"\n\n{disclaimer}"

    return {
        "product_id": product.get("product_id"),
        "product_name": p_name,
        "brand": brand,
        "question": question,
        "answer": answer_text,
        "conclusion": conclusion,
        "details": details,
        "disclaimer": disclaimer,
        "evidence_citations": citations,
        "grounded_metrics": {
            "energy_kcal": product.get("energy_kcal"),
            "sugars_g": product.get("sugars_g"),
            "sodium_mg": product.get("sodium_mg"),
            "protein_g": product.get("protein_g"),
            "dietary_fibre_g": product.get("dietary_fibre_g"),
            "general_grade": grade,
            "personalized_score": score if score is not None else 0,
        },
        "regulatory_benchmarks": {
            "standards_version": (spec or {}).get("standards_version", "No category limits"),
            "category": cat,
        },
    }
