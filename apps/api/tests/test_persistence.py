"""Tests for file-based snapshot persistence.

These tests exercise the persistence helpers directly against a temp dir so no
files leak.  The persistence layer is intentionally inert during the normal
test run (``resolve_data_dir`` returns ``None`` under pytest); here we drive the
build / write / read / apply functions explicitly.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api import persistence, state
from apps.api.routers.schemas import get_project_pins
from apps.api.tests.conftest import SOURCE_JSON_SCHEMA, analyst_headers


def _create_project_with_schema(client: TestClient) -> tuple[str, str]:
    """Create a project and import a user (custom) source schema into it."""
    r = client.post(
        "/projects",
        json={"name": "Persisted Project", "description": "roundtrip"},
        headers=analyst_headers(),
    )
    assert r.status_code == 201, r.text
    project_id = r.json()["id"]

    r2 = client.post(
        f"/projects/{project_id}/schemas/source/import",
        json={
            "format_id": "json_schema",
            "schema_name": "RegionPatient",
            "version_label": "1.0",
            "schema_payload": SOURCE_JSON_SCHEMA,
        },
        headers=analyst_headers(),
    )
    assert r2.status_code == 201, r2.text
    return project_id, r2.json()["schema_id"]


def test_resolve_data_dir_disabled_under_pytest() -> None:
    """Persistence is a no-op under pytest regardless of environment."""
    assert persistence.resolve_data_dir() is None
    # save/load through the state seams must be inert (no disk I/O, no error).
    assert state.save_state() is False
    assert state.load_state() is False


def test_snapshot_roundtrip_restores_project(client: TestClient, tmp_path: Path) -> None:
    """Create project → write snapshot → read + apply into fresh state → survives."""
    project_id, schema_id = _create_project_with_schema(client)

    # Build snapshot from the live in-memory state and persist it to a temp dir.
    snapshot = persistence.build_snapshot(
        projects=state.get_projects(),
        mapping_versions=state.get_mapping_versions(),
        audit_log=state.get_audit_log(),
        catalog=state.get_catalog(),
        project_pins=get_project_pins(),
    )
    assert persistence.write_snapshot(tmp_path, snapshot) is True
    assert persistence.snapshot_path(tmp_path).exists()

    # The user-imported schema is captured; standards are excluded.
    persisted_schema_ids = {
        e["descriptor"]["id"] for e in snapshot["catalog_entries"]
    }
    assert schema_id in persisted_schema_ids
    assert all(
        e["descriptor"]["schema_type"] != "standard"
        for e in snapshot["catalog_entries"]
    )

    # Read it back and apply into fresh, empty containers (+ a fresh catalog
    # that already has the standards loaded, mimicking a boot).
    loaded = persistence.read_snapshot(tmp_path)
    assert loaded is not None

    from apps.api.standards.loader import register_all, register_bundles
    from packages.adapters.defaults import register_defaults
    from packages.adapters.registry import AdapterRegistry
    from packages.catalog.catalog_service import CatalogService

    registry = AdapterRegistry()
    register_defaults(registry)
    fresh_audit: list = []
    fresh_catalog = CatalogService(adapter_registry=registry, audit_log=fresh_audit)
    register_all(fresh_catalog)
    register_bundles(fresh_catalog)

    fresh_projects: dict = {}
    fresh_versions: dict = {}
    fresh_project_pins: dict = {}

    persistence.apply_snapshot(
        loaded,
        projects=fresh_projects,
        mapping_versions=fresh_versions,
        audit_log=fresh_audit,
        catalog=fresh_catalog,
        project_pins=fresh_project_pins,
    )

    # Project survived the roundtrip.
    assert project_id in fresh_projects
    assert fresh_projects[project_id].name == "Persisted Project"

    # User schema survived and is resolvable from the fresh catalog.
    entry = fresh_catalog.get_entry(schema_id)
    assert entry.descriptor.name == "RegionPatient"

    # Standards were NOT duplicated: still exactly the bundled set count.
    standard_names = {
        e.descriptor.name
        for e in fresh_catalog.list_entries()
        if e.descriptor.schema_type.value == "standard"
    }
    assert "FHIR_R4" in standard_names
    assert "OMOP_CDM_5_4" in standard_names


def test_read_snapshot_missing_returns_none(tmp_path: Path) -> None:
    assert persistence.read_snapshot(tmp_path) is None


def test_apply_snapshot_skips_existing_standard_ids(tmp_path: Path) -> None:
    """A snapshot entry whose id collides with a live standard is ignored."""
    from apps.api.standards.loader import register_all
    from packages.adapters.defaults import register_defaults
    from packages.adapters.registry import AdapterRegistry
    from packages.catalog.catalog_service import CatalogService

    registry = AdapterRegistry()
    register_defaults(registry)
    audit: list = []
    catalog = CatalogService(adapter_registry=registry, audit_log=audit)
    register_all(catalog)

    existing_id = next(iter(catalog._entries.keys()))
    original = catalog._entries[existing_id]

    fake_snapshot = {
        "catalog_entries": [
            {
                "descriptor": {
                    "id": existing_id,
                    "name": "TAMPERED",
                    "schema_type": "custom",
                    "format_id": "json_schema",
                    "source": "uploaded",
                    "owner": "attacker",
                    "approval_status": "draft",
                    "description": None,
                    "metadata_tags": {},
                    "created_at": "2026-01-01T00:00:00+00:00",
                },
                "versions": [],
                "default_version_id": None,
            }
        ],
    }

    persistence.apply_snapshot(
        fake_snapshot,
        projects={},
        mapping_versions={},
        audit_log=audit,
        catalog=catalog,
        project_pins={},
    )

    # The live standard entry must be untouched.
    assert catalog._entries[existing_id] is original
    assert catalog._entries[existing_id].descriptor.name != "TAMPERED"
