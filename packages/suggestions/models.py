"""Suggestion Engine domain models.

These are pure data structures consumed by the suggestion engine and
returned to callers.  They contain NO format-specific logic (RL-05).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SuggestionCandidate:
    """A single mapping candidate for a target field.

    Attributes:
        source_field_ids: IDs of one or more source fields proposed for the mapping.
        confidence: Numeric score in [0.0, 1.0] — higher is better.
        reasons: Human-readable explainability lines (one per scoring factor).
        warnings: Mismatch warnings (type, cardinality, constraint, etc.).
    """

    source_field_ids: List[str]
    confidence: float
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_field_ids": list(self.source_field_ids),
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class FieldSuggestions:
    """Top-K candidates for a single target field.

    candidates is sorted by descending confidence (deterministic).
    """

    target_field_id: str
    target_field_path: str
    candidates: List[SuggestionCandidate] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_field_id": self.target_field_id,
            "target_field_path": self.target_field_path,
            "candidates": [c.to_dict() for c in self.candidates],
        }


@dataclass(frozen=True)
class SuggestionResult:
    """Complete suggestion output for a source→target schema pair.

    field_suggestions is sorted by target_field_path for determinism.
    """

    source_schema_id: str
    target_schema_id: str
    field_suggestions: List[FieldSuggestions] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_schema_id": self.source_schema_id,
            "target_schema_id": self.target_schema_id,
            "field_suggestions": [fs.to_dict() for fs in self.field_suggestions],
        }
