"""CatalogEntry — groups a SchemaDescriptor with its available versions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from packages.catalog.models.schema_descriptor import SchemaDescriptor
from packages.catalog.models.schema_version import SchemaVersion


@dataclass
class CatalogEntry:
    """A catalog entry containing a descriptor and all registered versions.

    Versions are ordered by insertion order (chronological).
    The default_version_id points to the version used when no specific
    version is requested.
    """

    descriptor: SchemaDescriptor = field(
        default_factory=SchemaDescriptor
    )
    versions: List[SchemaVersion] = field(default_factory=list)
    default_version_id: Optional[str] = None

    def get_version(self, version_label: str) -> Optional[SchemaVersion]:
        """Return the version with *version_label*, or None if not found."""
        for v in self.versions:
            if v.version_label == version_label:
                return v
        return None

    def get_version_by_id(self, version_id: str) -> Optional[SchemaVersion]:
        """Return the version with *version_id*, or None if not found."""
        for v in self.versions:
            if v.id == version_id:
                return v
        return None

    def get_latest_version(self) -> Optional[SchemaVersion]:
        """Return the most recently added version, or None if no versions."""
        return self.versions[-1] if self.versions else None

    def has_version(self, version_label: str) -> bool:
        return any(v.version_label == version_label for v in self.versions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "descriptor": self.descriptor.to_dict(),
            "versions": [v.to_dict() for v in self.versions],
            "default_version_id": self.default_version_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CatalogEntry:
        return cls(
            descriptor=SchemaDescriptor.from_dict(data["descriptor"]),
            versions=[
                SchemaVersion.from_dict(v) for v in data.get("versions", [])
            ],
            default_version_id=data.get("default_version_id"),
        )
