"""API security headers and CORS deny path (M46)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from adaptive_rag.api.app import create_app


def test_health_includes_baseline_security_headers() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_cors_preflight_disallowed_origin_has_no_acao() -> None:
    client = TestClient(create_app())
    response = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") not in {
        "https://evil.example",
        "*",
    }


def test_cors_preflight_allowed_origin_receives_acao() -> None:
    client = TestClient(create_app())
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    )
