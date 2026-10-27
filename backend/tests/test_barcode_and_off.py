import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.barcode_utils import (
    calculate_gs1_check_digit,
    validate_barcode,
    clean_barcode,
    normalize_upc_to_ean13
)
from backend.database import get_cached_barcode_product, cache_barcode_product

client = TestClient(app)

# ----------------- 1. Barcode Utility & Format Tests -----------------

def test_gs1_check_digit_calculation():
    """Verify GS1 Modulo-10 check digit math on known standard barcodes."""
    # 544900000099 (Coca-Cola 12 digits) -> check digit 6
    assert calculate_gs1_check_digit("544900000099") == 6
    # 890103000001 -> check digit 0 (sum=50, 50%10=0)
    assert calculate_gs1_check_digit("890103000001") == 0
    # EAN-8: 9638507 -> check digit 4
    assert calculate_gs1_check_digit("9638507") == 4
    # UPC-A: 01234567890 -> check digit 5
    assert calculate_gs1_check_digit("01234567890") == 5

def test_leading_zeros_preserved():
    """Ensure leading zeros are strictly preserved as strings and not truncated as ints."""
    code_with_zeros = "0012345678905"
    cleaned = clean_barcode(code_with_zeros)
    assert cleaned == "0012345678905"
    assert len(cleaned) == 13
    assert cleaned.startswith("00")

def test_barcode_format_detection():
    """Verify format classification for EAN-13, EAN-8, UPC-A, GTIN-14."""
    # EAN-13
    val13 = validate_barcode("5449000000996", strict=True)
    assert val13["is_valid"] is True
    assert val13["format"] == "EAN-13"
    assert val13["check_digit_valid"] is True

    # EAN-8
    val8 = validate_barcode("96385074", strict=True)
    assert val8["is_valid"] is True
    assert val8["format"] == "EAN-8"
    assert val8["check_digit_valid"] is True

    # UPC-A (12 digits)
    val12 = validate_barcode("012345678905", strict=True)
    assert val12["is_valid"] is True
    assert val12["format"] == "UPC-A"
    assert val12["check_digit_valid"] is True

    # Invalid characters
    val_invalid = validate_barcode("8901ABC123456")
    assert val_invalid["is_valid"] is False
    assert "numeric" in val_invalid["error"].lower()

def test_normalize_upc_to_ean13():
    """Check standard 12-digit UPC conversion to 13-digit EAN with leading 0."""
    ean = normalize_upc_to_ean13("012345678905")
    assert ean == "0012345678905"
    assert len(ean) == 13

# ----------------- 2. Layer 1: Local EATGOOD Catalogue Barcode Lookup -----------------

def test_lookup_local_product_by_barcode():
    """Verify barcode lookup matches a known product in the 852-item dataset."""
    # Aashirvaad Superior MP Sharbati Whole Wheat Atta has barcode 8903585650756
    res = client.get("/api/products/barcode/8903585650756")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "found"
    assert data["source"] == "local_database"
    assert data["barcode"] == "8903585650756"
    assert "product" in data
    assert "assessment" in data
    assert "layer1_general" in data["assessment"]
    assert "layer2_personalized" in data["assessment"]
    assert "layer3_allergens" in data["assessment"]
    assert "alternatives" in data

# ----------------- 3. Layer 2: Open Food Facts Integration (Mocked) -----------------

def test_lookup_openfoodfacts_mocked_hit():
    """Verify Open Food Facts integration converts external data into standard EATGOOD assessment."""
    fake_off_product = {
        "product_id": "OFF_7622210999999",
        "barcode": "7622210999999",
        "product_name": "Antigravity Grain Crisps",
        "brand": "Oreo / Mondelēz",
        "category": "Snacks",
        "sub_category": "Healthy Crisps",
        "serving_size": 100.0,
        "serving_size_unit": "g",
        "measurement_basis": "per 100g",
        "energy_kcal": 474.0,
        "carbohydrates_g": 69.0,
        "sugars_g": 38.0,
        "added_sugars_g": 35.0,
        "protein_g": 5.2,
        "total_fat_g": 19.0,
        "saturated_fat_g": 5.2,
        "trans_fat_g": 0.0,
        "sodium_mg": 400.0,
        "dietary_fibre_g": 2.7,
        "ingredients": "Wheat flour, sugar, palm oil, salt.",
        "allergens_declared": "Wheat",
        "image_url": "https://images.openfoodfacts.org/images/products/test/front.jpg",
        "data_source": "Open Food Facts (v3 API)",
        "data_confidence_status": "Community Sourced (Open Food Facts)",
        "openfoodfacts_attribution": "Product data retrieved from Open Food Facts (https://world.openfoodfacts.org), licensed under Open Database License (ODbL)."
    }

    with patch("backend.main.fetch_product_from_openfoodfacts") as mock_off:
        mock_off.return_value = {
            "status": "success",
            "product": fake_off_product
        }

        res = client.get("/api/products/barcode/7622210999999")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "found"
        assert data["source"] in ["openfoodfacts", "openfoodfacts_cached"]
        assert data["product"]["product_name"] == "Antigravity Grain Crisps"
        assert "ODbL" in data["openfoodfacts_attribution"]
        assert "assessment" in data
        assert data["assessment"]["layer1_general"]["grade"] in ["A", "B", "C", "D", "E"]

def test_lookup_openfoodfacts_not_found():
    """Verify structured 404 response when product is unlisted on both local DB and Open Food Facts."""
    with patch("backend.main.fetch_product_from_openfoodfacts") as mock_off:
        mock_off.return_value = {
            "status": "not_found",
            "message": "Product not found on Open Food Facts."
        }

        res = client.get("/api/products/barcode/9999999999999")
        assert res.status_code == 404
        detail = res.json()["detail"]
        assert detail["status"] == "not_found"
        assert detail["barcode"] == "9999999999999"
        assert "not found" in detail["message"].lower()

# ----------------- 4. Layer 3: Product Contribution Flow -----------------

def test_user_product_contribution_and_retrieval():
    """Verify contributing an unlisted product saves it to SQLite and enables layered lookup."""
    test_barcode = "8909876543210"

    contribution_payload = {
        "barcode": test_barcode,
        "product_name": "Antigravity Roasted Makhana",
        "brand": "SuperFoods",
        "category": "Snacks",
        "sub_category": "Foxnuts & Healthy Snacks",
        "serving_size": 30.0,
        "serving_size_unit": "g",
        "measurement_basis": "per 100g",
        "energy_kcal": 380.0,
        "carbohydrates_g": 72.0,
        "sugars_g": 1.5,
        "added_sugars_g": 0.0,
        "protein_g": 10.5,
        "total_fat_g": 4.5,
        "saturated_fat_g": 0.8,
        "trans_fat_g": 0.0,
        "sodium_mg": 180.0,
        "dietary_fibre_g": 7.5,
        "ingredients": "Foxnuts (Makhana), Olive Oil, Himalayan Pink Salt, Turmeric, Black Pepper.",
        "allergens_declared": "None",
        "submission_notes": "Added from packaging test"
    }

    # 1. Post contribution
    contrib_res = client.post("/api/products/contribute", json=contribution_payload)
    assert contrib_res.status_code == 200
    contrib_data = contrib_res.json()
    assert contrib_data["status"] == "success"
    assert contrib_data["review_status"] == "user_submitted"

    # 2. Retrieve contributed product via barcode lookup
    lookup_res = client.get(f"/api/products/barcode/{test_barcode}")
    assert lookup_res.status_code == 200
    lookup_data = lookup_res.json()
    assert lookup_data["status"] == "found"
    assert lookup_data["source"] == "user_contributed"
    assert lookup_data["data_confidence_status"] == "User Submitted (Unverified)"
    assert lookup_data["product"]["product_name"] == "Antigravity Roasted Makhana"
    # User-contributed foods are never falsely marked as verified
    assert "Unverified" in lookup_data["product"]["data_confidence_status"]

    # 3. Verify it appears in user contributions list
    list_res = client.get("/api/products/contributions")
    assert list_res.status_code == 200
    contributions = list_res.json()["contributions"]
    assert any(c["barcode"] == test_barcode for c in contributions)

def test_duplicate_contribution_rejected_if_in_local_db():
    """Verify attempting to contribute an existing catalogue barcode is rejected with 409."""
    # 8903585650756 already exists in EATGOOD catalogue
    payload = {
        "barcode": "8903585650756",
        "product_name": "Duplicate Attempt",
        "category": "Snacks",
        "serving_size": 100.0,
        "energy_kcal": 200.0
    }
    res = client.post("/api/products/contribute", json=payload)
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"].lower()

# ----------------- 5. Healthier Alternatives -----------------

def test_healthier_alternatives_endpoint():
    """Verify alternatives endpoint returns scored substitutes in the same category."""
    # Haldiram's Bhujia Sev IND_PKG_001
    res = client.get("/api/alternatives/IND_PKG_001")
    assert res.status_code == 200
    data = res.json()
    assert data["product_id"] == "IND_PKG_001"
    assert "alternatives" in data
    # Should find at least one healthier snack alternative with comparative advantages
    assert len(data["alternatives"]) > 0
    top_alt = data["alternatives"][0]
    assert "product_name" in top_alt
    assert "general_grade" in top_alt
    assert "comparative_advantages" in top_alt
