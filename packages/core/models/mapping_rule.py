"""Mapping Rule Model (FR-006).

A mapping rule connects one or more source canonical fields to a single target
canonical field, with optional transformation hints for script generation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TransformKind(str, Enum):
    """Categories of transformation hints.

    v1 provides the structural placeholder; actual transform logic is
    minimal.  Script generators in Phase 6 will interpret these.
    """

    DIRECT = "direct"  # 1-to-1 copy, no transformation
    CONCATENATE = "concatenate"  # join multiple source fields
    SPLIT = "split"  # split one source into parts
    LOOKUP = "lookup"  # code/terminology lookup
    CONSTANT = "constant"  # fixed value, no source field needed
    DEFAULT = "default"  # use source if present, else default
    CUSTOM = "custom"  # free-form expression (v2 expansion point)


@dataclass(frozen=True)
class TransformHint:
    """Declarative hint about how source values map to the target.

    This is a *description* of the intended transformation, not executable
    logic (RL-01: no execution in v1).
    """

    kind: TransformKind = TransformKind.DIRECT
    expression: Optional[str] = None  # human-readable or DSL placeholder

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"kind": self.kind.value}
        if self.expression is not None:
            d["expression"] = self.expression
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TransformHint:
        return cls(
            kind=TransformKind(data["kind"]),
            expression=data.get("expression"),
        )


@dataclass(frozen=True)
class MappingRule:
    """A single source-to-target field mapping rule.

    Attributes:
        id: Stable unique identifier for this rule.
        target_field_id: ID of the target CanonicalField.
        source_field_ids: IDs of one or more source CanonicalFields.
        transform: Optional hint describing the transformation.
        default_value: Value to use when source is absent.
        constant_value: Fixed value (overrides source).
        notes: Free-text justification or comment.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target_field_id: str = ""
    source_field_ids: List[str] = field(default_factory=list)
    transform: TransformHint = field(
        default_factory=lambda: TransformHint()
    )
    default_value: Optional[str] = None
    constant_value: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "target_field_id": self.target_field_id,
            "source_field_ids": list(self.source_field_ids),
            "transform": self.transform.to_dict(),
        }
        if self.default_value is not None:
            d["default_value"] = self.default_value
        if self.constant_value is not None:
            d["constant_value"] = self.constant_value
        if self.notes is not None:
            d["notes"] = self.notes
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MappingRule:
        return cls(
            id=data["id"],
            target_field_id=data["target_field_id"],
            source_field_ids=data.get("source_field_ids", []),
            transform=TransformHint.from_dict(data.get("transform", {"kind": "direct"})),
            default_value=data.get("default_value"),
            constant_value=data.get("constant_value"),
            notes=data.get("notes"),
        )
