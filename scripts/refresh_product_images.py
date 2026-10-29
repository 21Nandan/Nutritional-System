#!/usr/bin/env python3
"""
Refresh data/product_images.csv from the public Open Food Facts API.

For each row, looks up the product by its image barcode on world.openfoodfacts.org and
records the current production front-image URLs plus the product name Open Food Facts
holds, so a person can confirm the photo matches the catalogue product.

Rows already pointing at the production image host are skipped unless --all is given.
Rows whose barcode Open Food Facts doesn't know, or that have no front image, are removed
(the app then shows its category placeholder) and listed in the report. Any other failure
(rate limit after retries, server error) stops the script without rewriting the CSV, so a
temporary problem never deletes data. Run with --check to only print the report.

Usage: python scripts/refresh_product_images.py [--check] [--all]
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
PRODUCTION_HOST = "https://images.openfoodfacts.org/"
REQUEST_INTERVAL_SECONDS = 6.5  # Open Food Facts allows about 10 product reads per minute per client
MAX_ATTEMPTS = 5


class LookupFailed(Exception):
    pass


def fetch(client: httpx.Client, code: str) -> httpx.Response:
    """GET one product, retrying on 429 and 5xx with the server's Retry-After or a growing delay."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = client.get(API.format(code=code), params={"fields": FIELDS})
        if response.status_code != 429 and response.status_code < 500:
            return response
        wait = float(response.headers.get("retry-after") or 15 * attempt)
        print(f"  {code}: HTTP {response.status_code}, retrying in {wait:.0f}s ({attempt}/{MAX_ATTEMPTS})", file=sys.stderr)
        time.sleep(wait)
    raise LookupFailed(f"{code}: still HTTP {response.status_code} after {MAX_ATTEMPTS} attempts")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report only; do not rewrite the CSV")
    parser.add_argument("--all", action="store_true", help="also re-check rows already on the production host")
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
            if not args.all and row["image_url"].startswith(PRODUCTION_HOST):
                kept.append(row)
                continue
            code = row["image_barcode"]
            try:
                response = fetch(client, code)
            except LookupFailed as exc:
                print(f"ERROR {exc}. The CSV was not changed.", file=sys.stderr)
                return 1
            product = response.json().get("product") or {} if response.status_code == 200 else {}
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
            elif response.status_code in (200, 404):
                dropped.append(report)
            else:
                print(f"ERROR {code}: unexpected HTTP {response.status_code}. The CSV was not changed.", file=sys.stderr)
                return 1
            time.sleep(REQUEST_INTERVAL_SECONDS)

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
