"""Tests for GET /catalog/schemas and GET /catalog/schemas/{id}/versions.

Coverage:
  - empty catalog returns empty list
  - list returns all registered schemas
  - deterministic ordering (approved before draft, then name asc, then created_at asc)
  - filter by type (custom / standard)
  - filter by format (format_id)
  - filter by approval status (draft / approved)
  - combined filters
  - q substring search (case-insensitive)
  - invalid enum values return 422
  - versions endpoint returns correct versions in insertion order
  - versions endpoint returns 404 for unknown schema
  - viewer role can access both endpoints
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api import state
from apps.api.main import create_app
from apps.api.routers.schemas import reset_pins
from apps.api.tests.conftest import analyst_headers, admin_headers, viewer_headers

# ---------------------------------------------------------------------------
# Shared JSON-Schema payloads
# ---------------------------------------------------------------------------

_SCHEMA_A = {
    "type": "object",
    "title": "SchemaAlpha",
    "properties": {"id": {"type": "integer"}},
}
_SCHEMA_B = {
    "type": "object",
    "title": "SchemaBeta",
    "properties": {"name": {"type": "string"}},
}
_SCHEMA_C = {
    "type": "object",
    "title": "SchemaGamma",
    "properties": {"code": {"type": "string"}},
}

_CSV_SCHEMA = "name,type,required\nvisit_id,integer,true\n"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset():
    state.reset_state()
    reset_pins()
    yield
    state.reset_state()
    reset_pins()


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def _import(client: TestClient, payload, schema_name: str, format_id: str = "json_schema", version_label: str = "1.0") -> dict:
    """Import a schema into an ephemeral project (creates the catalog entry)."""
    # Create a throwaway project to satisfy the endpoint's project lookup
    proj = client.post(
        "/projects",
        json={"name": f"tmp-{schema_name}", "description": None},
        headers=analyst_headers(),
    )
    assert proj.status_code == 201, proj.text
    pid = proj.json()["id"]

    r = client.post(
        f"/projects/{pid}/schemas/source/import",
        json={
            "format_id": format_id,
            "schema_name": schema_name,
            "version_label": version_label,
            "schema_payload": payload,
        },
        headers=analyst_headers(),
    )
    assert r.status_code == 201, r.text
    return r.json()  # PinnedSchemaRef


# ---------------------------------------------------------------------------
# GET /catalog/schemas — basic behaviour
# ---------------------------------------------------------------------------

class TestCatalogList:
    def test_empty_catalog_returns_empty_list(self, client):
        r = client.get("/catalog/schemas", headers=viewer_headers())
        assert r.status_code == 200
        assert r.json() == []

    def test_registered_schema_appears_in_list(self, client):
        _import(client, _SCHEMA_A, "SchemaAlpha")
        r = client.get("/catalog/schemas", headers=viewer_headers())
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["name"] == "SchemaAlpha"
        assert body[0]["format_id"] == "json_schema"
        assert body[0]["schema_type"] == "custom"
        assert body[0]["available_versions_count"] == 1
        assert body[0]["latest_version_label"] == "1.0"

    def test_list_contains_all_registered_schemas(self, client):
        _import(client, _SCHEMA_A, "SchemaAlpha")
        _import(client, _SCHEMA_B, "SchemaBeta")
        _import(client, _SCHEMA_C, "SchemaGamma")
        r = client.get("/catalog/schemas", headers=viewer_headers())
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert set(names) == {"SchemaAlpha", "SchemaBeta", "SchemaGamma"}

    def test_response_contains_required_fields(self, client):
        ref = _import(client, _SCHEMA_A, "SchemaAlpha")
        r = client.get("/catalog/schemas", headers=viewer_headers())
        item = r.json()[0]
        for key in ("id", "name", "format_id", "schema_type", "approval_status",
                    "owner", "latest_version_label", "available_versions_count",
                    "created_at", "metadata_tags"):
            assert key in item, f"Missing field: {key}"
        # schema_id returned by the import endpoint is the catalog's schema id
        assert item["id"] == ref["schema_id"]


# ---------------------------------------------------------------------------
# GET /catalog/schemas — deterministic ordering
# ---------------------------------------------------------------------------

class TestCatalogOrdering:
    def test_ordering_is_deterministic_on_repeated_calls(self, client):
        _import(client, _SCHEMA_C, "SchemaGamma")
        _import(client, _SCHEMA_A, "SchemaAlpha")
        _import(client, _SCHEMA_B, "SchemaBeta")

        r1 = client.get("/catalog/schemas", headers=viewer_headers())
        r2 = client.get("/catalog/schemas", headers=viewer_headers())
        assert r1.json() == r2.json()

    def test_ordering_approved_before_draft(self, client):
        ref_a = _import(client, _SCHEMA_A, "SchemaAlpha")  # draft by default
        ref_b = _import(client, _SCHEMA_B, "SchemaBeta")   # will be approved

        # Approve SchemaBeta via the catalog service directly
        catalog = state.get_catalog()
        catalog.approve_schema(ref_b["schema_id"], actor="admin")

        r = client.get("/catalog/schemas", headers=viewer_headers())
        names = [s["name"] for s in r.json()]
        assert names[0] == "SchemaBeta"   # approved → first
        assert names[1] == "SchemaAlpha"  # draft → second

    def test_ordering_alphabetical_within_same_status(self, client):
        _import(client, _SCHEMA_C, "SchemaGamma")
        _import(client, _SCHEMA_A, "SchemaAlpha")
        _import(client, _SCHEMA_B, "SchemaBeta")

        r = client.get("/catalog/schemas", headers=viewer_headers())
        names = [s["name"] for s in r.json()]
        # All draft → alphabetical
        assert names == ["SchemaAlpha", "SchemaBeta", "SchemaGamma"]


# ---------------------------------------------------------------------------
# GET /catalog/schemas — filtering
# ---------------------------------------------------------------------------

class TestCatalogFiltering:
    def test_filter_by_format_id(self, client):
        _import(client, _SCHEMA_A, "SchemaAlpha", format_id="json_schema")
        _import(client, _CSV_SCHEMA, "VisitCSV", format_id="csv_schema")

        r = client.get("/catalog/schemas?format=json_schema", headers=viewer_headers())
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["name"] == "SchemaAlpha"
        assert body[0]["format_id"] == "json_schema"

    def test_filter_by_format_id_csv(self, client):
        _import(client, _SCHEMA_A, "SchemaAlpha", format_id="json_schema")
        _import(client, _CSV_SCHEMA, "VisitCSV", format_id="csv_schema")

        r = client.get("/catalog/schemas?format=csv_schema", headers=viewer_headers())
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["name"] == "VisitCSV"

    def test_filter_by_type_custom(self, client):
        _import(client, _SCHEMA_A, "SchemaAlpha")
        r = client.get("/catalog/schemas?type=custom", headers=viewer_headers())
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["schema_type"] == "custom"

    def test_filter_by_approval_status_draft(self, client):
        ref_a = _import(client, _SCHEMA_A, "SchemaAlpha")
        ref_b = _import(client, _SCHEMA_B, "SchemaBeta")
        catalog = state.get_catalog()
        catalog.approve_schema(ref_b["schema_id"], actor="admin")

        r = client.get("/catalog/schemas?status=draft", headers=viewer_headers())
        body = r.json()
        assert len(body) == 1
        assert body[0]["name"] == "SchemaAlpha"

    def test_filter_by_approval_status_approved(self, client):
        ref_a = _import(client, _SCHEMA_A, "SchemaAlpha")
        ref_b = _import(client, _SCHEMA_B, "SchemaBeta")
        catalog = state.get_catalog()
        catalog.approve_schema(ref_a["schema_id"], actor="admin")
        catalog.approve_schema(ref_b["schema_id"], actor="admin")

        r = client.get("/catalog/schemas?status=approved", headers=viewer_headers())
        body = r.json()
        assert len(body) == 2
        assert all(s["approval_status"] == "approved" for s in body)

    def test_filter_q_substring_case_insensitive(self, client):
        _import(client, _SCHEMA_A, "SchemaAlpha")
        _import(client, _SCHEMA_B, "SchemaBeta")

        r = client.get("/catalog/schemas?q=alpha", headers=viewer_headers())
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["name"] == "SchemaAlpha"

    def test_filter_q_case_insensitive_upper(self, client):
        _import(client, _SCHEMA_A, "SchemaAlpha")
        _import(client, _SCHEMA_B, "SchemaBeta")

        r = client.get("/catalog/schemas?q=BETA", headers=viewer_headers())
        body = r.json()
        assert len(body) == 1
        assert body[0]["name"] == "SchemaBeta"

    def test_filter_q_no_match_returns_empty(self, client):
        _import(client, _SCHEMA_A, "SchemaAlpha")
        r = client.get("/catalog/schemas?q=zzznomatch", headers=viewer_headers())
        assert r.json() == []

    def test_combined_filter_format_and_q(self, client):
        _import(client, _SCHEMA_A, "SchemaAlpha", format_id="json_schema")
        _import(client, _CSV_SCHEMA, "AlphaVisit", format_id="csv_schema")

        # q=alpha matches both names but format=json_schema should narrow to 1
        r = client.get("/catalog/schemas?format=json_schema&q=alpha", headers=viewer_headers())
        body = r.json()
        assert len(body) == 1
        assert body[0]["name"] == "SchemaAlpha"

    def test_invalid_type_returns_422(self, client):
        r = client.get("/catalog/schemas?type=unknown_type", headers=viewer_headers())
        assert r.status_code == 422

    def test_invalid_status_returns_422(self, client):
        r = client.get("/catalog/schemas?status=pending", headers=viewer_headers())
        assert r.status_code == 422

    def test_unknown_format_filter_returns_empty_not_error(self, client):
        _import(client, _SCHEMA_A, "SchemaAlpha")
        r = client.get("/catalog/schemas?format=nonexistent_format", headers=viewer_headers())
        assert r.status_code == 200
        assert r.json() == []


# ---------------------------------------------------------------------------
# GET /catalog/schemas/{id}/versions
# ---------------------------------------------------------------------------

class TestSchemaVersions:
    def test_versions_returns_all_versions_in_order(self, client):
        ref_v1 = _import(client, _SCHEMA_A, "SchemaAlpha", version_label="1.0")
        # Import a second version for the same schema
        schema_id = ref_v1["schema_id"]
        _schema_a_v2 = {
            "type": "object",
            "title": "SchemaAlpha",
            "properties": {"id": {"type": "integer"}, "code": {"type": "string"}},
        }
        proj2 = client.post(
            "/projects",
            json={"name": "tmp-v2", "description": None},
            headers=analyst_headers(),
        )
        pid2 = proj2.json()["id"]
        r2 = client.post(
            f"/projects/{pid2}/schemas/source/import",
            json={
                "format_id": "json_schema",
                "schema_name": "SchemaAlpha",
                "version_label": "2.0",
                "schema_payload": _schema_a_v2,
            },
            headers=analyst_headers(),
        )
        assert r2.status_code == 201

        r = client.get(f"/catalog/schemas/{schema_id}/versions", headers=viewer_headers())
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 2
        assert body[0]["version_label"] == "1.0"
        assert body[1]["version_label"] == "2.0"

    def test_versions_response_contains_required_fields(self, client):
        ref = _import(client, _SCHEMA_A, "SchemaAlpha")
        r = client.get(f"/catalog/schemas/{ref['schema_id']}/versions", headers=viewer_headers())
        assert r.status_code == 200
        v = r.json()[0]
        for key in ("id", "schema_id", "version_label", "created_at", "checksum"):
            assert key in v, f"Missing field: {key}"

    def test_versions_checksum_is_sha256_hex(self, client):
        ref = _import(client, _SCHEMA_A, "SchemaAlpha")
        r = client.get(f"/catalog/schemas/{ref['schema_id']}/versions", headers=viewer_headers())
        checksum = r.json()[0]["checksum"]
        # SHA-256 hex is exactly 64 characters
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_versions_same_content_same_checksum(self, client):
        """Two versions of the same schema registered with the same payload
        share an identical content checksum (the checksum is content-based,
        not version-label-based).
        """
        ref_v1 = _import(client, _SCHEMA_A, "SchemaAlpha", version_label="1.0")
        schema_id = ref_v1["schema_id"]

        # Register the same payload as version 2.0 of the same schema
        proj2 = client.post(
            "/projects",
            json={"name": "tmp-v2b", "description": None},
            headers=analyst_headers(),
        )
        pid2 = proj2.json()["id"]
        r2 = client.post(
            f"/projects/{pid2}/schemas/source/import",
            json={
                "format_id": "json_schema",
                "schema_name": "SchemaAlpha",
                "version_label": "2.0",
                "schema_payload": _SCHEMA_A,
            },
            headers=analyst_headers(),
        )
        assert r2.status_code == 201

        r = client.get(f"/catalog/schemas/{schema_id}/versions", headers=viewer_headers())
        versions = r.json()
        assert len(versions) == 2
        # Same payload → same content fingerprint across both versions
        assert versions[0]["checksum"] == versions[1]["checksum"]

    def test_versions_unknown_schema_returns_404(self, client):
        r = client.get("/catalog/schemas/does-not-exist/versions", headers=viewer_headers())
        assert r.status_code == 404

    def test_versions_schema_id_matches_parent(self, client):
        ref = _import(client, _SCHEMA_A, "SchemaAlpha")
        r = client.get(f"/catalog/schemas/{ref['schema_id']}/versions", headers=viewer_headers())
        for v in r.json():
            assert v["schema_id"] == ref["schema_id"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestCatalogAuth:
    def test_viewer_can_list_schemas(self, client):
        r = client.get("/catalog/schemas", headers=viewer_headers())
        assert r.status_code == 200

    def test_viewer_can_list_versions(self, client):
        ref = _import(client, _SCHEMA_A, "SchemaAlpha")
        r = client.get(f"/catalog/schemas/{ref['schema_id']}/versions", headers=viewer_headers())
        assert r.status_code == 200

    def test_missing_auth_returns_401(self, client):
        r = client.get("/catalog/schemas")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# OpenAPI presence
# ---------------------------------------------------------------------------

class TestCatalogOpenAPI:
    def test_catalog_paths_in_openapi(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        paths = r.json()["paths"]
        assert "/catalog/schemas" in paths
        assert "/catalog/schemas/{schema_id}/versions" in paths
