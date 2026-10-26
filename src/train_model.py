#!/usr/bin/env python3
"""
EATGOOD — Experimental Recommender Model Training Script
Trains a machine learning classifier on the 1,500 simulated user-product personalization examples.
Documents model limitations and outputs experimental metadata.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import classification_report, accuracy_score

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(BASE_DIR, "data", "personalization_examples.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "eatgood_model.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

os.makedirs(MODEL_DIR, exist_ok=True)

def train_eatgood_model():
    print(f"Loading personalization training data from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} simulated user-product records.")

    # Target variable: is_suitable_label (1 = Suitable, 0 = Not Suitable)
    y = df["is_suitable_label"]

    feature_cols = [
        "user_goal", "dietary_preference", "energy_kcal", "sugars_g",
        "sodium_mg", "protein_g", "dietary_fibre_g", "saturated_fat_g",
        "allergen_conflict", "preference_conflict"
    ]
    X = df[feature_cols].copy()

    # Preprocessing
    categorical_features = ["user_goal", "dietary_preference"]
    numeric_features = [
        "energy_kcal", "sugars_g", "sodium_mg", "protein_g",
        "dietary_fibre_g", "saturated_fat_g", "allergen_conflict", "preference_conflict"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features)
        ]
    )

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        random_state=42
    )

    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", clf)
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training set: {len(X_train)} samples, Test set: {len(X_test)} samples.")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    test_acc = accuracy_score(y_test, y_pred)
    print(f"\n--- Model Evaluation ---")
    print(f"Simulated Test Accuracy: {test_acc * 100:.2f}%")
    print(classification_report(y_test, y_pred, target_names=["Not Suitable", "Suitable"]))

    # Save model artifact
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Saved model artifact to: {MODEL_PATH}")

    # Save model transparency metadata
    metadata = {
        "model_name": "EATGOOD Personalization Matcher Prototype",
        "version": "1.0.0-experimental",
        "model_type": "Scikit-Learn RandomForestClassifier",
        "training_dataset": "data/personalization_examples.csv (1,500 simulated user-product pairs, 100 simulated users)",
        "features_used": feature_cols,
        "test_accuracy_simulated": float(test_acc),
        "scientific_disclaimer": (
            "IMPORTANT: High accuracy on this test set is an artifact of evaluation on synthetically generated rule-based labels. "
            "It does NOT represent clinical or real-world predictive validity. The model serves as an experimental architectural component "
            "demonstrating ML service integration alongside deterministic nutrition rules."
        ),
        "fallback_mechanism": "Deterministic Rule-Based Assessment Engine (Layer 1 + Layer 2)",
        "validation_status": "Experimental Prototype — Not Clinically Validated"
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved model metadata to: {METADATA_PATH}")

if __name__ == "__main__":
    train_eatgood_model()
