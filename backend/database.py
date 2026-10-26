"""
EATGOOD — SQLite Local Database Service
Persists user profiles, analysis history, and saved products locally.
No transmission of sensitive personal information to third-party endpoints.
"""

import os
import sqlite3
import json
from datetime import datetime

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
        saved_at TIMESTAMP
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
            "Demo Student / Evaluator",
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
        profile_data.get("name", "Student Evaluator"),
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

def toggle_save_product(product_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id FROM saved_products WHERE product_id = ?", (product_id,))
    exists = cursor.fetchone()
    if exists:
        cursor.execute("DELETE FROM saved_products WHERE product_id = ?", (product_id,))
        saved = False
    else:
        cursor.execute("INSERT INTO saved_products (product_id, saved_at) VALUES (?, ?)", (product_id, datetime.now().isoformat()))
        saved = True
    conn.commit()
    conn.close()
    return saved

def get_saved_product_ids():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id FROM saved_products ORDER BY saved_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

# Initialize DB on load
init_db()
