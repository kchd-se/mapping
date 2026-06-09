"""Unit tests for the Phase 4b semantic matching package.

Covers:
- SemanticDescriptor.semantic_text property (with/without description)
- SemanticScore validation: similarity out-of-range raises ValueError
- LexicalSemanticProvider: Protocol compliance (isinstance check)
- LexicalSemanticProvider: deterministic output (same inputs → same result)
- LexicalSemanticProvider: exact field-name match scores high
- LexicalSemanticProvider: completely unrelated fields score low
- LexicalSemanticProvider: partial/prefix field-name match
- LexicalSemanticProvider: shared vocabulary in description boosts score
- LexicalSemanticProvider: weight-sum validation raises ValueError
- LexicalSemanticProvider: explanation is non-empty and contains field names
- SemanticScoringStrategy: produces StrategyScore with correct name and weight
- SemanticScoringStrategy: flat path (no separator) handled gracefully
- _field_to_descriptor: dot-separated path → correct table/field split
- _field_to_descriptor: slash-separated path → correct table/field split
- _field_to_descriptor: flat path → both table and field equal full path
- SuggestionEngine: semantic_provider=None gives same results as default
- SuggestionEngine: semantic_provider enabled boosts semantically similar fields
"""

from __future__ import annotations

import pytest

from packages.core.models.canonical_schema import (
    CanonicalField,
    CanonicalSchema,
    Cardinality,
    FieldConstraints,
    FieldType,
    FieldTypeCategory,
)
from packages.suggestions.engine import SuggestionEngine
from packages.suggestions.semantic.default_provider import LexicalSemanticProvider
from packages.suggestions.semantic.interface import (
    SemanticDescriptor,
    SemanticScore,
    SemanticSimilarityProvider,
)
from packages.suggestions.strategies import (
    SemanticScoringStrategy,
    StrategyScore,
    _field_to_descriptor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str_type() -> FieldType:
    return FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="string")


def _make_field(
    id: str,
    path: str,
    description: str | None = None,
    ft: FieldType | None = None,
) -> CanonicalField:
    return CanonicalField(
        id=id,
        path=path,
        field_type=ft or _str_type(),
        description=description,
    )


def _make_schema(fields: list[CanonicalField], id: str = "s1") -> CanonicalSchema:
    return CanonicalSchema(id=id, name="test", fields=fields)


# ---------------------------------------------------------------------------
# SemanticDescriptor
# ---------------------------------------------------------------------------

class TestSemanticDescriptor:
    def test_semantic_text_without_description(self):
        d = SemanticDescriptor(table_name="patient", field_name="birth_date")
        assert d.semantic_text == "patient birth_date"

    def test_semantic_text_with_description(self):
        d = SemanticDescriptor(
            table_name="person",
            field_name="year_of_birth",
            description="The year when the person was born",
        )
        assert d.semantic_text == "person year_of_birth The year when the person was born"

    def test_semantic_text_empty_description_omitted(self):
        d = SemanticDescriptor(table_name="visit", field_name="visit_id", description="")
        # empty string is falsy — should not appear
        assert d.semantic_text == "visit visit_id"

    def test_frozen(self):
        d = SemanticDescriptor(table_name="t", field_name="f")
        with pytest.raises((AttributeError, TypeError)):
            d.table_name = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SemanticScore
# ---------------------------------------------------------------------------

class TestSemanticScore:
    def test_valid_similarity_lower_bound(self):
        s = SemanticScore(similarity=0.0, explanation="no match")
        assert s.similarity == 0.0

    def test_valid_similarity_upper_bound(self):
        s = SemanticScore(similarity=1.0, explanation="perfect")
        assert s.similarity == 1.0

    def test_similarity_out_of_range_negative(self):
        with pytest.raises(ValueError):
            SemanticScore(similarity=-0.001, explanation="bad")

    def test_similarity_out_of_range_above_one(self):
        with pytest.raises(ValueError):
            SemanticScore(similarity=1.001, explanation="bad")

    def test_empty_explanation_raises(self):
        with pytest.raises(ValueError):
            SemanticScore(similarity=0.5, explanation="")

    def test_frozen(self):
        s = SemanticScore(similarity=0.5, explanation="ok")
        with pytest.raises((AttributeError, TypeError)):
            s.similarity = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LexicalSemanticProvider — Protocol compliance
# ---------------------------------------------------------------------------

class TestLexicalProviderProtocol:
    def test_isinstance_check(self):
        provider = LexicalSemanticProvider()
        assert isinstance(provider, SemanticSimilarityProvider)


# ---------------------------------------------------------------------------
# LexicalSemanticProvider — determinism
# ---------------------------------------------------------------------------

class TestLexicalProviderDeterminism:
    def test_same_inputs_same_output(self):
        provider = LexicalSemanticProvider()
        src = SemanticDescriptor(table_name="patient", field_name="patient_id")
        tgt = SemanticDescriptor(table_name="person", field_name="person_id")
        r1 = provider.compute(src, tgt)
        r2 = provider.compute(src, tgt)
        assert r1.similarity == r2.similarity
        assert r1.explanation == r2.explanation

    def test_commutative_symmetry(self):
        """Similarity should be symmetric (A→B ≈ B→A)."""
        provider = LexicalSemanticProvider()
        a = SemanticDescriptor(table_name="patient", field_name="dob")
        b = SemanticDescriptor(table_name="person", field_name="birth_date")
        ab = provider.compute(a, b)
        ba = provider.compute(b, a)
        # Token overlap is symmetric; slight differences from field_bonus OK
        assert abs(ab.similarity - ba.similarity) <= 0.2


# ---------------------------------------------------------------------------
# LexicalSemanticProvider — scoring quality
# ---------------------------------------------------------------------------

class TestLexicalProviderScoring:
    """Scoring contract tests — relative ordering rather than exact values."""

    def _provider(self) -> LexicalSemanticProvider:
        return LexicalSemanticProvider()

    def test_identical_descriptors_score_high(self):
        p = self._provider()
        d = SemanticDescriptor(
            table_name="patient", field_name="patient_id", description="Patient identifier"
        )
        result = p.compute(d, d)
        assert result.similarity >= 0.8

    def test_exact_field_name_higher_than_unrelated(self):
        p = self._provider()
        src = SemanticDescriptor(table_name="orders", field_name="visit_id")
        same_name = SemanticDescriptor(table_name="encounters", field_name="visit_id")
        different = SemanticDescriptor(table_name="lab_results", field_name="value_as_number")
        score_same = p.compute(src, same_name).similarity
        score_diff = p.compute(src, different).similarity
        assert score_same > score_diff

    def test_unrelated_fields_score_low(self):
        p = self._provider()
        src = SemanticDescriptor(table_name="measurement", field_name="value_as_number")
        tgt = SemanticDescriptor(table_name="care_site", field_name="location_source_value")
        result = p.compute(src, tgt)
        # Completely different vocabularies — should be low
        assert result.similarity < 0.5

    def test_shared_description_boosts_score(self):
        """Fields with overlapping descriptions should score higher."""
        p = self._provider()
        src = SemanticDescriptor(
            table_name="visit",
            field_name="start_date",
            description="date when visit began",
        )
        tgt_with_desc = SemanticDescriptor(
            table_name="encounter",
            field_name="admission_date",
            description="date when patient was admitted",
        )
        tgt_no_desc = SemanticDescriptor(
            table_name="encounter",
            field_name="discharge_status",
        )
        score_with = p.compute(src, tgt_with_desc).similarity
        score_without = p.compute(src, tgt_no_desc).similarity
        assert score_with > score_without

    def test_field_name_prefix_match(self):
        """patient_dob vs patient_date_of_birth — shares 'patient' prefix."""
        p = self._provider()
        src = SemanticDescriptor(table_name="demographics", field_name="patient_dob")
        tgt = SemanticDescriptor(table_name="Person", field_name="patient_date_of_birth")
        result = p.compute(src, tgt)
        # At least a weak signal from shared prefix token "patient"
        assert result.similarity > 0.1


# ---------------------------------------------------------------------------
# LexicalSemanticProvider — weight validation
# ---------------------------------------------------------------------------

class TestLexicalProviderWeightValidation:
    def test_invalid_weights_raise(self):
        with pytest.raises(ValueError, match="sum to 1.0"):
            LexicalSemanticProvider(jaccard_weight=0.5, lcs_weight=0.3, field_name_weight=0.3)

    def test_custom_valid_weights_accepted(self):
        provider = LexicalSemanticProvider(
            jaccard_weight=0.6, lcs_weight=0.3, field_name_weight=0.1
        )
        d = SemanticDescriptor(table_name="t", field_name="f")
        result = provider.compute(d, d)
        assert 0.0 <= result.similarity <= 1.0


# ---------------------------------------------------------------------------
# LexicalSemanticProvider — explanation quality
# ---------------------------------------------------------------------------

class TestLexicalProviderExplanation:
    def test_explanation_non_empty(self):
        p = LexicalSemanticProvider()
        src = SemanticDescriptor(table_name="a", field_name="b")
        tgt = SemanticDescriptor(table_name="c", field_name="d")
        result = p.compute(src, tgt)
        assert result.explanation and len(result.explanation) > 10

    def test_explanation_mentions_table_or_field(self):
        p = LexicalSemanticProvider()
        src = SemanticDescriptor(table_name="hospital", field_name="patient_id")
        tgt = SemanticDescriptor(table_name="care_site", field_name="person_id")
        result = p.compute(src, tgt)
        # Explanation should reference the field or table context
        lower = result.explanation.lower()
        assert "hospital" in lower or "patient" in lower or "care" in lower or "person" in lower


# ---------------------------------------------------------------------------
# _field_to_descriptor helper
# ---------------------------------------------------------------------------

class TestFieldToDescriptor:
    def test_dot_separated_path(self):
        f = _make_field("1", "patient.patient_id")
        d = _field_to_descriptor(f)
        assert d.table_name == "patient"
        assert d.field_name == "patient_id"

    def test_slash_separated_path(self):
        f = _make_field("1", "Patient/birthDate")
        d = _field_to_descriptor(f)
        assert d.table_name == "Patient"
        assert d.field_name == "birthDate"

    def test_multi_segment_path_uses_first_and_last(self):
        f = _make_field("1", "schema.observation_period.start_date")
        d = _field_to_descriptor(f)
        assert d.table_name == "schema"
        assert d.field_name == "start_date"

    def test_flat_path_no_separator(self):
        f = _make_field("1", "patient_id")
        d = _field_to_descriptor(f)
        assert d.table_name == "patient_id"
        assert d.field_name == "patient_id"

    def test_description_propagated(self):
        f = _make_field("1", "person.year_of_birth", description="Birth year")
        d = _field_to_descriptor(f)
        assert d.description == "Birth year"

    def test_none_description_propagated(self):
        f = _make_field("1", "person.person_id")
        d = _field_to_descriptor(f)
        assert d.description is None


# ---------------------------------------------------------------------------
# SemanticScoringStrategy
# ---------------------------------------------------------------------------

class TestSemanticScoringStrategy:
    def _make_strategy(self, weight: float = 0.15) -> SemanticScoringStrategy:
        return SemanticScoringStrategy(LexicalSemanticProvider(), weight=weight)

    def test_name(self):
        s = self._make_strategy()
        assert s.name == "semantic_similarity"

    def test_weight_property(self):
        s = self._make_strategy(weight=0.20)
        assert s.weight == 0.20

    def test_invalid_weight_raises(self):
        with pytest.raises(ValueError):
            SemanticScoringStrategy(LexicalSemanticProvider(), weight=0.0)

    def test_score_returns_strategy_score(self):
        s = self._make_strategy()
        src = _make_field("a", "patient.patient_id")
        tgt = _make_field("b", "person.person_id")
        result = s.score(src, tgt)
        assert isinstance(result, StrategyScore)
        assert result.name == "semantic_similarity"
        assert 0.0 <= result.score <= 1.0
        assert result.reason

    def test_flat_path_does_not_crash(self):
        s = self._make_strategy()
        src = _make_field("a", "patient_id")
        tgt = _make_field("b", "person_id")
        result = s.score(src, tgt)
        assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# SuggestionEngine — semantic integration
# ---------------------------------------------------------------------------

class TestEngineSemanticIntegration:
    def _hospital_schema(self) -> CanonicalSchema:
        return _make_schema(
            [
                _make_field("src.hospital_id", "hospital.hospital_id",
                            description="Unique identifier for the hospital"),
                _make_field("src.patient_id", "hospital.patient_id",
                            description="Patient identifier within hospital system"),
                _make_field("src.admit_date", "hospital.admit_date",
                            description="Date patient was admitted"),
                _make_field("src.discharge_code", "hospital.discharge_code",
                            description="ICD discharge code"),
            ],
            id="hospital",
        )

    def _omop_schema(self) -> CanonicalSchema:
        return _make_schema(
            [
                _make_field("tgt.care_site_id", "care_site.care_site_id",
                            description="Unique identifier for care site"),
                _make_field("tgt.person_id", "person.person_id",
                            description="Unique identifier for person"),
                _make_field("tgt.visit_start_date", "visit_occurrence.visit_start_date",
                            description="Date when visit or admission started"),
                _make_field("tgt.condition_source_value", "condition_occurrence.condition_source_value",
                            description="Original condition code from source system"),
            ],
            id="omop",
        )

    def test_engine_no_semantic_provider_does_not_crash(self):
        engine = SuggestionEngine(semantic_provider=None)
        result = engine.suggest(self._hospital_schema(), self._omop_schema())
        assert len(result.field_suggestions) == 4

    def test_engine_with_semantic_provider_does_not_crash(self):
        engine = SuggestionEngine(semantic_provider=LexicalSemanticProvider())
        result = engine.suggest(self._hospital_schema(), self._omop_schema())
        assert len(result.field_suggestions) == 4

    def test_semantic_provider_changes_scores(self):
        """Engine scores with vs without semantic provider can differ."""
        src_schema = self._hospital_schema()
        tgt_schema = self._omop_schema()

        engine_plain = SuggestionEngine(semantic_provider=None)
        engine_semantic = SuggestionEngine(semantic_provider=LexicalSemanticProvider())

        result_plain = engine_plain.suggest(src_schema, tgt_schema)
        result_semantic = engine_semantic.suggest(src_schema, tgt_schema)

        plain_scores = {
            fs.target_field_id: [c.confidence for c in fs.candidates]
            for fs in result_plain.field_suggestions
        }
        semantic_scores = {
            fs.target_field_id: [c.confidence for c in fs.candidates]
            for fs in result_semantic.field_suggestions
        }

        # At least some score should differ when semantic provider is active
        all_same = all(
            plain_scores[tid] == semantic_scores[tid]
            for tid in plain_scores
        )
        assert not all_same, "Expected semantic provider to change at least one score"

    def test_semantic_provider_admit_date_to_visit_start_date(self):
        """With semantic provider, admit_date→visit_start_date should be top candidate."""
        engine = SuggestionEngine(semantic_provider=LexicalSemanticProvider(), top_k=4)
        result = engine.suggest(self._hospital_schema(), self._omop_schema())

        visit_start = next(
            fs for fs in result.field_suggestions
            if fs.target_field_id == "tgt.visit_start_date"
        )
        top_candidate_id = visit_start.candidates[0].source_field_ids[0]
        # admit_date is a strong match for visit_start_date semantically
        assert top_candidate_id == "src.admit_date", (
            f"Expected admit_date as top candidate for visit_start_date, "
            f"got {top_candidate_id}"
        )

    def test_engine_deterministic_with_semantic_provider(self):
        """Engine with semantic provider is deterministic across repeated runs."""
        engine = SuggestionEngine(semantic_provider=LexicalSemanticProvider())
        src = self._hospital_schema()
        tgt = self._omop_schema()
        r1 = engine.suggest(src, tgt)
        r2 = engine.suggest(src, tgt)
        for fs1, fs2 in zip(r1.field_suggestions, r2.field_suggestions):
            for c1, c2 in zip(fs1.candidates, fs2.candidates):
                assert c1.confidence == c2.confidence
                assert c1.source_field_ids == c2.source_field_ids

    def test_semantic_strategy_reason_in_candidate(self):
        """Candidate reasons list should include the semantic strategy explanation."""
        engine = SuggestionEngine(semantic_provider=LexicalSemanticProvider(), top_k=1)
        result = engine.suggest(self._hospital_schema(), self._omop_schema())
        # Any candidate's reasons should contain a semantic-related explanation
        any_semantic_reason = any(
            any("semantic" in r.lower() for r in fs.candidates[0].reasons)
            for fs in result.field_suggestions
            if fs.candidates
        )
        assert any_semantic_reason

    def test_custom_semantic_weight_accepted(self):
        engine = SuggestionEngine(
            semantic_provider=LexicalSemanticProvider(), semantic_weight=0.25
        )
        result = engine.suggest(self._hospital_schema(), self._omop_schema())
        assert result is not None
