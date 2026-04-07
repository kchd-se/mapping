"""Validation policy model — configurable severity per rule.

Severities are NEVER hardcoded (RL-03).  A ValidationPolicy maps each
rule_id to a Severity.  If a rule is not present in the policy, the
rule's own default_severity is used.

Policy-configurable severity — how it works:
    1. Each validation rule has a rule_id and a default_severity.
    2. A ValidationPolicy contains an overrides dict: rule_id → Severity.
    3. When the engine fires a rule, it looks up the severity in the policy
       first, falling back to the rule's default.
    4. Policies are scoped per-project (or per-deployment/region) — the
       caller chooses which policy to pass.
    5. Setting a rule to None / omitting it uses the default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from packages.validation.models import Severity


@dataclass
class ValidationPolicy:
    """Policy controlling validation severity per rule.

    Attributes:
        id: Unique policy identifier.
        name: Human-friendly name (e.g. "Region X strict", "POC lenient").
        severity_overrides: rule_id → Severity.  If a rule_id is not present,
            the rule's default_severity applies.
    """

    id: str = ""
    name: str = ""
    severity_overrides: Dict[str, Severity] = field(default_factory=dict)

    def resolve_severity(self, rule_id: str, default: Severity) -> Severity:
        """Return the effective severity for *rule_id*.

        Uses the override if configured, otherwise falls back to *default*.
        """
        return self.severity_overrides.get(rule_id, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "severity_overrides": {
                k: v.value for k, v in sorted(self.severity_overrides.items())
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ValidationPolicy:
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            severity_overrides={
                k: Severity(v)
                for k, v in data.get("severity_overrides", {}).items()
            },
        )


def default_policy() -> ValidationPolicy:
    """A lenient default policy — all rules use their built-in defaults."""
    return ValidationPolicy(id="default", name="Default policy")
