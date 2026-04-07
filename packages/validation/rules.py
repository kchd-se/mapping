"""Validation rules — individual checks applied to mapping rules.

Each rule is a callable conforming to the ValidationRule protocol.
New rules can be added by implementing the protocol and registering
the rule with the ValidationEngine.  No engine changes are needed.

Rules operate ONLY on CanonicalSchema / MappingRule objects (RL-05).
No patient data is accessed (RL-02).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from packages.core.models.canonical_schema import (
    CanonicalField,
    CanonicalSchema,
    FieldTypeCategory,
)
from packages.core.models.mapping_rule import MappingRule
from packages.validation.models import Severity, ValidationIssue
from packages.validation.policy import ValidationPolicy


# ---------------------------------------------------------------------------
# Rule protocol
# ---------------------------------------------------------------------------


class ValidationRule(Protocol):
    """Protocol for validation rules."""

    @property
    def rule_id(self) -> str: ...

    @property
    def default_severity(self) -> Severity: ...

    def evaluate(
        self,
        rules: List[MappingRule],
        source_schema: CanonicalSchema,
        target_schema: CanonicalSchema,
        policy: ValidationPolicy,
    ) -> List[ValidationIssue]: ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _field_index(schema: CanonicalSchema) -> Dict[str, CanonicalField]:
    """Build an id → CanonicalField index for fast lookup."""
    return {f.id: f for f in schema.fields}


def _path_index(schema: CanonicalSchema) -> Dict[str, CanonicalField]:
    """Build a path → CanonicalField index."""
    return {f.path: f for f in schema.fields}


# ---------------------------------------------------------------------------
# Rule 1: Target field existence (RL-14 — non-negotiable)
# ---------------------------------------------------------------------------


class TargetFieldExistsRule:
    """Every mapped target_field_id MUST exist in the target schema.

    RL-14: MUST NOT allow mapping to nonexistent target fields.
    Default severity is ERROR and should almost never be overridden to warn.
    """

    @property
    def rule_id(self) -> str:
        return "target_field_exists"

    @property
    def default_severity(self) -> Severity:
        return Severity.ERROR

    def evaluate(
        self,
        rules: List[MappingRule],
        source_schema: CanonicalSchema,
        target_schema: CanonicalSchema,
        policy: ValidationPolicy,
    ) -> List[ValidationIssue]:
        severity = policy.resolve_severity(self.rule_id, self.default_severity)
        target_ids = {f.id for f in target_schema.fields}
        issues: List[ValidationIssue] = []

        for rule in rules:
            if rule.target_field_id not in target_ids:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=severity,
                        message=(
                            f"Mapped target field '{rule.target_field_id}' does not "
                            f"exist in target schema '{target_schema.name}'."
                        ),
                        affected_field_ids=[rule.target_field_id],
                        affected_field_paths=[rule.target_field_id],
                        remediation_hint=(
                            "Remove this mapping rule or correct the target field ID."
                        ),
                    )
                )

        return issues


# ---------------------------------------------------------------------------
# Rule 2: Required target fields mapped
# ---------------------------------------------------------------------------


class RequiredTargetFieldsMappedRule:
    """All required target fields should be mapped (or explicitly constant/default).

    A target field is considered "required" if constraints.required is True.
    """

    @property
    def rule_id(self) -> str:
        return "required_target_mapped"

    @property
    def default_severity(self) -> Severity:
        return Severity.ERROR

    def evaluate(
        self,
        rules: List[MappingRule],
        source_schema: CanonicalSchema,
        target_schema: CanonicalSchema,
        policy: ValidationPolicy,
    ) -> List[ValidationIssue]:
        severity = policy.resolve_severity(self.rule_id, self.default_severity)

        mapped_target_ids = {r.target_field_id for r in rules}
        issues: List[ValidationIssue] = []

        for tf in sorted(target_schema.fields, key=lambda f: f.path):
            if tf.constraints.required and tf.id not in mapped_target_ids:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=severity,
                        message=(
                            f"Required target field '{tf.path}' is not mapped."
                        ),
                        affected_field_ids=[tf.id],
                        affected_field_paths=[tf.path],
                        remediation_hint=(
                            "Create a mapping rule targeting this field, or add "
                            "a constant/default value."
                        ),
                    )
                )

        return issues


# ---------------------------------------------------------------------------
# Rule 3: Type compatibility
# ---------------------------------------------------------------------------

_COMPATIBLE_TYPES: set[tuple[str, str]] = {
    ("integer", "decimal"),
    ("integer", "string"),
    ("decimal", "string"),
    ("boolean", "string"),
    ("boolean", "integer"),
    ("date", "datetime"),
    ("date", "string"),
    ("datetime", "string"),
    ("code", "string"),
    ("uri", "string"),
}


class TypeCompatibilityRule:
    """Check that source and target field types are compatible."""

    @property
    def rule_id(self) -> str:
        return "type_compatibility"

    @property
    def default_severity(self) -> Severity:
        return Severity.WARN

    def evaluate(
        self,
        rules: List[MappingRule],
        source_schema: CanonicalSchema,
        target_schema: CanonicalSchema,
        policy: ValidationPolicy,
    ) -> List[ValidationIssue]:
        severity = policy.resolve_severity(self.rule_id, self.default_severity)
        src_idx = _field_index(source_schema)
        tgt_idx = _field_index(target_schema)
        issues: List[ValidationIssue] = []

        for rule in sorted(rules, key=lambda r: r.target_field_id):
            target_field = tgt_idx.get(rule.target_field_id)
            if target_field is None:
                continue  # caught by TargetFieldExistsRule

            for src_id in sorted(rule.source_field_ids):
                source_field = src_idx.get(src_id)
                if source_field is None:
                    issues.append(
                        ValidationIssue(
                            rule_id=self.rule_id,
                            severity=severity,
                            message=(
                                f"Source field '{src_id}' referenced in mapping "
                                f"rule does not exist in source schema."
                            ),
                            affected_field_ids=[src_id, rule.target_field_id],
                            affected_field_paths=[src_id, target_field.path],
                            remediation_hint="Correct the source field ID.",
                        )
                    )
                    continue

                if not self._types_compatible(
                    source_field.field_type, target_field.field_type
                ):
                    issues.append(
                        ValidationIssue(
                            rule_id=self.rule_id,
                            severity=severity,
                            message=(
                                f"Type mismatch: source '{source_field.path}' "
                                f"({self._type_label(source_field.field_type)}) → "
                                f"target '{target_field.path}' "
                                f"({self._type_label(target_field.field_type)})."
                            ),
                            affected_field_ids=[source_field.id, target_field.id],
                            affected_field_paths=[source_field.path, target_field.path],
                            remediation_hint=(
                                "Add a transform hint to handle the type conversion, "
                                "or choose a different source field."
                            ),
                        )
                    )

        return issues

    @staticmethod
    def _types_compatible(src_ft, tgt_ft) -> bool:
        if src_ft.category != tgt_ft.category:
            return False
        if src_ft.category != FieldTypeCategory.PRIMITIVE:
            return True  # structural match for object/array
        s = src_ft.primitive or ""
        t = tgt_ft.primitive or ""
        if s == t:
            return True
        return (s, t) in _COMPATIBLE_TYPES or (t, s) in _COMPATIBLE_TYPES

    @staticmethod
    def _type_label(ft) -> str:
        if ft.category == FieldTypeCategory.PRIMITIVE:
            return ft.primitive or "unknown"
        return ft.category.value


# ---------------------------------------------------------------------------
# Rule 4: Cardinality compatibility
# ---------------------------------------------------------------------------


class CardinalityCompatibilityRule:
    """Check that source cardinality is compatible with target expectations."""

    @property
    def rule_id(self) -> str:
        return "cardinality_compatibility"

    @property
    def default_severity(self) -> Severity:
        return Severity.WARN

    def evaluate(
        self,
        rules: List[MappingRule],
        source_schema: CanonicalSchema,
        target_schema: CanonicalSchema,
        policy: ValidationPolicy,
    ) -> List[ValidationIssue]:
        severity = policy.resolve_severity(self.rule_id, self.default_severity)
        src_idx = _field_index(source_schema)
        tgt_idx = _field_index(target_schema)
        issues: List[ValidationIssue] = []

        for rule in sorted(rules, key=lambda r: r.target_field_id):
            target_field = tgt_idx.get(rule.target_field_id)
            if target_field is None:
                continue

            for src_id in sorted(rule.source_field_ids):
                source_field = src_idx.get(src_id)
                if source_field is None:
                    continue

                issue = self._check_cardinality(
                    source_field, target_field, severity
                )
                if issue:
                    issues.append(issue)

        return issues

    @staticmethod
    def _check_cardinality(
        source: CanonicalField, target: CanonicalField, severity: Severity
    ) -> Optional[ValidationIssue]:
        sc = source.cardinality
        tc = target.cardinality

        # Multi-valued source → single-valued target
        s_multi = sc.max_occurs is None or (sc.max_occurs is not None and sc.max_occurs > 1)
        t_single = tc.max_occurs is not None and tc.max_occurs == 1

        if s_multi and t_single:
            return ValidationIssue(
                rule_id="cardinality_compatibility",
                severity=severity,
                message=(
                    f"Cardinality mismatch: source '{source.path}' is multi-valued "
                    f"(max={sc.max_occurs}) but target '{target.path}' is single-valued."
                ),
                affected_field_ids=[source.id, target.id],
                affected_field_paths=[source.path, target.path],
                remediation_hint=(
                    "Add a transform hint to select one value, or adjust the target schema."
                ),
            )

        # Required target (min>0) with optional source (min=0)
        if tc.min_occurs > 0 and sc.min_occurs == 0:
            return ValidationIssue(
                rule_id="cardinality_compatibility",
                severity=severity,
                message=(
                    f"Cardinality mismatch: target '{target.path}' requires "
                    f"min={tc.min_occurs} but source '{source.path}' allows min=0."
                ),
                affected_field_ids=[source.id, target.id],
                affected_field_paths=[source.path, target.path],
                remediation_hint=(
                    "Add a default value for when the source field is absent."
                ),
            )

        return None


# ---------------------------------------------------------------------------
# Rule 5: Constraint conflicts (enum/pattern/range)
# ---------------------------------------------------------------------------


class ConstraintConflictRule:
    """Detect constraint conflicts between mapped source and target fields.

    Checks:
    - Enum: source has values not in target enum
    - Pattern: target has a regex pattern but source does not
    - Range: source range exceeds target range
    """

    @property
    def rule_id(self) -> str:
        return "constraint_conflict"

    @property
    def default_severity(self) -> Severity:
        return Severity.WARN

    def evaluate(
        self,
        rules: List[MappingRule],
        source_schema: CanonicalSchema,
        target_schema: CanonicalSchema,
        policy: ValidationPolicy,
    ) -> List[ValidationIssue]:
        severity = policy.resolve_severity(self.rule_id, self.default_severity)
        src_idx = _field_index(source_schema)
        tgt_idx = _field_index(target_schema)
        issues: List[ValidationIssue] = []

        for rule in sorted(rules, key=lambda r: r.target_field_id):
            target_field = tgt_idx.get(rule.target_field_id)
            if target_field is None:
                continue

            for src_id in sorted(rule.source_field_ids):
                source_field = src_idx.get(src_id)
                if source_field is None:
                    continue

                issues.extend(
                    self._check_constraints(source_field, target_field, severity)
                )

        return issues

    @staticmethod
    def _check_constraints(
        source: CanonicalField, target: CanonicalField, severity: Severity
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        sc = source.constraints
        tc = target.constraints

        # Enum conflict
        if tc.enums and sc.enums:
            source_extra = set(sc.enums) - set(tc.enums)
            if source_extra:
                issues.append(
                    ValidationIssue(
                        rule_id="constraint_conflict",
                        severity=severity,
                        message=(
                            f"Enum conflict: source '{source.path}' has values "
                            f"{sorted(source_extra)} not in target '{target.path}' enum."
                        ),
                        affected_field_ids=[source.id, target.id],
                        affected_field_paths=[source.path, target.path],
                        remediation_hint="Add a value mapping or restrict source values.",
                    )
                )

        # Target has pattern but source does not
        if tc.pattern and not sc.pattern:
            issues.append(
                ValidationIssue(
                    rule_id="constraint_conflict",
                    severity=severity,
                    message=(
                        f"Pattern constraint: target '{target.path}' requires pattern "
                        f"'{tc.pattern}' but source '{source.path}' has no pattern constraint."
                    ),
                    affected_field_ids=[source.id, target.id],
                    affected_field_paths=[source.path, target.path],
                    remediation_hint="Ensure source data conforms to the target pattern.",
                )
            )

        # Range conflicts
        if tc.min_value is not None and sc.min_value is not None:
            if sc.min_value < tc.min_value:
                issues.append(
                    ValidationIssue(
                        rule_id="constraint_conflict",
                        severity=severity,
                        message=(
                            f"Range conflict: source '{source.path}' min={sc.min_value} "
                            f"< target '{target.path}' min={tc.min_value}."
                        ),
                        affected_field_ids=[source.id, target.id],
                        affected_field_paths=[source.path, target.path],
                        remediation_hint="Clamp or filter source values before mapping.",
                    )
                )

        if tc.max_value is not None and sc.max_value is not None:
            if sc.max_value > tc.max_value:
                issues.append(
                    ValidationIssue(
                        rule_id="constraint_conflict",
                        severity=severity,
                        message=(
                            f"Range conflict: source '{source.path}' max={sc.max_value} "
                            f"> target '{target.path}' max={tc.max_value}."
                        ),
                        affected_field_ids=[source.id, target.id],
                        affected_field_paths=[source.path, target.path],
                        remediation_hint="Clamp or filter source values before mapping.",
                    )
                )

        return issues


# ---------------------------------------------------------------------------
# Default rule set
# ---------------------------------------------------------------------------

def default_rules() -> List[ValidationRule]:
    """Return the standard set of validation rules."""
    return [
        TargetFieldExistsRule(),
        RequiredTargetFieldsMappedRule(),
        TypeCompatibilityRule(),
        CardinalityCompatibilityRule(),
        ConstraintConflictRule(),
    ]
