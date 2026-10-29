"""Search ranking, eligibility and data-quality rules (backend/core/product_quality.py)."""

import pytest
from fastapi.testclient import TestClient

from backend.core import off_catalogue
from backend.core.openfoodfacts import map_off_product_to_eatgood
from backend.core.product_quality import assess_record, rank_products, relevance
from backend.main import app
from backend.tests import catalogue_fixture as fx

client = TestClient(app)


def product(name, brand="Cadbury", barcode="8901233030548", **overrides):
    """A complete, valid record; overrides remove or change fields (None = not stated)."""
    record = {
        "product_name": name, "brand": brand, "barcode": barcode, "measurement_basis": "per 100g",
        "energy_kcal": 530, "protein_g": 7, "carbohydrates_g": 58, "sugars_g": 56, "total_fat_g": 30,
        "saturated_fat_g": 18, "sodium_mg": 90, "dietary_fibre_g": 2, "added_sugars_g": 50, "trans_fat_g": 0,
        "cholesterol_mg": 10, "ingredients": "Sugar, milk solids, cocoa butter", "allergens_declared": "Milk",
        "sold_in_india": True,
    }
    record.update(overrides)
    return record


def names(ranked):
    return [p["product_name"] for p in ranked]


# ---------- relevance before completeness ----------

def test_exact_match_with_missing_data_outranks_near_match_with_complete_data():
    exact_incomplete = product("Cadbury Dairy Milk", protein_g=None, total_fat_g=None, ingredients="",
                               allergens_declared="", sold_in_india=None, dietary_fibre_g=None, barcode="1234")
    near_complete = product("Cadbury Dairy Milk Silk Hazelnut", barcode="7622201761738")
    ranked, _ = rank_products([near_complete, exact_incomplete], "cadbury dairy milk")
    assert names(ranked) == ["Cadbury Dairy Milk", "Cadbury Dairy Milk Silk Hazelnut"]


def test_unrelated_complete_product_never_outranks_a_relevant_one():
    relevant_sparse = product("Dairy Milk", protein_g=None, carbohydrates_g=None, total_fat_g=None, ingredients="",
                              allergens_declared="", barcode="1111")
    unrelated_complete = product("Bourbon Biscuits", brand="Britannia", barcode="8901063010000")
    ranked, _ = rank_products([unrelated_complete, relevant_sparse], "dairy milk")
    assert names(ranked) == ["Dairy Milk", "Bourbon Biscuits"]
    assert ranked[1]["search_relevance"] == 0


def test_similarly_relevant_products_are_ordered_by_data_quality():
    sparse = product("Cadbury Dairy Milk Fruit", barcode="2222", ingredients="", allergens_declared="",
                     dietary_fibre_g=None, added_sugars_g=None)
    complete = product("Cadbury Dairy Milk Nut", barcode="7622201149406")
    ranked, _ = rank_products([sparse, complete], "cadbury dairy milk")
    assert names(ranked) == ["Cadbury Dairy Milk Nut", "Cadbury Dairy Milk Fruit"]


def test_typos_and_unfinished_words_still_match():
    bar = product("Cadbury Dairy Milk")
    assert relevance(bar, "cadbry dairy") > 0
    assert relevance(bar, "cadbury da") >= 80
    assert relevance(bar, "dairy mi") >= 70  # every word matched (one still being typed)
    assert relevance(bar, "xyz") == 0
    assert relevance(bar, "") == 0


def test_a_name_match_ranks_above_a_brand_only_match():
    brand_only = product("Puffcorn", brand="Kurkure", barcode="1001")  # complete data
    named = product("Kurkure Masala Munch", brand="PepsiCo", barcode="1002", ingredients="", allergens_declared="")
    ranked, _ = rank_products([brand_only, named], "kurkure")
    assert names(ranked) == ["Kurkure Masala Munch", "Puffcorn"]


def test_ranking_is_deterministic():
    items = [product(f"Cadbury Dairy Milk {n}", barcode=str(5000 + n)) for n in range(6)]
    first, _ = rank_products(items, "cadbury dairy milk")
    second, _ = rank_products(list(items), "cadbury dairy milk")
    assert names(first) == names(second)


# ---------- eligibility and completeness ----------

def test_products_missing_up_to_three_key_values_stay_but_severely_incomplete_ones_go():
    missing_three = product("Bar A", sugars_g=None, sodium_mg=None, saturated_fat_g=None)
    missing_four = product("Bar B", barcode="1", sugars_g=None, sodium_mg=None, saturated_fat_g=None, protein_g=None)
    no_energy = product("Bar C", barcode="2", energy_kcal=None)
    assert assess_record(missing_three)["eligible"] is True
    assert assess_record(missing_four)["eligible"] is False
    assert assess_record(no_energy)["eligible"] is False
    ranked, removed = rank_products([missing_three, missing_four, no_energy])
    assert names(ranked) == ["Bar A"]
    assert removed["ineligible"] == 2


def test_missing_optional_fields_never_make_a_product_ineligible():
    record = product("Bar", dietary_fibre_g=None, added_sugars_g=None, trans_fat_g=None, cholesterol_mg=None)
    assert assess_record(record)["eligible"] is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"sugars_g": 70, "carbohydrates_g": 58},  # sugars above carbohydrates
        {"saturated_fat_g": 40, "total_fat_g": 30},  # saturated fat above total fat
        {"energy_kcal": 2000},  # above the physical maximum per 100 g
        {"sodium_mg": -5},  # negative
        {"protein_g": "abc", "sugars_g": "n/a", "sodium_mg": "", "total_fat_g": None},  # unreadable = missing
        {"measurement_basis": "unspecified"},  # values can't be interpreted
    ],
)
def test_invalid_or_unreadable_values_make_a_record_ineligible(overrides):
    assert assess_record(product("Bar", **overrides))["eligible"] is False


def test_missing_values_are_never_counted_as_zero():
    zero = product("Zero Sugar Bar", sugars_g=0)
    missing = product("Unknown Sugar Bar", sugars_g=None)
    assert assess_record(zero)["missing_essential"] == []
    assert assess_record(missing)["missing_essential"] == ["sugars_g"]
    assert assess_record(zero)["completeness"] > assess_record(missing)["completeness"]


def test_duplicates_are_merged_keeping_the_more_complete_record():
    sparse = product("Cadbury Dairy Milk", ingredients="", allergens_declared="")
    complete = product("CADBURY DAIRY MILK")  # same barcode
    no_barcode_a = product("Gems", barcode="", sugars_g=60)
    no_barcode_b = product("gems", barcode="", sugars_g=60, ingredients="")  # same brand, name and values
    ranked, removed = rank_products([sparse, complete, no_barcode_a, no_barcode_b])
    assert removed["duplicates"] == 2
    assert names(ranked) == ["CADBURY DAIRY MILK", "Gems"]


def test_empty_results_are_handled():
    assert rank_products([], "anything") == ([], {"ineligible": 0, "duplicates": 0})


# ---------- Indian-market evidence ----------

def test_sold_in_india_comes_only_from_country_data():
    base = {"product_name": "Glucose Biscuits", "brands": "Parle", "nutriments": {}}
    assert map_off_product_to_eatgood("8901719110016", {**base, "countries_tags": ["en:india"]})["sold_in_india"] is True
    assert map_off_product_to_eatgood("8901719110016", {**base, "countries_tags": ["en:france"]})["sold_in_india"] is False
    # An Indian brand and an 890 (India) barcode prefix are not evidence on their own.
    assert map_off_product_to_eatgood("8901719110016", base)["sold_in_india"] is None


def test_india_evidence_only_breaks_ties_and_unknown_is_not_treated_as_sold():
    in_india = product("Cadbury Dairy Milk A", barcode="3333")
    unknown = product("Cadbury Dairy Milk B", barcode="4444", sold_in_india=None)
    abroad = product("Cadbury Dairy Milk C", barcode="5555", sold_in_india=False)
    assert assess_record(in_india)["quality"] > assess_record(unknown)["quality"] == assess_record(abroad)["quality"]
    ranked, _ = rank_products([abroad, unknown, in_india], "cadbury dairy milk")
    assert names(ranked)[0] == "Cadbury Dairy Milk A"
    exact_abroad = product("Cadbury Dairy Milk", barcode="6666", sold_in_india=False)
    ranked, _ = rank_products([in_india, exact_abroad], "cadbury dairy milk")
    assert names(ranked)[0] == "Cadbury Dairy Milk"  # relevance still comes first


# ---------- the same rules everywhere ----------

POOL = [fx.by_name("Masala Bhujia Test"), fx.by_name("Incomplete Label Test"), fx.by_name("Partial Label Test"),
        dict(fx.by_name("Masala Bhujia Test"))]


def test_catalogue_search_browsing_and_alternatives_apply_the_same_rules(monkeypatch):
    monkeypatch.setattr(off_catalogue, "search_openfoodfacts", lambda *a, **k: {"status": "ok", "products": POOL, "count": len(POOL)})
    expected = {"Masala Bhujia Test", "Partial Label Test"}
    assert set(names(off_catalogue.browse_catalogue(text="test")["products"])) == expected
    assert set(names(off_catalogue.browse_catalogue()["products"])) == expected
    alternatives = off_catalogue.alternative_candidates({"category": "Snacks", "barcode": "x"})
    assert set(names(alternatives["products"])) == expected


def test_product_search_endpoint_applies_the_same_rules(monkeypatch):
    from backend.routes import catalogue

    monkeypatch.setattr(catalogue, "search_openfoodfacts_text", lambda term, limit, page: {"status": "ok", "products": POOL, "count": 4})
    data = client.get("/api/products/search/openfoodfacts?q=test").json()
    assert sorted(names(data["products"])) == ["Masala Bhujia Test", "Partial Label Test"]


def test_catalogue_endpoint_excludes_severely_incomplete_products():
    listed = names(client.get("/api/products?limit=100").json()["products"])
    assert "Incomplete Label Test" not in listed
    assert "Partial Label Test" in listed


# ---------- existing behaviour preserved ----------

def test_an_exact_barcode_lookup_still_returns_an_incomplete_product():
    """Scanning a barcode asks for that product, so it is shown (with honest 'not enough data')."""
    data = client.get("/api/products/barcode/2000000000121").json()
    assert data["status"] == "found"
    assert data["assessment"]["layer1_general"]["grade"] == "Insufficient Data"
    assert data["assessment"]["layer2_personalized"]["personalized_score"] is None


def test_scoring_and_allergen_override_are_unchanged_for_listed_products():
    header = {"X-Eatgood-Profile": '%7B%22allergens_to_avoid%22%3A%22Milk%22%7D'}
    items = client.get("/api/products?query=cheese%20puffs", headers=header).json()["products"]
    assert items[0]["product_name"] == "Cheese Puffs Test"
    assert items[0]["has_allergen_conflict"] is True
    assert items[0]["personalized_score"] == 0
