"""
EATGOOD — Standards Registry
Defines documented authoritative nutritional and food-safety reference standards
from WHO, FSSAI, and Codex Alimentarius.
No invented thresholds. Every reference is cited and verifiable.
"""

STANDARDS_REGISTRY = [
    {
        "standard_id": "STD_WHO_SEARO_2017_SUGAR",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO Regional Office for South-East Asia)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Total Sugars",
        "applicable_category": "Snacks",
        "measurement_basis": "per 100g",
        "threshold": 10.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Sugar)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-09-15",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_SODIUM_SNACK",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Sodium",
        "applicable_category": "Snacks",
        "measurement_basis": "per 100g",
        "threshold": 400.0,
        "unit": "mg",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Sodium)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-09-15",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_SATFAT_SNACK",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Saturated Fat",
        "applicable_category": "Snacks",
        "measurement_basis": "per 100g",
        "threshold": 4.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Saturated Fat)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-09-15",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_BEV_SUGAR_2020",
        "standard_name": "WHO Guidance on Sugar-Sweetened Beverages",
        "organization": "World Health Organization (WHO HQ)",
        "document_title": "Fiscal policies to promote healthy diets: policy brief",
        "publication_year": 2020,
        "nutrient": "Total Sugars",
        "applicable_category": "Packaged Beverages",
        "measurement_basis": "per 100ml",
        "threshold": 5.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (Sugar-Sweetened Beverage)",
        "citation_url": "https://www.who.int/publications/i/item/9789240019447",
        "verification_date": "2026-09-15",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_FSSAI_INR_2022_CEREALS",
        "standard_name": "FSSAI Draft Indian Nutrition Rating (INR)",
        "organization": "Food Safety and Standards Authority of India (FSSAI)",
        "document_title": "Draft Food Safety and Standards (Labelling and Display) Amendment Regulations",
        "publication_year": 2022,
        "nutrient": "Total Sugars",
        "applicable_category": "Breakfast Cereals",
        "measurement_basis": "per 100g",
        "threshold": 15.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "High Sugar Boundary for Cereals",
        "citation_url": "https://www.fssai.gov.in/upload/uploadfiles/files/Draft_Notification_Labelling_Display_20_09_2022.pdf",
        "verification_date": "2026-09-15",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_CODEX_FIBRE_1985",
        "standard_name": "Codex Guidelines on Nutrition Claims (CAC/GL 23-1997)",
        "organization": "Codex Alimentarius Commission (FAO/WHO)",
        "document_title": "Guidelines for Use of Nutrition and Health Claims",
        "publication_year": 2013,
        "nutrient": "Dietary Fibre",
        "applicable_category": "All Packaged Foods",
        "measurement_basis": "per 100g",
        "threshold": 6.0,
        "unit": "g",
        "comparison_operator": ">=",
        "classification": "Beneficial Nutrient (High in Fibre Claim Standard)",
        "citation_url": "https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%253A%252F%252Fworkspace.fao.org%252Fsites%252Fcodex%252FStandards%252FCAC%2BGL%2B23-1997%252FCXG_023e.pdf",
        "verification_date": "2026-09-15",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_CODEX_PROTEIN_1985",
        "standard_name": "Codex Guidelines on Nutrition Claims (CAC/GL 23-1997)",
        "organization": "Codex Alimentarius Commission (FAO/WHO)",
        "document_title": "Guidelines for Use of Nutrition and Health Claims",
        "publication_year": 2013,
        "nutrient": "Protein",
        "applicable_category": "All Packaged Foods",
        "measurement_basis": "per 100g",
        "threshold": 10.0,
        "unit": "g",
        "comparison_operator": ">=",
        "classification": "Beneficial Nutrient (Source of / High Protein Standard)",
        "citation_url": "https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%253A%252F%252Fworkspace.fao.org%252Fsites%252Fcodex%252FStandards%252FCAC%2BGL%2B23-1997%252FCXG_023e.pdf",
        "verification_date": "2026-09-15",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_TRANS_FAT_GLOBAL",
        "standard_name": "WHO REPLACE Trans Fat Action Package",
        "organization": "World Health Organization (WHO HQ)",
        "document_title": "REPLACE: An action package to eliminate industrially-produced trans-fatty acids",
        "publication_year": 2018,
        "nutrient": "Trans Fat",
        "applicable_category": "All Packaged Foods",
        "measurement_basis": "per 100g",
        "threshold": 0.2,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Mandatory Elimination Target (<2% total fat / <0.2g per 100g)",
        "citation_url": "https://www.who.int/teams/nutrition-and-food-safety/replace-trans-fat",
        "verification_date": "2026-09-15",
        "implementation_status": "Active / Calibrated"
    }
]

# Supported calibrated categories for Layer 1 grading
CALIBRATED_CATEGORIES = ["Snacks", "Breakfast Cereals", "Packaged Beverages"]

def get_applicable_standards(category: str):
    """Returns active standards applicable to a given product category."""
    standards = []
    for std in STANDARDS_REGISTRY:
        if std["applicable_category"] in [category, "All Packaged Foods"]:
            standards.append(std)
    return standards
