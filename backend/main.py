"""
EATGOOD — FastAPI Backend Application
Main entry point serving REST APIs for food analysis, personalized nutrition grading,
product comparison, healthier recommendations, OCR label extraction, and data audits.
"""

import os
import shutil
import json
import uuid
import re
import io
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from PIL import Image

from backend.config import (
    CORS_ORIGINS,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_MIME_TYPES
)
from backend.core.rate_limiter import enforce_rate_limit
from backend.core.data_loader import data_loader
from backend.core.nutrition_scoring import run_full_product_assessment, assess_general_nutrition, assess_personalized_suitability
from backend.core.standards_registry import (
    STANDARDS_REGISTRY,
    CALIBRATED_CATEGORIES,
    STANDARDS_REGISTRY_VERSION,
    CATEGORY_CALIBRATION_SPECS
)
from backend.core.recommender import get_healthier_alternatives
from backend.core.ml_model import ml_service
from backend.core.ocr_service import run_image_ocr, extract_nutrition_from_text, get_ocr_engine_info
from backend.core.barcode_utils import validate_barcode, clean_barcode
from backend.core.openfoodfacts import fetch_product_from_openfoodfacts, search_openfoodfacts_text
from backend.core.semantic_search import execute_semantic_search, parse_semantic_intent
from backend.core.assistant import answer_product_question
from backend.database import (
    get_connection,
    get_active_profile, save_active_profile,
    record_analysis_history, get_recent_history, clear_analysis_history,
    toggle_save_product, get_saved_product_ids,
    is_product_saved, get_saved_products_records, get_saved_product,
    record_scan_session, get_recent_scan_sessions,
    get_cached_barcode_product, cache_barcode_product,
    record_user_contribution, get_user_contributions, get_user_contribution_by_barcode
)

logger = logging.getLogger("eatgood")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")

app = FastAPI(
    title="EATGOOD API",
    description="AI-Powered Personalized Food Safety and Nutrition Assessment Engine",
    version="1.0.0"
)

cors_origins = CORS_ORIGINS if CORS_ORIGINS else ["*"]
allow_creds = "*" not in cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers_and_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

@app.middleware("http")
async def ensure_api_prefix(request: Request, call_next):
    # Never tamper with static assets, favicons, or client-side routes
    path = request.scope.get("path", "")
    is_static_or_doc = (
        path.startswith("/assets") or 
        path.startswith("/favicon") or 
        path.startswith("/apple-touch-icon") or
        path.startswith("/docs") or 
        path.startswith("/openapi.json") or
        path == "/" or path == "/health" or
        any(path.endswith(ext) for ext in [".js", ".css", ".png", ".svg", ".ico", ".jpg", ".jpeg", ".webp", ".woff", ".woff2"])
    )
    
    # In serverless environments, if an API call arrives without /api prefix, add it safely
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    if is_serverless and not is_static_or_doc and path and not path.startswith("/api"):
        request.scope["path"] = f"/api{path}"

    response = await call_next(request)
    return response

# Serverless-safe upload directory
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    UPLOAD_DIR = "/tmp/eatgood_uploads"
else:
    UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "uploads"))

try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except Exception:
    UPLOAD_DIR = "/tmp"

@app.get("/api/health")
@app.get("/health")
def health_check():
    count = len(data_loader.products_df) if data_loader.products_df is not None else 0
    return {
        "status": "healthy",
        "service": "EATGOOD API",
        "database": "connected",
        "products_count": count,
        "environment": "serverless" if (os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")) else "local"
    }

@app.get("/api/ready")
@app.get("/ready")
def readiness_check():
    db_status = "healthy"
    try:
        conn = get_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    data_loaded = (data_loader.products_df is not None and len(data_loader.products_df) > 0)
    
    if db_status != "healthy" or not data_loaded:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "database": db_status,
                "dataset_ready": data_loaded
            }
        )

    return {
        "status": "ready",
        "database": db_status,
        "dataset_ready": data_loaded,
        "products_count": len(data_loader.products_df)
    }

# ----------------- Models -----------------
class UserProfileModel(BaseModel):
    user_id: Optional[str] = "USR_DEFAULT"
    name: Optional[str] = "User"
    goal: str = "Balanced Choices"
    dietary_preference: str = "No preference"
    allergens_to_avoid: Optional[str] = ""
    age_group: Optional[str] = "18-24"
    activity_level: Optional[str] = "Moderately active"

class AssistantQueryModel(BaseModel):
    product_id: str
    question: str
    user_id: Optional[str] = None

class ManualNutritionInput(BaseModel):
    product_name: str
    brand: Optional[str] = "Custom / Unbranded"
    category: str = "Snacks"
    serving_size: Optional[float] = 100.0
    serving_size_unit: Optional[str] = "g"
    measurement_basis: Optional[str] = "per 100g"
    energy_kcal: Optional[float] = None
    carbohydrates_g: Optional[float] = None
    sugars_g: Optional[float] = None
    added_sugars_g: Optional[float] = None
    protein_g: Optional[float] = None
    total_fat_g: Optional[float] = None
    saturated_fat_g: Optional[float] = None
    trans_fat_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    dietary_fibre_g: Optional[float] = None
    ingredients: Optional[str] = ""
    allergens_declared: Optional[str] = ""
    marketing_claims: Optional[str] = ""

class ProductContributionRequest(BaseModel):
    barcode: str
    product_name: str
    brand: Optional[str] = "Unknown Brand"
    category: str = "Snacks"
    sub_category: Optional[str] = "User Contributed"
    serving_size: Optional[float] = 100.0
    serving_size_unit: Optional[str] = "g"
    measurement_basis: Optional[str] = "per 100g"
    energy_kcal: Optional[float] = None
    carbohydrates_g: Optional[float] = None
    sugars_g: Optional[float] = None
    added_sugars_g: Optional[float] = None
    protein_g: Optional[float] = None
    total_fat_g: Optional[float] = None
    saturated_fat_g: Optional[float] = None
    trans_fat_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    dietary_fibre_g: Optional[float] = None
    ingredients: Optional[str] = ""
    allergens_declared: Optional[str] = ""
    submission_notes: Optional[str] = "Local User Contribution — Pending Audit"

# ----------------- Routes -----------------

def get_profile_for_request(request: Optional[Request] = None, user_id: Optional[str] = None) -> dict:
    uid = user_id
    if not uid and request is not None:
        uid = request.query_params.get("user_id") or request.headers.get("x-user-id")
    return get_active_profile(uid)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "EATGOOD Nutritional Assessment API",
        "products_loaded": len(data_loader.products_df) if data_loader.products_df is not None else 0,
        "ml_model_status": "Ready (Experimental)" if ml_service.is_loaded else "Rule-based Fallback Active"
    }

@app.get("/api/products")
def list_products(
    query: Optional[str] = "",
    category: Optional[str] = "All",
    brand: Optional[str] = "All",
    max_sugars: Optional[float] = None,
    max_sodium: Optional[float] = None,
    max_sat_fat: Optional[float] = None,
    min_fibre: Optional[float] = None,
    min_protein: Optional[float] = None,
    has_image: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    deduplicate_variants: Optional[bool] = None,
    request: Request = None,
    user_id: Optional[str] = None
):
    """Retrieves paginated products with search query, category, image, and nutritional filters."""
    # Check for natural language semantic intent
    if query and not query.strip().isdigit() and not query.lower().startswith("ind_pkg_") and category in ["All", ""]:
        intent = parse_semantic_intent(query)
        if intent["nutrient_descriptions"] or intent["excluded_allergens"] or (intent["category"] and len(query.strip().split()) >= 2):
            profile = get_profile_for_request(request, user_id)
            return execute_semantic_search(
                query=query,
                products_df=data_loader.products_df,
                user_profile=profile,
                limit=limit,
                offset=offset
            )

    # When query is provided (e.g. searching 'cok' in compare modal or catalogue search),
    # deduplicate synthetic (Variant X) products so users see distinct products.
    # When browsing catalogue with no search query, preserve all catalogue products.
    if deduplicate_variants is not None:
        dedup = deduplicate_variants
    else:
        dedup = bool(query and query.strip())

    return data_loader.search_products(
        query=query,
        category=category,
        brand=brand,
        max_sugars=max_sugars,
        max_sodium=max_sodium,
        max_sat_fat=max_sat_fat,
        min_fibre=min_fibre,
        min_protein=min_protein,
        has_image=has_image,
        limit=limit,
        offset=offset,
        deduplicate_variants=dedup
    )

@app.get("/api/products/search")
def search_products_endpoint(
    q: Optional[str] = Query(None, description="Search keyword or product name"),
    query: Optional[str] = Query(None, description="Alternative query param"),
    category: Optional[str] = "All",
    brand: Optional[str] = "All",
    max_sugars: Optional[float] = None,
    max_sodium: Optional[float] = None,
    max_sat_fat: Optional[float] = None,
    min_fibre: Optional[float] = None,
    min_protein: Optional[float] = None,
    has_image: Optional[bool] = None,
    include_external: bool = Query(True, description="Query Open Food Facts if needed"),
    limit: int = 50,
    offset: int = 0,
    request: Request = None,
    user_id: Optional[str] = None
):
    """
    Multi-source product search endpoint accepting 'q' or 'query' parameters.
    Prioritizes the local Indian packaged food catalogue first, then falls back to or enriches
    with Open Food Facts results, intelligently deduplicating against local catalogue records.
    """
    term = (q if q is not None else (query or "")).strip()

    # Route pure nutrient/allergen constraint expressions to semantic search
    if term and not term.isdigit() and not term.lower().startswith("ind_pkg_") and category in ["All", ""]:
        intent = parse_semantic_intent(term)
        if intent["nutrient_descriptions"] or intent["excluded_allergens"]:
            profile = get_profile_for_request(request, user_id)
            return execute_semantic_search(
                query=term,
                products_df=data_loader.products_df,
                user_profile=profile,
                limit=limit,
                offset=offset
            )

    # 1. Search local Indian catalogue first
    local_res = data_loader.search_products(
        query=term,
        category=category,
        brand=brand,
        max_sugars=max_sugars,
        max_sodium=max_sodium,
        max_sat_fat=max_sat_fat,
        min_fibre=min_fibre,
        min_protein=min_protein,
        has_image=has_image,
        limit=limit,
        offset=offset,
        deduplicate_variants=bool(term)
    )

    local_prods = local_res.get("products", [])

    # 2. If external discovery is enabled and search query has at least 2 characters, query Open Food Facts
    filtered_external = []
    if include_external and term and len(term) >= 2 and not term.isdigit() and not term.lower().startswith("ind_pkg_"):
        try:
            # Query official Open Food Facts text search API
            off_prods = search_openfoodfacts_text(term, limit=min(limit, 8))
            
            # Deduplicate against local catalogue: check both returned local items and all local barcodes
            local_barcodes = set()
            if data_loader.products_df is not None and "barcode" in data_loader.products_df.columns:
                local_barcodes = {str(b).strip() for b in data_loader.products_df["barcode"].dropna().tolist()}

            local_names = {
                (str(r.get("brand", "")).strip().lower(), str(r.get("product_name", "")).strip().lower())
                for r in local_prods
            }

            for op in off_prods:
                op_code = str(op.get("barcode") or "").strip()
                if op_code and op_code in local_barcodes:
                    continue
                op_key = (
                    str(op.get("brand") or "").strip().lower(),
                    str(op.get("product_name") or "").strip().lower()
                )
                if op_key in local_names:
                    continue
                filtered_external.append(op)
        except Exception as e:
            logger.warning("Open Food Facts search discovery skipped due to error: %s", e)

    merged = local_prods + filtered_external
    return {
        "query": term,
        "total": len(merged),
        "local_count": len(local_prods),
        "external_count": len(filtered_external),
        "products": merged[:limit]
    }

@app.get("/api/products/categories")
def get_categories():
    if data_loader.products_df is None or data_loader.products_df.empty:
        return {"categories": []}
    cats = sorted(data_loader.products_df["category"].dropna().unique().tolist())
    return {
        "categories": ["All"] + cats,
        "calibrated_categories": CALIBRATED_CATEGORIES
    }

@app.get("/api/search/semantic")
def search_semantic_endpoint(
    q: str = Query(..., description="Natural language search query e.g. 'Less salty snacks for evening'"),
    limit: int = 50,
    offset: int = 0,
    request: Request = None,
    user_id: Optional[str] = None
):
    """
    Translates natural language food queries into structured nutritional constraints,
    allergen exclusions, and hybrid relevance-ranked products.
    """
    profile = get_profile_for_request(request, user_id)
    return execute_semantic_search(
        query=q,
        products_df=data_loader.products_df,
        user_profile=profile,
        limit=limit,
        offset=offset
    )

@app.post("/api/assistant/ask")
def ask_assistant_endpoint(
    query_data: AssistantQueryModel,
    request: Request = None
):
    """
    Evaluates consumer inquiries grounded in product facts, statutory guidelines,
    and deterministic Layer 1 / Layer 2 / Layer 3 assessments.
    """
    uid = query_data.user_id or (request.headers.get("x-user-id") if request else None)
    profile = get_profile_for_request(request, uid)
    product = data_loader.get_product_by_id(query_data.product_id)
    if not product:
        if query_data.product_id.strip().isdigit():
            product = data_loader.get_product_by_barcode(query_data.product_id.strip())
        if not product:
            product = get_cached_barcode_product(query_data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found for assistant evaluation.")

    return answer_product_question(
        product=product,
        question=query_data.question,
        user_profile=profile
    )

# ----------------- Barcode Discovery & Contributions (Preceding {product_id}) -----------------

@app.get("/api/products/contributions")
def list_user_contributions(limit: int = 50):
    """Returns recently submitted user contributions from SQLite."""
    return {"contributions": get_user_contributions(limit=limit)}

@app.post("/api/products")
@app.post("/api/products/contribute")
def contribute_new_product(payload: ProductContributionRequest, request: Request = None):
    """
    Allows user to submit an unlisted product with packaging nutrition details.
    Saves record locally in SQLite under 'user_submitted' status (never falsely verified).
    """
    if request:
        enforce_rate_limit(request, "contribution")

    clean_code = str(payload.barcode).strip()
    val = validate_barcode(clean_code, strict=False)
    if not val["is_valid"]:
        raise HTTPException(status_code=400, detail=val["error"] or "Invalid barcode format.")

    # Check if duplicate in local catalogue
    if data_loader.get_product_by_barcode(clean_code):
        raise HTTPException(status_code=409, detail=f"A product with barcode {clean_code} already exists in EATGOOD.")

    nutrition_dict = {
        "energy_kcal": payload.energy_kcal,
        "carbohydrates_g": payload.carbohydrates_g,
        "sugars_g": payload.sugars_g,
        "added_sugars_g": payload.added_sugars_g,
        "protein_g": payload.protein_g,
        "total_fat_g": payload.total_fat_g,
        "saturated_fat_g": payload.saturated_fat_g,
        "trans_fat_g": payload.trans_fat_g,
        "sodium_mg": payload.sodium_mg,
        "dietary_fibre_g": payload.dietary_fibre_g
    }

    sub_id = record_user_contribution({
        "barcode": clean_code,
        "product_name": payload.product_name,
        "brand": payload.brand,
        "category": payload.category,
        "sub_category": payload.sub_category,
        "serving_size": payload.serving_size,
        "serving_size_unit": payload.serving_size_unit,
        "measurement_basis": payload.measurement_basis,
        "nutrition_data": nutrition_dict,
        "ingredients": payload.ingredients,
        "allergens_declared": payload.allergens_declared,
        "submission_notes": payload.submission_notes,
        "review_status": "user_submitted"
    })

    return {
        "status": "success",
        "submission_id": sub_id,
        "barcode": clean_code,
        "review_status": "user_submitted",
        "message": f"Thank you! '{payload.product_name}' has been saved locally for review."
    }

@app.get("/api/products/barcode/{barcode}")
def lookup_product_by_barcode(barcode: str, request: Request = None):
    """
    Layered barcode product discovery:
    1. Validates barcode format (EAN-13, EAN-8, UPC-A, UPC-E).
    2. Layer 1: Local EATGOOD Catalogue (852 authentic retail products).
    3. Layer 2: Local User Contributions & SQLite Cache.
    4. Layer 3: Open Food Facts API v3 (external community database).
    5. Returns 404 structured response with contribution options if not found anywhere.
    """
    if request:
        enforce_rate_limit(request, "off_barcode")

    val = validate_barcode(barcode, strict=False)
    if not val["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "invalid_barcode",
                "barcode": barcode,
                "message": val["error"] or "Invalid barcode format or length."
            }
        )

    clean_code = val["normalized"]
    profile = get_active_profile()

    # 1. First Source: Local EATGOOD Catalogue
    local_prod = data_loader.get_product_by_barcode(clean_code)
    if local_prod:
        assessment = run_full_product_assessment(local_prod, profile)
        assessment["is_saved"] = is_product_saved(local_prod["product_id"])
        alts = get_healthier_alternatives(local_prod, profile)
        alts_list = alts.get("alternatives", []) if isinstance(alts, dict) else alts

        uid = (request.headers.get("x-user-id") if request else None) or "USR_DEFAULT"
        record_analysis_history(
            product_id=local_prod["product_id"],
            product_name=local_prod["product_name"],
            brand=local_prod["brand"],
            category=local_prod["category"],
            score=assessment["layer2_personalized"]["personalized_score"],
            grade=assessment["layer1_general"].get("grade", "N/A"),
            source="Barcode Scan (Local Catalogue)",
            user_id=uid
        )

        return {
            "status": "found",
            "source": "local_database",
            "barcode": clean_code,
            "barcode_format": val["format"],
            "check_digit_valid": val["check_digit_valid"],
            "product": local_prod,
            "assessment": assessment,
            "alternatives": alts_list,
            "data_confidence_status": local_prod.get("data_confidence_status", "Verified"),
            "message": f"Found '{local_prod['product_name']}' in local EATGOOD catalogue."
        }

    # 2. Second Source: Local User Contributions
    user_contrib = get_user_contribution_by_barcode(clean_code)
    if user_contrib:
        nutr = user_contrib.get("nutrition_data", {}) or {}
        contrib_prod = {
            "product_id": f"CONTRIB_{clean_code}",
            "product_name": user_contrib["product_name"],
            "brand": user_contrib.get("brand") or "User Contributed",
            "category": user_contrib.get("category", "Snacks"),
            "sub_category": user_contrib.get("sub_category", "User Contributed"),
            "barcode": clean_code,
            "serving_size": user_contrib.get("serving_size", 100.0),
            "serving_size_unit": user_contrib.get("serving_size_unit", "g"),
            "measurement_basis": user_contrib.get("measurement_basis", "per 100g"),
            "energy_kcal": nutr.get("energy_kcal"),
            "carbohydrates_g": nutr.get("carbohydrates_g"),
            "sugars_g": nutr.get("sugars_g"),
            "added_sugars_g": nutr.get("added_sugars_g"),
            "protein_g": nutr.get("protein_g"),
            "total_fat_g": nutr.get("total_fat_g"),
            "saturated_fat_g": nutr.get("saturated_fat_g"),
            "trans_fat_g": nutr.get("trans_fat_g"),
            "sodium_mg": nutr.get("sodium_mg"),
            "dietary_fibre_g": nutr.get("dietary_fibre_g"),
            "ingredients": user_contrib.get("ingredients"),
            "allergens_declared": user_contrib.get("allergens_declared"),
            "data_source": "Local User Contribution (Pending Review)",
            "data_confidence_status": "User Submitted (Unverified)"
        }

        assessment = run_full_product_assessment(contrib_prod, profile)
        assessment["is_saved"] = is_product_saved(contrib_prod["product_id"])
        alts = get_healthier_alternatives(contrib_prod, profile)
        alts_list = alts.get("alternatives", []) if isinstance(alts, dict) else alts

        return {
            "status": "found",
            "source": "user_contributed",
            "barcode": clean_code,
            "barcode_format": val["format"],
            "check_digit_valid": val["check_digit_valid"],
            "product": contrib_prod,
            "assessment": assessment,
            "alternatives": alts_list,
            "data_confidence_status": "User Submitted (Unverified)",
            "message": f"Found '{contrib_prod['product_name']}' from local user contributions (Pending Review)."
        }

    # 3. Third Source: SQLite Cache (previously queried Open Food Facts records)
    cached_prod = get_cached_barcode_product(clean_code)
    if cached_prod:
        assessment = run_full_product_assessment(cached_prod, profile)
        assessment["is_saved"] = is_product_saved(cached_prod["product_id"])
        alts = get_healthier_alternatives(cached_prod, profile)
        alts_list = alts.get("alternatives", []) if isinstance(alts, dict) else alts

        return {
            "status": "found",
            "source": "openfoodfacts_cached",
            "barcode": clean_code,
            "barcode_format": val["format"],
            "check_digit_valid": val["check_digit_valid"],
            "product": cached_prod,
            "assessment": assessment,
            "alternatives": alts_list,
            "openfoodfacts_attribution": cached_prod.get("openfoodfacts_attribution"),
            "data_confidence_status": cached_prod.get("data_confidence_status", "Community Sourced (Open Food Facts)"),
            "message": f"Found '{cached_prod['product_name']}' on Open Food Facts (Cached)."
        }

    # 4. Fourth Source: Open Food Facts API v3 (Live Query)
    off_result = fetch_product_from_openfoodfacts(clean_code)
    if off_result["status"] == "success" and off_result.get("product"):
        off_prod = off_result["product"]
        # Save to SQLite cache for 7 days
        cache_barcode_product(clean_code, off_prod, source="openfoodfacts", status="success", ttl_hours=168)

        assessment = run_full_product_assessment(off_prod, profile)
        assessment["is_saved"] = is_product_saved(off_prod["product_id"])
        alts = get_healthier_alternatives(off_prod, profile)
        alts_list = alts.get("alternatives", []) if isinstance(alts, dict) else alts

        uid = (request.headers.get("x-user-id") if request else None) or "USR_DEFAULT"
        record_analysis_history(
            product_id=off_prod["product_id"],
            product_name=off_prod["product_name"],
            brand=off_prod["brand"],
            category=off_prod["category"],
            score=assessment["layer2_personalized"]["personalized_score"],
            grade=assessment["layer1_general"].get("grade", "N/A"),
            source="Barcode Scan (Open Food Facts)",
            user_id=uid
        )

        return {
            "status": "found",
            "source": "openfoodfacts",
            "barcode": clean_code,
            "barcode_format": val["format"],
            "check_digit_valid": val["check_digit_valid"],
            "product": off_prod,
            "assessment": assessment,
            "alternatives": alts_list,
            "openfoodfacts_attribution": off_prod.get("openfoodfacts_attribution"),
            "data_confidence_status": off_prod.get("data_confidence_status"),
            "message": f"Product retrieved from Open Food Facts."
        }

    elif off_result["status"] == "not_found":
        # Cache negative lookup briefly (2 hours) to avoid hammering external service
        cache_barcode_product(clean_code, None, source="openfoodfacts", status="not_found", ttl_hours=2)
        raise HTTPException(
            status_code=404,
            detail={
                "status": "not_found",
                "barcode": clean_code,
                "barcode_format": val["format"],
                "check_digit_valid": val["check_digit_valid"],
                "message": f"Barcode {clean_code} was not found in the local catalogue or Open Food Facts."
            }
        )

    else:
        # Network or timeout error
        raise HTTPException(
            status_code=502,
            detail={
                "status": "external_unavailable",
                "barcode": clean_code,
                "barcode_format": val["format"],
                "message": off_result.get("message") or "External Open Food Facts service currently unavailable."
            }
        )

@app.get("/api/products/{product_id}")
def get_product_assessment(product_id: str, request: Request = None, user_id: Optional[str] = None):
    """
    Returns full product details along with comprehensive Layer 1, Layer 2, Layer 3 assessment
    tailored to the active user profile.
    """
    product = data_loader.get_product_by_id(product_id)
    if not product:
        if product_id.startswith("OFF_"):
            code = product_id.replace("OFF_", "")
            cached = get_cached_barcode_product(code)
            if cached:
                product = cached
            else:
                off_res = fetch_product_from_openfoodfacts(code)
                if off_res.get("status") == "success" and off_res.get("product"):
                    product = off_res["product"]
                    cache_barcode_product(code, product, source="openfoodfacts", status="success", ttl_hours=168)
        elif product_id.startswith("USER_SUB_"):
            code = product_id.replace("USER_SUB_", "")
            contrib = get_user_contribution_by_barcode(code)
            if contrib:
                nutr = contrib.get("nutrition_data") or {}
                product = {
                    "product_id": f"USER_SUB_{clean_barcode(contrib.get('barcode', code))}",
                    "barcode": contrib.get("barcode", code),
                    "product_name": contrib.get("product_name"),
                    "brand": contrib.get("brand") or "User Contributed",
                    "category": contrib.get("category", "Snacks"),
                    "sub_category": contrib.get("sub_category", "User Contributed"),
                    "serving_size": contrib.get("serving_size", 100),
                    "serving_size_unit": contrib.get("serving_size_unit", "g"),
                    "measurement_basis": contrib.get("measurement_basis", "per 100g"),
                    "energy_kcal": nutr.get("energy_kcal"),
                    "carbohydrates_g": nutr.get("carbohydrates_g"),
                    "sugars_g": nutr.get("sugars_g"),
                    "added_sugars_g": nutr.get("added_sugars_g"),
                    "protein_g": nutr.get("protein_g"),
                    "total_fat_g": nutr.get("total_fat_g"),
                    "saturated_fat_g": nutr.get("saturated_fat_g"),
                    "trans_fat_g": nutr.get("trans_fat_g"),
                    "sodium_mg": nutr.get("sodium_mg"),
                    "dietary_fibre_g": nutr.get("dietary_fibre_g"),
                    "ingredients": contrib.get("ingredients"),
                    "allergens_declared": contrib.get("allergens_declared"),
                    "data_source": "Local User Contribution (Pending Review)",
                    "data_confidence_status": "User Submitted (Unverified)"
                }
        elif product_id.strip().isdigit():
            clean_code = product_id.strip()
            product = data_loader.get_product_by_barcode(clean_code)
            if not product:
                product = get_cached_barcode_product(clean_code)
            if not product:
                contrib = get_user_contribution_by_barcode(clean_code)
                if contrib:
                    nutr = contrib.get("nutrition_data") or {}
                    product = {
                        "product_id": f"USER_SUB_{clean_code}",
                        "barcode": clean_code,
                        "product_name": contrib.get("product_name"),
                        "brand": contrib.get("brand") or "User Contributed",
                        "category": contrib.get("category", "Snacks"),
                        "sub_category": contrib.get("sub_category", "User Contributed"),
                        "serving_size": contrib.get("serving_size", 100),
                        "serving_size_unit": contrib.get("serving_size_unit", "g"),
                        "measurement_basis": contrib.get("measurement_basis", "per 100g"),
                        "energy_kcal": nutr.get("energy_kcal"),
                        "carbohydrates_g": nutr.get("carbohydrates_g"),
                        "sugars_g": nutr.get("sugars_g"),
                        "added_sugars_g": nutr.get("added_sugars_g"),
                        "protein_g": nutr.get("protein_g"),
                        "total_fat_g": nutr.get("total_fat_g"),
                        "saturated_fat_g": nutr.get("saturated_fat_g"),
                        "trans_fat_g": nutr.get("trans_fat_g"),
                        "sodium_mg": nutr.get("sodium_mg"),
                        "dietary_fibre_g": nutr.get("dietary_fibre_g"),
                        "ingredients": contrib.get("ingredients"),
                        "allergens_declared": contrib.get("allergens_declared"),
                        "data_source": "Local User Contribution (Pending Review)",
                        "data_confidence_status": "User Submitted (Unverified)"
                    }
            if not product:
                off_res = fetch_product_from_openfoodfacts(clean_code)
                if off_res.get("status") == "success" and off_res.get("product"):
                    product = off_res["product"]
                    cache_barcode_product(clean_code, product, source="openfoodfacts", status="success", ttl_hours=168)
    if not product:
        saved_rec = get_saved_product(product_id)
        if saved_rec and saved_rec.get("product_data"):
            try:
                product = json.loads(saved_rec["product_data"])
            except Exception:
                pass
        if not product and saved_rec:
            product = {
                "product_id": product_id,
                "product_name": saved_rec.get("product_name") or "Scanned Product",
                "brand": saved_rec.get("brand") or "Custom",
                "category": saved_rec.get("category") or "Custom Scan",
                "sub_category": "User Scan",
                "measurement_basis": "per 100g",
                "serving_size": 100,
                "serving_size_unit": "g"
            }

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    profile = get_profile_for_request(request, user_id)
    assessment = run_full_product_assessment(product, profile)

    # Attach ML prediction as an experimental secondary perspective
    ml_eval = ml_service.predict_suitability(profile, product)
    assessment["ml_experimental_insight"] = ml_eval
    assessment["is_saved"] = is_product_saved(product_id)

    # Record analysis history
    uid = (request.headers.get("x-user-id") if request else None) or "USR_DEFAULT"
    record_analysis_history(
        product_id=product["product_id"],
        product_name=product["product_name"],
        brand=product["brand"],
        category=product["category"],
        score=assessment["layer2_personalized"]["personalized_score"],
        grade=assessment["layer1_general"].get("grade", "N/A"),
        source="Product Catalogue",
        user_id=uid
    )

    return assessment

@app.post("/api/products/assess")
def assess_custom_food(input_data: ManualNutritionInput, request: Request = None, user_id: Optional[str] = None):
    """
    Assesses manually entered nutrition facts or user-confirmed OCR values.
    """
    profile = get_profile_for_request(request, user_id)
    prod_dict = input_data.model_dump() if hasattr(input_data, "model_dump") else input_data.dict()
    prod_dict["product_id"] = "CUSTOM_SCAN"
    prod_dict["data_source"] = "User / OCR Input"
    prod_dict["data_confidence_status"] = "User-Verified Custom Data"

    assessment = run_full_product_assessment(prod_dict, profile)
    assessment["ml_experimental_insight"] = ml_service.predict_suitability(profile, prod_dict)
    assessment["is_custom"] = True
    assessment["raw_input"] = prod_dict

    uid = (request.headers.get("x-user-id") if request else None) or "USR_DEFAULT"
    record_analysis_history(
        product_id="CUSTOM_SCAN",
        product_name=input_data.product_name,
        brand=input_data.brand or "Custom",
        category=input_data.category,
        score=assessment["layer2_personalized"]["personalized_score"],
        grade=assessment["layer1_general"].get("grade", "N/A"),
        source="Label Scan / Manual Entry",
        user_id=uid
    )

    return assessment

@app.get("/api/alternatives/{product_id}")
def get_alternatives_endpoint(product_id: str):
    """Returns healthier same-category alternatives for a given product ID."""
    prod = data_loader.get_product_by_id(product_id)
    if not prod:
        if product_id.startswith("OFF_"):
            code = product_id.replace("OFF_", "")
            prod = get_cached_barcode_product(code)
        elif product_id.startswith("USER_SUB_"):
            code = product_id.replace("USER_SUB_", "")
            contrib = get_user_contribution_by_barcode(code)
            if contrib:
                nutr = contrib.get("nutrition_data") or {}
                prod = {
                    "product_id": product_id,
                    "category": contrib.get("category", "Snacks"),
                    "energy_kcal": nutr.get("energy_kcal"),
                    "sugars_g": nutr.get("sugars_g"),
                    "sodium_mg": nutr.get("sodium_mg"),
                    "saturated_fat_g": nutr.get("saturated_fat_g")
                }
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found.")

    profile = get_active_profile()
    alts = get_healthier_alternatives(prod, profile)
    alts_list = alts.get("alternatives", []) if isinstance(alts, dict) else alts
    return {
        "product_id": product_id,
        "category": prod.get("category"),
        "alternatives": alts_list
    }

@app.get("/api/ocr/status")
def get_ocr_status():
    """Returns local Tesseract OCR engine installation status and available features."""
    return get_ocr_engine_info()

@app.post("/api/analyze/ocr")
async def analyze_food_label_image(file: UploadFile = File(...), request: Request = None):
    """
    Receives an image of a food label or ingredient list,
    verifies magic bytes and size constraints (<= 10MB),
    extracts raw text via local Tesseract 5 OCR after OpenCV preprocessing,
    and parses structured nutrition fields with explicit status badges.
    Persists scan session locally in SQLite for full provenance.
    NEVER returns silent fallback mock data.
    """
    if request:
        enforce_rate_limit(request, "ocr")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image format. Please upload PNG, JPEG, or WebP.")

    # Read and validate image content size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds maximum limit of {MAX_UPLOAD_SIZE_MB}MB."
        )
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded image file is empty.")

    # Deep magic byte / header verification using Pillow
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
        fmt = (img.format or "").upper()
        if fmt not in ["PNG", "JPEG", "WEBP"]:
            raise HTTPException(status_code=400, detail=f"Image format '{fmt}' is not permitted. Please upload PNG, JPEG, or WebP.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Corrupt or invalid image file. Magic bytes could not be decoded.")

    # Unique scan session identifier
    scan_id = f"scn_{uuid.uuid4().hex[:10]}"
    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename or 'upload.jpg')
    temp_path = os.path.join(UPLOAD_DIR, f"{scan_id}_{safe_name}")

    try:
        with open(temp_path, "wb") as buffer:
            buffer.write(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store uploaded image: {str(e)}")

    try:
        # Execute OCR pipeline
        ocr_res = run_image_ocr(temp_path)
    finally:
        # Clean up temporary upload in serverless microVMs (Vercel / AWS Lambda) to prevent disk exhaustion
        if (os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")) and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
    
    # Structured extraction
    extraction = extract_nutrition_from_text(
        ocr_res.get("raw_text", ""),
        ocr_res.get("ocr_confidence", 0.85)
    )

    overall_status = ocr_res.get("status", "success")
    if overall_status == "success" and not extraction.get("extracted_values", {}).get("energy_kcal") and not extraction.get("extracted_values", {}).get("protein_g"):
        # Text was extracted, but no clear nutrient values matched
        overall_status = "partial"

    # Record scan session in SQLite
    try:
        record_scan_session(
            scan_id=scan_id,
            filename=file.filename or "unknown",
            image_path=temp_path,
            ocr_engine=ocr_res.get("engine", "Tesseract Local"),
            raw_text=ocr_res.get("raw_text", ""),
            status=overall_status,
            extracted_data=extraction["extracted_values"],
            confidence=ocr_res.get("ocr_confidence", 0.0)
        )
    except Exception as e:
        print(f"Notice: Failed to record scan session: {e}")

    return {
        "status": overall_status,
        "scan_id": scan_id,
        "ocr_engine": ocr_res.get("engine", "Local OCR Engine"),
        "ocr_confidence": ocr_res.get("ocr_confidence", 0.0),
        "raw_text": ocr_res.get("raw_text", ""),
        "lines": ocr_res.get("lines", []),
        "extracted_values": extraction["extracted_values"],
        "field_statuses": extraction["field_statuses"],
        "confidence_scores": extraction["confidence_scores"],
        "field_notes": extraction["field_notes"],
        "missing_fields": extraction["missing_fields"],
        "suspicious_flags": extraction["suspicious_flags"],
        "requires_user_confirmation": True,
        "message": ocr_res.get("message") or "Text extracted. Please verify and confirm all fields before generating the food assessment.",
        "instruction": "Please confirm or correct the extracted values before generating the final assessment."
    }

@app.get("/api/scans/recent")
def list_recent_scans(limit: int = 10):
    """Returns recently recorded local OCR scan sessions from SQLite."""
    return get_recent_scan_sessions(limit=limit)

@app.get("/api/compare")
def compare_products(
    ids: str = Query(..., description="Comma-separated product IDs to compare"),
    request: Request = None,
    user_id: Optional[str] = None
):
    """
    Compares 2 to 4 products side-by-side.
    Normalizes measurement basis to per-100g or per-100ml.
    Highlights key deltas relative to user goals.
    """
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 product IDs for comparison.")

    profile = get_profile_for_request(request, user_id)
    compared_items = []

    for pid in id_list[:4]:
        prod = data_loader.get_product_by_id(pid)
        if prod:
            assessment = run_full_product_assessment(prod, profile)
            compared_items.append({
                "product_id": prod["product_id"],
                "product_name": prod["product_name"],
                "brand": prod["brand"],
                "category": prod["category"],
                "image_url": prod.get("image_url"),
                "image_small_url": prod.get("image_small_url"),
                "measurement_basis": prod.get("measurement_basis", "per 100g"),
                "data_confidence_status": prod.get("data_confidence_status", "Verified"),
                "energy_kcal": prod.get("energy_kcal"),
                "carbohydrates_g": prod.get("carbohydrates_g"),
                "sugars_g": prod.get("sugars_g"),
                "added_sugars_g": prod.get("added_sugars_g"),
                "protein_g": prod.get("protein_g"),
                "total_fat_g": prod.get("total_fat_g"),
                "saturated_fat_g": prod.get("saturated_fat_g"),
                "sodium_mg": prod.get("sodium_mg"),
                "dietary_fibre_g": prod.get("dietary_fibre_g"),
                "general_grade": assessment["layer1_general"].get("grade", "N/A"),
                "personalized_score": assessment["layer2_personalized"]["personalized_score"],
                "allergen_conflicts": assessment["layer2_personalized"]["allergen_conflicts"],
                "has_allergen_conflict": assessment["layer2_personalized"]["has_critical_allergen_conflict"],
                "ingredients": prod.get("ingredients")
            })

    return {
        "user_goal": profile.get("goal"),
        "products_compared": compared_items
    }

@app.get("/api/alternatives/{product_id}")
def get_alternatives(product_id: str, limit: int = 4, request: Request = None, user_id: Optional[str] = None):
    """Returns healthier alternatives for a given product."""
    profile = get_profile_for_request(request, user_id)
    return get_healthier_alternatives(product_id, profile, limit=limit)

@app.get("/api/profile")
def get_profile(request: Request = None, user_id: Optional[str] = None):
    return get_profile_for_request(request, user_id)

@app.post("/api/profile")
def update_profile(profile: UserProfileModel, request: Request = None):
    data = profile.model_dump() if hasattr(profile, "model_dump") else profile.dict()
    if request:
        header_uid = request.headers.get("x-user-id")
        if header_uid and (not data.get("user_id") or data.get("user_id") == "USR_DEFAULT"):
            data["user_id"] = header_uid
    return save_active_profile(data)

@app.get("/api/standards")
def get_standards():
    return {
        "standards_version": STANDARDS_REGISTRY_VERSION,
        "calibrated_categories": CALIBRATED_CATEGORIES,
        "category_specs": CATEGORY_CALIBRATION_SPECS,
        "total_standards": len(STANDARDS_REGISTRY),
        "standards": STANDARDS_REGISTRY
    }

@app.get("/api/audit")
def get_data_audit():
    """Returns statistical data quality report, 78 calorie anomalies, and 13 macro-serving flags."""
    return data_loader.get_audit_metrics()

@app.get("/api/history")
def get_history(request: Request, limit: int = 20, user_id: Optional[str] = None):
    uid = user_id or request.headers.get("x-user-id")
    return get_recent_history(limit=limit, user_id=uid)

@app.delete("/api/history")
@app.post("/api/history/clear")
def clear_history_endpoint(request: Request, user_id: Optional[str] = None):
    uid = user_id or request.headers.get("x-user-id")
    return clear_analysis_history(user_id=uid)

@app.post("/api/saved/{product_id}")
def save_product(product_id: str, payload: dict = Body(default=None)):
    if payload is None:
        p = data_loader.get_product_by_id(product_id)
        if p:
            payload = p
    is_saved = toggle_save_product(product_id, payload)
    return {"product_id": product_id, "is_saved": is_saved}

@app.get("/api/saved/check/{product_id}")
def check_saved(product_id: str):
    return {"product_id": product_id, "is_saved": is_product_saved(product_id)}

@app.get("/api/saved")
def get_saved():
    saved_records = get_saved_products_records()
    products = []
    for rec in saved_records:
        pid = rec["product_id"]
        prod = data_loader.get_product_by_id(pid)
        if prod:
            products.append(prod)
        else:
            prod_dict = {}
            if rec.get("product_data"):
                try:
                    prod_dict = json.loads(rec["product_data"])
                except Exception:
                    pass
            prod_dict.setdefault("product_id", pid)
            prod_dict.setdefault("product_name", rec.get("product_name") or "Saved Scanned Product")
            prod_dict.setdefault("brand", rec.get("brand") or "Custom")
            prod_dict.setdefault("category", rec.get("category") or "Custom Scan")
            prod_dict.setdefault("sub_category", "User Scan")
            products.append(prod_dict)
    return {"total": len(products), "saved_products": products}

FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.api_route("/favicon.svg", methods=["GET", "HEAD"], include_in_schema=False)
    async def favicon_svg():
        fav_svg_path = os.path.join(FRONTEND_DIST, "favicon.svg")
        if os.path.exists(fav_svg_path):
            return FileResponse(fav_svg_path, media_type="image/svg+xml")
        return FileResponse(os.path.join(FRONTEND_DIST, "logo.png"), media_type="image/png")

    @app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
    async def favicon():
        fav_path = os.path.join(FRONTEND_DIST, "favicon.ico")
        if os.path.exists(fav_path):
            return FileResponse(fav_path, media_type="image/x-icon")
        return FileResponse(os.path.join(FRONTEND_DIST, "logo.png"), media_type="image/png")

    @app.api_route("/apple-touch-icon.png", methods=["GET", "HEAD"], include_in_schema=False)
    @app.api_route("/apple-touch-icon-precomposed.png", methods=["GET", "HEAD"], include_in_schema=False)
    async def apple_touch_icon():
        icon_path = os.path.join(FRONTEND_DIST, "apple-touch-icon.png")
        if os.path.exists(icon_path):
            return FileResponse(icon_path, media_type="image/png")
        return FileResponse(os.path.join(FRONTEND_DIST, "logo.png"), media_type="image/png")

    @app.api_route("/favicon.png", methods=["GET", "HEAD"], include_in_schema=False)
    @app.api_route("/favicon-32x32.png", methods=["GET", "HEAD"], include_in_schema=False)
    @app.api_route("/favicon-16x16.png", methods=["GET", "HEAD"], include_in_schema=False)
    async def favicon_png():
        fav_png_path = os.path.join(FRONTEND_DIST, "favicon-32x32.png")
        if os.path.exists(fav_png_path):
            return FileResponse(fav_png_path, media_type="image/png")
        return FileResponse(os.path.join(FRONTEND_DIST, "logo.png"), media_type="image/png")

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def serve_frontend(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
