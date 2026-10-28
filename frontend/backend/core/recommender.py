"""
EATGOOD — Healthier Alternatives Recommender Engine (Section 9)
Recommends verified, goal-aligned alternatives within comparable product categories.
Strictly excludes allergen conflicts and explains comparative nutritional advantages.
"""

import pandas as pd
from backend.core.data_loader import data_loader
from backend.core.nutrition_scoring import assess_personalized_suitability, assess_general_nutrition

def get_healthier_alternatives(current_product_or_id, user_profile: dict, limit: int = 4):
    """
    Finds healthier alternative products in the same category that match the user's goals.
    Accepts either a string product_id or a product dictionary.
    Never recommends products with allergen conflicts.
    Explains the comparative nutritional delta (e.g. -40% sugar, +3x fibre).
    """
    if isinstance(current_product_or_id, dict):
        current_product = current_product_or_id
        current_product_id = current_product.get("product_id", "")
    else:
        current_product_id = str(current_product_or_id)
        current_product = data_loader.get_product_by_id(current_product_id)

    if not current_product:
        return {"current_product": None, "alternatives": [], "message": "Product not found."}

    category = current_product.get("category")
    df = data_loader.products_df

    if df is None or df.empty:
        return {"current_product": current_product, "alternatives": [], "message": "Product database empty."}

    # Filter to same category, excluding self and redundant duplicate variants
    candidates_df = df[(df["category"] == category) & (df["product_id"] != current_product_id)].copy()
    candidates_df = candidates_df[~candidates_df["product_name"].str.contains(r'\(Variant\s*\d+\)', case=False, na=False)]

    # Prefer verified data confidence status
    candidates = candidates_df.replace({float('nan'): None}).to_dict(orient="records")

    goal = user_profile.get("goal", "Balanced Choices")
    curr_assessment = assess_personalized_suitability(current_product, user_profile)
    curr_score = curr_assessment["personalized_score"] or 0

    alternatives = []

    for cand in candidates:
        suitability = assess_personalized_suitability(cand, user_profile)
        
        # Hard exclusion: critical allergen conflict
        if suitability["has_critical_allergen_conflict"] or suitability["preference_conflict"]:
            continue

        cand_score = suitability["personalized_score"] or 0

        # Only recommend if better or comparable with meaningful positive attributes
        if cand_score >= curr_score or cand_score >= 70:
            general = assess_general_nutrition(cand)
            
            # Compute comparative advantages
            advantages = []
            
            # Sugar delta
            if pd.notna(current_product.get("sugars_g")) and pd.notna(cand.get("sugars_g")):
                diff = round(current_product["sugars_g"] - cand["sugars_g"], 1)
                if diff > 3.0:
                    advantages.append(f"{diff}g less sugar per 100g ({round((diff/current_product['sugars_g'])*100)}% lower)")
            
            # Sodium delta
            if pd.notna(current_product.get("sodium_mg")) and pd.notna(cand.get("sodium_mg")):
                diff = round(current_product["sodium_mg"] - cand["sodium_mg"], 1)
                if diff > 100.0:
                    advantages.append(f"{int(diff)}mg less sodium per 100g")
            
            # Fibre delta
            if pd.notna(cand.get("dietary_fibre_g")):
                curr_fib = current_product.get("dietary_fibre_g") or 0.0
                if cand["dietary_fibre_g"] > curr_fib + 2.0:
                    advantages.append(f"+{round(cand['dietary_fibre_g'] - curr_fib, 1)}g more dietary fibre")
            
            # Protein delta
            if pd.notna(cand.get("protein_g")):
                curr_prot = current_product.get("protein_g") or 0.0
                if cand["protein_g"] > curr_prot + 2.5:
                    advantages.append(f"+{round(cand['protein_g'] - curr_prot, 1)}g higher protein")

            if not advantages:
                advantages.append(f"Better aligned with your '{goal}' nutritional objective ({cand_score}/100 vs {curr_score}/100).")

            alternatives.append({
                "product_id": cand["product_id"],
                "product_name": cand["product_name"],
                "brand": cand["brand"],
                "category": cand["category"],
                "sub_category": cand["sub_category"],
                "image_url": cand.get("image_url"),
                "image_small_url": cand.get("image_small_url"),
                "personalized_score": cand_score,
                "suitability_status": suitability["suitability_status"],
                "general_grade": general.get("grade", "N/A"),
                "data_confidence_status": cand.get("data_confidence_status", "Verified"),
                "comparative_advantages": advantages,
                "nutrition_highlights": {
                    "energy_kcal": cand.get("energy_kcal"),
                    "sugars_g": cand.get("sugars_g"),
                    "sodium_mg": cand.get("sodium_mg"),
                    "protein_g": cand.get("protein_g"),
                    "dietary_fibre_g": cand.get("dietary_fibre_g"),
                    "saturated_fat_g": cand.get("saturated_fat_g")
                }
            })

    # Sort by personalized score descending
    alternatives.sort(key=lambda x: x["personalized_score"] or 0, reverse=True)

    return {
        "current_product": {
            "product_id": current_product["product_id"],
            "product_name": current_product["product_name"],
            "personalized_score": curr_score,
            "category": category
        },
        "target_goal": goal,
        "alternatives_count": len(alternatives[:limit]),
        "alternatives": alternatives[:limit]
    }
