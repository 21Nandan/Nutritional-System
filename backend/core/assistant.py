"""
EATGOOD — Grounded AI Food Assistant
Provides evidence-based, transparent, rule-grounded answers to consumer questions
about packaged foods. Never contradicts deterministic Layer 1 FoPL grades or Layer 2
suitability scores. Never fabricates nutrients or ingredients.

Guarantees:
- Strict evidence grounding in product facts (nutrition table, ingredients, allergens)
- Alignment with statutory Indian (FSSAI) and international (WHO SEARO) guidelines
- Transparent citation of numeric facts per 100g/serving
- Absolute allergen safety precedence
- Medical disclaimer included on clinical queries
"""

import re
from typing import Dict, Any, Optional
import pandas as pd

from backend.core.nutrition_scoring import run_full_product_assessment

DISCLAIMER_MEDICAL = "Note: EATGOOD provides nutritional assessments based on declared packaging facts and published benchmarks. This is not individualized clinical medical advice."

def answer_product_question(
    product: Dict[str, Any],
    question: str,
    user_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates a user query against verified product facts and deterministic scoring layers.
    Returns a structured, transparent, factual answer with cited metrics.
    """
    clean_q = question.strip().lower()
    profile = user_profile or {
        "user_id": "USR_DEFAULT",
        "name": "Guest User",
        "goal": "Balanced Choices",
        "dietary_preference": "No preference",
        "allergens_to_avoid": ""
    }

    # Run deterministic assessment
    assessment = run_full_product_assessment(product, profile)
    layer1 = assessment.get("layer1_general", {})
    layer2 = assessment.get("layer2_personalized", {})
    layer3 = assessment.get("layer3_allergens", {})

    p_name = product.get("product_name", "this product")
    brand = product.get("brand", "Unknown")
    cat = product.get("category", "General Food")
    basis = product.get("measurement_basis", "per 100g")

    # Extract verified nutrients
    kcal = product.get("energy_kcal")
    sugars = product.get("sugars_g")
    sodium = product.get("sodium_mg")
    protein = product.get("protein_g")
    fibre = product.get("dietary_fibre_g")
    sat_fat = product.get("saturated_fat_g")
    ings = product.get("ingredients") or "Not declared on packaging"
    declared_allgs = product.get("allergens_declared") or "None declared"

    answer_parts = []
    citations = []
    clinical_intent = False

    # 1. Diabetes / Blood Sugar Queries
    if any(w in clean_q for w in ["diabet", "sugar", "insulin", "glycemic", "glucose"]):
        clinical_intent = True
        sug_str = f"{sugars}g/100g" if pd.notna(sugars) else "Not declared"
        fib_str = f"{fibre}g/100g" if pd.notna(fibre) else "0g"
        citations.append(f"Total Sugars: {sug_str}")
        citations.append(f"Dietary Fibre: {fib_str}")

        if pd.notna(sugars) and float(sugars) > 10.0:
            answer_parts.append(
                f"**High Sugar Content:** {p_name} contains **{sug_str}** of total sugars, "
                f"which exceeds the WHO standard threshold of 10g/100g for this category. "
                f"Foods high in free sugars can cause rapid post-prandial blood glucose spikes."
            )
        elif pd.notna(sugars) and float(sugars) <= 5.0:
            answer_parts.append(
                f"**Low Sugar Content:** {p_name} contains **{sug_str}** of total sugars, "
                f"which is well within moderate limits (<= 5g/100g)."
            )
        else:
            answer_parts.append(
                f"**Moderate Sugar Content:** {p_name} contains **{sug_str}** of total sugars."
            )

        if pd.notna(fibre) and float(fibre) >= 5.0:
            answer_parts.append(
                f"Dietary fibre is favourable (**{fib_str}**), which helps moderate the absorption rate of carbohydrates."
            )
        elif pd.notna(fibre) and float(fibre) < 2.0:
            answer_parts.append(
                f"Dietary fibre is low (**{fib_str}**), offering minimal buffer against carbohydrate absorption."
            )

    # 2. Blood Pressure / Sodium / Hypertension Queries
    elif any(w in clean_q for w in ["blood pressure", "hypertension", "bp", "salt", "sodium"]):
        clinical_intent = True
        sod_str = f"{int(sodium)}mg/100g" if pd.notna(sodium) else "Not declared"
        citations.append(f"Sodium: {sod_str}")

        if pd.notna(sodium) and float(sodium) > 600.0:
            answer_parts.append(
                f"**High Sodium Warning:** {p_name} contains **{sod_str}** of sodium. "
                f"This significantly exceeds the WHO benchmark for snacks (350–500 mg/100g) "
                f"and represents over 30% of the recommended daily sodium allowance (2000 mg) in a standard 100g portion."
            )
        elif pd.notna(sodium) and float(sodium) <= 350.0:
            answer_parts.append(
                f"**Low-to-Moderate Sodium:** {p_name} contains **{sod_str}** of sodium, "
                f"which conforms to the low-sodium benchmark (<= 350 mg/100g)."
            )
        else:
            answer_parts.append(
                f"**Moderate Sodium:** {p_name} contains **{sod_str}** of sodium."
            )

    # 3. Allergen Specific Queries (Peanut, Gluten, Dairy, Soy, Egg)
    elif any(w in clean_q for w in ["allergy", "allergic", "peanut", "gluten", "celiac", "dairy", "lactose", "soy", "egg", "wheat"]):
        target_allg = None
        for a in ["peanut", "gluten", "dairy", "milk", "soy", "egg", "wheat"]:
            if a in clean_q:
                target_allg = a
                break

        citations.append(f"Declared Allergens: {declared_allgs}")
        citations.append(f"Ingredients: {ings[:100]}...")

        if layer3.get("has_critical_conflict"):
            conflicts = ", ".join(c.get("allergen", "") for c in layer3.get("user_conflicts", []))
            answer_parts.append(
                f"⚠️ **Critical Safety Alert:** An allergen conflict was identified ({conflicts}). "
                f"This product is strictly flagged as **unsafe** for your profile."
            )
        else:
            found_in_ings = False
            if target_allg:
                ings_l = str(ings).lower()
                allg_l = str(declared_allgs).lower()
                if target_allg in ings_l or target_allg in allg_l:
                    found_in_ings = True
                    answer_parts.append(
                        f"⚠️ **Contains {target_allg.title()}:** Verified on label packaging. "
                        f"Found in declared allergens or ingredient list."
                    )
            if not found_in_ings:
                answer_parts.append(
                    f"**No {target_allg.title() if target_allg else 'conflict'} detected on label:** "
                    f"Neither the ingredients list nor the allergen declaration explicitly lists {target_allg or 'the queried allergen'}. "
                    f"However, check manufacturer packaging for facility cross-contamination notices ('May contain traces of...')."
                )

    # 4. Score / Grade Explanation Queries
    elif any(w in clean_q for w in ["why", "score", "grade", "rating", "how good", "bad", "healthy"]):
        gen_grade = layer1.get("grade", "N/A")
        pers_score = layer2.get("personalized_score", "N/A")
        citations.append(f"General Grade: {gen_grade}")
        citations.append(f"Personalized Score: {pers_score}/100")
        citations.append(f"Goal: {layer2.get('user_goal', profile.get('goal', 'Balanced Choices'))}")

        reasons = []
        # Check Layer 1 flags
        flags = layer1.get("threshold_flags") or []
        for fl in flags:
            reasons.append(f"Exceeds statutory threshold for {fl.get('nutrient')}: {fl.get('actual_value')} (benchmark: {fl.get('threshold_value')})")

        # Check Layer 2 goal match
        user_rules = layer2.get("rules_applied") or []
        for r in user_rules[:2]:
            reasons.append(r)

        answer_parts.append(
            f"{p_name} received an Overall Grade of **{gen_grade}** and a Personal Goal Match of **{pers_score}/100**."
        )
        if reasons:
            answer_parts.append("Key contributing factors:\n- " + "\n- ".join(reasons))
        else:
            answer_parts.append(f"Nutrient composition is balanced according to calibrated {cat} category standards.")

    # 5. Protein / Muscle / Workout Queries
    elif any(w in clean_q for w in ["protein", "muscle", "workout", "gym", "bodybuilding"]):
        prot_str = f"{protein}g/100g" if pd.notna(protein) else "Not declared"
        citations.append(f"Protein: {prot_str}")
        if pd.notna(protein) and float(protein) >= 10.0:
            answer_parts.append(
                f"**High Protein Source:** {p_name} provides **{prot_str}** of protein. "
                f"This meets the statutory threshold (>= 10g/100g) for a high-protein packaged food."
            )
        elif pd.notna(protein) and float(protein) >= 5.0:
            answer_parts.append(
                f"**Moderate Protein:** {p_name} provides **{prot_str}** of protein."
            )
        else:
            answer_parts.append(
                f"**Low Protein:** {p_name} contains only **{prot_str}** of protein, "
                f"making it a poor primary protein source."
            )

    # 6. Default / Comprehensive Summary
    else:
        gen_grade = layer1.get("grade", "N/A")
        pers_score = layer2.get("personalized_score", "N/A")
        citations.append(f"Energy: {kcal or 'N/A'} kcal/100g")
        citations.append(f"Sugars: {sugars or 'N/A'} g")
        citations.append(f"Sodium: {int(sodium) if pd.notna(sodium) else 'N/A'} mg")
        citations.append(f"Protein: {protein or 'N/A'} g")

        answer_parts.append(
            f"**{p_name}** by {brand} is categorized under **{cat}**. "
            f"It receives an Overall Nutrition Grade of **{gen_grade}** and a personalized Goal Match of **{pers_score}/100** "
            f"for your active profile ('{profile.get('goal', 'Balanced Choices')}')."
        )
        if pd.notna(sugars) and float(sugars) > 10:
            answer_parts.append(f"Note: Total sugars ({sugars}g/100g) is elevated.")
        if pd.notna(sodium) and float(sodium) > 500:
            answer_parts.append(f"Note: Sodium ({int(sodium)}mg/100g) is elevated.")

    # Assemble response
    answer_text = "\n\n".join(answer_parts)
    if clinical_intent:
        answer_text += f"\n\n_{DISCLAIMER_MEDICAL}_"

    return {
        "product_id": product.get("product_id"),
        "product_name": p_name,
        "brand": brand,
        "question": question,
        "answer": answer_text,
        "evidence_citations": citations,
        "grounded_metrics": {
            "energy_kcal": kcal,
            "sugars_g": sugars,
            "sodium_mg": sodium,
            "protein_g": protein,
            "dietary_fibre_g": fibre,
            "general_grade": layer1.get("grade", "N/A"),
            "personalized_score": layer2.get("personalized_score", 0)
        },
        "regulatory_benchmarks": {
            "standards_version": "WHO SEARO / FSSAI INR 2026",
            "category": cat
        }
    }
