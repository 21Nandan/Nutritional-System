"""Nutrition Grade coverage: grade bands, category thresholds, missing and invalid values, and the
Open Food Facts records that used to show no grade (per-serving labels, label units, categories).

All products here are invented; thresholds are read from the category registry, not repeated.
"""

import pytest
from fastapi.testclient import TestClient

from backend.core.nutrition_scoring import assess_general_nutrition, grade_for_score
from backend.core.openfoodfacts import map_off_category_to_eatgood, map_off_product_to_eatgood
from backend.core.standards_registry import CATEGORY_CALIBRATION_SPECS
from backend.main import app

client = TestClient(app)

CALIBRATED = [name for name, spec in CATEGORY_CALIBRATION_SPECS.items() if spec["status"] == "Calibrated"]
# Alcoholic drinks have their own reason (see test_alcoholic_drinks_are_never_graded_or_scored).
UNSUPPORTED = [
    name for name, spec in CATEGORY_CALIBRATION_SPECS.items() if spec["status"] != "Calibrated" and name != "Alcoholic Drinks"
]


def neutral(category, **overrides):
    """A complete record sitting exactly on the category's limits (no penalty, no bonus)."""
    spec = CATEGORY_CALIBRATION_SPECS[category]
    limits = spec["thresholds"]
    record = {
        "category": category, "measurement_basis": spec["reference_basis"],
        "energy_kcal": 100, "carbohydrates_g": 60, "sugars_g": limits["sugars_g"], "total_fat_g": 20,
        "saturated_fat_g": limits["saturated_fat_g"], "sodium_mg": limits["sodium_mg"], "protein_g": 2,
    }
    record.update(overrides)
    return record


def grade(record):
    return assess_general_nutrition(record)


def points(result, nutrient):
    return result["key_contributing_nutrients"][nutrient]["points"]


# ---------- grade bands ----------

@pytest.mark.parametrize(
    ("score", "expected"),
    [(100, "A"), (80, "A"), (79, "B"), (65, "B"), (64, "C"), (48, "C"), (47, "D"), (32, "D"), (31, "E"), (10, "E")],
)
def test_grade_band_boundaries(score, expected):
    assert grade_for_score(score)[0] == expected


def snack(**overrides):
    return {"category": "Snacks", "measurement_basis": "per 100g", "energy_kcal": 450, "carbohydrates_g": 60,
            "sugars_g": 6, "total_fat_g": 20, "saturated_fat_g": 3, "sodium_mg": 300, "protein_g": 4, **overrides}


@pytest.mark.parametrize(
    ("overrides", "score", "expected"),
    [
        ({"sugars_g": 2, "sodium_mg": 100, "saturated_fat_g": 1, "dietary_fibre_g": 3}, 82, "A"),  # 4 bonus points, no penalty
        ({"sugars_g": 2, "sodium_mg": 100, "saturated_fat_g": 1, "trans_fat_g": 0}, 74, "B"),  # 0 g trans fat earns no bonus
        ({"sugars_g": 2, "sodium_mg": 100}, 66, "B"),  # 2 bonus points
        ({}, 50, "C"),  # nothing above or well below a limit
        ({"saturated_fat_g": 5}, 43, "D"),  # saturated fat above its limit: 1 penalty point
        ({"sugars_g": 15}, 36, "D"),  # sugars above the limit: 2 penalty points
        ({"sodium_mg": 900}, 22, "E"),  # sodium above twice the limit: 4 penalty points
    ],
)
def test_products_land_in_each_grade(overrides, score, expected):
    result = grade(snack(**overrides))
    assert (result["general_nutrition_score"], result["grade"]) == (score, expected)
    assert result["grade_reason"] is None


# ---------- category thresholds (at, just above, twice, just above twice) ----------

@pytest.mark.parametrize("category", CALIBRATED)
@pytest.mark.parametrize(("nutrient", "field", "penalties"), [
    ("sugars", "sugars_g", (-2, -4)), ("sodium", "sodium_mg", (-2, -4)), ("saturated_fat", "saturated_fat_g", (-1, -3)),
])
def test_category_threshold_boundaries(category, nutrient, field, penalties):
    spec = CATEGORY_CALIBRATION_SPECS[category]
    limit = spec["thresholds"][field]
    if nutrient == "saturated_fat" and spec["reference_basis"] == "per 100ml":
        assert "saturated_fat" not in grade(neutral(category))["key_contributing_nutrients"]  # not used for drinks
        return
    step = 0.01
    at_limit = grade(neutral(category, **{field: limit}))
    above = grade(neutral(category, **{field: limit + step}))
    twice = grade(neutral(category, **{field: limit * 2}))
    above_twice = grade(neutral(category, **{field: limit * 2 + step}))
    assert all(r["status"] == "Calibrated" for r in (at_limit, above, twice, above_twice))
    assert points(at_limit, nutrient) >= 0
    assert points(above, nutrient) == penalties[0]
    assert points(twice, nutrient) == penalties[0]
    assert points(above_twice, nutrient) == penalties[1]


def test_beverage_limits_are_per_100ml():
    result = grade(neutral("Packaged Beverages", sugars_g=11))
    assert result["reference_basis"].lower().replace(" ", "").endswith("100ml")
    assert points(result, "sugars") == -4  # above 2 x 5 g/100 ml


# ---------- missing values ----------

@pytest.mark.parametrize("category", CALIBRATED)
def test_each_missing_required_value_is_named(category):
    for field in CATEGORY_CALIBRATION_SPECS[category]["mandatory_fields"]:
        result = grade(neutral(category, **{field: None}))
        assert result["grade"] == "Insufficient Data", (category, field)
        assert result["missing_fields"] == [field]
        assert result["grade_reason"].startswith("Not graded:")


def test_missing_required_values_listed_together():
    result = grade(snack(sugars_g=None, sodium_mg=""))
    assert result["grade_reason"] == "Not graded: Total Sugars, Sodium not stated on the label."


def test_undeclared_optional_sodium_earns_no_low_sodium_bonus():
    """Dairy doesn't require sodium. A missing value is not zero, so it earns no 'low sodium' point."""
    declared_low = grade(neutral("Dairy", sodium_mg=50, protein_g=3))
    missing = grade(neutral("Dairy", sodium_mg=None, protein_g=3))
    assert missing["status"] == "Calibrated"
    assert points(declared_low, "sodium") == 1
    assert points(missing, "sodium") == 0
    assert missing["key_contributing_nutrients"]["sodium"]["status"] == "Not declared"
    assert missing["general_nutrition_score"] == declared_low["general_nutrition_score"] - 8


def test_missing_optional_values_never_block_a_grade():
    result = grade(snack(dietary_fibre_g=None, trans_fat_g=None, added_sugars_g=None, protein_g=None))
    assert result["status"] == "Calibrated"


# ---------- invalid data ----------

@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"sugars_g": 70, "carbohydrates_g": 50}, "exceeds Total Carbohydrates"),
        ({"saturated_fat_g": 30, "total_fat_g": 20}, "exceeds Total Fat"),
        ({"energy_kcal": 1200}, "thermodynamic"),
        ({"sodium_mg": 45000}, "pure salt"),
        ({"sugars_g": -1}, "negative"),
        ({"measurement_basis": "unspecified"}, "does not say"),
        ({"measurement_basis": "per serving", "serving_size": None}, "serving size is missing"),
    ],
)
def test_invalid_values_are_not_graded_and_say_why(overrides, fragment):
    result = grade(snack(**overrides))
    assert result["grade"] in ("Data Contradiction", "Insufficient Data")
    assert fragment.lower() in result["grade_reason"].lower()


def test_text_values_that_are_not_numbers_count_as_missing():
    result = grade(snack(sugars_g="n/a"))
    assert result["grade"] == "Insufficient Data"


# ---------- why a product has no grade ----------

@pytest.mark.parametrize("category", UNSUPPORTED)
def test_unsupported_categories_keep_na_with_their_reason(category):
    result = grade(snack(category=category))
    assert result["grade"] == "N/A"
    assert result["grade_reason"] == f"Not graded: no validated grading method for {category} yet."


def test_alcoholic_drinks_are_never_graded_or_scored():
    from backend.core.nutrition_scoring import assess_personalized_suitability
    from backend.core.openfoodfacts import is_alcoholic

    beer = snack(category="Alcoholic Drinks", sugars_g=0.6, sodium_mg=0)
    assert grade(beer)["grade_reason"] == "Not graded: EATGOOD does not grade alcoholic drinks."
    assert assess_personalized_suitability(beer, {"goal": "Balanced Choices"})["personalized_score"] is None
    assert is_alcoholic({"categories_tags": ["en:beverages", "en:alcoholic-beverages", "en:beers"]})
    assert is_alcoholic({"categories_tags": ["en:beverages"], "nutriments": {"alcohol_100g": 7}})
    assert not is_alcoholic({"categories_tags": ["en:beverages", "en:juices"], "nutriments": {"alcohol_100g": 0}})


def test_uncategorised_products_are_graded_with_the_general_method():
    result = grade(snack(category="Uncategorised"))
    assert result["status"] == "Calibrated" and result["category_calibrated"] == "General Packaged Food"
    assert result["grade_reason"] is None
    assert "general limits" in result["method_notice"]


def test_grade_ignores_community_ratings_and_the_visitor_profile():
    base = grade(snack())
    rated = grade(snack(source_indicators={"nutriscore_grade": "A", "nova_group": 1}))
    assert (base["grade"], base["general_nutrition_score"]) == (rated["grade"], rated["general_nutrition_score"])
    header = {"X-Eatgood-Profile": '%7B%22goal%22%3A%22Reduce%20Sugar%22%7D'}
    plain = client.get("/api/products?query=masala").json()["products"][0]
    profiled = client.get("/api/products?query=masala", headers=header).json()["products"][0]
    assert plain["general_grade"] == profiled["general_grade"]


def test_listings_carry_the_reason_for_a_missing_grade():
    items = {p["product_name"]: p for p in client.get("/api/products?limit=100").json()["products"]}
    assert items["Partial Label Test"]["grade_reason"] == (
        "Not graded: Total Sugars, Saturated Fat, Sodium not stated on the label."
    )
    assert items["Masala Bhujia Test"]["grade_reason"] is None
    assert items["Masala Bhujia Test"]["grade_note"] is None
    chocolate = items["Milk Chocolate Bar Test"]  # graded with EATGOOD's own method, and labelled
    assert (chocolate["general_grade"], chocolate["grade_reason"]) == ("E", None)
    assert chocolate["grade_note"] == "EATGOOD's own method, not an official grade"


# ---------- Open Food Facts records that used to show no grade ----------

PER_100G = {"energy-kcal_100g": 480, "carbohydrates_100g": 62, "sugars_100g": 4, "fat_100g": 22,
            "saturated-fat_100g": 9, "proteins_100g": 7, "sodium_100g": 0.6}


def off(nutriments, tags=("en:snacks", "en:salty-snacks"), name="Spiced Rice Crisps", **extra):
    return map_off_product_to_eatgood("2000000000990", {
        "code": "2000000000990", "product_name": name, "brands": "Test Brand", "categories_tags": list(tags),
        "nutriments": nutriments, **extra,
    })


def test_per_serving_label_uses_the_per_100g_values_without_converting_twice():
    """Labels stated per serving: Open Food Facts also gives per-100 g values. Before, these were
    labelled 'per serving' and multiplied again (energy 1600 kcal/100 g, a contradiction)."""
    product = off({**PER_100G, "energy-kcal": 144, "sugars": 1.2}, nutrition_data_per="serving", serving_quantity=30)
    assert product["measurement_basis"] == "per 100g"
    assert (product["energy_kcal"], product["sugars_g"], product["sodium_mg"]) == (480, 4, 600)
    result = grade(product)
    assert result["status"] == "Calibrated" and result["grade"] in "ABCDE"


def test_label_values_per_serving_are_converted_with_the_stated_serving_size():
    product = off({"energy-kcal": 120, "carbohydrates": 15, "sugars": 1, "fat": 5, "saturated-fat": 2,
                   "proteins": 2, "sodium": 0.1}, nutrition_data_per="serving", serving_quantity=25)
    assert product["measurement_basis"] == "per serving"
    result = grade(product)
    assert result["status"] == "Calibrated"
    assert result["key_contributing_nutrients"]["sodium"]["value"] == 400  # 100 mg per 25 g


def test_unknown_serving_size_is_never_assumed():
    product = off({"energy-kcal": 120, "sugars": 1, "saturated-fat": 2, "sodium": 0.1}, nutrition_data_per="serving")
    assert product["serving_size"] is None
    result = grade(product)
    assert result["grade"] == "Data Contradiction"
    assert "serving size is missing" in result["grade_reason"]


def test_sodium_typed_in_mg_is_read_in_mg():
    """The _100g value is in grams whatever unit the label used; the typed value uses its own unit."""
    assert off({**PER_100G, "sodium_unit": "mg", "sodium_value": 600})["sodium_mg"] == 600
    only_typed = {k: v for k, v in PER_100G.items() if k != "sodium_100g"}
    assert off({**only_typed, "sodium_value": 450, "sodium_unit": "mg"})["sodium_mg"] == 450
    assert off({**only_typed, "salt_value": 1.5, "salt_unit": "g"})["sodium_mg"] == 600
    assert off({**only_typed, "sodium_value": 450})["sodium_mg"] is None  # unit unknown: not guessed


def test_energy_in_kj_is_never_read_as_kcal():
    without_kcal = {k: v for k, v in PER_100G.items() if not k.startswith("energy")}
    product = off({**without_kcal, "energy_100g": 2008, "energy_unit": "kcal", "energy_value": 480})
    assert product["energy_kcal"] == pytest.approx(480, abs=0.5)
    assert grade(product)["status"] == "Calibrated"
    assert off({**without_kcal, "energy_value": 480, "energy_unit": "kcal"})["energy_kcal"] == 480


def test_products_without_categories_use_an_unambiguous_product_name():
    noodles = off(PER_100G, tags=(), name="Masala Instant Noodles")
    assert noodles["category"] == "Instant Foods"
    assert grade(noodles)["status"] == "Calibrated"
    assert off(PER_100G, tags=(), name="Salted Potato Chips")["category"] == "Snacks"


@pytest.mark.parametrize("name", ["Oats Cookies", "Milk Chocolate", "Cheese Spread", "Fruit & Nut", "Masala Munch"])
def test_ambiguous_names_are_not_categorised(name):
    product = off(PER_100G, tags=(), name=name)
    assert product["category"] == "Uncategorised"
    assert grade(product)["category_calibrated"] == "General Packaged Food"


def test_tags_win_over_the_product_name():
    assert off(PER_100G, tags=("en:biscuits",), name="Noodle Shaped Biscuits")["category"] == "Biscuits & Bakery"


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        (["en:spreads", "en:nut-butters", "en:peanut-butters"], "Condiments & Spreads"),  # not dairy butter
        (["en:dairies", "en:butters"], "Dairy"),
        (["en:meals"], "Instant Foods"),
        (["en:meal-replacements"], "Uncategorised"),
        (["en:plant-based-foods", "en:cereals-and-potatoes", "en:cereals-and-their-products", "en:rices"], "Uncategorised"),
        (["en:cereals-and-their-products", "en:breakfast-cereals"], "Breakfast Cereals"),
        (["en:cereals-and-their-products", "en:breakfast-cereals", "en:rolled-oats"], "Breakfast Cereals"),
        (["en:fermented-milk-products", "en:dahi"], "Dairy"),
        # Milk drinks are Dairy, not soft drinks; a "dairy by-products" tag doesn't make crisps Dairy.
        (["en:beverages", "en:dairies", "en:dairy-drinks", "en:fermented-milk-drinks", "en:yogurt-drinks"], "Dairy"),
        (["en:beverages", "en:dairies", "en:lassi"], "Dairy"),
        (["en:dairies", "en:salty-snacks", "en:potato-crisps", "en:barbecue-crisps", "en:dairy-by-products"], "Snacks"),
    ],
)
def test_category_tags(tags, expected):
    assert map_off_category_to_eatgood(None, tags) == expected


def test_energy_dense_foods_and_drinks_take_a_penalty_point():
    assert "energy" not in grade(snack(energy_kcal=450))["key_contributing_nutrients"]
    dense = grade(snack(energy_kcal=451))
    assert dense["key_contributing_nutrients"]["energy"]["points"] == -1
    assert dense["general_nutrition_score"] == 43
    drink = {"category": "Packaged Beverages", "measurement_basis": "per 100ml", "energy_kcal": 71, "sugars_g": 4, "sodium_mg": 10}
    assert grade(drink)["key_contributing_nutrients"]["energy"]["points"] == -1


def test_bonuses_cannot_cancel_penalties_but_clean_products_keep_them_all():
    # Sugar just over the limit (2 penalty points) with 4 bonus points: only 3 count, 50 - 14 + 24 = 60.
    capped = grade(snack(sugars_g=12, sodium_mg=100, saturated_fat_g=1, dietary_fibre_g=6))
    assert (capped["penalty_points"], capped["bonus_points"], capped["general_nutrition_score"]) == (2, 3, 60)
    # Nothing over a limit: all 6 bonus points count (sugar, sodium, saturated fat 1 each, fibre 3), 50 + 48 = 98.
    clean = grade(snack(sugars_g=2, sodium_mg=100, saturated_fat_g=1, dietary_fibre_g=6))
    assert (clean["penalty_points"], clean["bonus_points"], clean["general_nutrition_score"]) == (0, 6, 98)
