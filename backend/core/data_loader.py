"""
EATGOOD — Data Loader & Catalogue Service
Loads and serves the multi-tier product datasets and audit reports.
Preserves original values, tracks data quality statuses, and prevents silent zeroing.
"""

import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")

class DataLoaderService:
    def __init__(self):
        self.products_df = None
        self.standardized_df = None
        self.raw_df = None
        self.quality_report_df = None
        self.nutrition_review_df = None
        self.serving_review_df = None
        self.users_df = None
        self.load_all()

    def load_all(self):
        cleaned_path = os.path.join(DATA_DIR, "products_cleaned.csv")
        if os.path.exists(cleaned_path):
            self.products_df = pd.read_csv(cleaned_path)
        else:
            self.products_df = pd.DataFrame()

        std_path = os.path.join(DATA_DIR, "products_standardized.csv")
        if os.path.exists(std_path):
            self.standardized_df = pd.read_csv(std_path)
        else:
            self.standardized_df = pd.DataFrame()

        raw_path = os.path.join(DATA_DIR, "raw", "packaged_foods_india.csv")
        if os.path.exists(raw_path):
            self.raw_df = pd.read_csv(raw_path)
        else:
            self.raw_df = pd.DataFrame()

        q_path = os.path.join(DATA_DIR, "data_quality_report.csv")
        if os.path.exists(q_path):
            self.quality_report_df = pd.read_csv(q_path)

        nr_path = os.path.join(DATA_DIR, "nutrition_review.csv")
        if os.path.exists(nr_path):
            self.nutrition_review_df = pd.read_csv(nr_path)

        sr_path = os.path.join(DATA_DIR, "serving_size_review.csv")
        if os.path.exists(sr_path):
            self.serving_review_df = pd.read_csv(sr_path)

        users_path = os.path.join(DATA_DIR, "users.csv")
        if os.path.exists(users_path):
            self.users_df = pd.read_csv(users_path)

    def search_products(self, query: str = "", category: str = "", brand: str = "", limit: int = 50, offset: int = 0):
        if self.products_df is None or self.products_df.empty:
            return {"total": 0, "products": []}

        df = self.products_df.copy()

        if category and category != "All":
            df = df[df["category"] == category]

        if brand and brand != "All":
            df = df[df["brand"] == brand]

        if query:
            q = query.lower()
            mask = (
                df["product_name"].str.lower().str.contains(q, na=False) |
                df["brand"].str.lower().str.contains(q, na=False) |
                df["ingredients"].str.lower().str.contains(q, na=False) |
                df["barcode"].astype(str).str.contains(q, na=False)
            )
            df = df[mask]

        total = len(df)
        records = df.iloc[offset:offset+limit].replace({np.nan: None}).to_dict(orient="records")
        return {"total": total, "products": records}

    def get_product_by_id(self, product_id: str):
        if self.products_df is None:
            return None
        matches = self.products_df[self.products_df["product_id"] == product_id]
        if matches.empty:
            return None
        return matches.iloc[0].replace({np.nan: None}).to_dict()

    def get_audit_metrics(self):
        quality = self.quality_report_df.to_dict(orient="records") if self.quality_report_df is not None else []
        nutrition_flags = self.nutrition_review_df.replace({np.nan: None}).to_dict(orient="records") if self.nutrition_review_df is not None else []
        serving_flags = self.serving_review_df.replace({np.nan: None}).to_dict(orient="records") if self.serving_review_df is not None else []
        
        return {
            "total_products": len(self.products_df) if self.products_df is not None else 0,
            "quality_summary": quality,
            "total_atwater_discrepancies": len(nutrition_flags),
            "atwater_discrepancies_sample": nutrition_flags[:25],
            "total_macro_serving_discrepancies": len(serving_flags),
            "macro_serving_discrepancies": serving_flags
        }

data_loader = DataLoaderService()
