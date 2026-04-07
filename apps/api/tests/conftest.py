"""Shared pytest fixtures for API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Must import state before main so the shared objects exist
from apps.api import state
from apps.api.main import create_app
from apps.api.routers.schemas import reset_pins


@pytest.fixture(autouse=True)
def reset_app_state():
    """Reset all in-memory state before each test for isolation."""
    state.reset_state()
    reset_pins()
    yield
    state.reset_state()
    reset_pins()


@pytest.fixture()
def client() -> TestClient:
    """Synchronous TestClient for the FastAPI app."""
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth header factories
# ---------------------------------------------------------------------------

def analyst_headers(user_id: str = "alice") -> dict:
    return {"X-User-Id": user_id, "X-User-Role": "analyst"}


def admin_headers(user_id: str = "admin") -> dict:
    return {"X-User-Id": user_id, "X-User-Role": "admin"}


def viewer_headers(user_id: str = "bob") -> dict:
    return {"X-User-Id": user_id, "X-User-Role": "viewer"}


# ---------------------------------------------------------------------------
# Schema payloads used across test modules
# ---------------------------------------------------------------------------

SOURCE_JSON_SCHEMA = {
    "type": "object",
    "title": "RegionPatient",
    "properties": {
        "patient_id": {"type": "integer"},
        "fornamn": {"type": "string"},
        "efternamn": {"type": "string"},
        "fodelsedatum": {"type": "string", "format": "date"},
    },
    "required": ["patient_id"],
}

TARGET_JSON_SCHEMA = {
    "type": "object",
    "title": "StandardPatient",
    "properties": {
        "patient_id": {"type": "integer"},
        "given_name": {"type": "string"},
        "family_name": {"type": "string"},
        "birth_date": {"type": "string", "format": "date"},
    },
    "required": ["patient_id"],
}
