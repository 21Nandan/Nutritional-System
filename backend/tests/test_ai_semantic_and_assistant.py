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

def test_semantic_search_api_endpoint():
    res = client.get("/api/search/semantic?q=Less+salty+snacks+for+evening&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "interpreted_intent" in data
    assert data["interpreted_intent"]["category"] == "Snacks"
    assert len(data["products"]) > 0
    # Every returned product has semantic score and reason
    first = data["products"][0]
    assert "semantic_score" in first
    assert "semantic_reason" in first

def test_semantic_search_allergen_exclusion():
    res = client.get("/api/search/semantic?q=Snacks+without+peanuts&limit=10")
    assert res.status_code == 200
    data = res.json()
    for p in data["products"]:
        ings = str(p.get("ingredients", "")).lower()
        allgs = str(p.get("allergens_declared", "")).lower()
        assert "peanut" not in ings
        assert "peanut" not in allgs

def test_grounded_assistant_diabetes_query():
    # Cadbury Oreo IND_PKG_564 has high sugar
    payload = {
        "product_id": "IND_PKG_564",
        "question": "Is this suitable for a diabetic?"
    }
    res = client.post("/api/assistant/ask", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "Total Sugars" in str(data["evidence_citations"])
    assert "clinical medical advice" in data["answer"].lower()

def test_grounded_assistant_sodium_query():
    # Haldiram Bhujia Sev IND_PKG_001
    payload = {
        "product_id": "IND_PKG_001",
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
