"""
EATGOOD — Automated Test Suite
Verifies data loading, 3-layer assessment logic, allergen conflicts,
missing data handling, recommendation rankings, and claim detection.
"""

import pytest
import pandas as pd
from backend.core.data_loader import data_loader
from backend.core.standards_registry import CALIBRATED_CATEGORIES, get_applicable_standards
from backend.core.allergen_engine import analyze_allergens
from backend.core.claims_detector import evaluate_claims
from backend.core.nutrition_scoring import (
    assess_general_nutrition, assess_personalized_suitability, run_full_product_assessment
)
from backend.core.recommender import get_healthier_alternatives

def test_data_loader_integrity():
    assert data_loader.products_df is not None
    assert len(data_loader.products_df) == 852, f"Expected 852 products, found {len(data_loader.products_df)}"
    
    # Audit metrics check
    audit = data_loader.get_audit_metrics()
    assert audit["total_atwater_discrepancies"] == 78, f"Expected 78 Atwater anomalies, found {audit['total_atwater_discrepancies']}"
    assert audit["total_macro_serving_discrepancies"] == 13, f"Expected 13 macro serving anomalies, found {audit['total_macro_serving_discrepancies']}"

def test_layer1_calibrated_vs_uncalibrated():
    # Calibrated category: Snacks
    snack = {
        "category": "Snacks",
        "energy_kcal": 520,
        "sugars_g": 3.5,
        "sodium_mg": 350,
        "saturated_fat_g": 3.8,
        "protein_g": 8.0,
        "dietary_fibre_g": 4.5
    }
    res_snack = assess_general_nutrition(snack)
    assert res_snack["status"] == "Calibrated"
    assert res_snack["grade"] in ["A", "B", "C", "D", "E"]

    # Uncalibrated category: Chocolates & Sweets
    sweet = {
        "category": "Chocolates & Sweets",
        "energy_kcal": 540,
        "sugars_g": 52.0,
        "sodium_mg": 80,
        "saturated_fat_g": 18.0
    }
    res_sweet = assess_general_nutrition(sweet)
    assert res_sweet["status"] == "Uncalibrated Category"
    assert res_sweet["grade"] == "N/A"
    assert "not currently calibrated" in res_sweet["explanation"]

def test_missing_data_refusal():
    # Product missing sugars and sodium
    incomplete_snack = {
        "category": "Snacks",
        "energy_kcal": 450,
        "sugars_g": None,
        "sodium_mg": None,
        "saturated_fat_g": 5.0
    }
    res = assess_general_nutrition(incomplete_snack)
    assert res["status"] == "Insufficient Data"
    assert "sugars_g" in res["missing_fields"]
    assert "sodium_mg" in res["missing_fields"]

def test_allergen_critical_conflict():
    user_profile = {
        "goal": "Reduce Sugar",
        "dietary_preference": "Vegetarian",
        "allergens_to_avoid": "Milk, Peanuts"
    }
    product_with_milk = {
        "product_id": "TEST_01",
        "product_name": "Milk Biscuit",
        "category": "Snacks",
        "sugars_g": 2.0,
        "sodium_mg": 200,
        "ingredients": "Refined wheat flour, sugar, butter (milk solids), salt",
        "allergens_declared": "Milk"
    }
    suitability = assess_personalized_suitability(product_with_milk, user_profile)
    assert suitability["has_critical_allergen_conflict"] is True
    assert suitability["personalized_score"] == 0, "Allergen conflict MUST zero out suitability score!"
    assert len(suitability["allergen_conflicts"]) > 0

def test_goal_personalization_delta():
    prod_high_sugar = {
        "product_id": "TEST_02",
        "product_name": "Sweet Cereal",
        "category": "Breakfast Cereals",
        "sugars_g": 28.0,
        "sodium_mg": 180,
        "protein_g": 7.0,
        "dietary_fibre_g": 3.0,
        "saturated_fat_g": 1.0,
        "ingredients": "Corn, Sugar, Malt",
        "allergens_declared": "None"
    }
    # User aiming to reduce sugar
    user_reduce_sugar = {"goal": "Reduce Sugar", "dietary_preference": "No preference", "allergens_to_avoid": ""}
    res_sugar_user = assess_personalized_suitability(prod_high_sugar, user_reduce_sugar)

    # User aiming for protein
    user_protein = {"goal": "Increase Protein", "dietary_preference": "No preference", "allergens_to_avoid": ""}
    res_protein_user = assess_personalized_suitability(prod_high_sugar, user_protein)

    assert res_sugar_user["personalized_score"] < res_protein_user["personalized_score"]
    assert any("sugar" in r.lower() for r in res_sugar_user["rules_applied"])

def test_misleading_claims_evaluation():
    prod_data = {
        "protein_g": 4.0, # Below 10g
        "sugars_g": 15.0, # Not zero sugar
        "ingredients": "Wheat flour, liquid glucose, palm oil"
    }
    claims = "High Protein, Zero Sugar, No Added Sugar"
    evals = evaluate_claims(claims, prod_data)
    
    assert len(evals) == 3
    # High protein check
    prot_eval = next(e for e in evals if e["claim"] == "High Protein")
    assert prot_eval["status"] == "Potential inconsistency"

    # Zero sugar check
    sugar_eval = next(e for e in evals if e["claim"] == "Zero Sugar")
    assert sugar_eval["status"] == "Potential inconsistency"

    # No added sugar check (has liquid glucose in ingredients)
    no_added_eval = next(e for e in evals if e["claim"] == "No Added Sugar")
    assert no_added_eval["status"] == "Potential inconsistency"

def test_incomplete_data_no_score():
    """Verifies that products with incomplete nutrition declarations do NOT receive a personalized score."""
    incomplete_prod = {
        "product_id": "CUSTOM_SCAN",
        "product_name": "qwe",
        "category": "Snacks",
        "energy_kcal": None,
        "sugars_g": None,
        "sodium_mg": None,
        "saturated_fat_g": None
    }
    profile = {"goal": "Balanced Choices", "dietary_preference": "No preference", "allergens_to_avoid": ""}
    res = assess_personalized_suitability(incomplete_prod, profile)
    
    assert res["personalized_score"] is None, "Incomplete product must NOT have a numeric personalized score!"
    assert res["has_insufficient_data"] is True
    assert res["calculation_breakdown"] is None
    assert "Insufficient Data" in res["suitability_status"]

def test_score_calculation_breakdown_and_scale():
    """Verifies 1–100 scale calibration and transparent step-by-step formula breakdown."""
    prod = {
        "product_id": "TEST_OATS",
        "product_name": "Rolled Oats",
        "category": "Breakfast Cereals",
        "energy_kcal": 380,
        "sugars_g": 1.2,
        "sodium_mg": 20,
        "protein_g": 13.0,
        "dietary_fibre_g": 10.0,
        "saturated_fat_g": 1.1,
        "trans_fat_g": 0.0
    }
    profile = {"goal": "Reduce Sugar", "dietary_preference": "Vegetarian", "allergens_to_avoid": ""}
    res = assess_personalized_suitability(prod, profile)
    
    assert res["personalized_score"] is not None
    assert 1 <= res["personalized_score"] <= 100
    assert res["calculation_breakdown"] is not None
    
    breakdown = res["calculation_breakdown"]
    assert breakdown["base_score"] == 70
    assert len(breakdown["steps"]) >= 3
    # Check that steps include starting base score and low sugar bonus
    assert breakdown["steps"][0]["factor"] == "Baseline Profile Neutral Score"
    assert any("Reduce Sugar" in s["factor"] for s in breakdown["steps"])
    assert breakdown["steps"][-1]["type"] == "final"
    assert breakdown["steps"][-1]["running_total"] == res["personalized_score"]

def test_product_catalogue_nutritional_filters():
    """Verifies that search_products filters accurately by nutrient limits."""
    # Test healthy sugar filter (<= 10g) in Breakfast Cereals
    healthy_cereals = data_loader.search_products(category="Breakfast Cereals", max_sugars=10.0, max_sodium=400.0, max_sat_fat=4.0)
    assert healthy_cereals["total"] == 55
    for p in healthy_cereals["products"]:
        assert p["sugars_g"] <= 10.0
        assert p["sodium_mg"] <= 400.0
        assert p["saturated_fat_g"] <= 4.0

    # Test unfiltered count in Breakfast Cereals
    all_cereals = data_loader.search_products(category="Breakfast Cereals")
    assert all_cereals["total"] == 160
