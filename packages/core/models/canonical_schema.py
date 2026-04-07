"""Canonical Schema Model — format-agnostic internal representation (FR-005).

This module defines the canonical schema that ALL adapters convert into and
ALL downstream features (suggestions, validation, UI, script-gen) consume.
No format-specific logic belongs here (RL-05).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class FieldTypeCategory(str, Enum):
    """Top-level category for a canonical field's type."""

    PRIMITIVE = "primitive"
    OBJECT = "object"
    ARRAY = "array"


@dataclass(frozen=True)
class FieldType:
    """Type descriptor for a canonical field.

    Attributes:
        category: Whether the field is primitive, object, or array.
        primitive: Specific primitive type name when category is PRIMITIVE
                   (e.g. "string", "integer", "boolean", "decimal", "date",
                   "datetime", "code", "uri").  Not an enum so that new types
                   can be introduced without changing this module.
        items_type: For ARRAY fields, the type of the array elements.
    """

    category: FieldTypeCategory
    primitive: Optional[str] = None
    items_type: Optional[FieldType] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"category": self.category.value}
        if self.primitive is not None:
            d["primitive"] = self.primitive
        if self.items_type is not None:
            d["items_type"] = self.items_type.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FieldType:
        items = data.get("items_type")
        return cls(
            category=FieldTypeCategory(data["category"]),
            primitive=data.get("primitive"),
            items_type=cls.from_dict(items) if items else None,
        )


@dataclass(frozen=True)
class Cardinality:
    """Occurrence constraints for a field."""

    min_occurs: int = 0
    max_occurs: Optional[int] = None  # None means unbounded

    def to_dict(self) -> Dict[str, Any]:
        return {"min_occurs": self.min_occurs, "max_occurs": self.max_occurs}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Cardinality:
        return cls(
            min_occurs=data["min_occurs"],
            max_occurs=data.get("max_occurs"),
        )


@dataclass(frozen=True)
class FieldConstraints:
    """Constraints on a canonical field's value.

    All fields are optional — only populated when the source schema
    declares them.
    """

    required: bool = False
    enums: Optional[List[str]] = None
    pattern: Optional[str] = None  # regex pattern
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"required": self.required}
        if self.enums is not None:
            d["enums"] = list(self.enums)
        if self.pattern is not None:
            d["pattern"] = self.pattern
        if self.min_value is not None:
            d["min_value"] = self.min_value
        if self.max_value is not None:
            d["max_value"] = self.max_value
        if self.min_length is not None:
            d["min_length"] = self.min_length
        if self.max_length is not None:
            d["max_length"] = self.max_length
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FieldConstraints:
        return cls(
            required=data.get("required", False),
            enums=data.get("enums"),
            pattern=data.get("pattern"),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            min_length=data.get("min_length"),
            max_length=data.get("max_length"),
        )


@dataclass(frozen=True)
class TerminologyReference:
    """Reference to an external code system or concept.

    Format-agnostic: can represent FHIR ValueSets, OMOP concept domains, or
    any other terminology system without hardcoding specifics (RL-03).
    """

    system: str  # e.g. "http://hl7.org/fhir/ValueSet/...", "OMOP:condition"
    code: Optional[str] = None
    display: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"system": self.system}
        if self.code is not None:
            d["code"] = self.code
        if self.display is not None:
            d["display"] = self.display
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TerminologyReference:
        return cls(
            system=data["system"],
            code=data.get("code"),
            display=data.get("display"),
        )


@dataclass(frozen=True)
class CanonicalField:
    """A single field in the canonical schema representation.

    This is the atomic unit that suggestions, validation, mapping UI, and
    script generation all operate on.
    """

    id: str
    path: str
    field_type: FieldType
    cardinality: Cardinality = field(default_factory=lambda: Cardinality())
    label: Optional[str] = None
    description: Optional[str] = None
    constraints: FieldConstraints = field(
        default_factory=lambda: FieldConstraints()
    )
    terminology_references: List[TerminologyReference] = field(
        default_factory=list
    )
    metadata_tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "path": self.path,
            "field_type": self.field_type.to_dict(),
            "cardinality": self.cardinality.to_dict(),
        }
        if self.label is not None:
            d["label"] = self.label
        if self.description is not None:
            d["description"] = self.description
        d["constraints"] = self.constraints.to_dict()
        d["terminology_references"] = [
            t.to_dict() for t in self.terminology_references
        ]
        d["metadata_tags"] = dict(sorted(self.metadata_tags.items()))
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CanonicalField:
        return cls(
            id=data["id"],
            path=data["path"],
            field_type=FieldType.from_dict(data["field_type"]),
            cardinality=Cardinality.from_dict(data["cardinality"]),
            label=data.get("label"),
            description=data.get("description"),
            constraints=FieldConstraints.from_dict(data.get("constraints", {})),
            terminology_references=[
                TerminologyReference.from_dict(t)
                for t in data.get("terminology_references", [])
            ],
            metadata_tags=data.get("metadata_tags", {}),
        )


@dataclass
class CanonicalSchema:
    """A complete schema in canonical form.

    Produced by input adapters; consumed by ALL core features.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = ""
    description: Optional[str] = None
    fields: List[CanonicalField] = field(default_factory=list)
    metadata_tags: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "fields": [f.to_dict() for f in self.fields],
            "metadata_tags": dict(sorted(self.metadata_tags.items())),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CanonicalSchema:
        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            description=data.get("description"),
            fields=[CanonicalField.from_dict(f) for f in data.get("fields", [])],
            metadata_tags=data.get("metadata_tags", {}),
            created_at=data["created_at"],
        )
