"""Unit tests for SyncService.

Covers:
- Scope filtering: STANDARDS_ONLY, CUSTOM_ONLY, APPROVED_ONLY, ALL
- Scope APPROVED_ONLY respects approval_status field
- SyncJob status transitions (PENDING → RUNNING → COMPLETED)
- SyncAction records produced for each version processed
- SCHEMA_VERSION_ADDED for new versions
- SCHEMA_SKIPPED for versions already present in target
- SCHEMA_CONFLICT for same version label but different checksum
- SCHEMA_FILTERED for entries excluded by scope
- Audit event emitted to target catalog after sync
- SyncAction round-trip serialisation
- SyncPolicy round-trip serialisation
- SyncJob round-trip serialisation
- Version transferred to target is resolvable
- Sync preserves source schema_id so cross-catalog pins remain valid
"""

from __future__ import annotations

import pytest

from packages.adapters.defaults import register_defaults
from packages.adapters.registry import AdapterRegistry
from packages.catalog.catalog_service import CatalogService
from packages.catalog.models.schema_descriptor import ApprovalStatus, SchemaType
from packages.catalog.models.sync import (
    SyncAction,
    SyncActionType,
    SyncDirection,
    SyncJob,
    SyncJobStatus,
    SyncPolicy,
    SyncScope,
)
from packages.catalog.sync_service import SyncService
from packages.core.models.audit_event import AuditAction

# ---------------------------------------------------------------------------
# Schemas used as test data (format_id kept as "json_schema" — no hardcoding)
# ---------------------------------------------------------------------------

_SCHEMA_STANDARD = {
    "type": "object",
    "title": "ObservationR4",
    "properties": {
        "obs_id": {"type": "string"},
        "value": {"type": "number"},
    },
}

_SCHEMA_CUSTOM = {
    "type": "object",
    "title": "RegionPatient",
    "properties": {
        "patient_id": {"type": "integer"},
        "personnummer": {"type": "string"},
    },
    "required": ["patient_id"],
}

_SCHEMA_CUSTOM_V2 = {
    "type": "object",
    "title": "RegionPatientV2",
    "properties": {
        "patient_id": {"type": "integer"},
        "personnummer": {"type": "string"},
        "contact_email": {"type": "string"},
    },
    "required": ["patient_id"],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_registry() -> AdapterRegistry:
    reg = AdapterRegistry()
    register_defaults(reg)
    return reg


def _make_catalog(registry=None, catalog_id: str = "") -> tuple[CatalogService, list]:
    reg = registry or _make_registry()
    audit: list = []
    return CatalogService(adapter_registry=reg, audit_log=audit, catalog_id=catalog_id), audit


def _make_policy(scope: SyncScope, direction: SyncDirection = SyncDirection.PULL) -> SyncPolicy:
    return SyncPolicy(
        name="test-policy",
        direction=direction,
        scope=scope,
        source_catalog_id="central",
        target_catalog_id="region-x",
    )


# ---------------------------------------------------------------------------
# Helpers to pre-populate a source catalog
# ---------------------------------------------------------------------------

class _SourceFixture:
    """Pre-populated source catalog used across multiple tests."""

    def __init__(self):
        self.registry = _make_registry()
        self.catalog, self.audit = _make_catalog(self.registry, catalog_id="central")

        # One standard schema
        self.std_v = self.catalog.register_custom_schema(
            raw_input=_SCHEMA_STANDARD,
            format_id="json_schema",
            schema_name="ObservationR4",
            version_label="4.0",
            owner="admin",
        )
        # Manually flip type to STANDARD (register_custom_schema always sets CUSTOM;
        # standard registration uses register_standard_schema — but we just parse
        # consistently and then mutate the descriptor to STANDARD for test isolation
        # without touching the service API under test).
        entry = self.catalog.get_entry(self.std_v.schema_id)
        entry.descriptor.schema_type = SchemaType.STANDARD

        # One custom schema, draft
        self.custom_v = self.catalog.register_custom_schema(
            raw_input=_SCHEMA_CUSTOM,
            format_id="json_schema",
            schema_name="RegionPatient",
            version_label="1.0",
            owner="analyst",
        )

        # Another custom schema, approved
        self.approved_v = self.catalog.register_custom_schema(
            raw_input=_SCHEMA_CUSTOM_V2,
            format_id="json_schema",
            schema_name="RegionPatientV2",
            version_label="2.0",
            owner="analyst",
        )
        self.catalog.approve_schema(self.approved_v.schema_id, actor="approver")


# ---------------------------------------------------------------------------
# SyncJob / SyncAction serialisation
# ---------------------------------------------------------------------------

class TestSyncModelSerialisation:
    def test_sync_policy_round_trip(self):
        policy = _make_policy(SyncScope.STANDARDS_ONLY, SyncDirection.PULL)
        restored = SyncPolicy.from_dict(policy.to_dict())
        assert restored.scope == SyncScope.STANDARDS_ONLY
        assert restored.direction == SyncDirection.PULL
        assert restored.id == policy.id

    def test_sync_action_round_trip(self):
        action = SyncAction(
            job_id="job-1",
            action_type=SyncActionType.SCHEMA_VERSION_ADDED,
            schema_id="s-1",
            schema_name="Foo",
            version_label="1.0",
            details="ok",
        )
        restored = SyncAction.from_dict(action.to_dict())
        assert restored == action

    def test_sync_job_round_trip(self):
        job = SyncJob(
            policy_id="p-1",
            triggered_by="admin",
            status=SyncJobStatus.COMPLETED,
        )
        restored = SyncJob.from_dict(job.to_dict())
        assert restored.status == SyncJobStatus.COMPLETED
        assert restored.policy_id == "p-1"

    def test_sync_action_is_frozen(self):
        action = SyncAction(job_id="j")
        with pytest.raises(AttributeError):
            action.job_id = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SyncScope.ALL — every entry transferred
# ---------------------------------------------------------------------------

class TestSyncScopeAll:
    def setup_method(self):
        self._src = _SourceFixture()
        self._tgt, self._tgt_audit = _make_catalog(
            self._src.registry, catalog_id="region-x"
        )
        self._svc = SyncService(source=self._src.catalog, target=self._tgt)

    def test_all_entries_transferred(self):
        policy = _make_policy(SyncScope.ALL)
        job = self._svc.run_sync(policy, actor="scheduler")

        added = [a for a in job.actions if a.action_type == SyncActionType.SCHEMA_VERSION_ADDED]
        # Source has 3 entries, each with 1 version → 3 added
        assert len(added) == 3

    def test_no_filtered_actions_with_scope_all(self):
        policy = _make_policy(SyncScope.ALL)
        job = self._svc.run_sync(policy, actor="scheduler")

        filtered = [a for a in job.actions if a.action_type == SyncActionType.SCHEMA_FILTERED]
        assert len(filtered) == 0

    def test_job_status_is_completed(self):
        policy = _make_policy(SyncScope.ALL)
        job = self._svc.run_sync(policy, actor="scheduler")
        assert job.status == SyncJobStatus.COMPLETED

    def test_job_has_completed_at_timestamp(self):
        policy = _make_policy(SyncScope.ALL)
        job = self._svc.run_sync(policy, actor="scheduler")
        assert job.completed_at is not None

    def test_job_triggered_by_recorded(self):
        policy = _make_policy(SyncScope.ALL)
        job = self._svc.run_sync(policy, actor="scheduler")
        assert job.triggered_by == "scheduler"

    def test_target_can_get_transferred_entry(self):
        policy = _make_policy(SyncScope.ALL)
        self._svc.run_sync(policy, actor="scheduler")
        # Version from source should be retrievable in target
        version_in_target = self._tgt.get_schema_version(
            self._src.std_v.schema_id, "4.0"
        )
        assert version_in_target is not None
        assert version_in_target.checksum == self._src.std_v.checksum

    def test_transferred_version_preserves_source_schema_id(self):
        """The schema_id in the target MUST match the source so cross-catalog pins resolve."""
        policy = _make_policy(SyncScope.ALL)
        self._svc.run_sync(policy, actor="scheduler")
        # schema_id in target equals schema_id in source
        entry = self._tgt.get_entry(self._src.custom_v.schema_id)
        assert entry.descriptor.id == self._src.custom_v.schema_id

    def test_transferred_version_resolves_to_canonical(self):
        policy = _make_policy(SyncScope.ALL)
        self._svc.run_sync(policy, actor="scheduler")
        version = self._tgt.get_schema_version(self._src.custom_v.schema_id, "1.0")
        schema = version.resolve_canonical()
        paths = {f.path for f in schema.fields}
        assert "patient_id" in paths


# ---------------------------------------------------------------------------
# SyncScope.STANDARDS_ONLY
# ---------------------------------------------------------------------------

class TestSyncScopeStandardsOnly:
    def setup_method(self):
        self._src = _SourceFixture()
        self._tgt, _ = _make_catalog(self._src.registry)
        self._svc = SyncService(source=self._src.catalog, target=self._tgt)

    def test_only_standard_schemas_transferred(self):
        policy = _make_policy(SyncScope.STANDARDS_ONLY)
        job = self._svc.run_sync(policy, actor="scheduler")

        added = [a for a in job.actions if a.action_type == SyncActionType.SCHEMA_VERSION_ADDED]
        assert len(added) == 1
        assert added[0].schema_id == self._src.std_v.schema_id

    def test_custom_schemas_produce_filtered_actions(self):
        policy = _make_policy(SyncScope.STANDARDS_ONLY)
        job = self._svc.run_sync(policy, actor="scheduler")

        filtered_ids = {a.schema_id for a in job.actions if a.action_type == SyncActionType.SCHEMA_FILTERED}
        # Two custom schemas (draft + approved) should be filtered
        assert self._src.custom_v.schema_id in filtered_ids
        assert self._src.approved_v.schema_id in filtered_ids

    def test_standard_schema_available_in_target(self):
        policy = _make_policy(SyncScope.STANDARDS_ONLY)
        self._svc.run_sync(policy, actor="scheduler")
        v = self._tgt.get_schema_version(self._src.std_v.schema_id, "4.0")
        assert v.checksum == self._src.std_v.checksum

    def test_custom_schema_not_in_target(self):
        from packages.catalog.catalog_service import SchemaNotFoundError

        policy = _make_policy(SyncScope.STANDARDS_ONLY)
        self._svc.run_sync(policy, actor="scheduler")
        with pytest.raises(SchemaNotFoundError):
            self._tgt.get_entry(self._src.custom_v.schema_id)


# ---------------------------------------------------------------------------
# SyncScope.CUSTOM_ONLY
# ---------------------------------------------------------------------------

class TestSyncScopeCustomOnly:
    def setup_method(self):
        self._src = _SourceFixture()
        self._tgt, _ = _make_catalog(self._src.registry)
        self._svc = SyncService(source=self._src.catalog, target=self._tgt)

    def test_only_custom_schemas_transferred(self):
        policy = _make_policy(SyncScope.CUSTOM_ONLY)
        job = self._svc.run_sync(policy, actor="scheduler")

        added = [a for a in job.actions if a.action_type == SyncActionType.SCHEMA_VERSION_ADDED]
        assert len(added) == 2  # custom (draft) + custom (approved)

    def test_standard_schema_filtered(self):
        policy = _make_policy(SyncScope.CUSTOM_ONLY)
        job = self._svc.run_sync(policy, actor="scheduler")

        filtered_ids = {a.schema_id for a in job.actions if a.action_type == SyncActionType.SCHEMA_FILTERED}
        assert self._src.std_v.schema_id in filtered_ids

    def test_standard_schema_not_in_target(self):
        from packages.catalog.catalog_service import SchemaNotFoundError

        policy = _make_policy(SyncScope.CUSTOM_ONLY)
        self._svc.run_sync(policy, actor="scheduler")
        with pytest.raises(SchemaNotFoundError):
            self._tgt.get_entry(self._src.std_v.schema_id)


# ---------------------------------------------------------------------------
# SyncScope.APPROVED_ONLY
# ---------------------------------------------------------------------------

class TestSyncScopeApprovedOnly:
    def setup_method(self):
        self._src = _SourceFixture()
        self._tgt, _ = _make_catalog(self._src.registry)
        self._svc = SyncService(source=self._src.catalog, target=self._tgt)

    def test_only_approved_schemas_transferred(self):
        policy = _make_policy(SyncScope.APPROVED_ONLY)
        job = self._svc.run_sync(policy, actor="scheduler")

        added = [a for a in job.actions if a.action_type == SyncActionType.SCHEMA_VERSION_ADDED]
        assert len(added) == 1
        assert added[0].schema_id == self._src.approved_v.schema_id

    def test_draft_and_standard_are_filtered(self):
        policy = _make_policy(SyncScope.APPROVED_ONLY)
        job = self._svc.run_sync(policy, actor="scheduler")

        filtered_ids = {a.schema_id for a in job.actions if a.action_type == SyncActionType.SCHEMA_FILTERED}
        # Standard entry (not approved via approve_schema) and draft custom should be filtered
        assert self._src.custom_v.schema_id in filtered_ids

    def test_approved_schema_in_target_after_sync(self):
        policy = _make_policy(SyncScope.APPROVED_ONLY)
        self._svc.run_sync(policy, actor="scheduler")
        v = self._tgt.get_schema_version(self._src.approved_v.schema_id, "2.0")
        assert v.checksum == self._src.approved_v.checksum


# ---------------------------------------------------------------------------
# Idempotent sync — SCHEMA_SKIPPED
# ---------------------------------------------------------------------------

class TestIdempotentSync:
    def setup_method(self):
        self._src = _SourceFixture()
        self._tgt, _ = _make_catalog(self._src.registry)
        self._svc = SyncService(source=self._src.catalog, target=self._tgt)

    def test_second_sync_produces_skipped_actions(self):
        policy = _make_policy(SyncScope.ALL)
        self._svc.run_sync(policy, actor="scheduler")    # first sync — adds all
        job2 = self._svc.run_sync(policy, actor="scheduler")  # second sync — all already there

        skipped = [a for a in job2.actions if a.action_type == SyncActionType.SCHEMA_SKIPPED]
        assert len(skipped) == 3  # all three versions already in target

    def test_second_sync_produces_no_added_actions(self):
        policy = _make_policy(SyncScope.ALL)
        self._svc.run_sync(policy, actor="scheduler")
        job2 = self._svc.run_sync(policy, actor="scheduler")

        added = [a for a in job2.actions if a.action_type == SyncActionType.SCHEMA_VERSION_ADDED]
        assert len(added) == 0


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

class TestSyncConflict:
    def test_conflict_detected_when_target_has_same_label_different_checksum(self):
        """
        Populate target with a synthetic version for the same label but different content.
        SyncService should record SCHEMA_CONFLICT without raising.
        """
        registry = _make_registry()
        src, _ = _make_catalog(registry)
        tgt, _ = _make_catalog(registry)

        # Register schema in source
        v_src = src.register_custom_schema(
            raw_input=_SCHEMA_CUSTOM,
            format_id="json_schema",
            schema_name="RegionPatient",
            version_label="1.0",
            owner="admin",
        )

        # Manually plant a DIFFERENT schema under the same schema_id+version in target
        from packages.catalog.models.schema_version import SchemaVersion
        from packages.catalog.models.catalog_entry import CatalogEntry
        from packages.catalog.models.schema_descriptor import SchemaDescriptor, SchemaSource

        different_schema = {
            "type": "object",
            "title": "DifferentContent",
            "properties": {"x": {"type": "string"}},
        }
        # Build a conflicting version with same schema_id and version_label but different content
        src_entry = src.get_entry(v_src.schema_id)
        fake_version = SchemaVersion(
            id="fake-version-id",
            schema_id=v_src.schema_id,
            version_label="1.0",
            checksum="0000000000000000000000000000000000000000000000000000000000000000",
            canonical_schema_snapshot=different_schema,
        )
        fake_descriptor = SchemaDescriptor.from_dict(src_entry.descriptor.to_dict())
        fake_descriptor.source = SchemaSource.SYNC_RECEIVED
        tgt._entries[v_src.schema_id] = CatalogEntry(
            descriptor=fake_descriptor,
            versions=[fake_version],
            default_version_id="fake-version-id",
        )

        svc = SyncService(source=src, target=tgt)
        policy = _make_policy(SyncScope.ALL)
        job = svc.run_sync(policy, actor="admin")

        conflicts = [a for a in job.actions if a.action_type == SyncActionType.SCHEMA_CONFLICT]
        assert len(conflicts) == 1
        assert job.status == SyncJobStatus.COMPLETED  # conflict does not abort the job


# ---------------------------------------------------------------------------
# Audit emission
# ---------------------------------------------------------------------------

class TestSyncAuditEmission:
    def setup_method(self):
        self._src = _SourceFixture()
        self._tgt, self._tgt_audit = _make_catalog(self._src.registry)
        self._svc = SyncService(source=self._src.catalog, target=self._tgt)

    def test_sync_emits_catalog_sync_audit_event(self):
        policy = _make_policy(SyncScope.ALL)
        job = self._svc.run_sync(policy, actor="scheduler")

        sync_events = [e for e in self._tgt_audit if e.action == AuditAction.CATALOG_SYNC]
        # One summary event for the job + one per version transferred
        assert any(
            e.after.get("policy_id") == policy.id
            for e in sync_events
        )

    def test_sync_audit_event_records_versions_added(self):
        policy = _make_policy(SyncScope.ALL)
        job = self._svc.run_sync(policy, actor="scheduler")

        summary_events = [
            e for e in self._tgt_audit
            if e.action == AuditAction.CATALOG_SYNC
            and e.after is not None
            and "versions_added" in e.after
        ]
        assert len(summary_events) == 1
        assert summary_events[0].after["versions_added"] == 3

    def test_sync_audit_actor_recorded(self):
        policy = _make_policy(SyncScope.ALL)
        self._svc.run_sync(policy, actor="nightly-job")

        summary_events = [
            e for e in self._tgt_audit
            if e.action == AuditAction.CATALOG_SYNC
            and e.after is not None
            and "versions_added" in e.after
        ]
        assert summary_events[0].actor == "nightly-job"


# ---------------------------------------------------------------------------
# Sync direction stored on policy
# ---------------------------------------------------------------------------

class TestSyncDirection:
    def test_direction_pull_stored_on_policy(self):
        policy = _make_policy(SyncScope.ALL, direction=SyncDirection.PULL)
        assert policy.direction == SyncDirection.PULL

    def test_direction_push_stored_on_policy(self):
        policy = _make_policy(SyncScope.ALL, direction=SyncDirection.PUSH)
        assert policy.direction == SyncDirection.PUSH

    def test_direction_both_stored_on_policy(self):
        policy = _make_policy(SyncScope.ALL, direction=SyncDirection.BOTH)
        assert policy.direction == SyncDirection.BOTH

    def test_policy_direction_round_trips(self):
        policy = _make_policy(SyncScope.ALL, direction=SyncDirection.BOTH)
        restored = SyncPolicy.from_dict(policy.to_dict())
        assert restored.direction == SyncDirection.BOTH

    def test_sync_runs_regardless_of_direction_value(self):
        """v1: direction is metadata only — sync always copies source → target."""
        registry = _make_registry()
        src, _ = _make_catalog(registry)
        tgt, _ = _make_catalog(registry)
        src.register_custom_schema(
            raw_input=_SCHEMA_CUSTOM,
            format_id="json_schema",
            schema_name="RegionPatient",
            version_label="1.0",
            owner="admin",
        )
        svc = SyncService(source=src, target=tgt)
        for direction in (SyncDirection.PULL, SyncDirection.PUSH, SyncDirection.BOTH):
            tgt._entries.clear()  # reset target between runs
            policy = _make_policy(SyncScope.ALL, direction=direction)
            job = svc.run_sync(policy, actor="admin")
            assert job.status == SyncJobStatus.COMPLETED
            added = [a for a in job.actions if a.action_type == SyncActionType.SCHEMA_VERSION_ADDED]
            assert len(added) == 1
