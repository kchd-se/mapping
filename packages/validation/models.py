"""Validation Engine domain models.

Pure data structures — no format-specific logic (RL-05).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARN = "warn"
    INFO = "info"


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation finding.

    Attributes:
        rule_id: Identifier of the validation rule that fired.
        severity: error/warn/info — determined by policy, NOT hardcoded.
        message: Human-readable description of the issue.
        affected_field_ids: CanonicalField IDs involved.
        affected_field_paths: CanonicalField paths (human-friendly).
        remediation_hint: Optional suggestion for fixing the issue.
    """

    rule_id: str
    severity: Severity
    message: str
    affected_field_ids: List[str] = field(default_factory=list)
    affected_field_paths: List[str] = field(default_factory=list)
    remediation_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "affected_field_ids": list(self.affected_field_ids),
            "affected_field_paths": list(self.affected_field_paths),
        }
        if self.remediation_hint is not None:
            d["remediation_hint"] = self.remediation_hint
        return d


@dataclass(frozen=True)
class ValidationResult:
    """Complete validation output for a mapping version.

    issues is deterministically ordered: by severity (error>warn>info), then
    by rule_id, then by affected_field_paths.
    """

    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARN)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issues": [i.to_dict() for i in self.issues],
            "has_errors": self.has_errors,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }
