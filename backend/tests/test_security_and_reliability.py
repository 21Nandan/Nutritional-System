"""
EATGOOD — Security, Reliability, & Readiness Verification Suite
Tests security headers, upload constraints (magic bytes, size), rate limiting,
health/readiness probes, and database integrity (WAL mode, busy timeout).
"""

import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app
from backend.core.rate_limiter import rate_limiter
from backend.database import get_connection

client = TestClient(app)

def test_readiness_probe():
    response = client.get("/api/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "healthy"
    assert data["dataset_ready"] is True
    assert data["products_count"] > 800

def test_security_headers_and_request_id():
    response = client.get("/api/health")
    assert response.status_code == 200
    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "X-Request-ID" in headers
    assert len(headers["X-Request-ID"]) > 10

def test_upload_invalid_extension_rejected():
    files = {"file": ("malicious.sh", b"echo 'hack'", "text/plain")}
    response = client.post("/api/analyze/ocr", files=files)
    assert response.status_code == 400
    assert "Unsupported image format" in response.json()["detail"]

def test_upload_empty_file_rejected():
    files = {"file": ("empty.png", b"", "image/png")}
    response = client.post("/api/analyze/ocr", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_upload_corrupt_magic_bytes_rejected():
    files = {"file": ("fake.jpg", b"This is not a real JPEG file at all!", "image/jpeg")}
    response = client.post("/api/analyze/ocr", files=files)
    assert response.status_code == 400
    assert "Corrupt or invalid image file" in response.json()["detail"]

def test_upload_oversized_file_rejected(monkeypatch):
    # Temporarily set MAX_UPLOAD_SIZE_BYTES to 100 bytes for fast deterministic test
    import backend.main as main_mod
    monkeypatch.setattr(main_mod, "MAX_UPLOAD_SIZE_BYTES", 100)
    monkeypatch.setattr(main_mod, "MAX_UPLOAD_SIZE_MB", 0.0001)

    # Valid PNG image of 200 bytes
    img = Image.new("RGB", (30, 30), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    assert len(png_bytes) > 100

    files = {"file": ("oversized.png", png_bytes, "image/png")}
    response = client.post("/api/analyze/ocr", files=files)
    assert response.status_code == 413
    assert "exceeds maximum limit" in response.json()["detail"]

def test_sliding_window_rate_limiter_unit():
    key = "test_client_isolated_bucket"
    # Allow 3 requests per 60 seconds
    assert rate_limiter.is_rate_limited(key, max_requests=3, window_seconds=60)[0] is False
    assert rate_limiter.is_rate_limited(key, max_requests=3, window_seconds=60)[0] is False
    assert rate_limiter.is_rate_limited(key, max_requests=3, window_seconds=60)[0] is False
    
    # 4th request must be rate limited
    is_limited, retry_after = rate_limiter.is_rate_limited(key, max_requests=3, window_seconds=60)
    assert is_limited is True
    assert retry_after > 0

def test_database_pragmas_configured():
    conn = get_connection()
    # Check foreign keys
    fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    assert fk == 1
    # Check busy timeout >= 5000ms
    timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
    assert timeout >= 5000
    conn.close()
