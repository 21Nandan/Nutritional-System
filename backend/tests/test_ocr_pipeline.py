"""
EATGOOD — OCR Pipeline & Food Label Extraction Test Suite
Automated regression tests verifying:
1. Local Tesseract 5 engine initialization & status.
2. OpenCV/PIL preprocessing pipeline (orientation, normalization, contrast enhancement).
3. Distinct image byte processing (guaranteeing different images yield different extracted text).
4. Elimination of silent mock fallbacks (blank or corrupt images return error/not_found, never sample data).
5. Heuristic repair of common OCR artifacts (e.g. missing decimal points, 'Og' for 0g).
6. Evidence-based cross-field consistency checks (Atwater formula, Sat Fat <= Total Fat, Sugars <= Carbs).
7. FastAPI endpoint /api/analyze/ocr integration and SQLite scan session logging.
"""

import os
import pytest
from PIL import Image
import httpx
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.ocr_service import (
    get_ocr_engine_info,
    preprocess_image_for_ocr,
    run_image_ocr,
    extract_nutrition_from_text
)
from backend.database import get_recent_scan_sessions

client = TestClient(app)

def resolve_uploads_dir():
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "uploads")),
        os.path.abspath(os.path.join(os.getcwd(), "data", "uploads")),
        os.path.abspath(os.path.join(os.getcwd(), "..", "data", "uploads")),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

UPLOADS_DIR = resolve_uploads_dir()


def test_ocr_engine_status():
    """Verifies that local Tesseract OCR binary is located and functional."""
    info = get_ocr_engine_info()
    assert info["available"] is True, "Tesseract binary must be installed and accessible locally."
    assert "Tesseract" in info["engine"]
    assert info["version"] is not None


def test_image_preprocessing():
    """Verifies image loading, normalization, and contrast enhancement."""
    # Create a small test image
    test_img_path = os.path.join(UPLOADS_DIR, "test_preprocess_fixture.png")
    img = Image.new("RGB", (300, 300), color=(200, 200, 200))
    img.save(test_img_path)

    try:
        processed_img, meta = preprocess_image_for_ocr(test_img_path)
        assert processed_img is not None
        assert meta["orientation_corrected"] is True
        # Small image (300x300) should be upscaled
        assert meta["processed_size"][0] >= 600 or meta["processed_size"][1] >= 600
    finally:
        if os.path.exists(test_img_path):
            os.remove(test_img_path)


def test_distinct_images_produce_distinct_text():
    """
    CRITICAL REGRESSION TEST:
    Ensures that different uploaded label images produce genuinely distinct OCR text and values,
    proving that no cached result or hardcoded fallback is masking actual OCR extraction.
    """
    img1_path = os.path.join(UPLOADS_DIR, "scan_Screenshot 2026-10-26 at 9.37.26 PM.png")
    img2_path = os.path.join(UPLOADS_DIR, "scan_Screenshot 2026-10-26 at 9.56.28 PM.png")

    if not os.path.exists(img1_path) or not os.path.exists(img2_path):
        pytest.skip(f"Test fixture images not present in {UPLOADS_DIR}")

    res1 = run_image_ocr(img1_path)
    res2 = run_image_ocr(img2_path)

    assert res1["status"] == "success"
    assert res2["status"] == "success"

    # Texts must be substantially different
    assert res1["raw_text"] != res2["raw_text"], "Different images MUST produce different raw OCR texts."

    ext1 = extract_nutrition_from_text(res1["raw_text"])
    ext2 = extract_nutrition_from_text(res2["raw_text"])

    val1 = ext1["extracted_values"]
    val2 = ext2["extracted_values"]

    # Image 1 (snack chips label) has ~602 kcal; Image 2 has ~388 kcal
    assert val1["energy_kcal"] != val2["energy_kcal"], "Distinct images must have different extracted calorie metrics."
    assert val1["energy_kcal"] == 602.0
    assert val2["energy_kcal"] == 388.0


def test_no_silent_fallback_on_blank_image():
    """
    CRITICAL REGRESSION TEST:
    Verifies that a blank image returns 'no_text_found' and DOES NOT fall back to
    any hardcoded 450 kcal sample text or fake values.
    """
    blank_path = os.path.join(UPLOADS_DIR, "test_blank_fixture.png")
    img = Image.new("RGB", (400, 400), color="white")
    img.save(blank_path)

    try:
        res = run_image_ocr(blank_path)
        assert res["status"] in ["no_text_found", "error"]
        assert "450 kcal" not in res["raw_text"]
        assert len(res["raw_text"].strip()) == 0

        ext = extract_nutrition_from_text(res["raw_text"])
        assert ext["extracted_values"]["energy_kcal"] is None
        assert ext["extracted_values"]["carbohydrates_g"] is None
        assert ext["extracted_values"]["protein_g"] is None
        assert all(status == "not_found" for status in ext["field_statuses"].values())
    finally:
        if os.path.exists(blank_path):
            os.remove(blank_path)


def test_macro_glitch_repair_and_field_status():
    """Verifies that missing decimals in OCR (e.g. 3736g) are repaired and flagged with 'needs_review'."""
    raw_snippet = """
    NUTRITIONAL INFORMATION
    Per 100g
    Energy: 420 kcal
    Carbohydrates: 3736 g
    Protein: 8.5 g
    Total Fat: 14.0 g
    Total Sugars: Og
    """
    ext = extract_nutrition_from_text(raw_snippet)
    vals = ext["extracted_values"]
    statuses = ext["field_statuses"]

    # Carbohydrates 3736g on per 100g basis should be auto-repaired to 37.36g
    assert vals["carbohydrates_g"] == 37.36
    assert statuses["carbohydrates_g"] == "needs_review"
    assert "repaired" in ext["field_notes"]["carbohydrates_g"]

    # 'Og' should be parsed as 0.0
    assert vals["sugars_g"] == 0.0
    assert statuses["sugars_g"] == "extracted"


def test_atwater_calorie_crosscheck():
    """Verifies that severe calorie discrepancies trigger a suspicious flag and 'needs_review' on calories."""
    # Label claims 800 kcal but macros only add up to 4*10 + 4*5 + 9*5 = 105 kcal
    discrepant_text = """
    Nutrition Facts
    Per 100g
    Energy: 800 kcal
    Carbohydrates: 10.0g
    Protein: 5.0g
    Total Fat: 5.0g
    """
    ext = extract_nutrition_from_text(discrepant_text)
    assert ext["field_statuses"]["energy_kcal"] == "needs_review"
    assert any("Calorie discrepancy" in flag for flag in ext["suspicious_flags"])


def test_sub_nutrient_consistency_checks():
    """Verifies that impossible values (Sat Fat > Total Fat or Sugars > Carbs) are flagged."""
    contradictory_text = """
    Nutrition Facts
    Per 100g
    Energy: 300 kcal
    Carbohydrates: 20.0g
    Total Sugars: 45.0g
    Total Fat: 10.0g
    Saturated Fat: 15.0g
    """
    ext = extract_nutrition_from_text(contradictory_text)
    flags = ext["suspicious_flags"]

    assert any("Fat inconsistency" in flag for flag in flags)
    assert ext["field_statuses"]["saturated_fat_g"] == "needs_review"

    assert any("Carbohydrate inconsistency" in flag for flag in flags)
    assert ext["field_statuses"]["sugars_g"] == "needs_review"


def test_api_analyze_ocr_integration():
    """Tests the full FastAPI file-upload OCR route and scan session logging."""
    img_path = os.path.join(UPLOADS_DIR, "scan_Screenshot 2026-10-26 at 9.37.26 PM.png")
    if not os.path.exists(img_path):
        pytest.skip(f"Test fixture image not present in {UPLOADS_DIR}")

    with open(img_path, "rb") as f:
        response = client.post("/api/analyze/ocr", files={"file": ("label.png", f, "image/png")})

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["scan_id"].startswith("scn_")
    assert "Tesseract" in data["ocr_engine"]
    assert data["extracted_values"]["energy_kcal"] == 602.0
    assert data["extracted_values"]["total_fat_g"] == 44.56
    assert data["requires_user_confirmation"] is True

    # Verify session was recorded in SQLite
    recent_scans = get_recent_scan_sessions(limit=5)
    matching_scan = next((s for s in recent_scans if s["scan_id"] == data["scan_id"]), None)
    assert matching_scan is not None, "Scan session must be logged to SQLite."
    assert matching_scan["status"] == "success"


def test_cloud_vision_ocr_mocked_success(monkeypatch):
    """Verifies Cloud Vision OCR request structure, response parsing, and nutrition extraction."""
    monkeypatch.setenv("VISION_API_KEY", "mock_test_key_12345")
    monkeypatch.setenv("EATGOOD_OCR_PROVIDER", "cloud")

    sample_label_text = (
        "NUTRITION FACTS\n"
        "Serving Size: 100g\n"
        "Energy: 485 kcal\n"
        "Carbohydrates: 58.2g\n"
        "Total Sugars: 12.0g\n"
        "Protein: 9.4g\n"
        "Total Fat: 22.5g\n"
        "Saturated Fat: 4.8g\n"
        "Sodium: 340mg\n"
        "Dietary Fibre: 6.5g\n"
        "Ingredients: Whole wheat flour, edible vegetable oil, salt, spices."
    )

    mock_vision_payload = {
        "responses": [
            {
                "fullTextAnnotation": {
                    "text": sample_label_text,
                    "pages": [
                        {
                            "confidence": 0.96,
                            "blocks": [
                                {
                                    "confidence": 0.95,
                                    "paragraphs": [
                                        {"confidence": 0.97}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        ]
    }

    class MockResponse:
        status_code = 200
        def json(self):
            return mock_vision_payload

    orig_post = httpx.Client.post

    def mock_post(self, url, *args, **kwargs):
        if "vision.googleapis.com" in str(url):
            assert "key=mock_test_key_12345" in str(url)
            json_body = kwargs.get("json", {})
            assert "requests" in json_body
            assert json_body["requests"][0]["features"][0]["type"] == "DOCUMENT_TEXT_DETECTION"
            return MockResponse()
        return orig_post(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    test_img = os.path.join(UPLOADS_DIR, "test_cloud_fixture.png")
    Image.new("RGB", (200, 200), color="blue").save(test_img)

    try:
        res = run_image_ocr(test_img)
        assert res["status"] == "success"
        assert "Google Cloud Vision" in res["engine"]
        assert res["ocr_confidence"] >= 0.90
        assert "485 kcal" in res["raw_text"]

        ext = extract_nutrition_from_text(res["raw_text"], res["ocr_confidence"])
        vals = ext["extracted_values"]
        assert vals["energy_kcal"] == 485.0
        assert vals["carbohydrates_g"] == 58.2
        assert vals["protein_g"] == 9.4
        assert vals["total_fat_g"] == 22.5
        assert vals["sodium_mg"] == 340.0
        assert vals["dietary_fibre_g"] == 6.5
        assert ext["field_statuses"]["energy_kcal"] == "extracted"
    finally:
        if os.path.exists(test_img):
            os.remove(test_img)


def test_cloud_vision_ocr_missing_key(monkeypatch):
    """Verifies clean error return when Cloud Vision is invoked without an API key."""
    monkeypatch.delenv("VISION_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_VISION_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_VISION_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    from backend.core.ocr_service import run_cloud_vision_ocr
    test_img = os.path.join(UPLOADS_DIR, "test_no_key.png")
    Image.new("RGB", (50, 50), color="gray").save(test_img)

    try:
        res = run_cloud_vision_ocr(test_img)
        assert res["status"] == "error"
        assert "not configured" in res["message"]
    finally:
        if os.path.exists(test_img):
            os.remove(test_img)


def test_cloud_vision_api_error_handling(monkeypatch):
    """Verifies that 403 (invalid key / API disabled) and 429 errors produce user-friendly messages."""
    monkeypatch.setenv("VISION_API_KEY", "bad_or_disabled_key")

    from backend.core.ocr_service import run_cloud_vision_ocr
    test_img = os.path.join(UPLOADS_DIR, "test_err_fixture.png")
    Image.new("RGB", (50, 50), color="gray").save(test_img)

    try:
        # Test 403 Forbidden / Not Enabled
        class Mock403:
            status_code = 403
            text = "Permission Denied"
            def json(self):
                return {"error": {"message": "Cloud Vision API has not been used..."}}

        orig_post = httpx.Client.post
        monkeypatch.setattr(httpx.Client, "post", lambda self, url, *a, **k: Mock403() if "vision.googleapis.com" in str(url) else orig_post(self, url, *a, **k))
        res403 = run_cloud_vision_ocr(test_img)
        assert res403["status"] == "error"
        assert "Cloud Vision API key is invalid" in res403["message"] or "not enabled" in res403["message"]

        # Test 429 Quota Exceeded
        class Mock429:
            status_code = 429
            text = "Resource Exhausted"
            def json(self):
                return {"error": {"message": "Quota exceeded"}}

        monkeypatch.setattr(httpx.Client, "post", lambda self, url, *a, **k: Mock429() if "vision.googleapis.com" in str(url) else orig_post(self, url, *a, **k))
        res429 = run_cloud_vision_ocr(test_img)
        assert res429["status"] == "error"
        assert "quota" in res429["message"].lower()
    finally:
        if os.path.exists(test_img):
            os.remove(test_img)


def test_ocr_provider_selection_and_diagnostics(monkeypatch):
    """Verifies OCR engine selection precedence and clear diagnostics when no engine is ready."""
    # Scenario A: Cloud Vision explicitly preferred with key
    monkeypatch.setenv("VISION_API_KEY", "test_key_abc")
    monkeypatch.setenv("EATGOOD_OCR_PROVIDER", "cloud")
    info = get_ocr_engine_info()
    assert info["available"] is True
    assert info["provider"] == "cloud_vision"
    assert "Google Cloud Vision" in info["engine"]

    # Scenario B: Vercel serverless environment with key defaults to Cloud Vision
    monkeypatch.delenv("EATGOOD_OCR_PROVIDER", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    info_vercel = get_ocr_engine_info()
    assert info_vercel["available"] is True
    assert info_vercel["provider"] == "cloud_vision"

    # Scenario C: Neither engine available (simulating unconfigured Vercel instance)
    monkeypatch.delenv("VISION_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_VISION_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_VISION_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr("backend.core.ocr_service.get_tesseract_path", lambda: None)

    info_none = get_ocr_engine_info()
    assert info_none["available"] is False
    assert "VISION_API_KEY" in info_none["message"]
    assert "manually" in info_none["message"]


def test_api_analyze_ocr_with_mocked_cloud_vision(monkeypatch):
    """Tests the full /api/analyze/ocr endpoint flow in a Vercel-like environment using Cloud Vision."""
    monkeypatch.setenv("VISION_API_KEY", "mock_prod_key")
    monkeypatch.setenv("VERCEL", "1")

    label_text = (
        "Nutrition Information per 100g:\n"
        "Energy: 520 kcal\n"
        "Protein: 7.2 g\n"
        "Total Fat: 28.0 g\n"
        "Carbohydrate: 59.0 g\n"
        "Total Sugars: 4.5 g\n"
        "Sodium: 480 mg"
    )

    class MockResp:
        status_code = 200
        def json(self):
            return {
                "responses": [
                    {
                        "fullTextAnnotation": {
                            "text": label_text,
                            "pages": [{"confidence": 0.94}]
                        }
                    }
                ]
            }

    orig_post = httpx.Client.post
    monkeypatch.setattr(httpx.Client, "post", lambda self, url, *a, **k: MockResp() if "vision.googleapis.com" in str(url) else orig_post(self, url, *a, **k))

    # Create dummy image in memory
    from io import BytesIO
    buf = BytesIO()
    Image.new("RGB", (100, 100), color="green").save(buf, format="PNG")
    buf.seek(0)

    response = client.post("/api/analyze/ocr", files={"file": ("label.png", buf.getvalue(), "image/png")})
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "Google Cloud Vision" in data["ocr_engine"]
    assert data["extracted_values"]["energy_kcal"] == 520.0
    assert data["extracted_values"]["protein_g"] == 7.2
    assert data["extracted_values"]["total_fat_g"] == 28.0
    assert data["extracted_values"]["carbohydrates_g"] == 59.0
    assert data["extracted_values"]["sodium_mg"] == 480.0
    assert data["requires_user_confirmation"] is True

