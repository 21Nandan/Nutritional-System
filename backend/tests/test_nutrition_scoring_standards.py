"""
EATGOOD — Standards-Based Nutrition Grading & Formula Validation Tests
Comprehensive regression suite validating:
- Deterministic Layer 1 statutory grading across all supported categories
- Explicit refusal states for uncalibrated/unsupported categories
- Mandatory nutrient completeness and missing data refusal
- Boundary condition precision (just below, at, and above thresholds)
- Reference basis normalization (per-serving vs per-100g vs per-100ml)
- Physical plausibility and contradiction detection
- Decoupling of Layer 1 (general grade), Layer 2 (goal suitability), Layer 3 (allergen safety)
- Oreo variant deterministic evaluation (Grade E, Goal Match 40–48/100, no 'Category Not Yet Calibrated' error)
"""

from backend.core.nutrition_scoring import (
    assess_general_nutrition,
    assess_personalized_suitability,
    run_full_product_assessment,
)
from backend.core.nutrition_validator import validate_and_normalize_nutrition
from backend.core.standards_registry import CALIBRATED_CATEGORIES, CATEGORY_CALIBRATION_SPECS, STANDARDS_REGISTRY


def test_standards_registry_completeness():
    """Verifies that all registered standards have verified citations, organizations, and documented thresholds."""
    assert len(STANDARDS_REGISTRY) >= 10
    for std in STANDARDS_REGISTRY:
        assert std["standard_id"].startswith("STD_")
        assert std["organization"] is not None
        assert std["document_title"] is not None
        assert std["citation_url"].startswith("http")
        assert std["publication_year"] >= 2013
        assert std["applicable_category"] is not None
        assert std["measurement_basis"] in ["per 100g", "per 100ml", "per 100g or per 100ml"]


def test_category_calibration_specs():
    """Verifies that all calibrated categories define mandatory fields, reference bases, and methodology names."""
    expected_calibrated = ["Biscuits & Bakery", "Snacks", "Breakfast Cereals", "Packaged Beverages", "Instant Foods", "Dairy"]
    for cat in expected_calibrated:
        assert cat in CALIBRATED_CATEGORIES
        spec = CATEGORY_CALIBRATION_SPECS[cat]
        assert spec["status"] == "Calibrated"
        assert spec["methodology_name"] is not None
        assert spec["standards_version"] is not None
        assert len(spec["mandatory_fields"]) >= 3
        assert spec["reference_basis"] in ["per 100g", "per 100ml"]
        assert "thresholds" in spec


def test_oreo_product_assessment_solves_uncalibrated_issue():
    """
    Specifically reproduces and tests the Oreo case from the user's issue:
    Product: Cadbury Oreo Original Vanilla Creme Biscuits
    Category: Biscuits & Bakery
    Should NO LONGER return 'Category Not Yet Calibrated' / 'Grade N/A'.
    Must compute a deterministic Grade E with documented penalty points.
    """
    # 1. Oreo with packaging data
    oreo_product = {
        "product_id": "IND_PKG_564",
        "product_name": "Cadbury Oreo Original Vanilla Creme Biscuits",
        "brand": "Cadbury",
        "category": "Biscuits & Bakery",
        "measurement_basis": "per 100g",
        "serving_size": 100.0,
        "energy_kcal": 494.1,
        "carbohydrates_g": 69.9,
        "sugars_g": 25.8,
        "saturated_fat_g": 8.9,
        "sodium_mg": 464.7,
        "protein_g": 5.7,
        "dietary_fibre_g": 0.0,
        "ingredients": "Refined Wheat Flour, Sugar, Edible Vegetable Oil, Butter, Salt"
    }

    l1 = assess_general_nutrition(oreo_product)
    assert l1["status"] == "Calibrated", "Oreo must be calibrated under Biscuits & Bakery!"
    assert l1["grade"] == "E", f"Expected Grade E for Oreo, got {l1['grade']}"
    assert "High in Sugar, Sodium, or Saturated Fat" in l1["grade_label"]
    assert "WHO SEARO" in l1["methodology_name"]
    assert "WHO-SEARO-2017-CAT3" in l1["standards_version"]
    assert l1["general_nutrition_score"] == 10
    assert len(l1["concerns"]) >= 2
    assert "sugars" in l1["key_contributing_nutrients"]
    assert "saturated_fat" in l1["key_contributing_nutrients"]

    # 2. Personalized suitability check for Balanced Choices
    profile = {"goal": "Balanced Choices", "dietary_preference": "No preference", "allergens_to_avoid": ""}
    l2 = assess_personalized_suitability(oreo_product, profile)

    # Base: 70 - 15 (sugars > 15g) - 15 (sat fat > 8g) = 40
    assert l2["personalized_score"] == 40, f"Expected 40/100, got {l2['personalized_score']}"
    assert l2["score_display"] == "40/100"
    assert "Suboptimal alignment" in l2["suitability_status"]

    # Verify calculation steps are completely transparent
    steps = l2["calculation_breakdown"]["steps"]
    assert steps[0]["factor"] == "Baseline Profile Neutral Score"
    assert steps[0]["points"] == 70
    assert any("sugar" in s.get("rule", "").lower() for s in steps)
    assert any("saturated fat" in s.get("rule", "").lower() for s in steps)
    assert steps[-1]["running_total"] == 40


def test_supported_categories_grading():
    """Tests each calibrated category computes an evidence-based grade."""
    test_cases = [
        {
            "category": "Biscuits & Bakery",
            "energy_kcal": 420.0,
            "sugars_g": 2.0,
            "saturated_fat_g": 1.2,
            "sodium_mg": 110.0,
            "dietary_fibre_g": 6.5,
            "protein_g": 8.0,
            "expected_grade": "A"
        },
        {
            "category": "Snacks",
            "energy_kcal": 450.0,
            "sugars_g": 1.5,
            "saturated_fat_g": 1.0,
            "sodium_mg": 120.0,
            "dietary_fibre_g": 7.0,
            "protein_g": 10.0,
            "expected_grade": "A"
        },
        {
            "category": "Breakfast Cereals",
            "energy_kcal": 360.0,
            "sugars_g": 2.5,
            "saturated_fat_g": 1.0,
            "sodium_mg": 50.0,
            "dietary_fibre_g": 8.0,
            "protein_g": 12.0,
            "expected_grade": "A"
        },
        {
            "category": "Packaged Beverages",
            "measurement_basis": "per 100ml",
            "energy_kcal": 15.0,
            "sugars_g": 0.5,
            "sodium_mg": 10.0,
            "expected_grade": "A"
        },
        {
            "category": "Instant Foods",
            "energy_kcal": 380.0,
            "sugars_g": 1.0,
            "saturated_fat_g": 1.5,
            "sodium_mg": 120.0,
            "dietary_fibre_g": 6.0,
            "protein_g": 10.0,
            "expected_grade": "A"
        },
        {
            "category": "Dairy",
            "energy_kcal": 65.0,
            "sugars_g": 4.5,
            "saturated_fat_g": 2.0,
            "protein_g": 7.0,
            "sodium_mg": 50.0,
            "expected_grade": "B"
        }
    ]

    for tc in test_cases:
        res = assess_general_nutrition(tc)
        assert res["status"] == "Calibrated", f"Failed for category: {tc['category']}"
        assert res["grade"] == tc["expected_grade"]
        assert res["methodology_name"] is not None
        assert res["standards_version"] is not None


def test_unsupported_categories_explicit_refusal():
    """Verifies that uncalibrated categories (Chocolates & Sweets, Condiments, unknown) are rejected with clear reasons."""
    # Chocolates & Sweets
    choc = {
        "category": "Chocolates & Sweets",
        "energy_kcal": 530,
        "sugars_g": 54.0,
        "saturated_fat_g": 19.0,
        "sodium_mg": 85.0
    }
    res_choc = assess_general_nutrition(choc)
    assert res_choc["status"] == "Uncalibrated Category"
    assert res_choc["grade"] == "N/A"
    assert "not currently calibrated" in res_choc["explanation"]

    # Condiments & Spreads
    ketchup = {
        "category": "Condiments & Spreads",
        "energy_kcal": 120,
        "sugars_g": 24.0,
        "saturated_fat_g": 0.1,
        "sodium_mg": 950.0
    }
    res_ketchup = assess_general_nutrition(ketchup)
    assert res_ketchup["status"] == "Uncalibrated Category"
    assert res_ketchup["grade"] == "N/A"
    assert "culinary condiments" in res_ketchup["explanation"]

    # Unknown Category
    supp = {
        "category": "Dietary Supplements",
        "energy_kcal": 200,
        "sugars_g": 0.0,
        "saturated_fat_g": 0.0,
        "sodium_mg": 10.0
    }
    res_supp = assess_general_nutrition(supp)
    assert res_supp["status"] == "Uncalibrated Category"
    assert res_supp["grade"] == "N/A"


def test_threshold_boundary_conditions():
    """
    Independent hand-calculated threshold boundary tests:
    Category: Biscuits & Bakery (Thresholds: Sugars: 10g, Sat Fat: 4g, Sodium: 300mg)
    Tests values just below threshold, at threshold, and just above threshold.
    """
    # 1. Sugars boundary: 9.9g (within limit), 10.0g (at limit), 10.1g (exceeds -> penalty 2)
    base_biscuit = {
        "category": "Biscuits & Bakery",
        "energy_kcal": 400.0,
        "sugars_g": 9.9,
        "saturated_fat_g": 3.9,
        "sodium_mg": 290.0,
        "dietary_fibre_g": 0.0,
        "protein_g": 4.0
    }
    res_below = assess_general_nutrition(base_biscuit)
    assert res_below["penalty_points"] == 0

    at_limit = dict(base_biscuit, sugars_g=10.0)
    res_at = assess_general_nutrition(at_limit)
    assert res_at["penalty_points"] == 0

    above_limit = dict(base_biscuit, sugars_g=10.1)
    res_above = assess_general_nutrition(above_limit)
    assert res_above["penalty_points"] == 2  # sugar penalty 2 points

    double_limit = dict(base_biscuit, sugars_g=20.1)
    res_double = assess_general_nutrition(double_limit)
    assert res_double["penalty_points"] == 4  # > 2x limit -> sugar penalty 4 points

    # 2. Saturated fat boundary: 4.0g (at limit), 4.1g (above -> penalty 1), 8.1g (> 2x -> penalty 3)
    sat_at = dict(base_biscuit, saturated_fat_g=4.0)
    assert assess_general_nutrition(sat_at)["penalty_points"] == 0

    sat_above = dict(base_biscuit, saturated_fat_g=4.1)
    assert assess_general_nutrition(sat_above)["penalty_points"] == 1

    sat_double = dict(base_biscuit, saturated_fat_g=8.1)
    assert assess_general_nutrition(sat_double)["penalty_points"] == 3

    # 3. Sodium boundary: 300.0mg (at limit), 301.0mg (above -> penalty 2), 601.0mg (> 2x -> penalty 4)
    sod_at = dict(base_biscuit, sodium_mg=300.0)
    assert assess_general_nutrition(sod_at)["penalty_points"] == 0

    sod_above = dict(base_biscuit, sodium_mg=301.0)
    assert assess_general_nutrition(sod_above)["penalty_points"] == 2

    sod_double = dict(base_biscuit, sodium_mg=601.0)
    assert assess_general_nutrition(sod_double)["penalty_points"] == 4


def test_missing_mandatory_nutrients_refusal():
    """Verifies that missing critical nutrient declarations cause an explicit refusal."""
    incomplete_cases = [
        {"category": "Biscuits & Bakery", "energy_kcal": 450, "sugars_g": None, "saturated_fat_g": 5.0, "sodium_mg": 200},
        {"category": "Biscuits & Bakery", "energy_kcal": 450, "sugars_g": 10.0, "saturated_fat_g": None, "sodium_mg": 200},
        {"category": "Biscuits & Bakery", "energy_kcal": 450, "sugars_g": 10.0, "saturated_fat_g": 5.0, "sodium_mg": None},
        {"category": "Biscuits & Bakery", "energy_kcal": None, "sugars_g": 10.0, "saturated_fat_g": 5.0, "sodium_mg": 200}
    ]

    for tc in incomplete_cases:
        res = assess_general_nutrition(tc)
        assert res["status"] == "Insufficient Data"
        assert res["grade"] == "Insufficient Data"
        assert len(res["missing_fields"]) >= 1


def test_per_serving_conversion_to_100g():
    """Verifies that products declared per serving are mathematically converted to per 100g basis."""
    product_serving = {
        "category": "Snacks",
        "measurement_basis": "per serving",
        "serving_size": 25.0,
        "serving_size_unit": "g",
        "energy_kcal": 125.0, # 125 * 4 = 500 kcal/100g
        "sugars_g": 1.0,      # 1.0 * 4 = 4.0 g/100g
        "saturated_fat_g": 1.0,# 1.0 * 4 = 4.0 g/100g
        "sodium_mg": 100.0,   # 100 * 4 = 400 mg/100g
        "dietary_fibre_g": 1.5,
        "protein_g": 2.0
    }
    val = validate_and_normalize_nutrition(product_serving, target_basis="per 100g")
    assert val["basis_converted"] is True
    assert val["conversion_factor"] == 4.0
    norm = val["normalized_nutrition"]
    assert norm["energy_kcal"] == 500.0
    assert norm["sugars_g"] == 4.0
    assert norm["sodium_mg"] == 400.0


def test_contradiction_detection():
    """Verifies that physical and thermodynamic impossibilities are caught."""
    # 1. Sugars > Carbs
    prod_bad_sugar = {
        "category": "Snacks",
        "energy_kcal": 400.0,
        "carbohydrates_g": 10.0,
        "sugars_g": 25.0,
        "total_fat_g": 15.0,
        "saturated_fat_g": 3.0,
        "sodium_mg": 200.0
    }
    val_sug = validate_and_normalize_nutrition(prod_bad_sugar)
    assert any("Total Sugars" in c and "exceeds Total Carbohydrates" in c for c in val_sug["contradictions"])

    # 2. Saturated Fat > Total Fat
    prod_bad_fat = {
        "category": "Snacks",
        "energy_kcal": 400.0,
        "carbohydrates_g": 50.0,
        "sugars_g": 5.0,
        "total_fat_g": 5.0,
        "saturated_fat_g": 12.0,
        "sodium_mg": 200.0
    }
    val_fat = validate_and_normalize_nutrition(prod_bad_fat)
    assert any("Saturated Fat" in c and "exceeds Total Fat" in c for c in val_fat["contradictions"])

    # 3. Energy exceeding 950 kcal/100g
    prod_bad_kcal = {
        "category": "Snacks",
        "energy_kcal": 1200.0,
        "sugars_g": 5.0,
        "saturated_fat_g": 2.0,
        "sodium_mg": 100.0
    }
    val_kcal = validate_and_normalize_nutrition(prod_bad_kcal)
    assert any("exceeds thermodynamic limit" in c for c in val_kcal["contradictions"])


def test_layer_decoupling_and_allergen_non_override():
    """
    Verifies the decoupling principle:
    A product with Grade A nutrition facts that contains an allergen excluded by the user profile:
    - Layer 1 Grade MUST remain 'A' (statutory nutrition profile is not affected by user allergy).
    - Layer 2 Personalized Score MUST be overridden to 0 (hard safety exclusion).
    - Layer 3 Allergen warning MUST be prominently triggered.
    """
    healthy_peanut_bar = {
        "product_id": "BAR_01",
        "product_name": "High Fibre Whole Grain Peanut Bar",
        "category": "Snacks",
        "energy_kcal": 380.0,
        "sugars_g": 2.0,
        "saturated_fat_g": 1.2,
        "sodium_mg": 110.0,
        "dietary_fibre_g": 7.0,
        "protein_g": 11.0,
        "ingredients": "Whole grain rolled oats, roasted peanuts, sea salt",
        "allergens_declared": "Peanuts"
    }

    user_allergic_to_peanuts = {
        "goal": "Increase Fibre",
        "dietary_preference": "Vegetarian",
        "allergens_to_avoid": "Peanuts"
    }

    full_assessment = run_full_product_assessment(healthy_peanut_bar, user_allergic_to_peanuts)

    # Layer 1 must be Grade A
    assert full_assessment["layer1_general"]["grade"] == "A"
    assert full_assessment["layer1_general"]["status"] == "Calibrated"

    # Layer 2 must be overridden to 0
    assert full_assessment["layer2_personalized"]["personalized_score"] == 0
    assert full_assessment["layer2_personalized"]["has_critical_allergen_conflict"] is True
    assert "Critical Allergen Conflict" in full_assessment["layer2_personalized"]["suitability_status"]

    # Layer 3 must identify peanuts
    assert len(full_assessment["layer3_allergens"]["user_conflicts"]) >= 1


def test_reproducibility_of_scoring():
    """Verifies that running the same assessment multiple times produces identical results."""
    prod = {
        "category": "Biscuits & Bakery",
        "energy_kcal": 460.0,
        "sugars_g": 22.0,
        "saturated_fat_g": 7.5,
        "sodium_mg": 380.0,
        "dietary_fibre_g": 2.0,
        "protein_g": 6.0
    }
    profile = {"goal": "Reduce Sugar", "dietary_preference": "Vegetarian", "allergens_to_avoid": ""}

    res1 = run_full_product_assessment(prod, profile)
    res2 = run_full_product_assessment(prod, profile)

    assert res1["layer1_general"]["grade"] == res2["layer1_general"]["grade"]
    assert res1["layer1_general"]["general_nutrition_score"] == res2["layer1_general"]["general_nutrition_score"]
    assert res1["layer2_personalized"]["personalized_score"] == res2["layer2_personalized"]["personalized_score"]
    assert res1["transparency"]["standards_version"] == res2["transparency"]["standards_version"]


def test_uncalibrated_category_user_friendly_wording():
    """
    Verifies that uncalibrated categories (e.g. Condiments & Spreads):
    - Display user-friendly labels ('Overall Grade Unavailable', 'Not yet rated')
    - Format reference basis cleanly ('Per 100 g')
    - Provide short, direct sentences without internal codes like PENDING or EXCLUSION
    """
    ketchup = {
        "category": "Condiments & Spreads",
        "energy_kcal": 110,
        "sugars_g": 22.0,
        "saturated_fat_g": 0.1,
        "sodium_mg": 900.0,
        "measurement_basis": "per 100g"
    }
    res = assess_general_nutrition(ketchup)
    assert res["status"] == "Uncalibrated Category"
    assert res["grade"] == "N/A"
    assert res["grade_label"] == "Overall Grade Unavailable"
    assert res["grade_status_badge"] == "Not yet rated"
    assert res["reference_basis"] == "Per 100 g"
    assert "PENDING" not in res["standards_version"]
    assert "EXCLUSION" not in res["standards_version"]
    assert len(res["explanation"].split(".")) <= 3  # concise, short sentences


def test_catalogue_nutrient_flags_use_category_thresholds():
    """Card colour coding comes from the same thresholds as the grade (single source of truth)."""
    from backend.core.standards_registry import CATEGORY_CALIBRATION_SPECS, nutrient_flags

    snack_limit = CATEGORY_CALIBRATION_SPECS["Snacks"]["thresholds"]["sodium_mg"]
    high = nutrient_flags({"category": "Snacks", "sodium_mg": snack_limit + 1, "sugars_g": None, "saturated_fat_g": 1.0})
    assert high["sodium_mg"] == {"level": "high", "threshold": snack_limit, "basis": "per 100g"}
    assert high["sugars_g"]["level"] == "missing"
    assert high["saturated_fat_g"]["level"] == "ok"
    ok = nutrient_flags({"category": "Snacks", "sodium_mg": snack_limit, "sugars_g": 1, "saturated_fat_g": 1})
    assert ok["sodium_mg"]["level"] == "ok"
    beverage = nutrient_flags({"category": "Packaged Beverages", "sugars_g": 6, "sodium_mg": 10, "saturated_fat_g": 0})
    assert beverage["sugars_g"]["basis"] == "per 100ml"
    assert nutrient_flags({"category": "Chocolates & Sweets", "sugars_g": 50}) == {}


def test_catalogue_records_carry_flags():
    from backend.core.data_loader import data_loader

    rec = data_loader.search_products(category="Snacks", limit=1)["products"][0]
    assert set(rec["nutrient_flags"]) == {"sugars_g", "saturated_fat_g", "sodium_mg"}


def test_unstated_measurement_basis_is_not_graded():
    """Values with no stated basis cannot be compared with per-100 g thresholds, so no grade is given."""
    from backend.core.nutrition_scoring import assess_general_nutrition

    product = {
        "category": "Snacks", "measurement_basis": "unspecified", "energy_kcal": 500, "sugars_g": 4,
        "saturated_fat_g": 10, "sodium_mg": 900, "carbohydrates_g": 50, "protein_g": 6, "total_fat_g": 28,
    }
    result = assess_general_nutrition(product)
    assert result["grade"] == "Data Contradiction"
    assert "per 100 g" in result["explanation"]
    product["measurement_basis"] = "per 100g"
    assert assess_general_nutrition(product)["grade"] in {"A", "B", "C", "D", "E"}
