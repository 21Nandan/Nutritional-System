"""Catalogue search over the Open Food Facts search service (the service itself is mocked)."""

import pytest

from backend.core import off_catalogue
from backend.core.off_catalogue import browse_catalogue, build_catalogue_query, compose_query
from backend.tests import catalogue_fixture as fx

CADBURY = [
    {**fx.by_name("Milk Chocolate Bar Test"), "product_name": "Cadbury Dairy Milk", "brand": "Cadbury", "barcode": "1"},
    {**fx.by_name("Milk Chocolate Bar Test"), "product_name": "Cadbury Gems", "brand": "Cadbury", "barcode": "2"},
    {**fx.by_name("Milk Chocolate Bar Test"), "product_name": "Dark Fantasy", "brand": "Sunfeast", "barcode": "3"},
]


@pytest.fixture
def service(monkeypatch):
    """Records each query and answers from a small product list, like the real service would."""
    calls = []

    def fake(query, limit=24, page=1, sort_by=None, client=None):
        calls.append({"query": query, "limit": limit, "page": page, "sort_by": sort_by})
        # Free-text words are the lower-case ones; filters and operators contain ":" or are upper case.
        words = [w for w in query.split() if w.isalpha() and w.islower()]
        # Like the real service, whole words match; there is no prefix matching.
        hits = [p for p in CADBURY if all(w in f"{p['product_name']} {p['brand']}".lower().split() for w in words)]
        return {"status": "ok", "products": hits[(page - 1) * limit: page * limit], "count": len(hits)}

    monkeypatch.setattr(off_catalogue, "search_openfoodfacts", fake)
    return calls


def test_words_are_placed_before_the_filters_without_and():
    words, filters, _ = build_catalogue_query("  Dairy   MILK ", category="Chocolates & Sweets")
    assert words == ["dairy", "milk"]
    query = compose_query(words, filters)
    assert query.startswith(
        'dairy milk NOT categories_tags:"en:alcoholic-beverages" AND countries_tags:"en:india" AND (categories_tags:"en:chocolates"'
    )
    assert "milk AND" not in query


def test_plain_browsing_is_popular_first_and_text_search_is_by_relevance(service):
    browse_catalogue()
    browse_catalogue(text="cadbury")
    assert service[0]["sort_by"] == off_catalogue.POPULAR_FIRST
    assert service[1]["sort_by"] is None


def test_unfinished_last_word_matches_word_starts(service):
    result = browse_catalogue(text="cadbury da")
    assert result["match_mode"] == "partial"
    assert [p["product_name"] for p in result["products"]] == ["Cadbury Dairy Milk"]
    assert service[0]["query"].startswith("cadbury ")
    assert service[0]["limit"] == off_catalogue.SEARCH_POOL


def test_a_single_partial_word_falls_back_to_word_starts(service):
    result = browse_catalogue(text="cadb")
    assert result["match_mode"] == "partial"
    assert {p["product_name"] for p in result["products"]} == {"Cadbury Dairy Milk", "Cadbury Gems"}


def test_full_words_are_searched_directly(service):
    result = browse_catalogue(text="cadbury")
    assert result["match_mode"] == "words"
    assert result["count"] == 2
    assert len(service) == 1


def test_nothing_matching_is_an_honest_empty_result(service):
    result = browse_catalogue(text="zzqqxx")
    assert result["status"] == "ok"
    assert result["products"] == []
    assert result["count"] == 0


def test_barcode_is_looked_up_exactly(service):
    result = browse_catalogue(text=" 8901233030548 ")
    assert result["match_mode"] == "barcode"
    assert service[0]["query"] == 'code:"8901233030548"'


def test_service_errors_are_passed_on_not_turned_into_empty_pages(monkeypatch):
    error = {"status": "error", "products": [], "count": None, "error_code": "OFF_RATE_LIMITED", "http_status": 429, "message": "busy"}
    monkeypatch.setattr(off_catalogue, "search_openfoodfacts", lambda *a, **k: error)
    assert browse_catalogue(text="cadbury da")["status"] == "error"
    assert browse_catalogue(text="cadbury")["status"] == "error"


def test_nutrient_filters_and_intents_become_ranges():
    _, filters, intent = build_catalogue_query("low sugar biscuits", nutrient_filters={"max_sodium": 400})
    assert "nutriments.sugars_100g:[0 TO 6.0]" in filters
    assert "nutriments.sodium_100g:[0 TO 0.4]" in filters
    assert intent["category"] == "Biscuits & Bakery"


def test_unknown_category_is_rejected():
    with pytest.raises(ValueError):
        build_catalogue_query("x", category="Furniture")


def test_catalogue_endpoint_validates_paging_and_category():
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    assert client.get("/api/products?limit=30&offset=15").json()["detail"]["error_code"] == "BAD_OFFSET"
    assert client.get("/api/products?limit=100&offset=10000").json()["detail"]["error_code"] == "PAGE_TOO_DEEP"
    assert client.get("/api/products?category=Furniture").json()["detail"]["error_code"] == "UNKNOWN_CATEGORY"
    data = client.get("/api/products?query=%20bhujia%20").json()
    assert data["query"] == "bhujia"
    assert [p["product_name"] for p in data["products"]] == ["Masala Bhujia Test"]
