"""
Nutrition-data quality checks: values that are possible but look suspicious, so the visitor can check
them against the pack. They never change the grade (impossible values are already refused by
nutrition_validator). A trained quality model, if one is installed (ml_models), adds its own flags.
"""

from typing import Any

from backend.core import ml_models
from backend.core.nutrition_validator import parse_float_safe

ENERGY_FIELDS = ("carbohydrates_g", "protein_g", "total_fat_g")
# Sodium above this per 100 g is very unusual outside salt, sauces, pickles and stock cubes.
SODIUM_UNUSUAL_MG = 3000.0
SALTY_CATEGORIES = {"Condiments & Spreads"}


def _num(product: dict[str, Any], key: str) -> float | None:
    return parse_float_safe(product.get(key))


def quality_flags(product: dict[str, Any]) -> list[dict[str, str]]:
    """[{"code", "message"}] for values worth checking against the pack; empty when nothing looks off."""
    flags: list[dict[str, str]] = []
    basis = str(product.get("measurement_basis") or "per 100g").lower().replace(" ", "")
    per_100 = basis in ("per100g", "per100ml")
    energy = _num(product, "energy_kcal")
    carbs, protein, fat = (_num(product, k) for k in ENERGY_FIELDS)

    # Energy should roughly equal 4 kcal per g of carbohydrate and protein plus 9 per g of fat. Fibre,
    # polyols and rounding explain small gaps, so only a gap of more than 35% (and 40 kcal) is flagged.
    if energy is not None and None not in (carbs, protein, fat):
        expected = 4 * carbs + 4 * protein + 9 * fat
        if expected > 0 and abs(energy - expected) > max(40.0, 0.35 * max(energy, expected)):
            flags.append({"code": "energy_mismatch", "message":
                          f"Energy ({energy:g} kcal) doesn't match the carbohydrate, protein and fat values "
                          f"(about {expected:.0f} kcal). One of them may be misread."})

    sodium = _num(product, "sodium_mg")
    if per_100 and sodium is not None and sodium > SODIUM_UNUSUAL_MG and product.get("category") not in SALTY_CATEGORIES:
        flags.append({"code": "sodium_unusual", "message":
                      f"Sodium ({sodium:g} mg per 100) is unusually high for this kind of food. It may be a "
                      "salt value or a per-pack value entered as sodium."})

    stated = [v for v in (_num(product, k) for k in ("energy_kcal", "sugars_g", "saturated_fat_g", "sodium_mg", *ENERGY_FIELDS)) if v is not None]
    if len(stated) >= 4 and all(v == 0 for v in stated):
        flags.append({"code": "all_zero", "message": "Every nutrition value is 0, which usually means the panel wasn't filled in."})

    if per_100 and energy is not None and 0 < energy < 25 and basis == "per100g" and (fat or 0) + (carbs or 0) > 0:
        flags.append({"code": "energy_low", "message":
                      f"Energy ({energy:g} kcal per 100 g) is very low for a solid food; the values may be per serving."})

    if not str(product.get("ingredients") or "").strip():
        flags.append({"code": "no_ingredients", "message": "The ingredients list is missing, so allergens and additives can't be fully checked."})

    for extra in ml_models.quality_model_flags(product):
        if extra["code"] not in {f["code"] for f in flags}:
            flags.append(extra)
    return flags
