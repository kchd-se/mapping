"""Mapping Project Model (FR-001).

Top-level organisational unit that owns source schemas, a target schema,
mapping versions, status lifecycle, and audit history.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ProjectStatus(str, Enum):
    """Status lifecycle: Draft → Review → Approved → Published → Archived."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# Allowed transitions expressed as adjacency list.
_VALID_TRANSITIONS: Dict[ProjectStatus, List[ProjectStatus]] = {
    ProjectStatus.DRAFT: [ProjectStatus.REVIEW],
    ProjectStatus.REVIEW: [ProjectStatus.DRAFT, ProjectStatus.APPROVED],
    ProjectStatus.APPROVED: [ProjectStatus.PUBLISHED, ProjectStatus.DRAFT],
    ProjectStatus.PUBLISHED: [ProjectStatus.ARCHIVED],
    ProjectStatus.ARCHIVED: [],
}


class InvalidStatusTransition(Exception):
    """Raised when a project status transition is not permitted."""


class SensitivityClassification(str, Enum):
    """Data sensitivity classification for a mapping project."""

    HEALTHCARE_HIGHLY_SENSITIVE = "healthcare_highly_sensitive"
    HEALTHCARE_SENSITIVE = "healthcare_sensitive"
    INTERNAL = "internal"
    PUBLIC = "public"


@dataclass
class MappingProject:
    """A mapping project grouping schemas, mappings, and governance metadata.

    Attributes:
        id: Stable unique identifier.
        name: Human-readable project name.
        description: Optional project description.
        owner: Identity of the project owner (opaque string; auth is
               abstracted — simulated in v1, real in v2).
        status: Current lifecycle status.
        sensitivity: Data sensitivity classification.
        source_schema_ids: IDs of one or more source CanonicalSchemas.
        target_schema_id: ID of exactly one target CanonicalSchema.
        version_ids: Ordered list of MappingVersion IDs.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: Optional[str] = None
    owner: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    sensitivity: SensitivityClassification = (
        SensitivityClassification.HEALTHCARE_HIGHLY_SENSITIVE
    )
    source_schema_ids: List[str] = field(default_factory=list)
    target_schema_id: str = ""
    version_ids: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # -- Lifecycle helpers ---------------------------------------------------

    @staticmethod
    def valid_transitions(status: ProjectStatus) -> List[ProjectStatus]:
        """Return the list of statuses reachable from *status*."""
        return list(_VALID_TRANSITIONS.get(status, []))

    def transition_to(self, new_status: ProjectStatus) -> None:
        """Move the project to *new_status*, enforcing lifecycle rules."""
        allowed = _VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidStatusTransition(
                f"Cannot transition from {self.status.value!r} to "
                f"{new_status.value!r}. Allowed: "
                f"{[s.value for s in allowed]}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc).isoformat()

    # -- Serialization -------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "status": self.status.value,
            "sensitivity": self.sensitivity.value,
            "source_schema_ids": list(self.source_schema_ids),
            "target_schema_id": self.target_schema_id,
            "version_ids": list(self.version_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MappingProject:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            owner=data["owner"],
            status=ProjectStatus(data["status"]),
            sensitivity=SensitivityClassification(data["sensitivity"]),
            source_schema_ids=data.get("source_schema_ids", []),
            target_schema_id=data["target_schema_id"],
            version_ids=data.get("version_ids", []),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
