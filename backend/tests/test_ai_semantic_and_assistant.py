from fastapi.testclient import TestClient

from backend.core.semantic_search import parse_semantic_intent
from backend.main import app

client = TestClient(app)

def test_semantic_intent_parser():
    # 1. Less salty snacks
    intent1 = parse_semantic_intent("Less salty snacks for evening")
    assert intent1["category"] == "Snacks"
    assert "max_sodium" in intent1["nutrient_filters"]
    assert intent1["nutrient_filters"]["max_sodium"] <= 350.0

    # 2. Breakfast cereal with more fibre
    intent2 = parse_semantic_intent("Breakfast cereal with more fibre")
    assert intent2["category"] == "Breakfast Cereals"
    assert "min_fibre" in intent2["nutrient_filters"]
    assert intent2["nutrient_filters"]["min_fibre"] >= 5.0

    # 3. High protein snacks without peanuts
    intent3 = parse_semantic_intent("High protein snacks without peanuts")
    assert intent3["category"] == "Snacks"
    assert "min_protein" in intent3["nutrient_filters"]
    assert "peanuts" in intent3["excluded_allergens"]
    assert "peanut" in intent3["forbidden_terms"]

def test_grounded_assistant_diabetes_query():
    # Test catalogue: Glucose Biscuits Test has 25 g sugars per 100 g
    payload = {
        "product_id": "OFF_2000000000060",
        "question": "Is this suitable for a diabetic?"
    }
    res = client.post("/api/assistant/ask", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "Total Sugars" in str(data["evidence_citations"])
    assert "clinical medical advice" in data["answer"].lower()

def test_grounded_assistant_sodium_query():
    # Test catalogue: Masala Bhujia Test, sodium above the snack limit
    payload = {
        "product_id": "OFF_2000000000015",
        "question": "Is this high in sodium for blood pressure?"
    }
    res = client.post("/api/assistant/ask", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "Sodium" in str(data["evidence_citations"])

def test_grounded_assistant_not_found():
    payload = {
        "product_id": "NON_EXISTENT_ID_99999",
        "question": "What is the protein content?"
    }
    res = client.post("/api/assistant/ask", json=payload)
    assert res.status_code == 404
