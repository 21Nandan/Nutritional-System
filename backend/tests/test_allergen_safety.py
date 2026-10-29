"""
EATGOOD — Allergen safety invariant.

1. An allergen conflict overrides the score on every path: catalogue product, barcode
   (catalogue, contribution, Open Food Facts), manual entry and comparison.
2. Alternatives never include a product that conflicts with the user's allergens, or one
   whose allergen information is missing while the user has allergens to avoid.
3. The allergen matcher handles synonyms, regional names, hidden sources and "may contain",
   without obvious false positives.
"""

import json
from unittest.mock import patch
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from backend.core.allergen_engine import MAJOR_ALLERGENS, analyze_allergens
from backend.core.nutrition_scoring import run_full_product_assessment
from backend.main import app
from backend.tests import catalogue_fixture as fx

client = TestClient(app)


def profile_header(allergens: str) -> dict:
    return {"X-Eatgood-Profile": quote(json.dumps({"allergens_to_avoid": allergens, "goal": "Balanced Choices"}))}


def assert_overridden(assessment: dict, allergen: str) -> None:
    assert assessment["safety_override"]["allergen_conflict"] is True
    assert allergen in assessment["safety_override"]["allergens"]
    assert assessment["layer2_personalized"]["personalized_score"] == 0
    assert assessment["layer2_personalized"]["has_critical_allergen_conflict"] is True


def first_catalogue_product_declaring(allergen_word: str) -> dict:
    return next(p for p in fx.PRODUCTS if allergen_word.lower() in str(p["allergens_declared"] or "").lower())


# ---------- 1. Override on every path ----------

def test_catalogue_product_path():
    product = first_catalogue_product_declaring("Milk")
    data = client.get(f"/api/products/{product['product_id']}", headers=profile_header("Milk")).json()
    assert_overridden(data, "Milk")


def test_barcode_catalogue_path():
    product = first_catalogue_product_declaring("Peanuts")
    data = client.get(f"/api/products/barcode/{product['barcode']}", headers=profile_header("Peanuts")).json()
    assert_overridden(data["assessment"], "Peanuts")


def test_barcode_open_food_facts_path():
    off_product = {
        "product_id": "OFF_5000000000001",
        "barcode": "5000000000001",
        "product_name": "Imported Biscuits",
        "brand": "X",
        "category": "Biscuits & Bakery",
        "measurement_basis": "per 100g",
        "energy_kcal": 480.0,
        "sugars_g": 20.0,
        "sodium_mg": 300.0,
        "saturated_fat_g": 8.0,
        "ingredients": "Wheat flour, sugar, palm oil, egg powder",
        "allergens_declared": "Gluten, Eggs",
    }
    with patch("backend.products.fetch_product_from_openfoodfacts", return_value={"status": "success", "product": off_product}):
        data = client.get("/api/products/barcode/5000000000001", headers=profile_header("Eggs")).json()
    assert_overridden(data["assessment"], "Eggs")


def test_barcode_user_contribution_path():
    payload = {
        "barcode": "8909999000017",
        "product_name": "Home Brand Chikki",
        "category": "Chocolates & Sweets",
        "energy_kcal": 500,
        "sugars_g": 40,
        "sodium_mg": 50,
        "saturated_fat_g": 5,
        "ingredients": "Jaggery, groundnuts",
        "allergens_declared": "",
    }
    assert client.post("/api/products/contribute", json=payload).status_code == 200
    data = client.get("/api/products/barcode/8909999000017", headers=profile_header("Peanuts")).json()
    assert_overridden(data["assessment"], "Peanuts")


def test_manual_entry_path():
    payload = {
        "product_name": "Scanned Wafer",
        "category": "Biscuits & Bakery",
        "energy_kcal": 520,
        "sugars_g": 30,
        "sodium_mg": 200,
        "saturated_fat_g": 12,
        "ingredients": "Refined wheat flour (maida), sugar, milk solids, soya lecithin",
        "allergens_declared": "",
    }
    data = client.post("/api/products/assess", json=payload, headers=profile_header("Soy")).json()
    assert_overridden(data, "Soy")


def test_compare_path():
    milk = first_catalogue_product_declaring("Milk")
    other = next(p["product_id"] for p in fx.PRODUCTS if p["product_id"] != milk["product_id"])
    data = client.get(f"/api/compare?ids={milk['product_id']},{other}", headers=profile_header("Milk")).json()
    row = next(p for p in data["products_compared"] if p["product_id"] == milk["product_id"])
    assert row["has_allergen_conflict"] is True
    assert row["personalized_score"] == 0


def test_saved_product_reassessment_path():
    """Saved items live in the browser and are re-assessed via /api/products/{id} or /assess; both override."""
    product = first_catalogue_product_declaring("Soy")
    data = client.get(f"/api/products/{product['product_id']}", headers=profile_header("soya")).json()
    assert_overridden(data, "Soy")


# ---------- 2. Alternatives never contain the user's allergen ----------

@pytest.mark.parametrize("allergen", ["Milk", "Gluten", "Peanuts", "Tree Nuts", "Soy"])
def test_alternatives_exclude_user_allergen_for_every_category(allergen):
    header = profile_header(allergen)
    profile = {"allergens_to_avoid": allergen, "goal": "Balanced Choices", "dietary_preference": "No preference"}
    for category in {p["category"] for p in fx.PRODUCTS}:
        pid = next(p["product_id"] for p in fx.PRODUCTS if p["category"] == category)
        alts = client.get(f"/api/alternatives/{pid}?limit=12", headers=header).json()["alternatives"]
        for alt in alts:
            assessment = run_full_product_assessment(fx.BY_BARCODE[alt["product_id"].removeprefix("OFF_")], profile)
            assert assessment["safety_override"]["allergen_conflict"] is False, (allergen, alt["product_id"])
            assert assessment["safety_override"]["allergen_check_incomplete"] is False, (allergen, alt["product_id"])


def test_alternatives_without_profile_header_use_no_one_elses_allergens():
    data = client.get("/api/alternatives/OFF_2000000000015").json()
    assert data["profile_source"] == "default"


# ---------- 3. Matcher accuracy ----------

@pytest.mark.parametrize(
    "ingredients,declared,user,expected_group",
    [
        ("Wheat flour, sugar", "", "Gluten", "Gluten"),
        ("Maida, palm oil", "", "Gluten", "Gluten"),
        ("Suji, ghee", "", "Milk", "Milk"),
        ("Sugar, whey powder", "", "Milk", "Milk"),
        ("Sugar, sodium caseinate", "", "Milk", "Milk"),
        ("Khoya, sugar", "", "Milk", "Milk"),
        ("Roasted groundnuts, salt", "", "Peanuts", "Peanuts"),
        ("Kaju, badam, sugar", "", "Tree Nuts", "Tree Nuts"),
        ("Rice", "Contains: Egg", "Eggs", "Eggs"),
        ("Rice", "Contains almonds", "Tree Nuts", "Tree Nuts"),
        ("Sugar, emulsifier (INS 322)", "", "Soy", "Soy"),
        ("Dried apricot, sodium metabisulphite", "", "Sulphites", "Sulphites"),
        ("Gingelly oil, salt", "", "Sesame", "Sesame"),
    ],
)
def test_detects_synonyms_regional_names_and_hidden_sources(ingredients, declared, user, expected_group):
    result = analyze_allergens(ingredients, declared, [user])
    assert result["has_critical_conflict"], (ingredients, declared)
    assert expected_group in [c["allergen"] for c in result["user_conflicts"]]


def test_may_contain_is_a_separate_level_and_still_a_conflict():
    result = analyze_allergens("Rice flour, sugar", "Contains: Milk. May contain traces of peanuts", ["Peanuts"])
    conflict = result["user_conflicts"][0]
    assert conflict["allergen"] == "Peanuts"
    assert conflict["status"] == "Advisory Warning (May Contain)"
    milk = next(a for a in result["detected_allergens"] if a["allergen"] == "Milk")
    assert milk["status"] == "Confirmed Allergen"


def test_generic_may_contain_nuts_warns_for_both_nut_groups():
    result = analyze_allergens("Oats", "May contain nuts", ["Peanuts", "Tree Nuts"])
    assert {c["allergen"] for c in result["user_conflicts"]} == {"Peanuts", "Tree Nuts"}


@pytest.mark.parametrize(
    "ingredients,declared,user",
    [
        ("Coconut milk, sugar", "", "Milk"),
        ("Cocoa butter, sugar", "", "Milk"),
        ("Peanut butter", "", "Milk"),
        ("Buckwheat flour", "", "Gluten"),
        ("Eggplant, oil", "", "Eggs"),
        ("Sunflower lecithin, sugar", "", "Soy"),
        ("Rice", "Milk, Tree Nuts (Almonds, Cashews)", "Peanuts"),
        ("Nutmeg, coconut", "", "Tree Nuts"),
    ],
)
def test_avoids_common_false_positives(ingredients, declared, user):
    result = analyze_allergens(ingredients, declared, [user])
    assert not result["has_critical_conflict"], (ingredients, declared, result["user_conflicts"])


def test_custom_allergen_from_profile_is_matched():
    result = analyze_allergens("Mustard seeds, salt", "", ["Mustard"])
    assert result["has_critical_conflict"]
    assert result["user_conflicts"][0]["allergen"] == "Mustard"


def test_missing_allergen_information_is_never_safe():
    result = analyze_allergens("", "", ["Milk"])
    assert result["allergen_status_unknown"] is True
    assert result["user_allergen_check_incomplete"] is True


def test_every_group_name_is_matched_when_declared():
    for group in MAJOR_ALLERGENS:
        result = analyze_allergens("", f"Contains: {group}", [group])
        assert result["has_critical_conflict"], group


def test_compare_reports_unknown_allergen_information_and_nutrient_flags():
    """The comparison must be able to tell "no alerts" apart from "allergen information missing"."""
    data = client.get("/api/compare?ids=OFF_2000000000015,OFF_2000000000114", headers=profile_header("Milk")).json()
    unknown = {row["product_name"]: row["allergen_status_unknown"] for row in data["products_compared"]}
    assert unknown == {"Masala Bhujia Test": False, "Mystery Snack Test": True}
    for row in data["products_compared"]:
        assert isinstance(row["allergen_status_unknown"], bool)
        assert isinstance(row["user_allergen_check_incomplete"], bool)
        assert set(row["nutrient_flags"]) <= {"sugars_g", "saturated_fat_g", "sodium_mg"}
