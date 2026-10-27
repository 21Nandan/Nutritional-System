"""
EATGOOD — OCR & Food Label Extraction Service
Integrates macOS Native Vision OCR with intelligent regex nutritional information parsing.
Enforces an editable confirmation step and explicit anomaly checks before grading.
"""

import os
import re
import json
import subprocess

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
OCR_BINARY = os.path.join(SCRIPT_DIR, "ocr_helper")

def run_image_ocr(image_path: str):
    """
    Runs text extraction on an image file using local OCR.
    Falls back gracefully if binary or image unavailable.
    """
    if not os.path.exists(image_path):
        return {"status": "error", "message": f"Image file not found at {image_path}", "raw_text": "", "lines": []}

    if os.path.exists(OCR_BINARY):
        try:
            res = subprocess.run([OCR_BINARY, image_path], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return {
                    "status": "success",
                    "raw_text": data.get("full_text", ""),
                    "lines": data.get("lines", []),
                    "engine": "Local OCR Engine"
                }
        except Exception as e:
            print(f"Warning: Vision OCR execution failed: {e}")

    # Fallback to simulated extraction for sample image or manual entry notice
    return {
        "status": "fallback",
        "raw_text": "Nutrition Facts\nPer 100g\nEnergy: 450 kcal\nCarbohydrates: 62.0g\nSugars: 14.5g\nProtein: 7.8g\nTotal Fat: 18.2g\nSaturated Fat: 8.5g\nSodium: 420mg\nDietary Fibre: 4.2g\nIngredients: Wheat flour, Sugar, Palm oil, Salt, Raising agents (INS 500ii).",
        "lines": ["Nutrition Facts", "Per 100g", "Energy: 450 kcal", "Carbohydrates: 62.0g"],
        "engine": "Sample Pattern Matcher / Fallback Parser"
    }

def extract_nutrition_from_text(text: str):
    """
    Parses unstructured OCR text into structured nutrition metrics using domain heuristics.
    """
    clean_text = text.replace(",", ".")
    results = {
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
    confidence = {}

    # Serving size & basis
    srv_match = re.search(r'(?:serving size|per serving|serve size)[\s:]*([0-9.]+)\s*(g|ml|gm)', clean_text, re.IGNORECASE)
    if srv_match:
        results["serving_size"] = float(srv_match.group(1))
        results["serving_size_unit"] = srv_match.group(2).lower()
        confidence["serving_size"] = 0.85
    elif "per 100g" in clean_text.lower():
        results["serving_size"] = 100.0
        results["serving_size_unit"] = "g"
        results["measurement_basis"] = "per 100g"
        confidence["serving_size"] = 0.95
    elif "per 100ml" in clean_text.lower():
        results["serving_size"] = 100.0
        results["serving_size_unit"] = "ml"
        results["measurement_basis"] = "per 100ml"
        confidence["serving_size"] = 0.95

    # Patterns for key nutrients
    patterns = {
        "energy_kcal": [
            r'(?:energy|calories|caloric value)[\s:]*([0-9.]+)\s*(?:kcal|cal)?',
            r'([0-9.]+)\s*kcal'
        ],
        "carbohydrates_g": [
            r'(?:carbohydrate|carbohydrates|total carbs|carbs)[\s:]*([0-9.]+)\s*g?',
        ],
        "sugars_g": [
            r'(?:total sugars|sugars|sugar)[\s:]*([0-9.]+)\s*g?',
        ],
        "added_sugars_g": [
            r'(?:added sugars|added sugar)[\s:]*([0-9.]+)\s*g?',
        ],
        "protein_g": [
            r'(?:protein)[\s:]*([0-9.]+)\s*g?',
        ],
        "total_fat_g": [
            r'(?:total fat|fat)[\s:]*([0-9.]+)\s*g?',
        ],
        "saturated_fat_g": [
            r'(?:saturated fat|sat fat|saturated fatty acids)[\s:]*([0-9.]+)\s*g?',
        ],
        "trans_fat_g": [
            r'(?:trans fat|trans fatty acids)[\s:]*([0-9.]+)\s*g?',
        ],
        "sodium_mg": [
            r'(?:sodium)[\s:]*([0-9.]+)\s*(?:mg)?',
            r'(?:salt)[\s:]*([0-9.]+)\s*(?:g|mg)?'
        ],
        "dietary_fibre_g": [
            r'(?:dietary fibre|dietary fiber|fibre|fiber)[\s:]*([0-9.]+)\s*g?',
        ]
    }

    for key, regexes in patterns.items():
        for p in regexes:
            m = re.search(p, clean_text, re.IGNORECASE)
            if m:
                val = float(m.group(1))
                if key == "sodium_mg" and "salt" in p and val < 50:
                    # Salt in g converted to sodium in mg: sodium = salt / 2.5 * 1000 = salt * 400
                    val = round(val * 400, 1)
                results[key] = val
                confidence[key] = 0.88
                break

    # Extract ingredients if present
    ing_match = re.search(r'(?:ingredients|contains)[\s:]*(.+?)(?:\.|$|\n\n)', text, re.IGNORECASE | re.DOTALL)
    if ing_match:
        results["ingredients"] = ing_match.group(1).strip()
        confidence["ingredients"] = 0.80

    # Sanity checks and missing fields audit
    missing_fields = [k for k, v in results.items() if v is None and k not in ["added_sugars_g", "trans_fat_g"]]
    suspicious_flags = []

    # Check Atwater calorie sum if macros present
    if results["carbohydrates_g"] and results["protein_g"] and results["total_fat_g"] and results["energy_kcal"]:
        atwater = 4*results["carbohydrates_g"] + 4*results["protein_g"] + 9*results["total_fat_g"]
        diff = abs(results["energy_kcal"] - atwater)
        if diff > 50:
            suspicious_flags.append(
                f"Calorie discrepancy: Reported {results['energy_kcal']} kcal vs Atwater macronutrient estimate {atwater:.1f} kcal (Delta: {diff:.1f} kcal). Please verify label."
            )

    # Check macro sum > stated serving size
    if results["serving_size"] and results["carbohydrates_g"] and results["protein_g"] and results["total_fat_g"]:
        macro_sum = results["carbohydrates_g"] + results["protein_g"] + results["total_fat_g"]
        if macro_sum > results["serving_size"]:
            suspicious_flags.append(
                f"Contradiction: Sum of macros ({macro_sum:.1f}g) exceeds stated serving size ({results['serving_size']}g). Please confirm if table is per 100g."
            )

    return {
        "extracted_values": results,
        "confidence_scores": confidence,
        "missing_fields": missing_fields,
        "suspicious_flags": suspicious_flags,
        "requires_user_confirmation": True
    }
