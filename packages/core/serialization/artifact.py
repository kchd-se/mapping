"""Mapping Artifact Serialization.

Produces a deterministic, portable JSON artifact containing a mapping version
with full project and schema context.  Designed for export/import across
central and on-prem deployments (AC-06).

Determinism guarantees:
- Keys are sorted at every level.
- No floating-point instability (no float keys; numeric values are preserved).
- Output encoding is UTF-8; ensure_ascii=False for Swedish characters.
- Indent is fixed at 2 spaces for human readability.
- Trailing newline is always appended.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from packages.core.models.mapping_project import MappingProject
from packages.core.models.mapping_version import MappingVersion


_JSON_KWARGS = {
    "sort_keys": True,
    "indent": 2,
    "ensure_ascii": False,
}


class ArtifactFormatError(Exception):
    """Raised when an artifact cannot be parsed from serialized form."""


class MappingArtifact:
    """Container that bundles a project snapshot and mapping version for export.

    The artifact is the portable unit exchanged between deployments.
    """

    ARTIFACT_FORMAT_VERSION = "1.0"

    def __init__(
        self,
        project: MappingProject,
        version: MappingVersion,
    ) -> None:
        self.project = project
        self.version = version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_format_version": self.ARTIFACT_FORMAT_VERSION,
            "project": self.project.to_dict(),
            "version": self.version.to_dict(),
        }

    def serialize(self) -> str:
        """Produce a deterministic JSON string.

        Calling this twice with the same data MUST yield byte-identical output.
        """
        return json.dumps(self.to_dict(), **_JSON_KWARGS) + "\n"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MappingArtifact:
        fmt = data.get("artifact_format_version")
        if fmt != cls.ARTIFACT_FORMAT_VERSION:
            raise ArtifactFormatError(
                f"Unsupported artifact format version: {fmt!r} "
                f"(expected {cls.ARTIFACT_FORMAT_VERSION!r})"
            )
        return cls(
            project=MappingProject.from_dict(data["project"]),
            version=MappingVersion.from_dict(data["version"]),
        )

    @classmethod
    def deserialize(cls, raw: str) -> MappingArtifact:
        """Parse a JSON artifact string back into a MappingArtifact.

        Uses json.loads (safe structured parsing — RL-08).
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ArtifactFormatError(f"Invalid JSON: {exc}") from exc
        return cls.from_dict(data)
