"""Validation Engine — policy-configurable mapping quality gates.

Design:
- Operates exclusively on CanonicalSchema / MappingRule objects (RL-05).
- No patient data (RL-02).
- Severities are NEVER hardcoded: every rule's severity can be overridden
  by the ValidationPolicy (RL-03, RL-15).
- Deterministic: issues are sorted by (severity_rank, rule_id, field_paths).
- Extensible: validation rules are injected; adding a new rule requires
  NO changes to this module.
"""

from __future__ import annotations

from typing import List, Optional

from packages.core.models.canonical_schema import CanonicalSchema
from packages.core.models.mapping_rule import MappingRule
from packages.validation.models import Severity, ValidationIssue, ValidationResult
from packages.validation.policy import ValidationPolicy, default_policy
from packages.validation.rules import ValidationRule, default_rules

_SEVERITY_RANK = {Severity.ERROR: 0, Severity.WARN: 1, Severity.INFO: 2}


class ValidationEngine:
    """Policy-configurable validation engine for mapping quality gates.

    Args:
        rules: List of ValidationRule instances. Defaults to rules.default_rules().
        policy: Severity policy. Defaults to policy.default_policy().
    """

    def __init__(
        self,
        rules: Optional[List[ValidationRule]] = None,
        policy: Optional[ValidationPolicy] = None,
    ) -> None:
        self._rules = rules if rules is not None else default_rules()
        self._policy = policy if policy is not None else default_policy()

    @property
    def policy(self) -> ValidationPolicy:
        return self._policy

    def validate(
        self,
        mapping_rules: List[MappingRule],
        source_schema: CanonicalSchema,
        target_schema: CanonicalSchema,
    ) -> ValidationResult:
        """Run all validation rules against the given mapping.

        Args:
            mapping_rules: The mapping rules to validate.
            source_schema: The pinned source canonical schema.
            target_schema: The pinned target canonical schema.

        Returns:
            A ValidationResult with deterministically ordered issues.
        """
        all_issues: List[ValidationIssue] = []

        for rule in self._rules:
            issues = rule.evaluate(
                mapping_rules, source_schema, target_schema, self._policy
            )
            all_issues.extend(issues)

        # Deterministic sort: severity rank → rule_id → field paths
        all_issues.sort(
            key=lambda i: (
                _SEVERITY_RANK.get(i.severity, 99),
                i.rule_id,
                tuple(i.affected_field_paths),
            )
        )

        return ValidationResult(issues=all_issues)
