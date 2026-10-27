"""
EATGOOD — SQLite Local Database Service
Persists user profiles, analysis history, and saved products locally.
No transmission of sensitive personal information to third-party endpoints.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "data", "eatgood_app.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # User Profile table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE,
        name TEXT,
        goal TEXT,
        dietary_preference TEXT,
        allergens_to_avoid TEXT,
        age_group TEXT,
        activity_level TEXT,
        updated_at TIMESTAMP
    )
    """)

    # Analysis History table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT,
        product_name TEXT,
        brand TEXT,
        category TEXT,
        personalized_score INTEGER,
        general_grade TEXT,
        analysis_source TEXT,
        timestamp TIMESTAMP
    )
    """)

    # Saved Products table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_products (
        product_id TEXT PRIMARY KEY,
        product_name TEXT,
        brand TEXT,
        category TEXT,
        product_data TEXT,
        saved_at TIMESTAMP
    )
    """)
    for col in ['product_name', 'brand', 'category', 'product_data']:
        try:
            cursor.execute(f"ALTER TABLE saved_products ADD COLUMN {col} TEXT")
        except Exception:
            pass

    # Scan Sessions table (local OCR scan provenance)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_sessions (
        scan_id TEXT PRIMARY KEY,
        filename TEXT,
        image_path TEXT,
        ocr_engine TEXT,
        raw_text TEXT,
        status TEXT,
        extracted_data TEXT,
        confidence REAL,
        created_at TIMESTAMP
    )
    """)

    # External Products Cache table (Open Food Facts caching with TTL)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS external_products_cache (
        barcode TEXT PRIMARY KEY,
        product_data TEXT,
        source TEXT,
        status TEXT,
        cached_at TIMESTAMP,
        expires_at TIMESTAMP
    )
    """)

    # User Contributions table (Products submitted by users when not found)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_contributions (
        submission_id TEXT PRIMARY KEY,
        barcode TEXT,
        product_name TEXT,
        brand TEXT,
        category TEXT,
        sub_category TEXT,
        serving_size REAL,
        serving_size_unit TEXT,
        measurement_basis TEXT,
        nutrition_data TEXT,
        ingredients TEXT,
        allergens_declared TEXT,
        front_image_path TEXT,
        label_image_path TEXT,
        ingredients_image_path TEXT,
        review_status TEXT,
        submission_notes TEXT,
        created_at TIMESTAMP
    )
    """)

    # Insert default active profile if empty
    cursor.execute("SELECT COUNT(*) FROM user_profile")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO user_profile (user_id, name, goal, dietary_preference, allergens_to_avoid, age_group, activity_level, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "USR_DEFAULT",
            "Guest User",
            "Reduce Sugar",
            "Vegetarian",
            "None",
            "18-24",
            "Moderately active",
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()

def get_active_profile():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profile ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "user_id": "USR_DEFAULT",
        "name": "Guest User",
        "goal": "Balanced Choices",
        "dietary_preference": "No preference",
        "allergens_to_avoid": "",
        "age_group": "25-34",
        "activity_level": "Moderately active"
    }

def save_active_profile(profile_data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO user_profile (user_id, name, goal, dietary_preference, allergens_to_avoid, age_group, activity_level, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        name=excluded.name,
        goal=excluded.goal,
        dietary_preference=excluded.dietary_preference,
        allergens_to_avoid=excluded.allergens_to_avoid,
        age_group=excluded.age_group,
        activity_level=excluded.activity_level,
        updated_at=excluded.updated_at
    """, (
        profile_data.get("user_id", "USR_DEFAULT"),
        profile_data.get("name", "Guest User"),
        profile_data.get("goal", "Balanced Choices"),
        profile_data.get("dietary_preference", "No preference"),
        profile_data.get("allergens_to_avoid", ""),
        profile_data.get("age_group", "18-24"),
        profile_data.get("activity_level", "Moderately active"),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
    return get_active_profile()

def record_analysis_history(product_id: str, product_name: str, brand: str, category: str, score: int, grade: str, source: str = "Catalogue Search"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO analysis_history (product_id, product_name, brand, category, personalized_score, general_grade, analysis_source, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (product_id, product_name, brand, category, score, grade, source, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_recent_history(limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analysis_history ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def toggle_save_product(product_id: str, product_info: dict = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id FROM saved_products WHERE product_id = ?", (product_id,))
    exists = cursor.fetchone()
    if exists:
        cursor.execute("DELETE FROM saved_products WHERE product_id = ?", (product_id,))
        saved = False
    else:
        name = (product_info.get("product_name") or product_info.get("name")) if product_info else None
        brand = product_info.get("brand") if product_info else None
        category = product_info.get("category") if product_info else None
        data_json = json.dumps(product_info) if product_info else None

        cursor.execute("""
        INSERT INTO saved_products (product_id, product_name, brand, category, product_data, saved_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (product_id, name, brand, category, data_json, datetime.now().isoformat()))
        saved = True
    conn.commit()
    conn.close()
    return saved

def is_product_saved(product_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM saved_products WHERE product_id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row)

def get_saved_products_records():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, product_name, brand, category, product_data, saved_at FROM saved_products ORDER BY saved_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_saved_product(product_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM saved_products WHERE product_id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_saved_product_ids():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id FROM saved_products ORDER BY saved_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def record_scan_session(scan_id: str, filename: str, image_path: str, ocr_engine: str, raw_text: str, status: str, extracted_data: dict, confidence: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO scan_sessions (scan_id, filename, image_path, ocr_engine, raw_text, status, extracted_data, confidence, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(scan_id) DO UPDATE SET
        ocr_engine=excluded.ocr_engine,
        raw_text=excluded.raw_text,
        status=excluded.status,
        extracted_data=excluded.extracted_data,
        confidence=excluded.confidence
    """, (
        scan_id,
        filename,
        image_path,
        ocr_engine,
        raw_text,
        status,
        json.dumps(extracted_data),
        confidence,
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

def get_recent_scan_sessions(limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scan_sessions ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("extracted_data"):
            try:
                d["extracted_data"] = json.loads(d["extracted_data"])
            except Exception:
                pass
        results.append(d)
    return results

# --- External Products Cache (Open Food Facts) ---

def get_cached_barcode_product(barcode: str):
    """Retrieves cached product data for a barcode if not expired."""
    clean_code = str(barcode).strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM external_products_cache WHERE barcode = ?", (clean_code,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    now_iso = datetime.now().isoformat()
    if d.get("expires_at") and d["expires_at"] < now_iso:
        return None  # Expired
    if d.get("product_data"):
        try:
            return json.loads(d["product_data"])
        except Exception:
            return None
    return None

def cache_barcode_product(barcode: str, product_data: Optional[dict], source: str = "openfoodfacts", status: str = "success", ttl_hours: int = 168):
    """Caches product lookup results (defaults to 7 days for success, 1 hour for negative results)."""
    clean_code = str(barcode).strip()
    from datetime import timedelta
    now = datetime.now()
    expires_at = (now + timedelta(hours=ttl_hours)).isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO external_products_cache (barcode, product_data, source, status, cached_at, expires_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(barcode) DO UPDATE SET
        product_data=excluded.product_data,
        source=excluded.source,
        status=excluded.status,
        cached_at=excluded.cached_at,
        expires_at=excluded.expires_at
    """, (
        clean_code,
        json.dumps(product_data) if product_data else None,
        source,
        status,
        now.isoformat(),
        expires_at
    ))
    conn.commit()
    conn.close()

# --- User Product Contributions ---

def record_user_contribution(contribution: dict):
    """Stores user-submitted product record locally with 'user_submitted' review status."""
    conn = get_connection()
    cursor = conn.cursor()
    sub_id = contribution.get("submission_id") or f"sub_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(contribution.get('barcode', ''))[:6]}"
    
    nutrition_json = json.dumps(contribution.get("nutrition_data", {}))
    cursor.execute("""
    INSERT INTO user_contributions (
        submission_id, barcode, product_name, brand, category, sub_category,
        serving_size, serving_size_unit, measurement_basis, nutrition_data,
        ingredients, allergens_declared, front_image_path, label_image_path,
        ingredients_image_path, review_status, submission_notes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(submission_id) DO UPDATE SET
        product_name=excluded.product_name,
        brand=excluded.brand,
        nutrition_data=excluded.nutrition_data,
        review_status=excluded.review_status
    """, (
        sub_id,
        str(contribution.get("barcode", "")).strip(),
        contribution.get("product_name"),
        contribution.get("brand"),
        contribution.get("category", "Snacks"),
        contribution.get("sub_category", "User Contributed"),
        contribution.get("serving_size", 100.0),
        contribution.get("serving_size_unit", "g"),
        contribution.get("measurement_basis", "per 100g"),
        nutrition_json,
        contribution.get("ingredients"),
        contribution.get("allergens_declared"),
        contribution.get("front_image_path"),
        contribution.get("label_image_path"),
        contribution.get("ingredients_image_path"),
        contribution.get("review_status", "user_submitted"),
        contribution.get("submission_notes", "Local User Contribution — Pending Audit"),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
    return sub_id

def get_user_contributions(limit: int = 50):
    """Retrieves recent user submitted products."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_contributions ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("nutrition_data"):
            try:
                d["nutrition_data"] = json.loads(d["nutrition_data"])
            except Exception:
                pass
        results.append(d)
    return results

def get_user_contribution_by_barcode(barcode: str):
    """Checks if a user contribution exists for this barcode."""
    clean_code = str(barcode).strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_contributions WHERE barcode = ? ORDER BY created_at DESC LIMIT 1", (clean_code,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get("nutrition_data"):
        try:
            d["nutrition_data"] = json.loads(d["nutrition_data"])
        except Exception:
            pass
    return d

# Initialize DB on load
init_db()
