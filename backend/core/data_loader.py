"""
EATGOOD — Data Loader & Catalogue Service
Loads and serves the multi-tier product datasets and audit reports.
Preserves original values, tracks data quality statuses, and prevents silent zeroing.
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from backend.config import DATA_DIR
from backend.core.standards_registry import nutrient_flags

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

REQUIRED_CATALOGUE_COLUMNS = [
    "product_id", "product_name", "brand", "category", "sub_category",
    "serving_size", "serving_size_unit", "measurement_basis",
    "energy_kcal", "sugars_g", "sodium_mg", "saturated_fat_g",
    "ingredients", "allergens_declared", "barcode", "data_source", "data_confidence_status",
]
IMAGE_COLUMNS = ["image_url", "image_small_url", "image_source", "matching_method", "review_status"]


class CatalogueLoadError(RuntimeError):
    """Raised when the bundled catalogue cannot be loaded. The app must not start without it."""


def _read_required_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.is_file():
        raise CatalogueLoadError(f"Required data file is missing: {path}")
    df = pd.read_csv(path, **kwargs)
    if df.empty:
        raise CatalogueLoadError(f"Required data file is empty: {path}")
    return df


class DataLoaderService:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.manifest = self._load_manifest()
        self.products_df = self._load_catalogue()
        self.quality_report_df = _read_required_csv(data_dir / "data_quality_report.csv")
        self.nutrition_review_df = _read_required_csv(data_dir / "nutrition_review.csv")
        self.serving_review_df = _read_required_csv(data_dir / "serving_size_review.csv")

    def _load_manifest(self) -> dict:
        path = self.data_dir / "dataset_manifest.json"
        if not path.is_file():
            raise CatalogueLoadError(f"Dataset manifest is missing: {path}")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _load_catalogue(self) -> pd.DataFrame:
        df = _read_required_csv(self.data_dir / "products_cleaned.csv", dtype={"barcode": str})
        missing_cols = [c for c in REQUIRED_CATALOGUE_COLUMNS if c not in df.columns]
        if missing_cols:
            raise CatalogueLoadError(f"Catalogue is missing columns: {missing_cols}")
        if df["product_id"].duplicated().any():
            raise CatalogueLoadError("Catalogue contains duplicate product_id values.")
        expected = self.manifest["catalogue_rows"]
        if len(df) != expected:
            raise CatalogueLoadError(f"Catalogue has {len(df)} rows but the manifest declares {expected}.")

        images = _read_required_csv(self.data_dir / "product_images.csv")
        unknown = set(images["product_id"]) - set(df["product_id"])
        if unknown:
            raise CatalogueLoadError(f"product_images.csv references unknown product_ids: {sorted(unknown)}")
        return df.merge(images[["product_id"] + IMAGE_COLUMNS], on="product_id", how="left")

    def dataset_info(self) -> dict:
        return {
            "dataset_version": self.manifest["dataset_version"],
            "provenance": self.manifest["provenance"],
            "provenance_note": self.manifest["provenance_note"],
            "catalogue_rows": len(self.products_df),
            "products_with_images": int(self.products_df["image_url"].notna().sum()),
            "categories": sorted(self.products_df["category"].dropna().unique().tolist()),
        }

    def search_products(
        self,
        query: str = "",
        category: str = "",
        brand: str = "",
        max_sugars: float | None = None,
        max_sodium: float | None = None,
        max_sat_fat: float | None = None,
        min_fibre: float | None = None,
        min_protein: float | None = None,
        has_image: bool | None = None,
        limit: int = 50,
        offset: int = 0,
        deduplicate_variants: bool = False
    ):
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
                    scores: dict = {}
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

                    matched["_relevance_score"] = pd.Series(scores)
                    df = matched.sort_values(by="_relevance_score", ascending=False)
                else:
                    df = matched

        total = len(df)
        records = df.iloc[offset:offset+limit].replace({np.nan: None}).to_dict(orient="records")

        # Enrich local records with consistent local metadata and nutrition summaries
        for rec in records:
            rec["nutrient_flags"] = nutrient_flags(rec)
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
        matches = self.products_df[self.products_df["product_id"] == product_id]
        if matches.empty:
            return None
        return matches.iloc[0].replace({np.nan: None}).to_dict()

    def get_product_by_barcode(self, barcode: str):
        if not barcode:
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
        quality = self.quality_report_df.to_dict(orient="records")
        nutrition_flags = self.nutrition_review_df.replace({np.nan: None}).to_dict(orient="records")
        serving_flags = self.serving_review_df.replace({np.nan: None}).to_dict(orient="records")

        return {
            "dataset": self.dataset_info(),
            "total_products": len(self.products_df),
            "quality_summary": quality,
            "total_atwater_discrepancies": len(nutrition_flags),
            "atwater_discrepancies_sample": nutrition_flags[:25],
            "total_macro_serving_discrepancies": len(serving_flags),
            "macro_serving_discrepancies": serving_flags
        }

data_loader = DataLoaderService()
