"""Tests for the unauthenticated /health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok_without_auth(client: TestClient) -> None:
    """GET /health must return 200 and {"status":"ok"} with no auth headers."""
    r = client.get("/health")
    assert r.status_code == 200, r.text
    assert r.json() == {"status": "ok"}


def test_health_ignores_role_headers(client: TestClient) -> None:
    """Even a viewer (or no role at all) can reach /health."""
    r = client.get("/health", headers={"X-User-Id": "anyone"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"


def test_health_in_openapi_contract(client: TestClient) -> None:
    """/health is part of the published contract so deploy tooling can rely on it."""
    spec = client.get("/openapi.json").json()
    assert "/health" in spec.get("paths", {})
