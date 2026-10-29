"""
EATGOOD — Security, reliability and readiness checks.
"""

import json
import sqlite3
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from backend.core.rate_limiter import rate_limiter
from backend.main import app

client = TestClient(app)


def test_health_reports_ok():
    data = client.get("/api/health").json()
    assert data["status"] == "ok"


def test_readiness_probe_ok():
    response = client.get("/api/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"] == {"database": "ok"}


def test_readiness_returns_503_when_database_unreachable(monkeypatch):
    from backend.routes import meta

    def broken():
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(meta, "check_db", broken)
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "unreachable"


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
        ("post", "/api/analyze/label-text"),
        ("get", "/api/dataset"),
        ("get", "/api/audit"),
        ("get", "/api/search/semantic"),
    ],
)
def test_removed_cross_user_and_upload_endpoints_do_not_exist(method, path):
    """These endpoints exposed or deleted other visitors' data, or accepted label photos or label text."""
    response = getattr(client, method)(path)
    assert response.status_code in (404, 405)


def test_invalid_profile_header_is_rejected_not_ignored():
    response = client.get("/api/products/OFF_2000000000015", headers={"X-Eatgood-Profile": "%7Bnot json"})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "PROFILE_INVALID"


def test_unknown_dietary_preference_is_rejected():
    header = quote(json.dumps({"dietary_preference": "Carnivore"}))
    response = client.get("/api/products/OFF_2000000000015", headers={"X-Eatgood-Profile": header})
    assert response.status_code == 400


def test_open_food_facts_search_query_length_is_bounded():
    assert client.get("/api/products/search/openfoodfacts?q=x").status_code == 422
    assert client.get("/api/products/search/openfoodfacts?q=" + "x" * 101).status_code == 422


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
    response = TestClient(app, raise_server_exceptions=False).get("/api/products/OFF_2000000000015")
    assert response.status_code == 500
    body = response.json()
    assert body["detail"]["error_code"] == "INTERNAL_ERROR"
    assert "secret" not in json.dumps(body)


def test_local_static_route_serves_only_built_files(tmp_path, monkeypatch):
    """The SPA route maps request paths to a startup allowlist; traversal falls back to index.html."""
    import importlib

    dist = tmp_path / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>index</html>")
    (dist / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("secret")
    import backend.config as config
    import backend.main as main

    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "IS_SERVERLESS", False)
    reloaded = importlib.reload(main)
    try:
        c = TestClient(reloaded.app)
        assert c.get("/favicon.svg").text == "<svg/>"
        assert c.get("/catalogue").text == "<html>index</html>"
        assert "secret" not in c.get("/../secret.txt").text
        assert "secret" not in c.get("/%2e%2e/secret.txt").text
    finally:
        monkeypatch.undo()
        importlib.reload(main)
