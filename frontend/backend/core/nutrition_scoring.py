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
    raw_goal = user_profile.get("goal", "Balanced Choices")
    if isinstance(raw_goal, list):
        goals = raw_goal
    else:
        goals = [g.strip() for g in str(raw_goal).split(",") if g.strip()]
    if not goals:
        goals = ["Balanced Choices"]
    primary_goal_str = ", ".join(goals)
    goal = primary_goal_str
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

    # 1. Hard Safety Exclusion: Critical Allergen Conflict
    if allergen_assessment["has_critical_conflict"]:
        allergen_names = ", ".join(c.get("allergen", "") for c in allergen_assessment.get("user_conflicts", []))
        return {
            "user_goal": primary_goal_str,
            "user_goals": goals,
            "dietary_preference": dietary_pref,
            "personalized_score": 0,
            "has_insufficient_data": False,
            "score_display": "0/100",
            "suitability_status": "Not Suitable — Critical Allergen Conflict",
            "suitability_badge": "Allergen Warning",
            "color": "red",
            "rules_applied": ["Safety Override: Critical Allergen Conflict Detected (Score: 0)"],
            "calculation_breakdown": {
                "scale_definition": {
                    "min": 1,
                    "min_label": "Unhealthy / Severe Profile Conflict",
                    "max": 100,
                    "max_label": "Healthiest / Optimal Profile Alignment",
                    "bands": [
                        {"range": "1 - 49", "label": "Unhealthy / Poor Match", "color": "#c62828"},
                        {"range": "50 - 74", "label": "Moderate Match", "color": "#00838f"},
                        {"range": "75 - 100", "label": "Healthiest / Optimal Match", "color": "#2e7d32"}
                    ]
                },
                "base_score": 70,
                "raw_score": 0,
                "final_score": 0,
                "steps": [
                    {
                        "step": 1,
                        "factor": "Baseline Starting Score",
                        "metric": "Standard 1–100 Scale Baseline",
                        "rule": "Neutral starting calibration",
                        "points": 70,
                        "points_str": "70",
                        "running_total": 70,
                        "type": "base"
                    },
                    {
                        "step": 2,
                        "factor": "Critical Allergen Conflict",
                        "metric": allergen_names or "Declared allergen",
                        "rule": "Absolute safety override: violates active profile allergen exclusion",
                        "points": -70,
                        "points_str": "Override (0)",
                        "running_total": 0,
                        "type": "override"
                    }
                ]
            },
            "goal_strengths": [],
            "goal_concerns": [
                f"Contains allergens strictly excluded in your profile ({allergen_names}). Consumption is not recommended."
            ],
            "allergen_conflicts": allergen_assessment["user_conflicts"],
            "has_critical_allergen_conflict": True,
            "preference_conflict": pref_conflict,
            "preference_reason": pref_reason
        }

    # 2. Incomplete / Missing Nutritional Data Verification
    critical_nutrients = ["energy_kcal", "sugars_g", "sodium_mg", "saturated_fat_g"]
    missing_critical = [
        f for f in critical_nutrients 
        if pd.isna(product_data.get(f)) or product_data.get(f) is None or str(product_data.get(f)).strip() == ""
    ]
    
    # Incomplete if sugars and sodium are both missing, or 2 or more critical fields are omitted
    has_insufficient_data = (
        len(missing_critical) >= 2 or 
        (
            (pd.isna(product_data.get("sugars_g")) or str(product_data.get("sugars_g")).strip() == "") and 
            (pd.isna(product_data.get("sodium_mg")) or str(product_data.get("sodium_mg")).strip() == "")
        )
    )

    if has_insufficient_data:
        friendly_names = {
            "energy_kcal": "Energy (kcal)",
            "sugars_g": "Total Sugars (g)",
            "sodium_mg": "Sodium (mg)",
            "saturated_fat_g": "Saturated Fat (g)"
        }
        missing_labels = [friendly_names.get(f, f) for f in missing_critical]
        return {
            "user_goal": primary_goal_str,
            "user_goals": goals,
            "dietary_preference": dietary_pref,
            "personalized_score": None,
            "has_insufficient_data": True,
            "score_display": "N/A",
            "suitability_status": "Insufficient Data to Calculate Personalized Score",
            "suitability_badge": "Incomplete Data",
            "color": "gray",
            "rules_applied": [],
            "calculation_breakdown": None,
            "goal_strengths": [],
            "goal_concerns": [
                f"Missing critical nutritional declarations: {', '.join(missing_labels)}. Please enter these values to compute an accurate 1–100 score."
            ],
            "allergen_conflicts": allergen_assessment["user_conflicts"],
            "has_critical_allergen_conflict": False,
            "preference_conflict": pref_conflict,
            "preference_reason": pref_reason
        }

    # 3. Transparent Multi-Factor Personalized Scoring (1 - 100 Scale)
    base_score = 70.0
    score = base_score
    steps = [
        {
            "step": 1,
            "factor": "Baseline Profile Neutral Score",
            "metric": "Standard 1–100 Scale Baseline",
            "rule": "Neutral starting calibration for verified nutrient declarations",
            "points": 70,
            "points_str": "70",
            "running_total": 70,
            "type": "base"
        }
    ]
    step_num = 2

    rules_applied = []
    goal_strengths = []
    goal_concerns = []

    sugars = product_data.get("sugars_g")
    sodium = product_data.get("sodium_mg")
    protein = product_data.get("protein_g")
    fibre = product_data.get("dietary_fibre_g")
    sat_fat = product_data.get("saturated_fat_g")
    trans_fat = product_data.get("trans_fat_g")

    weight = 1.0 if len(goals) == 1 else (0.85 if len(goals) == 2 else 0.7)

    # Goal: Reduce Sugar
    if "Reduce Sugar" in goals:
        if pd.notna(sugars) and str(sugars).strip() != "":
            sug_val = float(sugars)
            if sug_val <= 3.0:
                pts = round(20 * weight)
                score += pts
                goal_strengths.append(f"Very low sugar ({sug_val}g/100g) strongly benefits your 'Reduce Sugar' target.")
                rules_applied.append(f"Goal Reward: Total sugars <= 3g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sugar",
                    "metric": f"{sug_val}g sugars / 100g",
                    "rule": "Low sugar benchmark (<= 3.0g)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sug_val <= 7.0:
                pts = round(10 * weight)
                score += pts
                goal_strengths.append(f"Moderate sugar ({sug_val}g/100g) fits within sugar management targets.")
                rules_applied.append(f"Goal Reward: Total sugars 3g-7g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sugar",
                    "metric": f"{sug_val}g sugars / 100g",
                    "rule": "Moderate sugar benchmark (3.0g - 7.0g)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sug_val > 20.0:
                pts = -round(30 * weight)
                score += pts
                goal_concerns.append(f"High sugar level ({sug_val}g/100g) significantly impedes your 'Reduce Sugar' goal.")
                rules_applied.append(f"Goal Penalty: High sugar > 20g ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sugar",
                    "metric": f"{sug_val}g sugars / 100g",
                    "rule": "Excessive sugar threshold (> 20.0g)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1
            elif sug_val > 10.0:
                pts = -round(18 * weight)
                score += pts
                goal_concerns.append(f"Sugar content ({sug_val}g/100g) exceeds baseline threshold.")
                rules_applied.append(f"Goal Penalty: Elevated sugar 10g-20g ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sugar",
                    "metric": f"{sug_val}g sugars / 100g",
                    "rule": "Elevated sugar threshold (> 10.0g)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

    # Goal: Reduce Sodium
    if "Reduce Sodium" in goals:
        if pd.notna(sodium) and str(sodium).strip() != "":
            sod_val = float(sodium)
            if sod_val <= 140.0:
                pts = round(20 * weight)
                score += pts
                goal_strengths.append(f"Very low sodium ({sod_val}mg/100g) aligns with hypertension and sodium reduction targets.")
                rules_applied.append(f"Goal Reward: Low sodium <= 140mg (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sodium",
                    "metric": f"{sod_val}mg sodium / 100g",
                    "rule": "Low sodium benchmark (<= 140mg)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sod_val <= 350.0:
                pts = round(10 * weight)
                score += pts
                goal_strengths.append(f"Moderate sodium ({sod_val}mg/100g) fits daily allowance.")
                rules_applied.append(f"Goal Reward: Sodium 140mg-350mg (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sodium",
                    "metric": f"{sod_val}mg sodium / 100g",
                    "rule": "Moderate sodium benchmark (140mg - 350mg)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sod_val > 900.0:
                pts = -round(30 * weight)
                score += pts
                goal_concerns.append(f"Extremely high sodium ({sod_val}mg/100g) conflicts with 'Reduce Sodium' goal.")
                rules_applied.append(f"Goal Penalty: High sodium > 900mg ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sodium",
                    "metric": f"{sod_val}mg sodium / 100g",
                    "rule": "Excessive sodium threshold (> 900mg)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1
            elif sod_val > 400.0:
                pts = -round(18 * weight)
                score += pts
                goal_concerns.append(f"Elevated sodium ({sod_val}mg/100g) exceeds recommended boundary.")
                rules_applied.append(f"Goal Penalty: Elevated sodium 400mg-900mg ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Reduce Sodium",
                    "metric": f"{sod_val}mg sodium / 100g",
                    "rule": "Elevated sodium threshold (> 400mg)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

    # Goal: Increase Fibre
    if "Increase Fibre" in goals:
        if pd.notna(fibre) and str(fibre).strip() != "":
            fib_val = float(fibre)
            if fib_val >= 6.0:
                pts = round(25 * weight)
                score += pts
                goal_strengths.append(f"Excellent source of fibre ({fib_val}g/100g) directly fulfills your goal.")
                rules_applied.append(f"Goal Reward: High fibre >= 6g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Fibre",
                    "metric": f"{fib_val}g fibre / 100g",
                    "rule": "Codex high-fibre standard (>= 6.0g)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif fib_val >= 3.0:
                pts = round(12 * weight)
                score += pts
                goal_strengths.append(f"Provides good dietary fibre ({fib_val}g/100g).")
                rules_applied.append(f"Goal Reward: Moderate fibre >= 3g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Fibre",
                    "metric": f"{fib_val}g fibre / 100g",
                    "rule": "Good source of fibre (>= 3.0g)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif fib_val < 2.0:
                pts = -round(12 * weight)
                score += pts
                goal_concerns.append(f"Low dietary fibre ({fib_val}g/100g) relative to your increase-fibre goal.")
                rules_applied.append(f"Goal Adjustment: Low fibre < 2g ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Fibre",
                    "metric": f"{fib_val}g fibre / 100g",
                    "rule": "Low fibre relative to target (< 2.0g)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

    # Goal: Increase Protein
    if "Increase Protein" in goals:
        if pd.notna(protein) and str(protein).strip() != "":
            prot_val = float(protein)
            if prot_val >= 12.0:
                pts = round(25 * weight)
                score += pts
                goal_strengths.append(f"High protein concentration ({prot_val}g/100g) supports daily requirements.")
                rules_applied.append(f"Goal Reward: High protein >= 12g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Protein",
                    "metric": f"{prot_val}g protein / 100g",
                    "rule": "High protein standard (>= 12.0g)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif prot_val >= 7.0:
                pts = round(12 * weight)
                score += pts
                goal_strengths.append(f"Good protein contribution ({prot_val}g/100g).")
                rules_applied.append(f"Goal Reward: Moderate protein 7g-12g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Protein",
                    "metric": f"{prot_val}g protein / 100g",
                    "rule": "Good source of protein (7.0g - 12.0g)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif prot_val < 4.0:
                pts = -round(12 * weight)
                score += pts
                goal_concerns.append(f"Low protein contribution ({prot_val}g/100g).")
                rules_applied.append(f"Goal Adjustment: Low protein < 4g ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Goal: Increase Protein",
                    "metric": f"{prot_val}g protein / 100g",
                    "rule": "Low protein relative to target (< 4.0g)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

    # Goal: Balanced Choices
    if "Balanced Choices" in goals or len(goals) == 0:
        if pd.notna(sugars) and str(sugars).strip() != "":
            sug_val = float(sugars)
            if sug_val <= 5.0:
                pts = round(10 * weight)
                score += pts
                rules_applied.append(f"Balanced Factor: Modest sugar <= 5g (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Balanced Lifestyle",
                    "metric": f"{sug_val}g sugars / 100g",
                    "rule": "Modest sugar benchmark (<= 5.0g)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sug_val > 15.0:
                pts = -round(15 * weight)
                score += pts
                rules_applied.append(f"Balanced Factor: High sugar > 15g ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Balanced Lifestyle",
                    "metric": f"{sug_val}g sugars / 100g",
                    "rule": "Elevated sugar threshold (> 15.0g)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

        if pd.notna(sodium) and str(sodium).strip() != "":
            sod_val = float(sodium)
            if sod_val <= 300.0:
                pts = round(10 * weight)
                score += pts
                rules_applied.append(f"Balanced Factor: Controlled sodium <= 300mg (+{pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Balanced Lifestyle",
                    "metric": f"{sod_val}mg sodium / 100g",
                    "rule": "Controlled sodium benchmark (<= 300mg)",
                    "points": pts,
                    "points_str": f"+{pts}",
                    "running_total": int(round(score)),
                    "type": "bonus"
                })
                step_num += 1
            elif sod_val > 600.0:
                pts = -round(15 * weight)
                score += pts
                rules_applied.append(f"Balanced Factor: High sodium > 600mg ({pts} pts)")
                steps.append({
                    "step": step_num,
                    "factor": "Balanced Lifestyle",
                    "metric": f"{sod_val}mg sodium / 100g",
                    "rule": "Elevated sodium threshold (> 600mg)",
                    "points": pts,
                    "points_str": f"{pts}",
                    "running_total": int(round(score)),
                    "type": "penalty"
                })
                step_num += 1

        if pd.notna(protein) and str(protein).strip() != "" and float(protein) >= 6.0:
            pts = round(8 * weight)
            score += pts
            rules_applied.append(f"Balanced Factor: Solid protein >= 6g (+{pts} pts)")
            steps.append({
                "step": step_num,
                "factor": "Balanced Lifestyle",
                "metric": f"{float(protein)}g protein / 100g",
                "rule": "Solid protein contribution (>= 6.0g)",
                "points": pts,
                "points_str": f"+{pts}",
                "running_total": int(round(score)),
                "type": "bonus"
            })
            step_num += 1

        if pd.notna(fibre) and str(fibre).strip() != "" and float(fibre) >= 3.0:
            pts = round(8 * weight)
            score += pts
            rules_applied.append(f"Balanced Factor: Meaningful fibre >= 3g (+{pts} pts)")
            steps.append({
                "step": step_num,
                "factor": "Balanced Lifestyle",
                "metric": f"{float(fibre)}g fibre / 100g",
                "rule": "Meaningful dietary fibre (>= 3.0g)",
                "points": pts,
                "points_str": f"+{pts}",
                "running_total": int(round(score)),
                "type": "bonus"
            })
            step_num += 1

    # Baseline Health Factor: Saturated Fat
    if pd.notna(sat_fat) and str(sat_fat).strip() != "":
        sf_val = float(sat_fat)
        if sf_val > 8.0:
            pts = -15
            score += pts
            rules_applied.append(f"Heart Health: High saturated fat > 8g ({pts} pts)")
            goal_concerns.append(f"High saturated fat ({sf_val}g/100g) raises cardiovascular risk.")
            steps.append({
                "step": step_num,
                "factor": "Heart Health Factor",
                "metric": f"{sf_val}g sat fat / 100g",
                "rule": "High saturated fat benchmark (> 8.0g)",
                "points": pts,
                "points_str": f"{pts}",
                "running_total": int(round(score)),
                "type": "penalty"
            })
            step_num += 1
        elif sf_val > 4.5:
            pts = -8
            score += pts
            rules_applied.append(f"Heart Health: Elevated saturated fat > 4.5g ({pts} pts)")
            steps.append({
                "step": step_num,
                "factor": "Heart Health Factor",
                "metric": f"{sf_val}g sat fat / 100g",
                "rule": "Elevated saturated fat (> 4.5g)",
                "points": pts,
                "points_str": f"{pts}",
                "running_total": int(round(score)),
                "type": "penalty"
            })
            step_num += 1
        elif sf_val <= 1.5:
            pts = 5
            score += pts
            rules_applied.append(f"Heart Health: Low saturated fat <= 1.5g (+{pts} pts)")
            goal_strengths.append(f"Low saturated fat ({sf_val}g/100g).")
            steps.append({
                "step": step_num,
                "factor": "Heart Health Factor",
                "metric": f"{sf_val}g sat fat / 100g",
                "rule": "Low saturated fat benchmark (<= 1.5g)",
                "points": pts,
                "points_str": f"+{pts}",
                "running_total": int(round(score)),
                "type": "bonus"
            })
            step_num += 1

    # Baseline Health Factor: Trans Fat
    if pd.notna(trans_fat) and str(trans_fat).strip() != "" and float(trans_fat) > 0.1:
        pts = -20
        score += pts
        rules_applied.append(f"Safety Standard: Contains industrial trans fat ({pts} pts)")
        goal_concerns.append(f"Contains industrial trans fats ({float(trans_fat)}g).")
        steps.append({
            "step": step_num,
            "factor": "WHO REPLACE Standard",
            "metric": f"{float(trans_fat)}g trans fat",
            "rule": "Zero-trans-fat target violation (> 0.1g)",
            "points": pts,
            "points_str": f"{pts}",
            "running_total": int(round(score)),
            "type": "penalty"
        })
        step_num += 1

    # Dietary Preference Restriction
    if pref_conflict:
        score = min(15.0, score)
        steps.append({
            "step": step_num,
            "factor": "Dietary Preference Conflict",
            "metric": dietary_pref,
            "rule": pref_reason,
            "points": "Cap at 15",
            "points_str": "Cap at 15",
            "running_total": int(round(score)),
            "type": "override"
        })
        step_num += 1

    # Final 1 to 100 Score Clamping (1 = unhealthiest/worst match, 100 = healthiest/ideal match)
    raw_score = int(round(score))
    final_score = max(1, min(100, raw_score))

    steps.append({
        "step": step_num,
        "factor": "Final 1–100 Scale Calibration",
        "metric": f"Raw computation: {raw_score}",
        "rule": "Calibrated between 1 (unhealthy / severe conflict) and 100 (healthiest match)",
        "points": "=",
        "points_str": "=",
        "running_total": final_score,
        "type": "final"
    })

    if pref_conflict:
        suitability_status = f"Not Recommended — {pref_reason}"
        suitability_badge = "Preference Conflict"
        color = "orange"
    elif final_score >= 75:
        suitability_status = f"Highly Suitable for your target: {primary_goal_str}"
        suitability_badge = "Healthiest / Optimal Match"
        color = "green"
    elif final_score >= 50:
        suitability_status = f"Moderately Suitable for target: {primary_goal_str}"
        suitability_badge = "Moderate Match"
        color = "teal"
    else:
        suitability_status = f"Suboptimal alignment with target: {primary_goal_str}"
        suitability_badge = "Unhealthy / Poor Match"
        color = "orange" if final_score >= 30 else "red"

    return {
        "user_goal": primary_goal_str,
        "user_goals": goals,
        "dietary_preference": dietary_pref,
        "personalized_score": final_score,
        "has_insufficient_data": False,
        "score_display": f"{final_score}/100",
        "suitability_status": suitability_status,
        "suitability_badge": suitability_badge,
        "color": color,
        "rules_applied": rules_applied,
        "calculation_breakdown": {
            "scale_definition": {
                "min": 1,
                "min_label": "Unhealthy / Severe Profile Conflict",
                "max": 100,
                "max_label": "Healthiest / Optimal Profile Alignment",
                "bands": [
                    {"range": "1 - 49", "label": "Unhealthy / Poor Match", "color": "#c62828"},
                    {"range": "50 - 74", "label": "Moderate Match", "color": "#00838f"},
                    {"range": "75 - 100", "label": "Healthiest / Optimal Match", "color": "#2e7d32"}
                ]
            },
            "base_score": 70,
            "raw_score": raw_score,
            "final_score": final_score,
            "steps": steps
        },
        "goal_strengths": goal_strengths,
        "goal_concerns": goal_concerns,
        "allergen_conflicts": allergen_assessment["user_conflicts"],
        "has_critical_allergen_conflict": False,
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
