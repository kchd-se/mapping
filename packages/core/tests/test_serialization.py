"""Tests for Mapping Artifact Serialization.

Covers the three mandatory test requirements:
- Deterministic serialization (same input → byte-identical output)
- Export/import round-trip integrity
- Status lifecycle validity (tested in test_mapping_project.py; artifact
  tests verify project state survives serialization)
"""

import json

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
from packages.core.models.mapping_project import (
    MappingProject,
    ProjectStatus,
    SensitivityClassification,
)
from packages.core.models.mapping_rule import MappingRule, TransformHint, TransformKind
from packages.core.models.mapping_version import MappingVersion, SchemaReference
from packages.core.serialization.artifact import ArtifactFormatError, MappingArtifact


# ---------- Fixtures --------------------------------------------------------

def _sample_field():
    return CanonicalField(
        id="f1",
        path="Patient.name.given",
        field_type=FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="string"),
        cardinality=Cardinality(min_occurs=1, max_occurs=None),
        label="Förnamn",
        description="Given name (Swedish: förnamn)",
        constraints=FieldConstraints(required=True, max_length=200),
        terminology_references=[
            TerminologyReference(system="http://example.org/cs", code="given")
        ],
        metadata_tags={"domain": "demographics"},
    )


def _sample_project():
    return MappingProject(
        id="proj-100",
        name="Region Västra Götaland Mapping",
        description="Maps regional schema to OMOP",
        owner="admin@region-vgr.se",
        status=ProjectStatus.REVIEW,
        sensitivity=SensitivityClassification.HEALTHCARE_HIGHLY_SENSITIVE,
        source_schema_ids=["src-schema-1"],
        target_schema_id="target-schema-1",
        version_ids=["ver-1"],
        created_at="2026-03-01T00:00:00+00:00",
        updated_at="2026-03-15T12:00:00+00:00",
    )


def _sample_version():
    return MappingVersion(
        id="ver-1",
        project_id="proj-100",
        version_label="1.0.0",
        created_at="2026-03-01T00:00:00+00:00",
        source_schema_refs=[
            SchemaReference(schema_id="src-schema-1", schema_name="RegionalSQL", schema_version="1.0"),
        ],
        target_schema_ref=SchemaReference(
            schema_id="target-schema-1", schema_name="OMOP CDM", schema_version="5.4"
        ),
        rules=[
            MappingRule(
                id="r1",
                target_field_id="tf1",
                source_field_ids=["sf1"],
                transform=TransformHint(kind=TransformKind.DIRECT),
            ),
            MappingRule(
                id="r2",
                target_field_id="tf2",
                source_field_ids=["sf2", "sf3"],
                transform=TransformHint(kind=TransformKind.CONCATENATE, expression="join(' ')"),
                default_value="Unknown",
                notes="Combine names",
            ),
        ],
        notes="First mapping version",
    )


def _sample_artifact():
    return MappingArtifact(
        project=_sample_project(),
        version=_sample_version(),
    )


# ---------- Tests -----------------------------------------------------------

class TestDeterministicSerialization:
    """Same input MUST produce byte-identical output (mandatory test)."""

    def test_identical_output_on_repeated_calls(self):
        art = _sample_artifact()
        output1 = art.serialize()
        output2 = art.serialize()
        assert output1 == output2

    def test_identical_output_from_separate_instances(self):
        art1 = _sample_artifact()
        art2 = _sample_artifact()
        assert art1.serialize() == art2.serialize()

    def test_keys_are_sorted(self):
        raw = _sample_artifact().serialize()
        data = json.loads(raw)
        # Top-level keys must be sorted
        assert list(data.keys()) == sorted(data.keys())
        # Project keys must be sorted
        assert list(data["project"].keys()) == sorted(data["project"].keys())

    def test_trailing_newline(self):
        raw = _sample_artifact().serialize()
        assert raw.endswith("\n")

    def test_swedish_characters_preserved(self):
        raw = _sample_artifact().serialize()
        assert "Västra Götaland" in raw
        assert "\\u" not in raw  # ensure_ascii=False


class TestRoundTrip:
    """Export/import round-trip integrity (mandatory test)."""

    def test_serialize_then_deserialize(self):
        original = _sample_artifact()
        raw = original.serialize()
        restored = MappingArtifact.deserialize(raw)
        assert restored.project.id == original.project.id
        assert restored.project.name == original.project.name
        assert restored.project.status == original.project.status
        assert restored.version.id == original.version.id
        assert restored.version.version_label == original.version.version_label
        assert len(restored.version.rules) == len(original.version.rules)

    def test_double_roundtrip_byte_identical(self):
        """serialize → deserialize → serialize must yield the same bytes."""
        art = _sample_artifact()
        raw1 = art.serialize()
        restored = MappingArtifact.deserialize(raw1)
        raw2 = restored.serialize()
        assert raw1 == raw2

    def test_rules_preserve_order_and_values(self):
        art = _sample_artifact()
        restored = MappingArtifact.deserialize(art.serialize())
        for orig_rule, rest_rule in zip(art.version.rules, restored.version.rules):
            assert orig_rule == rest_rule

    def test_project_status_survives_roundtrip(self):
        art = _sample_artifact()
        assert art.project.status == ProjectStatus.REVIEW
        restored = MappingArtifact.deserialize(art.serialize())
        assert restored.project.status == ProjectStatus.REVIEW

    def test_schema_references_survive_roundtrip(self):
        art = _sample_artifact()
        restored = MappingArtifact.deserialize(art.serialize())
        assert restored.version.target_schema_ref == art.version.target_schema_ref
        assert restored.version.source_schema_refs == art.version.source_schema_refs


class TestErrorHandling:
    def test_invalid_json_raises(self):
        with pytest.raises(ArtifactFormatError, match="Invalid JSON"):
            MappingArtifact.deserialize("not json at all")

    def test_wrong_format_version_raises(self):
        data = _sample_artifact().to_dict()
        data["artifact_format_version"] = "99.0"
        raw = json.dumps(data)
        with pytest.raises(ArtifactFormatError, match="Unsupported artifact format"):
            MappingArtifact.deserialize(raw)

    def test_missing_format_version_raises(self):
        data = _sample_artifact().to_dict()
        del data["artifact_format_version"]
        raw = json.dumps(data)
        with pytest.raises(ArtifactFormatError):
            MappingArtifact.deserialize(raw)


class TestArtifactFormatVersion:
    def test_version_present_in_output(self):
        raw = _sample_artifact().serialize()
        data = json.loads(raw)
        assert data["artifact_format_version"] == "1.0"
