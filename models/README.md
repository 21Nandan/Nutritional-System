# Trained models (optional)

EATGOOD runs on rules. This folder is where separately trained models go; **none are included yet**.
`backend/core/ml_models.py` loads a file only if it is here, and falls back to the rules otherwise.

| File | Used for | Without it |
|---|---|---|
| `category_model.json` | Placing products whose category the keyword rules can't identify | Product is graded with the general method |
| `quality_model.json` | Extra "check these values" flag on suspicious nutrition records | Only the rule-based checks in `data_quality.py` |
| `recommender_model.json` | Reserved for ranking healthier alternatives | Rule-based ranking in `recommender.py` |

Models never change a grade or Goal Match; those come from the scoring rules.

## Formats

**category_model.json** (linear text classifier, e.g. TF-IDF + logistic regression exported to JSON)
```json
{"type": "linear_text", "version": "2026-11-01", "labels": ["Snacks", "Dairy", "..."],
 "vocabulary": {"namkeen": 0, "milk": 1}, "weights": [[0.9, -0.2], [-0.4, 1.3]], "bias": [0.0, 0.0],
 "min_confidence": 0.6}
```
`weights[i]` holds one weight per label for vocabulary token `i` (lower-case words of 3+ letters from
the product name and ingredients). Predictions below `min_confidence` are ignored.

**quality_model.json** (logistic model over nutrient fields)
```json
{"type": "linear_features", "version": "2026-11-01", "features": ["energy_kcal", "sodium_mg"],
 "weights": [0.001, 0.0004], "bias": -3.2, "threshold": 0.5,
 "message": "These values look unusual for this kind of product."}
```

## Training data
The Open Food Facts data export (https://world.openfoodfacts.org/data) has labelled categories and
nutrition values. Report held-out accuracy with any model you add.
