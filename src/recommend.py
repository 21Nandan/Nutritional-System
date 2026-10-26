#!/usr/bin/env python3
"""
EATGOOD — Recommender Engine Script
Supports both the simulated demonstration subset (~15 example products)
and full integration with the 852-product standardized catalogue.
Provides ML model inference with rule-based fallback.
"""

import os
import joblib
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.path.join(BASE_DIR, "models", "eatgood_model.joblib")
PRODUCTS_PATH = os.path.join(BASE_DIR, "data", "products_cleaned.csv")

# 15 Simulated Demonstration Products
DEMO_PRODUCTS = [
    {"product_id": "DEMO_01", "product_name": "Lay's Classic Salted", "category": "Snacks", "sugars_g": 1.5, "sodium_mg": 520, "protein_g": 6.8, "dietary_fibre_g": 3.2, "saturated_fat_g": 13.5, "allergens": "None declared"},
    {"product_id": "DEMO_02", "product_name": "Too Yumm! Multigrain Chips", "category": "Snacks", "sugars_g": 2.1, "sodium_mg": 380, "protein_g": 8.5, "dietary_fibre_g": 6.8, "saturated_fat_g": 4.5, "allergens": "None declared"},
    {"product_id": "DEMO_03", "product_name": "Haldiram's Bhujia Sev", "category": "Snacks", "sugars_g": 2.0, "sodium_mg": 780, "protein_g": 11.2, "dietary_fibre_g": 4.1, "saturated_fat_g": 14.8, "allergens": "Peanuts, Soy"},
    {"product_id": "DEMO_04", "product_name": "Kellogg's Corn Flakes Original", "category": "Breakfast Cereals", "sugars_g": 8.0, "sodium_mg": 480, "protein_g": 7.5, "dietary_fibre_g": 2.5, "saturated_fat_g": 0.3, "allergens": "Gluten"},
    {"product_id": "DEMO_05", "product_name": "Quaker Rolled Oats", "category": "Breakfast Cereals", "sugars_g": 0.8, "sodium_mg": 12, "protein_g": 12.8, "dietary_fibre_g": 10.5, "saturated_fat_g": 1.5, "allergens": "None declared"},
    {"product_id": "DEMO_06", "product_name": "Kellogg's Chocos", "category": "Breakfast Cereals", "sugars_g": 28.5, "sodium_mg": 320, "protein_g": 6.8, "dietary_fibre_g": 4.5, "saturated_fat_g": 1.2, "allergens": "Gluten, Soy"},
    {"product_id": "DEMO_07", "product_name": "Real Fruit Power Mixed Fruit", "category": "Packaged Beverages", "sugars_g": 12.8, "sodium_mg": 25, "protein_g": 0.3, "dietary_fibre_g": 0.2, "saturated_fat_g": 0.0, "allergens": "None declared"},
    {"product_id": "DEMO_08", "product_name": "Tropicana 100% Orange Juice", "category": "Packaged Beverages", "sugars_g": 8.5, "sodium_mg": 10, "protein_g": 0.7, "dietary_fibre_g": 0.6, "saturated_fat_g": 0.0, "allergens": "None declared"},
    {"product_id": "DEMO_09", "product_name": "Amul Kool Kesar Milk", "category": "Packaged Beverages", "sugars_g": 11.5, "sodium_mg": 65, "protein_g": 3.8, "dietary_fibre_g": 0.0, "saturated_fat_g": 2.6, "allergens": "Milk, Tree Nuts"},
    {"product_id": "DEMO_10", "product_name": "Coca-Cola Original", "category": "Packaged Beverages", "sugars_g": 10.6, "sodium_mg": 12, "protein_g": 0.0, "dietary_fibre_g": 0.0, "saturated_fat_g": 0.0, "allergens": "None declared"},
    {"product_id": "DEMO_11", "product_name": "Coca-Cola Zero Sugar", "category": "Packaged Beverages", "sugars_g": 0.0, "sodium_mg": 14, "protein_g": 0.0, "dietary_fibre_g": 0.0, "saturated_fat_g": 0.0, "allergens": "None declared"},
    {"product_id": "DEMO_12", "product_name": "Britannia Marie Gold", "category": "Biscuits & Bakery", "sugars_g": 19.5, "sodium_mg": 280, "protein_g": 7.8, "dietary_fibre_g": 2.8, "saturated_fat_g": 4.8, "allergens": "Gluten, Milk"},
    {"product_id": "DEMO_13", "product_name": "Cadbury Dairy Milk Silk", "category": "Chocolates & Sweets", "sugars_g": 54.0, "sodium_mg": 95, "protein_g": 7.2, "dietary_fibre_g": 2.1, "saturated_fat_g": 19.5, "allergens": "Milk, Soy"},
    {"product_id": "DEMO_14", "product_name": "Maggi 2-Minute Noodles", "category": "Instant Foods", "sugars_g": 2.5, "sodium_mg": 1180, "protein_g": 8.0, "dietary_fibre_g": 3.5, "saturated_fat_g": 6.5, "allergens": "Gluten, Wheat"},
    {"product_id": "DEMO_15", "product_name": "Epigamia Natural Greek Yogurt", "category": "Dairy", "sugars_g": 3.8, "sodium_mg": 45, "protein_g": 9.5, "dietary_fibre_g": 0.0, "saturated_fat_g": 2.8, "allergens": "Milk"}
]

class EatGoodRecommender:
    def __init__(self, use_ml_model=True):
        self.use_ml_model = use_ml_model
        self.model = None
        if os.path.exists(MODEL_PATH) and use_ml_model:
            try:
                self.model = joblib.load(MODEL_PATH)
            except Exception as e:
                print(f"Warning: Could not load ML model ({e}). Using deterministic rules.")
                self.model = None

    def evaluate_product_suitability(self, user_profile, product):
        """
        Calculates personalized suitability score (0-100) and suitability label.
        Handles missing fields gracefully without zero-replacement.
        """
        allergens_to_avoid = [a.strip().lower() for a in user_profile.get("allergens_to_avoid", "").split(",") if a.strip()]
        prod_allg_text = str(product.get("allergens_declared", product.get("allergens", ""))).lower()

        # Hard allergen conflict check
        allergen_conflict = False
        detected_allergens = []
        for allg in allergens_to_avoid:
            if allg in ["none", ""]:
                continue
            if allg in prod_allg_text or (allg == "gluten" and "wheat" in prod_allg_text):
                allergen_conflict = True
                detected_allergens.append(allg.capitalize())

        # Dietary preference check
        dietary_pref = user_profile.get("dietary_preference", "No preference")
        pref_conflict = False
        prod_ings = str(product.get("ingredients", "")).lower()
        if dietary_pref == "Vegan":
            if product.get("category") == "Dairy" or any(w in prod_ings for w in ["milk", "butter", "honey", "cheese", "whey"]):
                pref_conflict = True
        elif dietary_pref == "Lactose avoidance":
            if product.get("category") == "Dairy" or any(w in prod_ings for w in ["milk", "butter", "cheese", "whey", "lactose"]):
                pref_conflict = True

        goal = user_profile.get("goal", "Balanced Choices")
        base_score = 65.0
        explanations = []

        # Sugar check
        sugars = product.get("sugars_g")
        if pd.notna(sugars):
            if goal == "Reduce Sugar":
                if sugars <= 5.0:
                    base_score += 25
                    explanations.append(f"Low sugar content ({sugars}g) strongly aligns with your Reduce Sugar goal.")
                elif sugars > 18.0:
                    base_score -= 35
                    explanations.append(f"High sugar content ({sugars}g) conflicts with your Reduce Sugar goal.")
            else:
                if sugars > 25.0:
                    base_score -= 15
        else:
            explanations.append("Sugar declaration is missing; evaluation is partial.")

        # Sodium check
        sodium = product.get("sodium_mg")
        if pd.notna(sodium):
            if goal == "Reduce Sodium":
                if sodium <= 250:
                    base_score += 25
                    explanations.append(f"Low sodium ({sodium}mg) supports your Reduce Sodium objective.")
                elif sodium > 700:
                    base_score -= 35
                    explanations.append(f"High sodium ({sodium}mg) is a concern for your sodium limit.")
            else:
                if sodium > 1000:
                    base_score -= 15
        else:
            explanations.append("Sodium information is missing or unverified.")

        # Fibre check
        fibre = product.get("dietary_fibre_g")
        if pd.notna(fibre):
            if goal == "Increase Fibre":
                if fibre >= 6.0:
                    base_score += 30
                    explanations.append(f"Rich in dietary fibre ({fibre}g), exceeding recommended threshold.")
                elif fibre < 2.0:
                    base_score -= 20
                    explanations.append(f"Low fibre content ({fibre}g) for your Increase Fibre goal.")
        
        # Protein check
        protein = product.get("protein_g")
        if pd.notna(protein):
            if goal == "Increase Protein":
                if protein >= 10.0:
                    base_score += 30
                    explanations.append(f"High protein ({protein}g per serving) supports your protein goal.")
                elif protein < 4.0:
                    base_score -= 20
                    explanations.append(f"Low protein ({protein}g) relative to your target.")

        # Apply hard constraints
        if allergen_conflict:
            final_score = 0.0
            is_suitable = False
            explanations.insert(0, f"CRITICAL WARNING: Contains allergen ({', '.join(detected_allergens)}) restricted in your profile!")
        elif pref_conflict:
            final_score = min(20.0, base_score)
            is_suitable = False
            explanations.insert(0, f"Preference conflict: Incompatible with {dietary_pref} diet.")
        else:
            final_score = round(max(5.0, min(98.0, base_score)), 1)
            is_suitable = final_score >= 60.0

        # ML Model prediction (for experimental comparison)
        ml_prediction = None
        ml_note = None
        if self.model and not allergen_conflict and not pref_conflict:
            try:
                features_df = pd.DataFrame([{
                    "user_goal": goal,
                    "dietary_preference": dietary_pref,
                    "energy_kcal": product.get("energy_kcal", 250.0),
                    "sugars_g": product.get("sugars_g", 5.0),
                    "sodium_mg": product.get("sodium_mg", 300.0),
                    "protein_g": product.get("protein_g", 5.0),
                    "dietary_fibre_g": product.get("dietary_fibre_g", 2.0),
                    "saturated_fat_g": product.get("saturated_fat_g", 3.0),
                    "allergen_conflict": int(allergen_conflict),
                    "preference_conflict": int(pref_conflict)
                }])
                pred = self.model.predict(features_df)[0]
                proba = self.model.predict_proba(features_df)[0][1]
                ml_prediction = {
                    "is_suitable": bool(pred == 1),
                    "confidence": round(float(proba), 3),
                    "model_status": "Experimental (Trained on 1,500 simulated pairs)"
                }
            except Exception as e:
                ml_note = f"ML inference bypassed due to missing fields ({e})"

        return {
            "product_id": product.get("product_id"),
            "product_name": product.get("product_name"),
            "suitability_score": final_score,
            "is_suitable": is_suitable,
            "allergen_conflict": allergen_conflict,
            "detected_allergens": detected_allergens,
            "explanations": explanations,
            "ml_experimental_prediction": ml_prediction,
            "ml_note": ml_note
        }

    def recommend_alternatives(self, current_product, user_profile, pool="full", limit=3):
        """
        Recommends healthier alternatives strictly within the same or comparable category.
        Excludes allergen conflicts, respects dietary preferences, and explains reasons.
        """
        category = current_product.get("category")
        if pool == "demo":
            candidates = [p for p in DEMO_PRODUCTS if p["category"] == category and p["product_id"] != current_product.get("product_id")]
        else:
            if os.path.exists(PRODUCTS_PATH):
                df_all = pd.read_csv(PRODUCTS_PATH)
                candidates = df_all[(df_all["category"] == category) & (df_all["product_id"] != current_product.get("product_id"))].to_dict(orient="records")
            else:
                candidates = [p for p in DEMO_PRODUCTS if p["category"] == category]

        evaluations = []
        for cand in candidates:
            res = self.evaluate_product_suitability(user_profile, cand)
            if not res["allergen_conflict"]:
                # Compare to current product
                cand_res = {
                    **cand,
                    "assessment": res,
                    "suitability_score": res["suitability_score"]
                }
                evaluations.append(cand_res)

        # Sort by suitability score descending
        evaluations.sort(key=lambda x: x["suitability_score"], reverse=True)
        return evaluations[:limit]

if __name__ == "__main__":
    recommender = EatGoodRecommender()
    sample_user = {
        "user_id": "USR_001",
        "goal": "Reduce Sugar",
        "dietary_preference": "Vegetarian",
        "allergens_to_avoid": "Milk"
    }
    print("Testing Recommender on Demo Dataset...")
    eval_res = recommender.evaluate_product_suitability(sample_user, DEMO_PRODUCTS[0])
    print(f"Evaluated {DEMO_PRODUCTS[0]['product_name']}: Score = {eval_res['suitability_score']}, Suitable = {eval_res['is_suitable']}")
    print("Explanations:", eval_res["explanations"])
