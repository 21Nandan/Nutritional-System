"""
Rule-based assistant answers, semantic search intent and results, and claim checks.
"""

import json
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from backend.core.assistant import answer_product_question
from backend.core.claims_detector import evaluate_claims
from backend.core.data_loader import data_loader
from backend.core.semantic_search import execute_semantic_search, parse_semantic_intent
from backend.main import app

client = TestClient(app)

HIGH_SUGAR = {
    "product_id": "T1", "product_name": "Sweet Bar", "brand": "B", "category": "Snacks",
    "measurement_basis": "per 100g", "energy_kcal": 480, "sugars_g": 32, "sodium_mg": 700,
    "saturated_fat_g": 9, "protein_g": 3, "dietary_fibre_g": 1, "carbohydrates_g": 70, "total_fat_g": 20,
    "ingredients": "Sugar, wheat flour, peanuts", "allergens_declared": "Gluten, Peanuts",
}
LOW_SUGAR = {**HIGH_SUGAR, "product_id": "T2", "sugars_g": 2, "sodium_mg": 100, "protein_g": 14, "dietary_fibre_g": 8}


@pytest.mark.parametrize(
    "question,expect",
    [
        ("Is this suitable for a diabetic?", "sugar"),
        ("Is this high in sodium for blood pressure?", "sodium"),
        ("Can I eat this with a peanut allergy?", "peanut"),
        ("Why did this get its current score?", "grade"),
        ("Is it good for protein after the gym?", "protein"),
        ("What is the weather?", ""),
    ],
)
def test_assistant_answers_every_question_type(question, expect):
    result = answer_product_question(HIGH_SUGAR, question, {"goal": "Reduce Sugar", "dietary_preference": "No preference", "allergens_to_avoid": "Peanuts"})
    assert result["answer"]
    assert expect in result["answer"].lower()
    assert result["grounded_metrics"]["sugars_g"] == 32


def test_assistant_low_sugar_and_high_protein_branches():
    for q in ["diabetic?", "sodium?", "protein for muscle?"]:
        assert answer_product_question(LOW_SUGAR, q)["answer"]


def test_assistant_endpoint_uses_request_profile():
    header = {"X-Eatgood-Profile": quote(json.dumps({"allergens_to_avoid": "Milk"}))}
    pid = data_loader.products_df[data_loader.products_df["allergens_declared"].fillna("").str.contains("Milk")].iloc[0]["product_id"]
    res = client.post("/api/assistant/ask", json={"product_id": pid, "question": "Can I eat this with a dairy allergy?"}, headers=header)
    assert res.status_code == 200
    assert res.json()["grounded_metrics"]["personalized_score"] == 0


def test_assistant_unknown_product_is_404():
    res = client.post("/api/assistant/ask", json={"product_id": "NOPE", "question": "why?"})
    assert res.status_code == 404


@pytest.mark.parametrize(
    "query,category,descriptions,allergens",
    [
        ("less salty snacks", "Snacks", True, []),
        ("high protein breakfast cereal", "Breakfast Cereals", True, []),
        ("low sugar drinks", "Packaged Beverages", True, []),
        ("biscuits without peanuts", "Biscuits & Bakery", False, ["peanuts"]),
    ],
)
def test_semantic_intent(query, category, descriptions, allergens):
    intent = parse_semantic_intent(query)
    assert intent["category"] == category
    assert bool(intent["nutrient_descriptions"]) == descriptions
    for a in allergens:
        assert a in intent["excluded_allergens"]


def test_semantic_search_filters_and_explains():
    res = execute_semantic_search("less salty snacks", data_loader.products_df, {"allergens_to_avoid": ""}, limit=10)
    assert res["total"] > 0
    for p in res["products"]:
        assert p["category"] == "Snacks"
        assert p["semantic_reason"]
        assert "nutrient_flags" in p


def test_semantic_search_category_that_does_not_exist_returns_nothing_not_everything():
    df = data_loader.products_df[data_loader.products_df["category"] != "Packaged Beverages"]
    res = execute_semantic_search("low sugar drinks", df, {"allergens_to_avoid": ""}, limit=10)
    assert res["total"] == 0


def test_semantic_search_excludes_user_allergens():
    res = execute_semantic_search("high protein snacks", data_loader.products_df, {"allergens_to_avoid": "Milk"}, limit=50)
    assert all("milk" not in str(p.get("allergens_declared") or "").lower() for p in res["products"])


def test_catalogue_endpoint_routes_natural_language_to_semantic_search():
    res = client.get("/api/products?query=less%20salty%20snacks&limit=5").json()
    assert "interpreted_intent" in res


@pytest.mark.parametrize(
    "claim,product,expected_fragment",
    [
        ("Low Fat", {"total_fat_g": 20.0, "measurement_basis": "per 100g", "category": "Snacks"}, "inconsistent"),
        ("Low Fat", {"total_fat_g": 1.0, "measurement_basis": "per 100g", "category": "Snacks"}, "consistent with"),
        ("High Protein", {"protein_g": 4.0, "energy_kcal": 500, "measurement_basis": "per 100g", "category": "Snacks"}, "inconsistent"),
        ("Zero Sugar", {"sugars_g": None, "measurement_basis": "per 100g", "category": "Snacks"}, "insufficient"),
    ],
)
def test_claim_checks(claim, product, expected_fragment):
    result = evaluate_claims(claim, product)[0]
    assert expected_fragment in result["status"].lower(), result
