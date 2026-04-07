"""Mapping Version Model.

A versioned snapshot of mapping rules tied to specific schema references,
enabling version history and deterministic script generation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from packages.core.models.mapping_rule import MappingRule


@dataclass(frozen=True)
class SchemaReference:
    """Lightweight pointer to a CanonicalSchema used in a mapping version.

    Captures enough identity to pin and reproduce the version later.
    """

    schema_id: str
    schema_name: str = ""
    schema_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SchemaReference:
        return cls(
            schema_id=data["schema_id"],
            schema_name=data.get("schema_name", ""),
            schema_version=data.get("schema_version", ""),
        )


@dataclass
class MappingVersion:
    """An immutable snapshot of a set of mapping rules at a point in time.

    Attributes:
        id: Stable unique version identifier.
        project_id: Parent MappingProject ID.
        version_label: Human-readable version string (e.g. "1.0.0").
        created_at: ISO-8601 timestamp when this version was created.
        source_schema_refs: References to source schemas at this version.
        target_schema_ref: Reference to the target schema.
        rules: The complete set of MappingRules in this version.
        notes: Optional release notes / change description.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    version_label: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source_schema_refs: List[SchemaReference] = field(default_factory=list)
    target_schema_ref: Optional[SchemaReference] = None
    rules: List[MappingRule] = field(default_factory=list)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "version_label": self.version_label,
            "created_at": self.created_at,
            "source_schema_refs": [r.to_dict() for r in self.source_schema_refs],
            "target_schema_ref": (
                self.target_schema_ref.to_dict()
                if self.target_schema_ref
                else None
            ),
            "rules": [r.to_dict() for r in self.rules],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MappingVersion:
        target_ref = data.get("target_schema_ref")
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            version_label=data.get("version_label", ""),
            created_at=data["created_at"],
            source_schema_refs=[
                SchemaReference.from_dict(r)
                for r in data.get("source_schema_refs", [])
            ],
            target_schema_ref=(
                SchemaReference.from_dict(target_ref) if target_ref else None
            ),
            rules=[MappingRule.from_dict(r) for r in data.get("rules", [])],
            notes=data.get("notes"),
        )
