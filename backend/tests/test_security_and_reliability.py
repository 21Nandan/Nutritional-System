"""
EATGOOD — Security, reliability and readiness checks.
"""

import json
import shutil
import sqlite3
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from backend.core.data_loader import CatalogueLoadError, DataLoaderService
from backend.core.rate_limiter import rate_limiter
from backend.main import app

client = TestClient(app)


def test_health_reports_loaded_catalogue():
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["products_count"] > 800


def test_readiness_probe_ok():
    response = client.get("/api/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"] == {"catalogue": "ok", "database": "ok"}


def test_readiness_returns_503_when_database_unreachable(monkeypatch):
    from backend.routes import meta

    def broken():
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(meta, "check_db", broken)
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "unreachable"


def test_catalogue_loader_fails_fast_on_missing_file(tmp_path):
    from backend.config import DATA_DIR

    for name in ["dataset_manifest.json", "product_images.csv", "data_quality_report.csv",
                 "nutrition_review.csv", "serving_size_review.csv"]:
        shutil.copy(DATA_DIR / name, tmp_path / name)
    with pytest.raises(CatalogueLoadError, match="products_cleaned.csv"):
        DataLoaderService(tmp_path)


def test_catalogue_loader_fails_fast_on_row_count_mismatch(tmp_path):
    from backend.config import DATA_DIR

    for name in ["product_images.csv", "data_quality_report.csv", "nutrition_review.csv",
                 "serving_size_review.csv", "products_cleaned.csv"]:
        shutil.copy(DATA_DIR / name, tmp_path / name)
    manifest = json.loads((DATA_DIR / "dataset_manifest.json").read_text())
    manifest["catalogue_rows"] = 999
    (tmp_path / "dataset_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(CatalogueLoadError, match="manifest declares 999"):
        DataLoaderService(tmp_path)


def test_security_headers_and_request_id():
    response = client.get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert len(response.headers["X-Request-ID"]) >= 8


def test_untrusted_request_id_is_replaced():
    response = client.get("/api/health", headers={"X-Request-ID": "bad id\nwith newline"})
    assert response.headers["X-Request-ID"] != "bad id\nwith newline"


def test_cors_rejects_unknown_origin():
    response = client.options(
        "/api/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/history"),
        ("delete", "/api/history"),
        ("get", "/api/saved"),
        ("post", "/api/profile"),
        ("get", "/api/scans/recent"),
        ("get", "/api/products/contributions"),
        ("post", "/api/analyze/ocr"),
    ],
)
def test_removed_cross_user_and_upload_endpoints_do_not_exist(method, path):
    """These endpoints exposed or deleted other visitors' data, or accepted image uploads."""
    response = getattr(client, method)(path)
    assert response.status_code in (404, 405)


def test_invalid_profile_header_is_rejected_not_ignored():
    response = client.get("/api/products/IND_PKG_001", headers={"X-Eatgood-Profile": "%7Bnot json"})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "PROFILE_INVALID"


def test_unknown_dietary_preference_is_rejected():
    header = quote(json.dumps({"dietary_preference": "Carnivore"}))
    response = client.get("/api/products/IND_PKG_001", headers={"X-Eatgood-Profile": header})
    assert response.status_code == 400


def test_label_text_size_limit():
    response = client.post(
        "/api/analyze/label-text", json={"raw_text": "x" * 20001, "ocr_confidence": 0.5, "engine": "test"}
    )
    assert response.status_code == 413
    assert response.json()["detail"]["error_code"] == "OCR_TEXT_TOO_LONG"


def test_sliding_window_rate_limiter_blocks_after_limit():
    key = "test:rate-limit"
    for _ in range(3):
        limited, _ = rate_limiter.is_rate_limited(key, max_requests=3, window_seconds=60)
        assert limited is False
    limited, retry_after = rate_limiter.is_rate_limited(key, max_requests=3, window_seconds=60)
    assert limited is True
    assert retry_after >= 1


def test_rate_limit_ignores_spoofed_forwarded_for_outside_vercel(monkeypatch):
    from starlette.requests import Request

    from backend.core import rate_limiter as rl

    monkeypatch.setattr(rl, "IS_SERVERLESS", False)
    scope = {"type": "http", "headers": [(b"x-forwarded-for", b"1.2.3.4")], "client": ("10.0.0.9", 1234)}
    assert rl.get_client_identifier(Request(scope)) == "10.0.0.9"
    monkeypatch.setattr(rl, "IS_SERVERLESS", True)
    assert rl.get_client_identifier(Request(scope)) == "1.2.3.4"


def test_unhandled_errors_return_generic_message(monkeypatch):
    from backend.routes import catalogue

    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(catalogue, "run_full_product_assessment", boom)
    response = TestClient(app, raise_server_exceptions=False).get("/api/products/IND_PKG_001")
    assert response.status_code == 500
    body = response.json()
    assert body["detail"]["error_code"] == "INTERNAL_ERROR"
    assert "secret" not in json.dumps(body)
