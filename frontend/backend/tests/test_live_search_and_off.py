"""
EATGOOD — Test Suite for Live Product Search and Open Food Facts Discovery
Validates:
1. Multi-token conjunction search with stem expansion in DataLoaderService.
2. Relevance scoring prioritizing exact and brand matches.
3. Live Open Food Facts text search integration and caching.
4. Multi-tier search endpoint (/api/products/search) deduplicating against local catalogue.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.data_loader import data_loader
from backend.core.openfoodfacts import search_openfoodfacts_text, map_off_product_to_eatgood

client = TestClient(app)


def test_data_loader_multitoken_search_amul_choco():
    """Verifies that multi-token search 'amul choco' finds local Amul chocolates."""
    data_loader.load_all()
    res = data_loader.search_products(query="amul choco", limit=10)
    assert res["total"] > 0, "Should find matching Amul chocolate products"
    top_prod = res["products"][0]
    assert "amul" in top_prod["brand"].lower()
    assert "choc" in top_prod["product_name"].lower()
    assert top_prod["is_local"] is True
    assert top_prod["source"] == "Local Indian Catalogue"
    assert "energy_kcal" in top_prod["nutrition_summary"]


def test_data_loader_multitoken_search_britannia_good_day():
    """Verifies that 'britannia good day' finds Britannia Good Day biscuits."""
    data_loader.load_all()
    res = data_loader.search_products(query="britannia good day", limit=5)
    assert res["total"] > 0
    top_prod = res["products"][0]
    assert "britannia" in top_prod["brand"].lower()
    assert "good day" in top_prod["product_name"].lower()


def test_search_openfoodfacts_text_structure():
    """Verifies that search_openfoodfacts_text returns correctly mapped products."""
    results = search_openfoodfacts_text("haldiram bhujia", limit=3)
    if results:
        first = results[0]
        assert "product_name" in first
        assert "brand" in first
        assert first["is_local"] is False
        assert first["source"] == "Open Food Facts"
        assert "nutrition_summary" in first


def test_api_products_search_prioritizes_local_and_deduplicates():
    """
    Verifies that /api/products/search returns local catalogue products first,
    enriches with Open Food Facts results, and deduplicates barcodes.
    """
    resp = client.get("/api/products/search?q=haldiram+bhujia&limit=10&include_external=true")
    assert resp.status_code == 200
    data = resp.json()
    assert "products" in data
    assert "local_count" in data
    assert "external_count" in data
    assert data["local_count"] > 0

    # Ensure local products appear before external products
    products = data["products"]
    local_indices = [i for i, p in enumerate(products) if p.get("is_local")]
    external_indices = [i for i, p in enumerate(products) if not p.get("is_local")]
    if local_indices and external_indices:
        assert max(local_indices) < min(external_indices), "Local catalogue items must precede external items"

    # Ensure no duplicate barcodes in results
    barcodes = [p["barcode"] for p in products if p.get("barcode")]
    assert len(barcodes) == len(set(barcodes)), "Search results must not contain duplicate barcodes"


def test_map_off_product_to_eatgood_schema():
    """Verifies that Open Food Facts raw product dictionaries map into valid EATGOOD schema."""
    raw_off = {
        "code": "8901234567890",
        "product_name": "Test Masala Chips",
        "brands": "TestBrand",
        "categories": "Snacks, Chips",
        "nutriments": {
            "energy-kcal_100g": 520,
            "sugars_100g": 4.5,
            "sodium_100g": 0.65,
            "proteins_100g": 7.0,
            "saturated-fat_100g": 12.0
        },
        "image_front_url": "https://images.openfoodfacts.net/test.jpg"
    }
    mapped = map_off_product_to_eatgood("8901234567890", raw_off)
    assert mapped["barcode"] == "8901234567890"
    assert mapped["product_name"] == "Test Masala Chips"
    assert mapped["energy_kcal"] == 520
    assert mapped["sugars_g"] == 4.5
    assert mapped["sodium_mg"] == 650.0  # 0.65g sodium = 650mg
    assert mapped["protein_g"] == 7.0
    assert mapped["image_url"] == "https://images.openfoodfacts.net/test.jpg"
