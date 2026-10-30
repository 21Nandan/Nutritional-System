"""
Slots for separately trained models: product-category classification, nutrition-data quality and
product recommendations.

No model is trained or bundled yet. Each slot loads a model file from MODELS_DIR only if it exists;
otherwise its function returns None (or nothing) and the app keeps using its rules. Nothing here
pretends a model exists.

Model file format (JSON, so serving needs only the standard library and NumPy-free Python):
  category_model.json  {"type": "linear_text", "version": "...", "labels": [...], "vocabulary": {token: index},
                        "weights": [[...per label...] per token], "bias": [...], "min_confidence": 0.6}
  quality_model.json   {"type": "linear_features", "version": "...", "features": [...], "weights": [...],
                        "bias": 0.0, "threshold": 0.5, "message": "..."}
  recommender_model.json  reserved; see models/README.md.
Train them offline (e.g. scripts in scripts/training/) and drop the files into MODELS_DIR.
"""

import json
import logging
import math
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger("eatgood")

MODELS_DIR = Path(os.environ.get("EATGOOD_MODELS_DIR") or Path(__file__).resolve().parents[2] / "models")


@lru_cache(maxsize=None)
def _load(name: str) -> dict[str, Any] | None:
    path = MODELS_DIR / name
    if not path.is_file():
        return None
    try:
        model = json.loads(path.read_text())
    except (OSError, ValueError):
        logger.warning("model file %s couldn't be read; using rules instead", name)
        return None
    logger.info("loaded model %s (version %s)", name, model.get("version"))
    return model


def status() -> dict[str, bool]:
    """Which trained models are installed."""
    return {slot: _load(f"{slot}_model.json") is not None for slot in ("category", "quality", "recommender")}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]{3,}", text.lower())


def predict_category(product_name: str | None, ingredients: str | None) -> str | None:
    """The category the trained classifier is confident about, or None (no model, or not confident)."""
    model = _load("category_model.json")
    if not model or model.get("type") != "linear_text":
        return None
    vocab, weights, bias, labels = model["vocabulary"], model["weights"], model["bias"], model["labels"]
    scores = list(bias)
    for token in _tokens(f"{product_name or ''} {ingredients or ''}"):
        row = vocab.get(token)
        if row is not None:
            scores = [s + w for s, w in zip(scores, weights[row])]
    top = max(scores)
    exps = [math.exp(s - top) for s in scores]
    best = max(range(len(labels)), key=lambda i: scores[i])
    confidence = exps[best] / sum(exps)
    return labels[best] if confidence >= model.get("min_confidence", 0.6) else None


def quality_model_flags(product: dict[str, Any]) -> list[dict[str, str]]:
    """A flag from the trained quality model when it scores the record as suspicious; [] otherwise."""
    model = _load("quality_model.json")
    if not model or model.get("type") != "linear_features":
        return []
    total = model.get("bias", 0.0)
    for feature, weight in zip(model["features"], model["weights"]):
        try:
            total += weight * float(product.get(feature) or 0)
        except (TypeError, ValueError):
            continue
    probability = 1 / (1 + math.exp(-total))
    if probability < model.get("threshold", 0.5):
        return []
    return [{"code": "model_suspicious", "message": model.get("message", "These values look unusual for this kind of product.")}]
