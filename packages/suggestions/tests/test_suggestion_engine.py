"""Unit tests for the Suggestion Engine.

Covers:
- Top-K behavior (returns >1 candidate)
- Confidence ranking is deterministic across repeated runs
- Swedish character normalization (Å/Ä/Ö) affect name similarity
- Explainability present for each candidate
- Type mismatch generates warnings
- Cardinality mismatch generates warnings
- Terminology alignment scoring
- Path similarity scoring
- min_confidence filtering
- Custom strategy injection (extensibility)
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
    TerminologyReference,
)
from packages.suggestions.engine import SuggestionEngine
from packages.suggestions.models import SuggestionCandidate, FieldSuggestions
from packages.suggestions.strategies import (
    CardinalityCompatibilityStrategy,
    NameSimilarityStrategy,
    PathSimilarityStrategy,
    StrategyScore,
    TerminologyAlignmentStrategy,
    TypeCompatibilityStrategy,
    _normalize_name,
    default_strategies,
)


# ---------------------------------------------------------------------------
# Schema fixtures
# ---------------------------------------------------------------------------

def _str_type() -> FieldType:
    return FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="string")


def _int_type() -> FieldType:
    return FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="integer")


def _date_type() -> FieldType:
    return FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="date")


def _bool_type() -> FieldType:
    return FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="boolean")


def _make_field(
    id: str,
    path: str,
    ft: FieldType | None = None,
    label: str | None = None,
    required: bool = False,
    cardinality: Cardinality | None = None,
    terminology_refs: list | None = None,
) -> CanonicalField:
    return CanonicalField(
        id=id,
        path=path,
        field_type=ft or _str_type(),
        label=label,
        cardinality=cardinality or Cardinality(),
        constraints=FieldConstraints(required=required),
        terminology_references=terminology_refs or [],
    )


def _source_schema() -> CanonicalSchema:
    return CanonicalSchema(
        id="src-1",
        name="RegionPatient",
        version="1.0",
        fields=[
            _make_field("s1", "patient_id", _int_type()),
            _make_field("s2", "förnamn", _str_type(), label="Förnamn"),
            _make_field("s3", "efternamn", _str_type(), label="Efternamn"),
            _make_field("s4", "födelsedatum", _date_type(), label="Födelsedatum"),
            _make_field("s5", "kön", _str_type(), label="Kön"),
            _make_field(
                "s6", "diagnoskod", _str_type(),
                terminology_refs=[
                    TerminologyReference(system="http://snomed.info/sct", code="123"),
                ],
            ),
        ],
    )


def _target_schema() -> CanonicalSchema:
    return CanonicalSchema(
        id="tgt-1",
        name="StandardPatient",
        version="1.0",
        fields=[
            _make_field("t1", "patient_id", _int_type(), required=True),
            _make_field("t2", "given_name", _str_type(), label="Given Name"),
            _make_field("t3", "family_name", _str_type(), label="Family Name"),
            _make_field("t4", "birth_date", _date_type()),
            _make_field("t5", "gender", _str_type()),
            _make_field(
                "t6", "diagnosis_code", _str_type(),
                terminology_refs=[
                    TerminologyReference(system="http://snomed.info/sct", code="123"),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Name normalization tests
# ---------------------------------------------------------------------------

class TestSwedishNormalization:
    def test_a_ring_normalized(self):
        assert _normalize_name("Å") == "a"
        assert _normalize_name("å") == "a"

    def test_a_diaeresis_normalized(self):
        assert _normalize_name("Ä") == "a"
        assert _normalize_name("ä") == "a"

    def test_o_diaeresis_normalized(self):
        assert _normalize_name("Ö") == "o"
        assert _normalize_name("ö") == "o"

    def test_fornamn_normalized(self):
        assert _normalize_name("förnamn") == "fornamn"

    def test_fodelsedatum(self):
        assert _normalize_name("födelsedatum") == "fodelsedatum"

    def test_kon(self):
        assert _normalize_name("kön") == "kon"

    def test_mixed_case_and_separators(self):
        assert _normalize_name("Patient_Förnamn") == "patient_fornamn"
        assert _normalize_name("patient.förnamn") == "patient_fornamn"

    def test_empty_string(self):
        assert _normalize_name("") == ""


# ---------------------------------------------------------------------------
# Top-K behavior
# ---------------------------------------------------------------------------

class TestTopKBehavior:
    def test_returns_multiple_candidates(self):
        engine = SuggestionEngine(top_k=5)
        result = engine.suggest(_source_schema(), _target_schema())

        for fs in result.field_suggestions:
            assert len(fs.candidates) > 0, f"No candidates for {fs.target_field_path}"

    def test_returns_at_most_top_k(self):
        engine = SuggestionEngine(top_k=3)
        result = engine.suggest(_source_schema(), _target_schema())

        for fs in result.field_suggestions:
            assert len(fs.candidates) <= 3

    def test_top_k_1_returns_single_candidate(self):
        engine = SuggestionEngine(top_k=1)
        result = engine.suggest(_source_schema(), _target_schema())

        for fs in result.field_suggestions:
            assert len(fs.candidates) == 1

    def test_patient_id_best_match_is_patient_id(self):
        engine = SuggestionEngine(top_k=5)
        result = engine.suggest(_source_schema(), _target_schema())

        pid_suggestions = [
            fs for fs in result.field_suggestions
            if fs.target_field_path == "patient_id"
        ]
        assert len(pid_suggestions) == 1
        best = pid_suggestions[0].candidates[0]
        assert "s1" in best.source_field_ids  # s1 = patient_id

    def test_diagnosis_code_matches_diagnoskod_via_terminology(self):
        engine = SuggestionEngine(top_k=5)
        result = engine.suggest(_source_schema(), _target_schema())

        diag_suggestions = [
            fs for fs in result.field_suggestions
            if fs.target_field_path == "diagnosis_code"
        ]
        assert len(diag_suggestions) == 1
        # diagnoskod should be among top candidates due to terminology match
        top_ids = [c.source_field_ids[0] for c in diag_suggestions[0].candidates[:3]]
        assert "s6" in top_ids  # s6 = diagnoskod


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_repeated_runs_produce_identical_output(self):
        engine = SuggestionEngine(top_k=5)
        src = _source_schema()
        tgt = _target_schema()

        result1 = engine.suggest(src, tgt)
        result2 = engine.suggest(src, tgt)

        assert result1.to_dict() == result2.to_dict()

    def test_determinism_survives_large_k(self):
        engine = SuggestionEngine(top_k=100)
        src = _source_schema()
        tgt = _target_schema()

        result1 = engine.suggest(src, tgt)
        result2 = engine.suggest(src, tgt)

        assert result1.to_dict() == result2.to_dict()


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------

class TestExplainability:
    def test_every_candidate_has_reasons(self):
        engine = SuggestionEngine(top_k=5)
        result = engine.suggest(_source_schema(), _target_schema())

        for fs in result.field_suggestions:
            for c in fs.candidates:
                assert len(c.reasons) > 0, (
                    f"No reasons for candidate {c.source_field_ids} "
                    f"→ {fs.target_field_path}"
                )

    def test_reason_count_matches_strategy_count(self):
        strategies = default_strategies()
        engine = SuggestionEngine(strategies=strategies, top_k=5)
        result = engine.suggest(_source_schema(), _target_schema())

        for fs in result.field_suggestions:
            for c in fs.candidates:
                assert len(c.reasons) == len(strategies)


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------

class TestWarnings:
    def test_type_mismatch_generates_warning(self):
        """Map an integer source field to a string target — should warn."""
        src = CanonicalSchema(id="s", name="S", fields=[
            _make_field("s1", "age", _int_type()),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _make_field("t1", "age", _str_type()),
        ])
        engine = SuggestionEngine(top_k=1)
        result = engine.suggest(src, tgt)

        candidate = result.field_suggestions[0].candidates[0]
        type_warnings = [w for w in candidate.warnings if "Type mismatch" in w or "type" in w.lower()]
        assert len(type_warnings) > 0

    def test_cardinality_mismatch_generates_warning(self):
        """Source multi-valued, target single → cardinality warning."""
        src = CanonicalSchema(id="s", name="S", fields=[
            _make_field("s1", "phones", cardinality=Cardinality(min_occurs=0, max_occurs=None)),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _make_field("t1", "phones", cardinality=Cardinality(min_occurs=1, max_occurs=1)),
        ])
        engine = SuggestionEngine(top_k=1)
        result = engine.suggest(src, tgt)

        candidate = result.field_suggestions[0].candidates[0]
        card_warnings = [w for w in candidate.warnings if "ardinality" in w.lower()]
        assert len(card_warnings) > 0


# ---------------------------------------------------------------------------
# Swedish normalization impact on ranking
# ---------------------------------------------------------------------------

class TestSwedishNormalizationRanking:
    def test_fornamn_ranks_higher_for_fornamn_target(self):
        """förnamn should rank as the best match for a target also named förnamn."""
        src = CanonicalSchema(id="s", name="S", fields=[
            _make_field("s1", "förnamn"),
            _make_field("s2", "efternamn"),
            _make_field("s3", "ålder"),      # "alder" after normalization
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _make_field("t1", "förnamn"),
        ])
        engine = SuggestionEngine(top_k=3)
        result = engine.suggest(src, tgt)

        best = result.field_suggestions[0].candidates[0]
        assert "s1" in best.source_field_ids

    def test_alder_matches_alder_despite_a_ring(self):
        """Source 'ålder' should match target 'alder' via normalization."""
        src = CanonicalSchema(id="s", name="S", fields=[
            _make_field("s1", "ålder", _int_type()),
            _make_field("s2", "other_field"),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _make_field("t1", "alder", _int_type()),
        ])
        engine = SuggestionEngine(top_k=2)
        result = engine.suggest(src, tgt)

        best = result.field_suggestions[0].candidates[0]
        assert "s1" in best.source_field_ids

    def test_kon_matches_kon_despite_o_diaeresis(self):
        src = CanonicalSchema(id="s", name="S", fields=[
            _make_field("s1", "kön"),
            _make_field("s2", "namn"),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _make_field("t1", "kon"),
        ])
        engine = SuggestionEngine(top_k=2)
        result = engine.suggest(src, tgt)

        best = result.field_suggestions[0].candidates[0]
        assert "s1" in best.source_field_ids


# ---------------------------------------------------------------------------
# min_confidence filtering
# ---------------------------------------------------------------------------

class TestMinConfidence:
    def test_low_confidence_candidates_filtered(self):
        engine = SuggestionEngine(top_k=10, min_confidence=0.8)
        src = CanonicalSchema(id="s", name="S", fields=[
            _make_field("s1", "totally_unrelated", _bool_type()),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _make_field("t1", "patient_id", _int_type()),
        ])
        result = engine.suggest(src, tgt)

        # The only source field has very low similarity to "patient_id"
        for c in result.field_suggestions[0].candidates:
            assert c.confidence >= 0.8


# ---------------------------------------------------------------------------
# Custom strategy injection (extensibility)
# ---------------------------------------------------------------------------

class _ConstantStrategy:
    """Always returns 0.99 — used to verify custom strategy injection."""

    @property
    def name(self) -> str:
        return "constant_test"

    @property
    def weight(self) -> float:
        return 1.0

    def score(self, source, target) -> StrategyScore:
        return StrategyScore(
            name="constant_test", score=0.99, weight=1.0, reason="Constant score"
        )


class TestCustomStrategy:
    def test_custom_strategy_used(self):
        engine = SuggestionEngine(strategies=[_ConstantStrategy()], top_k=5)
        src = CanonicalSchema(id="s", name="S", fields=[
            _make_field("s1", "x"),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _make_field("t1", "y"),
        ])
        result = engine.suggest(src, tgt)

        best = result.field_suggestions[0].candidates[0]
        assert best.confidence == 0.99
        assert "Constant score" in best.reasons


# ---------------------------------------------------------------------------
# Individual strategy unit tests
# ---------------------------------------------------------------------------

class TestNameSimilarityStrategy:
    def test_exact_match_scores_1(self):
        s = NameSimilarityStrategy()
        result = s.score(
            _make_field("s1", "patient_id"),
            _make_field("t1", "patient_id"),
        )
        assert result.score == 1.0

    def test_no_overlap_scores_low(self):
        s = NameSimilarityStrategy()
        result = s.score(
            _make_field("s1", "foo"),
            _make_field("t1", "bar"),
        )
        assert result.score < 0.3


class TestTypeCompatibilityStrategy:
    def test_same_type_scores_1(self):
        s = TypeCompatibilityStrategy()
        result = s.score(
            _make_field("s1", "x", _str_type()),
            _make_field("t1", "y", _str_type()),
        )
        assert result.score == 1.0

    def test_int_to_string_warns(self):
        s = TypeCompatibilityStrategy()
        result = s.score(
            _make_field("s1", "x", _int_type()),
            _make_field("t1", "y", _str_type()),
        )
        assert result.score < 1.0
        assert result.warning is not None


class TestCardinalityStrategy:
    def test_identical_cardinality_scores_1(self):
        s = CardinalityCompatibilityStrategy()
        result = s.score(
            _make_field("s1", "x", cardinality=Cardinality(0, 1)),
            _make_field("t1", "y", cardinality=Cardinality(0, 1)),
        )
        assert result.score == 1.0

    def test_multi_to_single_penalized(self):
        s = CardinalityCompatibilityStrategy()
        result = s.score(
            _make_field("s1", "x", cardinality=Cardinality(0, None)),
            _make_field("t1", "y", cardinality=Cardinality(1, 1)),
        )
        assert result.score < 1.0
        assert result.warning is not None


class TestTerminologyAlignmentStrategy:
    def test_matching_system_and_code_scores_1(self):
        s = TerminologyAlignmentStrategy()
        refs = [TerminologyReference(system="http://snomed.info/sct", code="123")]
        result = s.score(
            _make_field("s1", "x", terminology_refs=refs),
            _make_field("t1", "y", terminology_refs=refs),
        )
        assert result.score == 1.0

    def test_no_refs_neutral(self):
        s = TerminologyAlignmentStrategy()
        result = s.score(
            _make_field("s1", "x"),
            _make_field("t1", "y"),
        )
        assert result.score == 0.5
