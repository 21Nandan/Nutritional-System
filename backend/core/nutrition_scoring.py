"""
EATGOOD — Hybrid Food Grading Engine (Section 4)
Implements:
- Layer 1: General Nutritional Assessment (Standards-based, Category-calibrated)
- Layer 2: Personalized Suitability (User Goal & Dietary Preference tailored)
- Layer 3: Hard Safety Exclusions & Allergen Warning integration
Refuses uncalibrated categories and handles missing data transparently.
"""

import pandas as pd
from backend.core.standards_registry import CALIBRATED_CATEGORIES, get_applicable_standards
from backend.core.allergen_engine import analyze_allergens, analyze_additives
from backend.core.claims_detector import evaluate_claims

def assess_general_nutrition(product_data: dict):
    """
    Layer 1: General Nutritional Assessment
    Computes an evidence-based nutrition grade for calibrated categories:
    - Snacks
    - Breakfast Cereals
    - Packaged Beverages
    Refuses grading for uncalibrated categories or when critical data are missing.
    """
    category = product_data.get("category", "")
    
    # Check calibrated scope
    if category not in CALIBRATED_CATEGORIES:
        return {
            "status": "Uncalibrated Category",
            "grade": "N/A",
            "grade_label": "Category Not Yet Calibrated",
            "explanation": (
                f"Products in '{category}' are not currently calibrated under the active WHO/FSSAI prototype benchmarks. "
                "Available nutrition facts are displayed below for informational review without an automated letter grade."
            ),
            "strengths": [],
            "concerns": [],
            "missing_fields": [],
            "standards_applied": []
        }

    # Verify critical nutrition data presence (Energy, Sugars, Sodium, Saturated Fat)
    critical_fields = ["energy_kcal", "sugars_g", "sodium_mg", "saturated_fat_g"]
    missing_fields = [f for f in critical_fields if pd.isna(product_data.get(f))]

    if missing_fields:
        return {
            "status": "Insufficient Data",
            "grade": "Insufficient Data",
            "grade_label": "Insufficient Data for Reliable Assessment",
            "explanation": f"Missing critical nutrient declarations: {', '.join(missing_fields)}. An evidence-based grade cannot be computed.",
            "strengths": [],
            "concerns": ["Incomplete nutritional panel — manufacturer omitted required baseline metrics."],
            "missing_fields": missing_fields,
            "standards_applied": []
        }

    # Retrieve values
    sugars = float(product_data.get("sugars_g", 0))
    sodium = float(product_data.get("sodium_mg", 0))
    sat_fat = float(product_data.get("saturated_fat_g", 0))
    protein = float(product_data.get("protein_g", 0)) if pd.notna(product_data.get("protein_g")) else 0.0
    fibre = float(product_data.get("dietary_fibre_g", 0)) if pd.notna(product_data.get("dietary_fibre_g")) else 0.0
    trans_fat = float(product_data.get("trans_fat_g", 0)) if pd.notna(product_data.get("trans_fat_g")) else 0.0

    strengths = []
    concerns = []
    standards_applied = get_applicable_standards(category)

    # Negative points (nutrients of concern)
    penalty_points = 0
    
    # 1. Sugars evaluation
    if category == "Packaged Beverages":
        # WHO Beverage threshold: > 5.0g per 100ml
        if sugars > 10.0:
            penalty_points += 4
            concerns.append(f"Very high sugar content ({sugars}g/100ml) — exceeds WHO beverage recommendation (>5g/100ml) by over 100%.")
        elif sugars > 5.0:
            penalty_points += 2
            concerns.append(f"Exceeds WHO sugar threshold for packaged beverages ({sugars}g/100ml vs >5g standard).")
        elif sugars <= 1.0:
            strengths.append(f"Virtually sugar-free ({sugars}g/100ml).")
    else:
        # Solid foods (Snacks & Cereals)
        sugar_thresh = 15.0 if category == "Breakfast Cereals" else 10.0
        if sugars > (sugar_thresh * 2):
            penalty_points += 4
            concerns.append(f"Excessive sugar ({sugars}g/100g) — exceeds category threshold ({sugar_thresh}g/100g) significantly.")
        elif sugars > sugar_thresh:
            penalty_points += 2
            concerns.append(f"High total sugar content ({sugars}g/100g) relative to regional nutrient guidelines ({sugar_thresh}g/100g).")
        elif sugars <= 4.0:
            strengths.append(f"Low sugar content ({sugars}g/100g).")

    # 2. Sodium evaluation
    sodium_thresh = 400.0 if category == "Snacks" else (300.0 if category == "Breakfast Cereals" else 80.0)
    if sodium > (sodium_thresh * 2):
        penalty_points += 4
        concerns.append(f"Very high sodium ({sodium}mg) — exceeds standard ({sodium_thresh}mg) by more than double.")
    elif sodium > sodium_thresh:
        penalty_points += 2
        concerns.append(f"Elevated sodium level ({sodium}mg) above WHO SEARO recommended benchmark ({sodium_thresh}mg).")
    elif sodium <= 120.0 and category != "Packaged Beverages":
        strengths.append(f"Low sodium ({sodium}mg/100g) supporting cardiovascular health guidelines.")

    # 3. Saturated Fat
    sat_thresh = 4.0 if category == "Snacks" else 2.0
    if sat_fat > (sat_thresh * 2.5):
        penalty_points += 3
        concerns.append(f"High saturated fat ({sat_fat}g/100g) — common in deep-fried palm oil processing.")
    elif sat_fat > sat_thresh:
        penalty_points += 1
        concerns.append(f"Elevated saturated fat ({sat_fat}g/100g) exceeding baseline guidance ({sat_thresh}g).")
    elif sat_fat <= 1.5 and category != "Packaged Beverages":
        strengths.append(f"Low saturated fat ({sat_fat}g/100g).")

    # 4. Trans Fat check
    if trans_fat > 0.1:
        penalty_points += 3
        concerns.append(f"Contains trans fatty acids ({trans_fat}g) — violates WHO REPLACE zero-trans-fat target.")
    elif pd.notna(product_data.get("trans_fat_g")) and trans_fat == 0.0:
        strengths.append("Zero industrial trans fats declared.")

    # Positive nutrients (Fibre & Protein)
    bonus_points = 0
    if fibre >= 6.0:
        bonus_points += 3
        strengths.append(f"High in dietary fibre ({fibre}g/100g) — meets Codex CAC/GL 23-1997 high-fibre standard.")
    elif fibre >= 3.0:
        bonus_points += 1
        strengths.append(f"Source of dietary fibre ({fibre}g/100g).")

    if protein >= 10.0:
        bonus_points += 2
        strengths.append(f"High protein content ({protein}g/100g) supporting daily amino acid requirements.")
    elif protein >= 6.0 and category != "Packaged Beverages":
        bonus_points += 1
        strengths.append(f"Good source of protein ({protein}g/100g).")

    # Composite general score calculation
    # Base = 50, subtract penalties, add bonuses
    net_score = max(10, min(100, 50 - (penalty_points * 7) + (bonus_points * 8)))

    if net_score >= 80:
        grade = "A"
        grade_label = "Grade A — Optimal Nutritional Profile"
        color = "green"
    elif net_score >= 65:
        grade = "B"
        grade_label = "Grade B — Favourable Nutritional Balance"
        color = "teal"
    elif net_score >= 48:
        grade = "C"
        grade_label = "Grade C — Moderate / Consume in Moderation"
        color = "yellow"
    elif net_score >= 32:
        grade = "D"
        grade_label = "Grade D — Elevated Nutrients of Concern"
        color = "orange"
    else:
        grade = "E"
        grade_label = "Grade E — High in Sugar, Sodium, or Saturated Fat"
        color = "red"

    # Identify missing optional fields
    optional_missing = []
    for f, name in [("dietary_fibre_g", "Dietary Fibre"), ("added_sugars_g", "Added Sugars"), ("trans_fat_g", "Trans Fat")]:
        if pd.isna(product_data.get(f)):
            optional_missing.append(name)

    return {
        "status": "Calibrated",
        "grade": grade,
        "grade_label": grade_label,
        "general_nutrition_score": net_score,
        "color": color,
        "explanation": f"Assessed against {len(standards_applied)} authoritative benchmarks for {category}.",
        "strengths": strengths,
        "concerns": concerns,
        "missing_fields": optional_missing,
        "standards_applied": [s["standard_name"] for s in standards_applied]
    }

def assess_personalized_suitability(product_data: dict, user_profile: dict):
    """
    Layer 2: Personalized Suitability Assessment
    Tailors the evaluation specifically to the active user's goals and preferences.
    """
    goal = user_profile.get("goal", "Balanced Choices")
    dietary_pref = user_profile.get("dietary_preference", "No preference")
    user_allergens = [a.strip() for a in user_profile.get("allergens_to_avoid", "").split(",") if a.strip()]

    # Run Layer 3 Allergen Check
    allergen_assessment = analyze_allergens(
        ingredients=product_data.get("ingredients", ""),
        allergens_declared=product_data.get("allergens_declared", ""),
        user_allergens_to_avoid=user_allergens
    )

    # Dietary preference check
    pref_conflict = False
    pref_reason = ""
    ings_lower = str(product_data.get("ingredients", "")).lower()
    cat = product_data.get("category", "")

    if dietary_pref == "Vegetarian":
        if any(w in ings_lower for w in ["gelatin", "gelatine", "beef", "chicken", "meat", "pork", "fish oil", "carmine", "e120"]):
            pref_conflict = True
            pref_reason = "Contains animal-derived ingredients conflicting with Vegetarian preference."
    elif dietary_pref == "Vegan":
        if cat == "Dairy" or any(w in ings_lower for w in ["milk", "butter", "cheese", "whey", "casein", "lactose", "curd", "paneer", "honey", "egg", "gelatin"]):
            pref_conflict = True
            pref_reason = "Contains dairy, honey, or animal derivatives incompatible with Vegan diet."
    elif dietary_pref == "Lactose avoidance":
        if cat == "Dairy" or any(w in ings_lower for w in ["milk", "butter", "cheese", "whey", "casein", "lactose", "curd", "paneer", "dahi"]):
            pref_conflict = True
            pref_reason = "Contains lactose or milk solids incompatible with Lactose Avoidance."

    # Personalized scoring logic (0 - 100)
    score = 65.0
    rules_applied = []
    goal_strengths = []
    goal_concerns = []

    sugars = product_data.get("sugars_g")
    sodium = product_data.get("sodium_mg")
    protein = product_data.get("protein_g")
    fibre = product_data.get("dietary_fibre_g")
    sat_fat = product_data.get("saturated_fat_g")

    # Goal: Reduce Sugar
    if goal == "Reduce Sugar":
        if pd.notna(sugars):
            if sugars <= 3.0:
                score += 25
                goal_strengths.append(f"Very low sugar ({sugars}g) strongly benefits your 'Reduce Sugar' target.")
                rules_applied.append("Goal Reward: Total sugars <= 3g/100g (+25 pts)")
            elif sugars <= 7.0:
                score += 12
                goal_strengths.append(f"Moderate sugar ({sugars}g) fits within sugar management targets.")
                rules_applied.append("Goal Reward: Total sugars 3g-7g (+12 pts)")
            elif sugars > 20.0:
                score -= 35
                goal_concerns.append(f"High sugar level ({sugars}g) significantly impedes your 'Reduce Sugar' goal.")
                rules_applied.append("Goal Penalty: High sugar > 20g (-35 pts)")
            elif sugars > 10.0:
                score -= 20
                goal_concerns.append(f"Sugar content ({sugars}g) exceeds baseline threshold.")
                rules_applied.append("Goal Penalty: Elevated sugar 10g-20g (-20 pts)")
        else:
            goal_concerns.append("Sugar value not verified on label.")

    # Goal: Reduce Sodium
    elif goal == "Reduce Sodium":
        if pd.notna(sodium):
            if sodium <= 140.0:
                score += 25
                goal_strengths.append(f"Very low sodium ({sodium}mg) aligns with hypertension and sodium reduction targets.")
                rules_applied.append("Goal Reward: Low sodium <= 140mg (+25 pts)")
            elif sodium <= 350.0:
                score += 10
                goal_strengths.append(f"Moderate sodium ({sodium}mg) fits daily allowance.")
                rules_applied.append("Goal Reward: Sodium 140mg-350mg (+10 pts)")
            elif sodium > 900.0:
                score -= 35
                goal_concerns.append(f"Extremely high sodium ({sodium}mg) conflicts with 'Reduce Sodium' goal.")
                rules_applied.append("Goal Penalty: High sodium > 900mg (-35 pts)")
            elif sodium > 400.0:
                score -= 20
                goal_concerns.append(f"Elevated sodium ({sodium}mg) exceeds recommended boundary.")
                rules_applied.append("Goal Penalty: Elevated sodium 400mg-900mg (-20 pts)")
        else:
            goal_concerns.append("Sodium information missing.")

    # Goal: Increase Fibre
    elif goal == "Increase Fibre":
        if pd.notna(fibre):
            if fibre >= 6.0:
                score += 30
                goal_strengths.append(f"Excellent source of fibre ({fibre}g) directly fulfills your goal.")
                rules_applied.append("Goal Reward: High fibre >= 6g (+30 pts)")
            elif fibre >= 3.0:
                score += 15
                goal_strengths.append(f"Provides good dietary fibre ({fibre}g).")
                rules_applied.append("Goal Reward: Moderate fibre >= 3g (+15 pts)")
            else:
                score -= 15
                goal_concerns.append(f"Low dietary fibre ({fibre}g) relative to your increase-fibre goal.")
                rules_applied.append("Goal Adjustment: Low fibre < 3g (-15 pts)")
        else:
            goal_concerns.append("Dietary fibre is not declared on label.")
            score -= 10

    # Goal: Increase Protein
    elif goal == "Increase Protein":
        if pd.notna(protein):
            if protein >= 12.0:
                score += 30
                goal_strengths.append(f"High protein concentration ({protein}g/100g) supports muscle protein synthesis.")
                rules_applied.append("Goal Reward: High protein >= 12g (+30 pts)")
            elif protein >= 7.0:
                score += 15
                goal_strengths.append(f"Good protein contribution ({protein}g).")
                rules_applied.append("Goal Reward: Moderate protein 7g-12g (+15 pts)")
            else:
                score -= 15
                goal_concerns.append(f"Low protein contribution ({protein}g).")
                rules_applied.append("Goal Adjustment: Low protein < 7g (-15 pts)")
        else:
            goal_concerns.append("Protein content missing.")

    # Goal: Balanced Choices
    else:
        # Multidimensional balance
        if pd.notna(sugars) and sugars <= 7.0:
            score += 10
            rules_applied.append("Balanced Factor: Modest sugar (+10 pts)")
        if pd.notna(sodium) and sodium <= 400.0:
            score += 10
            rules_applied.append("Balanced Factor: Controlled sodium (+10 pts)")
        if pd.notna(protein) and protein >= 6.0:
            score += 10
            rules_applied.append("Balanced Factor: Solid protein (+10 pts)")
        if pd.notna(fibre) and fibre >= 3.0:
            score += 10
            rules_applied.append("Balanced Factor: Meaningful fibre (+10 pts)")
        if pd.notna(sat_fat) and sat_fat > 6.0:
            score -= 15
            rules_applied.append("Balanced Factor: Saturated fat penalty (-15 pts)")

    # Hard Safety & Conflict Overrides
    if allergen_assessment["has_critical_conflict"]:
        final_score = 0
        suitability_status = "Not Suitable — Critical Allergen Conflict"
        suitability_badge = "Allergen Warning"
        color = "red"
    elif pref_conflict:
        final_score = min(20, int(score))
        suitability_status = f"Not Recommended — {pref_reason}"
        suitability_badge = "Preference Conflict"
        color = "orange"
    else:
        final_score = max(5, min(98, int(score)))
        if final_score >= 75:
            suitability_status = f"Highly Suitable for your '{goal}' goal"
            suitability_badge = "Great Match"
            color = "green"
        elif final_score >= 55:
            suitability_status = f"Moderately Suitable for '{goal}'"
            suitability_badge = "Moderate Match"
            color = "teal"
        else:
            suitability_status = f"Suboptimal alignment with '{goal}'"
            suitability_badge = "Poor Match"
            color = "orange"

    return {
        "user_goal": goal,
        "dietary_preference": dietary_pref,
        "personalized_score": final_score,
        "suitability_status": suitability_status,
        "suitability_badge": suitability_badge,
        "color": color,
        "rules_applied": rules_applied,
        "goal_strengths": goal_strengths,
        "goal_concerns": goal_concerns,
        "allergen_conflicts": allergen_assessment["user_conflicts"],
        "has_critical_allergen_conflict": allergen_assessment["has_critical_conflict"],
        "preference_conflict": pref_conflict,
        "preference_reason": pref_reason
    }

def run_full_product_assessment(product_data: dict, user_profile: dict = None):
    """
    Executes the complete 3-layer food assessment pipeline for a product.
    """
    if user_profile is None:
        user_profile = {
            "goal": "Balanced Choices",
            "dietary_preference": "No preference",
            "allergens_to_avoid": ""
        }

    layer1 = assess_general_nutrition(product_data)
    layer2 = assess_personalized_suitability(product_data, user_profile)
    layer3_allergens = analyze_allergens(
        ingredients=product_data.get("ingredients", ""),
        allergens_declared=product_data.get("allergens_declared", ""),
        user_allergens_to_avoid=[a.strip() for a in user_profile.get("allergens_to_avoid", "").split(",") if a.strip()]
    )
    layer3_additives = analyze_additives(
        ingredients=product_data.get("ingredients", ""),
        additives_declared=product_data.get("additives", "")
    )
    marketing_eval = evaluate_claims(
        marketing_claims=product_data.get("marketing_claims", ""),
        product_data=product_data
    )

    return {
        "product_id": product_data.get("product_id"),
        "product_name": product_data.get("product_name"),
        "brand": product_data.get("brand"),
        "category": product_data.get("category"),
        "sub_category": product_data.get("sub_category"),
        "serving_size": product_data.get("serving_size"),
        "serving_size_unit": product_data.get("serving_size_unit"),
        "measurement_basis": product_data.get("measurement_basis"),
        "data_confidence_status": product_data.get("data_confidence_status", "Verified"),
        "nutrition_facts": {
            "energy_kcal": product_data.get("energy_kcal"),
            "carbohydrates_g": product_data.get("carbohydrates_g"),
            "sugars_g": product_data.get("sugars_g"),
            "added_sugars_g": product_data.get("added_sugars_g"),
            "protein_g": product_data.get("protein_g"),
            "total_fat_g": product_data.get("total_fat_g"),
            "saturated_fat_g": product_data.get("saturated_fat_g"),
            "trans_fat_g": product_data.get("trans_fat_g"),
            "cholesterol_mg": product_data.get("cholesterol_mg"),
            "sodium_mg": product_data.get("sodium_mg"),
            "dietary_fibre_g": product_data.get("dietary_fibre_g"),
        },
        "ingredients": product_data.get("ingredients"),
        "layer1_general": layer1,
        "layer2_personalized": layer2,
        "layer3_allergens": layer3_allergens,
        "layer3_additives": layer3_additives,
        "marketing_claims_analysis": marketing_eval,
        "transparency": {
            "data_source": product_data.get("data_source", "Label Scan / Retail Packaging Audit"),
            "standards_applied": layer1.get("standards_applied", []),
            "assessment_disclaimer": (
                "EATGOOD provides educational nutritional and food-safety assessments based on available product packaging data. "
                "It does not replace personalized clinical dietetics or medical advice."
            )
        }
    }
