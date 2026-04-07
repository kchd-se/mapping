"""Schema Descriptor — administrative metadata for a catalog entry.

The format_id field is a free string (not an enum) so new schema formats
can be registered without modifying catalog code (RL-03 / AC-03).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class SchemaType(str, Enum):
    """Whether the schema originates from this deployment or an external standard."""

    CUSTOM = "custom"
    STANDARD = "standard"


class SchemaSource(str, Enum):
    """How the schema entered this catalog instance."""

    UPLOADED = "uploaded"                  # submitted directly by a user
    EXTERNAL_REGISTRY = "external_registry"  # abstract reference to an online registry
    SYNC_RECEIVED = "sync_received"          # received via a controlled sync


class ApprovalStatus(str, Enum):
    """Approval lifecycle for catalog entries (controls APPROVED_ONLY sync scope)."""

    DRAFT = "draft"
    APPROVED = "approved"


@dataclass
class SchemaDescriptor:
    """Administrative metadata describing a schema registered in the catalog.

    The format_id field is an open string (e.g. "json_schema", "fhir_profile")
    so new formats never require catalog code changes (RL-03).
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    schema_type: SchemaType = SchemaType.CUSTOM
    format_id: str = ""
    source: SchemaSource = SchemaSource.UPLOADED
    owner: str = ""
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    description: Optional[str] = None
    metadata_tags: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "schema_type": self.schema_type.value,
            "format_id": self.format_id,
            "source": self.source.value,
            "owner": self.owner,
            "approval_status": self.approval_status.value,
            "description": self.description,
            "metadata_tags": dict(sorted(self.metadata_tags.items())),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SchemaDescriptor:
        return cls(
            id=data["id"],
            name=data["name"],
            schema_type=SchemaType(data["schema_type"]),
            format_id=data["format_id"],
            source=SchemaSource(data["source"]),
            owner=data["owner"],
            approval_status=ApprovalStatus(data.get("approval_status", "draft")),
            description=data.get("description"),
            metadata_tags=data.get("metadata_tags", {}),
            created_at=data["created_at"],
        )
