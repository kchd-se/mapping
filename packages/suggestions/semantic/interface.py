"""Semantic similarity interface definitions.

Defines the SemanticDescriptor data-object and the SemanticSimilarityProvider
protocol.  No concrete implementation lives here — it belongs in
default_provider.py or a user-supplied provider.

Design notes
------------
* SemanticDescriptor carries the context needed for semantic matching:
  table/resource name, field name, and an optional human-readable description.
  These are derived from CanonicalField metadata by the caller; this module
  has NO dependency on CanonicalField so the interface stays portable.
* SemanticSimilarityProvider is a Protocol, not an ABC.  Any object that
  provides a ``compute`` method with the right signature satisfies it without
  subclassing — keeping third-party integrations friction-free.
* SemanticScore returns both a numeric similarity and an explanation string
  so that the engine's explainability requirements (RL-12) are satisfied.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Descriptor — input to all providers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDescriptor:
    """Context-rich description of a field used for semantic matching.

    Attributes:
        table_name:   Name of the containing table / resource / object
                      (e.g. ``"care_site"``, ``"Patient"``).
        field_name:   Name of the field / column / element
                      (e.g. ``"care_site_name"``, ``"name"``).
        description:  Optional human-readable description extracted from the
                      schema (e.g. ``"Name of the care site"``).

    Conceptual semantic text (used by providers internally):
        ``"{table_name} {field_name} {description}"``
        e.g. ``"care_site care_site_name name of the care site"``
    """

    table_name: str
    field_name: str
    description: Optional[str] = None

    @property
    def semantic_text(self) -> str:
        """Single string combining all context, used by text-based providers."""
        parts = [self.table_name, self.field_name]
        if self.description:
            parts.append(self.description)
        return " ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Score — output from all providers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticScore:
    """Result of a semantic similarity computation.

    Attributes:
        similarity:   Numeric score in [0.0, 1.0] where 1.0 is a perfect match.
        explanation:  Human-readable string describing why the fields are
                      (or are not) semantically similar.  Must always be
                      populated — empty string is not acceptable.
    """

    similarity: float
    explanation: str

    def __post_init__(self) -> None:
        if not (0.0 <= self.similarity <= 1.0):
            raise ValueError(
                f"SemanticScore.similarity must be in [0, 1]; got {self.similarity}"
            )
        if not self.explanation:
            raise ValueError("SemanticScore.explanation must not be empty.")


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SemanticSimilarityProvider(Protocol):
    """Protocol that all semantic-similarity providers must satisfy.

    Providers must be:
    * Deterministic — same inputs always produce the same output.
    * Side-effect free — no network calls, no mutable shared state.
    * Dependency-free on specific ML or embedding libraries.

    Any class that implements ``compute`` with the signature below satisfies
    this protocol without subclassing it.
    """

    def compute(
        self,
        source: SemanticDescriptor,
        target: SemanticDescriptor,
    ) -> SemanticScore:
        """Compute semantic similarity between two field descriptors.

        Args:
            source: Descriptor for the source (from) field.
            target: Descriptor for the target (to) field.

        Returns:
            A SemanticScore with similarity in [0, 1] and a non-empty
            explanation string.
        """
        ...
