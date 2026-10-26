"""
EATGOOD — Misleading Claim Detection Engine (Section 6)
Evaluates marketing claims against verified nutritional facts and documented reference criteria.
Produces objective transparency ratings without premature accusations of fraud.
"""

import re
import pandas as pd

CLAIM_CRITERIA = {
    "High Protein": {
        "nutrient": "protein_g",
        "threshold": 10.0,
        "operator": ">=",
        "reference": "Codex CAC/GL 23-1997 / FSSAI Labelling Regulations (At least 10g per 100g or 20% energy)",
        "unit": "g per 100g"
    },
    "Zero Sugar": {
        "nutrient": "sugars_g",
        "threshold": 0.5,
        "operator": "<=",
        "reference": "Codex Alimentarius: Sugar-free claim limit <= 0.5g per 100g/100ml",
        "unit": "g per 100g"
    },
    "No Added Sugar": {
        "nutrient": "added_sugars_g",
        "threshold": 0.0,
        "operator": "<=",
        "reference": "FSSAI (Labelling & Display) 2020: Contains no added sugars or ingredients with added sugar",
        "unit": "g"
    },
    "Low Fat": {
        "nutrient": "total_fat_g",
        "threshold": 3.0,
        "operator": "<=",
        "reference": "Codex / FSSAI: Low Fat claim standard <= 3.0g fat per 100g",
        "unit": "g per 100g"
    },
    "Rich in Fibre": {
        "nutrient": "dietary_fibre_g",
        "threshold": 6.0,
        "operator": ">=",
        "reference": "Codex CAC/GL 23-1997: High in Fibre claim threshold >= 6.0g per 100g",
        "unit": "g per 100g"
    },
    "100% Real Juice": {
        "nutrient": "category",
        "reference": "FSSAI Fruit Beverage Standards: Must be reconstituted from fruit concentrate with 0 added synthetic sugar",
        "unit": "category standard"
    }
}

HIDDEN_SUGAR_TERMS = [
    "liquid glucose", "invert sugar", "maltodextrin", "corn syrup",
    "high fructose corn syrup", "dextrose", "malt extract", "caramel syrup"
]

def evaluate_claims(marketing_claims: str, product_data: dict):
    """
    Evaluates marketing claims declared on packaging against available nutrition facts and ingredients.
    """
    if not marketing_claims or pd.isna(marketing_claims) or str(marketing_claims).strip() in ["", "nan"]:
        return []

    # Parse individual claims separated by commas or slashes
    claims_list = [c.strip() for c in re.split(r'[,;/]+', str(marketing_claims)) if c.strip()]
    evaluations = []

    ingredients_text = str(product_data.get("ingredients", "")).lower()

    for claim in claims_list:
        matched_criterion = None
        for crit_key in CLAIM_CRITERIA:
            if crit_key.lower() in claim.lower():
                matched_criterion = (crit_key, CLAIM_CRITERIA[crit_key])
                break

        if not matched_criterion:
            # Descriptive general claim (e.g. "Crispy & Crunchy", "Authentic Taste")
            evaluations.append({
                "claim": claim,
                "status": "Descriptive / Sensory Claim",
                "criterion_applied": "Sensory marketing claim — outside quantitative nutrition regulation scope.",
                "evidence": "Does not invoke a statutory nutritional threshold.",
                "explanation": "This is a subjective texture or flavour description rather than a regulated front-of-pack health claim."
            })
            continue

        crit_key, crit_info = matched_criterion

        if crit_key == "High Protein":
            val = product_data.get("protein_g")
            if pd.isna(val):
                status = "Needs verification"
                evidence = "Protein content is missing from label data."
                expl = "Cannot confirm High Protein claim because protein declaration is absent."
            elif val >= crit_info["threshold"]:
                status = "Consistent with available data"
                evidence = f"Reported protein is {val}g per 100g (Threshold: >= {crit_info['threshold']}g)."
                expl = f"Product satisfies the Codex and FSSAI threshold for High Protein claims ({val}g/100g)."
            else:
                status = "Potential inconsistency"
                evidence = f"Reported protein is {val}g per 100g (Required: >= {crit_info['threshold']}g)."
                expl = f"Reported protein ({val}g/100g) falls below the standard threshold of {crit_info['threshold']}g for high protein declarations."

        elif crit_key == "Zero Sugar":
            val = product_data.get("sugars_g")
            if pd.isna(val):
                status = "Needs verification"
                evidence = "Sugar value is missing."
                expl = "Cannot verify Zero Sugar without a verified sugars declaration."
            elif val <= crit_info["threshold"]:
                status = "Consistent with available data"
                evidence = f"Reported sugars is {val}g per 100g (Limit: <= {crit_info['threshold']}g)."
                expl = f"Meets international regulatory threshold (<= {crit_info['threshold']}g) for zero sugar claims."
            else:
                status = "Potential inconsistency"
                evidence = f"Reported sugars is {val}g per 100g (Limit: <= {crit_info['threshold']}g)."
                expl = f"Product declares {val}g total sugars, which exceeds the statutory zero sugar allowance."

        elif crit_key == "No Added Sugar":
            added_sugar = product_data.get("added_sugars_g")
            hidden_found = [term for term in HIDDEN_SUGAR_TERMS if term in ingredients_text]
            
            if pd.isna(added_sugar) and not hidden_found:
                status = "Needs verification"
                evidence = "Added sugar field not separately broken down on package."
                expl = "Requires lab verification of added vs intrinsic sugar proportions."
            elif (pd.notna(added_sugar) and added_sugar == 0.0) and not hidden_found:
                status = "Consistent with available data"
                evidence = "Added sugars declared as 0g, and no free sugar syrups detected in ingredient list."
                expl = "Available evidence supports the absence of added refining sugars."
            elif hidden_found:
                status = "Potential inconsistency"
                evidence = f"Ingredient list contains sugar derivatives: {', '.join(hidden_found)}."
                expl = f"While marketing claims 'No Added Sugar', ingredients include concentrated glycemic agents ({', '.join(hidden_found)})."
            else:
                status = "Potential inconsistency"
                evidence = f"Added sugars explicitly declared as {added_sugar}g."
                expl = f"Package states {added_sugar}g added sugar, contradicting a No Added Sugar claim."

        elif crit_key == "Low Fat":
            val = product_data.get("total_fat_g")
            if pd.isna(val):
                status = "Needs verification"
                evidence = "Total fat is missing from data."
                expl = "Cannot confirm without verified total fat metric."
            elif val <= crit_info["threshold"]:
                status = "Consistent with available data"
                evidence = f"Reported total fat is {val}g per 100g (Threshold: <= {crit_info['threshold']}g)."
                expl = "Satisfies statutory low-fat limit."
            else:
                status = "Potential inconsistency"
                evidence = f"Reported total fat is {val}g per 100g (Required: <= {crit_info['threshold']}g)."
                expl = f"Total fat ({val}g) exceeds the 3.0g/100g ceiling."

        elif crit_key == "Rich in Fibre":
            val = product_data.get("dietary_fibre_g")
            if pd.isna(val):
                status = "Needs verification"
                evidence = "Dietary fibre is not declared on package."
                expl = "Fibre declaration is missing from the nutritional facts panel."
            elif val >= crit_info["threshold"]:
                status = "Consistent with available data"
                evidence = f"Dietary fibre is {val}g per 100g (Threshold: >= {crit_info['threshold']}g)."
                expl = "Meets international standard for high dietary fibre claim."
            else:
                status = "Potential inconsistency"
                evidence = f"Dietary fibre is {val}g per 100g (Required: >= {crit_info['threshold']}g)."
                expl = f"Fibre content ({val}g) is below the 6g standard threshold."

        else: # 100% Real Juice
            sugars = product_data.get("sugars_g", 0)
            added = product_data.get("added_sugars_g", 0)
            if added == 0 and ("reconstituted" in ingredients_text or "concentrate" in ingredients_text or "pure" in ingredients_text):
                status = "Consistent with available data"
                evidence = "Reconstituted fruit juice concentrate without cane sugar addition."
                expl = "Complies with juice reconstitution standard."
            else:
                status = "Needs verification"
                evidence = "May contain added sweetening agents or water reconstitution."
                expl = "Further inspection of fruit pulp proportion required."

        evaluations.append({
            "claim": claim,
            "status": status,
            "criterion_applied": crit_info.get("reference", ""),
            "evidence": evidence,
            "explanation": expl
        })

    return evaluations
