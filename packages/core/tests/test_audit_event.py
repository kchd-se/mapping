"""Tests for the Audit Event Model."""

from packages.core.models.audit_event import AuditAction, AuditEvent


class TestAuditEvent:
    def test_roundtrip_full(self):
        evt = AuditEvent(
            id="evt-1",
            actor="user@region.se",
            action=AuditAction.MAPPING_EDIT,
            timestamp="2026-03-15T10:00:00+00:00",
            object_type="mapping_rule",
            object_id="rule-123",
            before={"target_field_id": "old"},
            after={"target_field_id": "new"},
            metadata={"ip": "10.0.0.1", "session": "abc"},
        )
        restored = AuditEvent.from_dict(evt.to_dict())
        assert restored == evt

    def test_roundtrip_minimal(self):
        evt = AuditEvent(
            id="evt-2",
            actor="system",
            action=AuditAction.SCHEMA_IMPORT,
            timestamp="2026-03-15T10:00:00+00:00",
        )
        restored = AuditEvent.from_dict(evt.to_dict())
        assert restored == evt
        assert restored.before is None
        assert restored.after is None

    def test_frozen(self):
        evt = AuditEvent(id="evt-3", actor="x", action=AuditAction.EXPORT)
        try:
            evt.actor = "y"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_metadata_sorted_in_dict(self):
        evt = AuditEvent(
            id="evt-4",
            actor="x",
            action=AuditAction.PUBLISH,
            timestamp="2026-01-01T00:00:00+00:00",
            metadata={"z_key": "1", "a_key": "2"},
        )
        keys = list(evt.to_dict()["metadata"].keys())
        assert keys == ["a_key", "z_key"]

    def test_all_actions_serializable(self):
        for action in AuditAction:
            evt = AuditEvent(
                id="evt",
                actor="a",
                action=action,
                timestamp="2026-01-01T00:00:00+00:00",
            )
            restored = AuditEvent.from_dict(evt.to_dict())
            assert restored.action == action
