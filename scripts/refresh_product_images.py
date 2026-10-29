#!/usr/bin/env python3
"""
Refresh data/product_images.csv from the public Open Food Facts API.

For each row, looks up the product by its image barcode on world.openfoodfacts.org and
records the current production front-image URLs plus the product name Open Food Facts
holds, so a person can confirm the photo matches the catalogue product.

Rows whose barcode is unknown or has no front image are removed from the CSV (the app
then shows its category placeholder); they are listed in the report so nothing
disappears silently. Run with --check to only print the report.

Usage: python scripts/refresh_product_images.py [--check]
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "product_images.csv"
API = "https://world.openfoodfacts.org/api/v3/product/{code}"
FIELDS = "code,product_name,brands,image_front_url,image_front_small_url"
USER_AGENT = "EATGOOD/1.1 (+https://github.com/21Nandan/Nutritional-System)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report only; do not rewrite the CSV")
    args = parser.parse_args()

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "off_product_name" not in fieldnames:
        fieldnames.append("off_product_name")

    kept, dropped = [], []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20) as client:
        for row in rows:
            code = row["image_barcode"]
            response = client.get(API.format(code=code), params={"fields": FIELDS})
            data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            product = data.get("product") or {}
            front = product.get("image_front_url")
            report = {
                "product_id": row["product_id"],
                "catalogue_name": row["product_name"],
                "barcode": code,
                "http": response.status_code,
                "off_name": product.get("product_name"),
                "off_brands": product.get("brands"),
                "front": front,
            }
            print(json.dumps(report, ensure_ascii=False))
            if response.status_code == 200 and front:
                row["image_url"] = front
                row["image_small_url"] = product.get("image_front_small_url") or front
                row["off_product_name"] = f"{product.get('brands') or ''} {product.get('product_name') or ''}".strip()
                kept.append(row)
            else:
                dropped.append(report)
            time.sleep(0.7)  # stay well under Open Food Facts' rate limits

    print(f"SUMMARY kept={len(kept)} dropped={len(dropped)}", file=sys.stderr)
    for d in dropped:
        print(f"DROPPED {d['product_id']} {d['catalogue_name']} (barcode {d['barcode']}, HTTP {d['http']})", file=sys.stderr)

    if not args.check:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(kept)
    return 0


if __name__ == "__main__":
    sys.exit(main())
