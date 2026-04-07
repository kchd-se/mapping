"""VersionPin — immutable reference from a mapping project to a schema version.

A pin is created once and never modified.  It permanently records which
schema version was active for a given project role at pin time, ensuring
reproducibility regardless of subsequent catalog evolution.

If a project needs a different version, a new pin is created.  The old
pin is not deleted; it remains auditable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class VersionPin:
    """Immutable link from (project, schema_role) → exact SchemaVersion.

    Attributes:
        id: Unique pin identifier.
        project_id: ID of the MappingProject that owns this pin.
        schema_role: Role descriptor — "source", "target", or a custom label
                     for multi-source projects.  Open string (not an enum)
                     so projects with unusual source configurations aren't
                     forced into a single vocabulary.
        schema_id: ID of the SchemaDescriptor in the catalog.
        schema_version_id: ID of the exact SchemaVersion being pinned.
        version_label: Human-readable label (denormalised for display without
                       a second catalog lookup).
        pinned_at: ISO-8601 UTC timestamp when the pin was created.
        pinned_by: Actor identity that created the pin.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    schema_role: str = ""
    schema_id: str = ""
    schema_version_id: str = ""
    version_label: str = ""
    pinned_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    pinned_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "schema_role": self.schema_role,
            "schema_id": self.schema_id,
            "schema_version_id": self.schema_version_id,
            "version_label": self.version_label,
            "pinned_at": self.pinned_at,
            "pinned_by": self.pinned_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VersionPin:
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            schema_role=data["schema_role"],
            schema_id=data["schema_id"],
            schema_version_id=data["schema_version_id"],
            version_label=data.get("version_label", ""),
            pinned_at=data["pinned_at"],
            pinned_by=data.get("pinned_by", ""),
        )
