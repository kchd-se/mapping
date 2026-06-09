"""Unit tests for the SQL INSERT … SELECT script generator.

All tests operate entirely on canonical-model objects — no real data,
no database connections, no patient-level payloads (RL-02).
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
from packages.core.models.mapping_project import MappingProject, SensitivityClassification
from packages.core.models.mapping_rule import MappingRule, TransformHint, TransformKind
from packages.core.models.mapping_version import MappingVersion
from packages.core.serialization.artifact import MappingArtifact
from packages.script_gen.generators.sql_insert_select import (
    SqlInsertSelectGenerator,
    _V1_NOTICE,
)
from packages.script_gen.models import GeneratedScript


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _string_field(id: str, path: str, required: bool = False) -> CanonicalField:
    return CanonicalField(
        id=id,
        path=path,
        field_type=FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="string"),
        cardinality=Cardinality(min_occurs=1 if required else 0),
        constraints=FieldConstraints(required=required),
    )


def _int_field(id: str, path: str, required: bool = False) -> CanonicalField:
    return CanonicalField(
        id=id,
        path=path,
        field_type=FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="integer"),
        cardinality=Cardinality(min_occurs=1 if required else 0),
        constraints=FieldConstraints(required=required),
    )


def _make_source_schema() -> CanonicalSchema:
    return CanonicalSchema(
        id="src-schema-001",
        name="RegionPatient",
        version="1.0",
        fields=[
            _string_field("src-f-patientId", "patientId"),
            _string_field("src-f-fornamn", "fornamn"),
            _string_field("src-f-efternamn", "efternamn"),
            _string_field("src-f-dob", "fodelsedatum"),
            _string_field("src-f-kon", "kon"),
            _string_field("src-f-diagnoskod", "diagnoskod"),
        ],
    )


def _make_target_schema() -> CanonicalSchema:
    return CanonicalSchema(
        id="tgt-schema-001",
        name="OMOP_Person",
        version="5.4",
        fields=[
            _int_field("tgt-f-person-id", "person.person_id", required=True),
            _string_field("tgt-f-first-name", "person.first_name"),
            _string_field("tgt-f-last-name", "person.last_name"),
            _string_field("tgt-f-birth-date", "person.birth_date"),
            _string_field("tgt-f-gender", "person.gender_concept_id"),
            _string_field("tgt-f-condition", "condition.condition_concept_id", required=True),
        ],
    )


def _make_artifact(rules: list[MappingRule]) -> MappingArtifact:
    project = MappingProject(
        id="proj-test-001",
        name="Test Project",
        sensitivity=SensitivityClassification.HEALTHCARE_HIGHLY_SENSITIVE,
    )
    version = MappingVersion(
        id="mv-test-001",
        project_id="proj-test-001",
        version_label="Draft v1",
        rules=rules,
    )
    return MappingArtifact(project=project, version=version)


def _direct_rule(target_id: str, source_id: str, notes: str = "") -> MappingRule:
    return MappingRule(
        id=f"rule-{target_id}",
        target_field_id=target_id,
        source_field_ids=[source_id],
        transform=TransformHint(kind=TransformKind.DIRECT),
        notes=notes or None,
    )


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_returns_generated_script(self):
        gen = SqlInsertSelectGenerator()
        src = _make_source_schema()
        tgt = _make_target_schema()
        artifact = _make_artifact([])
        result = gen.generate(artifact, src, tgt)
        assert isinstance(result, GeneratedScript)

    def test_generator_id_on_result(self):
        gen = SqlInsertSelectGenerator()
        result = gen.generate(_make_artifact([]), _make_source_schema(), _make_target_schema())
        assert result.generator_id == "sql_insert_select_v1"

    def test_generator_version_on_result(self):
        gen = SqlInsertSelectGenerator()
        result = gen.generate(_make_artifact([]), _make_source_schema(), _make_target_schema())
        assert result.generator_version == "1.0.0"


# ---------------------------------------------------------------------------
# Determinism — MANDATORY
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_input_produces_identical_output(self):
        gen = SqlInsertSelectGenerator()
        src = _make_source_schema()
        tgt = _make_target_schema()
        rules = [
            _direct_rule("tgt-f-first-name", "src-f-fornamn"),
            _direct_rule("tgt-f-last-name", "src-f-efternamn"),
        ]
        artifact = _make_artifact(rules)
        first = gen.generate(artifact, src, tgt).script_text
        second = gen.generate(artifact, src, tgt).script_text
        assert first == second

    def test_identical_output_across_multiple_calls(self):
        gen = SqlInsertSelectGenerator()
        src = _make_source_schema()
        tgt = _make_target_schema()
        artifact = _make_artifact([_direct_rule("tgt-f-first-name", "src-f-fornamn")])
        scripts = [gen.generate(artifact, src, tgt).script_text for _ in range(5)]
        assert all(s == scripts[0] for s in scripts)

    def test_field_order_is_alphabetical_by_target_path(self):
        """SELECT columns must be in sorted order regardless of rule insertion order."""
        gen = SqlInsertSelectGenerator()
        src = _make_source_schema()
        tgt = _make_target_schema()
        # Add rules in reverse alphabetical order
        rules = [
            _direct_rule("tgt-f-last-name", "src-f-efternamn"),
            _direct_rule("tgt-f-first-name", "src-f-fornamn"),
        ]
        artifact = _make_artifact(rules)
        script = gen.generate(artifact, src, tgt).script_text
        # first_name must appear before last_name in the script
        assert script.index("first_name") < script.index("last_name")

    def test_no_timestamps_in_script_body(self):
        """Only the header may reference fixed IDs — no wall-clock timestamps."""
        gen = SqlInsertSelectGenerator()
        src = _make_source_schema()
        tgt = _make_target_schema()
        script = gen.generate(_make_artifact([]), src, tgt).script_text
        # The script body (after the header block) must not contain NOW() etc.
        body = script.split("=\n", 1)[-1]  # strip header block
        for ts_keyword in ("NOW()", "CURRENT_TIMESTAMP", "GETDATE()", "SYSDATE"):
            assert ts_keyword not in body


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

class TestHeader:
    def _get_script(self) -> str:
        gen = SqlInsertSelectGenerator()
        src = _make_source_schema()
        tgt = _make_target_schema()
        return gen.generate(_make_artifact([]), src, tgt).script_text

    def test_header_contains_v1_notice(self):
        assert _V1_NOTICE in self._get_script()

    def test_header_contains_project_id(self):
        assert "proj-test-001" in self._get_script()

    def test_header_contains_mapping_version(self):
        assert "Draft v1" in self._get_script()

    def test_header_contains_source_schema_id(self):
        assert "src-schema-001" in self._get_script()

    def test_header_contains_target_schema_id(self):
        assert "tgt-schema-001" in self._get_script()

    def test_header_contains_generator_id(self):
        assert "sql_insert_select_v1" in self._get_script()

    def test_metadata_dict_populated(self):
        gen = SqlInsertSelectGenerator()
        result = gen.generate(_make_artifact([]), _make_source_schema(), _make_target_schema())
        assert result.metadata["project_id"] == "proj-test-001"
        assert result.metadata["mapping_version"] == "Draft v1"
        assert result.metadata["source_schema_id"] == "src-schema-001"
        assert result.metadata["target_schema_id"] == "tgt-schema-001"
        assert result.metadata["notice"] == _V1_NOTICE


# ---------------------------------------------------------------------------
# Mapped fields
# ---------------------------------------------------------------------------

class TestMappedFields:
    def test_mapped_required_field_included(self):
        gen = SqlInsertSelectGenerator()
        rules = [_direct_rule("tgt-f-person-id", "src-f-patientId")]
        script = gen.generate(_make_artifact(rules), _make_source_schema(), _make_target_schema()).script_text
        assert "person_id" in script
        assert "patientId" in script

    def test_mapped_optional_field_included(self):
        gen = SqlInsertSelectGenerator()
        rules = [_direct_rule("tgt-f-first-name", "src-f-fornamn")]
        script = gen.generate(_make_artifact(rules), _make_source_schema(), _make_target_schema()).script_text
        assert "first_name" in script
        assert "fornamn" in script

    def test_source_column_appears_as_alias_target(self):
        gen = SqlInsertSelectGenerator()
        rules = [_direct_rule("tgt-f-first-name", "src-f-fornamn")]
        script = gen.generate(_make_artifact(rules), _make_source_schema(), _make_target_schema()).script_text
        # Expect: fornamn AS first_name
        assert "fornamn AS first_name" in script

    def test_rule_notes_appear_as_sql_comment(self):
        gen = SqlInsertSelectGenerator()
        rules = [_direct_rule("tgt-f-first-name", "src-f-fornamn", notes="requires trim")]
        script = gen.generate(_make_artifact(rules), _make_source_schema(), _make_target_schema()).script_text
        assert "requires trim" in script


# ---------------------------------------------------------------------------
# Unmapped fields
# ---------------------------------------------------------------------------

class TestUnmappedFields:
    def test_unmapped_required_field_rendered_as_null(self):
        """Required target fields with no rule → NULL with comment."""
        gen = SqlInsertSelectGenerator()
        script = gen.generate(_make_artifact([]), _make_source_schema(), _make_target_schema()).script_text
        assert "NULL AS person_id  -- UNMAPPED (required)" in script
        assert "NULL AS condition_concept_id  -- UNMAPPED (required)" in script

    def test_unmapped_optional_field_excluded(self):
        """Optional target fields with no rule must NOT appear in the script."""
        gen = SqlInsertSelectGenerator()
        script = gen.generate(_make_artifact([]), _make_source_schema(), _make_target_schema()).script_text
        # These are optional and unmapped — should be absent
        assert "first_name" not in script
        assert "last_name" not in script
        assert "birth_date" not in script
        assert "gender_concept_id" not in script


# ---------------------------------------------------------------------------
# TransformKind handling
# ---------------------------------------------------------------------------

class TestTransformKinds:
    def _gen_script(self, rule: MappingRule) -> str:
        gen = SqlInsertSelectGenerator()
        return gen.generate(
            _make_artifact([rule]),
            _make_source_schema(),
            _make_target_schema(),
        ).script_text

    def test_direct_emits_column_name(self):
        rule = MappingRule(
            id="r1", target_field_id="tgt-f-first-name",
            source_field_ids=["src-f-fornamn"],
            transform=TransformHint(kind=TransformKind.DIRECT),
        )
        assert "fornamn AS first_name" in self._gen_script(rule)

    def test_constant_emits_literal(self):
        rule = MappingRule(
            id="r1", target_field_id="tgt-f-first-name",
            source_field_ids=[],
            transform=TransformHint(kind=TransformKind.CONSTANT),
            constant_value="N/A",
        )
        assert "'N/A' AS first_name" in self._gen_script(rule)

    def test_concatenate_emits_concat(self):
        rule = MappingRule(
            id="r1", target_field_id="tgt-f-first-name",
            source_field_ids=["src-f-fornamn", "src-f-efternamn"],
            transform=TransformHint(kind=TransformKind.CONCATENATE),
        )
        script = self._gen_script(rule)
        assert "CONCAT(" in script

    def test_default_emits_coalesce(self):
        rule = MappingRule(
            id="r1", target_field_id="tgt-f-first-name",
            source_field_ids=["src-f-fornamn"],
            transform=TransformHint(kind=TransformKind.DEFAULT),
            default_value="Unknown",
        )
        assert "COALESCE(fornamn, 'Unknown') AS first_name" in self._gen_script(rule)

    def test_lookup_emits_comment(self):
        rule = MappingRule(
            id="r1", target_field_id="tgt-f-first-name",
            source_field_ids=["src-f-fornamn"],
            transform=TransformHint(kind=TransformKind.LOOKUP, expression="icd10_map"),
        )
        assert "/* LOOKUP: icd10_map */" in self._gen_script(rule)

    def test_custom_emits_comment(self):
        rule = MappingRule(
            id="r1", target_field_id="tgt-f-first-name",
            source_field_ids=["src-f-fornamn"],
            transform=TransformHint(kind=TransformKind.CUSTOM, expression="UPPER(x)"),
        )
        assert "/* CUSTOM: UPPER(x) */" in self._gen_script(rule)


# ---------------------------------------------------------------------------
# Multi-table grouping
# ---------------------------------------------------------------------------

class TestMultiTableGrouping:
    def test_two_tables_produce_two_insert_blocks(self):
        """person.* and condition.* fields → two separate INSERT statements."""
        gen = SqlInsertSelectGenerator()
        rules = [
            _direct_rule("tgt-f-person-id", "src-f-patientId"),
            _direct_rule("tgt-f-condition", "src-f-diagnoskod"),
        ]
        script = gen.generate(_make_artifact(rules), _make_source_schema(), _make_target_schema()).script_text
        assert script.count("INSERT INTO") == 2
        assert "INSERT INTO person" in script
        assert "INSERT INTO condition" in script

    def test_table_order_is_alphabetical(self):
        gen = SqlInsertSelectGenerator()
        rules = [
            _direct_rule("tgt-f-condition", "src-f-diagnoskod"),
            _direct_rule("tgt-f-person-id", "src-f-patientId"),
        ]
        script = gen.generate(_make_artifact(rules), _make_source_schema(), _make_target_schema()).script_text
        assert script.index("INSERT INTO condition") < script.index("INSERT INTO person")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_get_default_returns_sql_generator(self):
        from packages.script_gen.registry import get_default
        gen = get_default()
        assert gen.generator_id == "sql_insert_select_v1"

    def test_get_by_id_returns_correct_generator(self):
        from packages.script_gen.registry import get
        gen = get("sql_insert_select_v1")
        assert isinstance(gen, SqlInsertSelectGenerator)

    def test_get_unknown_id_raises(self):
        from packages.script_gen.registry import get
        with pytest.raises(KeyError):
            get("nonexistent_generator_v99")
