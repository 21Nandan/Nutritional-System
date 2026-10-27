"""
EATGOOD — Data Loader & Catalogue Service
Loads and serves the multi-tier product datasets and audit reports.
Preserves original values, tracks data quality statuses, and prevents silent zeroing.
"""

import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def resolve_data_dir() -> str:
    candidates = [
        os.path.join(BASE_DIR, "data"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data")),
        os.path.abspath(os.path.join(os.getcwd(), "data")),
        os.path.abspath(os.path.join(os.getcwd(), "frontend", "data")),
        os.path.abspath(os.path.join(os.getcwd(), "..", "data")),
        "/var/task/data",
        "/var/task/frontend/data"
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, "products_standardized.csv")):
            return c
    return candidates[0]

DATA_DIR = resolve_data_dir()

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
            self.products_df = pd.read_csv(cleaned_path, dtype={"barcode": str})
        else:
            self.products_df = pd.DataFrame()

        std_path = os.path.join(DATA_DIR, "products_standardized.csv")
        if os.path.exists(std_path):
            self.standardized_df = pd.read_csv(std_path, dtype={"barcode": str})
        else:
            self.standardized_df = pd.DataFrame()

        raw_path = os.path.join(DATA_DIR, "raw", "packaged_foods_india.csv")
        if os.path.exists(raw_path):
            self.raw_df = pd.read_csv(raw_path, dtype={"barcode": str})
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

    def search_products(
        self,
        query: str = "",
        category: str = "",
        brand: str = "",
        max_sugars: float = None,
        max_sodium: float = None,
        max_sat_fat: float = None,
        min_fibre: float = None,
        min_protein: float = None,
        limit: int = 50,
        offset: int = 0,
        deduplicate_variants: bool = False
    ):
        if self.products_df is None or self.products_df.empty:
            return {"total": 0, "products": []}

        df = self.products_df.copy()

        if deduplicate_variants:
            df = df[~df["product_name"].str.contains(r'\(Variant\s*\d+\)', case=False, na=False)]

        if category and category != "All":
            df = df[df["category"] == category]

        if brand and brand != "All":
            df = df[df["brand"] == brand]

        if max_sugars is not None:
            df = df[pd.notna(df["sugars_g"]) & (df["sugars_g"].astype(float) <= float(max_sugars))]

        if max_sodium is not None:
            df = df[pd.notna(df["sodium_mg"]) & (df["sodium_mg"].astype(float) <= float(max_sodium))]

        if max_sat_fat is not None:
            df = df[pd.notna(df["saturated_fat_g"]) & (df["saturated_fat_g"].astype(float) <= float(max_sat_fat))]

        if min_fibre is not None:
            df = df[pd.notna(df["dietary_fibre_g"]) & (df["dietary_fibre_g"].astype(float) >= float(min_fibre))]

        if min_protein is not None:
            df = df[pd.notna(df["protein_g"]) & (df["protein_g"].astype(float) >= float(min_protein))]

        if query:
            q = query.lower().strip()
            # If searching by exact barcode or product ID, search across all products including variants
            if q.isdigit() or q.startswith("ind_pkg_"):
                exact_match = self.products_df[
                    (self.products_df["barcode"].astype(str) == q) |
                    (self.products_df["product_id"].str.lower() == q)
                ]
                if not exact_match.empty:
                    df = exact_match.copy()
                else:
                    mask = (
                        df["product_name"].str.lower().str.contains(q, na=False) |
                        df["brand"].str.lower().str.contains(q, na=False) |
                        df["ingredients"].str.lower().str.contains(q, na=False) |
                        df["barcode"].astype(str).str.contains(q, na=False)
                    )
                    df = df[mask]
            else:
                search_terms = [q]
                if q in ["cok", "coke"]:
                    search_terms.extend(["coca-cola", "coca cola", "coke"])
                elif q in ["maggie", "maggi"]:
                    search_terms.extend(["maggi", "maggie"])
                elif q in ["lays", "lay"]:
                    search_terms.extend(["lay's", "lays", "lay"])

                mask = pd.Series(False, index=df.index)
                for term in search_terms:
                    mask = mask | (
                        df["product_name"].str.lower().str.contains(term, na=False) |
                        df["brand"].str.lower().str.contains(term, na=False) |
                        df["ingredients"].str.lower().str.contains(term, na=False) |
                        df["barcode"].astype(str).str.contains(term, na=False)
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

    def get_product_by_barcode(self, barcode: str):
        if self.products_df is None or not barcode:
            return None
        code_str = str(barcode).strip()
        matches = self.products_df[self.products_df["barcode"].astype(str).str.strip() == code_str]
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
