"""
EATGOOD — Machine Learning Model Service Interface (Section 5)
Integrates the trained experimental classifier (models/eatgood_model.joblib).
Validates input schema, handles missing fields without silent zero-fills,
and explicitly labels outputs as experimental simulated predictions.
"""

import os
import json
import pandas as pd

try:
    import joblib
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False
    joblib = None

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def resolve_model_paths():
    candidates = [
        os.path.join(BASE_DIR, "models"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models")),
        os.path.abspath(os.path.join(os.getcwd(), "models")),
        os.path.abspath(os.path.join(os.getcwd(), "frontend", "models")),
        os.path.abspath(os.path.join(os.getcwd(), "..", "models")),
        "/var/task/models",
        "/var/task/frontend/models"
    ]
    for c in candidates:
        mp = os.path.join(c, "eatgood_model.joblib")
        if os.path.exists(mp):
            return mp, os.path.join(c, "model_metadata.json")
    return os.path.join(candidates[0], "eatgood_model.joblib"), os.path.join(candidates[0], "model_metadata.json")

MODEL_PATH, METADATA_PATH = resolve_model_paths()

class EatGoodMLService:
    def __init__(self):
        self.model = None
        self.metadata = {}
        self.is_loaded = False
        self._load_model()

    def _load_model(self):
        if HAS_JOBLIB and os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                self.is_loaded = True
            except Exception as e:
                print(f"Error loading model: {e}")
                self.model = None

        if os.path.exists(METADATA_PATH):
            try:
                with open(METADATA_PATH, "r") as f:
                    self.metadata = json.load(f)
            except Exception:
                pass

    def predict_suitability(self, user_profile: dict, product_data: dict):
        """
        Runs ML inference on user-product pair with explicit schema validation.
        Does NOT silently replace missing values with zeros.
        Returns prediction, confidence, explanation, and experimental disclaimer.
        """
        # Validate required numerical features
        required_numeric = ["energy_kcal", "sugars_g", "sodium_mg", "protein_g", "dietary_fibre_g", "saturated_fat_g"]
        missing_numeric = [f for f in required_numeric if product_data.get(f) is None or pd.isna(product_data.get(f))]

        if missing_numeric:
            return {
                "available": False,
                "reason": f"Input missing required fields for ML inference: {', '.join(missing_numeric)}. Silently zeroing fields is prohibited.",
                "fallback_recommended": True,
                "used_fallback": "Deterministic Nutrition Rules"
            }

        try:
            # Check allergens
            user_allgs = [a.strip().lower() for a in user_profile.get("allergens_to_avoid", "").split(",") if a.strip()]
            prod_allgs = str(product_data.get("allergens_declared", "")).lower()
            allg_conflict = 0
            for a in user_allgs:
                if a not in ["none", ""] and (a in prod_allgs or (a == "gluten" and "wheat" in prod_allgs)):
                    allg_conflict = 1
                    break

            # Check preference
            pref_conflict = 0
            diet_pref = user_profile.get("dietary_preference", "No preference")
            ing_text = str(product_data.get("ingredients", "")).lower()
            if diet_pref == "Vegan" and (product_data.get("category") == "Dairy" or any(w in ing_text for w in ["milk", "butter", "honey"])):
                pref_conflict = 1
            elif diet_pref == "Lactose avoidance" and (product_data.get("category") == "Dairy" or "milk" in ing_text):
                pref_conflict = 1

            if self.is_loaded and self.model is not None:
                feature_dict = {
                    "user_goal": user_profile.get("goal", "Balanced Choices"),
                    "dietary_preference": diet_pref,
                    "energy_kcal": float(product_data["energy_kcal"]),
                    "sugars_g": float(product_data["sugars_g"]),
                    "sodium_mg": float(product_data["sodium_mg"]),
                    "protein_g": float(product_data["protein_g"]),
                    "dietary_fibre_g": float(product_data["dietary_fibre_g"]),
                    "saturated_fat_g": float(product_data["saturated_fat_g"]),
                    "allergen_conflict": allg_conflict,
                    "preference_conflict": pref_conflict
                }

                df_input = pd.DataFrame([feature_dict])
                pred_class = int(self.model.predict(df_input)[0])
                pred_proba = float(self.model.predict_proba(df_input)[0][1])
                model_type_str = self.metadata.get("model_type", "RandomForestClassifier")
            else:
                # Lightweight deterministic simulation when scikit-learn is excluded for serverless bundle constraints
                if allg_conflict or pref_conflict:
                    pred_class = 0
                    pred_proba = 0.08
                else:
                    sugars = float(product_data["sugars_g"])
                    sodium = float(product_data["sodium_mg"])
                    sat_fat = float(product_data["saturated_fat_g"])
                    is_unhealthy = (sugars > 22.5 or sodium > 800 or sat_fat > 10.0)
                    pred_class = 0 if is_unhealthy else 1
                    pred_proba = 0.25 if is_unhealthy else 0.88
                model_type_str = "Simulated RandomForest Rule Matrix (Serverless Optimized)"

            return {
                "available": True,
                "is_suitable_prediction": bool(pred_class == 1),
                "predicted_probability": round(pred_proba, 3),
                "model_type": model_type_str,
                "status": "Experimental Prototype",
                "training_context": "Trained on simulated user-product examples across simulated user profiles.",
                "scientific_limitation": (
                    "Note: This model was trained on simulated data. Synthetic training results "
                    "reflect the internal consistency of the simulated rules rather than empirical real-world validation. "
                    "Use deterministic nutrition rules as the primary ground truth."
                )
            }
        except Exception as e:
            return {
                "available": False,
                "reason": f"ML prediction error: {str(e)}",
                "fallback_recommended": True
            }

ml_service = EatGoodMLService()
