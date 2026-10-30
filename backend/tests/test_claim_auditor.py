"""
EATGOOD — Front-of-Pack Marketing Claim Auditor Regression & Taxonomy Suite
Verifies:
1. Taxonomy classification across all 10 claim categories.
2. Rule precedence (comparative/nutrient claims evaluated before sensory/descriptive).
3. Superlative and relative comparative claim evaluation.
4. Multi-label claim detection (e.g. sensory + nutrient-content, comparative + sugar-related).
5. Robust normalization (uppercase, extra whitespace, punctuation).
6. Separation of classification from compliance assessment.
7. Missing data handling and regulatory provenance.
"""

from fastapi.testclient import TestClient

from backend.core.claims_detector import evaluate_single_claim
from backend.main import app

client = TestClient(app)

def test_highest_protein_classification_root_cause_fix():
    """
    Directly tests the reported bug:
    'highest protein' must NOT be classified as 'Descriptive / Sensory Claim'.
    It must be classified as 'Comparative Nutrition Claim'.
    """
    prod_data = {"protein_g": 12.0}
    res = evaluate_single_claim("highest protein", prod_data)

    assert "Comparative Nutrition Claim" in res["detected_claim_types"]
    assert res["primary_claim_type"] == "Comparative Nutrition Claim"
    assert "Descriptive / Sensory Claim" not in res["detected_claim_types"]
    assert res["relevant_nutrient"] == "Protein"
    assert "highest" in res["comparative_terms"]
    assert res["comparison_details"]["comparison_type"] == "superlative"
    assert res["compliance_status"] == "Insufficient evidence to assess compliance"
    assert any("category-wide" in m.lower() for m in res["missing_information"])
    assert "FSSAI" in res["regulatory_source"]

def test_highest_in_protein_variation():
    res = evaluate_single_claim("highest in protein", {"protein_g": 15.0})
    assert "Comparative Nutrition Claim" in res["detected_claim_types"]
    assert res["primary_claim_type"] == "Comparative Nutrition Claim"
    assert res["relevant_nutrient"] == "Protein"

def test_more_protein_comparative():
    res = evaluate_single_claim("more protein", {"protein_g": 8.0})
    assert "Comparative Nutrition Claim" in res["detected_claim_types"]
    assert res["primary_claim_type"] == "Comparative Nutrition Claim"
    assert res["comparison_details"]["comparison_type"] == "relative"
    assert res["compliance_status"] == "Potential concern — review required"
    assert any("reference food" in m.lower() for m in res["missing_information"])

def test_percentage_comparative_with_named_comparator():
    res = evaluate_single_claim("30% more protein than our regular product", {"protein_g": 12.0})
    assert "Comparative Nutrition Claim" in res["detected_claim_types"]
    assert res["comparison_details"]["claimed_difference"] == "30% more"
    assert res["comparison_details"]["comparator"] == "our regular product"
    assert res["compliance_status"] == "Insufficient evidence to assess compliance"
    assert any("baseline" in m.lower() for m in res["missing_information"])

def test_high_protein_nutrient_content():
    # Pass threshold (>= 10g)
    res_pass = evaluate_single_claim("high protein", {"protein_g": 11.5})
    assert "Nutrient-Content Claim" in res_pass["detected_claim_types"]
    assert res_pass["primary_claim_type"] == "Nutrient-Content Claim"
    assert res_pass["compliance_status"] == "Consistent with the checked criteria"

    # Below threshold (< 10g)
    res_fail = evaluate_single_claim("high protein", {"protein_g": 4.2})
    assert "Nutrient-Content Claim" in res_fail["detected_claim_types"]
    assert res_fail["compliance_status"] == "Potentially inconsistent with the checked criteria"

def test_source_of_fibre():
    res = evaluate_single_claim("source of fibre", {"dietary_fibre_g": 3.5})
    assert "Nutrient-Content Claim" in res["detected_claim_types"]
    assert res["compliance_status"] == "Consistent with the checked criteria"

def test_low_fat_nutrient_content():
    res_pass = evaluate_single_claim("low fat", {"total_fat_g": 2.1})
    assert "Nutrient-Content Claim" in res_pass["detected_claim_types"]
    assert res_pass["compliance_status"] == "Consistent with the checked criteria"

    res_fail = evaluate_single_claim("low fat", {"total_fat_g": 8.5})
    assert res_fail["compliance_status"] == "Potentially inconsistent with the checked criteria"

def test_sugar_free_claim():
    res_pass = evaluate_single_claim("sugar-free", {"sugars_g": 0.2})
    assert "Sugar-Related Claim" in res_pass["detected_claim_types"]
    assert res_pass["compliance_status"] == "Consistent with the checked criteria"

    res_fail = evaluate_single_claim("sugar-free", {"sugars_g": 6.8})
    assert res_fail["compliance_status"] == "Potentially inconsistent with the checked criteria"

def test_no_added_sugar_and_hidden_sugars():
    # True clean product
    res_clean = evaluate_single_claim(
        "no added sugar",
        {"added_sugars_g": 0.0, "ingredients": "Whole wheat, water, yeast, salt"}
    )
    assert "Sugar-Related Claim" in res_clean["detected_claim_types"]
    assert res_clean["compliance_status"] == "Consistent with the checked criteria"

    # Product claiming no added sugar but containing invert syrup / maltodextrin
    res_hidden = evaluate_single_claim(
        "no added sugar",
        {"added_sugars_g": 0.0, "ingredients": "Oats, invert sugar, palm oil, flavour"}
    )
    assert res_hidden["compliance_status"] == "Potentially inconsistent with the checked criteria"
    assert "invert sugar" in res_hidden["evidence"].lower()

def test_reduced_sugar_dual_classification():
    """'reduced sugar' is both Comparative Nutrition Claim and Sugar-Related Claim."""
    res = evaluate_single_claim("reduced sugar", {"sugars_g": 5.0})
    assert "Comparative Nutrition Claim" in res["detected_claim_types"]
    assert "Sugar-Related Claim" in res["detected_claim_types"]
    assert res["primary_claim_type"] == "Comparative Nutrition Claim"

def test_health_related_claim():
    res = evaluate_single_claim("supports immunity", {})
    assert "Health-Related Claim" in res["detected_claim_types"]
    assert res["primary_claim_type"] == "Health-Related Claim"
    assert res["compliance_status"] == "Potential concern — review required"
    assert any("clinical" in m.lower() for m in res["missing_information"])

def test_sensory_and_descriptive_claim():
    res = evaluate_single_claim("crispy and delicious", {})
    assert "Descriptive / Sensory Claim" in res["detected_claim_types"]
    assert res["primary_claim_type"] == "Descriptive / Sensory Claim"
    assert res["compliance_status"] == "Classification complete — non-statutory sensory claim"
    assert len(res["missing_information"]) == 0

def test_multi_label_claim_crispy_high_protein_snack():
    """'crispy, high protein snack' must detect both sensory and nutrient-content claim types."""
    res = evaluate_single_claim("crispy, high protein snack", {"protein_g": 14.0})
    assert "Descriptive / Sensory Claim" in res["detected_claim_types"]
    assert "Nutrient-Content Claim" in res["detected_claim_types"]
    assert res["primary_claim_type"] == "Nutrient-Content Claim"
    assert res["compliance_status"] == "Consistent with the checked criteria"

def test_normalization_and_formatting_robustness():
    # Uppercase
    res_upper = evaluate_single_claim("HIGHEST PROTEIN", {"protein_g": 12.0})
    assert res_upper["primary_claim_type"] == "Comparative Nutrition Claim"

    # Whitespace and punctuation
    res_punct = evaluate_single_claim("   30%   LESS   SODIUM!   ", {"sodium_mg": 180.0})
    assert res_punct["primary_claim_type"] == "Comparative Nutrition Claim"
    assert "sodium" in res_punct["relevant_nutrient"].lower()

def test_missing_data_insufficient_evidence():
    # High protein claim on product with no protein declared
    res = evaluate_single_claim("high protein", {"protein_g": None})
    assert res["compliance_status"] == "Insufficient evidence to assess compliance"
    assert any("protein declaration" in m.lower() for m in res["missing_information"])

def test_unclassified_ambiguous_claim():
    res = evaluate_single_claim("mom's secret recipe for vitality", {})
    assert "Unclassified or Ambiguous Claim" in res["detected_claim_types"]
    assert res["compliance_status"] == "Potential concern — review required"
    assert res["primary_claim_type"] == "Unclassified or Ambiguous Claim"

def test_api_full_product_assessment_includes_audited_claims():
    """Integration check: an assessment returns structured claim analysis."""
    response = client.post("/api/products/assess", json={
        "product_name": "Protein Crisps", "category": "Snacks", "measurement_basis": "per 100g",
        "energy_kcal": 480, "sugars_g": 3, "sodium_mg": 500, "saturated_fat_g": 5, "protein_g": 8,
        "marketing_claims": "High Protein, Low Fat",
    })
    assert response.status_code == 200
    data = response.json()
    claims_analysis = data.get("marketing_claims_analysis") or data.get("assessment", {}).get("marketing_claims_analysis", [])
    assert len(claims_analysis) > 0
    cl = claims_analysis[0]
    assert "detected_claim_types" in cl
    assert "compliance_status" in cl
    assert "classification_rationale" in cl
    assert "regulatory_source" in cl

def test_nutrient_function_claim_distinction():
    """Verifies that functional physiological claims (e.g. helps build muscle) are detected as Nutrient-Function."""
    res = evaluate_single_claim("helps build muscle", {"protein_g": 12.0})
    assert "Nutrient-Function Claim" in res["detected_claim_types"]
    assert res["primary_claim_type"] == "Nutrient-Function Claim"
    assert res["compliance_status"] == "Potential concern — review required"
    assert "FSSAI" in res["regulatory_source"]



def test_claims_read_from_a_pack_are_checked_against_entered_values():
    from fastapi.testclient import TestClient

    from backend.main import app

    product = {"product_name": "Test Bar", "category": "Snacks", "energy_kcal": 400, "sugars_g": 2, "protein_g": 12,
               "dietary_fibre_g": 7, "saturated_fat_g": 1, "sodium_mg": 100, "ingredients": "whole wheat flour, sugar, salt"}
    res = TestClient(app).post("/api/claims/check", json={"claims": "High protein\nNo added sugar\nGluten-free", "product": product})
    assert res.status_code == 200
    verdicts = {c["claim"]: c["compliance_status"] for c in res.json()["claims"]}
    assert verdicts["High protein"].startswith("Consistent")
    assert verdicts["No added sugar"].startswith("Potentially inconsistent")
    assert verdicts["Gluten-free"].startswith("Potentially inconsistent")

    assert TestClient(app).post("/api/claims/check", json={"claims": "High protein"}).status_code == 400


def test_accurate_claims_on_products_over_their_limits_get_context():
    from backend.core.claims_detector import add_misleading_context, evaluate_claims

    snack = {"category": "Snacks", "measurement_basis": "per 100g", "energy_kcal": 540, "sugars_g": 2, "protein_g": 12,
             "saturated_fat_g": 9.6, "sodium_mg": 780, "ingredients": "soya, palm oil, salt"}
    results = evaluate_claims("High protein, crunchy", snack)
    add_misleading_context(results, snack)
    by_claim = {r["claim"]: r for r in results}
    assert "high in sodium, saturated fat and calories" in by_claim["High protein"]["context_note"]
    assert "context_note" not in by_claim["crunchy"]  # sensory words aren't health claims

    clean = {**snack, "saturated_fat_g": 1, "sodium_mg": 100, "energy_kcal": 380}
    results = evaluate_claims("High protein", clean)
    add_misleading_context(results, clean)
    assert "context_note" not in results[0]
