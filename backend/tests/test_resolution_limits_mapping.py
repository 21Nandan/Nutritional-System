"""
Product resolution paths, rate-limit enforcement, configuration validation,
per-goal personal scoring and Open Food Facts mapping.
"""

import importlib
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from backend.core import rate_limiter as rl
from backend.core.nutrition_scoring import assess_personalized_suitability
from backend.core.openfoodfacts import map_off_category_to_eatgood, map_off_product_to_eatgood
from backend.main import app
from backend.products import OpenFoodFactsUnavailable, resolve_product

client = TestClient(app)


# ---------- product resolution ----------

def test_resolve_catalogue_id_and_barcode():
    assert resolve_product("IND_PKG_001")["product_name"] == "Haldiram's Bhujia Sev"
    assert resolve_product("8903585650756")["product_id"] == "IND_PKG_001"


def test_resolve_unknown_non_numeric_id_is_none():
    assert resolve_product("NOT_A_PRODUCT") is None


def test_resolve_off_id_uses_open_food_facts_and_reports_failures():
    with patch("backend.products.fetch_product_from_openfoodfacts", return_value={"status": "not_found"}):
        assert resolve_product("OFF_4000000000001") is None
    failure = {"status": "error", "error_code": "OFF_TIMEOUT", "http_status": 504, "message": "slow", "technical_detail": "t"}
    with patch("backend.products.fetch_product_from_openfoodfacts", return_value=failure):
        with pytest.raises(OpenFoodFactsUnavailable):
            resolve_product("OFF_4000000000002")
        res = client.get("/api/products/OFF_4000000000003")
        assert res.status_code == 504
        assert res.json()["detail"]["error_code"] == "OFF_TIMEOUT"


def test_open_food_facts_results_are_cached_including_not_found():
    calls = []

    def fake(code):
        calls.append(code)
        return {"status": "not_found"}

    with patch("backend.products.fetch_product_from_openfoodfacts", side_effect=fake):
        assert client.get("/api/products/barcode/4000000000019").status_code == 404
        assert client.get("/api/products/barcode/4000000000019").status_code == 404
    assert calls == ["4000000000019"]


def test_user_contribution_resolves_by_prefixed_id():
    payload = {"barcode": "8901234500016", "product_name": "Test Rusk", "category": "Biscuits & Bakery", "sugars_g": 10}
    assert client.post("/api/products/contribute", json=payload).status_code == 200
    product = resolve_product("USER_SUB_8901234500016")
    assert product["data_confidence_status"] == "User submitted (not reviewed)"
    assert resolve_product("8901234500016")["product_name"] == "Test Rusk"
    assert resolve_product("USER_SUB_0000000000000") is None


def test_invalid_barcode_is_400():
    res = client.get("/api/products/barcode/12AB")
    assert res.status_code == 400
    assert res.json()["detail"]["error_code"] == "INVALID_BARCODE"


def test_compare_requires_two_to_four_products():
    assert client.get("/api/compare?ids=IND_PKG_001").status_code == 400
    assert client.get("/api/compare?ids=IND_PKG_001,NOPE").status_code == 404


# ---------- rate limiting ----------

def test_enforce_rate_limit_raises_429_with_retry_after(monkeypatch):
    monkeypatch.setattr(rl, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rl, "rate_limiter", rl.SlidingWindowRateLimiter())
    request = Request({"type": "http", "headers": [], "client": ("10.1.1.1", 1)})
    for _ in range(rl.RATE_LIMIT_CONTRIB_RPM):
        rl.enforce_rate_limit(request, "contribution")
    with pytest.raises(HTTPException) as exc:
        rl.enforce_rate_limit(request, "contribution")
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_rate_limiter_cleans_idle_keys():
    limiter = rl.SlidingWindowRateLimiter()
    limiter.is_rate_limited("k", 5)
    limiter.cleanup_stale_keys(max_idle_seconds=-1)
    assert limiter._history == {}


# ---------- configuration ----------

@pytest.mark.parametrize(
    "env,value,message",
    [
        ("EATGOOD_ENV", "staging", "EATGOOD_ENV"),
        ("EATGOOD_RATE_LIMIT", "maybe", "true/false"),
        ("RATE_LIMIT_OFF_SEARCH_RPM", "lots", "integer"),
        ("OFF_TIMEOUT_SECONDS", "slow", "number"),
        ("EATGOOD_CORS_ORIGINS", "*", "explicit origins"),
    ],
)
def test_invalid_configuration_fails_at_startup(monkeypatch, env, value, message):
    import backend.config as config

    monkeypatch.setenv(env, value)
    with pytest.raises(RuntimeError, match=message):
        importlib.reload(config)
    monkeypatch.delenv(env)
    importlib.reload(config)


def test_boolean_and_cors_configuration(monkeypatch):
    import backend.config as config

    monkeypatch.setenv("EATGOOD_RATE_LIMIT", "no")
    monkeypatch.setenv("EATGOOD_CORS_ORIGINS", "https://a.example, https://b.example")
    importlib.reload(config)
    assert config.RATE_LIMIT_ENABLED is False
    assert config.CORS_ORIGINS == ["https://a.example", "https://b.example"]
    monkeypatch.delenv("EATGOOD_RATE_LIMIT")
    monkeypatch.delenv("EATGOOD_CORS_ORIGINS")
    importlib.reload(config)


# ---------- personal scoring per goal ----------

BASE = {"category": "Snacks", "measurement_basis": "per 100g", "energy_kcal": 450, "saturated_fat_g": 5,
        "ingredients": "Rice flour, oil", "allergens_declared": "None declared"}


@pytest.mark.parametrize(
    "goal,good,bad",
    [
        ("Reduce Sugar", {"sugars_g": 1, "sodium_mg": 300}, {"sugars_g": 30, "sodium_mg": 300}),
        ("Reduce Sodium", {"sugars_g": 5, "sodium_mg": 100}, {"sugars_g": 5, "sodium_mg": 1200}),
        ("Increase Fibre", {"sugars_g": 5, "sodium_mg": 300, "dietary_fibre_g": 9}, {"sugars_g": 5, "sodium_mg": 300, "dietary_fibre_g": 0.5}),
        ("Increase Protein", {"sugars_g": 5, "sodium_mg": 300, "protein_g": 15}, {"sugars_g": 5, "sodium_mg": 300, "protein_g": 1}),
        ("Balanced Choices", {"sugars_g": 2, "sodium_mg": 100, "saturated_fat_g": 1}, {"sugars_g": 35, "sodium_mg": 1500, "saturated_fat_g": 15}),
    ],
)
def test_each_goal_rewards_good_and_penalises_bad(goal, good, bad):
    profile = {"goal": goal, "dietary_preference": "No preference", "allergens_to_avoid": ""}
    good_score = assess_personalized_suitability({**BASE, **good}, profile)["personalized_score"]
    bad_score = assess_personalized_suitability({**BASE, **bad}, profile)["personalized_score"]
    assert good_score > bad_score


@pytest.mark.parametrize(
    "pref,ingredients",
    [("Vegetarian", "Wheat, gelatin"), ("Vegan", "Wheat, honey"), ("Lactose avoidance", "Wheat, milk solids")],
)
def test_dietary_preference_conflicts(pref, ingredients):
    profile = {"goal": "Balanced Choices", "dietary_preference": pref, "allergens_to_avoid": ""}
    result = assess_personalized_suitability({**BASE, "sugars_g": 5, "sodium_mg": 300, "ingredients": ingredients}, profile)
    assert result["preference_conflict"] is True


def test_missing_sugar_and_sodium_means_no_score_not_zero():
    profile = {"goal": "Balanced Choices", "dietary_preference": "No preference", "allergens_to_avoid": ""}
    result = assess_personalized_suitability({**BASE, "sugars_g": None, "sodium_mg": None}, profile)
    assert result["personalized_score"] is None
    assert result["has_insufficient_data"] is True


# ---------- Open Food Facts mapping ----------

@pytest.mark.parametrize(
    "categories,expected",
    [
        ("Beverages, Juices", "Packaged Beverages"),
        ("Breakfast cereals", "Breakfast Cereals"),
        ("Biscuits", "Biscuits & Bakery"),
        ("Chocolates", "Chocolates & Sweets"),
        ("Instant noodles", "Instant Foods"),
        ("Cheeses", "Dairy"),
        ("Tomato ketchup", "Condiments & Spreads"),
        ("Basmati rice", "Uncategorised"),
    ],
)
def test_off_category_mapping_never_guesses(categories, expected):
    assert map_off_category_to_eatgood(categories, []) == expected


def test_off_unknown_category_gets_no_grade():
    from backend.core.nutrition_scoring import assess_general_nutrition

    product = map_off_product_to_eatgood("4000000000026", {"code": "4000000000026", "product_name": "Rice", "categories": "Rice",
                                                           "nutriments": {"energy-kcal_100g": 350, "sugars_100g": 0.2, "sodium_100g": 0.01, "saturated-fat_100g": 0.1}})
    assert product["category"] == "Uncategorised"
    assert assess_general_nutrition(product)["grade"] == "N/A"


def test_off_traces_become_may_contain():
    product = map_off_product_to_eatgood("4000000000033", {"code": "4000000000033", "product_name": "Oat bar", "categories": "Snacks",
                                                           "allergens_tags": ["en:gluten"], "traces_tags": ["en:nuts", "en:milk"], "nutriments": {}})
    assert product["allergens_declared"] == "Gluten. May contain: Nuts, Milk"
    from backend.core.allergen_engine import analyze_allergens

    result = analyze_allergens("", product["allergens_declared"], ["Peanuts"])
    assert result["user_conflicts"][0]["status"] == "Advisory Warning (May Contain)"


def test_off_salt_only_is_converted_and_kj_only_energy_is_converted():
    product = map_off_product_to_eatgood("4000000000040", {"code": "4000000000040", "product_name": "Crackers", "categories": "Crackers",
                                                           "nutriments": {"salt_100g": 1.5, "energy-kj_100g": 2000}})
    assert product["sodium_mg"] == pytest.approx(600, abs=1)
    assert product["energy_kcal"] == pytest.approx(478, abs=2)


@pytest.mark.parametrize("categories", ["Chocolates", "Beef steak", "Watermelon"])
def test_off_category_mapping_uses_whole_words(categories):
    assert map_off_category_to_eatgood(categories, []) != "Packaged Beverages"


LAYS_TAGS = [
    "en:plant-based-foods-and-beverages", "en:plant-based-foods", "en:snacks", "en:salty-snacks",
    "en:appetizers", "en:chips-and-fries", "en:crisps", "en:potato-crisps",
]


def test_off_umbrella_foods_and_beverages_category_does_not_make_crisps_a_drink():
    """Real Open Food Facts tags for Lay's Classic: the umbrella "...foods-and-beverages" tag comes first."""
    assert map_off_category_to_eatgood(None, LAYS_TAGS) == "Snacks"
    assert map_off_category_to_eatgood("Plant-based foods and beverages, Plant-based foods, Snacks, Crisps", []) == "Snacks"
    product = map_off_product_to_eatgood("0060410025604", {
        "code": "0060410025604", "product_name": "Lay's classic", "brands": "Lay's",
        "categories_tags": LAYS_TAGS, "serving_size": "28 g", "nutriments": {"energy-kcal_100g": 536},
    })
    assert product["category"] == "Snacks"
    assert product["measurement_basis"] == "per 100g"
    assert product["serving_size_unit"] == "g"


def test_off_most_specific_category_wins():
    juice = ["en:plant-based-foods-and-beverages", "en:beverages", "en:plant-based-beverages",
             "en:fruit-based-beverages", "en:juices-and-nectars", "en:fruit-juices"]
    assert map_off_category_to_eatgood(None, juice) == "Packaged Beverages"
    assert map_off_category_to_eatgood("Snacks, Sweet snacks, Biscuits and cakes, Biscuits", []) == "Biscuits & Bakery"
