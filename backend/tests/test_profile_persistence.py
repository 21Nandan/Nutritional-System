import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import save_active_profile, get_active_profile

client = TestClient(app)

def test_profile_default_and_custom_persistence():
    test_uid = "test_user_persistence_123"

    # Initially, new user gets default or empty profile
    res = client.get(f"/api/profile?user_id={test_uid}", headers={"X-User-Id": test_uid})
    assert res.status_code == 200
    data = res.json()
    assert "user_id" in data

    # Update profile with multiple goals, dietary preference, and multiple allergens
    payload = {
        "user_id": test_uid,
        "name": "Nandan",
        "goal": "Reduce Sugar, Increase Fibre",
        "dietary_preference": "Vegetarian",
        "allergens_to_avoid": "Peanuts, Soy",
        "age_group": "18-24",
        "activity_level": "Very active"
    }

    post_res = client.post("/api/profile", json=payload, headers={"X-User-Id": test_uid})
    assert post_res.status_code == 200
    saved = post_res.json()
    assert saved["name"] == "Nandan"
    assert saved["goal"] == "Reduce Sugar, Increase Fibre"
    assert saved["dietary_preference"] == "Vegetarian"
    assert saved["allergens_to_avoid"] == "Peanuts, Soy"
    assert saved["activity_level"] == "Very active"

    try:
        # Re-fetch profile
        get_res = client.get(f"/api/profile?user_id={test_uid}", headers={"X-User-Id": test_uid})
        assert get_res.status_code == 200
        fetched = get_res.json()
        assert fetched["name"] == "Nandan"
        assert fetched["goal"] == "Reduce Sugar, Increase Fibre"
        assert fetched["dietary_preference"] == "Vegetarian"
        assert fetched["allergens_to_avoid"] == "Peanuts, Soy"
        assert fetched["activity_level"] == "Very active"
    finally:
        from backend.database import get_connection
        conn = get_connection()
        conn.execute("DELETE FROM user_profile WHERE user_id LIKE 'test_%'")
        conn.commit()
        conn.close()

def test_assessment_uses_active_user_profile():
    test_uid = "test_user_allergen_pref_456"

    # Configure user with Peanut allergen
    payload = {
        "user_id": test_uid,
        "name": "Alex",
        "goal": "Reduce Sugar",
        "dietary_preference": "No preference",
        "allergens_to_avoid": "Peanuts",
        "age_group": "25-34",
        "activity_level": "Moderately active"
    }
    client.post("/api/profile", json=payload, headers={"X-User-Id": test_uid})

    # IND_PKG_001 (Haldiram Bhujia Sev contains peanuts / groundnut oil / tree nuts or manufactured on shared equipment)
    # Or let's test custom assessment containing peanuts
    custom_payload = {
        "product_name": "Peanut Chikki Bar",
        "brand": "Sweet Brand",
        "category": "Snacks",
        "serving_size": 50,
        "energy_kcal": 250,
        "carbohydrates_g": 30,
        "sugars_g": 18,
        "added_sugars_g": 15,
        "protein_g": 8,
        "total_fat_g": 12,
        "saturated_fat_g": 2.5,
        "trans_fat_g": 0,
        "sodium_mg": 80,
        "dietary_fibre_g": 3,
        "ingredients": "Peanuts, Jaggery, Sugar",
        "allergens_declared": "Peanuts"
    }

    try:
        res = client.post(f"/api/products/assess?user_id={test_uid}", json=custom_payload, headers={"X-User-Id": test_uid})
        assert res.status_code == 200
        data = res.json()
        layer2 = data.get("layer2_personalized", {})
        assert layer2.get("personalized_score") == 0
        assert "Allergen" in layer2.get("suitability_badge", "") or "Conflict" in layer2.get("suitability_status", "")
    finally:
        from backend.database import get_connection
        conn = get_connection()
        conn.execute("DELETE FROM user_profile WHERE user_id LIKE 'test_%'")
        conn.commit()
        conn.close()
