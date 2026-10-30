"""Data-quality flags and the optional trained-model slots."""

import json

from backend.core import ml_models
from backend.core.data_quality import quality_flags
from backend.core.nutrition_scoring import assess_general_nutrition, run_full_product_assessment


def snack(**overrides):
    return {"category": "Snacks", "measurement_basis": "per 100g", "energy_kcal": 500, "carbohydrates_g": 60,
            "protein_g": 7, "total_fat_g": 26, "sugars_g": 4, "saturated_fat_g": 9, "sodium_mg": 600,
            "ingredients": "potato, palm oil, salt", **overrides}


def codes(product):
    return {f["code"] for f in quality_flags(product)}


def test_a_consistent_label_has_no_flags():
    assert codes(snack()) == set()


def test_energy_that_doesnt_match_the_macronutrients_is_flagged():
    assert "energy_mismatch" in codes(snack(energy_kcal=150))  # 60 g carbs + 26 g fat is about 500 kcal


def test_unusual_sodium_and_empty_panels_are_flagged():
    assert "sodium_unusual" in codes(snack(sodium_mg=12000))
    assert "sodium_unusual" not in codes(snack(category="Condiments & Spreads", sodium_mg=12000))
    zero = snack(energy_kcal=0, carbohydrates_g=0, protein_g=0, total_fat_g=0, sugars_g=0, saturated_fat_g=0, sodium_mg=0)
    assert "all_zero" in codes(zero)
    assert "no_ingredients" in codes(snack(ingredients=""))


def test_flags_never_change_the_grade():
    clean, odd = snack(), snack(energy_kcal=150)
    assert assess_general_nutrition(clean)["grade"] == assess_general_nutrition(snack(energy_kcal=500))["grade"]
    result = run_full_product_assessment({**odd, "product_id": "X", "product_name": "Test"}, {"goal": "Balanced Choices"})
    assert any(f["code"] == "energy_mismatch" for f in result["data_quality_flags"])


def test_without_model_files_every_slot_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr(ml_models, "MODELS_DIR", tmp_path)
    ml_models._load.cache_clear()
    assert ml_models.status() == {"category": False, "quality": False, "recommender": False}
    assert ml_models.predict_category("Masala Peanuts", "peanuts, salt") is None
    assert ml_models.quality_model_flags(snack()) == []


def test_installed_models_are_used(tmp_path, monkeypatch):
    (tmp_path / "category_model.json").write_text(json.dumps({
        "type": "linear_text", "version": "test", "labels": ["Snacks", "Dairy"],
        "vocabulary": {"peanuts": 0, "milk": 1}, "weights": [[3.0, -3.0], [-3.0, 3.0]], "bias": [0, 0], "min_confidence": 0.6,
    }))
    (tmp_path / "quality_model.json").write_text(json.dumps({
        "type": "linear_features", "version": "test", "features": ["sodium_mg"], "weights": [0.01], "bias": -5, "threshold": 0.5,
        "message": "Unusual for this kind of product.",
    }))
    monkeypatch.setattr(ml_models, "MODELS_DIR", tmp_path)
    ml_models._load.cache_clear()
    try:
        assert ml_models.status()["category"] is True
        assert ml_models.predict_category("Masala Peanuts", "peanuts, salt") == "Snacks"
        assert ml_models.predict_category("Fresh Milk", "toned milk") == "Dairy"
        assert ml_models.predict_category("Mystery", "water") is None  # not confident
        assert ml_models.quality_model_flags(snack(sodium_mg=900))[0]["code"] == "model_suspicious"
        assert ml_models.quality_model_flags(snack(sodium_mg=100)) == []
    finally:
        ml_models._load.cache_clear()
