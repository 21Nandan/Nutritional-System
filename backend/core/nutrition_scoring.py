"""
EATGOOD — Hybrid Food Grading Engine
Implements three decoupled, independent assessment layers:
- Layer 1: General Nutritional Assessment (Category-calibrated statutory standards: WHO SEARO / FSSAI INR)
- Layer 2: Personalized Suitability (User-profile goal & dietary preference tailored 1–100 scale)
- Layer 3: Hard Safety Exclusions (Allergen conflicts & food additive warnings)

Decoupling Guarantee:
- Layer 1 never depends on user goals.
- Layer 2 never modifies or replaces Layer 1 letter grades.
- Layer 3 safety overrides Layer 2 personalized suitability (score: 0) but cannot alter statutory nutrient grading.
- Missing critical data produce explicit refusal states ('Insufficient Data'), never silent zeroes.
"""

import re
from typing import Any

import pandas as pd

from backend.core.allergen_engine import analyze_additives, analyze_allergens
from backend.core.claims_detector import evaluate_claims
from backend.core.nutrition_validator import FIELD_FRIENDLY_NAMES, parse_float_safe, validate_and_normalize_nutrition
from backend.core.standards_registry import (
    get_applicable_standards,
    get_category_spec,
    normalize_category,
)


def format_reference_basis(basis: str | None) -> str:
    """Formats raw reference basis strings like 'per100g' or 'per 100g' into consumer-readable labels."""
    if not basis:
        return "Per 100 g"
    clean = str(basis).strip().lower()
    if "100ml" in clean or "100 ml" in clean:
        return "Per 100 ml"
    if "100g" in clean or "100 g" in clean:
        return "Per 100 g"
    if "serving" in clean:
        return "Per Serving"
    return str(basis).strip()


# Grade bands for the composite score (10–100): the minimum score for each grade.
GRADE_BANDS = (
    (80, "A", "Grade A — Optimal Nutritional Profile", "green"),
    (65, "B", "Grade B — Favourable Nutritional Balance", "teal"),
    (48, "C", "Grade C — Moderate / Consume in Moderation", "yellow"),
    (32, "D", "Grade D — Elevated Nutrients of Concern", "orange"),
    (10, "E", "Grade E — High in Sugar, Sodium, or Saturated Fat", "red"),
)


def grade_for_score(score: float) -> tuple[str, str, str]:
    """(grade, label, colour) for a composite score."""
    for minimum, grade, label, color in GRADE_BANDS:
        if score >= minimum:
            return grade, label, color
    _, grade, label, color = GRADE_BANDS[-1]
    return grade, label, color


def grade_unavailable_reason(layer1: dict[str, Any]) -> str | None:
    """One sentence saying why a product has no grade (None when it is graded), for lists and cards."""
    status = layer1.get("status")
    if status == "Calibrated":
        return None
    if status == "Insufficient Data":
        labels = [re.sub(r"\s*\(.*\)$", "", label) for label in layer1.get("missing_field_labels") or []]
        return f"Not graded: {', '.join(labels)} not stated on the label."
    if status == "Data Contradiction":
        concerns = layer1.get("concerns") or []
        return f"Not graded: {concerns[0]}" if concerns else "Not graded: label values contradict each other."
    category = layer1.get("category_calibrated")
    if category == "Alcoholic Drinks":
        return "Not graded: EATGOOD does not grade alcoholic drinks."
    if not category or category in ("Unspecified", "Uncategorised"):
        return "Not graded: the food category could not be identified, so no category limits apply."
    return f"Not graded: no validated grading method for {category} yet."


def assess_general_nutrition(product_data: dict[str, Any]) -> dict[str, Any]:
    """Layer 1 grade (see _assess_general_nutrition), with grade_reason saying why a product has no grade."""
    result = _assess_general_nutrition(product_data)
    result["grade_reason"] = grade_unavailable_reason(result)
    # The category actually used (unknown food types are graded as General Packaged Food).
    spec = get_category_spec(result.get("category_calibrated") or normalize_category(product_data.get("category", ""))) or {}
    own_method = spec.get("method_type") == "EATGOOD" and result["status"] == "Calibrated"
    # Grades from EATGOOD's own methods say so wherever they are shown.
    result["is_eatgood_method"] = own_method
    result["method_notice"] = spec.get("method_notice") if own_method else None
    result["grade_note"] = "EATGOOD's own method, not an official grade" if own_method else None
    return result


def _assess_general_nutrition(product_data: dict[str, Any]) -> dict[str, Any]:
    """
    Layer 1: General Nutritional Assessment
    Computes an evidence-based statutory nutrition grade for calibrated categories:
    - Biscuits & Bakery (WHO SEARO 2017 Cat 3 / FSSAI INR 2022 Solid Foods)
    - Snacks (WHO SEARO 2017 Cat 4 / FSSAI INR 2022 Solid Foods)
    - Breakfast Cereals (WHO SEARO 2017 Cat 1 / FSSAI INR 2022 Solid Foods)
    - Packaged Beverages (WHO SSB 2020 / FSSAI INR 2022 Liquid Foods)
    - Instant Foods (WHO SEARO 2017 Cat 6 / FSSAI INR 2022 Solid Foods)
    - Dairy (WHO SEARO 2017 Cat 2 / FSSAI INR 2022 Dairy Products)

    Refuses grading for uncalibrated/unsupported categories or when critical data are missing.
    """
    raw_category = product_data.get("category", "")
    canonical_category = normalize_category(raw_category)
    # A food whose type isn't one of the categories is graded with the general method.
    if canonical_category in ("", "Uncategorised", "Unspecified") or get_category_spec(canonical_category) is None:
        canonical_category = "General Packaged Food"
    spec = get_category_spec(canonical_category)

    # 1. Scope & Calibration Check
    if not spec or spec.get("status") != "Calibrated":
        if spec and spec.get("unsupported_reason"):
            unsupported_msg = spec["unsupported_reason"]
        elif not canonical_category or canonical_category == "Uncategorised":
            unsupported_msg = (
                "An overall grade is unavailable because the product's food category could not be identified "
                "from its record, so no category thresholds apply."
            )
        else:
            unsupported_msg = (
                f"An overall grade is unavailable because the {canonical_category} category has not yet been "
                "assessed using a suitable validated method."
            )
        return {
            "status": "Uncalibrated Category",
            "grade": "N/A",
            "grade_label": "Overall Grade Unavailable",
            "grade_status_badge": "Not yet rated",
            "general_nutrition_score": None,
            "methodology_name": None,
            "standards_version": spec.get("standards_version", "N/A") if spec else "N/A",
            "reference_basis": format_reference_basis(product_data.get("measurement_basis", "per 100g")),
            "category_calibrated": canonical_category or "Unspecified",
            "color": "gray",
            "explanation": unsupported_msg,
            "strengths": [],
            "concerns": [],
            "key_contributing_nutrients": {},
            "intermediate_calculations": [],
            "missing_fields": [],
            "validation_warnings": [],
            "standards_applied": []
        }

    # 2. Input Validation, Reference Basis Verification & Contradiction Detection
    mandatory_fields = spec.get("mandatory_fields", ["energy_kcal", "sugars_g", "saturated_fat_g", "sodium_mg"])
    target_basis = spec.get("reference_basis", "per 100g")

    validation = validate_and_normalize_nutrition(
        product_data,
        mandatory_fields=mandatory_fields,
        target_basis=target_basis
    )

    # Handle Severe Data Contradictions (e.g. Sugars > Carbs, Sat Fat > Total Fat). Checked before missing
    # values, so a negative value (removed by the validator) is reported as invalid, not as missing.
    if validation["contradictions"]:
        return {
            "status": "Data Contradiction",
            "grade": "Data Contradiction",
            "grade_label": "Overall Grade Unavailable — Data Contradiction",
            "grade_status_badge": "Conflicting Data",
            "general_nutrition_score": None,
            "methodology_name": spec["methodology_name"],
            "standards_version": spec["standards_version"],
            "reference_basis": format_reference_basis(target_basis),
            "category_calibrated": spec["canonical_name"],
            "color": "red",
            "explanation": f"An overall grade is unavailable due to conflicting packaging declarations: {'; '.join(validation['contradictions'])}.",
            "strengths": [],
            "concerns": validation["contradictions"],
            "key_contributing_nutrients": {},
            "intermediate_calculations": [],
            "missing_fields": [],
            "validation_warnings": validation["validation_warnings"],
            "standards_applied": []
        }

    # Handle Missing Critical Nutrients
    if validation["missing_mandatory_fields"]:
        missing_fields = validation["missing_mandatory_fields"]
        missing_labels = validation["missing_mandatory_labels"]
        return {
            "status": "Insufficient Data",
            "grade": "Insufficient Data",
            "grade_label": "Overall Grade Unavailable — Incomplete Data",
            "grade_status_badge": "Incomplete Data",
            "general_nutrition_score": None,
            "methodology_name": spec["methodology_name"],
            "standards_version": spec["standards_version"],
            "reference_basis": format_reference_basis(target_basis),
            "category_calibrated": spec["canonical_name"],
            "color": "gray",
            "explanation": f"An overall grade is unavailable because required nutrition declarations ({', '.join(missing_labels)}) are missing.",
            "strengths": [],
            "concerns": ["Incomplete nutritional panel — required baseline metrics omitted."],
            "key_contributing_nutrients": {},
            "intermediate_calculations": [],
            "missing_fields": missing_fields,
            "missing_field_labels": missing_labels,
            "validation_warnings": validation["validation_warnings"],
            "standards_applied": []
        }

    # 3. Retrieve Normalized Values
    nutr = validation["normalized_nutrition"]
    sugars = nutr.get("sugars_g", 0.0) or 0.0
    sat_fat = nutr.get("saturated_fat_g", 0.0) or 0.0
    # Sodium is not required for every category (Dairy). When it isn't declared it earns neither a
    # penalty nor a low-sodium bonus: a missing value is never read as zero.
    sodium_declared = nutr.get("sodium_mg") is not None
    sodium = nutr.get("sodium_mg", 0.0) or 0.0
    protein = nutr.get("protein_g", 0.0) or 0.0
    fibre = nutr.get("dietary_fibre_g", 0.0) or 0.0
    trans_fat = nutr.get("trans_fat_g", 0.0) or 0.0

    thresholds = spec.get("thresholds", {})
    sugar_thresh = thresholds.get("sugars_g", 10.0)
    sat_thresh = thresholds.get("saturated_fat_g", 4.0)
    sodium_thresh = thresholds.get("sodium_mg", 300.0)

    strengths: list[str] = []
    concerns: list[str] = []
    key_nutrients: dict[str, Any] = {}
    intermediate_calc: list[dict[str, Any]] = []

    penalty_points = 0
    bonus_points = 0

    # -------------------------------------------------------------
    # Step A: Total Sugars Evaluation (WHO SEARO Category Benchmarks)
    # -------------------------------------------------------------
    if target_basis == "per 100ml":
        if sugars > (sugar_thresh * 2.0):
            penalty_points += 4
            concerns.append(f"Very high sugar content ({sugars}g/100ml) — exceeds WHO beverage recommendation (>5g/100ml) by over 100%.")
            key_nutrients["sugars"] = {"value": sugars, "threshold": sugar_thresh, "unit": "g/100ml", "status": "Excessive (>2x threshold)", "points": -4}
            intermediate_calc.append({"nutrient": "Total Sugars", "value": f"{sugars}g", "rule": f"> 2x WHO threshold ({sugar_thresh*2}g)", "points": -4, "type": "penalty"})
        elif sugars > sugar_thresh:
            penalty_points += 2
            concerns.append(f"Exceeds WHO sugar threshold for packaged beverages ({sugars}g/100ml vs >{sugar_thresh}g standard).")
            key_nutrients["sugars"] = {"value": sugars, "threshold": sugar_thresh, "unit": "g/100ml", "status": "Elevated (>threshold)", "points": -2}
            intermediate_calc.append({"nutrient": "Total Sugars", "value": f"{sugars}g", "rule": f"> WHO threshold ({sugar_thresh}g)", "points": -2, "type": "penalty"})
        elif sugars <= 1.0:
            bonus_points += 4
            strengths.append(f"Virtually sugar-free beverage ({sugars}g/100ml).")
            key_nutrients["sugars"] = {"value": sugars, "threshold": sugar_thresh, "unit": "g/100ml", "status": "Optimal / Low", "points": +4}
            intermediate_calc.append({"nutrient": "Total Sugars", "value": f"{sugars}g", "rule": "<= 1.0g virtually sugar-free", "points": +4, "type": "bonus"})
        elif sugars <= 3.0:
            bonus_points += 2
            strengths.append(f"Low sugar beverage ({sugars}g/100ml).")
            key_nutrients["sugars"] = {"value": sugars, "threshold": sugar_thresh, "unit": "g/100ml", "status": "Favourable / Low", "points": +2}
            intermediate_calc.append({"nutrient": "Total Sugars", "value": f"{sugars}g", "rule": "<= 3.0g low sugar benchmark", "points": +2, "type": "bonus"})
        else:
            key_nutrients["sugars"] = {"value": sugars, "threshold": sugar_thresh, "unit": "g/100ml", "status": "Moderate", "points": 0}
            intermediate_calc.append({"nutrient": "Total Sugars", "value": f"{sugars}g", "rule": "Within standard limits", "points": 0, "type": "neutral"})
    else:
        # Solid foods (Biscuits, Snacks, Cereals, Instant, Dairy)
        if sugars > (sugar_thresh * 2.0):
            penalty_points += 4
            concerns.append(f"Excessive sugar ({sugars}g/100g) — exceeds category threshold ({sugar_thresh}g/100g) significantly.")
            key_nutrients["sugars"] = {"value": sugars, "threshold": sugar_thresh, "unit": "g/100g", "status": "Excessive (>2x threshold)", "points": -4}
            intermediate_calc.append({"nutrient": "Total Sugars", "value": f"{sugars}g", "rule": f"> 2x threshold ({sugar_thresh*2}g)", "points": -4, "type": "penalty"})
        elif sugars > sugar_thresh:
            penalty_points += 2
            concerns.append(f"High total sugar content ({sugars}g/100g) relative to regional nutrient guidelines ({sugar_thresh}g/100g).")
            key_nutrients["sugars"] = {"value": sugars, "threshold": sugar_thresh, "unit": "g/100g", "status": "Elevated (>threshold)", "points": -2}
            intermediate_calc.append({"nutrient": "Total Sugars", "value": f"{sugars}g", "rule": f"> threshold ({sugar_thresh}g)", "points": -2, "type": "penalty"})
        elif sugars <= 4.0:
            bonus_points += 1
            strengths.append(f"Low sugar content ({sugars}g/100g).")
            key_nutrients["sugars"] = {"value": sugars, "threshold": sugar_thresh, "unit": "g/100g", "status": "Optimal / Low", "points": +1}
            intermediate_calc.append({"nutrient": "Total Sugars", "value": f"{sugars}g", "rule": "<= 4.0g low sugar benchmark", "points": +1, "type": "bonus"})
        else:
            key_nutrients["sugars"] = {"value": sugars, "threshold": sugar_thresh, "unit": "g/100g", "status": "Moderate", "points": 0}
            intermediate_calc.append({"nutrient": "Total Sugars", "value": f"{sugars}g", "rule": "Within category threshold", "points": 0, "type": "neutral"})

    # -------------------------------------------------------------
    # Step B: Sodium Evaluation (WHO SEARO Benchmark)
    # -------------------------------------------------------------
    if not sodium_declared:
        key_nutrients["sodium"] = {"value": None, "threshold": sodium_thresh, "unit": "mg", "status": "Not declared", "points": 0}
        intermediate_calc.append({"nutrient": "Sodium", "value": "Not declared", "rule": "Not required for this category; no points", "points": 0, "type": "neutral"})
    elif sodium > (sodium_thresh * 2.0):
        penalty_points += 4
        concerns.append(f"Very high sodium ({sodium}mg) — exceeds standard ({sodium_thresh}mg) by more than double.")
        key_nutrients["sodium"] = {"value": sodium, "threshold": sodium_thresh, "unit": "mg", "status": "Excessive (>2x threshold)", "points": -4}
        intermediate_calc.append({"nutrient": "Sodium", "value": f"{sodium}mg", "rule": f"> 2x standard ({sodium_thresh*2}mg)", "points": -4, "type": "penalty"})
    elif sodium > sodium_thresh:
        penalty_points += 2
        concerns.append(f"Elevated sodium level ({sodium}mg) above WHO SEARO recommended benchmark ({sodium_thresh}mg).")
        key_nutrients["sodium"] = {"value": sodium, "threshold": sodium_thresh, "unit": "mg", "status": "Elevated (>threshold)", "points": -2}
        intermediate_calc.append({"nutrient": "Sodium", "value": f"{sodium}mg", "rule": f"> standard ({sodium_thresh}mg)", "points": -2, "type": "penalty"})
    elif sodium <= 120.0 and target_basis != "per 100ml":
        bonus_points += 1
        strengths.append(f"Low sodium ({sodium}mg/100g) supporting cardiovascular health guidelines.")
        key_nutrients["sodium"] = {"value": sodium, "threshold": sodium_thresh, "unit": "mg", "status": "Low / Heart Healthy", "points": +1}
        intermediate_calc.append({"nutrient": "Sodium", "value": f"{sodium}mg", "rule": "<= 120mg low sodium benchmark", "points": +1, "type": "bonus"})
    else:
        key_nutrients["sodium"] = {"value": sodium, "threshold": sodium_thresh, "unit": "mg", "status": "Moderate", "points": 0}
        intermediate_calc.append({"nutrient": "Sodium", "value": f"{sodium}mg", "rule": "Within standard limits", "points": 0, "type": "neutral"})

    # -------------------------------------------------------------
    # Step C: Saturated Fat Evaluation (WHO SEARO / FSSAI INR)
    # -------------------------------------------------------------
    if target_basis != "per 100ml":
        if sat_fat > (sat_thresh * 2.0):
            penalty_points += 3
            concerns.append(f"High saturated fat ({sat_fat}g/100g) — exceeds category threshold ({sat_thresh}g/100g) by over 100%.")
            key_nutrients["saturated_fat"] = {"value": sat_fat, "threshold": sat_thresh, "unit": "g/100g", "status": "Excessive (>2x threshold)", "points": -3}
            intermediate_calc.append({"nutrient": "Saturated Fat", "value": f"{sat_fat}g", "rule": f"> 2x threshold ({sat_thresh*2}g)", "points": -3, "type": "penalty"})
        elif sat_fat > sat_thresh:
            penalty_points += 1
            concerns.append(f"Elevated saturated fat ({sat_fat}g/100g) exceeding baseline guidance ({sat_thresh}g).")
            key_nutrients["saturated_fat"] = {"value": sat_fat, "threshold": sat_thresh, "unit": "g/100g", "status": "Elevated (>threshold)", "points": -1}
            intermediate_calc.append({"nutrient": "Saturated Fat", "value": f"{sat_fat}g", "rule": f"> threshold ({sat_thresh}g)", "points": -1, "type": "penalty"})
        elif sat_fat <= 1.5:
            bonus_points += 1
            strengths.append(f"Low saturated fat ({sat_fat}g/100g).")
            key_nutrients["saturated_fat"] = {"value": sat_fat, "threshold": sat_thresh, "unit": "g/100g", "status": "Low / Favourable", "points": +1}
            intermediate_calc.append({"nutrient": "Saturated Fat", "value": f"{sat_fat}g", "rule": "<= 1.5g low saturated fat benchmark", "points": +1, "type": "bonus"})
        else:
            key_nutrients["saturated_fat"] = {"value": sat_fat, "threshold": sat_thresh, "unit": "g/100g", "status": "Moderate", "points": 0}
            intermediate_calc.append({"nutrient": "Saturated Fat", "value": f"{sat_fat}g", "rule": "Within category threshold", "points": 0, "type": "neutral"})

    # -------------------------------------------------------------
    # Step D: Trans Fat Check (WHO REPLACE Action Package Target)
    # -------------------------------------------------------------
    if trans_fat > 0.1:
        penalty_points += 3
        concerns.append(f"Contains trans fatty acids ({trans_fat}g) — violates WHO REPLACE zero-trans-fat target.")
        key_nutrients["trans_fat"] = {"value": trans_fat, "threshold": 0.1, "unit": "g", "status": "Non-compliant (WHO REPLACE target: <0.2g)", "points": -3}
        intermediate_calc.append({"nutrient": "Trans Fat", "value": f"{trans_fat}g", "rule": "> 0.1g WHO REPLACE target", "points": -3, "type": "penalty"})
    elif nutr.get("trans_fat_g") is not None and trans_fat == 0.0:
        bonus_points += 1
        strengths.append("Zero industrial trans fats declared.")
        key_nutrients["trans_fat"] = {"value": 0.0, "threshold": 0.1, "unit": "g", "status": "Optimal (0g)", "points": +1}
        intermediate_calc.append({"nutrient": "Trans Fat", "value": "0g", "rule": "Zero trans fat declared", "points": +1, "type": "bonus"})

    # -------------------------------------------------------------
    # Step E: Positive Nutrients (Dietary Fibre & Protein Codex CAC/GL 23-1997)
    # -------------------------------------------------------------
    if fibre >= 6.0:
        bonus_points += 3
        strengths.append(f"High in dietary fibre ({fibre}g/100g) — meets Codex CAC/GL 23-1997 high-fibre standard.")
        key_nutrients["dietary_fibre"] = {"value": fibre, "threshold": 6.0, "unit": "g/100g", "status": "High Fibre (Codex Standard)", "points": +3}
        intermediate_calc.append({"nutrient": "Dietary Fibre", "value": f"{fibre}g", "rule": ">= 6.0g Codex High Fibre", "points": +3, "type": "bonus"})
    elif fibre >= 3.0:
        bonus_points += 1
        strengths.append(f"Source of dietary fibre ({fibre}g/100g).")
        key_nutrients["dietary_fibre"] = {"value": fibre, "threshold": 3.0, "unit": "g/100g", "status": "Source of Fibre", "points": +1}
        intermediate_calc.append({"nutrient": "Dietary Fibre", "value": f"{fibre}g", "rule": ">= 3.0g Codex Source of Fibre", "points": +1, "type": "bonus"})

    if protein >= 10.0:
        bonus_points += 2
        strengths.append(f"High protein content ({protein}g/100g) supporting daily amino acid requirements.")
        key_nutrients["protein"] = {"value": protein, "threshold": 10.0, "unit": "g/100g", "status": "High Protein (Codex Standard)", "points": +2}
        intermediate_calc.append({"nutrient": "Protein", "value": f"{protein}g", "rule": ">= 10.0g Codex High Protein", "points": +2, "type": "bonus"})
    elif protein >= 6.0:
        bonus_points += 1
        strengths.append(f"Good source of protein ({protein}g/100g).")
        key_nutrients["protein"] = {"value": protein, "threshold": 6.0, "unit": "g/100g", "status": "Source of Protein", "points": +1}
        intermediate_calc.append({"nutrient": "Protein", "value": f"{protein}g", "rule": ">= 6.0g Codex Source of Protein", "points": +1, "type": "bonus"})

    # -------------------------------------------------------------
    # Step F: Composite Score Calculation
    # Formula: net_score = max(10, min(100, 50 - (penalties * 7) + (bonuses * 8)))
    # -------------------------------------------------------------
    raw_score = 50 - (penalty_points * 7) + (bonus_points * 8)
    net_score = max(10, min(100, raw_score))

    intermediate_calc.append({
        "nutrient": "Net Composite Grade Calculation",
        "value": f"Base: 50 - ({penalty_points} penalties * 7) + ({bonus_points} bonuses * 8)",
        "rule": "Scored on a 10 to 100 scale",
        "points": raw_score,
        "type": "final"
    })

    grade, grade_label, color = grade_for_score(net_score)

    standards_applied = get_applicable_standards(canonical_category)

    return {
        "status": "Calibrated",
        "grade": grade,
        "grade_label": grade_label,
        "general_nutrition_score": net_score,
        "raw_score": raw_score,
        "penalty_points": penalty_points,
        "bonus_points": bonus_points,
        "color": color,
        "methodology_name": spec["methodology_name"],
        "standards_version": spec["standards_version"],
        "reference_basis": format_reference_basis(target_basis),
        "category_calibrated": spec["canonical_name"],
        "explanation": (
            f"Graded with {spec['methodology_name']}. {spec.get('method_notice', '')}".strip()
            if spec.get("method_type") == "EATGOOD"
            else f"Assessed against {len(standards_applied)} authoritative benchmarks under {spec['methodology_name']}."
        ),
        "strengths": strengths,
        "concerns": concerns,
        "key_contributing_nutrients": key_nutrients,
        "intermediate_calculations": intermediate_calc,
        "missing_fields": validation["missing_optional_fields"],
        "validation_warnings": validation["validation_warnings"],
        "standards_applied": [s["standard_name"] for s in standards_applied]
    }


def assess_personalized_suitability(product_data: dict[str, Any], user_profile: dict[str, Any]) -> dict[str, Any]:
    """
    Layer 2: Personalized Suitability Assessment
    Tailors the evaluation specifically to the active user's goals and preferences.
    Independent of Layer 1 general nutrition grade.
    """
    raw_goal = user_profile.get("goal", "Balanced Choices")
    if isinstance(raw_goal, list):
        goals = raw_goal
    else:
        goals = [g.strip() for g in str(raw_goal).split(",") if g.strip()]
    if not goals:
        goals = ["Balanced Choices"]
    primary_goal_str = ", ".join(goals)
    dietary_pref = user_profile.get("dietary_preference", "No preference")
    user_allergens = [a.strip() for a in user_profile.get("allergens_to_avoid", "").split(",") if a.strip()]

    # Run Layer 3 Allergen Check
    allergen_assessment = analyze_allergens(
        ingredients=product_data.get("ingredients", ""),
        allergens_declared=product_data.get("allergens_declared", ""),
        user_allergens_to_avoid=user_allergens
    )

    # Dietary preference check
    pref_conflict = False
    pref_reason = ""
    ings_lower = str(product_data.get("ingredients", "")).lower()
    cat = normalize_category(product_data.get("category", ""))

    if dietary_pref == "Vegetarian":
        if any(w in ings_lower for w in ["gelatin", "gelatine", "beef", "chicken", "meat", "pork", "fish oil", "carmine", "e120"]):
            pref_conflict = True
            pref_reason = "Contains animal-derived ingredients conflicting with Vegetarian preference."
    elif dietary_pref == "Vegan":
        if cat == "Dairy" or any(w in ings_lower for w in ["milk", "butter", "cheese", "whey", "casein", "lactose", "curd", "paneer", "honey", "egg", "gelatin"]):
            pref_conflict = True
            pref_reason = "Contains dairy, honey, or animal derivatives incompatible with Vegan diet."
    elif dietary_pref == "Lactose avoidance":
        if cat == "Dairy" or any(w in ings_lower for w in ["milk", "butter", "cheese", "whey", "casein", "lactose", "curd", "paneer", "dahi"]):
            pref_conflict = True
            pref_reason = "Contains lactose or milk solids incompatible with Lactose Avoidance."

    # 1. Hard Safety Exclusion: Critical Allergen Conflict
    if allergen_assessment["has_critical_conflict"]:
        allergen_names = ", ".join(c.get("allergen", "") for c in allergen_assessment.get("user_conflicts", []))
        return {
            "user_goal": primary_goal_str,
            "user_goals": goals,
            "dietary_preference": dietary_pref,
            "personalized_score": 0,
            "has_insufficient_data": False,
            "score_display": "0/100",
            "suitability_status": "Not Suitable — Critical Allergen Conflict",
            "suitability_badge": "Allergen Warning",
            "color": "red",
            "rules_applied": ["Safety Override: Critical Allergen Conflict Detected (Score: 0)"],
            "calculation_breakdown": {
                "scale_definition": {
                    "min": 1,
                    "min_label": "Unhealthy / Severe Profile Conflict",
                    "max": 100,
                    "max_label": "Healthiest / Optimal Profile Alignment",
                    "bands": [
                        {"range": "1 - 49", "label": "Unhealthy / Poor Match", "color": "#c62828"},
                        {"range": "50 - 74", "label": "Moderate Match", "color": "#00838f"},
                        {"range": "75 - 100", "label": "Healthiest / Optimal Match", "color": "#2e7d32"}
                    ]
                },
                "base_score": 70,
                "raw_score": 0,
                "final_score": 0,
                "steps": [
                    {
                        "step": 1,
                        "factor": "Baseline Starting Score",
                        "metric": "Standard 1–100 Scale Baseline",
                        "rule": "Neutral starting calibration",
                        "threshold_source": "EATGOOD Personalization Baseline Model",
                        "points": 70,
                        "points_str": "70",
                        "score_before": 0,
                        "score_after": 70,
                        "running_total": 70,
                        "type": "base"
                    },
                    {
                        "step": 2,
                        "factor": "Critical Allergen Conflict",
                        "metric": allergen_names or "Declared allergen",
                        "rule": "Absolute safety override: violates active profile allergen exclusion",
                        "threshold_source": "Layer 3 Allergen Safety Engine",
                        "points": -70,
                        "points_str": "Override (0)",
                        "score_before": 70,
                        "score_after": 0,
                        "running_total": 0,
                        "type": "override"
                    }
                ]
            },
            "goal_strengths": [],
            "goal_concerns": [
                f"Contains allergens strictly excluded in your profile ({allergen_names}). Consumption is not recommended."
            ],
            "allergen_conflicts": allergen_assessment["user_conflicts"],
            "has_critical_allergen_conflict": True,
            "allergen_check_incomplete": allergen_assessment["user_allergen_check_incomplete"],
            "preference_conflict": pref_conflict,
            "preference_reason": pref_reason
        }

    # 2. Incomplete / Missing Nutritional Data Verification
    critical_nutrients = ["energy_kcal", "sugars_g", "sodium_mg", "saturated_fat_g"]
    missing_critical = [
        f for f in critical_nutrients
        if pd.isna(product_data.get(f)) or product_data.get(f) is None or str(product_data.get(f)).strip() == ""
    ]

    # Incomplete if sugars and sodium are both missing, or 2 or more critical fields are omitted
    has_insufficient_data = (
        len(missing_critical) >= 2 or
        (
            (pd.isna(product_data.get("sugars_g")) or str(product_data.get("sugars_g")).strip() == "") and
            (pd.isna(product_data.get("sodium_mg")) or str(product_data.get("sodium_mg")).strip() == "")
        )
    )

    if has_insufficient_data:
        missing_labels = [FIELD_FRIENDLY_NAMES.get(f, f) for f in missing_critical]
        return {
            "user_goal": primary_goal_str,
            "user_goals": goals,
            "dietary_preference": dietary_pref,
            "personalized_score": None,
            "has_insufficient_data": True,
            "score_display": "N/A",
            "suitability_status": "Insufficient Data to Calculate Personalized Score",
            "suitability_badge": "Incomplete Data",
            "color": "gray",
            "rules_applied": [],
            "calculation_breakdown": None,
            "goal_strengths": [],
            "goal_concerns": [
                f"Missing critical nutritional declarations: {', '.join(missing_labels)}. Please enter these values to compute an accurate 1–100 score."
            ],
            "allergen_conflicts": allergen_assessment["user_conflicts"],
            "has_critical_allergen_conflict": False,
            "allergen_check_incomplete": allergen_assessment["user_allergen_check_incomplete"],
            "preference_conflict": pref_conflict,
            "preference_reason": pref_reason
        }

    if cat == "Alcoholic Drinks":
        return {
            "user_goal": primary_goal_str,
            "user_goals": goals,
            "dietary_preference": dietary_pref,
            "personalized_score": None,
            "has_insufficient_data": False,
            "score_display": "N/A",
            "suitability_status": "Not scored: EATGOOD does not score alcoholic drinks",
            "suitability_badge": "Alcoholic drink",
            "color": "gray",
            "rules_applied": [],
            "calculation_breakdown": None,
            "goal_strengths": [],
            "goal_concerns": ["EATGOOD does not score alcoholic drinks for any goal."],
            "allergen_conflicts": allergen_assessment["user_conflicts"],
            "has_critical_allergen_conflict": False,
            "allergen_check_incomplete": allergen_assessment["user_allergen_check_incomplete"],
            "preference_conflict": pref_conflict,
            "preference_reason": pref_reason
        }

    # 3. Transparent Multi-Factor Personalized Scoring (1 - 100 Scale)
    base_score = 70.0
    score = base_score
    steps = [
        {
            "step": 1,
            "factor": "Baseline Profile Neutral Score",
            "metric": "Standard 1–100 Scale Baseline",
            "rule": "Neutral starting calibration for verified nutrient declarations",
            "threshold_source": "EATGOOD Personalization Model",
            "points": 70,
            "points_str": "70",
            "score_before": 0,
            "score_after": 70,
            "running_total": 70,
            "type": "base"
        }
    ]
    step_num = 2

    rules_applied = []
    goal_strengths = []
    goal_concerns = []

    sugars = parse_float_safe(product_data.get("sugars_g"))
    sodium = parse_float_safe(product_data.get("sodium_mg"))
    protein = parse_float_safe(product_data.get("protein_g"))
    fibre = parse_float_safe(product_data.get("dietary_fibre_g"))
    sat_fat = parse_float_safe(product_data.get("saturated_fat_g"))
    trans_fat = parse_float_safe(product_data.get("trans_fat_g"))

    weight = 1.0 if len(goals) == 1 else (0.85 if len(goals) == 2 else 0.7)

    # Goal: Reduce Sugar
    if "Reduce Sugar" in goals:
        if sugars is not None:
            score_before = int(round(score))
            if sugars <= 3.0:
                pts = round(20 * weight)
                score += pts
                goal_strengths.append(f"Very low sugar ({sugars}g/100g) strongly benefits your 'Reduce Sugar' target.")
                rules_applied.append(f"Goal Reward: Total sugars <= 3g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sugar",
                    "metric": f"{sugars}g sugars / 100g",
                    "rule": "Low sugar benchmark (<= 3.0g)",
                    "threshold_source": "EATGOOD dietary goal (Reduce Sugar)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sugars <= 7.0:
                pts = round(10 * weight)
                score += pts
                goal_strengths.append(f"Moderate sugar ({sugars}g/100g) fits within sugar management targets.")
                rules_applied.append(f"Goal Reward: Total sugars 3g-7g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sugar",
                    "metric": f"{sugars}g sugars / 100g",
                    "rule": "Moderate sugar benchmark (3.0g - 7.0g)",
                    "threshold_source": "EATGOOD dietary goal (Reduce Sugar)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sugars > 20.0:
                pts = -round(30 * weight)
                score += pts
                goal_concerns.append(f"High sugar level ({sugars}g/100g) significantly impedes your 'Reduce Sugar' goal.")
                rules_applied.append(f"Goal Penalty: High sugar > 20g ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sugar",
                    "metric": f"{sugars}g sugars / 100g",
                    "rule": "Excessive sugar threshold (> 20.0g)",
                    "threshold_source": "EATGOOD dietary goal (Reduce Sugar)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1
            elif sugars > 10.0:
                pts = -round(18 * weight)
                score += pts
                goal_concerns.append(f"Sugar content ({sugars}g/100g) exceeds baseline threshold.")
                rules_applied.append(f"Goal Penalty: Elevated sugar 10g-20g ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sugar",
                    "metric": f"{sugars}g sugars / 100g",
                    "rule": "Elevated sugar threshold (> 10.0g)",
                    "threshold_source": "EATGOOD dietary goal (Reduce Sugar)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

    # Goal: Reduce Sodium
    if "Reduce Sodium" in goals:
        if sodium is not None:
            score_before = int(round(score))
            if sodium <= 140.0:
                pts = round(20 * weight)
                score += pts
                goal_strengths.append(f"Very low sodium ({sodium}mg/100g) aligns with hypertension and sodium reduction targets.")
                rules_applied.append(f"Goal Reward: Low sodium <= 140mg (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sodium",
                    "metric": f"{sodium}mg sodium / 100g",
                    "rule": "Low sodium benchmark (<= 140mg)",
                    "threshold_source": "US FDA / Codex Low Sodium Benchmark",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sodium <= 350.0:
                pts = round(10 * weight)
                score += pts
                goal_strengths.append(f"Moderate sodium ({sodium}mg/100g) fits daily allowance.")
                rules_applied.append(f"Goal Reward: Sodium 140mg-350mg (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sodium",
                    "metric": f"{sodium}mg sodium / 100g",
                    "rule": "Moderate sodium benchmark (140mg - 350mg)",
                    "threshold_source": "EATGOOD dietary goal (Reduce Sodium)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sodium > 900.0:
                pts = -round(30 * weight)
                score += pts
                goal_concerns.append(f"Extremely high sodium ({sodium}mg/100g) conflicts with 'Reduce Sodium' goal.")
                rules_applied.append(f"Goal Penalty: High sodium > 900mg ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sodium",
                    "metric": f"{sodium}mg sodium / 100g",
                    "rule": "Excessive sodium threshold (> 900mg)",
                    "threshold_source": "EATGOOD dietary goal (Reduce Sodium)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1
            elif sodium > 400.0:
                pts = -round(18 * weight)
                score += pts
                goal_concerns.append(f"Elevated sodium ({sodium}mg/100g) exceeds recommended boundary.")
                rules_applied.append(f"Goal Penalty: Elevated sodium 400mg-900mg ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sodium",
                    "metric": f"{sodium}mg sodium / 100g",
                    "rule": "Elevated sodium threshold (> 400mg)",
                    "threshold_source": "WHO SEARO Benchmark (400mg)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

    # Goal: Increase Fibre
    if "Increase Fibre" in goals:
        if fibre is not None:
            score_before = int(round(score))
            if fibre >= 6.0:
                pts = round(25 * weight)
                score += pts
                goal_strengths.append(f"Excellent source of fibre ({fibre}g/100g) directly fulfills your goal.")
                rules_applied.append(f"Goal Reward: High fibre >= 6g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Fibre",
                    "metric": f"{fibre}g fibre / 100g",
                    "rule": "Codex high-fibre standard (>= 6.0g)",
                    "threshold_source": "Codex CAC/GL 23-1997",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif fibre >= 3.0:
                pts = round(12 * weight)
                score += pts
                goal_strengths.append(f"Provides good dietary fibre ({fibre}g/100g).")
                rules_applied.append(f"Goal Reward: Moderate fibre >= 3g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Fibre",
                    "metric": f"{fibre}g fibre / 100g",
                    "rule": "Good source of fibre (>= 3.0g)",
                    "threshold_source": "Codex CAC/GL 23-1997",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif fibre < 2.0:
                pts = -round(12 * weight)
                score += pts
                goal_concerns.append(f"Low dietary fibre ({fibre}g/100g) relative to your increase-fibre goal.")
                rules_applied.append(f"Goal Adjustment: Low fibre < 2g ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Fibre",
                    "metric": f"{fibre}g fibre / 100g",
                    "rule": "Low fibre relative to target (< 2.0g)",
                    "threshold_source": "EATGOOD dietary goal (Increase Fibre)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

    # Goal: Increase Protein
    if "Increase Protein" in goals:
        if protein is not None:
            score_before = int(round(score))
            if protein >= 12.0:
                pts = round(25 * weight)
                score += pts
                goal_strengths.append(f"High protein concentration ({protein}g/100g) supports daily requirements.")
                rules_applied.append(f"Goal Reward: High protein >= 12g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Protein",
                    "metric": f"{protein}g protein / 100g",
                    "rule": "High protein standard (>= 12.0g)",
                    "threshold_source": "Codex CAC/GL 23-1997",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif protein >= 7.0:
                pts = round(12 * weight)
                score += pts
                goal_strengths.append(f"Good protein contribution ({protein}g/100g).")
                rules_applied.append(f"Goal Reward: Moderate protein 7g-12g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Protein",
                    "metric": f"{protein}g protein / 100g",
                    "rule": "Good source of protein (7.0g - 12.0g)",
                    "threshold_source": "Codex CAC/GL 23-1997",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif protein < 4.0:
                pts = -round(12 * weight)
                score += pts
                goal_concerns.append(f"Low protein contribution ({protein}g/100g).")
                rules_applied.append(f"Goal Adjustment: Low protein < 4g ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Protein",
                    "metric": f"{protein}g protein / 100g",
                    "rule": "Low protein relative to target (< 4.0g)",
                    "threshold_source": "EATGOOD dietary goal (Increase Protein)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

    # Goal: Balanced Choices
    if "Balanced Choices" in goals or len(goals) == 0:
        if sugars is not None:
            score_before = int(round(score))
            if sugars <= 5.0:
                pts = round(10 * weight)
                score += pts
                rules_applied.append(f"Balanced Factor: Modest sugar <= 5g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Balanced Lifestyle",
                    "metric": f"{sugars}g sugars / 100g",
                    "rule": "Modest sugar benchmark (<= 5.0g)",
                    "threshold_source": "WHO Daily Free Sugar Guidance",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sugars > 15.0:
                pts = -round(15 * weight)
                score += pts
                rules_applied.append(f"Balanced Factor: High sugar > 15g ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Balanced Lifestyle",
                    "metric": f"{sugars}g sugars / 100g",
                    "rule": "Elevated sugar threshold (> 15.0g)",
                    "threshold_source": "FSSAI Draft INR High Sugar Boundary",
                    "points": pts,
                    "points_str": f"{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

        if sodium is not None:
            score_before = int(round(score))
            if sodium <= 300.0:
                pts = round(10 * weight)
                score += pts
                rules_applied.append(f"Balanced Factor: Controlled sodium <= 300mg (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Balanced Lifestyle",
                    "metric": f"{sodium}mg sodium / 100g",
                    "rule": "Controlled sodium benchmark (<= 300mg)",
                    "threshold_source": "WHO SEARO Recommended Benchmark",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sodium > 600.0:
                pts = -round(15 * weight)
                score += pts
                rules_applied.append(f"Balanced Factor: High sodium > 600mg ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Balanced Lifestyle",
                    "metric": f"{sodium}mg sodium / 100g",
                    "rule": "Elevated sodium threshold (> 600mg)",
                    "threshold_source": "EATGOOD Balanced Lifestyle Benchmark",
                    "points": pts,
                    "points_str": f"{pts}",
                    "score_before": score_before,
                    "score_after": int(round(score)),
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

        if protein is not None and protein >= 6.0:
            score_before = int(round(score))
            pts = round(8 * weight)
            score += pts
            rules_applied.append(f"Balanced Factor: Solid protein >= 6g (+{pts} pts)")
            steps.append({
                "step": step_num,
                "factor": "Balanced Lifestyle",
                "metric": f"{protein}g protein / 100g",
                "rule": "Solid protein contribution (>= 6.0g)",
                "threshold_source": "Codex Source of Protein Benchmark",
                "points": pts,
                "points_str": f"+{pts}",
                "score_before": score_before,
                "score_after": int(round(score)),
                "running_total": int(round(score)),
                "type": "bonus"
            })
            step_num += 1

        if fibre is not None and fibre >= 3.0:
            score_before = int(round(score))
            pts = round(8 * weight)
            score += pts
            rules_applied.append(f"Balanced Factor: Meaningful fibre >= 3g (+{pts} pts)")
            steps.append({
                "step": step_num,
                "factor": "Balanced Lifestyle",
                "metric": f"{fibre}g fibre / 100g",
                "rule": "Meaningful dietary fibre (>= 3.0g)",
                "threshold_source": "Codex Source of Fibre Benchmark",
                "points": pts,
                "points_str": f"+{pts}",
                "score_before": score_before,
                "score_after": int(round(score)),
                "running_total": int(round(score)),
                "type": "bonus"
            })
            step_num += 1

    # Baseline Health Factor: Saturated Fat
    if sat_fat is not None:
        score_before = int(round(score))
        if sat_fat > 8.0:
            pts = -15
            score += pts
            rules_applied.append(f"Heart Health: High saturated fat > 8g ({pts} pts)")
            goal_concerns.append(f"High saturated fat ({sat_fat}g/100g) raises cardiovascular risk.")
            steps.append({
                "step": step_num,
                "factor": "Heart Health Factor",
                "metric": f"{sat_fat}g sat fat / 100g",
                "rule": "High saturated fat benchmark (> 8.0g)",
                "threshold_source": "AHA / WHO Saturated Fat Upper Limit",
                "points": pts,
                "points_str": f"{pts}",
                "score_before": score_before,
                "score_after": int(round(score)),
                "running_total": int(round(score)),
                "type": "penalty"
            })
            step_num += 1
        elif sat_fat > 4.5:
            pts = -8
            score += pts
            rules_applied.append(f"Heart Health: Elevated saturated fat > 4.5g ({pts} pts)")
            steps.append({
                "step": step_num,
                "factor": "Heart Health Factor",
                "metric": f"{sat_fat}g sat fat / 100g",
                "rule": "Elevated saturated fat (> 4.5g)",
                "threshold_source": "WHO SEARO Sat Fat Baseline (4.0g)",
                "points": pts,
                "points_str": f"{pts}",
                "score_before": score_before,
                "score_after": int(round(score)),
                "running_total": int(round(score)),
                "type": "penalty"
            })
            step_num += 1
        elif sat_fat <= 1.5:
            pts = 5
            score += pts
            rules_applied.append(f"Heart Health: Low saturated fat <= 1.5g (+{pts} pts)")
            goal_strengths.append(f"Low saturated fat ({sat_fat}g/100g).")
            steps.append({
                "step": step_num,
                "factor": "Heart Health Factor",
                "metric": f"{sat_fat}g sat fat / 100g",
                "rule": "Low saturated fat benchmark (<= 1.5g)",
                "threshold_source": "Codex Low Saturated Fat Benchmark",
                "points": pts,
                "points_str": f"+{pts}",
                "score_before": score_before,
                "score_after": int(round(score)),
                "running_total": int(round(score)),
                "type": "bonus"
            })
            step_num += 1

    # Baseline Health Factor: Trans Fat
    if trans_fat is not None and trans_fat > 0.1:
        score_before = int(round(score))
        pts = -20
        score += pts
        rules_applied.append(f"Safety Standard: Contains industrial trans fat ({pts} pts)")
        goal_concerns.append(f"Contains industrial trans fats ({trans_fat}g).")
        steps.append({
            "step": step_num,
            "factor": "WHO REPLACE Standard",
            "metric": f"{trans_fat}g trans fat",
            "rule": "Zero-trans-fat target violation (> 0.1g)",
            "threshold_source": "WHO REPLACE Trans Fat Action Package",
            "points": pts,
            "points_str": f"{pts}",
            "score_before": score_before,
            "score_after": int(round(score)),
            "running_total": int(round(score)),
            "type": "penalty"
        })
        step_num += 1

    # Dietary Preference Restriction
    if pref_conflict:
        score_before = int(round(score))
        score = min(15.0, score)
        steps.append({
            "step": step_num,
            "factor": "Dietary Preference Conflict",
            "metric": dietary_pref,
            "rule": pref_reason,
            "threshold_source": "User Dietary Preference Exclusion",
            "points": "Cap at 15",
            "points_str": "Cap at 15",
            "score_before": score_before,
            "score_after": int(round(score)),
            "running_total": int(round(score)),
            "type": "override"
        })
        step_num += 1

    # Final 1 to 100 Score Clamping (1 = unhealthiest/worst match, 100 = healthiest/ideal match)
    raw_score = int(round(score))
    final_score = max(1, min(100, raw_score))

    steps.append({
        "step": step_num,
        "factor": "Final 1–100 Scale Calibration",
        "metric": f"Raw computation: {raw_score}",
        "rule": "Calibrated between 1 (unhealthy / severe conflict) and 100 (healthiest match)",
        "threshold_source": "EATGOOD Standard Scale Definition",
        "points": "=",
        "points_str": "=",
        "score_before": raw_score,
        "score_after": final_score,
        "running_total": final_score,
        "type": "final"
    })

    if pref_conflict:
        suitability_status = f"Not Recommended — {pref_reason}"
        suitability_badge = "Preference Conflict"
        color = "orange"
    elif final_score >= 75:
        suitability_status = f"Highly Suitable for your target: {primary_goal_str}"
        suitability_badge = "Healthiest / Optimal Match"
        color = "green"
    elif final_score >= 50:
        suitability_status = f"Moderately Suitable for target: {primary_goal_str}"
        suitability_badge = "Moderate Match"
        color = "teal"
    else:
        suitability_status = f"Suboptimal alignment with target: {primary_goal_str}"
        suitability_badge = "Unhealthy / Poor Match"
        color = "orange" if final_score >= 30 else "red"

    return {
        "user_goal": primary_goal_str,
        "user_goals": goals,
        "dietary_preference": dietary_pref,
        "personalized_score": final_score,
        "has_insufficient_data": False,
        "score_display": f"{final_score}/100",
        "suitability_status": suitability_status,
        "suitability_badge": suitability_badge,
        "color": color,
        "rules_applied": rules_applied,
        "calculation_breakdown": {
            "scale_definition": {
                "min": 1,
                "min_label": "Unhealthy / Severe Profile Conflict",
                "max": 100,
                "max_label": "Healthiest / Optimal Profile Alignment",
                "bands": [
                    {"range": "1 - 49", "label": "Unhealthy / Poor Match", "color": "#c62828"},
                    {"range": "50 - 74", "label": "Moderate Match", "color": "#00838f"},
                    {"range": "75 - 100", "label": "Healthiest / Optimal Match", "color": "#2e7d32"}
                ]
            },
            "base_score": 70,
            "raw_score": raw_score,
            "final_score": final_score,
            "steps": steps
        },
        "goal_strengths": goal_strengths,
        "goal_concerns": goal_concerns,
        "allergen_conflicts": allergen_assessment["user_conflicts"],
        "has_critical_allergen_conflict": False,
        "allergen_check_incomplete": allergen_assessment["user_allergen_check_incomplete"],
        "preference_conflict": pref_conflict,
        "preference_reason": pref_reason
    }


def run_full_product_assessment(product_data: dict[str, Any], user_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Executes the complete 3-layer food assessment pipeline for a product.
    Independent Layers:
    - Layer 1: Statutory / Category Nutrition Grade (WHO SEARO / FSSAI INR)
    - Layer 2: Personalized Suitability Score (User profile goals & diet)
    - Layer 3: Hard Safety Exclusions & Allergen Warnings
    """
    if user_profile is None:
        user_profile = {
            "goal": "Balanced Choices",
            "dietary_preference": "No preference",
            "allergens_to_avoid": ""
        }

    layer1 = assess_general_nutrition(product_data)
    layer2 = assess_personalized_suitability(product_data, user_profile)
    layer3_allergens = analyze_allergens(
        ingredients=product_data.get("ingredients", ""),
        allergens_declared=product_data.get("allergens_declared", ""),
        user_allergens_to_avoid=[a.strip() for a in user_profile.get("allergens_to_avoid", "").split(",") if a.strip()]
    )
    layer3_additives = analyze_additives(
        ingredients=product_data.get("ingredients", ""),
        additives_declared=product_data.get("additives", "")
    )
    marketing_eval = evaluate_claims(
        marketing_claims=product_data.get("marketing_claims", ""),
        product_data=product_data
    )

    return {
        "product_id": product_data.get("product_id"),
        "product_name": product_data.get("product_name"),
        "brand": product_data.get("brand"),
        "category": product_data.get("category"),
        "sub_category": product_data.get("sub_category"),
        "barcode": product_data.get("barcode"),
        "image_url": product_data.get("image_url"),
        "image_small_url": product_data.get("image_small_url"),
        "image_ingredients_url": product_data.get("image_ingredients_url"),
        "image_nutrition_url": product_data.get("image_nutrition_url"),
        "marketing_claims": product_data.get("marketing_claims") or "",
        "quantity": product_data.get("quantity"),
        "serving_size": product_data.get("serving_size"),
        "serving_size_unit": product_data.get("serving_size_unit"),
        "measurement_basis": product_data.get("measurement_basis"),
        "data_confidence_status": product_data.get("data_confidence_status", "Unknown"),
        "data_source": product_data.get("data_source", "Unknown"),
        "openfoodfacts_attribution": product_data.get("openfoodfacts_attribution"),
        "source_indicators": product_data.get("source_indicators"),
        "retrieved_at": product_data.get("retrieved_at"),
        "nutrition_facts": {
            "energy_kcal": product_data.get("energy_kcal"),
            "carbohydrates_g": product_data.get("carbohydrates_g"),
            "sugars_g": product_data.get("sugars_g"),
            "added_sugars_g": product_data.get("added_sugars_g"),
            "protein_g": product_data.get("protein_g"),
            "total_fat_g": product_data.get("total_fat_g"),
            "saturated_fat_g": product_data.get("saturated_fat_g"),
            "trans_fat_g": product_data.get("trans_fat_g"),
            "cholesterol_mg": product_data.get("cholesterol_mg"),
            "sodium_mg": product_data.get("sodium_mg"),
            "dietary_fibre_g": product_data.get("dietary_fibre_g"),
        },
        "ingredients": product_data.get("ingredients"),
        # Safety first: when the product conflicts with the user's allergens, this flag tells every
        # screen to show the allergen warning instead of (and above) any grade or score.
        "safety_override": {
            "allergen_conflict": layer2["has_critical_allergen_conflict"],
            "allergens": [c["allergen"] for c in layer2["allergen_conflicts"]],
            "allergen_check_incomplete": layer2["allergen_check_incomplete"],
        },
        "layer1_general": layer1,
        "layer2_personalized": layer2,
        "layer3_allergens": layer3_allergens,
        "layer3_additives": layer3_additives,
        "marketing_claims_analysis": marketing_eval,
        "transparency": {
            "data_source": product_data.get("data_source", "Unknown"),
            "methodology_name": layer1.get("methodology_name"),
            "standards_version": layer1.get("standards_version"),
            "standards_applied": layer1.get("standards_applied", []),
            "reference_basis": layer1.get("reference_basis"),
            "validation_warnings": layer1.get("validation_warnings", []),
            "assessment_disclaimer": (
                "EATGOOD provides educational nutritional and food-safety assessments based on available product packaging data. "
                "It does not replace personalized clinical dietetics or medical advice."
            )
        }
    }
