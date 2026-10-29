import ssl
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from backend.core.barcode_utils import (
    calculate_gs1_check_digit,
    clean_barcode,
    normalize_upc_to_ean13,
    validate_barcode,
)
from backend.core.openfoodfacts import fetch_product_from_openfoodfacts
from backend.main import app

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

# ----------------- 2. Barcode lookup through Open Food Facts (test catalogue) -----------------

def test_lookup_product_by_barcode():
    """A barcode Open Food Facts knows returns the product with its full assessment."""
    res = client.get("/api/products/barcode/2000000000015")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "found"
    assert data["source"] == "openfoodfacts"
    assert data["barcode"] == "2000000000015"
    assert data["product"]["product_name"] == "Masala Bhujia Test"
    assert "layer1_general" in data["assessment"]
    assert "layer2_personalized" in data["assessment"]
    assert "layer3_allergens" in data["assessment"]

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

    with patch("backend.products.fetch_product_from_openfoodfacts") as mock_off:
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
    with patch("backend.products.fetch_product_from_openfoodfacts") as mock_off:
        mock_off.return_value = {
            "status": "not_found",
            "message": "Product not found on Open Food Facts."
        }

        res = client.get("/api/products/barcode/9999999999999")
        assert res.status_code == 404
        detail = res.json()["detail"]
        assert detail["error_code"] == "OFF_PRODUCT_NOT_FOUND"
        assert detail["barcode"] == "9999999999999"
        assert "isn't in the product database" in detail["message"]

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
    assert contrib_data["review_status"] == "pending_review"

    # 2. Retrieve contributed product via barcode lookup
    lookup_res = client.get(f"/api/products/barcode/{test_barcode}")
    assert lookup_res.status_code == 200
    lookup_data = lookup_res.json()
    assert lookup_data["status"] == "found"
    assert lookup_data["source"] == "user_contributed"
    assert lookup_data["data_confidence_status"] == "User submitted (not reviewed)"
    assert lookup_data["product"]["product_name"] == "Antigravity Roasted Makhana"
    assert lookup_data["product"]["review_status"] == "pending_review"
    assert "not been reviewed" in lookup_data["message"]

# ----------------- 5. Healthier Alternatives -----------------

def test_healthier_alternatives_endpoint():
    """Verify alternatives endpoint returns scored substitutes in the same category."""
    res = client.get("/api/alternatives/OFF_2000000000015")
    assert res.status_code == 200
    data = res.json()
    assert data["product_id"] == "OFF_2000000000015"
    assert all(alt["category"] == "Snacks" for alt in data["alternatives"])
    assert "alternatives" in data
    # Should find at least one healthier snack alternative with comparative advantages
    assert len(data["alternatives"]) > 0
    top_alt = data["alternatives"][0]
    assert "product_name" in top_alt
    assert "general_grade" in top_alt
    assert "comparative_advantages" in top_alt

# ----------------- 6. Detailed Validation & Error Boundary Tests -----------------

def test_invalid_check_digit_flagged_in_strict_mode():
    """Verify check digit mismatch is explicitly flagged when strict check is required."""
    # 5449000000996 is valid (check digit 6); 5449000000997 is invalid
    val = validate_barcode("5449000000997", strict=True)
    assert val["is_valid"] is False
    assert val["check_digit_valid"] is False
    assert "check digit" in val["error"].lower()

def test_empty_and_whitespace_barcode_handling():
    """Verify empty or space-only input is rejected cleanly."""
    val = validate_barcode("   ")
    assert val["is_valid"] is False
    assert "empty" in val["error"].lower()

def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _raise(exc):
    def handler(request):
        raise exc
    return handler


def test_openfoodfacts_barcode_mismatch_rejected():
    payload = {"status": "success", "code": "1111111111111",
               "product": {"code": "1111111111111", "product_name": "Mismatched", "nutriments": {}}}
    res = fetch_product_from_openfoodfacts("2222222222222", client=_client(lambda r: httpx.Response(200, json=payload)))
    assert res["status"] == "error"
    assert res["error_code"] == "OFF_BARCODE_MISMATCH"


def test_openfoodfacts_rate_limit_handling():
    res = fetch_product_from_openfoodfacts("5449000000996", client=_client(lambda r: httpx.Response(429)))
    assert res["error_code"] == "OFF_RATE_LIMITED"
    assert res["http_status"] == 429


def test_openfoodfacts_timeout_handling_retries_once(monkeypatch):
    monkeypatch.setattr("backend.core.openfoodfacts.RETRY_BACKOFF_SECONDS", 0)
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ReadTimeout("timed out", request=request)

    res = fetch_product_from_openfoodfacts("5449000000996", client=_client(handler))
    assert res["error_code"] == "OFF_TIMEOUT"
    assert res["http_status"] == 504
    assert len(calls) == 2


def test_openfoodfacts_tls_error_is_not_retried_and_message_is_plain():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ConnectError("certificate problem") from ssl.SSLCertVerificationError(
            1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1129)"
        )

    res = fetch_product_from_openfoodfacts("5449000000996", client=_client(handler))
    assert res["error_code"] == "OFF_TLS_ERROR"
    assert res["http_status"] == 502
    assert "secure connection" in res["message"]
    assert "_ssl.c" not in res["message"]
    assert len(calls) == 1


def test_openfoodfacts_tls_error_detected_from_message():
    res = fetch_product_from_openfoodfacts(
        "5449000000996",
        client=_client(_raise(httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"))),
    )
    assert res["error_code"] == "OFF_TLS_ERROR"


def test_openfoodfacts_network_error_handling(monkeypatch):
    monkeypatch.setattr("backend.core.openfoodfacts.RETRY_BACKOFF_SECONDS", 0)
    res = fetch_product_from_openfoodfacts(
        "5449000000996", client=_client(_raise(httpx.ConnectError("[Errno 61] Connection refused")))
    )
    assert res["error_code"] == "OFF_NETWORK_ERROR"
    assert "Errno 61" not in res["message"]
    assert "Errno 61" in res["technical_detail"]


def test_openfoodfacts_upstream_500_handling(monkeypatch):
    monkeypatch.setattr("backend.core.openfoodfacts.RETRY_BACKOFF_SECONDS", 0)
    res = fetch_product_from_openfoodfacts("5449000000996", client=_client(lambda r: httpx.Response(500)))
    assert res["error_code"] == "OFF_UPSTREAM_ERROR"
    assert res["http_status"] == 502


def test_openfoodfacts_unexpected_payload_is_an_error():
    res = fetch_product_from_openfoodfacts("5449000000996", client=_client(lambda r: httpx.Response(200, json={"status": "weird"})))
    assert res["error_code"] == "OFF_BAD_RESPONSE"


def test_openfoodfacts_not_found():
    res = fetch_product_from_openfoodfacts(
        "5449000000996", client=_client(lambda r: httpx.Response(404, json={"status": "failure"}))
    )
    assert res["status"] == "not_found"


def test_ssl_context_uses_certifi_and_verifies():
    import certifi

    from backend.core.openfoodfacts import build_ssl_context

    ctx = build_ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True
    assert certifi.where()


def test_barcode_endpoint_ssl_error_integration():
    """Verify API endpoint returns HTTP 502 with structured error_code and sanitized message on SSL failure."""
    from unittest.mock import patch
    uncached_test_barcode = "9999999999994"
    with patch("backend.products.fetch_product_from_openfoodfacts") as mock_off:
        mock_off.return_value = {
            "status": "error",
            "error_code": "OFF_TLS_ERROR",
            "http_status": 502,
            "product": None,
            "barcode": uncached_test_barcode,
            "message": "Unable to verify secure connection to Open Food Facts. Check your system certificates or enter nutrition facts manually.",
            "technical_detail": "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1129)"
        }
        res = client.get(f"/api/products/barcode/{uncached_test_barcode}")
        assert res.status_code == 502
        detail = res.json()["detail"]
        assert detail["error_code"] == "OFF_TLS_ERROR"
        assert "_ssl.c" not in str(detail)

def test_barcode_endpoint_not_found_is_distinct_from_network_error():
    """Verify HTTP 404 with OFF_PRODUCT_NOT_FOUND is returned for unknown barcodes, never looking like connection error."""
    from unittest.mock import patch
    with patch("backend.products.fetch_product_from_openfoodfacts") as mock_off:
        mock_off.return_value = {
            "status": "not_found",
            "error_code": "OFF_PRODUCT_NOT_FOUND",
            "http_status": 404,
            "product": None,
            "barcode": "7622210000000",
            "message": "Barcode 7622210000000 was not found in the Open Food Facts database."
        }
        res = client.get("/api/products/barcode/7622210000000")
        assert res.status_code == 404
        detail = res.json()["detail"]
        assert detail["error_code"] == "OFF_PRODUCT_NOT_FOUND"
        assert "network" not in detail["message"].lower()

def test_off_normalization_extracts_proteins_and_additives():
    """Verify map_off_product_to_eatgood maps proteins_100g, additives_tags, allergens_tags properly."""
    from backend.core.openfoodfacts import map_off_product_to_eatgood

    raw_off_payload = {
        "code": "3017620422003",
        "product_name": "Hazelnut Spread",
        "brands": "Ferrero",
        "categories": "Confectionary based spreads, Sweet spreads",
        "serving_size": "15 g",
        "serving_quantity": 15.0,
        "nutrition_data_per": "100g",
        "nutriments": {
            "energy-kcal_100g": 539.0,
            "carbohydrates_100g": 57.5,
            "sugars_100g": 56.3,
            "proteins_100g": 6.3,
            "fat_100g": 30.9,
            "saturated-fat_100g": 10.6,
            "sodium_100g": 0.0428,
            "sodium_unit": "g"
        },
        "allergens_tags": ["en:milk", "en:nuts", "en:soybeans"],
        "additives_tags": ["en:e322", "en:e150d"],
        "nutriscore_grade": "e",
        "nova_group": 4,
        "completeness": 0.95
    }

    normalized = map_off_product_to_eatgood("3017620422003", raw_off_payload)
    assert normalized["product_id"] == "OFF_3017620422003"
    assert normalized["protein_g"] == 6.3
    assert normalized["energy_kcal"] == 539.0
    assert normalized["sodium_mg"] == 42.8  # 0.0428 * 1000
    assert "Milk" in normalized["allergens_declared"]
    assert "Soybeans" in normalized["allergens_declared"]
    assert "INS 322" in normalized["additives"]
    assert "INS 150d" in normalized["additives"]
    assert normalized["source_indicators"]["nutriscore_grade"] == "E"
    assert normalized["source_indicators"]["nova_group"] == 4

def test_contribution_validation_rejects_bad_input():
    res = client.post("/api/products/contribute", json={"barcode": "abc", "product_name": "X"})
    assert res.status_code == 422
    res = client.post("/api/products/contribute", json={"barcode": "8901112223334", "product_name": "Cookies", "sugars_g": -5})
    assert res.status_code == 422


def test_direct_barcode_lookup_on_product_endpoint():
    """Verify GET /api/products/{barcode} can resolve by numeric barcode."""
    res = client.get("/api/products/2000000000015")
    assert res.status_code == 200
    data = res.json()
    assert data["product_id"] == "OFF_2000000000015"
    assert data["barcode"] == "2000000000015"

