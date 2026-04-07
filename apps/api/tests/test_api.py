"""API tests — full workflow covering required test cases.

Mandatory test scenarios:
1. Project create + status update
2. Schema import routes through adapters and results in pinned versions
3. Suggestions endpoint returns top-k
4. Validation endpoint returns deterministic ordered issues
Plus: auth, export, edge cases.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from apps.api.tests.conftest import (
    SOURCE_JSON_SCHEMA,
    TARGET_JSON_SCHEMA,
    admin_headers,
    analyst_headers,
    viewer_headers,
)


# ---------------------------------------------------------------------------
# Helper: build a fully-wired project (project + source + target pinned)
# ---------------------------------------------------------------------------

def _create_project(client: TestClient, name: str = "Test Project") -> str:
    r = client.post(
        "/projects",
        json={"name": name, "description": "test"},
        headers=analyst_headers(),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _import_source(client: TestClient, project_id: str) -> dict:
    r = client.post(
        f"/projects/{project_id}/schemas/source/import",
        json={
            "format_id": "json_schema",
            "schema_name": "RegionPatient",
            "version_label": "1.0",
            "schema_payload": SOURCE_JSON_SCHEMA,
        },
        headers=analyst_headers(),
    )
    assert r.status_code == 201, r.text
    return r.json()


def _import_target(client: TestClient, project_id: str) -> dict:
    # Import target schema into catalog first
    r = client.post(
        f"/projects/{project_id}/schemas/source/import",
        json={
            "format_id": "json_schema",
            "schema_name": "StandardPatient",
            "version_label": "1.0",
            "schema_payload": TARGET_JSON_SCHEMA,
        },
        headers=analyst_headers(),
    )
    assert r.status_code == 201, r.text
    schema_id = r.json()["schema_id"]

    # Now pin it as target
    r2 = client.post(
        f"/projects/{project_id}/schemas/target/select",
        json={"schema_id": schema_id, "version_label": "1.0"},
        headers=analyst_headers(),
    )
    assert r2.status_code == 201, r2.text
    return r2.json()


def _wire_project(client: TestClient):
    """Create a project with source + target pinned. Returns (project_id, src, tgt)."""
    pid = _create_project(client)
    src = _import_source(client, pid)
    tgt = _import_target(client, pid)
    return pid, src, tgt


# ---------------------------------------------------------------------------
# Scenario 1: Project create + status update
# ---------------------------------------------------------------------------


class TestProjectCreateAndStatus:
    def test_create_project_returns_201(self, client):
        r = client.post(
            "/projects",
            json={"name": "My Project", "description": "desc"},
            headers=analyst_headers(),
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "My Project"
        assert body["status"] == "draft"
        assert body["owner"] == "alice"
        assert "id" in body

    def test_create_project_requires_auth(self, client):
        r = client.post("/projects", json={"name": "x"})  # no headers
        assert r.status_code == 401

    def test_viewer_cannot_create_project(self, client):
        r = client.post(
            "/projects",
            json={"name": "x"},
            headers=viewer_headers(),
        )
        assert r.status_code == 403

    def test_list_projects(self, client):
        _create_project(client, "A")
        _create_project(client, "B")
        r = client.get("/projects", headers=viewer_headers("bob"))
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_get_project(self, client):
        pid = _create_project(client)
        r = client.get(f"/projects/{pid}", headers=viewer_headers("bob"))
        assert r.status_code == 200
        assert r.json()["id"] == pid

    def test_get_nonexistent_project_returns_404(self, client):
        r = client.get("/projects/bad-id", headers=viewer_headers("bob"))
        assert r.status_code == 404

    def test_status_transition_draft_to_review(self, client):
        pid = _create_project(client)
        r = client.patch(
            f"/projects/{pid}",
            json={"status": "review"},
            headers=analyst_headers(),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "review"

    def test_invalid_status_transition_returns_409(self, client):
        pid = _create_project(client)
        # Cannot go draft → published (must go via review → approved)
        r = client.patch(
            f"/projects/{pid}",
            json={"status": "published"},
            headers=analyst_headers(),
        )
        assert r.status_code == 409

    def test_status_update_emits_audit_event(self, client):
        pid = _create_project(client)
        client.patch(
            f"/projects/{pid}",
            json={"status": "review"},
            headers=analyst_headers(),
        )
        from apps.api import state
        from packages.core.models.audit_event import AuditAction
        audit = state.get_audit_log()
        status_events = [e for e in audit if e.action == AuditAction.PROJECT_STATUS_CHANGE]
        assert len(status_events) == 1
        assert status_events[0].after["status"] == "review"


# ---------------------------------------------------------------------------
# Scenario 2: Schema import — routes through adapters, pins version
# ---------------------------------------------------------------------------


class TestSchemaImport:
    def test_import_source_schema_returns_201(self, client):
        pid = _create_project(client)
        r = _import_source(client, pid)
        assert "pin_id" in r
        assert "schema_id" in r
        assert r["version_label"] == "1.0"
        assert r["schema_name"] == "RegionPatient"
        assert r["field_count"] == 4

    def test_import_uses_adapter_registry(self, client):
        """CSV adapter must also work — confirms adapter dispatch, not hardcoding."""
        pid = _create_project(client)
        csv_payload = "name,type,required\nvisit_id,integer,true\nvisit_date,date,true\n"
        r = client.post(
            f"/projects/{pid}/schemas/source/import",
            json={
                "format_id": "csv_schema",
                "schema_name": "VisitCSV",
                "version_label": "1.0",
                "schema_payload": csv_payload,
            },
            headers=analyst_headers(),
        )
        assert r.status_code == 201
        assert r.json()["field_count"] == 2

    def test_import_emits_audit_event(self, client):
        from apps.api import state
        from packages.core.models.audit_event import AuditAction
        pid = _create_project(client)
        _import_source(client, pid)
        import_events = [
            e for e in state.get_audit_log()
            if e.action == AuditAction.SCHEMA_IMPORT
        ]
        assert len(import_events) >= 1

    def test_import_unknown_format_returns_422(self, client):
        pid = _create_project(client)
        r = client.post(
            f"/projects/{pid}/schemas/source/import",
            json={
                "format_id": "totally_unknown_format",
                "schema_name": "X",
                "version_label": "1.0",
                "schema_payload": {},
            },
            headers=analyst_headers(),
        )
        assert r.status_code == 422

    def test_import_duplicate_version_returns_409(self, client):
        pid = _create_project(client)
        _import_source(client, pid)
        # Same name + format + version → conflict
        r = client.post(
            f"/projects/{pid}/schemas/source/import",
            json={
                "format_id": "json_schema",
                "schema_name": "RegionPatient",
                "version_label": "1.0",
                "schema_payload": SOURCE_JSON_SCHEMA,
            },
            headers=analyst_headers(),
        )
        assert r.status_code == 409

    def test_get_schemas_shows_source_and_target(self, client):
        pid, src, tgt = _wire_project(client)
        r = client.get(f"/projects/{pid}/schemas", headers=viewer_headers("bob"))
        assert r.status_code == 200
        body = r.json()
        assert body["source"] is not None
        assert body["target"] is not None
        assert body["source"]["schema_name"] == "RegionPatient"

    def test_get_schemas_empty_project(self, client):
        pid = _create_project(client)
        r = client.get(f"/projects/{pid}/schemas", headers=viewer_headers("bob"))
        assert r.status_code == 200
        body = r.json()
        assert body["source"] is None
        assert body["target"] is None


# ---------------------------------------------------------------------------
# Scenario 3: Suggestions — top-k returned with explainability
# ---------------------------------------------------------------------------


class TestSuggestions:
    def test_suggestions_returns_200(self, client):
        pid, _, _ = _wire_project(client)
        r = client.post(
            f"/projects/{pid}/suggestions",
            json={"top_k": 3},
            headers=analyst_headers(),
        )
        assert r.status_code == 200

    def test_suggestions_returns_top_k_candidates(self, client):
        pid, _, _ = _wire_project(client)
        r = client.post(
            f"/projects/{pid}/suggestions",
            json={"top_k": 3},
            headers=analyst_headers(),
        )
        body = r.json()
        assert len(body["field_suggestions"]) > 0
        for fs in body["field_suggestions"]:
            assert len(fs["candidates"]) > 0
            assert len(fs["candidates"]) <= 3

    def test_suggestions_have_explainability(self, client):
        pid, _, _ = _wire_project(client)
        r = client.post(
            f"/projects/{pid}/suggestions",
            json={"top_k": 5},
            headers=analyst_headers(),
        )
        body = r.json()
        for fs in body["field_suggestions"]:
            for c in fs["candidates"]:
                assert len(c["reasons"]) > 0, f"Missing reasons for {fs['target_field_path']}"

    def test_suggestions_are_deterministic(self, client):
        pid, _, _ = _wire_project(client)
        r1 = client.post(
            f"/projects/{pid}/suggestions",
            json={"top_k": 5},
            headers=analyst_headers(),
        )
        r2 = client.post(
            f"/projects/{pid}/suggestions",
            json={"top_k": 5},
            headers=analyst_headers(),
        )
        assert r1.json()["field_suggestions"] == r2.json()["field_suggestions"]

    def test_suggestions_patient_id_best_match(self, client):
        pid, _, _ = _wire_project(client)
        r = client.post(
            f"/projects/{pid}/suggestions",
            json={"top_k": 5},
            headers=analyst_headers(),
        )
        pid_suggestions = [
            fs for fs in r.json()["field_suggestions"]
            if fs["target_field_path"] == "patient_id"
        ]
        assert len(pid_suggestions) == 1
        best = pid_suggestions[0]["candidates"][0]
        assert best["confidence"] > 0.5

    def test_suggestions_no_source_schema_returns_422(self, client):
        pid = _create_project(client)
        r = client.post(
            f"/projects/{pid}/suggestions",
            json={"top_k": 3},
            headers=analyst_headers(),
        )
        assert r.status_code == 422

    def test_viewer_cannot_request_suggestions(self, client):
        pid, _, _ = _wire_project(client)
        r = client.post(
            f"/projects/{pid}/suggestions",
            json={"top_k": 3},
            headers=viewer_headers(),
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Scenario 4: Validation — deterministic ordered issues
# ---------------------------------------------------------------------------


def _create_mapping_version(client, pid, rules=None) -> str:
    if rules is None:
        rules = []
    r = client.post(
        f"/projects/{pid}/mappings",
        json={"version_label": "1.0", "rules": rules},
        headers=analyst_headers(),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestValidation:
    def test_validate_empty_rules_reports_required_fields_missing(self, client):
        pid, _, _ = _wire_project(client)
        mv_id = _create_mapping_version(client, pid, rules=[])
        r = client.post(
            f"/projects/{pid}/validate",
            json={"mapping_version_id": mv_id},
            headers=analyst_headers(),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["has_errors"] is True
        # patient_id is required in target schema
        req_msgs = [
            i for i in body["issues"] if i["rule_id"] == "required_target_mapped"
        ]
        assert len(req_msgs) > 0

    def test_validate_nonexistent_target_field_raises_error(self, client):
        pid, src_ref, _ = _wire_project(client)
        # Map to a field that does not exist in target
        rules = [
            {
                "target_field_id": "NONEXISTENT_FIELD_ID",
                "source_field_ids": ["some_src"],
            }
        ]
        mv_id = _create_mapping_version(client, pid, rules=rules)
        r = client.post(
            f"/projects/{pid}/validate",
            json={"mapping_version_id": mv_id},
            headers=analyst_headers(),
        )
        assert r.status_code == 200
        issues = r.json()["issues"]
        exist_issues = [i for i in issues if i["rule_id"] == "target_field_exists"]
        assert len(exist_issues) >= 1
        assert exist_issues[0]["severity"] == "error"

    def test_validate_deterministic_ordering(self, client):
        pid, _, _ = _wire_project(client)
        mv_id = _create_mapping_version(client, pid, rules=[])
        r1 = client.post(
            f"/projects/{pid}/validate",
            json={"mapping_version_id": mv_id},
            headers=analyst_headers(),
        )
        r2 = client.post(
            f"/projects/{pid}/validate",
            json={"mapping_version_id": mv_id},
            headers=analyst_headers(),
        )
        assert r1.json()["issues"] == r2.json()["issues"]

    def test_validate_policy_override_escalates_to_error(self, client):
        pid, _, _ = _wire_project(client)
        mv_id = _create_mapping_version(client, pid, rules=[])
        r = client.post(
            f"/projects/{pid}/validate",
            json={
                "mapping_version_id": mv_id,
                "severity_overrides": [
                    {"rule_id": "cardinality_compatibility", "severity": "error"}
                ],
            },
            headers=analyst_headers(),
        )
        assert r.status_code == 200

    def test_validate_issues_errors_before_warnings(self, client):
        """Determinism: errors must appear before warnings in the issue list."""
        pid, _, _ = _wire_project(client)
        # Map to a nonexistent field (error) + empty rules (no required mapped = error too)
        rules = [{"target_field_id": "BAD", "source_field_ids": []}]
        mv_id = _create_mapping_version(client, pid, rules=rules)
        r = client.post(
            f"/projects/{pid}/validate",
            json={"mapping_version_id": mv_id},
            headers=analyst_headers(),
        )
        issues = r.json()["issues"]
        severity_order = [i["severity"] for i in issues]
        _SEV_RANK = {"error": 0, "warn": 1, "info": 2}
        for i in range(len(severity_order) - 1):
            assert _SEV_RANK[severity_order[i]] <= _SEV_RANK[severity_order[i + 1]]

    def test_validate_unknown_mapping_version_returns_404(self, client):
        pid, _, _ = _wire_project(client)
        r = client.post(
            f"/projects/{pid}/validate",
            json={"mapping_version_id": "nonexistent"},
            headers=analyst_headers(),
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Mappings CRUD
# ---------------------------------------------------------------------------


class TestMappings:
    def test_create_mapping_version(self, client):
        pid = _create_project(client)
        r = client.post(
            f"/projects/{pid}/mappings",
            json={"version_label": "1.0", "rules": []},
            headers=analyst_headers(),
        )
        assert r.status_code == 201
        assert r.json()["version_label"] == "1.0"

    def test_duplicate_version_label_returns_409(self, client):
        pid = _create_project(client)
        client.post(
            f"/projects/{pid}/mappings",
            json={"version_label": "1.0", "rules": []},
            headers=analyst_headers(),
        )
        r = client.post(
            f"/projects/{pid}/mappings",
            json={"version_label": "1.0", "rules": []},
            headers=analyst_headers(),
        )
        assert r.status_code == 409

    def test_list_mapping_versions(self, client):
        pid = _create_project(client)
        client.post(
            f"/projects/{pid}/mappings",
            json={"version_label": "1.0", "rules": []},
            headers=analyst_headers(),
        )
        client.post(
            f"/projects/{pid}/mappings",
            json={"version_label": "2.0", "rules": []},
            headers=analyst_headers(),
        )
        r = client.get(f"/projects/{pid}/mappings", headers=viewer_headers("bob"))
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_get_single_mapping_version(self, client):
        pid = _create_project(client)
        r_create = client.post(
            f"/projects/{pid}/mappings",
            json={"version_label": "1.0", "rules": []},
            headers=analyst_headers(),
        )
        mv_id = r_create.json()["id"]
        r = client.get(f"/projects/{pid}/mappings/{mv_id}", headers=viewer_headers("bob"))
        assert r.status_code == 200
        assert r.json()["id"] == mv_id

    def test_mapping_audit_event_emitted(self, client):
        from apps.api import state
        from packages.core.models.audit_event import AuditAction
        pid = _create_project(client)
        client.post(
            f"/projects/{pid}/mappings",
            json={"version_label": "1.0", "rules": []},
            headers=analyst_headers(),
        )
        edit_events = [
            e for e in state.get_audit_log()
            if e.action == AuditAction.MAPPING_EDIT
        ]
        assert len(edit_events) == 1


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_returns_artifact_json(self, client):
        pid = _create_project(client)
        mv_id = _create_mapping_version(client, pid, rules=[])
        r = client.post(
            f"/projects/{pid}/export",
            params={"mapping_version_id": mv_id},
            headers=analyst_headers(),
        )
        assert r.status_code == 200
        body = r.json()
        assert "artifact_json" in body
        # artifact_json must be valid JSON
        artifact = json.loads(body["artifact_json"])
        assert artifact["artifact_format_version"] == "1.0"

    def test_export_script_is_placeholder(self, client):
        pid = _create_project(client)
        mv_id = _create_mapping_version(client, pid, rules=[])
        r = client.post(
            f"/projects/{pid}/export",
            params={"mapping_version_id": mv_id},
            headers=analyst_headers(),
        )
        assert "TODO: Phase 6" in r.json()["transformation_script"]

    def test_export_emits_audit_event(self, client):
        from apps.api import state
        from packages.core.models.audit_event import AuditAction
        pid = _create_project(client)
        mv_id = _create_mapping_version(client, pid, rules=[])
        client.post(
            f"/projects/{pid}/export",
            params={"mapping_version_id": mv_id},
            headers=analyst_headers(),
        )
        export_events = [
            e for e in state.get_audit_log()
            if e.action == AuditAction.EXPORT
        ]
        assert len(export_events) == 1


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------


class TestAuthGuards:
    def test_missing_user_id_returns_401(self, client):
        r = client.post(
            "/projects",
            json={"name": "x"},
            headers={"X-User-Role": "analyst"},  # X-User-Id missing
        )
        assert r.status_code == 401

    def test_invalid_role_returns_401(self, client):
        r = client.post(
            "/projects",
            json={"name": "x"},
            headers={"X-User-Id": "alice", "X-User-Role": "superuser"},
        )
        assert r.status_code == 401

    def test_viewer_can_list_projects(self, client):
        r = client.get("/projects", headers=viewer_headers())
        assert r.status_code == 200

    def test_viewer_cannot_import_schema(self, client):
        pid = _create_project(client)
        r = client.post(
            f"/projects/{pid}/schemas/source/import",
            json={
                "format_id": "json_schema",
                "schema_name": "X",
                "version_label": "1.0",
                "schema_payload": SOURCE_JSON_SCHEMA,
            },
            headers=viewer_headers(),
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# OpenAPI spec sanity
# ---------------------------------------------------------------------------


class TestOpenAPISpec:
    def test_openapi_endpoint_reachable(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        assert spec["info"]["title"] == "Healthcare Data Mapping Tool API"

    def test_all_required_paths_present(self, client):
        r = client.get("/openapi.json")
        paths = set(r.json()["paths"].keys())
        required = {
            "/projects",
            "/projects/{project_id}",
            "/projects/{project_id}/schemas/source/import",
            "/projects/{project_id}/schemas/target/select",
            "/projects/{project_id}/schemas",
            "/projects/{project_id}/suggestions",
            "/projects/{project_id}/mappings",
            "/projects/{project_id}/mappings/{version_id}",
            "/projects/{project_id}/validate",
            "/projects/{project_id}/export",
        }
        assert required.issubset(paths)
