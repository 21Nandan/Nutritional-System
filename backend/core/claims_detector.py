"""
EATGOOD — Front-of-Pack Marketing Claim Auditor & Taxonomy Classifier
Evaluates marketing claims declared on packaged food labels against verified nutritional facts,
ingredient declarations, and documented statutory reference criteria:
- FSSAI Food Safety and Standards (Advertising and Claims) Regulations, 2018 (as amended)
- Codex Alimentarius Guidelines for Use of Nutrition and Health Claims (CAC/GL 23-1997)

Principles:
1. Separation of Concerns: Classification (what claim is made) is decoupled from compliance evaluation (whether evidence supports it).
2. Multi-label Taxonomy: Supports multiple simultaneous claim types (e.g. Comparative + Sugar-related, or Sensory + Nutrient-content).
3. Rule Precedence: Specific comparative, nutrient, health, and ingredient claims take precedence over broad sensory terms.
4. Comparative Substantiation: Comparative and superlative claims ("highest protein", "30% less sugar") require comparator identity and baseline proof. Single-product panels cannot substantiate category superiority.
5. Statutory Integrity: Official criteria (FSSAI/Codex) are strictly distinguished from non-statutory sensory descriptions.
"""

import re
from typing import Any

import pandas as pd

# ----------------- Statutory Benchmarks & References -----------------

FSSAI_REF_NUTRIENT = "FSSAI Food Safety and Standards (Advertising and Claims) Regulations, 2018 (Regulation 5 & Schedule I/II)"
FSSAI_REF_COMPARATIVE = "FSSAI Food Safety and Standards (Advertising and Claims) Regulations, 2018 (Regulation 6 & Schedule IV)"
FSSAI_REF_SUPERLATIVE = "FSSAI Food Safety and Standards (Advertising and Claims) Regulations, 2018 (Regulation 4(7) & Misleading Claims Guidance)"
FSSAI_REF_NON_ADDITION = "FSSAI Food Safety and Standards (Advertising and Claims) Regulations, 2018 (Regulation 6(1) & Schedule IV)"
FSSAI_REF_HEALTH = "FSSAI Food Safety and Standards (Advertising and Claims) Regulations, 2018 (Regulation 7 & Schedule III/V)"
CODEX_REF_CLAIMS = "Codex Alimentarius Guidelines for Use of Nutrition and Health Claims (CAC/GL 23-1997)"

HIDDEN_SUGAR_TERMS = [
    "liquid glucose", "invert sugar", "maltodextrin", "corn syrup",
    "high fructose corn syrup", "dextrose", "malt extract", "caramel syrup",
    "honey", "jaggery", "molasses", "fruit juice concentrate", "sucrose", "glucose syrup"
]

GLUTEN_GRAIN_TERMS = [
    "wheat", "barley", "rye", "oats", "maida", "atta", "semolina", "sooji", "malt", "spelt"
]

COMMON_CHEMICAL_PRESERVATIVES = [
    "sodium benzoate", "potassium sorbate", "sorbic acid", "benzoic acid",
    "sodium metabisulphite", "potassium metabisulphite", "sulfur dioxide",
    "ins 211", "ins 202", "ins 200", "ins 224", "ins 223", "ins 220"
]

# ----------------- Lexical Token Patterns -----------------

COMPARATIVE_SUPERLATIVE_PATTERNS = [
    r"\bhighest\b", r"\blowest\b", r"\bmost\b", r"\bleast\b",
    r"\bmaximum\b", r"\bminimum\b", r"\bbest\b", r"\bunmatched\b"
]

COMPARATIVE_RELATIVE_PATTERNS = [
    r"\bmore\b", r"\bless\b", r"\breduced\b", r"\blower\b", r"\bhigher\b",
    r"\bincreased\b", r"\bextra\b", r"\badded\s+(?:protein|vitamins?|calcium|fibre|fiber|minerals?)\b", r"\bboosted\b",
    r"\b\d+%\s*(?:more|less|reduced|lower|higher|extra)\b",
    r"\b(?:more|less|reduced|lower|higher)\s*than\b",
    r"\b\d+x\s*(?:more|higher|protein|fibre)\b"
]

NUTRIENT_KEYWORDS = {
    "protein": [r"\bproteins?\b"],
    "sugars": [r"\bsugars?\b", r"\bsweet\b"],
    "total_fat": [r"\bfats?\b", r"\blipid\b"],
    "saturated_fat": [r"\bsaturated\s*fats?\b", r"\bsat\s*fats?\b"],
    "trans_fat": [r"\btrans\s*fats?\b"],
    "dietary_fibre": [r"\bfibres?\b", r"\bfibers?\b", r"\broughage\b"],
    "sodium": [r"\bsodium\b", r"\bsalt\b"],
    "energy": [r"\bcalories?\b", r"\bkcal\b", r"\benergy\b"],
    "calcium": [r"\bcalcium\b"],
    "iron": [r"\biron\b"],
    "vitamins": [r"\bvitamins?\b", r"\bvitamin\s*[a-e]\b"]
}

LEVEL_CONTENT_PATTERNS = [
    r"\bhigh\b", r"\brich\s*in\b", r"\bsource\s*of\b", r"\bgood\s*source\s*of\b",
    r"\bexcellent\s*source\s*of\b", r"\bloaded\s*with\b", r"\bpacked\s*with\b",
    r"\blow\b", r"\bzero\b", r"\bfree\b", r"\b0%\b"
]

HEALTH_CLAIM_PATTERNS = [
    r"\bimmunity\b", r"\bimmune\b", r"\bheart\s*health\b", r"\bcardiovascular\b",
    r"\bdigestion\b", r"\bgut\s*health\b", r"\bweight\s*(?:loss|management)\b",
    r"\bactive\s*lifestyle\b", r"\benergy\s*boost\b", r"\bwellness\b",
    r"\bdetox\b", r"\bdiabetic\s*friendly\b", r"\bblood\s*sugar\b"
]

FUNCTION_CLAIM_PATTERNS = [
    r"\bbuilds?\s*(?:muscle|tissue|bone)\b",
    r"\bhelps?\s*(?:build|grow|repair|maintain|absorb)\b",
    r"\bsupports?\s*(?:growth|muscle|recovery|development)\b",
    r"\baids?\s*in\b", r"\bcontributes?\s*to\b"
]

FREE_FROM_PATTERNS = [
    r"\bgluten[-\s]*free\b", r"\bpreservative[-\s]*free\b", r"\bno\s*preservatives?\b",
    r"\bdairy[-\s]*free\b", r"\blactose[-\s]*free\b", r"\btrans[-\s]*fat[-\s]*free\b",
    r"\bzero\s*trans\s*fat\b", r"\bno\s*trans\s*fats?\b", r"\bno\s*added\s*msg\b",
    r"\bmsg[-\s]*free\b", r"\bno\s*artificial\s*(?:colours?|colors?|flavours?|flavors?)\b"
]

INGREDIENT_COMPOSITION_PATTERNS = [
    r"\bmade\s*with\b", r"\bcontains\s*real\b", r"\b100%\s*real\b",
    r"\b100%\s*pure\b", r"\bwhole\s*grains?\b", r"\breal\s*fruit\b",
    r"\breal\s*(?:almonds?|nuts?|veggies?|vegetables?|milk)\b",
    r"\b100%\s*juice\b"
]

ORGANIC_NATURAL_PATTERNS = [
    r"\b(?:100%\s*)?organic\b", r"\bcertified\s*organic\b",
    r"\b(?:100%\s*)?natural\b", r"\ball\s*natural\b", r"\bpure\s*natural\b"
]

SENSORY_DESCRIPTIVE_PATTERNS = [
    r"\bcrispy\b", r"\bcrunchy\b", r"\bcreamy\b", r"\bdelicious\b",
    r"\btasty\b", r"\brich\s*flavo(?:u)?r\b", r"\bmouth[-\s]*watering\b",
    r"\bauthentic\s*taste\b", r"\btraditional\s*recipe\b", r"\bhomestyle\b",
    r"\bbaked\s*to\s*perfection\b", r"\byummy\b", r"\bsavou?ry\b", r"\bjuicy\b"
]

# ----------------- Normalization & Classification -----------------

def normalize_claim_text(claim: str) -> str:
    """Normalizes whitespace and standardizes punctuation while preserving numbers and comparison tokens."""
    if not claim or pd.isna(claim):
        return ""
    text = str(claim).strip()
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip('"\' ')
    return text

def detect_nutrients_in_claim(normalized_claim: str) -> list[str]:
    """Identifies which nutritional dimensions are referenced in the claim text."""
    lower = normalized_claim.lower()
    matched_nutrients = []
    for nutrient, patterns in NUTRIENT_KEYWORDS.items():
        if any(re.search(pat, lower) for pat in patterns):
            matched_nutrients.append(nutrient)
    return matched_nutrients

def classify_claim_taxonomy(normalized_claim: str) -> dict[str, Any]:
    """
    Classifies a claim into one or more categories based on strict rule precedence.
    Returns detected categories, primary category, matching keywords, and classification rationale.
    """
    lower = normalized_claim.lower()
    detected_types = []
    detected_nutrients = detect_nutrients_in_claim(normalized_claim)
    comparative_terms = []
    comparison_type = None

    # 1. Check Comparative Nutrition Claims (superlatives & relative differences)
    is_superlative = any(re.search(pat, lower) for pat in COMPARATIVE_SUPERLATIVE_PATTERNS)
    is_relative = any(re.search(pat, lower) for pat in COMPARATIVE_RELATIVE_PATTERNS)

    # Exclude non-addition claims ("no added sugar", "zero added sugar") from relative comparative category
    if bool(re.search(r"\b(?:no|without|zero)\s*added\b", lower)):
        is_relative = False

    # Must involve a nutrient or nutritional dimension (or comparison context like 'less calorie', 'more protein')
    if (is_superlative or is_relative) and (detected_nutrients or "calorie" in lower or "nutrition" in lower):
        detected_types.append("Comparative Nutrition Claim")
        comparison_type = "superlative" if is_superlative else "relative"
        for pat in (COMPARATIVE_SUPERLATIVE_PATTERNS + COMPARATIVE_RELATIVE_PATTERNS):
            matches = re.findall(pat, lower)
            if matches:
                comparative_terms.extend(matches)

    # 2. Check Sugar-Related Claims
    is_sugar_free = bool(re.search(r"\b(?:zero|0%|no|free)\s*sugars?\b|\bsugar[-\s]*free\b", lower))
    is_no_added_sugar = bool(re.search(r"\bno\s*added\s*sugars?\b|\bwithout\s*added\s*sugars?\b|\bzero\s*added\s*sugar\b", lower))
    is_reduced_sugar = bool(re.search(r"\b(?:reduced|less|lower)\s*sugars?\b|\b\d+%\s*less\s*sugars?\b", lower))
    is_low_sugar = bool(re.search(r"\blow\s*sugars?\b", lower))

    if is_sugar_free or is_no_added_sugar or is_reduced_sugar or is_low_sugar:
        detected_types.append("Sugar-Related Claim")
        if "sugars" not in detected_nutrients:
            detected_nutrients.append("sugars")

    # 3. Check Nutrient-Content Claims (absolute level declarations)
    has_level_marker = any(re.search(pat, lower) for pat in LEVEL_CONTENT_PATTERNS)
    if has_level_marker and detected_nutrients and "Comparative Nutrition Claim" not in detected_types:
        detected_types.append("Nutrient-Content Claim")
    elif has_level_marker and detected_nutrients and "Comparative Nutrition Claim" in detected_types:
        # Also tag as Nutrient-Content Claim if absolute descriptor is present alongside comparative
        if any(re.search(r"\b(?:high|rich|source|low|zero)\b", lower) for _ in [1]):
            detected_types.append("Nutrient-Content Claim")

    # 4. Check Free-From Claims
    if any(re.search(pat, lower) for pat in FREE_FROM_PATTERNS):
        detected_types.append("Free-From Claim")

    # 5. Check Nutrient-Function Claims (physiological action)
    has_function = any(re.search(pat, lower) for pat in FUNCTION_CLAIM_PATTERNS)
    if has_function and (detected_nutrients or any(w in lower for w in ["muscle", "bone", "growth", "tissue", "recovery", "development", "repair"])):
        detected_types.append("Nutrient-Function Claim")

    # 6. Check Health-Related Claims (body systems, disease risk, wellness)
    if any(re.search(pat, lower) for pat in HEALTH_CLAIM_PATTERNS):
        if "Nutrient-Function Claim" not in detected_types:
            detected_types.append("Health-Related Claim")

    # 7. Check Ingredient and Composition Claims
    if any(re.search(pat, lower) for pat in INGREDIENT_COMPOSITION_PATTERNS):
        detected_types.append("Ingredient & Composition Claim")

    # 8. Check Organic and Natural Claims
    if any(re.search(pat, lower) for pat in ORGANIC_NATURAL_PATTERNS):
        detected_types.append("Organic & Natural Claim")

    # 9. Check Descriptive or Sensory Claims
    if any(re.search(pat, lower) for pat in SENSORY_DESCRIPTIVE_PATTERNS):
        detected_types.append("Descriptive / Sensory Claim")

    # 10. Fallback: Unclassified or Ambiguous Claim
    if not detected_types:
        detected_types.append("Unclassified or Ambiguous Claim")

    # Determine Primary Claim Type based on regulatory gravity
    priority_order = [
        "Comparative Nutrition Claim",
        "Sugar-Related Claim",
        "Nutrient-Content Claim",
        "Free-From Claim",
        "Nutrient-Function Claim",
        "Health-Related Claim",
        "Ingredient & Composition Claim",
        "Organic & Natural Claim",
        "Descriptive / Sensory Claim",
        "Unclassified or Ambiguous Claim"
    ]
    primary_type = next((t for t in priority_order if t in detected_types), detected_types[0])

    # Build classification rationale
    rationale_parts = []
    if "Comparative Nutrition Claim" in detected_types:
        comp_str = f"'{comparison_type}' comparison" if comparison_type else "comparative term"
        nutr_str = f" referencing {', '.join(detected_nutrients)}" if detected_nutrients else ""
        rationale_parts.append(f"Invokes {comp_str}{nutr_str} subject to statutory comparative substantiation rules.")
    if "Sugar-Related Claim" in detected_types:
        rationale_parts.append("Specific sugar content or non-addition claim governed by statutory sugar thresholds.")
    if "Nutrient-Content Claim" in detected_types:
        rationale_parts.append(f"Declares presence or level of {', '.join(detected_nutrients) if detected_nutrients else 'a nutrient'} governed by statutory schedule limits.")
    if "Free-From Claim" in detected_types:
        rationale_parts.append("Declares absence of specific ingredient, allergen, or synthetic component.")
    if "Health-Related Claim" in detected_types or "Nutrient-Function Claim" in detected_types:
        rationale_parts.append("States or implies a relationship between food/nutrient and biological function or health status.")
    if "Ingredient & Composition Claim" in detected_types:
        rationale_parts.append("Highlights prominent ingredients or composition proportions.")
    if "Organic & Natural Claim" in detected_types:
        rationale_parts.append("Agricultural or natural origin claim subject to certification guidelines.")
    if "Descriptive / Sensory Claim" in detected_types:
        rationale_parts.append("Subjective sensory, texture, or culinary description outside quantitative nutrition regulation scope.")
    if "Unclassified or Ambiguous Claim" in detected_types:
        rationale_parts.append("Does not match standard statutory nutrient, comparative, health, or sensory claim categories.")

    return {
        "detected_claim_types": detected_types,
        "primary_claim_type": primary_type,
        "detected_nutrients": detected_nutrients,
        "comparative_terms": list(set(comparative_terms)),
        "comparison_type": comparison_type,
        "classification_rationale": " ".join(rationale_parts)
    }

# ----------------- Empirical Compliance Evaluation -----------------

def evaluate_single_claim(claim_raw: str, product_data: dict) -> dict[str, Any]:
    """
    Performs decoupled 2-stage auditing:
    Stage 1: Taxonomic Classification.
    Stage 2: Empirical Compliance Assessment against available product nutrition declarations & ingredients.
    """
    normalized = normalize_claim_text(claim_raw)
    taxonomy = classify_claim_taxonomy(normalized)

    primary_type = taxonomy["primary_claim_type"]
    detected_types = taxonomy["detected_claim_types"]
    nutrients = taxonomy["detected_nutrients"]
    primary_nutrient = nutrients[0] if nutrients else None

    ingredients_text = str(product_data.get("ingredients", "")).lower()

    # Default result container
    evidence_required = ""
    evidence_available = ""
    missing_info = []
    compliance_status = "Insufficient evidence to assess compliance"
    regulatory_source = ""
    confidence = "Medium"
    explanation = ""

    # Check comparison basis details if comparative
    comparison_details = None
    if "Comparative Nutrition Claim" in detected_types:
        # Check if comparator is mentioned (e.g. 'than our regular', 'vs standard')
        comparator_match = re.search(r"than\s+([^,;.]+)", normalized, re.IGNORECASE)
        claimed_diff_match = re.search(r"(\d+%\s*(?:more|less|reduced|lower|higher|extra)|\d+x)", normalized, re.IGNORECASE)
        comparison_details = {
            "comparison_type": taxonomy.get("comparison_type") or "relative",
            "claimed_nutrient": primary_nutrient,
            "comparator": comparator_match.group(1).strip() if comparator_match else None,
            "claimed_difference": claimed_diff_match.group(1).strip() if claimed_diff_match else None
        }

    # --- Case 1: Comparative Nutrition Claim (e.g. 'highest protein', '30% less sugar') ---
    if "Comparative Nutrition Claim" in detected_types:
        comp_type = taxonomy.get("comparison_type")
        nutrient_name = primary_nutrient or "nutrient"
        regulatory_source = f"{FSSAI_REF_COMPARATIVE} / {CODEX_REF_CLAIMS}"

        if comp_type == "superlative":
            regulatory_source = f"{FSSAI_REF_SUPERLATIVE} / {CODEX_REF_CLAIMS}"
            evidence_required = (
                f"FSSAI Reg 4(7) & Codex CAC/GL 23-1997: Superlative claims ('highest', 'most') require "
                f"verifiable category-wide market comparative data demonstrating that the food possesses the highest "
                f"{nutrient_name} level among all peer products in the identical category."
            )
            # Check what is in the current product record
            current_val = product_data.get(f"{nutrient_name}_g") if nutrient_name in ["protein", "sugars", "total_fat", "saturated_fat", "trans_fat", "dietary_fibre"] else product_data.get(nutrient_name)
            if current_val is not None and not pd.isna(current_val):
                evidence_available = f"Product declares {current_val}g {nutrient_name} per 100g. However, no category-wide market comparative study is attached to the single packaging label."
            else:
                evidence_available = f"Declared {nutrient_name} level is not available on this package."
                missing_info.append(f"Declared {nutrient_name} content on package")

            missing_info.extend([
                "Category-wide comparative market survey / benchmark across competitor products",
                "Substantiation of absolute category-highest claim",
                "Specific reference foods analyzed"
            ])
            compliance_status = "Insufficient evidence to assess compliance"
            confidence = "Needs Verification"
            explanation = (
                "Superlative claims ('highest') invoke market-wide superiority across all competing products. "
                "A single product nutrition panel cannot substantiate category-wide superiority without an identified "
                "market comparator dataset and category benchmark."
            )

        else: # Relative comparison (e.g. 'more protein', '30% less sugar', 'reduced sodium')
            evidence_required = (
                "FSSAI Reg 6 & Schedule IV / Codex CAC/GL 23-1997: Relative comparative claims require a minimum 25% "
                "difference in nutrient content (energy or macronutrients) compared to an explicitly named reference food."
            )
            claimed_diff = comparison_details.get("claimed_difference") if comparison_details else None
            comparator = comparison_details.get("comparator") if comparison_details else None

            current_val = product_data.get(f"{nutrient_name}_g") if nutrient_name in ["protein", "sugars", "total_fat", "saturated_fat", "trans_fat", "dietary_fibre"] else product_data.get(nutrient_name)
            val_str = f"Product declares {current_val}g {nutrient_name}/100g. " if (current_val is not None and not pd.isna(current_val)) else ""

            if comparator and claimed_diff:
                evidence_available = f"{val_str}Packaging states '{claimed_diff}' relative difference compared to '{comparator}'."
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Medium"
                missing_info.append(f"Baseline {nutrient_name} content of reference food '{comparator}' to verify claimed {claimed_diff} differential")
                explanation = (
                    f"Packaging specifies a comparator ('{comparator}') and claimed difference ('{claimed_diff}'), "
                    f"which satisfies the labelling disclosure requirement. Baseline nutrient data for '{comparator}' "
                    f"must be verified to confirm the statutory 25% difference."
                )
            elif comparator and not claimed_diff:
                evidence_available = f"{val_str}Names comparator '{comparator}', but does not specify the quantitative percentage difference."
                compliance_status = "Potential concern — review required"
                confidence = "Medium"
                missing_info.append("Quantitative differential declaration (minimum 25% required)")
                explanation = f"Comparator '{comparator}' is named, but statutory regulations require declaring the quantitative difference (minimum 25% relative difference)."
            else:
                evidence_available = f"{val_str}No reference food or competitor baseline is named on the packaging."
                compliance_status = "Potential concern — review required"
                confidence = "High"
                missing_info.extend([
                    "Identity of reference food / comparator product",
                    "Baseline nutrient value of comparator",
                    "Quantitative difference (minimum 25% required by FSSAI/Codex)"
                ])
                explanation = (
                    "FSSAI and Codex require comparative claims to explicitly name the reference food "
                    "and demonstrate at least a 25% difference. The claim does not state what food it is being compared to."
                )

    # --- Case 2: Sugar-Related Claims (without comparative precedence, or secondary sugar check) ---
    elif "Sugar-Related Claim" in detected_types or "sugars" in nutrients:
        regulatory_source = f"{FSSAI_REF_NUTRIENT} / {FSSAI_REF_NON_ADDITION} / {CODEX_REF_CLAIMS}"
        lower_claim = normalized.lower()

        if "zero" in lower_claim or "sugar-free" in lower_claim or "0%" in lower_claim or "no sugar" in lower_claim:
            evidence_required = "Codex CAC/GL 23-1997 / FSSAI Schedule II: Sugar-free claim limit <= 0.5g total sugars per 100g/100ml."
            val = product_data.get("sugars_g")
            if val is None or pd.isna(val):
                evidence_available = "Total sugars declaration is absent from packaging data."
                missing_info.append("Total sugars declaration")
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Needs Verification"
                explanation = "Cannot evaluate Sugar-Free claim because total sugars are not declared on the label."
            elif val <= 0.5:
                evidence_available = f"Reported total sugars is {val}g per 100g (Statutory limit: <= 0.5g)."
                compliance_status = "Consistent with the checked criteria"
                confidence = "High"
                explanation = "Meets statutory threshold (<= 0.5g/100g) for sugar-free claims."
            else:
                evidence_available = f"Reported total sugars is {val}g per 100g (Statutory limit: <= 0.5g)."
                compliance_status = "Potentially inconsistent with the checked criteria"
                confidence = "High"
                explanation = f"Declared sugars ({val}g/100g) exceeds the statutory limit (<= 0.5g) for sugar-free claims."

        elif "low sugar" in lower_claim:
            evidence_required = "Codex CAC/GL 23-1997 / FSSAI Schedule II: Low sugar claim limit <= 5.0g total sugars per 100g (solids) or <= 2.5g (liquids)."
            val = product_data.get("sugars_g")
            if val is None or pd.isna(val):
                evidence_available = "Total sugars declaration is absent from packaging data."
                missing_info.append("Total sugars declaration")
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Needs Verification"
                explanation = "Cannot evaluate Low Sugar claim because total sugars are not declared on the label."
            elif val <= 5.0:
                evidence_available = f"Reported total sugars is {val}g per 100g (Statutory limit: <= 5.0g)."
                compliance_status = "Consistent with the checked criteria"
                confidence = "High"
                explanation = "Meets statutory threshold (<= 5.0g/100g) for low sugar claims."
            else:
                evidence_available = f"Reported total sugars is {val}g per 100g (Statutory limit: <= 5.0g)."
                compliance_status = "Potentially inconsistent with the checked criteria"
                confidence = "High"
                explanation = f"Declared sugars ({val}g/100g) exceeds the statutory limit (<= 5.0g) for low sugar claims."

        elif "no added sugar" in lower_claim or "without added sugar" in lower_claim:
            evidence_required = (
                "FSSAI Reg 6(1): Product must contain 0g added refining sugars AND no added ingredients "
                "that contain free sugars (e.g., honey, invert syrup, jaggery, corn syrup, fruit juice concentrates)."
            )
            added_sugar = product_data.get("added_sugars_g")
            hidden_found = [term for term in HIDDEN_SUGAR_TERMS if term in ingredients_text]
            # Plain sugar itself, not only its syrups and derivatives ("sugar-free" sweetener names excluded).
            if not hidden_found and re.search(r"\bsugar\b(?![\s-]*free)", ingredients_text):
                hidden_found = ["sugar"]

            if (added_sugar is None or pd.isna(added_sugar)) and not hidden_found:
                evidence_available = "Added sugars not separately declared; no obvious free sugar terms in ingredients."
                missing_info.append("Quantitative added sugars declaration")
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Needs Verification"
                explanation = "Requires quantitative declaration of added sugars to verify absence of refined sweeteners."
            elif (added_sugar is not None and not pd.isna(added_sugar) and added_sugar == 0.0) and not hidden_found:
                evidence_available = "Added sugars declared as 0g, and no free sugar syrups detected in ingredient list."
                compliance_status = "Consistent with the checked criteria"
                confidence = "High"
                explanation = "Available packaging data supports the absence of added refining sugars."
            elif hidden_found:
                evidence_available = f"Ingredient list contains concentrated caloric sweetening agents: {', '.join(hidden_found)}."
                compliance_status = "Potentially inconsistent with the checked criteria"
                confidence = "High"
                explanation = (
                    f"While packaging claims 'No Added Sugar', ingredients declare free sugar derivatives "
                    f"({', '.join(hidden_found)}), which is restricted under FSSAI non-addition claim regulations."
                )
            else:
                evidence_available = f"Added sugars explicitly declared as {added_sugar}g."
                compliance_status = "Potentially inconsistent with the checked criteria"
                confidence = "High"
                explanation = f"Product declares {added_sugar}g added sugar, contradicting a No Added Sugar claim."

    # --- Case 3: Absolute Nutrient-Content Claims (High Protein, Low Fat, Rich in Fibre, Low Sodium) ---
    elif "Nutrient-Content Claim" in detected_types:
        regulatory_source = f"{FSSAI_REF_NUTRIENT} / {CODEX_REF_CLAIMS}"

        if "protein" in nutrients:
            is_high = any(w in normalized.lower() for w in ["high", "rich", "packed", "loaded", "excellent"])
            threshold = 10.0 if is_high else 5.0
            claim_label = "High Protein" if is_high else "Source of Protein"
            evidence_required = f"FSSAI Schedule II / Codex: '{claim_label}' requires >= {threshold}g protein per 100g (or 20% of energy for high, 10% for source)."

            val = product_data.get("protein_g")
            if val is None or pd.isna(val):
                evidence_available = "Protein declaration is absent from the nutritional facts panel."
                missing_info.append("Protein declaration")
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Needs Verification"
                explanation = f"Cannot confirm {claim_label} claim because protein declaration is absent."
            elif val >= threshold:
                evidence_available = f"Reported protein is {val}g per 100g (Statutory threshold: >= {threshold}g)."
                compliance_status = "Consistent with the checked criteria"
                confidence = "High"
                explanation = f"Product satisfies statutory criteria for {claim_label} ({val}g/100g vs required >={threshold}g)."
            else:
                evidence_available = f"Reported protein is {val}g per 100g (Statutory threshold: >= {threshold}g)."
                compliance_status = "Potentially inconsistent with the checked criteria"
                confidence = "High"
                explanation = f"Reported protein ({val}g/100g) falls below the {threshold}g threshold for {claim_label} declarations."

        elif "dietary_fibre" in nutrients:
            is_high = any(w in normalized.lower() for w in ["high", "rich", "excellent"])
            threshold = 6.0 if is_high else 3.0
            claim_label = "High in Fibre" if is_high else "Source of Fibre"
            evidence_required = f"FSSAI Schedule II / Codex: '{claim_label}' requires >= {threshold}g dietary fibre per 100g."

            val = product_data.get("dietary_fibre_g")
            if val is None or pd.isna(val):
                evidence_available = "Dietary fibre declaration is missing from data."
                missing_info.append("Dietary fibre declaration")
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Needs Verification"
                explanation = f"Fibre content is not declared on packaging to assess '{claim_label}'."
            elif val >= threshold:
                evidence_available = f"Reported dietary fibre is {val}g per 100g (Statutory threshold: >= {threshold}g)."
                compliance_status = "Consistent with the checked criteria"
                confidence = "High"
                explanation = f"Meets statutory benchmark for {claim_label} ({val}g/100g)."
            else:
                evidence_available = f"Reported dietary fibre is {val}g per 100g (Statutory threshold: >= {threshold}g)."
                compliance_status = "Potentially inconsistent with the checked criteria"
                confidence = "High"
                explanation = f"Reported fibre ({val}g/100g) is below the statutory threshold of {threshold}g/100g."

        elif "total_fat" in nutrients:
            is_free = any(w in normalized.lower() for w in ["zero", "free", "0%"])
            threshold = 0.5 if is_free else 3.0
            claim_label = "Fat Free" if is_free else "Low Fat"
            evidence_required = f"FSSAI Schedule II / Codex: '{claim_label}' requires <= {threshold}g total fat per 100g."

            val = product_data.get("total_fat_g")
            if val is None or pd.isna(val):
                evidence_available = "Total fat declaration is missing."
                missing_info.append("Total fat declaration")
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Needs Verification"
                explanation = f"Cannot evaluate {claim_label} claim without total fat declaration."
            elif val <= threshold:
                evidence_available = f"Reported total fat is {val}g per 100g (Statutory limit: <= {threshold}g)."
                compliance_status = "Consistent with the checked criteria"
                confidence = "High"
                explanation = f"Satisfies statutory {claim_label} limit ({val}g/100g)."
            else:
                evidence_available = f"Reported total fat is {val}g per 100g (Statutory limit: <= {threshold}g)."
                compliance_status = "Potentially inconsistent with the checked criteria"
                confidence = "High"
                explanation = f"Declared total fat ({val}g/100g) exceeds the statutory limit of {threshold}g/100g."

        elif "sodium" in nutrients:
            threshold = 120.0
            evidence_required = "FSSAI Schedule II / Codex: 'Low Sodium' requires <= 120mg sodium per 100g."
            val = product_data.get("sodium_mg")
            if val is None or pd.isna(val):
                evidence_available = "Sodium is not declared on package."
                missing_info.append("Sodium declaration")
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Needs Verification"
                explanation = "Sodium declaration is missing."
            elif val <= threshold:
                evidence_available = f"Reported sodium is {val}mg per 100g (Statutory limit: <= 120mg)."
                compliance_status = "Consistent with the checked criteria"
                confidence = "High"
                explanation = f"Meets statutory low sodium threshold ({val}mg/100g)."
            else:
                evidence_available = f"Reported sodium is {val}mg per 100g (Statutory limit: <= 120mg)."
                compliance_status = "Potentially inconsistent with the checked criteria"
                confidence = "High"
                explanation = f"Declared sodium ({val}mg/100g) exceeds the statutory ceiling of 120mg/100g."

        else:
            evidence_required = "Statutory nutrient content schedule verification."
            evidence_available = "Nutrient declaration requires lab panel audit."
            compliance_status = "Insufficient evidence to assess compliance"
            confidence = "Needs Verification"
            explanation = "Nutrient level declaration requires laboratory verification."

    # --- Case 4: Free-From Claims (Gluten-Free, Preservative-Free, Trans-Fat Free) ---
    elif "Free-From Claim" in detected_types:
        lower_claim = normalized.lower()
        if "gluten" in lower_claim:
            regulatory_source = "FSSAI (Food Products Standards and Food Additives) Regulations: Gluten-free requires < 20 mg/kg (20 ppm) gluten."
            evidence_required = "Gluten content < 20 ppm and zero gluten-containing grains in ingredients."
            gluten_found = [grain for grain in GLUTEN_GRAIN_TERMS if grain in ingredients_text]
            if gluten_found:
                evidence_available = f"Ingredients declare gluten-containing grains: {', '.join(gluten_found)}."
                compliance_status = "Potentially inconsistent with the checked criteria"
                confidence = "High"
                explanation = f"Product claims Gluten-Free, but ingredients list contains gluten sources ({', '.join(gluten_found)})."
            else:
                evidence_available = "No explicit gluten grains detected in ingredient list."
                missing_info.append("Laboratory test report confirming gluten content < 20 ppm")
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Needs Verification"
                explanation = "Ingredients do not list gluten grains; laboratory verification (<20 ppm) is required for formal certification."

        elif "preservative" in lower_claim:
            regulatory_source = "FSSAI (Advertising and Claims) Regulations, 2018: Preservative-free claims prohibit all Class I & Class II preservatives."
            evidence_required = "Zero chemical or synthetic food preservatives declared in ingredients."
            preservatives_found = [p for p in COMMON_CHEMICAL_PRESERVATIVES if p in ingredients_text]
            if preservatives_found:
                evidence_available = f"Ingredients declare preservatives: {', '.join(preservatives_found)}."
                compliance_status = "Potentially inconsistent with the checked criteria"
                confidence = "High"
                explanation = f"Packaging claims Preservative-Free, but declares preservative additives ({', '.join(preservatives_found)})."
            else:
                evidence_available = "No listed chemical preservatives detected in ingredient list."
                compliance_status = "Consistent with available data"
                confidence = "Medium"
                explanation = "Available ingredient panel does not declare standard chemical preservatives."

        elif "trans" in lower_claim:
            regulatory_source = "FSSAI (Advertising and Claims) Regulations, 2018: Trans fat free requires <= 0.2g trans fat per 100g."
            evidence_required = "Trans fat content <= 0.2g per 100g and no partially hydrogenated vegetable oils."
            tf = product_data.get("trans_fat_g")
            if tf is not None and not pd.isna(tf):
                if tf <= 0.2 and "partially hydrogenated" not in ingredients_text:
                    evidence_available = f"Declared trans fat is {tf}g/100g with no partially hydrogenated oils."
                    compliance_status = "Consistent with available data"
                    confidence = "High"
                    explanation = "Meets trans-fat free standard (<= 0.2g/100g)."
                else:
                    evidence_available = f"Declared trans fat is {tf}g/100g."
                    compliance_status = "Potentially inconsistent with the checked criteria"
                    confidence = "High"
                    explanation = f"Trans fat ({tf}g) exceeds statutory limit (<= 0.2g)."
            else:
                evidence_available = "Trans fat not separately declared on label."
                missing_info.append("Trans fat declaration")
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Needs Verification"
                explanation = "Trans fat must be explicitly declared to substantiate claim."

    # --- Case 5: Health-Related Claims & Nutrient-Function Claims ---
    elif "Health-Related Claim" in detected_types or "Nutrient-Function Claim" in detected_types:
        regulatory_source = f"{FSSAI_REF_HEALTH} / {CODEX_REF_CLAIMS}"
        evidence_required = (
            "FSSAI Reg 7 & Schedule III/V: Health and function claims must be backed by documented "
            "clinical evidence and approved physiological benefit schedules."
        )
        evidence_available = "Packaging states physiological health benefit without documented clinical trial or statutory schedule reference."
        missing_info.extend([
            "Approved FSSAI Schedule III/V listing or pre-market approval notice",
            "Human intervention clinical study supporting health benefit"
        ])
        compliance_status = "Potential concern — review required"
        confidence = "Medium"
        explanation = (
            "Health claims ('supports immunity', 'heart healthy') are subject to stringent pre-market approval under FSSAI. "
            "Available packaging declarations do not provide the mandatory clinical endorsement or approved schedule reference."
        )

    # --- Case 6: Ingredient & Composition Claims ---
    elif "Ingredient & Composition Claim" in detected_types:
        regulatory_source = "FSSAI (Advertising and Claims) Regulations, 2018 (Regulation 4)"
        evidence_required = "FSSAI Reg 4: Ingredient highlighted on front-of-pack must specify quantitative percentage in ingredient list (QUID rules)."

        # Check if the highlighted ingredient is in ingredients
        lower_claim = normalized.lower()
        if "juice" in lower_claim:
            added = product_data.get("added_sugars_g", 0)
            if added == 0 and ("reconstituted" in ingredients_text or "concentrate" in ingredients_text or "pure" in ingredients_text):
                evidence_available = "Reconstituted fruit juice concentrate without added refined cane sugar."
                compliance_status = "Consistent with available data"
                confidence = "Medium"
                explanation = "Ingredients support fruit juice composition without added refined sugar."
            else:
                evidence_available = "May contain added sugars or water dilution."
                missing_info.append("Fruit juice percentage disclosure (QUID)")
                compliance_status = "Insufficient evidence to assess compliance"
                confidence = "Needs Verification"
                explanation = "Requires quantitative ingredient declaration (QUID) of fruit juice percentage."
        else:
            evidence_available = "Ingredient highlighted on package."
            missing_info.append("Quantitative Ingredient Declaration (QUID percentage in ingredients list)")
            compliance_status = "Insufficient evidence to assess compliance"
            confidence = "Medium"
            explanation = "Under FSSAI rules, highlighting an ingredient on the front of pack requires declaring its percentage in the ingredient list."

    # --- Case 7: Organic & Natural Claims ---
    elif "Organic & Natural Claim" in detected_types:
        regulatory_source = "FSSAI Food Safety and Standards (Organic Foods) Regulations, 2017 / Jaivik Bharat"
        evidence_required = "Organic claims require certified NPOP / PGS-India accreditation and Jaivik Bharat logo."
        evidence_available = "Package states organic/natural without verifiable certification logo data in digital record."
        missing_info.append("NPOP / PGS-India Certification / Jaivik Bharat authentication")
        compliance_status = "Insufficient evidence to assess compliance"
        confidence = "Needs Verification"
        explanation = "Organic claims in India strictly require statutory Jaivik Bharat certification. Packaging logo authentication required."

    # --- Case 8: Descriptive / Sensory Claims ---
    elif "Descriptive / Sensory Claim" in detected_types:
        regulatory_source = "Non-statutory marketing descriptor"
        evidence_required = "None — culinary/texture descriptions are outside quantitative nutrition regulation scope."
        evidence_available = "Subjective sensory description (e.g., crispy, creamy, delicious, rich flavour)."
        compliance_status = "Classification complete — non-statutory sensory claim"
        confidence = "High"
        explanation = "This is a subjective texture or culinary descriptor rather than a regulated front-of-pack health or nutrition claim."

    # --- Case 9: Unclassified / Ambiguous ---
    else:
        regulatory_source = "FSSAI General Labelling Requirements"
        evidence_required = "Manufacturer substantiation of ambiguous marketing phrase."
        evidence_available = f"Unclassified marketing phrase: '{normalized}'."
        missing_info.append("Manufacturer context or definition of marketing phrase")
        compliance_status = "Potential concern — review required"
        confidence = "Needs Verification"
        explanation = "This claim does not match standard statutory nutrient, comparative, health, or sensory categories. Requires manufacturer substantiation."

    return {
        "claim": claim_raw,
        "original_claim": claim_raw,
        "normalized_claim": normalized,
        "status": compliance_status, # clean backward compatibility
        "compliance_status": compliance_status,
        "detected_claim_types": detected_types,
        "primary_claim_type": primary_type,
        "classification_rationale": taxonomy["classification_rationale"],
        "relevant_nutrient": primary_nutrient.capitalize() if primary_nutrient else None,
        "comparative_terms": taxonomy["comparative_terms"],
        "comparison_details": comparison_details,
        "evidence_required": evidence_required,
        "evidence_available": evidence_available,
        "criterion_applied": regulatory_source,
        "regulatory_source": regulatory_source,
        "missing_information": missing_info,
        "confidence_indicator": confidence,
        "evidence": evidence_available,
        "explanation": explanation,
        "disclaimer": "Automated claim auditing evaluates available packaging data against benchmark criteria. It does not constitute a formal legal or regulatory determination."
    }

def evaluate_claims(marketing_claims: str, product_data: dict) -> list[dict[str, Any]]:
    """
    Evaluates marketing claims declared on packaging against available nutrition facts and ingredients.
    Parses multiple claims separated by commas, semicolons, or slashes.
    """
    if not marketing_claims or pd.isna(marketing_claims) or str(marketing_claims).strip() in ["", "nan"]:
        return []

    # Parse individual claims separated by commas, semicolons, or slashes
    claims_list = [c.strip() for c in re.split(r'[,;/]+', str(marketing_claims)) if c.strip()]
    evaluations = []

    for claim in claims_list:
        eval_result = evaluate_single_claim(claim, product_data)
        evaluations.append(eval_result)

    return evaluations
