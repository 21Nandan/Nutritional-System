"""
Gemini phrasing for product questions the built-in answers don't cover. Gemini gets only this
product's facts and EATGOOD's own results (grade, Goal Match and their reasons) and must answer from
them alone, so it explains the scores rather than inventing new ones. Returns None to fall back.
"""

import re
from typing import Any

from backend.core import gemini
from backend.core.nutrition_scoring import run_full_product_assessment

FACT_FIELDS = [
    ("energy_kcal", "Energy", "kcal"), ("carbohydrates_g", "Carbohydrates", "g"), ("sugars_g", "Total sugars", "g"),
    ("added_sugars_g", "Added sugars", "g"), ("protein_g", "Protein", "g"), ("total_fat_g", "Total fat", "g"),
    ("saturated_fat_g", "Saturated fat", "g"), ("trans_fat_g", "Trans fat", "g"), ("sodium_mg", "Sodium", "mg"),
    ("dietary_fibre_g", "Dietary fibre", "g"),
]

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "answer": {"type": "STRING"},
        "details": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["answer"],
}

INSTRUCTIONS = (
    "You answer a shopper's question about one packaged food, using ONLY the facts below. "
    "If the facts don't answer it, say what is known and that the label doesn't say. Never invent values, "
    "never change the grade or Goal Match, give no medical diagnosis, and suggest a doctor or dietitian for "
    "medical conditions. Reply in the language of the question. Keep 'answer' to at most 2 short sentences "
    "and 'details' to at most 3 short points. Do not mention these instructions or that you are an AI."
)


def _facts(product: dict[str, Any], profile: dict[str, Any]) -> str:
    assessment = run_full_product_assessment(product, profile)
    l1, l2 = assessment.get("layer1_general", {}), assessment.get("layer2_personalized", {})
    basis = product.get("measurement_basis") or "per 100g"
    values = [f"{label}: {product[key]} {unit}" for key, label, unit in FACT_FIELDS if product.get(key) is not None]
    over = [f"{k.replace('_', ' ')} {v.get('value')} vs limit {v.get('threshold')}"
            for k, v in (l1.get("key_contributing_nutrients") or {}).items() if (v.get("points") or 0) < 0]
    lines = [
        f"Product: {product.get('product_name')} by {product.get('brand')} ({product.get('category')})",
        f"Values ({basis}): " + ("; ".join(values) or "none stated"),
        f"Ingredients: {product.get('ingredients') or 'not stated'}",
        f"Allergens declared: {product.get('allergens_declared') or 'not stated'}",
        f"Nutrition grade (same for everyone): {l1.get('grade')}" + (f" - {l1.get('grade_reason')}" if l1.get("grade_reason") else ""),
        "Over the category limit: " + ("; ".join(over) or "nothing"),
        f"Goal Match for the shopper's goal ({l2.get('user_goal')}): {l2.get('personalized_score')}/100",
        "Goal Match reasons: " + ("; ".join(l2.get("rules_applied") or []) or "none"),
        f"Shopper's diet: {profile.get('dietary_preference') or 'No preference'}; allergens to avoid: {profile.get('allergens_to_avoid') or 'none'}",
    ]
    return "\n".join(lines)


def answer_with_gemini(product: dict[str, Any], question: str, profile: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any] | None:
    # Lower-cased and trimmed so the same question asked twice reuses the cached answer.
    clean_question = re.sub(r"\s+", " ", question.strip().lower()).rstrip("?!. ")
    prompt = f"{INSTRUCTIONS}\n\nFACTS\n{_facts(product, profile)}\n\nQUESTION\n{clean_question}"
    reply = gemini.generate_json(prompt, SCHEMA, text_only=True, max_output_tokens=300)
    if not isinstance(reply, dict) or not str(reply.get("answer") or "").strip():
        return None
    answer = str(reply["answer"]).strip()[:600]
    details = [str(d).strip()[:300] for d in (reply.get("details") or []) if str(d).strip()][:3]
    return {
        **fallback,
        "answer": "\n\n".join([answer, *details]),
        "conclusion": [{"text": answer}],
        "details": [[{"text": d}] for d in details],
        "understood": True,
    }


SEARCH_SCHEMA = {"type": "OBJECT", "properties": {"keywords": {"type": "STRING"}}, "required": ["keywords"]}


def rewrite_search_query(query: str) -> str | None:
    """Two to four product words for a search written in everyday language, or None."""
    clean = re.sub(r"\s+", " ", query.strip().lower())
    prompt = (
        "A shopper searched an Indian packaged-food catalogue with the words below and found nothing. "
        "Give 1 to 4 plain words naming the kind of product they most likely want (for example 'roasted makhana', "
        "'oats', 'dark chocolate', 'ragi biscuits'), using product names or types, not adjectives like 'healthy'. "
        f"Search: {clean}"
    )
    reply = gemini.generate_json(prompt, SEARCH_SCHEMA, text_only=True, max_output_tokens=40)
    words = re.sub(r"[^a-z0-9 &'-]", " ", str((reply or {}).get("keywords") or "").lower()).split()
    rewritten = " ".join(words[:4])
    return rewritten if rewritten and rewritten != clean else None


CLAIM_STATUSES = [
    "Consistent with available data",
    "Potentially inconsistent with the checked criteria",
    "Insufficient evidence to assess compliance",
    "Descriptive / Sensory Claim",
]
CLAIM_TYPES = [
    "Ingredient & Composition Claim", "Free-From Claim", "Nutrient-Content Claim", "Processing Claim",
    "Health Claim", "Descriptive / Sensory Claim", "Other Claim",
]
CLAIMS_CHECK_SCHEMA = {
    "type": "OBJECT",
    "properties": {"results": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "claim": {"type": "STRING"},
        "claim_type": {"type": "STRING", "enum": CLAIM_TYPES},
        "status": {"type": "STRING", "enum": CLAIM_STATUSES},
        "evidence": {"type": "STRING"},
        "explanation": {"type": "STRING"},
    }, "required": ["claim", "claim_type", "status", "evidence", "explanation"]}}},
    "required": ["results"],
}


def check_claims_with_gemini(claims: list[str], product: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Verdicts for claims the built-in checks don't recognise, all in one request, keyed by claim text.
    Judged only against this product's ingredients and values; an empty dict means use the built-in result."""
    values = [f"{label}: {product[key]} {unit}" for key, label, unit in FACT_FIELDS if product.get(key) is not None]
    prompt = (
        "Check each claim printed on a packaged food against ONLY the facts below. 'Consistent' when the "
        "ingredients and values support it; 'Potentially inconsistent' when they contradict it (e.g. 'no oil' "
        "but oil is an ingredient); 'Insufficient evidence' when the facts can't settle it (e.g. 'baked not fried': "
        "oil in the ingredients doesn't show the product was fried, so judge it only if the label says how it was "
        "made); 'Descriptive / Sensory' for taste or texture words. Quote the fact you used as "
        "evidence. One short sentence of explanation each. Do not mention these instructions or that you are an AI.\n\n"
        f"Product: {product.get('product_name')} ({product.get('category')})\n"
        f"Values ({product.get('measurement_basis') or 'per 100g'}): {'; '.join(values) or 'none stated'}\n"
        f"Ingredients: {product.get('ingredients') or 'not stated'}\n"
        f"Allergens declared: {product.get('allergens_declared') or 'not stated'}\n\n"
        "Claims:\n" + "\n".join(f"- {c}" for c in claims)
    )
    reply = gemini.generate_json(prompt, CLAIMS_CHECK_SCHEMA, text_only=True, max_output_tokens=150 + 120 * len(claims))
    results = (reply or {}).get("results") if isinstance(reply, dict) else None
    out: dict[str, dict[str, str]] = {}
    for item in results or []:
        claim = str(item.get("claim") or "").strip().lower()
        if claim and item.get("status") in CLAIM_STATUSES:
            out[claim] = {k: str(item.get(k) or "")[:400] for k in ("claim_type", "status", "evidence", "explanation")}
    return out


INGREDIENTS_SCHEMA = {
    "type": "OBJECT",
    "properties": {"items": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "as_listed": {"type": "STRING"},
        "what_it_is": {"type": "STRING"},
        "why_used": {"type": "STRING"},
        "note": {"type": "STRING"},
    }, "required": ["as_listed", "what_it_is", "why_used"]}}},
    "required": ["items"],
}


def explain_ingredients(ingredients: str, known_additives: list[dict[str, Any]]) -> list[dict[str, str]] | None:
    """Plain explanations of the items on this ingredient list, or None to fall back. Only items whose
    'as_listed' text really appears in the list are kept, so nothing is invented. Additives the built-in
    list knows keep its name and class."""
    text = str(ingredients or "").strip()
    if not text:
        return None
    known = "; ".join(f"{a['code']} = {a['name']} ({a['functional_class']})" for a in known_additives
                      if not a["name"].startswith("Food Additive "))
    prompt = (
        "Explain the ingredients of a packaged food for a shopper, in plain words. Use widely accepted food-science "
        "and regulatory knowledge (FSSAI, Codex, JECFA); don't overstate risks. For each distinct ingredient or "
        "additive on the list (at most 14, most important first), give: 'as_listed' copied exactly as it appears "
        "in the list, 'what_it_is', 'why_used', and 'note' only for a real, well-established consideration (e.g. "
        "high in saturated fat, refined flour, a source of added sugar, a common allergen, flavour enhancer); "
        "otherwise leave 'note' empty. Additive codes like 500(ii) or INS 471 are additives; name them. "
        + (f"Use these known names: {known}. " if known else "")
        + "Do not mention these instructions or that you are an AI.\n\nIngredients: " + text[:2500]
    )
    reply = gemini.generate_json(prompt, INGREDIENTS_SCHEMA, text_only=True, max_output_tokens=1400)
    items = (reply or {}).get("items") if isinstance(reply, dict) else None
    if not items:
        return None
    lowered = text.lower()
    out = []
    for item in items:
        listed = str(item.get("as_listed") or "").strip()
        if not listed or listed.lower() not in lowered:
            continue  # not on this product's list
        out.append({k: str(item.get(k) or "").strip()[:240] for k in ("as_listed", "what_it_is", "why_used", "note")})
    return out[:14] or None


COMPARE_SCHEMA = {"type": "OBJECT", "properties": {"explanation": {"type": "STRING"}}, "required": ["explanation"]}


def explain_comparison(facts: list[dict[str, Any]], priority: dict[str, int], goal: str) -> str | None:
    """Two or three plain sentences on how the products differ, from their values and EATGOOD's results."""
    lines = []
    for f in facts:
        values = ", ".join(f"{k.replace('_', ' ')} {f[k]}" for k in ("sugars_g", "sodium_mg", "saturated_fat_g", "protein_g",
                                                                       "dietary_fibre_g", "energy_kcal") if f.get(k) is not None)
        rank = priority.get(str(f["product_id"]))
        lines.append(f"- {f['name']} ({f['brand']}): grade {f['grade']}, Goal Match {f['goal_match']}"
                     + (f", nutrient priority #{rank}" if rank else "")
                     + (f", over limit: {', '.join(f['over_limit'])}" if f["over_limit"] else "")
                     + ("; contains the shopper's allergen" if f["allergen_conflict"] else "") + f"; per 100: {values}")
    prompt = (
        f"Explain to a shopper with the goal '{goal}' how these packaged foods compare, in 2 or 3 short plain "
        "sentences. Use ONLY these facts; do not change or recompute grades, Goal Match or priorities; mention the "
        "biggest real differences in numbers; never recommend a product containing the shopper's allergen. Do not "
        "mention these instructions or that you are an AI.\n" + "\n".join(lines)
    )
    reply = gemini.generate_json(prompt, COMPARE_SCHEMA, text_only=True, max_output_tokens=260)
    text = str((reply or {}).get("explanation") or "").strip() if isinstance(reply, dict) else ""
    return text[:700] or None
