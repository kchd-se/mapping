"""Schema Version — immutable snapshot of a schema at a specific version.

Design:
- frozen=True enforces immutability at the object level.
- canonical_schema_snapshot stores the complete CanonicalSchema.to_dict()
  so that version resolution is self-contained and independent of what
  adapters or catalog state exists at resolution time.
- checksum is computed from schema CONTENT only (name, version, fields,
  constraints) — deliberately excludes volatile ids and timestamps so
  that the same schema content always produces the same fingerprint.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from packages.core.models.canonical_schema import CanonicalSchema

_CONTENT_KEYS = frozenset(
    {"name", "description", "fields", "metadata_tags"}
)
_JSON_KWARGS = {"sort_keys": True, "ensure_ascii": False}


def compute_checksum(canonical_schema: CanonicalSchema) -> str:
    """SHA-256 fingerprint derived from schema content only.

    Excludes volatile fields (id, created_at) so that two parsings of the
    same schema always yield the same checksum regardless of when or where
    they were produced.
    """
    full = canonical_schema.to_dict()
    content = {k: v for k, v in full.items() if k in _CONTENT_KEYS}
    raw = json.dumps(content, **_JSON_KWARGS)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SchemaVersion:
    """Immutable snapshot of a registered schema version.

    Once created, a SchemaVersion is never mutated.  The canonical_schema_snapshot
    stores the full CanonicalSchema dict so that resolve_canonical() can reconstruct
    the exact schema that existed at pin time, even after the catalog evolves.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_id: str = ""
    version_label: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    checksum: str = ""
    canonical_schema_snapshot: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None

    def resolve_canonical(self) -> CanonicalSchema:
        """Reconstruct the CanonicalSchema from the stored snapshot.

        This is catalog-independent: the snapshot is self-contained.
        """
        return CanonicalSchema.from_dict(self.canonical_schema_snapshot)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "schema_id": self.schema_id,
            "version_label": self.version_label,
            "created_at": self.created_at,
            "checksum": self.checksum,
            "canonical_schema_snapshot": self.canonical_schema_snapshot,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SchemaVersion:
        return cls(
            id=data["id"],
            schema_id=data["schema_id"],
            version_label=data.get("version_label", ""),
            created_at=data["created_at"],
            checksum=data["checksum"],
            canonical_schema_snapshot=data.get("canonical_schema_snapshot", {}),
            notes=data.get("notes"),
        )

    @classmethod
    def create(
        cls,
        schema_id: str,
        version_label: str,
        canonical_schema: CanonicalSchema,
        notes: Optional[str] = None,
    ) -> SchemaVersion:
        """Factory: create a new version with a computed content checksum."""
        checksum = compute_checksum(canonical_schema)
        return cls(
            id=str(uuid.uuid4()),
            schema_id=schema_id,
            version_label=version_label,
            created_at=datetime.now(timezone.utc).isoformat(),
            checksum=checksum,
            canonical_schema_snapshot=canonical_schema.to_dict(),
            notes=notes,
        )
