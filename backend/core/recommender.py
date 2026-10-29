"""
EATGOOD — Healthier Alternatives Recommender Engine (Section 9)
Recommends goal-aligned alternatives from a list of same-category candidates.
Strictly excludes allergen conflicts and explains comparative nutritional advantages.
"""

from typing import Any

import pandas as pd

from backend.core.nutrition_scoring import assess_general_nutrition, assess_personalized_suitability


def get_healthier_alternatives(
    current_product: dict[str, Any], user_profile: dict, candidates: list[dict[str, Any]], limit: int = 4
):
    """
    Picks healthier alternatives for the current product from the given candidates (already
    limited to its category). Never recommends products with allergen conflicts.
    Explains the comparative nutritional delta (e.g. -40% sugar, +3x fibre).
    """
    category = current_product.get("category")

    goal = user_profile.get("goal", "Balanced Choices")
    curr_assessment = assess_personalized_suitability(current_product, user_profile)
    curr_score = curr_assessment["personalized_score"] or 0

    alternatives = []

    for cand in candidates:
        suitability = assess_personalized_suitability(cand, user_profile)

        # Hard exclusions: any allergen conflict, a candidate whose allergen information is
        # missing while the user has allergens to avoid, or a dietary preference conflict.
        if (
            suitability["has_critical_allergen_conflict"]
            or suitability["allergen_check_incomplete"]
            or suitability["preference_conflict"]
        ):
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
            # A value missing on either product is never treated as 0.
            if pd.notna(cand.get("dietary_fibre_g")) and pd.notna(current_product.get("dietary_fibre_g")):
                curr_fib = current_product["dietary_fibre_g"]
                if cand["dietary_fibre_g"] > curr_fib + 2.0:
                    advantages.append(f"+{round(cand['dietary_fibre_g'] - curr_fib, 1)}g more dietary fibre")

            # Protein delta
            if pd.notna(cand.get("protein_g")) and pd.notna(current_product.get("protein_g")):
                curr_prot = current_product["protein_g"]
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
                "data_confidence_status": cand.get("data_confidence_status"),
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
