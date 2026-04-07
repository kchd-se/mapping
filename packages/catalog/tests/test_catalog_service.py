"""Unit tests for CatalogService.

Covers:
- Custom schema registration via JSON Schema and CSV adapters
- Standard schema registration
- Version overwrite protection (mandatory test)
- Multi-version support for same schema
- Retrieval by id + version label
- Latest-version resolution
- List with filters (schema_type, format_id, approval_status)
- Approval workflow
- Audit event emission on all catalog operations
- Checksum determinism across identical parses
"""

from __future__ import annotations

import pytest

from packages.adapters.defaults import register_defaults
from packages.adapters.registry import AdapterRegistry
from packages.catalog.catalog_service import (
    CatalogService,
    SchemaNotFoundError,
    SchemaVersionConflictError,
)
from packages.catalog.models.schema_descriptor import ApprovalStatus, SchemaType
from packages.core.models.audit_event import AuditAction
from packages.core.models.canonical_schema import CanonicalSchema, FieldType, FieldTypeCategory, CanonicalField, Cardinality


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIMPLE_JSON_SCHEMA = {
    "type": "object",
    "title": "Patient",
    "properties": {
        "patient_id": {"type": "integer"},
        "given_name": {"type": "string"},
        "birth_date": {"type": "string", "format": "date"},
    },
    "required": ["patient_id"],
}

_CSV_SCHEMA = (
    "name,type,required,label\n"
    "visit_id,integer,true,Visit ID\n"
    "visit_date,date,true,Visit Date\n"
    "reason,string,false,Reason\n"
)


def _make_service():
    registry = AdapterRegistry()
    register_defaults(registry)
    audit: list = []
    svc = CatalogService(adapter_registry=registry, audit_log=audit)
    return svc, audit


def _make_canonical():
    """Build a minimal CanonicalSchema without invoking an adapter."""
    return CanonicalSchema(
        id="cs-1",
        name="MinimalSchema",
        version="1.0",
        fields=[
            CanonicalField(
                id="f1",
                path="id",
                field_type=FieldType(
                    category=FieldTypeCategory.PRIMITIVE, primitive="integer"
                ),
                cardinality=Cardinality(min_occurs=1, max_occurs=1),
            )
        ],
        created_at="2026-01-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestCustomSchemaRegistration:
    def test_register_json_schema_creates_entry(self):
        svc, _ = _make_service()
        version = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        assert version.schema_id
        assert version.version_label == "1.0"
        assert version.checksum  # non-empty

    def test_register_csv_schema(self):
        svc, _ = _make_service()
        version = svc.register_custom_schema(
            raw_input=_CSV_SCHEMA,
            format_id="csv_schema",
            schema_name="Visit",
            version_label="1.0",
            owner="admin",
        )
        assert version.version_label == "1.0"
        entry = svc.get_entry(version.schema_id)
        assert entry.descriptor.schema_type == SchemaType.CUSTOM

    def test_descriptor_name_matches(self):
        svc, _ = _make_service()
        version = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        entry = svc.get_entry(version.schema_id)
        assert entry.descriptor.name == "Patient"

    def test_descriptor_owner_matches(self):
        svc, _ = _make_service()
        version = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="user@region.se",
        )
        entry = svc.get_entry(version.schema_id)
        assert entry.descriptor.owner == "user@region.se"

    def test_default_approval_status_is_draft(self):
        svc, _ = _make_service()
        version = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        entry = svc.get_entry(version.schema_id)
        assert entry.descriptor.approval_status == ApprovalStatus.DRAFT


class TestStandardSchemaRegistration:
    def test_register_standard_schema(self):
        svc, _ = _make_service()
        canonical = _make_canonical()
        version = svc.register_standard_schema(
            canonical=canonical,
            format_id="omop_cdm",
            schema_name="OMOP Person",
            version_label="5.4",
        )
        assert version.version_label == "5.4"
        entry = svc.get_entry(version.schema_id)
        assert entry.descriptor.schema_type == SchemaType.STANDARD


class TestVersionOverwriteProtection:
    """Mandatory test: same version label MUST NOT be registered twice."""

    def test_registering_same_version_raises_conflict(self):
        svc, _ = _make_service()
        svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        with pytest.raises(SchemaVersionConflictError):
            svc.register_custom_schema(
                raw_input=_SIMPLE_JSON_SCHEMA,
                format_id="json_schema",
                schema_name="Patient",
                version_label="1.0",
                owner="admin",
            )

    def test_different_version_labels_ok(self):
        svc, _ = _make_service()
        v1 = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        v2 = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="2.0",
            owner="admin",
        )
        assert v1.schema_id == v2.schema_id  # same entry
        assert v1.id != v2.id  # different version objects
        entry = svc.get_entry(v1.schema_id)
        assert len(entry.versions) == 2

    def test_same_name_different_format_creates_separate_entries(self):
        svc, _ = _make_service()
        v_json = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="MySchema",
            version_label="1.0",
            owner="admin",
        )
        v_csv = svc.register_custom_schema(
            raw_input=_CSV_SCHEMA,
            format_id="csv_schema",
            schema_name="MySchema",
            version_label="1.0",
            owner="admin",
        )
        assert v_json.schema_id != v_csv.schema_id


class TestRetrieval:
    def test_get_schema_version(self):
        svc, _ = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        retrieved = svc.get_schema_version(v.schema_id, "1.0")
        assert retrieved.id == v.id

    def test_get_latest_version_is_last_registered(self):
        svc, _ = _make_service()
        v1 = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        v2 = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="2.0",
            owner="admin",
        )
        latest = svc.get_latest_version(v1.schema_id)
        assert latest.id == v2.id

    def test_get_unknown_schema_raises(self):
        svc, _ = _make_service()
        with pytest.raises(SchemaNotFoundError):
            svc.get_entry("nonexistent-id")

    def test_get_unknown_version_raises(self):
        svc, _ = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        with pytest.raises(SchemaNotFoundError):
            svc.get_schema_version(v.schema_id, "99.0")


class TestListFilters:
    def _populate(self):
        svc, audit = _make_service()
        v_custom = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        v_csv = svc.register_custom_schema(
            raw_input=_CSV_SCHEMA,
            format_id="csv_schema",
            schema_name="Visit",
            version_label="1.0",
            owner="admin",
        )
        v_std = svc.register_standard_schema(
            canonical=_make_canonical(),
            format_id="omop_cdm",
            schema_name="OMOP Person",
            version_label="5.4",
        )
        return svc, v_custom, v_csv, v_std

    def test_list_all(self):
        svc, *_ = self._populate()
        assert len(svc.list_entries()) == 3

    def test_filter_by_schema_type_custom(self):
        svc, *_ = self._populate()
        custom = svc.list_entries(schema_type=SchemaType.CUSTOM)
        assert len(custom) == 2
        assert all(e.descriptor.schema_type == SchemaType.CUSTOM for e in custom)

    def test_filter_by_schema_type_standard(self):
        svc, *_ = self._populate()
        std = svc.list_entries(schema_type=SchemaType.STANDARD)
        assert len(std) == 1
        assert std[0].descriptor.format_id == "omop_cdm"

    def test_filter_by_format_id(self):
        svc, *_ = self._populate()
        json_entries = svc.list_entries(format_id="json_schema")
        assert len(json_entries) == 1
        assert json_entries[0].descriptor.name == "Patient"

    def test_filter_by_approval_status(self):
        svc, v_custom, _v_csv, v_std = self._populate()
        svc.approve_schema(v_custom.schema_id, actor="approver")
        approved = svc.list_entries(approval_status=ApprovalStatus.APPROVED)
        assert len(approved) == 1
        assert approved[0].descriptor.id == v_custom.schema_id


class TestApproval:
    def test_approve_schema_changes_status(self):
        svc, _ = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        svc.approve_schema(v.schema_id, actor="approver")
        assert svc.get_entry(v.schema_id).descriptor.approval_status == ApprovalStatus.APPROVED

    def test_approve_emits_audit_event(self):
        svc, audit = _make_service()
        v = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        svc.approve_schema(v.schema_id, actor="approver")
        approval_events = [e for e in audit if e.action == AuditAction.APPROVAL]
        assert len(approval_events) == 1
        assert approval_events[0].actor == "approver"


class TestAuditEmission:
    def test_registration_emits_audit_event(self):
        svc, audit = _make_service()
        svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        assert len(audit) == 1
        assert audit[0].action == AuditAction.SCHEMA_VERSION_CREATE
        assert audit[0].actor == "admin"

    def test_each_version_emits_one_event(self):
        svc, audit = _make_service()
        svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="1.0",
            owner="admin",
        )
        svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="Patient",
            version_label="2.0",
            owner="admin",
        )
        schema_events = [e for e in audit if e.action == AuditAction.SCHEMA_VERSION_CREATE]
        assert len(schema_events) == 2

    def test_audit_log_property_returns_copy(self):
        svc, audit = _make_service()
        log1 = svc.audit_log
        log1.append("tamper")  # mutate the copy
        assert len(svc.audit_log) == len(audit)  # original unaffected


class TestChecksum:
    def test_same_schema_content_same_checksum(self):
        svc, _ = _make_service()
        v1 = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="SchemaA",
            version_label="1.0",
            owner="admin",
        )
        v2 = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="SchemaA",
            version_label="2.0",
            owner="admin",
        )
        assert v1.checksum == v2.checksum  # same content regardless of version label

    def test_different_schema_content_different_checksum(self):
        svc, _ = _make_service()
        other_schema = {
            "type": "object",
            "properties": {"visit_id": {"type": "integer"}},
        }
        v1 = svc.register_custom_schema(
            raw_input=_SIMPLE_JSON_SCHEMA,
            format_id="json_schema",
            schema_name="SchemaX",
            version_label="1.0",
            owner="admin",
        )
        v2 = svc.register_custom_schema(
            raw_input=other_schema,
            format_id="json_schema",
            schema_name="SchemaY",
            version_label="1.0",
            owner="admin",
        )
        assert v1.checksum != v2.checksum
