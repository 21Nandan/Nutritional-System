"""
EATGOOD — Nutrition Input Validator & Basis Normalizer
Performs rigorous pre-scoring verification:
- Reference basis verification (per 100g, per 100ml, per serving normalization)
- Data type and boundary validation (no negative numbers, NaN checks)
- Physical plausibility and thermodynamic consistency cross-checks
- Explicit missing data tracking (never silently zeroes omitted values)
- Separation of raw provenance and normalized calculation values
"""

import math
from typing import Any

NUTRIENT_FIELDS = [
    "energy_kcal",
    "carbohydrates_g",
    "sugars_g",
    "added_sugars_g",
    "protein_g",
    "total_fat_g",
    "saturated_fat_g",
    "trans_fat_g",
    "cholesterol_mg",
    "sodium_mg",
    "dietary_fibre_g"
]

FIELD_FRIENDLY_NAMES = {
    "energy_kcal": "Energy (kcal)",
    "carbohydrates_g": "Carbohydrates (g)",
    "sugars_g": "Total Sugars (g)",
    "added_sugars_g": "Added Sugars (g)",
    "protein_g": "Protein (g)",
    "total_fat_g": "Total Fat (g)",
    "saturated_fat_g": "Saturated Fat (g)",
    "trans_fat_g": "Trans Fat (g)",
    "cholesterol_mg": "Cholesterol (mg)",
    "sodium_mg": "Sodium (mg)",
    "dietary_fibre_g": "Dietary Fibre (g)"
}

def parse_float_safe(val: Any) -> float | None:
    """Parses a float value safely; returns None if null, empty, or unparseable."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    s = str(val).strip()
    if not s or s.lower() in ["none", "null", "nan", "n/a", "na", "-", "nil", ""]:
        return None
    # Strip trailing unit characters if present (e.g. '12.5g', '350mg')
    s_clean = s.rstrip("gGmMkKlLoOzZ /").strip()
    try:
        f = float(s_clean)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None

def validate_and_normalize_nutrition(
    product_data: dict[str, Any],
    mandatory_fields: list[str] | None = None,
    target_basis: str = "per 100g"
) -> dict[str, Any]:
    """
    Validates and normalizes nutritional facts before feeding them into scoring engines.
    Preserves raw inputs and flags anomalies.
    """
    if mandatory_fields is None:
        mandatory_fields = ["energy_kcal", "sugars_g", "saturated_fat_g", "sodium_mg"]

    raw_nutrition: dict[str, Any] = {}
    cleaned_nutrition: dict[str, float | None] = {}
    missing_mandatory: list[str] = []
    missing_optional: list[str] = []
    validation_warnings: list[str] = []
    contradictions: list[str] = []

    # 1. Extract raw and cleaned numeric values
    for f in NUTRIENT_FIELDS:
        raw_val = product_data.get(f)
        raw_nutrition[f] = raw_val
        parsed = parse_float_safe(raw_val)

        # Check negative
        if parsed is not None and parsed < 0:
            contradictions.append(f"Invalid negative value for {FIELD_FRIENDLY_NAMES.get(f, f)}: {parsed}")
            cleaned_nutrition[f] = None
        else:
            cleaned_nutrition[f] = parsed

    # 2. Reference Basis Detection & Normalization
    raw_basis = str(product_data.get("measurement_basis", "per 100g")).strip().lower()
    raw_serving_size = parse_float_safe(product_data.get("serving_size"))
    serving_unit = str(product_data.get("serving_size_unit", "g")).strip().lower()

    normalized_nutrition = dict(cleaned_nutrition)
    basis_converted = False
    conversion_factor = 1.0

    if "serving" in raw_basis:
        if raw_serving_size and raw_serving_size > 0:
            # Convert per-serving values to per-100g or per-100ml
            target_denom = 100.0
            conversion_factor = target_denom / raw_serving_size
            for k, v in cleaned_nutrition.items():
                if v is not None:
                    normalized_nutrition[k] = round(v * conversion_factor, 2)
            basis_converted = True
            validation_warnings.append(
                f"Nutritional values converted from per-serving basis ({raw_serving_size}{serving_unit}) to {target_basis}."
            )
        else:
            contradictions.append(
                "Declared reference basis is 'per serving', but serving size is missing or invalid. Cannot normalize safely."
            )

    # 3. Check Mandatory and Optional Nutrient Completeness
    missing_mandatory_labels: list[str] = []
    missing_optional_labels: list[str] = []

    for f in mandatory_fields:
        if normalized_nutrition.get(f) is None:
            missing_mandatory.append(f)
            missing_mandatory_labels.append(FIELD_FRIENDLY_NAMES.get(f, f))

    for f in NUTRIENT_FIELDS:
        if f not in mandatory_fields and normalized_nutrition.get(f) is None:
            missing_optional.append(f)
            missing_optional_labels.append(FIELD_FRIENDLY_NAMES.get(f, f))

    # 4. Thermodynamic & Compositional Consistency Cross-Checks
    carbs = normalized_nutrition.get("carbohydrates_g")
    sugars = normalized_nutrition.get("sugars_g")
    tot_fat = normalized_nutrition.get("total_fat_g")
    sat_fat = normalized_nutrition.get("saturated_fat_g")
    trans_fat = normalized_nutrition.get("trans_fat_g")
    protein = normalized_nutrition.get("protein_g")
    energy = normalized_nutrition.get("energy_kcal")
    sodium = normalized_nutrition.get("sodium_mg")

    # A. Sugars cannot exceed Total Carbohydrates (with 5% analytical tolerance)
    if sugars is not None and carbs is not None and carbs > 0:
        if sugars > (carbs * 1.05 + 0.1):
            contradictions.append(
                f"Total Sugars ({sugars}g) exceeds Total Carbohydrates ({carbs}g) on product label."
            )

    # B. Saturated Fat cannot exceed Total Fat (with 5% analytical tolerance)
    if sat_fat is not None and tot_fat is not None and tot_fat > 0:
        if sat_fat > (tot_fat * 1.05 + 0.1):
            contradictions.append(
                f"Saturated Fat ({sat_fat}g) exceeds Total Fat ({tot_fat}g) on product label."
            )

    # C. Trans Fat cannot exceed Total Fat
    if trans_fat is not None and tot_fat is not None and tot_fat > 0:
        if trans_fat > (tot_fat * 1.05 + 0.1):
            contradictions.append(
                f"Trans Fat ({trans_fat}g) exceeds Total Fat ({tot_fat}g)."
            )

    # D. Maximum physical calorie density check (pure fat is 900 kcal/100g, thermodynamic max ~950)
    if energy is not None and target_basis in ["per 100g", "per 100ml"]:
        if energy > 950.0:
            contradictions.append(
                f"Declared energy ({energy} kcal/{target_basis}) exceeds thermodynamic limit for organic food (950 kcal/100g)."
            )

    # E. Sodium plausibility check (pure sodium chloride salt is ~39,340 mg sodium / 100g)
    if sodium is not None and target_basis in ["per 100g", "per 100ml"]:
        if sodium > 40000.0:
            contradictions.append(
                f"Declared sodium ({sodium} mg/{target_basis}) exceeds pure salt chemical density (40,000 mg/100g)."
            )

    # F. Sum of macronutrients should not exceed 100g (plus 5% analytical variance allowance = 105g)
    if carbs is not None and tot_fat is not None and protein is not None and target_basis == "per 100g":
        macro_sum = carbs + tot_fat + protein
        if macro_sum > 105.0:
            validation_warnings.append(
                f"Sum of declared macronutrients ({macro_sum:.1f}g) exceeds 100g basis by >5%."
            )

    is_valid_for_scoring = (len(missing_mandatory) == 0 and len(contradictions) == 0)

    return {
        "is_valid_for_scoring": is_valid_for_scoring,
        "is_complete": len(missing_mandatory) == 0,
        "missing_mandatory_fields": missing_mandatory,
        "missing_mandatory_labels": missing_mandatory_labels,
        "missing_optional_fields": missing_optional,
        "missing_optional_labels": missing_optional_labels,
        "validation_warnings": validation_warnings,
        "contradictions": contradictions,
        "normalized_nutrition": normalized_nutrition,
        "raw_nutrition": raw_nutrition,
        "reference_basis": target_basis,
        "basis_converted": basis_converted,
        "conversion_factor": conversion_factor
    }
