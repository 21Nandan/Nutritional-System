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
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.core.data_loader import data_loader
from backend.core.nutrition_scoring import run_full_product_assessment, assess_general_nutrition, assess_personalized_suitability
from backend.core.standards_registry import STANDARDS_REGISTRY, CALIBRATED_CATEGORIES
from backend.core.recommender import get_healthier_alternatives
from backend.core.ml_model import ml_service
from backend.core.ocr_service import run_image_ocr, extract_nutrition_from_text, get_ocr_engine_info
from backend.core.barcode_utils import validate_barcode
from backend.core.openfoodfacts import fetch_product_from_openfoodfacts
from backend.database import (
    get_active_profile, save_active_profile,
    record_analysis_history, get_recent_history, clear_analysis_history,
    toggle_save_product, get_saved_product_ids,
    is_product_saved, get_saved_products_records, get_saved_product,
    record_scan_session, get_recent_scan_sessions,
    get_cached_barcode_product, cache_barcode_product,
    record_user_contribution, get_user_contributions, get_user_contribution_by_barcode
)

app = FastAPI(
    title="EATGOOD API",
    description="AI-Powered Personalized Food Safety and Nutrition Assessment Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def ensure_api_prefix(request: Request, call_next):
    # If incoming path does not start with /api and is not docs/openapi/health/root,
    # normalize path to start with /api so all routes match reliably across serverless environments
    path = request.scope.get("path", "")
    if path and not path.startswith("/api") and not path.startswith("/docs") and not path.startswith("/openapi.json") and path != "/health" and path != "/":
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

# ----------------- Models -----------------
class UserProfileModel(BaseModel):
    user_id: Optional[str] = "USR_DEFAULT"
    name: Optional[str] = "User"
    goal: str = "Balanced Choices"
    dietary_preference: str = "No preference"
    allergens_to_avoid: Optional[str] = ""
    age_group: Optional[str] = "18-24"
    activity_level: Optional[str] = "Moderately active"

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
    limit: int = 50,
    offset: int = 0,
    deduplicate_variants: Optional[bool] = None
):
    """Retrieves paginated products with search query, category, and nutritional filters."""
    # When query is provided (e.g. searching 'cok' in compare modal or catalogue search),
    # deduplicate synthetic (Variant X) products so users see distinct products.
    # When browsing catalogue with no search query, preserve all 852 products.
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
        limit=limit,
        offset=offset,
        deduplicate_variants=dedup
    )

@app.get("/api/products/categories")
def get_categories():
    if data_loader.products_df is None or data_loader.products_df.empty:
        return {"categories": []}
    cats = sorted(data_loader.products_df["category"].dropna().unique().tolist())
    return {
        "categories": ["All"] + cats,
        "calibrated_categories": CALIBRATED_CATEGORIES
    }

# ----------------- Barcode Discovery & Contributions (Preceding {product_id}) -----------------

@app.get("/api/products/contributions")
def list_user_contributions(limit: int = 50):
    """Returns recently submitted user contributions from SQLite."""
    return {"contributions": get_user_contributions(limit=limit)}

@app.post("/api/products/contribute")
def contribute_new_product(payload: ProductContributionRequest):
    """
    Allows user to submit an unlisted product with packaging nutrition details.
    Saves record locally in SQLite under 'user_submitted' status (never falsely verified).
    """
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
def get_product_assessment(product_id: str, request: Request = None):
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

    profile = get_active_profile()
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
def assess_custom_food(input_data: ManualNutritionInput, request: Request = None):
    """
    Assesses manually entered nutrition facts or user-confirmed OCR values.
    """
    profile = get_active_profile()
    prod_dict = input_data.dict()
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
async def analyze_food_label_image(file: UploadFile = File(...)):
    """
    Receives an image of a food label or ingredient list,
    extracts raw text via local Tesseract 5 OCR after OpenCV preprocessing,
    and parses structured nutrition fields with explicit status badges.
    Persists scan session locally in SQLite for full provenance.
    NEVER returns silent fallback mock data.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.webp']:
        raise HTTPException(status_code=400, detail="Unsupported image format. Please upload PNG, JPEG, or WebP.")

    # Unique scan session identifier
    scan_id = f"scn_{uuid.uuid4().hex[:10]}"
    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename or 'upload.jpg')
    temp_path = os.path.join(UPLOAD_DIR, f"{scan_id}_{safe_name}")

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store uploaded image: {str(e)}")

    # Execute OCR pipeline
    ocr_res = run_image_ocr(temp_path)
    
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
def compare_products(ids: str = Query(..., description="Comma-separated product IDs to compare")):
    """
    Compares 2 to 4 products side-by-side.
    Normalizes measurement basis to per-100g or per-100ml.
    Highlights key deltas relative to user goals.
    """
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 product IDs for comparison.")

    profile = get_active_profile()
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
def get_alternatives(product_id: str, limit: int = 4):
    """Returns healthier alternatives for a given product."""
    profile = get_active_profile()
    return get_healthier_alternatives(product_id, profile, limit=limit)

@app.get("/api/profile")
def get_profile():
    return get_active_profile()

@app.post("/api/profile")
def update_profile(profile: UserProfileModel):
    return save_active_profile(profile.dict())

@app.get("/api/standards")
def get_standards():
    return {
        "calibrated_categories": CALIBRATED_CATEGORIES,
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
