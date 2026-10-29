"""
EATGOOD — SQLite storage for caches and unmoderated user contributions.

No personal data is stored here: profiles, saved products and history live in the
visitor's own browser. On serverless hosts the database lives in /tmp, which is
per-instance and ephemeral, so everything here must be safe to lose.
"""

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from backend.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS external_products_cache (
    barcode TEXT PRIMARY KEY,
    product_data TEXT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ext_cache_expires ON external_products_cache(expires_at);

CREATE TABLE IF NOT EXISTS user_contributions (
    submission_id TEXT PRIMARY KEY,
    barcode TEXT NOT NULL,
    product_name TEXT NOT NULL,
    brand TEXT,
    category TEXT NOT NULL,
    sub_category TEXT,
    serving_size REAL,
    serving_size_unit TEXT,
    measurement_basis TEXT NOT NULL,
    nutrition_data TEXT NOT NULL,
    ingredients TEXT,
    allergens_declared TEXT,
    review_status TEXT NOT NULL,
    submission_notes TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_contrib_barcode ON user_contributions(barcode);
"""


def _now() -> datetime:
    return datetime.now(UTC)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Opens a connection, commits on success, rolls back on error and always closes."""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 5000;")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def check_db() -> None:
    """Raises if the database is not reachable or the schema is missing."""
    with get_connection() as conn:
        conn.execute("SELECT 1 FROM external_products_cache LIMIT 1").fetchall()
        conn.execute("SELECT 1 FROM user_contributions LIMIT 1").fetchall()


# --- External Products Cache (Open Food Facts) ---

def get_cached_lookup(barcode: str) -> dict | None:
    """Returns {"status": "success"|"not_found", "product": dict|None} for an unexpired entry, else None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT status, product_data, expires_at FROM external_products_cache WHERE barcode = ?",
            (str(barcode).strip(),),
        ).fetchone()
    if row is None or row["expires_at"] < _now().isoformat():
        return None
    product = json.loads(row["product_data"]) if row["product_data"] else None
    return {"status": row["status"], "product": product}


def cache_barcode_product(
    barcode: str,
    product_data: dict | None,
    source: str = "openfoodfacts",
    status: str = "success",
    ttl_hours: int = 168,
) -> None:
    now = _now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO external_products_cache (barcode, product_data, source, status, cached_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(barcode) DO UPDATE SET
                product_data=excluded.product_data,
                source=excluded.source,
                status=excluded.status,
                cached_at=excluded.cached_at,
                expires_at=excluded.expires_at
            """,
            (
                str(barcode).strip(),
                json.dumps(product_data) if product_data else None,
                source,
                status,
                now.isoformat(),
                (now + timedelta(hours=ttl_hours)).isoformat(),
            ),
        )


# --- User Product Contributions (unmoderated) ---

def record_user_contribution(contribution: dict) -> str:
    sub_id = f"sub_{uuid.uuid4().hex[:12]}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_contributions (
                submission_id, barcode, product_name, brand, category, sub_category,
                serving_size, serving_size_unit, measurement_basis, nutrition_data,
                ingredients, allergens_declared, review_status, submission_notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sub_id,
                contribution["barcode"],
                contribution["product_name"],
                contribution.get("brand"),
                contribution["category"],
                contribution.get("sub_category"),
                contribution.get("serving_size"),
                contribution.get("serving_size_unit"),
                contribution["measurement_basis"],
                json.dumps(contribution["nutrition_data"]),
                contribution.get("ingredients"),
                contribution.get("allergens_declared"),
                "pending_review",
                contribution.get("submission_notes"),
                _now().isoformat(),
            ),
        )
    return sub_id


def get_user_contribution_by_barcode(barcode: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_contributions WHERE barcode = ? ORDER BY created_at DESC LIMIT 1",
            (str(barcode).strip(),),
        ).fetchone()
    if row is None:
        return None
    record = dict(row)
    record["nutrition_data"] = json.loads(record["nutrition_data"])
    return record
