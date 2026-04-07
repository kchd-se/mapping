"""Scoring strategies for the suggestion engine.

Each strategy is a callable conforming to the ScoringStrategy protocol.
New strategies can be added by creating a function (or class with __call__)
that accepts (source_field, target_field) and returns a StrategyScore.

Design:
- Strategies operate ONLY on CanonicalField objects (RL-05).
- No patient data is accessed (RL-02).
- Swedish character normalization is isolated in _normalize_name().
- Adding a new strategy requires NO changes to the engine — just register
  it in the strategy list passed to SuggestionEngine.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional, Protocol

from packages.core.models.canonical_schema import (
    CanonicalField,
    Cardinality,
    FieldType,
    FieldTypeCategory,
)

# ---------------------------------------------------------------------------
# Strategy protocol and result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyScore:
    """Score contribution from a single strategy.

    Attributes:
        name: Strategy identifier (used in explainability).
        score: Contribution in [0.0, 1.0].
        weight: How much this strategy contributes to the composite score.
        reason: Human-readable explanation for this factor.
        warning: Optional mismatch warning.
    """

    name: str
    score: float
    weight: float
    reason: str
    warning: Optional[str] = None


class ScoringStrategy(Protocol):
    """Protocol that all scoring strategies must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def weight(self) -> float: ...

    def score(
        self, source: CanonicalField, target: CanonicalField
    ) -> StrategyScore: ...


# ---------------------------------------------------------------------------
# Name normalization (Swedish-aware)
# ---------------------------------------------------------------------------

# Mapping for Swedish characters → ASCII equivalents used during comparison.
_SWEDISH_NORMALIZE: dict[str, str] = {
    "å": "a",
    "ä": "a",
    "ö": "o",
    "Å": "A",
    "Ä": "A",
    "Ö": "O",
}

_WORD_SEP_RE = re.compile(r"[_.\-/\s]+")


def _normalize_name(raw: str) -> str:
    """Normalize a field name for similarity comparison.

    Steps:
    1. Replace Swedish characters with ASCII equivalents.
    2. NFC-normalize remaining unicode.
    3. Lowercase.
    4. Split on common separators (_, ., -, /, whitespace).
    5. Rejoin with single underscore.
    """
    for src, dst in _SWEDISH_NORMALIZE.items():
        raw = raw.replace(src, dst)
    raw = unicodedata.normalize("NFC", raw)
    raw = raw.lower()
    parts = _WORD_SEP_RE.split(raw)
    return "_".join(p for p in parts if p)


def _token_set(normalized: str) -> set[str]:
    """Split a normalized name into tokens for set-based similarity."""
    return set(normalized.split("_"))


# ---------------------------------------------------------------------------
# Strategy 1: Name Similarity
# ---------------------------------------------------------------------------


class NameSimilarityStrategy:
    """Scores based on normalized name/path token overlap.

    Uses Jaccard similarity over tokenized, Swedish-normalized field names.
    Also considers the leaf name (last path segment) for bonus precision.
    """

    def __init__(self, weight: float = 0.35) -> None:
        self._weight = weight

    @property
    def name(self) -> str:
        return "name_similarity"

    @property
    def weight(self) -> float:
        return self._weight

    def score(
        self, source: CanonicalField, target: CanonicalField
    ) -> StrategyScore:
        src_path_norm = _normalize_name(source.path)
        tgt_path_norm = _normalize_name(target.path)

        # Exact normalized match
        if src_path_norm == tgt_path_norm:
            return StrategyScore(
                name=self.name,
                score=1.0,
                weight=self._weight,
                reason=f"Exact name match (normalized): '{source.path}' == '{target.path}'",
            )

        # Jaccard on full path tokens
        src_tokens = _token_set(src_path_norm)
        tgt_tokens = _token_set(tgt_path_norm)

        intersection = src_tokens & tgt_tokens
        union = src_tokens | tgt_tokens
        jaccard = len(intersection) / len(union) if union else 0.0

        # Leaf-name bonus: compare last segment only
        src_leaf = src_path_norm.rsplit("_", 1)[-1] if "_" in src_path_norm else src_path_norm
        tgt_leaf = tgt_path_norm.rsplit("_", 1)[-1] if "_" in tgt_path_norm else tgt_path_norm
        leaf_bonus = 0.2 if src_leaf == tgt_leaf and src_leaf else 0.0

        score = min(jaccard + leaf_bonus, 1.0)

        # Also check label if available
        if source.label and target.label:
            src_label = _normalize_name(source.label)
            tgt_label = _normalize_name(target.label)
            label_tokens_src = _token_set(src_label)
            label_tokens_tgt = _token_set(tgt_label)
            li = label_tokens_src & label_tokens_tgt
            lu = label_tokens_src | label_tokens_tgt
            label_jaccard = len(li) / len(lu) if lu else 0.0
            score = max(score, label_jaccard)

        reasons = []
        if score > 0:
            reasons.append(
                f"Name tokens overlap: {sorted(intersection)} "
                f"(Jaccard={jaccard:.2f}, leaf_bonus={leaf_bonus:.1f})"
            )
        else:
            reasons.append(f"No name similarity: '{source.path}' vs '{target.path}'")

        return StrategyScore(
            name=self.name,
            score=round(score, 4),
            weight=self._weight,
            reason=reasons[0],
        )


# ---------------------------------------------------------------------------
# Strategy 2: Type Compatibility
# ---------------------------------------------------------------------------

# Compatibility matrix for primitive type pairs.  Missing pairs default to 0.
_TYPE_COMPAT: dict[tuple[str, str], float] = {
    ("string", "string"): 1.0,
    ("integer", "integer"): 1.0,
    ("decimal", "decimal"): 1.0,
    ("boolean", "boolean"): 1.0,
    ("date", "date"): 1.0,
    ("datetime", "datetime"): 1.0,
    ("code", "code"): 1.0,
    ("uri", "uri"): 1.0,
    # Widening conversions (acceptable with warning)
    ("integer", "decimal"): 0.8,
    ("integer", "string"): 0.5,
    ("decimal", "string"): 0.5,
    ("boolean", "string"): 0.4,
    ("boolean", "integer"): 0.4,
    ("date", "datetime"): 0.8,
    ("date", "string"): 0.5,
    ("datetime", "string"): 0.5,
    ("code", "string"): 0.7,
    ("uri", "string"): 0.6,
}


class TypeCompatibilityStrategy:
    """Scores based on field type compatibility."""

    def __init__(self, weight: float = 0.25) -> None:
        self._weight = weight

    @property
    def name(self) -> str:
        return "type_compatibility"

    @property
    def weight(self) -> float:
        return self._weight

    def score(
        self, source: CanonicalField, target: CanonicalField
    ) -> StrategyScore:
        s_type = source.field_type
        t_type = target.field_type

        # Category match
        if s_type.category != t_type.category:
            # Object↔Primitive or Array↔Primitive: poor match
            return StrategyScore(
                name=self.name,
                score=0.1,
                weight=self._weight,
                reason=(
                    f"Type category mismatch: {s_type.category.value} vs "
                    f"{t_type.category.value}"
                ),
                warning=(
                    f"Type category mismatch: source is {s_type.category.value}, "
                    f"target expects {t_type.category.value}"
                ),
            )

        # Both same category
        if s_type.category == FieldTypeCategory.OBJECT:
            return StrategyScore(
                name=self.name,
                score=0.7,
                weight=self._weight,
                reason="Both fields are objects (structural match).",
            )

        if s_type.category == FieldTypeCategory.ARRAY:
            # Compare element types if available
            if s_type.items_type and t_type.items_type:
                inner_score = self._primitive_compat(
                    s_type.items_type.primitive, t_type.items_type.primitive
                )
                return StrategyScore(
                    name=self.name,
                    score=inner_score,
                    weight=self._weight,
                    reason=(
                        f"Array element type compat: "
                        f"{s_type.items_type.primitive} → {t_type.items_type.primitive} "
                        f"(score={inner_score:.2f})"
                    ),
                    warning=(
                        f"Array element type mismatch: {s_type.items_type.primitive} "
                        f"vs {t_type.items_type.primitive}"
                        if inner_score < 1.0
                        else None
                    ),
                )
            return StrategyScore(
                name=self.name,
                score=0.6,
                weight=self._weight,
                reason="Both fields are arrays (element types not specified).",
            )

        # Primitive vs primitive
        compat = self._primitive_compat(s_type.primitive, t_type.primitive)
        warning = None
        if compat < 1.0 and s_type.primitive != t_type.primitive:
            warning = (
                f"Type mismatch: source '{s_type.primitive}' → "
                f"target '{t_type.primitive}'"
            )
        return StrategyScore(
            name=self.name,
            score=compat,
            weight=self._weight,
            reason=(
                f"Primitive type compatibility: {s_type.primitive} → "
                f"{t_type.primitive} (score={compat:.2f})"
            ),
            warning=warning,
        )

    @staticmethod
    def _primitive_compat(src: Optional[str], tgt: Optional[str]) -> float:
        if src is None or tgt is None:
            return 0.3
        if src == tgt:
            return 1.0
        return _TYPE_COMPAT.get((src, tgt), _TYPE_COMPAT.get((tgt, src), 0.2))


# ---------------------------------------------------------------------------
# Strategy 3: Cardinality Compatibility
# ---------------------------------------------------------------------------


class CardinalityCompatibilityStrategy:
    """Scores based on min/max cardinality alignment."""

    def __init__(self, weight: float = 0.15) -> None:
        self._weight = weight

    @property
    def name(self) -> str:
        return "cardinality_compatibility"

    @property
    def weight(self) -> float:
        return self._weight

    def score(
        self, source: CanonicalField, target: CanonicalField
    ) -> StrategyScore:
        s = source.cardinality
        t = target.cardinality

        # Perfect match
        if s.min_occurs == t.min_occurs and s.max_occurs == t.max_occurs:
            return StrategyScore(
                name=self.name,
                score=1.0,
                weight=self._weight,
                reason="Cardinality match: identical min/max.",
            )

        warnings: List[str] = []
        penalty = 0.0

        # Required target (min>0) but optional source (min=0)
        if t.min_occurs > 0 and s.min_occurs == 0:
            penalty += 0.3
            warnings.append(
                f"Cardinality: target requires min={t.min_occurs} but "
                f"source allows min={s.min_occurs}"
            )

        # Multiple→single or single→multiple
        s_multi = s.max_occurs is None or (s.max_occurs is not None and s.max_occurs > 1)
        t_multi = t.max_occurs is None or (t.max_occurs is not None and t.max_occurs > 1)
        if s_multi and not t_multi:
            penalty += 0.3
            warnings.append(
                "Cardinality: source is multi-valued but target is single-valued"
            )
        elif not s_multi and t_multi:
            penalty += 0.1  # minor: single fits into multi

        score = max(1.0 - penalty, 0.0)
        warning_str = "; ".join(warnings) if warnings else None

        return StrategyScore(
            name=self.name,
            score=round(score, 4),
            weight=self._weight,
            reason=f"Cardinality compat score={score:.2f} (penalty={penalty:.2f})",
            warning=warning_str,
        )


# ---------------------------------------------------------------------------
# Strategy 4: Structural / Path Similarity
# ---------------------------------------------------------------------------


class PathSimilarityStrategy:
    """Scores based on hierarchy position (path depth and parent overlap)."""

    def __init__(self, weight: float = 0.15) -> None:
        self._weight = weight

    @property
    def name(self) -> str:
        return "path_similarity"

    @property
    def weight(self) -> float:
        return self._weight

    def score(
        self, source: CanonicalField, target: CanonicalField
    ) -> StrategyScore:
        src_parts = _normalize_name(source.path).split("_")
        tgt_parts = _normalize_name(target.path).split("_")

        # Depth similarity: penalize large depth differences
        depth_diff = abs(len(src_parts) - len(tgt_parts))
        depth_score = max(1.0 - depth_diff * 0.2, 0.0)

        # Parent overlap: compare all segments except the leaf
        src_parents = src_parts[:-1] if len(src_parts) > 1 else []
        tgt_parents = tgt_parts[:-1] if len(tgt_parts) > 1 else []
        if src_parents and tgt_parents:
            common = len(set(src_parents) & set(tgt_parents))
            total = max(len(set(src_parents) | set(tgt_parents)), 1)
            parent_score = common / total
        elif not src_parents and not tgt_parents:
            parent_score = 1.0  # both root-level
        else:
            parent_score = 0.3

        composite = 0.5 * depth_score + 0.5 * parent_score

        return StrategyScore(
            name=self.name,
            score=round(composite, 4),
            weight=self._weight,
            reason=(
                f"Path similarity: depth_score={depth_score:.2f}, "
                f"parent_overlap={parent_score:.2f}"
            ),
        )


# ---------------------------------------------------------------------------
# Strategy 5: Terminology Reference Alignment
# ---------------------------------------------------------------------------


class TerminologyAlignmentStrategy:
    """Scores based on shared terminology system references."""

    def __init__(self, weight: float = 0.10) -> None:
        self._weight = weight

    @property
    def name(self) -> str:
        return "terminology_alignment"

    @property
    def weight(self) -> float:
        return self._weight

    def score(
        self, source: CanonicalField, target: CanonicalField
    ) -> StrategyScore:
        s_refs = source.terminology_references
        t_refs = target.terminology_references

        if not s_refs and not t_refs:
            return StrategyScore(
                name=self.name,
                score=0.5,
                weight=self._weight,
                reason="No terminology references on either side (neutral).",
            )

        if not s_refs or not t_refs:
            return StrategyScore(
                name=self.name,
                score=0.3,
                weight=self._weight,
                reason="Terminology reference present on one side only.",
                warning=(
                    "Terminology mismatch: only "
                    f"{'source' if s_refs else 'target'} has terminology refs"
                ),
            )

        s_systems = {r.system for r in s_refs}
        t_systems = {r.system for r in t_refs}

        common_systems = s_systems & t_systems

        if common_systems:
            # Check if codes also match
            s_codes = {(r.system, r.code) for r in s_refs if r.code}
            t_codes = {(r.system, r.code) for r in t_refs if r.code}
            common_codes = s_codes & t_codes

            if common_codes:
                return StrategyScore(
                    name=self.name,
                    score=1.0,
                    weight=self._weight,
                    reason=(
                        f"Terminology systems AND codes match: "
                        f"{sorted(str(c) for c in common_codes)}"
                    ),
                )
            return StrategyScore(
                name=self.name,
                score=0.7,
                weight=self._weight,
                reason=(
                    f"Terminology systems match but codes differ: "
                    f"{sorted(common_systems)}"
                ),
            )

        return StrategyScore(
            name=self.name,
            score=0.2,
            weight=self._weight,
            reason="Terminology systems do not overlap.",
            warning="Different terminology systems referenced.",
        )


# ---------------------------------------------------------------------------
# Default strategy set
# ---------------------------------------------------------------------------

def default_strategies() -> List[ScoringStrategy]:
    """Return the default set of scoring strategies with standard weights.

    Weights sum to 1.0:
      name_similarity=0.35, type_compatibility=0.25,
      cardinality_compatibility=0.15, path_similarity=0.15,
      terminology_alignment=0.10
    """
    return [
        NameSimilarityStrategy(weight=0.35),
        TypeCompatibilityStrategy(weight=0.25),
        CardinalityCompatibilityStrategy(weight=0.15),
        PathSimilarityStrategy(weight=0.15),
        TerminologyAlignmentStrategy(weight=0.10),
    ]
