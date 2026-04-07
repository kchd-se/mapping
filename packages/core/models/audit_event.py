"""Audit Event Model (FR-015).

Append-only, tamper-evident audit log entries covering schema imports,
mapping edits, approvals, exports, and catalog sync actions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class AuditAction(str, Enum):
    """Types of auditable actions throughout the system."""

    SCHEMA_IMPORT = "schema_import"
    SCHEMA_UPDATE = "schema_update"
    SCHEMA_VERSION_CREATE = "schema_version_create"
    MAPPING_EDIT = "mapping_edit"
    MAPPING_ACCEPT = "mapping_accept"
    MAPPING_REJECT = "mapping_reject"
    MAPPING_OVERRIDE = "mapping_override"
    VERSION_CREATE = "version_create"
    VERSION_PIN = "version_pin"
    PROJECT_CREATE = "project_create"
    PROJECT_STATUS_CHANGE = "project_status_change"
    APPROVAL = "approval"
    PUBLISH = "publish"
    EXPORT = "export"
    CATALOG_SYNC = "catalog_sync"


@dataclass(frozen=True)
class AuditEvent:
    """A single audit log entry.

    Frozen to enforce append-only semantics at the model level (AC-05).
    The storage layer (Phase 3+) MUST persist these without allowing
    mutation or deletion.

    Attributes:
        id: Unique event identifier.
        actor: Identity of the user or system that performed the action.
        action: Categorised action type.
        timestamp: ISO-8601 UTC timestamp of the event.
        object_type: Type of the affected object (e.g. "project", "schema").
        object_id: ID of the affected object.
        before: Optional snapshot of state before the action.
        after: Optional snapshot of state after the action.
        metadata: Additional free-form context (e.g. IP, session ID).
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actor: str = ""
    action: AuditAction = AuditAction.MAPPING_EDIT
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    object_type: str = ""
    object_id: str = ""
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actor": self.actor,
            "action": self.action.value,
            "timestamp": self.timestamp,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "before": self.before,
            "after": self.after,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuditEvent:
        return cls(
            id=data["id"],
            actor=data["actor"],
            action=AuditAction(data["action"]),
            timestamp=data["timestamp"],
            object_type=data.get("object_type", ""),
            object_id=data.get("object_id", ""),
            before=data.get("before"),
            after=data.get("after"),
            metadata=data.get("metadata", {}),
        )
