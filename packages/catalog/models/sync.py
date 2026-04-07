"""Sync domain models — SyncPolicy, SyncJob, SyncAction.

No network I/O is represented here.  These models describe WHAT should
be synced (policy) and WHAT was done (job + actions).  Actual transfer
is performed by SyncService, which is designed with a hook for v2 to
replace local-copy transfer with real network operations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SyncDirection(str, Enum):
    """Conceptual direction of a sync operation.

    Used to document intent; the simulated v1 implementation always copies
    from the source catalog to the target catalog regardless of direction.
    A real v2 implementation would use this to decide which system initiates
    the network connection.
    """

    PULL = "pull"   # target pulls from source (on-prem ← central)
    PUSH = "push"   # source pushes to target (on-prem → central)
    BOTH = "both"   # bidirectional


class SyncScope(str, Enum):
    """Which catalog entries are eligible for this sync."""

    STANDARDS_ONLY = "standards_only"   # only SchemaType.STANDARD entries
    CUSTOM_ONLY = "custom_only"         # only SchemaType.CUSTOM entries
    APPROVED_ONLY = "approved_only"     # only entries with ApprovalStatus.APPROVED
    ALL = "all"                          # all entries regardless of type/status


@dataclass
class SyncPolicy:
    """Configuration that governs a controlled sync between catalog instances.

    No endpoint URLs or credentials are stored here (RL-11).
    The source/target are identified by logical catalog IDs; the binding to
    actual network addresses is the responsibility of deployment configuration.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    direction: SyncDirection = SyncDirection.PULL
    scope: SyncScope = SyncScope.ALL
    source_catalog_id: str = ""
    target_catalog_id: str = ""
    enabled: bool = True
    metadata_tags: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "direction": self.direction.value,
            "scope": self.scope.value,
            "source_catalog_id": self.source_catalog_id,
            "target_catalog_id": self.target_catalog_id,
            "enabled": self.enabled,
            "metadata_tags": dict(sorted(self.metadata_tags.items())),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SyncPolicy:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            direction=SyncDirection(data["direction"]),
            scope=SyncScope(data["scope"]),
            source_catalog_id=data["source_catalog_id"],
            target_catalog_id=data["target_catalog_id"],
            enabled=data.get("enabled", True),
            metadata_tags=data.get("metadata_tags", {}),
            created_at=data["created_at"],
        )


class SyncActionType(str, Enum):
    """Outcome of a single schema-version transfer decision."""

    SCHEMA_VERSION_ADDED = "schema_version_added"   # transferred successfully
    SCHEMA_SKIPPED = "schema_skipped"               # target already has this version
    SCHEMA_CONFLICT = "schema_conflict"             # same version label but different checksum
    SCHEMA_FILTERED = "schema_filtered"             # excluded by scope policy


@dataclass(frozen=True)
class SyncAction:
    """Immutable record of one transfer decision during a sync job."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    action_type: SyncActionType = SyncActionType.SCHEMA_VERSION_ADDED
    schema_id: str = ""
    schema_name: str = ""
    version_label: str = ""
    details: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "action_type": self.action_type.value,
            "schema_id": self.schema_id,
            "schema_name": self.schema_name,
            "version_label": self.version_label,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SyncAction:
        return cls(
            id=data["id"],
            job_id=data["job_id"],
            action_type=SyncActionType(data["action_type"]),
            schema_id=data["schema_id"],
            schema_name=data.get("schema_name", ""),
            version_label=data.get("version_label", ""),
            details=data.get("details", ""),
            timestamp=data["timestamp"],
        )


class SyncJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncJob:
    """Runtime record of a sync execution."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str = ""
    triggered_by: str = ""
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    status: SyncJobStatus = SyncJobStatus.PENDING
    actions: List[SyncAction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "triggered_by": self.triggered_by,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status.value,
            "actions": [a.to_dict() for a in self.actions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SyncJob:
        return cls(
            id=data["id"],
            policy_id=data["policy_id"],
            triggered_by=data.get("triggered_by", ""),
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            status=SyncJobStatus(data["status"]),
            actions=[SyncAction.from_dict(a) for a in data.get("actions", [])],
        )
