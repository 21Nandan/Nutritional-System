"""
EATGOOD — Label text parser and /api/analyze/label-text tests.

OCR runs in the browser; these tests cover what the server does with the recognised text.
The fixture ocr_peanut_label_tesseract.txt is real Tesseract 5.5.3 output from a label photo
taken during development (kept from the original scan log).
"""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.label_text_parser import extract_nutrition_from_text
from backend.main import app

client = TestClient(app)
FIXTURES = Path(__file__).parent / "fixtures"


def test_real_tesseract_output_regression():
    text = (FIXTURES / "ocr_peanut_label_tesseract.txt").read_text()
    ext = extract_nutrition_from_text(text, 0.8)
    vals = ext["extracted_values"]
    assert vals["energy_kcal"] == 602
    assert vals["protein_g"] == 12.95
    assert vals["total_fat_g"] == 44.56
    assert vals["saturated_fat_g"] == 18.72
    assert vals["sodium_mg"] == 788
    assert vals["sugars_g"] == 0.0
    assert vals["serving_size"] == 20
    # "3736 g" and "468g" are impossible per 100 g: never guessed, never scored.
    assert vals["carbohydrates_g"] is None
    assert ext["field_statuses"]["carbohydrates_g"] == "needs_review"
    assert ext["suggestions"]["carbohydrates_g"] == {
        "original_token": "3736", "original_value": 3736.0, "suggested_value": 37.36
    }
    assert vals["dietary_fibre_g"] is None
    assert ext["suggestions"]["dietary_fibre_g"]["suggested_value"] == 4.68


def test_impossible_value_is_cleared_with_suggestion_not_auto_repaired():
    ext = extract_nutrition_from_text("Per 100g\nEnergy: 420 kcal\nCarbohydrates: 3736 g\nProtein: 8.5 g\nTotal Sugars: Og")
    assert ext["extracted_values"]["carbohydrates_g"] is None
    assert ext["field_statuses"]["carbohydrates_g"] == "needs_review"
    assert ext["suggestions"]["carbohydrates_g"]["suggested_value"] == 37.36
    assert "3736" in ext["field_notes"]["carbohydrates_g"]
    assert ext["extracted_values"]["sugars_g"] == 0.0


def test_value_with_no_plausible_suggestion():
    ext = extract_nutrition_from_text("Per 100g\nProtein: 123456 g")
    assert ext["extracted_values"]["protein_g"] is None
    assert ext["suggestions"]["protein_g"]["suggested_value"] is None


def test_missing_values_stay_missing_not_zero():
    ext = extract_nutrition_from_text("Per 100g\nEnergy: 250 kcal")
    vals = ext["extracted_values"]
    assert vals["sodium_mg"] is None
    assert vals["sugars_g"] is None
    assert "sodium_mg" in ext["missing_fields"]


def test_salt_converted_to_sodium():
    ext = extract_nutrition_from_text("Per 100g\nSalt 1.25 g")
    assert ext["extracted_values"]["sodium_mg"] == 500.0  # 1.25 g salt / 2.5 = 0.5 g sodium


def test_atwater_calorie_crosscheck():
    ext = extract_nutrition_from_text("Per 100g\nEnergy: 800 kcal\nCarbohydrates: 10.0g\nProtein: 5.0g\nTotal Fat: 5.0g")
    assert ext["field_statuses"]["energy_kcal"] == "needs_review"
    assert any("Calorie discrepancy" in flag for flag in ext["suspicious_flags"])


def test_sub_nutrient_consistency_checks():
    ext = extract_nutrition_from_text(
        "Per 100g\nEnergy: 300 kcal\nCarbohydrates: 20.0g\nTotal Sugars: 45.0g\nTotal Fat: 10.0g\nSaturated Fat: 15.0g"
    )
    assert ext["field_statuses"]["saturated_fat_g"] == "needs_review"
    assert ext["field_statuses"]["sugars_g"] == "needs_review"


def test_beverage_basis_detected():
    ext = extract_nutrition_from_text("Nutrition information per 100 ml\nEnergy 42 kcal\nTotal sugars 10.6 g")
    assert ext["extracted_values"]["measurement_basis"] == "per 100ml"
    assert ext["extracted_values"]["serving_size_unit"] == "ml"


def test_empty_text_returns_nothing_found():
    ext = extract_nutrition_from_text("   ")
    assert all(v is None for k, v in ext["extracted_values"].items() if k.endswith(("_g", "_mg", "_kcal")))


def test_label_text_endpoint():
    text = (FIXTURES / "ocr_peanut_label_tesseract.txt").read_text()
    res = client.post("/api/analyze/label-text", json={"raw_text": text, "ocr_confidence": 0.81, "engine": "tesseract.js 5"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["requires_user_confirmation"] is True
    assert data["extracted_values"]["carbohydrates_g"] is None
    assert "carbohydrates_g" in data["suggestions"]


def test_label_text_endpoint_reports_no_values():
    res = client.post("/api/analyze/label-text", json={"raw_text": "hello world", "ocr_confidence": 0.3, "engine": "t"})
    assert res.json()["status"] == "no_values_found"


def test_label_text_endpoint_validates_input():
    assert client.post("/api/analyze/label-text", json={"raw_text": "", "ocr_confidence": 0.3, "engine": "t"}).status_code == 422
    assert client.post("/api/analyze/label-text", json={"raw_text": "x", "ocr_confidence": 3, "engine": "t"}).status_code == 422
