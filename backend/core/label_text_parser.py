"""
EATGOOD — Nutrition label text parser.

OCR runs in the visitor's browser (tesseract.js); this module only turns the
recognised text into candidate nutrition values. Every value it returns must be
confirmed by the user before it is scored. Values that look like OCR glitches are
never silently corrected: they are left empty, flagged needs_review, and a
suggestion is offered alongside the original token.
"""

import re
from typing import Any

FIELD_LABELS = {
    "carbohydrates_g": "Carbohydrates",
    "protein_g": "Protein",
    "total_fat_g": "Total fat",
    "sugars_g": "Sugars",
    "dietary_fibre_g": "Dietary fibre",
}


def _clean_number_str(raw_str: str) -> float | None:
    """
    Cleans raw OCR number strings handling common OCR artifacts:
    - Replaces comma with decimal point ('12,5' -> '12.5')
    - Replaces leading 'O' or 'o' with '0' ('Og' -> '0')
    - Handles '<0.1' or '<01'
    - Strips trailing characters
    """
    if not raw_str:
        return None
    s = raw_str.strip().replace(",", ".")

    # Handle common OCR 'Og' -> '0g' or 'O g'
    s = re.sub(r'^[Oo]\s*g?', '0', s)

    # Handle '<01' -> '0.1' or '<0.1'
    if s.startswith("<01") or s == "01":
        return 0.1
    if s.startswith("<"):
        s = s.lstrip("<").strip()

    # Extract first valid floating point or integer number
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)', s)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def extract_nutrition_from_text(text: str, ocr_confidence: float = 0.85) -> dict[str, Any]:
    """
    Parses unstructured OCR text into structured nutrition metrics using domain heuristics.
    Detects inline and tabular representations, checks physiological plausibility,
    and returns explicit status tags for every field.
    """
    if not text or not text.strip():
        # Clean empty return when no text was extracted
        empty_fields = {
            "serving_size": None,
            "serving_size_unit": "g",
            "measurement_basis": "per 100g",
            "energy_kcal": None,
            "carbohydrates_g": None,
            "sugars_g": None,
            "added_sugars_g": None,
            "protein_g": None,
            "total_fat_g": None,
            "saturated_fat_g": None,
            "trans_fat_g": None,
            "sodium_mg": None,
            "dietary_fibre_g": None,
            "ingredients": None
        }
        return {
            "extracted_values": empty_fields,
            "field_statuses": {k: "not_found" for k in empty_fields},
            "confidence_scores": {},
            "field_notes": {},
            "missing_fields": list(empty_fields.keys()),
            "suspicious_flags": [],
            "suggestions": {},
            "requires_user_confirmation": True
        }

    clean_text = text.replace(",", ".")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    results: dict[str, Any] = {
        "serving_size": None,
        "serving_size_unit": "g",
        "measurement_basis": "per 100g",
        "energy_kcal": None,
        "carbohydrates_g": None,
        "sugars_g": None,
        "added_sugars_g": None,
        "protein_g": None,
        "total_fat_g": None,
        "saturated_fat_g": None,
        "trans_fat_g": None,
        "sodium_mg": None,
        "dietary_fibre_g": None,
        "ingredients": None
    }

    confidence: dict[str, float] = {}
    field_statuses: dict[str, str] = {}
    field_notes: dict[str, str] = {}
    suspicious_flags: list[str] = []
    suggestions: dict[str, dict[str, Any]] = {}
    raw_tokens: dict[str, str] = {}

    # 1. Serving size & basis detection
    srv_patterns = [
        r'(?:serve\s*size\s*(?:is)?|serving\s*size\s*(?:is)?|serve\s*measure|per\s*serve)[\s:]*([0-9.]+)\s*([gml]{1,2}|gm)',
        r'([0-9.]+)\s*([gml]{1,2})\s*(?:per\s*serving|serve\s*size)'
    ]
    for p in srv_patterns:
        m = re.search(p, clean_text, re.IGNORECASE)
        if m:
            results["serving_size"] = float(m.group(1))
            unit = m.group(2).lower()
            results["serving_size_unit"] = "ml" if "ml" in unit else "g"
            confidence["serving_size"] = min(0.95, ocr_confidence + 0.1)
            field_statuses["serving_size"] = "extracted"
            break

    # Measurement basis detection
    if re.search(r'per\s*100\s*ml', clean_text, re.IGNORECASE):
        results["measurement_basis"] = "per 100ml"
        results["serving_size_unit"] = "ml"
    elif re.search(r'per\s*100\s*(?:g|gm|9)', clean_text, re.IGNORECASE):
        results["measurement_basis"] = "per 100g"
        results["serving_size_unit"] = "g"
    elif results["serving_size"] and re.search(r'per\s*serving', clean_text, re.IGNORECASE):
        results["measurement_basis"] = "per serving"

    if results["serving_size"] is None:
        if results["measurement_basis"] in ["per 100g", "per 100ml"]:
            results["serving_size"] = 100.0
            confidence["serving_size"] = 0.80
            field_statuses["serving_size"] = "extracted"
        else:
            field_statuses["serving_size"] = "not_found"

    # 2. Nutrient Line & Tabular Regex Matching
    nutrient_matchers = [
        ("energy_kcal", [
            r'(?:energy|calories|caloric\s*value)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([0-9.]+)\s*(?:kcal|cal)?',
            r'([0-9.]+)\s*kcal'
        ]),
        ("carbohydrates_g", [
            r'(?:total\s*carbohydrates?|carbohydrates?|total\s*carbs?|carbs?)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("added_sugars_g", [
            r'(?:added\s*sugars?|of\s*which\s*added\s*sugars?)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("sugars_g", [
            r'(?:total\s*sugars?|sugars?|of\s*which\s*sugars?)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("protein_g", [
            r'(?:protein)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("saturated_fat_g", [
            r'(?:saturated\s*fat(?:ty\s*acids)?|sat\s*fat)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("trans_fat_g", [
            r'(?:trans\s*fat(?:ty\s*acids)?)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("total_fat_g", [
            r'(?:total\s*fat|fat)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("sodium_mg", [
            r'(?:sodium)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)\s*(?:mg)?',
            r'(?:salt)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)\s*(?:g|mg)?'
        ]),
        ("dietary_fibre_g", [
            r'(?:dietary\s*fib(?:re|er)|fib(?:re|er))[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ])
    ]

    for key, regex_list in nutrient_matchers:
        val = None
        # Check line by line first (handles tabular rows cleanly)
        for line in lines:
            for p in regex_list:
                m = re.search(p, line, re.IGNORECASE)
                if m:
                    parsed = _clean_number_str(m.group(1))
                    if parsed is not None:
                        val = parsed
                        raw_tokens[key] = m.group(1).strip()
                        if key == "sodium_mg" and "salt" in p.lower() and val < 50:
                            # Convert salt in grams to sodium in mg (salt * 400 = sodium mg)
                            val = round(val * 400, 1)
                            field_notes["sodium_mg"] = f"Calculated from Salt ({m.group(1)}g)"
                        break
            if val is not None:
                break

        # Fallback to multi-line string search if line-by-line missed
        if val is None:
            for p in regex_list:
                m = re.search(p, clean_text, re.IGNORECASE)
                if m:
                    parsed = _clean_number_str(m.group(1))
                    if parsed is not None:
                        val = parsed
                        raw_tokens[key] = m.group(1).strip()
                        if key == "sodium_mg" and "salt" in p.lower() and val < 50:
                            val = round(val * 400, 1)
                        break

        if val is not None:
            results[key] = val
            confidence[key] = min(0.92, ocr_confidence)
            field_statuses[key] = "extracted"
        else:
            field_statuses[key] = "not_found"

    # 3. Implausible macro values (> 100 g per 100 g/ml). OCR often drops a decimal
    # point (e.g. "37.36" read as "3736"). We never guess: the field is cleared so it
    # cannot be scored, and a suggestion is offered for the user to accept or reject.
    if results["measurement_basis"] in ["per 100g", "per 100ml"]:
        for macro in ["carbohydrates_g", "protein_g", "total_fat_g", "sugars_g", "dietary_fibre_g"]:
            raw_v = results[macro]
            if raw_v is not None and raw_v > 100.0:
                label = FIELD_LABELS[macro]
                results[macro] = None
                field_statuses[macro] = "needs_review"
                suggested = round(raw_v / 100.0, 2)
                suggestion = {"original_token": raw_tokens[macro], "original_value": raw_v, "suggested_value": None}
                if suggested <= 100.0:
                    suggestion["suggested_value"] = suggested
                    field_notes[macro] = f"Read as {raw_tokens[macro]!r}, which is impossible per 100. Did you mean {suggested}?"
                else:
                    field_notes[macro] = f"Read as {raw_tokens[macro]!r}, which is impossible per 100. Enter the value from the label."
                suggestions[macro] = suggestion
                suspicious_flags.append(f"{label}: read as {raw_tokens[macro]!r}, which exceeds 100 g per 100. Please enter the value from the label.")

    # 4. Ingredients Extraction
    ing_patterns = [
        r'(?:ingredients|ingredient\s*list)[\s:]*([^\.\n]+(?:\.[^\.\n]+){1,5})',
        r'(?:contains\s*[:])\s*([^\.\n]+)'
    ]
    for p in ing_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            ing_text = m.group(1).strip()
            if len(ing_text) > 8:
                results["ingredients"] = ing_text
                confidence["ingredients"] = 0.85
                field_statuses["ingredients"] = "extracted"
                break
    if results["ingredients"] is None:
        field_statuses["ingredients"] = "not_found"

    # 5. Scientific Plausibility & Cross-Field Consistency Audits
    # Atwater calorie check: Energy = 4*Carbs + 4*Protein + 9*Fat
    if results["carbohydrates_g"] is not None and results["protein_g"] is not None and results["total_fat_g"] is not None and results["energy_kcal"] is not None:
        atwater = 4.0 * results["carbohydrates_g"] + 4.0 * results["protein_g"] + 9.0 * results["total_fat_g"]
        diff = abs(results["energy_kcal"] - atwater)
        if diff > 60:
            suspicious_flags.append(
                f"Calorie discrepancy: Reported {results['energy_kcal']} kcal vs Atwater estimate {atwater:.1f} kcal (Delta: {diff:.1f} kcal). Please verify label numbers."
            )
            field_statuses["energy_kcal"] = "needs_review"
            field_notes["energy_kcal"] = f"Atwater estimate is {atwater:.1f} kcal"

    # Saturated fat vs Total fat check
    if results["saturated_fat_g"] is not None and results["total_fat_g"] is not None:
        if results["saturated_fat_g"] > results["total_fat_g"]:
            suspicious_flags.append(
                f"Fat inconsistency: Saturated fat ({results['saturated_fat_g']}g) cannot exceed Total fat ({results['total_fat_g']}g)."
            )
            field_statuses["saturated_fat_g"] = "needs_review"

    # Sugars vs Carbohydrates check
    if results["sugars_g"] is not None and results["carbohydrates_g"] is not None:
        if results["sugars_g"] > results["carbohydrates_g"]:
            suspicious_flags.append(
                f"Carbohydrate inconsistency: Sugars ({results['sugars_g']}g) cannot exceed Total carbohydrates ({results['carbohydrates_g']}g)."
            )
            field_statuses["sugars_g"] = "needs_review"

    # Macronutrient sum vs serving size
    if results["serving_size"] and results["carbohydrates_g"] is not None and results["protein_g"] is not None and results["total_fat_g"] is not None:
        macro_sum = results["carbohydrates_g"] + results["protein_g"] + results["total_fat_g"]
        if macro_sum > (results["serving_size"] * 1.05):
            suspicious_flags.append(
                f"Macro sum ({macro_sum:.1f}g) exceeds declared serving basis ({results['serving_size']}g)."
            )

    # Missing core fields audit
    core_keys = ["energy_kcal", "carbohydrates_g", "sugars_g", "protein_g", "total_fat_g", "sodium_mg"]
    missing_fields = [k for k in core_keys if results[k] is None]

    return {
        "extracted_values": results,
        "field_statuses": field_statuses,
        "confidence_scores": confidence,
        "field_notes": field_notes,
        "missing_fields": missing_fields,
        "suspicious_flags": suspicious_flags,
        "suggestions": suggestions,
        "requires_user_confirmation": True
    }
