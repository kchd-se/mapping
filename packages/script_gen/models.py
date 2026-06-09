"""Script generation domain models.

Pure data structures — no format logic lives here (RL-05).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class GeneratedScript:
    """The output produced by a ScriptGenerator.

    Attributes:
        generator_id:   Stable identifier for the generator that produced this
                        script (e.g. "sql_insert_select_v1").
        generator_version: Semver string for the generator implementation.
        script_text:    The complete, deterministic transformation script as a
                        UTF-8 string.  Read-only in v1 — NOT executed (RL-01).
        metadata:       Structured copy of the header fields for programmatic
                        access without re-parsing the script text.
    """

    generator_id: str
    generator_version: str
    script_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
