"""
Patterns across a set of products (a comparison or a basket), from their stated values and EATGOOD's
own results. Plain arithmetic: no scores are made or changed here.
"""

from typing import Any

from backend.core.nutrition_scoring import run_full_product_assessment

NUTRIENTS = [("sugars", "sugar", "sugars_g", "g"), ("sodium", "sodium", "sodium_mg", "mg"),
             ("saturated_fat", "saturated fat", "saturated_fat_g", "g"), ("energy", "calories", "energy_kcal", "kcal")]


def basket_summary(products: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    """{"facts": [...per product...], "patterns": [plain sentences]} for 2 or more products."""
    facts = []
    for p in products:
        a = run_full_product_assessment(p, profile)
        l1, l2 = a.get("layer1_general", {}), a.get("layer2_personalized", {})
        over = [k for k, v in (l1.get("key_contributing_nutrients") or {}).items() if (v.get("points") or 0) < 0]
        facts.append({
            "product_id": p.get("product_id"), "name": p.get("product_name"), "brand": p.get("brand"),
            "category": p.get("category"), "grade": l1.get("grade"), "goal_match": l2.get("personalized_score"),
            "allergen_conflict": bool(l2.get("has_critical_allergen_conflict")), "over_limit": over,
            **{key: p.get(key) for _, _, key, _ in NUTRIENTS},
            "protein_g": p.get("protein_g"), "dietary_fibre_g": p.get("dietary_fibre_g"),
        })
    n = len(facts)
    patterns: list[str] = []
    for code, label, key, unit in NUTRIENTS:
        count = sum(1 for f in facts if code in f["over_limit"])
        if count >= 2 or (count == 1 and n == 2):
            patterns.append(f"{count} of {n} are over the {label} limit for their category.")
        values = [f[key] for f in facts if isinstance(f[key], (int, float))]
        if code in ("sugars", "sodium") and len(values) == n and n >= 3:
            avg = sum(values) / n
            patterns.append(f"Average {label}: {avg:.0f} {unit} per 100." if unit == "mg" else f"Average {label}: {avg:.1f} {unit} per 100.")
    low = [f for f in facts if f["grade"] in ("D", "E")]
    if low and len(low) >= max(2, n // 2):
        patterns.append(f"{len(low)} of {n} have a nutrition grade of D or E.")
    conflicts = [f["name"] for f in facts if f["allergen_conflict"]]
    if conflicts:
        patterns.append(f"Contains an allergen from your profile: {', '.join(conflicts)}.")
    return {"facts": facts, "patterns": patterns}
