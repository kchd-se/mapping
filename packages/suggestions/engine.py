"""Suggestion Engine — schema-only TOP-K mapping candidate generator.

Design:
- Operates exclusively on CanonicalSchema / CanonicalField objects (RL-05).
- No patient data is accessed or required (RL-02).
- Returns TOP-K candidates per target field with confidence + explainability (RL-12).
- Deterministic: same inputs always produce the same ordered results.
  Determinism is achieved by:
    1. Sorting target fields by path before processing.
    2. Using a weighted-sum composite score (no randomness).
    3. Breaking ties by source field path (lexicographic).
    4. Rounding scores to 4 decimal places to avoid float instability.
- Extensible: scoring strategies are injected; adding a new strategy
  requires NO changes to this module.

Adding a new strategy:
    1. Create a class/function conforming to the ScoringStrategy protocol
       in strategies.py (needs name, weight, score(source, target) → StrategyScore).
    2. Add it to the list passed to SuggestionEngine(strategies=[...]).
    3. Done. No engine changes needed.
"""

from __future__ import annotations

from typing import List, Optional

from packages.core.models.canonical_schema import CanonicalField, CanonicalSchema
from packages.suggestions.models import (
    FieldSuggestions,
    SuggestionCandidate,
    SuggestionResult,
)
from packages.suggestions.semantic.interface import SemanticSimilarityProvider
from packages.suggestions.strategies import (
    ScoringStrategy,
    SemanticScoringStrategy,
    StrategyScore,
    default_strategies,
)


class SuggestionEngine:
    """Schema-only suggestion engine returning TOP-K candidates per target field.

    Args:
        strategies: List of scoring strategies. Defaults to
            strategies.default_strategies() if not provided.
        top_k: Maximum number of candidates to return per target field.
        min_confidence: Minimum composite score for a candidate to be included.
        semantic_provider: Optional SemanticSimilarityProvider.  When supplied,
            a SemanticScoringStrategy is appended to the strategy list.  The
            engine's weighted-average normalisation means existing strategy
            weights need no modification.
        semantic_weight: Weight for the semantic strategy when
            ``semantic_provider`` is given.  Default 0.15.
    """

    def __init__(
        self,
        strategies: Optional[List[ScoringStrategy]] = None,
        top_k: int = 5,
        min_confidence: float = 0.0,
        semantic_provider: Optional[SemanticSimilarityProvider] = None,
        semantic_weight: float = 0.15,
    ) -> None:
        base = strategies if strategies is not None else default_strategies()
        if semantic_provider is not None:
            base = list(base) + [
                SemanticScoringStrategy(semantic_provider, weight=semantic_weight)
            ]
        self._strategies = base
        self._top_k = top_k
        self._min_confidence = min_confidence

    def suggest(
        self,
        source_schema: CanonicalSchema,
        target_schema: CanonicalSchema,
    ) -> SuggestionResult:
        """Generate TOP-K mapping suggestions for every target field.

        Args:
            source_schema: The source canonical schema (fields to match FROM).
            target_schema: The target canonical schema (fields to match TO).

        Returns:
            A SuggestionResult with deterministic ordering.
        """
        source_fields = source_schema.fields
        # Sort target fields by path for deterministic output order.
        target_fields = sorted(target_schema.fields, key=lambda f: f.path)

        field_suggestions: List[FieldSuggestions] = []

        for target_field in target_fields:
            candidates = self._score_candidates(source_fields, target_field)
            field_suggestions.append(
                FieldSuggestions(
                    target_field_id=target_field.id,
                    target_field_path=target_field.path,
                    candidates=candidates,
                )
            )

        return SuggestionResult(
            source_schema_id=source_schema.id,
            target_schema_id=target_schema.id,
            field_suggestions=field_suggestions,
        )

    def _score_candidates(
        self,
        source_fields: List[CanonicalField],
        target_field: CanonicalField,
    ) -> List[SuggestionCandidate]:
        """Score all source fields against one target field, return TOP-K."""
        scored: List[tuple[float, str, SuggestionCandidate]] = []

        for source_field in source_fields:
            strategy_scores: List[StrategyScore] = []
            for strategy in self._strategies:
                ss = strategy.score(source_field, target_field)
                strategy_scores.append(ss)

            # Weighted sum of scores
            total_weight = sum(ss.weight for ss in strategy_scores)
            if total_weight > 0:
                composite = sum(
                    ss.score * ss.weight for ss in strategy_scores
                ) / total_weight
            else:
                composite = 0.0

            composite = round(composite, 4)

            if composite < self._min_confidence:
                continue

            reasons = [ss.reason for ss in strategy_scores]
            warnings = [ss.warning for ss in strategy_scores if ss.warning]

            candidate = SuggestionCandidate(
                source_field_ids=[source_field.id],
                confidence=composite,
                reasons=reasons,
                warnings=warnings,
            )
            # Sort key: descending confidence, then ascending source path for tie-breaking
            scored.append((composite, source_field.path, candidate))

        # Deterministic sort: descending confidence, ascending path on tie
        scored.sort(key=lambda t: (-t[0], t[1]))

        return [entry[2] for entry in scored[: self._top_k]]
