"""Unit tests for the Validation Engine.

Covers:
- Target field existence rule triggers errors correctly (RL-14)
- Required target field unmapped triggers error by policy
- Type mismatch triggers warn/error according to configured policy
- Cardinality mismatch tests
- Constraint conflicts (enum, pattern, range)
- Policy-configurable severity overrides
- Determinism: repeated runs produce identical ordered issues
- Custom rule injection (extensibility)
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
from packages.core.models.mapping_rule import MappingRule
from packages.validation.engine import ValidationEngine
from packages.validation.models import Severity, ValidationIssue, ValidationResult
from packages.validation.policy import ValidationPolicy, default_policy
from packages.validation.rules import (
    CardinalityCompatibilityRule,
    ConstraintConflictRule,
    RequiredTargetFieldsMappedRule,
    TargetFieldExistsRule,
    TypeCompatibilityRule,
    default_rules,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _str_type() -> FieldType:
    return FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="string")


def _int_type() -> FieldType:
    return FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="integer")


def _date_type() -> FieldType:
    return FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="date")


def _bool_type() -> FieldType:
    return FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="boolean")


def _field(
    id: str,
    path: str,
    ft: FieldType | None = None,
    required: bool = False,
    cardinality: Cardinality | None = None,
    enums: list[str] | None = None,
    pattern: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
) -> CanonicalField:
    return CanonicalField(
        id=id,
        path=path,
        field_type=ft or _str_type(),
        cardinality=cardinality or Cardinality(),
        constraints=FieldConstraints(
            required=required,
            enums=enums,
            pattern=pattern,
            min_value=min_value,
            max_value=max_value,
        ),
    )


def _rule(target_id: str, source_ids: list[str]) -> MappingRule:
    return MappingRule(target_field_id=target_id, source_field_ids=source_ids)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


def _source() -> CanonicalSchema:
    return CanonicalSchema(
        id="src-1",
        name="Source",
        fields=[
            _field("s1", "patient_id", _int_type()),
            _field("s2", "name", _str_type()),
            _field("s3", "age", _int_type()),
            _field("s4", "active", _bool_type()),
            _field("s5", "score", _int_type(), min_value=0, max_value=200),
        ],
    )


def _target() -> CanonicalSchema:
    return CanonicalSchema(
        id="tgt-1",
        name="Target",
        fields=[
            _field("t1", "patient_id", _int_type(), required=True),
            _field("t2", "full_name", _str_type(), required=True),
            _field("t3", "birth_date", _date_type()),
            _field("t4", "is_active", _str_type()),
            _field(
                "t5", "score", _int_type(),
                min_value=0, max_value=100,
                enums=None,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Target Field Existence (RL-14)
# ---------------------------------------------------------------------------


class TestTargetFieldExistence:
    def test_valid_mapping_no_errors(self):
        engine = ValidationEngine()
        rules = [_rule("t1", ["s1"]), _rule("t2", ["s2"])]
        result = engine.validate(rules, _source(), _target())

        exist_issues = [i for i in result.issues if i.rule_id == "target_field_exists"]
        assert len(exist_issues) == 0

    def test_nonexistent_target_field_triggers_error(self):
        engine = ValidationEngine()
        rules = [_rule("NONEXISTENT", ["s1"])]
        result = engine.validate(rules, _source(), _target())

        exist_issues = [i for i in result.issues if i.rule_id == "target_field_exists"]
        assert len(exist_issues) == 1
        assert exist_issues[0].severity == Severity.ERROR
        assert "NONEXISTENT" in exist_issues[0].message

    def test_multiple_nonexistent_fields_all_reported(self):
        engine = ValidationEngine()
        rules = [_rule("BAD1", ["s1"]), _rule("BAD2", ["s2"])]
        result = engine.validate(rules, _source(), _target())

        exist_issues = [i for i in result.issues if i.rule_id == "target_field_exists"]
        assert len(exist_issues) == 2


# ---------------------------------------------------------------------------
# Required Target Fields Mapped
# ---------------------------------------------------------------------------


class TestRequiredTargetMapped:
    def test_all_required_mapped_no_errors(self):
        engine = ValidationEngine()
        rules = [_rule("t1", ["s1"]), _rule("t2", ["s2"])]
        result = engine.validate(rules, _source(), _target())

        req_issues = [i for i in result.issues if i.rule_id == "required_target_mapped"]
        assert len(req_issues) == 0

    def test_required_field_unmapped_triggers_error(self):
        engine = ValidationEngine()
        rules = [_rule("t1", ["s1"])]  # t2 (required) not mapped
        result = engine.validate(rules, _source(), _target())

        req_issues = [i for i in result.issues if i.rule_id == "required_target_mapped"]
        assert len(req_issues) == 1
        assert req_issues[0].severity == Severity.ERROR
        assert "full_name" in req_issues[0].message

    def test_no_rules_reports_all_required_unmapped(self):
        engine = ValidationEngine()
        result = engine.validate([], _source(), _target())

        req_issues = [i for i in result.issues if i.rule_id == "required_target_mapped"]
        assert len(req_issues) == 2  # t1 and t2 are required

    def test_policy_override_to_warn(self):
        policy = ValidationPolicy(
            id="lenient",
            name="Lenient",
            severity_overrides={"required_target_mapped": Severity.WARN},
        )
        engine = ValidationEngine(policy=policy)
        rules = [_rule("t1", ["s1"])]  # t2 unmapped
        result = engine.validate(rules, _source(), _target())

        req_issues = [i for i in result.issues if i.rule_id == "required_target_mapped"]
        assert all(i.severity == Severity.WARN for i in req_issues)


# ---------------------------------------------------------------------------
# Type Compatibility
# ---------------------------------------------------------------------------


class TestTypeCompatibility:
    def test_compatible_types_no_issues(self):
        engine = ValidationEngine()
        rules = [_rule("t1", ["s1"])]  # int → int
        result = engine.validate(rules, _source(), _target())

        type_issues = [i for i in result.issues if i.rule_id == "type_compatibility"]
        assert len(type_issues) == 0

    def test_bool_to_string_is_compatible(self):
        engine = ValidationEngine()
        rules = [_rule("t4", ["s4"])]  # bool → string (widening)
        result = engine.validate(rules, _source(), _target())

        type_issues = [i for i in result.issues if i.rule_id == "type_compatibility"]
        assert len(type_issues) == 0

    def test_int_to_date_triggers_type_mismatch(self):
        engine = ValidationEngine()
        rules = [_rule("t3", ["s3"])]  # int → date
        result = engine.validate(rules, _source(), _target())

        type_issues = [i for i in result.issues if i.rule_id == "type_compatibility"]
        assert len(type_issues) == 1
        assert type_issues[0].severity == Severity.WARN

    def test_policy_escalates_type_mismatch_to_error(self):
        policy = ValidationPolicy(
            id="strict",
            name="Strict",
            severity_overrides={"type_compatibility": Severity.ERROR},
        )
        engine = ValidationEngine(policy=policy)
        rules = [_rule("t3", ["s3"])]
        result = engine.validate(rules, _source(), _target())

        type_issues = [i for i in result.issues if i.rule_id == "type_compatibility"]
        assert type_issues[0].severity == Severity.ERROR


# ---------------------------------------------------------------------------
# Cardinality Compatibility
# ---------------------------------------------------------------------------


class TestCardinalityCompatibility:
    def test_matching_cardinality_no_issues(self):
        src = CanonicalSchema(id="s", name="S", fields=[
            _field("s1", "x", _str_type(), cardinality=Cardinality(0, 1)),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _field("t1", "x", _str_type(), cardinality=Cardinality(0, 1)),
        ])
        engine = ValidationEngine()
        result = engine.validate([_rule("t1", ["s1"])], src, tgt)

        card_issues = [i for i in result.issues if i.rule_id == "cardinality_compatibility"]
        assert len(card_issues) == 0

    def test_multi_to_single_triggers_warning(self):
        src = CanonicalSchema(id="s", name="S", fields=[
            _field("s1", "phones", _str_type(), cardinality=Cardinality(0, None)),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _field("t1", "phone", _str_type(), cardinality=Cardinality(0, 1)),
        ])
        engine = ValidationEngine()
        result = engine.validate([_rule("t1", ["s1"])], src, tgt)

        card_issues = [i for i in result.issues if i.rule_id == "cardinality_compatibility"]
        assert len(card_issues) == 1
        assert "multi-valued" in card_issues[0].message

    def test_optional_source_required_target_triggers_warning(self):
        src = CanonicalSchema(id="s", name="S", fields=[
            _field("s1", "x", _str_type(), cardinality=Cardinality(0, 1)),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _field("t1", "x", _str_type(), cardinality=Cardinality(1, 1)),
        ])
        engine = ValidationEngine()
        result = engine.validate([_rule("t1", ["s1"])], src, tgt)

        card_issues = [i for i in result.issues if i.rule_id == "cardinality_compatibility"]
        assert len(card_issues) == 1
        assert "min=" in card_issues[0].message


# ---------------------------------------------------------------------------
# Constraint Conflicts
# ---------------------------------------------------------------------------


class TestConstraintConflicts:
    def test_enum_conflict_detected(self):
        src = CanonicalSchema(id="s", name="S", fields=[
            _field("s1", "status", enums=["active", "inactive", "pending"]),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _field("t1", "status", enums=["active", "inactive"]),
        ])
        engine = ValidationEngine()
        result = engine.validate([_rule("t1", ["s1"])], src, tgt)

        constraint_issues = [i for i in result.issues if i.rule_id == "constraint_conflict"]
        assert len(constraint_issues) == 1
        assert "pending" in constraint_issues[0].message

    def test_pattern_mismatch_detected(self):
        src = CanonicalSchema(id="s", name="S", fields=[
            _field("s1", "code"),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _field("t1", "code", pattern=r"^[A-Z]{3}\d{4}$"),
        ])
        engine = ValidationEngine()
        result = engine.validate([_rule("t1", ["s1"])], src, tgt)

        constraint_issues = [i for i in result.issues if i.rule_id == "constraint_conflict"]
        assert len(constraint_issues) == 1
        assert "pattern" in constraint_issues[0].message.lower()

    def test_range_conflict_min(self):
        src = CanonicalSchema(id="s", name="S", fields=[
            _field("s1", "temp", _int_type(), min_value=-10, max_value=100),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _field("t1", "temp", _int_type(), min_value=0, max_value=100),
        ])
        engine = ValidationEngine()
        result = engine.validate([_rule("t1", ["s1"])], src, tgt)

        constraint_issues = [i for i in result.issues if i.rule_id == "constraint_conflict"]
        assert len(constraint_issues) == 1
        assert "min=" in constraint_issues[0].message

    def test_range_conflict_max(self):
        engine = ValidationEngine()
        rules = [_rule("t5", ["s5"])]  # s5: max=200, t5: max=100
        result = engine.validate(rules, _source(), _target())

        constraint_issues = [i for i in result.issues if i.rule_id == "constraint_conflict"]
        assert any("max=" in i.message for i in constraint_issues)


# ---------------------------------------------------------------------------
# Policy-Configurable Severity
# ---------------------------------------------------------------------------


class TestPolicyConfigurableSeverity:
    def test_default_policy_uses_rule_defaults(self):
        engine = ValidationEngine(policy=default_policy())
        rules = [_rule("NONEXISTENT", ["s1"])]
        result = engine.validate(rules, _source(), _target())

        exist_issues = [i for i in result.issues if i.rule_id == "target_field_exists"]
        assert exist_issues[0].severity == Severity.ERROR  # default

    def test_override_target_exists_to_warn(self):
        policy = ValidationPolicy(
            id="lenient",
            name="Lenient policy",
            severity_overrides={"target_field_exists": Severity.WARN},
        )
        engine = ValidationEngine(policy=policy)
        rules = [_rule("NONEXISTENT", ["s1"])]
        result = engine.validate(rules, _source(), _target())

        exist_issues = [i for i in result.issues if i.rule_id == "target_field_exists"]
        assert exist_issues[0].severity == Severity.WARN

    def test_override_constraint_conflict_to_error(self):
        policy = ValidationPolicy(
            id="strict",
            name="Strict",
            severity_overrides={"constraint_conflict": Severity.ERROR},
        )
        engine = ValidationEngine(policy=policy)
        src = CanonicalSchema(id="s", name="S", fields=[
            _field("s1", "status", enums=["active", "inactive", "pending"]),
        ])
        tgt = CanonicalSchema(id="t", name="T", fields=[
            _field("t1", "status", enums=["active", "inactive"]),
        ])
        result = engine.validate([_rule("t1", ["s1"])], src, tgt)

        constraint_issues = [i for i in result.issues if i.rule_id == "constraint_conflict"]
        assert constraint_issues[0].severity == Severity.ERROR

    def test_override_to_info_suppresses_severity(self):
        policy = ValidationPolicy(
            id="poc",
            name="POC",
            severity_overrides={"type_compatibility": Severity.INFO},
        )
        engine = ValidationEngine(policy=policy)
        rules = [_rule("t3", ["s3"])]  # int → date
        result = engine.validate(rules, _source(), _target())

        type_issues = [i for i in result.issues if i.rule_id == "type_compatibility"]
        assert type_issues[0].severity == Severity.INFO

    def test_policy_round_trip(self):
        policy = ValidationPolicy(
            id="test",
            name="Test",
            severity_overrides={
                "target_field_exists": Severity.WARN,
                "type_compatibility": Severity.ERROR,
            },
        )
        restored = ValidationPolicy.from_dict(policy.to_dict())
        assert restored.severity_overrides == policy.severity_overrides
        assert restored.id == "test"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_repeated_runs_identical_output(self):
        engine = ValidationEngine()
        rules = [
            _rule("t3", ["s3"]),   # type mismatch
            _rule("NONEXISTENT", ["s1"]),  # target not found
        ]
        src = _source()
        tgt = _target()

        result1 = engine.validate(rules, src, tgt)
        result2 = engine.validate(rules, src, tgt)

        assert result1.to_dict() == result2.to_dict()

    def test_issues_sorted_by_severity_then_rule_id(self):
        engine = ValidationEngine()
        rules = [_rule("t3", ["s3"]), _rule("NONEXISTENT", ["s1"])]
        result = engine.validate(rules, _source(), _target())

        # Errors should come before warnings
        severities = [i.severity for i in result.issues]
        error_indices = [i for i, s in enumerate(severities) if s == Severity.ERROR]
        warn_indices = [i for i, s in enumerate(severities) if s == Severity.WARN]
        if error_indices and warn_indices:
            assert max(error_indices) < min(warn_indices)


# ---------------------------------------------------------------------------
# has_errors / counts
# ---------------------------------------------------------------------------


class TestValidationResultProperties:
    def test_has_errors_true_when_errors_present(self):
        engine = ValidationEngine()
        result = engine.validate([_rule("NONEXISTENT", ["s1"])], _source(), _target())
        assert result.has_errors is True

    def test_has_errors_false_when_no_errors(self):
        engine = ValidationEngine()
        result = engine.validate(
            [_rule("t1", ["s1"]), _rule("t2", ["s2"])],
            _source(),
            _target(),
        )
        # No existence errors, no required unmapped (t1 and t2 mapped)
        exist_errors = [
            i for i in result.issues
            if i.severity == Severity.ERROR
        ]
        # Could still have errors from required_target_mapped for unmapped fields
        # but t1 and t2 are both required and both mapped
        # So no errors from the first two rules
        # Other rules produce warnings only by default
        assert result.error_count == 0

    def test_error_count_matches(self):
        engine = ValidationEngine()
        rules = [_rule("BAD1", ["s1"]), _rule("BAD2", ["s2"])]
        result = engine.validate(rules, _source(), _target())

        # 2 from target_field_exists + 2 from required_target_mapped
        assert result.error_count == 4

    def test_to_dict_includes_counts(self):
        engine = ValidationEngine()
        result = engine.validate([], _source(), _target())
        d = result.to_dict()
        assert "error_count" in d
        assert "warning_count" in d
        assert "has_errors" in d
