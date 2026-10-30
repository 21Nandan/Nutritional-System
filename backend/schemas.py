"""Request models. Pydantic validates every request body before any business logic runs."""

from typing import Literal

from pydantic import BaseModel, Field

CATEGORIES = Literal[
    "Snacks",
    "Breakfast Cereals",
    "Packaged Beverages",
    "Biscuits & Bakery",
    "Chocolates & Sweets",
    "Instant Foods",
    "Dairy",
    "Condiments & Spreads",
]
BASES = Literal["per 100g", "per 100ml", "per serving"]


class NutritionFields(BaseModel):
    """Nutrient values exactly as the user confirmed them. None means 'not on the label', never 0."""

    energy_kcal: float | None = Field(default=None, ge=0, le=5000)
    carbohydrates_g: float | None = Field(default=None, ge=0, le=5000)
    sugars_g: float | None = Field(default=None, ge=0, le=5000)
    added_sugars_g: float | None = Field(default=None, ge=0, le=5000)
    protein_g: float | None = Field(default=None, ge=0, le=5000)
    total_fat_g: float | None = Field(default=None, ge=0, le=5000)
    saturated_fat_g: float | None = Field(default=None, ge=0, le=5000)
    trans_fat_g: float | None = Field(default=None, ge=0, le=5000)
    sodium_mg: float | None = Field(default=None, ge=0, le=100000)
    dietary_fibre_g: float | None = Field(default=None, ge=0, le=5000)


class ManualNutritionInput(NutritionFields):
    product_name: str = Field(min_length=1, max_length=200)
    brand: str = Field(default="", max_length=120)
    category: CATEGORIES = "Snacks"
    serving_size: float | None = Field(default=None, gt=0, le=10000)
    serving_size_unit: Literal["g", "ml"] = "g"
    measurement_basis: BASES = "per 100g"
    ingredients: str = Field(default="", max_length=5000)
    allergens_declared: str = Field(default="", max_length=1000)
    marketing_claims: str = Field(default="", max_length=1000)


class ProductContributionRequest(NutritionFields):
    barcode: str = Field(min_length=6, max_length=14, pattern=r"^\d+$")
    product_name: str = Field(min_length=2, max_length=200)
    brand: str = Field(default="", max_length=120)
    category: CATEGORIES = "Snacks"
    sub_category: str = Field(default="", max_length=120)
    serving_size: float | None = Field(default=None, gt=0, le=10000)
    serving_size_unit: Literal["g", "ml"] = "g"
    measurement_basis: BASES = "per 100g"
    ingredients: str = Field(default="", max_length=5000)
    allergens_declared: str = Field(default="", max_length=1000)
    submission_notes: str = Field(default="", max_length=1000)


class AssistantQuery(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=500)


class ClaimProductValues(NutritionFields):
    """The values shown on a product page; any category, since claims don't depend on it."""

    product_name: str = Field(default="", max_length=200)
    category: str = Field(default="", max_length=80)
    measurement_basis: BASES = "per 100g"
    ingredients: str | None = Field(default="", max_length=5000)
    allergens_declared: str | None = Field(default="", max_length=1000)


class ClaimCheckRequest(BaseModel):
    """Claims read from a pack, checked against a catalogue product (product_id) or the page's values (product)."""

    claims: str = Field(min_length=1, max_length=2000)
    product_id: str | None = Field(default=None, max_length=64)
    product: ClaimProductValues | None = None
