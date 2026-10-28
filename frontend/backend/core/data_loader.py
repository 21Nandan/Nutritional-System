"""
EATGOOD — Data Loader & Catalogue Service
Loads and serves the multi-tier product datasets and audit reports.
Preserves original values, tracks data quality statuses, and prevents silent zeroing.
"""

import os
import re
import pandas as pd
import numpy as np

# Common stem and synonym expansions for Indian packaged foods search
COMMON_STEMS = {
    "choco": ["choco", "choc", "chocolate", "chocolates"],
    "chocolate": ["choco", "choc", "chocolate", "chocolates"],
    "biscuit": ["biscuit", "biscuits", "cookie", "cookies"],
    "biscuits": ["biscuit", "biscuits", "cookie", "cookies"],
    "cookie": ["cookie", "cookies", "biscuit", "biscuits"],
    "cookies": ["cookie", "cookies", "biscuit", "biscuits"],
    "coke": ["coke", "coca-cola", "coca cola"],
    "cola": ["coca-cola", "coca cola", "cola", "coke"],
    "maggi": ["maggi", "maggie", "nestle"],
    "maggie": ["maggi", "maggie", "nestle"],
    "lays": ["lay's", "lays", "lay"],
    "lay": ["lay's", "lays", "lay"],
    "chip": ["chip", "chips", "crisp", "crisps", "wafers"],
    "chips": ["chip", "chips", "crisp", "crisps", "wafers"],
    "noodle": ["noodle", "noodles"],
    "noodles": ["noodle", "noodles"],
    "butter": ["butter", "makkhan"],
    "tea": ["tea", "chai"],
    "chai": ["tea", "chai"],
    "coffee": ["coffee", "cafe"],
    "atta": ["atta", "flour", "wheat"],
    "flour": ["atta", "flour", "maida"],
    "dahi": ["dahi", "curd", "yogurt", "yoghurt"],
    "curd": ["dahi", "curd", "yogurt", "yoghurt"],
    "yogurt": ["dahi", "curd", "yogurt", "yoghurt"],
    "paneer": ["paneer", "cottage cheese"],
    "milk": ["milk", "dairy"],
    "namkeen": ["namkeen", "bhujia", "sev", "mixture"],
    "bhujia": ["bhujia", "namkeen", "sev"],
    "sev": ["sev", "bhujia", "namkeen"],
    "haldiram": ["haldiram", "haldirams", "haldiram's"],
    "haldirams": ["haldiram", "haldirams", "haldiram's"],
    "parle": ["parle", "parle-g", "parleg"],
    "cadbury": ["cadbury", "cadburys"],
    "britannia": ["britannia", "good day"],
}

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

        # Seed curated authentic Open Food Facts images if table is fresh
        try:
            from backend.core.image_enrichment import seed_initial_curated_images
            seed_initial_curated_images()
        except Exception:
            pass

        # Merge enriched product images from SQLite registry
        try:
            from backend.database import get_all_product_images
            image_records = get_all_product_images()
            if image_records and self.products_df is not None and not self.products_df.empty:
                img_df = pd.DataFrame(list(image_records.values()))
                cols_to_merge = [
                    "product_id", "image_url", "image_small_url",
                    "image_ingredients_url", "image_nutrition_url",
                    "image_source", "matching_method", "review_status"
                ]
                cols_present = [c for c in cols_to_merge if c in img_df.columns]
                # Drop existing image cols if any to avoid duplication
                for c in ["image_url", "image_small_url", "image_ingredients_url", "image_nutrition_url", "image_source", "matching_method", "review_status"]:
                    if c in self.products_df.columns:
                        self.products_df.drop(columns=[c], inplace=True)
                self.products_df = self.products_df.merge(img_df[cols_present], on="product_id", how="left")
        except Exception as e:
            print(f"Notice: Image merge failed in DataLoader: {e}")

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
        has_image: bool = None,
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

        if has_image is True:
            if "image_url" in df.columns:
                df = df[df["image_url"].notna() & (df["image_url"].astype(str).str.strip() != "") & (df["image_url"].astype(str) != "None")]
        elif has_image is False:
            if "image_url" in df.columns:
                df = df[df["image_url"].isna() | (df["image_url"].astype(str).str.strip() == "") | (df["image_url"].astype(str) == "None")]

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
                # Multi-token conjunctive search with stem expansion and fallback
                raw_tokens = [t for t in re.split(r"[\s,\-_/]+", q) if len(t) >= 2]
                if not raw_tokens and q:
                    raw_tokens = [q]

                cols_to_check = ["product_name", "brand", "category", "sub_category", "ingredients"]
                existing_cols = [c for c in cols_to_check if c in df.columns]

                token_masks = []
                for token in raw_tokens:
                    variants = COMMON_STEMS.get(token, [token])
                    t_mask = pd.Series(False, index=df.index)
                    for var in variants:
                        for col in existing_cols:
                            t_mask = t_mask | df[col].astype(str).str.lower().str.contains(re.escape(var), na=False)
                    token_masks.append(t_mask)

                # First attempt: Conjunction (all query tokens matched across fields)
                conjunction = pd.Series(True, index=df.index)
                for t_mask in token_masks:
                    conjunction = conjunction & t_mask

                matched = df[conjunction].copy()

                # Fallback: if conjunction returned 0 and we have multiple tokens, try disjunction (any token matched)
                if matched.empty and len(token_masks) > 1:
                    disjunction = pd.Series(False, index=df.index)
                    for t_mask in token_masks:
                        disjunction = disjunction | t_mask
                    matched = df[disjunction].copy()

                if not matched.empty:
                    # Relevance scoring: reward exact matches, prefix matches, and name matches
                    scores = pd.Series(0, index=matched.index)
                    for idx, row in matched.iterrows():
                        score = 0
                        p_name = str(row.get("product_name", "")).lower()
                        p_brand = str(row.get("brand", "")).lower()
                        p_cat = str(row.get("category", "")).lower()

                        if q in p_name:
                            score += 100
                        if q in p_brand:
                            score += 80
                        if p_name.startswith(q) or q.startswith(p_name):
                            score += 40

                        for token in raw_tokens:
                            variants = COMMON_STEMS.get(token, [token])
                            if any(v in p_name for v in variants):
                                score += 30
                            if any(v in p_brand for v in variants):
                                score += 25
                            if any(v in p_cat for v in variants):
                                score += 15

                        if pd.notna(row.get("image_url")) and str(row.get("image_url")).strip() not in ["", "None"]:
                            score += 10

                        scores[idx] = score

                    matched["_relevance_score"] = scores
                    df = matched.sort_values(by="_relevance_score", ascending=False)
                else:
                    df = matched

        total = len(df)
        records = df.iloc[offset:offset+limit].replace({np.nan: None}).to_dict(orient="records")

        # Enrich local records with consistent local metadata and nutrition summaries
        for rec in records:
            rec["is_local"] = True
            rec["source"] = "Local Indian Catalogue"
            rec["nutrition_summary"] = {
                "energy_kcal": rec.get("energy_kcal"),
                "sugars_g": rec.get("sugars_g"),
                "protein_g": rec.get("protein_g"),
                "sodium_mg": rec.get("sodium_mg"),
                "saturated_fat_g": rec.get("saturated_fat_g"),
                "serving_size": rec.get("serving_size"),
                "serving_size_unit": rec.get("serving_size_unit", "g")
            }

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
            if len(code_str) == 12:
                matches = self.products_df[self.products_df["barcode"].astype(str).str.strip() == f"0{code_str}"]
            elif len(code_str) == 13 and code_str.startswith("0"):
                matches = self.products_df[self.products_df["barcode"].astype(str).str.strip() == code_str[1:]]
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
