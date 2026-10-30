"""Gemini-backed helpers: reading label and claim photos. Each returns 503 AI_UNAVAILABLE when
Gemini can't be used (no key, paused, daily budget spent), and the page falls back to its own way."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from backend.core import gemini, ml_models
from backend.core.rate_limiter import enforce_rate_limit
from backend.core.allergen_engine import analyze_additives
from backend.core.coach import ask_coach, coach_insights
from backend.profile import get_request_profile
from backend.core.assistant_ai import explain_ingredients
from backend.products import OpenFoodFactsUnavailable, cached_product, resolve_product
from backend.schemas import AiImageRequest, CoachRequest, IngredientsRequest, NutritionFields

router = APIRouter(prefix="/api/ai")

NUTRIENTS = list(NutritionFields.model_fields)

LABEL_PROMPT = (
    "This is a photo of a packaged food's nutrition label (often Indian). Read only what is printed. "
    "Use the per 100 g or per 100 ml column when there is one, and set basis to match; otherwise use the "
    "per serving column with basis 'per serving'. Sodium in mg (if only salt in g is printed, sodium mg = "
    "salt g x 400). Energy in kcal. Use null for anything not printed or unreadable; never guess."
)
LABEL_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "product_name": {"type": "STRING", "nullable": True},
        "brand": {"type": "STRING", "nullable": True},
        "basis": {"type": "STRING", "enum": ["per 100g", "per 100ml", "per serving"]},
        "serving_size": {"type": "NUMBER", "nullable": True},
        **{name: {"type": "NUMBER", "nullable": True} for name in NUTRIENTS},
        "ingredients": {"type": "STRING", "nullable": True},
        "allergens": {"type": "STRING", "nullable": True},
    },
    "required": ["basis"],
}

CLAIMS_PROMPT = (
    "This is a photo of the front of a food pack. List the marketing, nutrition and health claims printed "
    "on it (for example 'High protein', 'No added sugar', 'Baked not fried', '30% less fat'), each as a "
    "short phrase as printed. Leave out the brand, product name, flavour, weight, price and pictures. "
    "Return an empty list if there are no claims."
)
CLAIMS_SCHEMA = {
    "type": "OBJECT",
    "properties": {"claims": {"type": "ARRAY", "items": {"type": "STRING"}}},
    "required": ["claims"],
}


def _unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail={"error_code": "AI_UNAVAILABLE", "message": "Photo reading isn't available right now."})


def _read(request: Request, body: AiImageRequest, prompt: str, schema: dict[str, Any], max_tokens: int) -> Any:
    enforce_rate_limit(request, "ai")
    if gemini.decode_image(body.image) is None:
        raise HTTPException(status_code=400, detail={"error_code": "BAD_IMAGE", "message": "That photo couldn't be read."})
    if not gemini.is_available():
        raise _unavailable()
    result = gemini.generate_json(prompt, schema, image=gemini.image_part(body.image, body.mime_type), max_output_tokens=max_tokens)
    if result is None:
        raise _unavailable()
    return result


@router.get("/status")
def ai_status():
    # "models": which separately trained models are installed (none until model files are added).
    return {"available": gemini.is_available(), "models": ml_models.status()}


@router.post("/read-label")
def read_label(body: AiImageRequest, request: Request):
    """Values read from a nutrition label photo, for the visitor to check in the Manual Entry form."""
    raw = _read(request, body, LABEL_PROMPT, LABEL_SCHEMA, 600)
    values: dict[str, Any] = {}
    for name in NUTRIENTS:
        try:
            values.update(NutritionFields(**{name: raw.get(name)}).model_dump(include={name}))
        except ValidationError:
            values[name] = None  # out of range: left for the visitor to fill in
    return {
        "values": values,
        "measurement_basis": raw.get("basis") if raw.get("basis") in ("per 100g", "per 100ml", "per serving") else "per 100g",
        "serving_size": raw.get("serving_size") if isinstance(raw.get("serving_size"), (int, float)) and 0 < raw["serving_size"] <= 10000 else None,
        "product_name": str(raw.get("product_name") or "")[:200],
        "brand": str(raw.get("brand") or "")[:120],
        "ingredients": str(raw.get("ingredients") or "")[:5000],
        "allergens": str(raw.get("allergens") or "")[:1000],
    }


@router.post("/read-claims")
def read_claims(body: AiImageRequest, request: Request):
    """Claims read from a photo of the front of the pack."""
    raw = _read(request, body, CLAIMS_PROMPT, CLAIMS_SCHEMA, 300)
    claims = [str(c).strip()[:80] for c in raw.get("claims") or [] if str(c).strip()]
    return {"claims": list(dict.fromkeys(claims))[:12]}


@router.post("/explain-ingredients")
def explain_product_ingredients(body: IngredientsRequest, request: Request):
    """What each ingredient on this product's list is and why it's used, with notes worth knowing."""
    if body.ingredients is not None:
        ingredients = body.ingredients
    else:
        try:
            product = resolve_product(body.product_id or "")
        except OpenFoodFactsUnavailable:
            product = None
        if not product:
            raise HTTPException(status_code=404, detail={"error_code": "PRODUCT_NOT_FOUND", "message": "That product couldn't be found."})
        ingredients = product.get("ingredients") or ""
    if not ingredients.strip():
        raise HTTPException(status_code=400, detail={"error_code": "NO_INGREDIENTS", "message": "This product has no ingredients list."})
    enforce_rate_limit(request, "ai")
    if not gemini.is_available():
        raise _unavailable()
    items = explain_ingredients(ingredients, analyze_additives(ingredients)["additives_list"])
    if items is None:
        raise _unavailable()
    return {"items": items}


def _load_one(pid: str) -> dict | None:
    try:
        return resolve_product(pid)
    except OpenFoodFactsUnavailable:
        return None


def _own_products(ids: list[str], cached_only: bool = False) -> list[dict]:
    """The visitor's saved and recent catalogue products (own entries skipped). cached_only uses just what
    the server already has, with no network calls; otherwise missing ones are loaded in parallel."""
    wanted = [pid for pid in dict.fromkeys(ids) if pid.startswith(("OFF_", "USER_SUB_"))]
    if cached_only:
        return [p for p in (cached_product(pid) for pid in wanted) if p]
    with ThreadPoolExecutor(max_workers=6) as pool:
        return [p for p in pool.map(_load_one, wanted) if p]


@router.post("/coach/insights")
def food_insights(body: CoachRequest, profile: dict = Depends(get_request_profile)):
    """Patterns across the visitor's saved products and history; no new scores."""
    return coach_insights(_own_products(body.product_ids), profile)


@router.post("/coach/ask")
def ask_food_coach(body: CoachRequest, request: Request, profile: dict = Depends(get_request_profile)):
    """Products from the catalogue that fit the question and the visitor's profile, with a short answer
    when available. Products with the visitor's allergens or diet conflicts are never suggested."""
    if not body.question.strip():
        raise HTTPException(status_code=400, detail={"error_code": "NO_QUESTION", "message": "Type a question first."})
    enforce_rate_limit(request, "off_search")
    if gemini.is_available():
        enforce_rate_limit(request, "ai")
    return ask_coach(body.question.strip(), profile, _own_products(body.product_ids, cached_only=True))
