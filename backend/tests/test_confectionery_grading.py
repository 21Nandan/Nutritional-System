"""Chocolates & Sweets: EATGOOD's own A–E method (backend/core/standards_registry.py).

Each product is graded from its own values per 100 g with the same points, formula and grade bands
as every other category; only the limits are EATGOOD's own, and every grade says so. All products
here are invented.
"""

import pytest
from fastapi.testclient import TestClient

from backend.core.nutrition_scoring import assess_general_nutrition
from backend.core.standards_registry import CALIBRATED_CATEGORIES, CATEGORY_CALIBRATION_SPECS, nutrient_flags
from backend.main import app

client = TestClient(app)

SPEC = CATEGORY_CALIBRATION_SPECS["Chocolates & Sweets"]
LIMITS = SPEC["thresholds"]


def sweet(**values):
    record = {"category": "Chocolates & Sweets", "measurement_basis": "per 100g", "energy_kcal": 400,
              "carbohydrates_g": 98, "sugars_g": 10, "total_fat_g": 20, "saturated_fat_g": 3, "sodium_mg": 200}
    record.update(values)
    return record


def grade(**values):
    return assess_general_nutrition(sweet(**values))


def points(result, nutrient):
    return result["key_contributing_nutrients"][nutrient]["points"]


# ---------- the method itself ----------

def test_method_is_labelled_as_eatgoods_own_not_official():
    assert "Chocolates & Sweets" in CALIBRATED_CATEGORIES
    assert SPEC["method_type"] == "EATGOOD"
    assert "not an official WHO or FSSAI grade" in SPEC["methodology_name"]
    assert "not an official WHO or FSSAI grade" in SPEC["method_notice"]
    result = grade()
    assert result["is_eatgood_method"] is True
    assert result["grade_note"] == "EATGOOD's own method, not an official grade"
    assert result["method_notice"] == SPEC["method_notice"]
    assert result["methodology_name"] == SPEC["methodology_name"]
    assert "not an official" in result["explanation"]
    assert "authoritative" not in result["explanation"]


def test_limits_are_per_100g_for_sugar_saturated_fat_and_sodium():
    assert SPEC["reference_basis"] == "per 100g"
    assert (LIMITS["sugars_g"], LIMITS["saturated_fat_g"], LIMITS["sodium_mg"]) == (22.5, 5.0, 600.0)
    assert SPEC["mandatory_fields"] == ["energy_kcal", "sugars_g", "saturated_fat_g", "sodium_mg"]


# ---------- graded by values, not automatically E ----------

@pytest.mark.parametrize(
    ("description", "values", "expected"),
    [
        ("sugar-free mint", {"sugars_g": 0.5, "saturated_fat_g": 0, "sodium_mg": 20, "carbohydrates_g": 95, "total_fat_g": 0}, "B"),
        ("85% dark chocolate", {"sugars_g": 14, "saturated_fat_g": 28, "sodium_mg": 20, "dietary_fibre_g": 12, "protein_g": 10,
                                "total_fat_g": 46, "carbohydrates_g": 22}, "B"),
        ("70% dark chocolate", {"sugars_g": 28, "saturated_fat_g": 24, "sodium_mg": 20, "dietary_fibre_g": 11, "protein_g": 8,
                                "total_fat_g": 42, "carbohydrates_g": 36}, "C"),
        ("fruit jelly sweets", {"sugars_g": 55, "saturated_fat_g": 0.1, "sodium_mg": 30, "carbohydrates_g": 78, "total_fat_g": 0.2}, "D"),
        ("milk chocolate", {"sugars_g": 56, "saturated_fat_g": 18, "sodium_mg": 90, "protein_g": 7, "total_fat_g": 30,
                            "carbohydrates_g": 58}, "E"),
        ("butter toffee", {"sugars_g": 60, "saturated_fat_g": 10, "sodium_mg": 300, "total_fat_g": 15, "carbohydrates_g": 75}, "E"),
    ],
)
def test_products_get_different_grades_from_their_values(description, values, expected):
    result = grade(**values)
    assert result["status"] == "Calibrated", description
    assert result["grade"] == expected, (description, result["general_nutrition_score"])


def test_grades_span_the_scale():
    grades = {grade(sugars_g=s, saturated_fat_g=f, sodium_mg=n)["grade"]
              for s in (2, 15, 30, 60) for f in (1, 4, 8, 20) for n in (50, 400, 900, 1500)}
    assert {"B", "C", "D", "E"} <= grades


def test_a_is_reachable_with_low_values_and_fibre_or_protein():
    result = grade(sugars_g=2, saturated_fat_g=1, sodium_mg=50, trans_fat_g=0, protein_g=12, dietary_fibre_g=7)
    assert result["grade"] == "A"


# ---------- boundaries: at the limit, just above, twice, just above twice ----------

@pytest.mark.parametrize(("nutrient", "field", "penalties"), [
    ("sugars", "sugars_g", (-2, -4)), ("sodium", "sodium_mg", (-2, -4)), ("saturated_fat", "saturated_fat_g", (-1, -3)),
])
def test_limit_boundaries(nutrient, field, penalties):
    limit = LIMITS[field]
    base = {"sugars_g": 10, "saturated_fat_g": 3, "sodium_mg": 200, "carbohydrates_g": 98, "total_fat_g": 40}
    at = grade(**{**base, field: limit})
    above = grade(**{**base, field: limit + 0.01})
    twice = grade(**{**base, field: limit * 2})
    above_twice = grade(**{**base, field: limit * 2 + 0.01})
    assert points(at, nutrient) >= 0
    assert (points(above, nutrient), points(twice, nutrient), points(above_twice, nutrient)) == (penalties[0], penalties[0], penalties[1])


def test_grade_band_edges_use_the_shared_bands():
    """66 is just above B's minimum of 65 and 50 just above C's 48: the same bands as every category."""
    one_bonus = grade(sugars_g=3, saturated_fat_g=3, sodium_mg=200)  # low sugar only
    assert (one_bonus["general_nutrition_score"], one_bonus["grade"]) == (58, "C")
    two_bonuses = grade(sugars_g=3, saturated_fat_g=1, sodium_mg=200)
    assert (two_bonuses["general_nutrition_score"], two_bonuses["grade"]) == (66, "B")
    neutral = grade()
    assert (neutral["general_nutrition_score"], neutral["grade"]) == (50, "C")
    one_penalty = grade(saturated_fat_g=6)
    assert (one_penalty["general_nutrition_score"], one_penalty["grade"]) == (43, "D")


def test_catalogue_flags_use_the_same_limits():
    flags = nutrient_flags(sweet(sugars_g=23, saturated_fat_g=5, sodium_mg=601))
    assert flags["sugars_g"]["level"] == "high"
    assert flags["saturated_fat_g"]["level"] == "ok"
    assert flags["sodium_mg"]["level"] == "high"


# ---------- missing and invalid data stay ungraded ----------

@pytest.mark.parametrize("field", ["energy_kcal", "sugars_g", "saturated_fat_g", "sodium_mg"])
def test_missing_essential_values_are_not_graded(field):
    result = grade(**{field: None})
    assert result["grade"] == "Insufficient Data"
    assert result["missing_fields"] == [field]
    assert result["grade_reason"].startswith("Not graded:")
    assert result["is_eatgood_method"] is False and result["grade_note"] is None


@pytest.mark.parametrize(
    "values",
    [
        {"sugars_g": 70, "carbohydrates_g": 60},
        {"saturated_fat_g": 25, "total_fat_g": 20},
        {"energy_kcal": 1000},
        {"sugars_g": -2},
        {"measurement_basis": "unspecified"},
        {"measurement_basis": "per serving", "serving_size": None},
    ],
)
def test_invalid_values_are_not_graded(values):
    result = grade(**values)
    assert result["grade"] == "Data Contradiction"
    assert result["grade_reason"].startswith("Not graded:")
    assert result["grade_note"] is None


def test_optional_values_never_block_the_grade():
    assert grade(dietary_fibre_g=None, protein_g=None, trans_fat_g=None, carbohydrates_g=None)["status"] == "Calibrated"


def test_per_serving_values_are_converted_before_grading():
    per_serving = grade(measurement_basis="per serving", serving_size=20, energy_kcal=100, sugars_g=11,
                        saturated_fat_g=1, sodium_mg=10, carbohydrates_g=14, total_fat_g=5)
    per_100g = grade(energy_kcal=500, sugars_g=55, saturated_fat_g=5, sodium_mg=50, carbohydrates_g=70, total_fat_g=25)
    assert per_serving["general_nutrition_score"] == per_100g["general_nutrition_score"]


# ---------- regressions ----------

def test_other_categories_are_unchanged():
    # Condiments & Spreads use the same limits as sweets (22.5 g sugar, 5 g saturated fat, 600 mg sodium):
    # 900 mg sodium costs 2 points, no saturated fat earns 1, so 50 - 14 + 8 = 44.
    sauce = assess_general_nutrition({"category": "Condiments & Spreads", "measurement_basis": "per 100g", "energy_kcal": 100,
                                      "sugars_g": 20, "saturated_fat_g": 0, "sodium_mg": 900})
    assert (sauce["general_nutrition_score"], sauce["grade"], sauce["is_eatgood_method"]) == (44, "D", True)
    snack = assess_general_nutrition({"category": "Snacks", "measurement_basis": "per 100g", "energy_kcal": 450,
                                      "sugars_g": 6, "saturated_fat_g": 3, "sodium_mg": 300})
    assert (snack["general_nutrition_score"], snack["grade"], snack["grade_note"]) == (50, "C", None)
    assert "authoritative benchmarks" in snack["explanation"]


def test_listing_comparison_and_product_page_carry_the_label():
    items = {p["product_name"]: p for p in client.get("/api/products?query=chocolate").json()["products"]}
    assert items["Milk Chocolate Bar Test"]["grade_note"] == "EATGOOD's own method, not an official grade"
    product_id = items["Milk Chocolate Bar Test"]["product_id"]
    compared = client.get(f"/api/compare?ids={product_id}").json()
    assert compared["products_compared"][0]["grade_note"] == "EATGOOD's own method, not an official grade"
    page = client.get("/api/products/barcode/2000000000022").json()["assessment"]["layer1_general"]
    assert page["is_eatgood_method"] is True and "not an official" in page["method_notice"]


def test_allergen_override_still_applies_to_chocolates():
    header = {"X-Eatgood-Profile": '%7B%22allergens_to_avoid%22%3A%22Milk%22%7D'}
    item = client.get("/api/products?query=chocolate", headers=header).json()["products"][0]
    assert item["has_allergen_conflict"] is True
    assert item["personalized_score"] == 0
    assert item["general_grade"] == "E"  # the grade is the same for everyone
