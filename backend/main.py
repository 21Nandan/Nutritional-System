"""
EATGOOD — FastAPI Backend Application
Main entry point serving REST APIs for food analysis, personalized nutrition grading,
product comparison, healthier recommendations, OCR label extraction, and data audits.
"""

import os
import shutil
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.core.data_loader import data_loader
from backend.core.nutrition_scoring import run_full_product_assessment, assess_general_nutrition, assess_personalized_suitability
from backend.core.standards_registry import STANDARDS_REGISTRY, CALIBRATED_CATEGORIES
from backend.core.recommender import get_healthier_alternatives
from backend.core.ml_model import ml_service
from backend.core.ocr_service import run_image_ocr, extract_nutrition_from_text
from backend.database import (
    get_active_profile, save_active_profile,
    record_analysis_history, get_recent_history,
    toggle_save_product, get_saved_product_ids
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

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    limit: int = 50,
    offset: int = 0
):
    """Retrieves paginated products with search query and category/brand filters."""
    return data_loader.search_products(query=query, category=category, brand=brand, limit=limit, offset=offset)

@app.get("/api/products/categories")
def get_categories():
    if data_loader.products_df is None or data_loader.products_df.empty:
        return {"categories": []}
    cats = sorted(data_loader.products_df["category"].dropna().unique().tolist())
    return {
        "categories": ["All"] + cats,
        "calibrated_categories": CALIBRATED_CATEGORIES
    }

@app.get("/api/products/{product_id}")
def get_product_assessment(product_id: str):
    """
    Returns full product details along with comprehensive Layer 1, Layer 2, Layer 3 assessment
    tailored to the active user profile.
    """
    product = data_loader.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    profile = get_active_profile()
    assessment = run_full_product_assessment(product, profile)

    # Attach ML prediction as an experimental secondary perspective
    ml_eval = ml_service.predict_suitability(profile, product)
    assessment["ml_experimental_insight"] = ml_eval

    # Record analysis history
    record_analysis_history(
        product_id=product["product_id"],
        product_name=product["product_name"],
        brand=product["brand"],
        category=product["category"],
        score=assessment["layer2_personalized"]["personalized_score"],
        grade=assessment["layer1_general"].get("grade", "N/A"),
        source="Product Catalogue"
    )

    return assessment

@app.post("/api/products/assess")
def assess_custom_food(input_data: ManualNutritionInput):
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

    record_analysis_history(
        product_id="CUSTOM_SCAN",
        product_name=input_data.product_name,
        brand=input_data.brand or "Custom",
        category=input_data.category,
        score=assessment["layer2_personalized"]["personalized_score"],
        grade=assessment["layer1_general"].get("grade", "N/A"),
        source="Label Scan / Manual Entry"
    )

    return assessment

@app.post("/api/analyze/ocr")
async def analyze_food_label_image(file: UploadFile = File(...)):
    """
    Receives an image of a food label or ingredient list,
    extracts raw text via OCR, and parses structured fields.
    Returns editable fields with confidence flags for user confirmation.
    """
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise HTTPException(status_code=400, detail="Unsupported image format. Please upload PNG or JPEG.")

    temp_path = os.path.join(UPLOAD_DIR, f"scan_{file.filename}")
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ocr_res = run_image_ocr(temp_path)
    extraction = extract_nutrition_from_text(ocr_res["raw_text"])

    return {
        "status": "success",
        "ocr_engine": ocr_res.get("engine", "Local OCR Engine"),
        "raw_text": ocr_res["raw_text"],
        "lines": ocr_res.get("lines", []),
        "extracted_values": extraction["extracted_values"],
        "confidence_scores": extraction["confidence_scores"],
        "missing_fields": extraction["missing_fields"],
        "suspicious_flags": extraction["suspicious_flags"],
        "instruction": "Please confirm or correct the extracted values before generating the final assessment."
    }

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
def get_history(limit: int = 10):
    return get_recent_history(limit=limit)

@app.post("/api/saved/{product_id}")
def save_product(product_id: str):
    is_saved = toggle_save_product(product_id)
    return {"product_id": product_id, "is_saved": is_saved}

@app.get("/api/saved")
def get_saved():
    saved_ids = get_saved_product_ids()
    products = [data_loader.get_product_by_id(pid) for pid in saved_ids if data_loader.get_product_by_id(pid)]
    return {"total": len(products), "saved_products": products}

FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
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
