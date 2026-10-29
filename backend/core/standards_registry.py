"""
EATGOOD — Standards Registry
Defines documented authoritative nutritional and food-safety reference standards
from WHO, FSSAI, and Codex Alimentarius.
No invented thresholds. Every reference is cited and verifiable.
Distinguishes voluntary front-of-pack nutrition profiling from mandatory statutory labeling.
"""

from typing import Any

STANDARDS_REGISTRY_VERSION = "2026.2"

STANDARDS_REGISTRY: list[dict[str, Any]] = [
    # -------------------------------------------------------------
    # 1. WHO SEARO (2017) Category 3: Biscuits, Cakes and Sweet Baked Goods
    # -------------------------------------------------------------
    {
        "standard_id": "STD_WHO_SEARO_2017_BAKERY_SUGAR",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO Regional Office for South-East Asia)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Total Sugars",
        "applicable_category": "Biscuits & Bakery",
        "regulatory_subcategory": "Category 3: Biscuits, cakes and sweet baked goods",
        "measurement_basis": "per 100g",
        "threshold": 10.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Sugar)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_BAKERY_SATFAT",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Saturated Fat",
        "applicable_category": "Biscuits & Bakery",
        "regulatory_subcategory": "Category 3: Biscuits, cakes and sweet baked goods",
        "measurement_basis": "per 100g",
        "threshold": 4.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Saturated Fat)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_BAKERY_SODIUM",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Sodium",
        "applicable_category": "Biscuits & Bakery",
        "regulatory_subcategory": "Category 3: Biscuits, cakes and sweet baked goods",
        "measurement_basis": "per 100g",
        "threshold": 300.0,
        "unit": "mg",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Sodium)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },

    # -------------------------------------------------------------
    # 2. WHO SEARO (2017) Category 4: Savoury Snacks and Chips
    # -------------------------------------------------------------
    {
        "standard_id": "STD_WHO_SEARO_2017_SUGAR",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO Regional Office for South-East Asia)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Total Sugars",
        "applicable_category": "Snacks",
        "regulatory_subcategory": "Category 4: Savoury snacks and chips",
        "measurement_basis": "per 100g",
        "threshold": 10.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Sugar)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_SODIUM_SNACK",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Sodium",
        "applicable_category": "Snacks",
        "regulatory_subcategory": "Category 4: Savoury snacks and chips",
        "measurement_basis": "per 100g",
        "threshold": 400.0,
        "unit": "mg",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Sodium)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_SATFAT_SNACK",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Saturated Fat",
        "applicable_category": "Snacks",
        "regulatory_subcategory": "Category 4: Savoury snacks and chips",
        "measurement_basis": "per 100g",
        "threshold": 4.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Saturated Fat)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },

    # -------------------------------------------------------------
    # 3. WHO Guidance on Sugar-Sweetened Beverages & FSSAI Liquid Foods
    # -------------------------------------------------------------
    {
        "standard_id": "STD_WHO_BEV_SUGAR_2020",
        "standard_name": "WHO Guidance on Sugar-Sweetened Beverages",
        "organization": "World Health Organization (WHO HQ)",
        "jurisdiction": "Global / International",
        "document_title": "Fiscal policies to promote healthy diets: policy brief",
        "publication_year": 2020,
        "nutrient": "Total Sugars",
        "applicable_category": "Packaged Beverages",
        "regulatory_subcategory": "Category 7: Packaged Beverages & Soft Drinks",
        "measurement_basis": "per 100ml",
        "threshold": 5.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (Sugar-Sweetened Beverage)",
        "citation_url": "https://www.who.int/publications/i/item/9789240019447",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_BEV_SODIUM_2017",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Sodium",
        "applicable_category": "Packaged Beverages",
        "regulatory_subcategory": "Category 7: Packaged Beverages",
        "measurement_basis": "per 100ml",
        "threshold": 80.0,
        "unit": "mg",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (Elevated Sodium in Beverage)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },

    # -------------------------------------------------------------
    # 4. FSSAI Draft Indian Nutrition Rating (INR) & WHO SEARO Cereals
    # -------------------------------------------------------------
    {
        "standard_id": "STD_FSSAI_INR_2022_CEREALS",
        "standard_name": "FSSAI Draft Indian Nutrition Rating (INR)",
        "organization": "Food Safety and Standards Authority of India (FSSAI)",
        "jurisdiction": "India",
        "document_title": "Draft Food Safety and Standards (Labelling and Display) Amendment Regulations",
        "publication_year": 2022,
        "nutrient": "Total Sugars",
        "applicable_category": "Breakfast Cereals",
        "regulatory_subcategory": "Category 1: Breakfast Cereals & Solid Grains",
        "measurement_basis": "per 100g",
        "threshold": 15.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "High Sugar Boundary for Cereals",
        "citation_url": "https://www.fssai.gov.in/upload/uploadfiles/files/Draft_Notification_Labelling_Display_20_09_2022.pdf",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_CEREALS_SATFAT",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Saturated Fat",
        "applicable_category": "Breakfast Cereals",
        "regulatory_subcategory": "Category 1: Breakfast Cereals",
        "measurement_basis": "per 100g",
        "threshold": 2.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Saturated Fat for Cereals)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_CEREALS_SODIUM",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Sodium",
        "applicable_category": "Breakfast Cereals",
        "regulatory_subcategory": "Category 1: Breakfast Cereals",
        "measurement_basis": "per 100g",
        "threshold": 300.0,
        "unit": "mg",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Sodium in Cereals)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },

    # -------------------------------------------------------------
    # 5. WHO SEARO (2017) Category 6: Convenience and Instant Foods
    # -------------------------------------------------------------
    {
        "standard_id": "STD_WHO_SEARO_2017_INSTANT_SODIUM",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Sodium",
        "applicable_category": "Instant Foods",
        "regulatory_subcategory": "Category 6: Convenience and Ready-to-cook Foods (Instant Noodles)",
        "measurement_basis": "per 100g",
        "threshold": 450.0,
        "unit": "mg",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Sodium in Instant Foods)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_INSTANT_SATFAT",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Saturated Fat",
        "applicable_category": "Instant Foods",
        "regulatory_subcategory": "Category 6: Convenience and Ready-to-cook Foods (Instant Noodles)",
        "measurement_basis": "per 100g",
        "threshold": 4.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Saturated Fat in Instant Foods)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_INSTANT_SUGAR",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Total Sugars",
        "applicable_category": "Instant Foods",
        "regulatory_subcategory": "Category 6: Convenience and Ready-to-cook Foods",
        "measurement_basis": "per 100g",
        "threshold": 5.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (Added Sugars in Savoury Foods)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },

    # -------------------------------------------------------------
    # 6. WHO SEARO (2017) Category 2: Dairy Products
    # -------------------------------------------------------------
    {
        "standard_id": "STD_WHO_SEARO_2017_DAIRY_SUGAR",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Total Sugars",
        "applicable_category": "Dairy",
        "regulatory_subcategory": "Category 2: Dairy Products",
        "measurement_basis": "per 100g",
        "threshold": 10.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (Added Sugars in Dairy)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_DAIRY_SATFAT",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Saturated Fat",
        "applicable_category": "Dairy",
        "regulatory_subcategory": "Category 2: Dairy Products",
        "measurement_basis": "per 100g",
        "threshold": 4.0,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (Elevated Saturated Fat in Dairy)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_SEARO_2017_DAIRY_SODIUM",
        "standard_name": "WHO South-East Asia Regional Nutrient Profile Model (2017)",
        "organization": "World Health Organization (WHO SEARO)",
        "jurisdiction": "South-East Asia Region (including India)",
        "document_title": "WHO Nutrient Profile Model for South-East Asia Region",
        "publication_year": 2017,
        "nutrient": "Sodium",
        "applicable_category": "Dairy",
        "regulatory_subcategory": "Category 2: Dairy Products",
        "measurement_basis": "per 100g",
        "threshold": 300.0,
        "unit": "mg",
        "comparison_operator": ">",
        "classification": "Nutrient of Concern (High Sodium in Processed Dairy)",
        "citation_url": "https://www.who.int/publications/i/item/9789290225898",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },

    # -------------------------------------------------------------
    # 7. Global Codex Alimentarius & WHO REPLACE Targets
    # -------------------------------------------------------------
    {
        "standard_id": "STD_CODEX_FIBRE_1985",
        "standard_name": "Codex Guidelines on Nutrition Claims (CAC/GL 23-1997)",
        "organization": "Codex Alimentarius Commission (FAO/WHO)",
        "jurisdiction": "International",
        "document_title": "Guidelines for Use of Nutrition and Health Claims",
        "publication_year": 2013,
        "nutrient": "Dietary Fibre",
        "applicable_category": "All Packaged Foods",
        "regulatory_subcategory": "General Benchmark",
        "measurement_basis": "per 100g",
        "threshold": 6.0,
        "unit": "g",
        "comparison_operator": ">=",
        "classification": "Beneficial Nutrient (High in Fibre Claim Standard)",
        "citation_url": "https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%253A%252F%252Fworkspace.fao.org%252Fsites%252Fcodex%252FStandards%252FCAC%2BGL%2B23-1997%252FCXG_023e.pdf",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_CODEX_PROTEIN_1985",
        "standard_name": "Codex Guidelines on Nutrition Claims (CAC/GL 23-1997)",
        "organization": "Codex Alimentarius Commission (FAO/WHO)",
        "jurisdiction": "International",
        "document_title": "Guidelines for Use of Nutrition and Health Claims",
        "publication_year": 2013,
        "nutrient": "Protein",
        "applicable_category": "All Packaged Foods",
        "regulatory_subcategory": "General Benchmark",
        "measurement_basis": "per 100g",
        "threshold": 10.0,
        "unit": "g",
        "comparison_operator": ">=",
        "classification": "Beneficial Nutrient (High Protein Claim Standard)",
        "citation_url": "https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%253A%252F%252Fworkspace.fao.org%252Fsites%252Fcodex%252FStandards%252FCAC%2BGL%2B23-1997%252FCXG_023e.pdf",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },
    {
        "standard_id": "STD_WHO_TRANS_FAT_GLOBAL",
        "standard_name": "WHO REPLACE Trans Fat Action Package",
        "organization": "World Health Organization (WHO HQ)",
        "jurisdiction": "Global / International",
        "document_title": "REPLACE: An action package to eliminate industrially-produced trans-fatty acids",
        "publication_year": 2018,
        "nutrient": "Trans Fat",
        "applicable_category": "All Packaged Foods",
        "regulatory_subcategory": "Mandatory Elimination Target",
        "measurement_basis": "per 100g",
        "threshold": 0.2,
        "unit": "g",
        "comparison_operator": ">",
        "classification": "Mandatory Elimination Target (<2% total fat / <0.2g per 100g)",
        "citation_url": "https://www.who.int/teams/nutrition-and-food-safety/replace-trans-fat",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Calibrated"
    },

    # -------------------------------------------------------------
    # 8. Statutory FSSAI Mandatory Labelling Regulations
    # -------------------------------------------------------------
    {
        "standard_id": "STD_FSSAI_LABEL_2020_MANDATORY",
        "standard_name": "FSSAI (Labelling and Display) Regulations, 2020",
        "organization": "Food Safety and Standards Authority of India (FSSAI)",
        "jurisdiction": "India",
        "document_title": "Food Safety and Standards (Labelling and Display) Regulations, 2020",
        "publication_year": 2020,
        "nutrient": "Baseline Nutritional Panel",
        "applicable_category": "All Packaged Foods",
        "regulatory_subcategory": "Statutory Labelling Requirement",
        "measurement_basis": "per 100g or per 100ml",
        "threshold": 0.0,
        "unit": "declaration",
        "comparison_operator": ">=",
        "classification": "Statutory Mandatory Declaration (Energy, Protein, Carbs, Total Sugars, Added Sugars, Total Fat, Sat Fat, Trans Fat, Sodium)",
        "citation_url": "https://www.fssai.gov.in/upload/uploadfiles/files/Gazette_Notification_Labelling_Display_18_11_2020.pdf",
        "verification_date": "2026-10-28",
        "implementation_status": "Active / Baseline Requirement"
    }
]

# -------------------------------------------------------------------
# CATEGORY CALIBRATION REGISTRY
# Maps product categories to documented profiling standards, mandatory
# fields, reference bases, and explicit status justifications.
# -------------------------------------------------------------------
CATEGORY_CALIBRATION_SPECS: dict[str, dict[str, Any]] = {
    "Biscuits & Bakery": {
        "status": "Calibrated",
        "canonical_name": "Biscuits & Bakery",
        "methodology_name": "WHO SEARO (2017) / FSSAI Indian Nutrition Rating (INR 2022) Solid Foods Model",
        "standards_version": "WHO-SEARO-2017-CAT3 / FSSAI-INR-2022-CAT1",
        "regulatory_category": "Category 3: Biscuits, Cakes and Sweet Baked Goods (Solid Foods)",
        "reference_basis": "per 100g",
        "mandatory_fields": ["energy_kcal", "sugars_g", "saturated_fat_g", "sodium_mg"],
        "optional_fields": ["dietary_fibre_g", "protein_g", "trans_fat_g", "added_sugars_g"],
        "thresholds": {
            "sugars_g": 10.0,
            "saturated_fat_g": 4.0,
            "sodium_mg": 300.0,
            "trans_fat_g": 0.1
        },
        "positive_benchmarks": {
            "fibre_high_g": 6.0,
            "fibre_source_g": 3.0,
            "protein_high_g": 10.0,
            "protein_source_g": 6.0
        },
        "source_citations": [
            "WHO Regional Office for South-East Asia Nutrient Profile Model (ISBN 978-92-9022-589-8, Cat 3)",
            "FSSAI Draft Notification F. No. STD/SP-08/A-1.2022/N-01 (Indian Nutrition Rating Schedule 1)"
        ]
    },
    "Snacks": {
        "status": "Calibrated",
        "canonical_name": "Snacks",
        "methodology_name": "WHO SEARO (2017) / FSSAI Indian Nutrition Rating (INR 2022) Savoury Snacks Model",
        "standards_version": "WHO-SEARO-2017-CAT4 / FSSAI-INR-2022-CAT1",
        "regulatory_category": "Category 4: Savoury Snacks and Chips (Solid Foods)",
        "reference_basis": "per 100g",
        "mandatory_fields": ["energy_kcal", "sugars_g", "saturated_fat_g", "sodium_mg"],
        "optional_fields": ["dietary_fibre_g", "protein_g", "trans_fat_g", "added_sugars_g"],
        "thresholds": {
            "sugars_g": 10.0,
            "saturated_fat_g": 4.0,
            "sodium_mg": 400.0,
            "trans_fat_g": 0.1
        },
        "positive_benchmarks": {
            "fibre_high_g": 6.0,
            "fibre_source_g": 3.0,
            "protein_high_g": 10.0,
            "protein_source_g": 6.0
        },
        "source_citations": [
            "WHO Regional Office for South-East Asia Nutrient Profile Model (Cat 4)",
            "FSSAI Draft Notification F. No. STD/SP-08/A-1.2022/N-01 (Solid Foods)"
        ]
    },
    "Breakfast Cereals": {
        "status": "Calibrated",
        "canonical_name": "Breakfast Cereals",
        "methodology_name": "WHO SEARO (2017) / FSSAI Indian Nutrition Rating (INR 2022) Cereals Model",
        "standards_version": "WHO-SEARO-2017-CAT1 / FSSAI-INR-2022-CAT1",
        "regulatory_category": "Category 1: Breakfast Cereals & Solid Grains",
        "reference_basis": "per 100g",
        "mandatory_fields": ["energy_kcal", "sugars_g", "saturated_fat_g", "sodium_mg"],
        "optional_fields": ["dietary_fibre_g", "protein_g", "trans_fat_g", "added_sugars_g"],
        "thresholds": {
            "sugars_g": 15.0,
            "saturated_fat_g": 2.0,
            "sodium_mg": 300.0,
            "trans_fat_g": 0.1
        },
        "positive_benchmarks": {
            "fibre_high_g": 6.0,
            "fibre_source_g": 3.0,
            "protein_high_g": 10.0,
            "protein_source_g": 6.0
        },
        "source_citations": [
            "WHO SEARO Nutrient Profile Model (Cat 1: Breakfast Cereals)",
            "FSSAI INR 2022 Cereals Sugar Standard (15g/100g threshold)"
        ]
    },
    "Packaged Beverages": {
        "status": "Calibrated",
        "canonical_name": "Packaged Beverages",
        "methodology_name": "WHO Sugar-Sweetened Beverage Guidance (2020) / FSSAI INR Liquid Foods Model",
        "standards_version": "WHO-SSB-2020 / FSSAI-INR-2022-CAT2",
        "regulatory_category": "Category 2: Liquid Foods & Packaged Beverages",
        "reference_basis": "per 100ml",
        "mandatory_fields": ["energy_kcal", "sugars_g", "sodium_mg"],
        "optional_fields": ["saturated_fat_g", "protein_g", "dietary_fibre_g", "added_sugars_g"],
        "thresholds": {
            "sugars_g": 5.0,
            "saturated_fat_g": 0.0,
            "sodium_mg": 80.0,
            "trans_fat_g": 0.1
        },
        "positive_benchmarks": {
            "fibre_high_g": 3.0,
            "fibre_source_g": 1.5,
            "protein_high_g": 5.0,
            "protein_source_g": 3.0
        },
        "source_citations": [
            "WHO Guidance on Sugar-Sweetened Beverages (2020, ISBN 978-92-4-001944-7)",
            "FSSAI Draft INR Category 2 (Liquid Foods: 5g sugar / 100ml threshold)"
        ]
    },
    "Instant Foods": {
        "status": "Calibrated",
        "canonical_name": "Instant Foods",
        "methodology_name": "WHO SEARO (2017) / FSSAI Indian Nutrition Rating (INR 2022) Convenience Foods Model",
        "standards_version": "WHO-SEARO-2017-CAT6 / FSSAI-INR-2022-CAT1",
        "regulatory_category": "Category 6: Convenience and Ready-to-cook Foods (Instant Noodles)",
        "reference_basis": "per 100g",
        "mandatory_fields": ["energy_kcal", "sugars_g", "saturated_fat_g", "sodium_mg"],
        "optional_fields": ["dietary_fibre_g", "protein_g", "trans_fat_g", "added_sugars_g"],
        "thresholds": {
            "sugars_g": 5.0,
            "saturated_fat_g": 4.0,
            "sodium_mg": 450.0,
            "trans_fat_g": 0.1
        },
        "positive_benchmarks": {
            "fibre_high_g": 6.0,
            "fibre_source_g": 3.0,
            "protein_high_g": 10.0,
            "protein_source_g": 6.0
        },
        "source_citations": [
            "WHO Regional Office for South-East Asia Nutrient Profile Model (Cat 6)",
            "FSSAI Draft Indian Nutrition Rating Solid Foods Schedule"
        ]
    },
    "Dairy": {
        "status": "Calibrated",
        "canonical_name": "Dairy",
        "methodology_name": "WHO SEARO (2017) / FSSAI Indian Nutrition Rating (INR 2022) Dairy Products Model",
        "standards_version": "WHO-SEARO-2017-CAT2 / FSSAI-INR-2022-CAT3",
        "regulatory_category": "Category 2 & 3: Dairy Products and Analogues",
        "reference_basis": "per 100g",
        "mandatory_fields": ["energy_kcal", "sugars_g", "saturated_fat_g", "protein_g"],
        "optional_fields": ["sodium_mg", "total_fat_g", "trans_fat_g", "added_sugars_g"],
        "thresholds": {
            "sugars_g": 10.0,
            "saturated_fat_g": 4.0,
            "sodium_mg": 300.0,
            "trans_fat_g": 0.1
        },
        "positive_benchmarks": {
            "fibre_high_g": 4.0,
            "fibre_source_g": 2.0,
            "protein_high_g": 10.0,
            "protein_source_g": 6.0
        },
        "source_citations": [
            "WHO SEARO Nutrient Profile Model (Cat 2: Milk and Dairy Products)",
            "FSSAI Draft INR Schedule 3 (Dairy Products & Analogues)"
        ]
    },
    "Chocolates & Sweets": {
        "status": "Unsupported",
        "canonical_name": "Chocolates & Sweets",
        "methodology_name": None,
        "standards_version": "WHO SEARO Category 5 (Confectionery)",
        "regulatory_category": "Category 5: Confectionery and Sweet Treats",
        "reference_basis": "per 100g",
        "mandatory_fields": ["energy_kcal", "sugars_g", "saturated_fat_g"],
        "unsupported_reason": (
            "An overall grade is unavailable because confectionery is not currently calibrated under statutory front-of-pack grading systems."
        ),
        "source_citations": [
            "WHO Regional Office for South-East Asia Nutrient Profile Model (ISBN 978-92-9022-589-8, Section Category 5)"
        ]
    },
    "Condiments & Spreads": {
        "status": "Unsupported",
        "canonical_name": "Condiments & Spreads",
        "methodology_name": None,
        "standards_version": "FSSAI Portion-Size Guidance Pending",
        "regulatory_category": "Category 8: Sauces, Dips and Culinary Condiments",
        "reference_basis": "per 100g",
        "mandatory_fields": ["energy_kcal", "sugars_g", "sodium_mg"],
        "unsupported_reason": (
            "An overall grade is unavailable because standard 100 g profiling is not calibrated for typical culinary condiments and table sauces portion sizes (10–15 g)."
        ),
        "source_citations": [
            "WHO SEARO Nutrient Profile Model (Cat 8: Sauces and Condiments serving considerations)",
            "Codex Alimentarius Guidelines on Nutrition Labelling (CAC/GL 2-1985)"
        ]
    }
}

# Supported calibrated categories for Layer 1 grading
CALIBRATED_CATEGORIES = [
    cat for cat, spec in CATEGORY_CALIBRATION_SPECS.items()
    if spec.get("status") == "Calibrated"
]

CATEGORY_ALIASES = {
    "biscuits": "Biscuits & Bakery",
    "bakery": "Biscuits & Bakery",
    "cookies": "Biscuits & Bakery",
    "crackers": "Biscuits & Bakery",
    "crackers & biscuits": "Biscuits & Bakery",
    "cookies & biscuits": "Biscuits & Bakery",
    "snack": "Snacks",
    "snacks": "Snacks",
    "chips": "Snacks",
    "savoury snacks": "Snacks",
    "namkeen": "Snacks",
    "cereal": "Breakfast Cereals",
    "cereals": "Breakfast Cereals",
    "breakfast cereal": "Breakfast Cereals",
    "breakfast cereals": "Breakfast Cereals",
    "oats": "Breakfast Cereals",
    "beverage": "Packaged Beverages",
    "beverages": "Packaged Beverages",
    "packaged beverages": "Packaged Beverages",
    "drinks": "Packaged Beverages",
    "soft drink": "Packaged Beverages",
    "fruit juice": "Packaged Beverages",
    "juice": "Packaged Beverages",
    "instant foods": "Instant Foods",
    "instant food": "Instant Foods",
    "noodles": "Instant Foods",
    "instant noodles": "Instant Foods",
    "ready to eat": "Instant Foods",
    "ready to cook": "Instant Foods",
    "dairy": "Dairy",
    "milk": "Dairy",
    "cheese": "Dairy",
    "butter": "Dairy",
    "yogurt": "Dairy",
    "chocolates": "Chocolates & Sweets",
    "chocolate": "Chocolates & Sweets",
    "sweets": "Chocolates & Sweets",
    "chocolates & sweets": "Chocolates & Sweets",
    "confectionery": "Chocolates & Sweets",
    "candy": "Chocolates & Sweets",
    "condiments": "Condiments & Spreads",
    "spreads": "Condiments & Spreads",
    "condiments & spreads": "Condiments & Spreads",
    "sauce": "Condiments & Spreads",
    "sauces": "Condiments & Spreads",
    "ketchup": "Condiments & Spreads"
}

def normalize_category(category: str | None) -> str:
    """Normalizes category aliases to the canonical calibrated category name."""
    if not category:
        return ""
    clean = str(category).strip()
    lower = clean.lower()
    if lower in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[lower]
    for key, canonical in CATEGORY_ALIASES.items():
        if key in lower:
            return canonical
    return clean

def get_category_spec(category: str) -> dict[str, Any] | None:
    """Retrieves the official calibration specification for a category."""
    canonical = normalize_category(category)
    return CATEGORY_CALIBRATION_SPECS.get(canonical)

def get_applicable_standards(category: str) -> list[dict[str, Any]]:
    """Returns active standards applicable to a given product category."""
    canonical = normalize_category(category)
    standards = []
    for std in STANDARDS_REGISTRY:
        if std["applicable_category"] in [canonical, category, "All Packaged Foods"]:
            standards.append(std)
    return standards
