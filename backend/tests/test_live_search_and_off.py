"""
EATGOOD — Open Food Facts search client and the product search endpoint.
"""

import httpx
from fastapi.testclient import TestClient

from backend.core.openfoodfacts import map_off_product_to_eatgood, search_openfoodfacts_text
from backend.main import app

client = TestClient(app)


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_search_openfoodfacts_text_structure():
    """search_openfoodfacts_text maps Open Food Facts results into the EATGOOD schema."""
    def handler(request):
        assert request.url.host == "search.openfoodfacts.org"
        assert request.url.params["q"].startswith('haldiram bhujia test countries_tags:"en:india" AND brands_tags:(')
        return httpx.Response(200, json={"count": 2, "hits": [
            {"code": "8904004400069", "product_name": "Bhujia Sev", "brands": ["Haldiram's", "Haldiram"], "nutriments": {}},
            {"code": "", "product_name": "No barcode, skipped"},
        ]})

    result = search_openfoodfacts_text("haldiram bhujia test", limit=3, client=_mock_client(handler))
    assert result["status"] == "ok"
    assert len(result["products"]) == 1
    first = result["products"][0]
    assert first["product_name"] == "Bhujia Sev"
    assert first["brand"] == "Haldiram's"
    assert first["is_local"] is False
    assert first["source"] == "Open Food Facts"
    assert "nutrition_summary" in first


def test_search_openfoodfacts_text_reports_errors_instead_of_empty_list():
    """A failed external search must surface as an error, never as 'no results'."""
    result = search_openfoodfacts_text(
        "rate limited query", limit=3, client=_mock_client(lambda request: httpx.Response(429))
    )
    assert result["status"] == "error"
    assert result["error_code"] == "OFF_RATE_LIMITED"
    assert result["message"]


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


def test_search_openfoodfacts_text_requests_the_page_and_reports_count():
    seen = {}

    def handler(request):
        seen.update(request.url.params)
        return httpx.Response(200, json={"count": 120, "page": 3, "page_size": 24, "hits": [
            {"code": "8901491101837", "product_name": "Kurkure Masala Munch", "brands": ["PepsiCo"],
             "nutriments": {"energy-kcal_100g": 554, "sugars_100g": 2.1}},
        ]})

    result = search_openfoodfacts_text("kurkure page test", limit=24, page=3, client=_mock_client(handler))
    assert seen["page"] == "3"
    assert seen["page_size"] == "24"
    assert result["count"] == 120
    assert result["products"][0]["barcode"] == "8901491101837"
    assert result["products"][0]["energy_kcal"] == 554


def test_search_openfoodfacts_text_rejects_unexpected_body():
    result = search_openfoodfacts_text(
        "odd body test", limit=3, client=_mock_client(lambda request: httpx.Response(200, json={"products": []}))
    )
    assert result["status"] == "error"
    assert result["error_code"] == "OFF_BAD_RESPONSE"


def test_open_food_facts_search_endpoint_ranks_filters_and_pages(monkeypatch):
    """The product search ranks the first 100 results like the catalogue and pages them locally."""
    from backend.routes import catalogue
    from backend.tests import catalogue_fixture as fx

    base = fx.by_name("Masala Bhujia Test")
    pool = [{**base, "product_name": f"Kurkure Flavour {n}", "brand": "Kurkure", "barcode": f"20000001{n:05d}"} for n in range(29)]
    pool.insert(5, {**base, "product_name": "Kurkure", "brand": "Kurkure", "barcode": "2000000200001"})
    pool.append({**base, "product_name": "Kurkure Broken", "barcode": "2000000200002", "sugars_g": None, "sodium_mg": None,
                 "protein_g": None, "total_fat_g": None})  # 4 key values missing: not listed
    pool.append(dict(pool[0]))  # duplicate barcode: merged
    calls = []

    def fake(term, limit, page):
        calls.append((term, limit, page))
        return {"status": "ok", "count": 450, "products": pool}

    monkeypatch.setattr(catalogue, "search_openfoodfacts_text", fake)
    first = client.get("/api/products/search/openfoodfacts?q=kurkure&page=1").json()
    assert calls == [("kurkure", 100, 1)]
    assert first["count"] == 30
    assert first["pool_limited"] is True
    assert first["has_more"] is True
    assert len(first["products"]) == 24
    assert first["products"][0]["product_name"] == "Kurkure"  # the exact name match ranks first
    second = client.get("/api/products/search/openfoodfacts?q=kurkure&page=2").json()
    assert len(second["products"]) == 6 and second["has_more"] is False
    names = [p["product_name"] for p in first["products"] + second["products"]]
    assert "Kurkure Broken" not in names
    assert len(names) == len(set(names))
    assert "Open Food Facts" in first["attribution"]


def test_open_food_facts_search_endpoint_surfaces_failure_as_http_error(monkeypatch):
    from backend.routes import catalogue

    monkeypatch.setattr(
        catalogue,
        "search_openfoodfacts_text",
        lambda term, limit, page: {
            "status": "error", "products": [], "count": None,
            "error_code": "OFF_RATE_LIMITED", "http_status": 429, "message": "busy",
        },
    )
    response = client.get("/api/products/search/openfoodfacts?q=kurkure")
    assert response.status_code == 429
    assert response.json()["detail"] == {"error_code": "OFF_RATE_LIMITED", "message": "busy"}
