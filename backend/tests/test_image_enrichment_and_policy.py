"""
EATGOOD — Test Suite for Image Enrichment, Matching Hierarchy, and Presentation Policy
Validates:
1. Open Food Facts image enrichment match hierarchy (Exact Barcode -> Brand/Variant -> Fallback).
2. Image storage in SQLite and merging in DataLoaderService.
3. Filtering by image availability ('has_image').
4. Regression test enforcing Phase K: Strict prohibition of dataset record counts,
   model accuracy percentages, confidence percentages, or internal data quantities in UI.
"""

import os
import re
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.data_loader import data_loader
from backend.database import (
    upsert_product_image,
    get_product_image,
    get_all_product_images,
    get_connection
)
from backend.core.image_enrichment import (
    seed_initial_curated_images,
    fetch_image_by_exact_barcode,
    normalize_brand_slug,
    enrich_product_image_record
)

client = TestClient(app)


def test_seed_initial_curated_images():
    """Verifies that authentic Open Food Facts imagery seeds into SQLite registry."""
    count = seed_initial_curated_images()
    images = get_all_product_images()
    assert len(images) >= 10, "Should have seeded at least 10 authentic product images"
    
    # Check Oreo
    oreo_img = images.get("IND_PKG_564")
    assert oreo_img is not None
    assert "openfoodfacts" in oreo_img["image_url"]
    assert oreo_img["review_status"] == "verified"

    # Check Haldiram's Bhujia Sev
    sev_img = images.get("IND_PKG_001")
    assert sev_img is not None
    assert "openfoodfacts" in sev_img["image_url"]
    assert sev_img["review_status"] == "verified"


def test_data_loader_includes_images():
    """Verifies that data_loader merges product images into the products dataframe."""
    data_loader.load_all()
    prod = data_loader.get_product_by_id("IND_PKG_564")
    assert prod is not None
    assert prod.get("image_url") is not None
    assert "openfoodfacts" in prod["image_url"]


def test_catalogue_filter_by_has_image():
    """Verifies that searching with has_image=True returns only products with images."""
    data_loader.load_all()
    res_with_img = data_loader.search_products(has_image=True, limit=50)
    assert res_with_img["total"] > 0
    for p in res_with_img["products"]:
        assert p.get("image_url") is not None and p.get("image_url") != ""

    res_without_img = data_loader.search_products(has_image=False, limit=50)
    assert res_without_img["total"] > 0
    for p in res_without_img["products"]:
        assert p.get("image_url") is None or p.get("image_url") == ""


def test_api_products_with_image_filter():
    """Verifies /api/products endpoint accepts has_image query param."""
    resp = client.get("/api/products?has_image=true&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["products"]) > 0
    for p in data["products"]:
        assert p.get("image_url") is not None


def test_normalize_brand_slug():
    """Verifies brand name slug normalization for Open Food Facts query tags."""
    assert normalize_brand_slug("Haldiram's") == "haldirams"
    assert normalize_brand_slug("Lay's") == "lays"
    assert normalize_brand_slug("Too Yumm!") == "too-yumm"
    assert normalize_brand_slug("Kellogg's") == "kelloggs"


def test_fallback_record_assignment_on_unmatched():
    """Verifies that products without high confidence matches get assigned fallback status rather than incorrect images."""
    fake_pid = "TEST_UNMATCHED_PRODUCT"
    rec = enrich_product_image_record(
        product_id=fake_pid,
        barcode="9999999999999",
        product_name="Completely Nonexistent Food 12345",
        brand="NonexistentBrandXYZ",
        category="Snacks"
    )
    assert rec["review_status"] == "fallback"
    assert rec["image_url"] is None

    # Clean up test row
    conn = get_connection()
    conn.execute("DELETE FROM product_images WHERE product_id = ?", (fake_pid,))
    conn.commit()
    conn.close()


def test_navratan_mix_cannot_have_maggi_noodles_image():
    """
    CRITICAL REGRESSION TEST:
    Verifies that Haldiram's Navratan Mix (IND_PKG_141) NEVER displays
    a Maggi 2-Minute Noodles photograph or any other mismatched image.
    """
    data_loader.load_all()
    p_navratan_v2 = data_loader.get_product_by_id("IND_PKG_141")
    assert p_navratan_v2 is not None
    assert p_navratan_v2["product_name"] == "Haldiram's Navratan Mix (Variant 2)"
    # Must be None (neutral placeholder)
    assert p_navratan_v2.get("image_url") is None or "890/105/890/1511" not in str(p_navratan_v2.get("image_url")), \
        "Haldiram's Navratan Mix must NEVER display Maggi noodles image!"

    # Verify Maggi noodles (IND_PKG_731) has its own genuine image
    p_maggi = data_loader.get_product_by_id("IND_PKG_731")
    assert p_maggi is not None
    assert "Maggi" in p_maggi["brand"]
    assert "890/105/890/1511" in str(p_maggi.get("image_url"))


def test_cross_brand_image_rejection():
    """
    Verifies that conservative matching rejects candidate images when brand differs,
    even if the product name or category shares generic keywords.
    """
    from backend.core.image_enrichment import fetch_image_by_brand_and_product
    # Searching for Haldiram's Navratan Mix must NEVER return a Maggi/Nestle product
    res = fetch_image_by_brand_and_product(
        brand="Haldiram's",
        product_name="Haldiram's Navratan Mix",
        category="Snacks"
    )
    if res and res.get("image_url"):
        # If an image was returned, it must not be Maggi
        assert "890/105/890/1511" not in res["image_url"]


def test_flavour_conflict_detection():
    """
    Verifies that a product with one flavour (e.g. Cream & Onion)
    never matches an image of a conflicting flavour (e.g. Tomato or Chilli).
    """
    from backend.core.image_enrichment import check_flavour_conflict
    assert check_flavour_conflict({"cream", "onion"}, {"tomato", "tangy"}) is True
    assert check_flavour_conflict({"tomato"}, {"cream", "onion"}) is True
    assert check_flavour_conflict({"salted"}, {"chilli", "spicy"}) is True
    # Compatible should not conflict
    assert check_flavour_conflict({"cream", "onion"}, {"cream", "onion", "style"}) is False


def test_idempotent_curated_seed_purges_bad_mappings():
    """
    Verifies that running seed_initial_curated_images() is idempotent and
    actively purges known legacy wrong IDs (IND_PKG_141, IND_PKG_450, IND_PKG_222).
    """
    from backend.database import upsert_product_image, get_product_image
    # Inject a bad mapping simulating legacy corrupt state
    upsert_product_image(
        product_id="IND_PKG_141",
        image_url="https://images.openfoodfacts.net/images/products/890/105/890/1511/front_en.26.400.jpg",
        review_status="verified"
    )
    # Re-run seeding
    seed_initial_curated_images()
    # Check that IND_PKG_141 was purged
    rec = get_product_image("IND_PKG_141")
    assert rec is None or rec.get("image_url") is None


def test_no_prohibited_dataset_counts_in_frontend():
    """
    CRITICAL POLICY ENFORCEMENT (Phase K):
    Regression test scanning all frontend UI source files.
    Guarantees that:
    1. Total dataset counts (e.g. 852) are never hardcoded or displayed in UI text.
    2. Prohibited phrases like 'X products found' or 'Showing X of Y' are eliminated.
    3. Accuracy percentages, model accuracy statistics, and confidence percentages
       are absent from user-facing screens.
    """
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src"))
    assert os.path.exists(frontend_dir), f"Frontend directory not found at {frontend_dir}"

    prohibited_patterns = [
        (r'\b852\b', "Raw dataset record count '852' must not be exposed in user-facing code"),
        (r'Showing\s+.*products', "Generic 'Showing X products' count pattern prohibited"),
        (r'\b\d+(?:\.\d+)?%\s*(?:accuracy|confidence|coverage|precision|recall|validation)\b', "Accuracy or confidence percentage prohibited in UI"),
        (r'Atwater Calorie Anomalies', "Prohibited internal anomaly count title"),
        (r'Macro > Serving Discrepancies', "Prohibited internal discrepancy count title"),
    ]

    violations = []

    for root, _, files in os.walk(frontend_dir):
        for f in files:
            if f.endswith(('.jsx', '.js', '.html')):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_idx, line in enumerate(fp, 1):
                        # Skip pure comment lines
                        stripped = line.strip()
                        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                            continue
                        for pat, reason in prohibited_patterns:
                            if re.search(pat, line, re.IGNORECASE):
                                violations.append(f"{f}:{line_idx}: {line.strip()[:80]} -> {reason}")

    assert not violations, "Found prohibited dataset counts or statistics in frontend:\n" + "\n".join(violations)
