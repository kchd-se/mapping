"""Unit tests for Version Pinning.

Covers:
- Creating an immutable pin
- Resolving the pinned CanonicalSchema
- Reproducibility: resolution is independent of catalog evolution
- Pin survives new versions being added to catalog
- Pin for nonexistent version raises
- Frozen pin cannot be mutated
- get_pins_for_project
- Audit event emitted on pin creation
"""

from __future__ import annotations

import pytest

from packages.adapters.defaults import register_defaults
from packages.adapters.registry import AdapterRegistry
from packages.catalog.catalog_service import (
    CatalogService,
    PinNotFoundError,
    SchemaNotFoundError,
)
from packages.catalog.models.version_pin import VersionPin
from packages.core.models.audit_event import AuditAction
from packages.core.models.canonical_schema import CanonicalSchema

_SCHEMA_A = {
    "type": "object",
    "title": "PatientV1",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
    },
    "required": ["id"],
}

_SCHEMA_A_V2 = {
    "type": "object",
    "title": "PatientV2",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "ssn": {"type": "string"},     # new field in v2
    },
    "required": ["id"],
}


def _make_service():
    registry = AdapterRegistry()
    register_defaults(registry)
    audit: list = []
    return CatalogService(adapter_registry=registry, audit_log=audit), audit


class TestVersionPinCreation:
    def test_pin_returns_version_pin(self):
        svc, _ = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SCHEMA_A,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        pin = svc.pin_version(
            project_id="proj-1",
            schema_role="source",
            schema_id=v.schema_id,
            version_label="1.0",
            actor="analyst",
        )
        assert isinstance(pin, VersionPin)
        assert pin.project_id == "proj-1"
        assert pin.schema_role == "source"
        assert pin.schema_id == v.schema_id
        assert pin.version_label == "1.0"
        assert pin.pinned_by == "analyst"
        assert pin.schema_version_id == v.id

    def test_pin_for_nonexistent_schema_raises(self):
        svc, _ = _make_service()
        with pytest.raises(SchemaNotFoundError):
            svc.pin_version(
                project_id="proj-1",
                schema_role="source",
                schema_id="bad-schema-id",
                version_label="1.0",
                actor="analyst",
            )

    def test_pin_for_nonexistent_version_raises(self):
        svc, _ = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SCHEMA_A,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        with pytest.raises(SchemaNotFoundError):
            svc.pin_version(
                project_id="proj-1",
                schema_role="source",
                schema_id=v.schema_id,
                version_label="99.0",  # does not exist
                actor="analyst",
            )

    def test_pin_is_frozen(self):
        svc, _ = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SCHEMA_A,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        pin = svc.pin_version(
            project_id="proj-1",
            schema_role="source",
            schema_id=v.schema_id,
            version_label="1.0",
            actor="analyst",
        )
        with pytest.raises(AttributeError):
            pin.project_id = "different-project"  # type: ignore[misc]


class TestVersionPinResolution:
    def test_resolve_pin_returns_canonical_schema(self):
        svc, _ = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SCHEMA_A,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        pin = svc.pin_version(
            project_id="proj-1",
            schema_role="source",
            schema_id=v.schema_id,
            version_label="1.0",
            actor="analyst",
        )
        resolved = svc.resolve_pin(pin.id)
        assert isinstance(resolved, CanonicalSchema)
        assert resolved.name == "Patient"

    def test_resolved_schema_has_expected_fields(self):
        svc, _ = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SCHEMA_A,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        pin = svc.pin_version(
            project_id="proj-1",
            schema_role="source",
            schema_id=v.schema_id,
            version_label="1.0",
            actor="analyst",
        )
        resolved = svc.resolve_pin(pin.id)
        paths = {f.path for f in resolved.fields}
        assert "id" in paths
        assert "name" in paths

    def test_pin_resolves_same_schema_after_catalog_evolves(self):
        """Mandatory: pin resolution is independent of subsequent catalog changes."""
        svc, _ = _make_service()
        v1 = svc.register_custom_schema(
            raw_input=_SCHEMA_A,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        pin = svc.pin_version(
            project_id="proj-1",
            schema_role="source",
            schema_id=v1.schema_id,
            version_label="1.0",
            actor="analyst",
        )
        # Add a new version to the catalog (simulates catalog evolution)
        svc.register_custom_schema(
            raw_input=_SCHEMA_A_V2,
            format_id="json_schema",
            schema_name="Patient",
            version_label="2.0",
            owner="admin",
        )
        # Latest version is now 2.0, but pin still resolves to 1.0
        resolved = svc.resolve_pin(pin.id)
        paths = {f.path for f in resolved.fields}
        assert "ssn" not in paths  # v2 added ssn — it should NOT be here
        assert "id" in paths

    def test_two_pins_on_same_schema_different_versions_independent(self):
        """Two pins on different versions resolve independently."""
        svc, _ = _make_service()
        v1 = svc.register_custom_schema(
            raw_input=_SCHEMA_A,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        v2 = svc.register_custom_schema(
            raw_input=_SCHEMA_A_V2,
            format_id="json_schema",
            schema_name="Patient",
            version_label="2.0",
            owner="admin",
        )
        pin1 = svc.pin_version(
            project_id="proj-1",
            schema_role="source",
            schema_id=v1.schema_id,
            version_label="1.0",
            actor="a",
        )
        pin2 = svc.pin_version(
            project_id="proj-2",
            schema_role="source",
            schema_id=v2.schema_id,
            version_label="2.0",
            actor="a",
        )
        resolved1 = svc.resolve_pin(pin1.id)
        resolved2 = svc.resolve_pin(pin2.id)

        paths1 = {f.path for f in resolved1.fields}
        paths2 = {f.path for f in resolved2.fields}

        assert "ssn" not in paths1
        assert "ssn" in paths2

    def test_resolve_unknown_pin_raises(self):
        svc, _ = _make_service()
        with pytest.raises(PinNotFoundError):
            svc.resolve_pin("nonexistent-pin-id")


class TestGetPinsForProject:
    def test_returns_only_pins_for_project(self):
        svc, _ = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SCHEMA_A,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        svc.pin_version("proj-A", "source", v.schema_id, "1.0", "a")
        svc.pin_version("proj-A", "target", v.schema_id, "1.0", "a")
        svc.pin_version("proj-B", "source", v.schema_id, "1.0", "a")

        pins_A = svc.get_pins_for_project("proj-A")
        assert len(pins_A) == 2
        assert all(p.project_id == "proj-A" for p in pins_A)

        pins_B = svc.get_pins_for_project("proj-B")
        assert len(pins_B) == 1

    def test_project_with_no_pins_returns_empty_list(self):
        svc, _ = _make_service()
        assert svc.get_pins_for_project("no-such-project") == []


class TestPinAuditEmission:
    def test_pin_emits_audit_event(self):
        svc, audit = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SCHEMA_A,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        svc.pin_version(
            project_id="proj-1",
            schema_role="source",
            schema_id=v.schema_id,
            version_label="1.0",
            actor="analyst",
        )
        pin_events = [e for e in audit if e.action == AuditAction.VERSION_PIN]
        assert len(pin_events) == 1
        assert pin_events[0].actor == "analyst"
        assert pin_events[0].after["project_id"] == "proj-1"

    def test_version_pin_round_trip_serialization(self):
        svc, _ = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SCHEMA_A,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        pin = svc.pin_version(
            project_id="proj-1",
            schema_role="target",
            schema_id=v.schema_id,
            version_label="1.0",
            actor="analyst",
        )
        restored = VersionPin.from_dict(pin.to_dict())
        assert restored == pin
