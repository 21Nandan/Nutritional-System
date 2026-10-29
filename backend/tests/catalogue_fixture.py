"""
Test catalogue: invented products in Open Food Facts' raw format, mapped through the real
map_off_product_to_eatgood(). Barcodes use the GS1 "restricted circulation" prefix 20, which
is never assigned to real products. None of these values describe a real product.
"""

from typing import Any

from backend.core.openfoodfacts import map_off_product_to_eatgood
from backend.core.product_quality import rank_products
from backend.core.standards_registry import nutrient_flags


def _raw(code, name, brand, tags, nutriments, ingredients="", allergens=(), per=None, countries=("en:india",)):
    raw: dict[str, Any] = {
        "countries_tags": list(countries),
        "code": code,
        "product_name": name,
        "brands": brand,
        "categories_tags": tags,
        "nutriments": nutriments,
        "ingredients_text": ingredients,
        "allergens_tags": list(allergens),
    }
    if per:
        raw["nutrition_data_per"] = per
    return raw


def _n(kcal=None, sugars=None, sodium_mg=None, sat=None, protein=None, fibre=None, fat=None, carbs=None, trans=None):
    values = {
        "energy-kcal_100g": kcal, "sugars_100g": sugars, "saturated-fat_100g": sat, "proteins_100g": protein,
        "fiber_100g": fibre, "fat_100g": fat, "carbohydrates_100g": carbs, "trans-fat_100g": trans,
        "sodium_100g": None if sodium_mg is None else sodium_mg / 1000,
    }
    return {k: v for k, v in values.items() if v is not None}


SNACKS = ["en:snacks", "en:salty-snacks", "en:crisps"]

RAW_PRODUCTS = [
    _raw("2000000000015", "Masala Bhujia Test", "Test Brand A", SNACKS,
         _n(540, 2.7, 493.5, 11.2, 5.6, 4.6, 30, 50, 0.07), "Gram flour, edible vegetable oil, salt, spices"),
    _raw("2000000000022", "Milk Chocolate Bar Test", "Test Brand B", ["en:sweet-snacks", "en:chocolates"],
         _n(530, 56, 90, 18, 7, 2, 30, 58), "Sugar, cocoa butter, milk solids, soy lecithin", ["en:milk", "en:soybeans"]),
    _raw("2000000000039", "Cheese Puffs Test", "Test Brand A", SNACKS,
         _n(520, 3, 700, 9, 6, 1.5, 28, 55), "Corn, vegetable oil, cheese powder, salt", ["en:milk"]),
    _raw("2000000000046", "Peanut Crunch Test", "Test Brand C", SNACKS,
         _n(560, 4, 300, 6, 20, 6, 40, 30), "Peanuts, gram flour, salt", ["en:peanuts"]),
    _raw("2000000000053", "Baked Oat Crackers Test", "Test Brand D", SNACKS,
         _n(420, 2, 100, 1, 11, 7, 12, 60, 0), "Oats, sunflower oil, salt"),
    _raw("2000000000060", "Glucose Biscuits Test", "Test Brand B", ["en:biscuits-and-cakes", "en:biscuits"],
         _n(450, 25, 300, 8, 7, 2, 14, 75), "Wheat flour, sugar, milk solids", ["en:gluten", "en:milk"]),
    _raw("2000000000077", "Orange Drink Test", "Test Brand E", ["en:beverages", "en:sweetened-beverages"],
         _n(45, 11, 10, 0, 0, 0, 0, 11), "Water, sugar, orange concentrate", per="100ml", countries=("en:france",)),
    _raw("2000000000084", "Instant Noodles Test", "Test Brand F", ["en:noodles", "en:instant-noodles"],
         _n(430, 2, 1200, 7, 9, 3, 16, 60), "Wheat flour, palm oil, salt, spices, flavour enhancers (INS 627, INS 631)", ["en:gluten"]),
    _raw("2000000000091", "Plain Yogurt Test", "Test Brand G", ["en:dairies", "en:yogurts"],
         _n(60, 4.5, 50, 2, 3.5, 0, 3, 5), "Milk, live cultures", ["en:milk"]),
    _raw("2000000000107", "Corn Flakes Test", "Test Brand H", ["en:breakfast-cereals", "en:corn-flakes"],
         _n(380, 8, 600, 0.5, 7, 3, 1, 84), "Corn, sugar, salt"),
    _raw("2000000000114", "Mystery Snack Test", "Test Brand C", SNACKS,
         _n(500, 5, 450, 5, 6, 2, 25, 60), countries=()),
    # Severely incomplete: 6 of 7 key nutrition values missing. Never listed.
    _raw("2000000000121", "Incomplete Label Test", "Test Brand D", SNACKS, _n(kcal=480), "Rice, oil"),
    # Missing 3 key values (sugars, sodium, saturated fat): listed, but it can't be graded or scored.
    _raw("2000000000138", "Partial Label Test", "Test Brand D", SNACKS,
         _n(kcal=470, protein=8, fat=20, carbs=62), "Rice flour, oil, spices"),
]


def _product(raw: dict) -> dict:
    product = map_off_product_to_eatgood(raw["code"], raw)
    product["nutrient_flags"] = nutrient_flags(product)
    product["is_local"] = False
    return product


# Community ratings reported with one product, to check they are still shown.
RAW_PRODUCTS[2].update(nutriscore_grade="d", nova_group=4)

PRODUCTS = [_product(r) for r in RAW_PRODUCTS]
BY_BARCODE = {p["barcode"]: p for p in PRODUCTS}


def by_name(name: str) -> dict:
    return next(p for p in PRODUCTS if p["product_name"] == name)


def fake_fetch(barcode: str) -> dict:
    """Stands in for the live Open Food Facts product lookup."""
    if barcode in BY_BARCODE:
        return {"status": "success", "product": dict(BY_BARCODE[barcode]), "barcode": barcode}
    return {"status": "not_found", "error_code": "OFF_PRODUCT_NOT_FOUND", "barcode": barcode}


_LIMIT_FIELDS = {
    "max_sugars": ("sugars_g", lambda v, x: v is not None and v <= x),
    "max_sodium": ("sodium_mg", lambda v, x: v is not None and v <= x),
    "max_sat_fat": ("saturated_fat_g", lambda v, x: v is not None and v <= x),
    "min_fibre": ("dietary_fibre_g", lambda v, x: v is not None and v >= x),
    "min_protein": ("protein_g", lambda v, x: v is not None and v >= x),
}


def fake_browse(text="", category="All", india_only=True, nutrient_filters=None, has_image=False, limit=30, page=1):
    """Stands in for the Open Food Facts catalogue search: every word must be in the name or brand.
    The results then go through the real eligibility and ranking rules."""
    words = text.lower().split()
    items = [p for p in PRODUCTS if all(w in f"{p['product_name']} {p['brand']}".lower() for w in words)]
    if category not in ("All", ""):
        items = [p for p in items if p["category"] == category]
    for key, limit_value in (nutrient_filters or {}).items():
        if limit_value is not None:
            field, ok = _LIMIT_FIELDS[key]
            items = [p for p in items if ok(p.get(field), limit_value)]
    items, _ = rank_products(items, text)
    start = (page - 1) * limit
    return {"status": "ok", "products": items[start:start + limit], "count": len(items),
            "interpreted_intent": None, "match_mode": "words"}


def fake_alternative_candidates(product: dict, limit: int = 40) -> dict:
    same = [p for p in PRODUCTS if p["category"] == product.get("category") and p["barcode"] != product.get("barcode")]
    same, _ = rank_products(same[:limit])
    return {"status": "ok", "products": same, "count": len(same)}
