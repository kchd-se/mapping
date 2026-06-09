"""Script Generator interface (Protocol).

Defines the stable, extensible contract that ALL concrete generators must
satisfy.  Adding a new generator (FHIR mappings, CSV, XLSX, Python pandas,
etc.) requires:

  1. Implement a class with a ``generate`` method matching this signature.
  2. Register it in the generator registry (registry.py).
  3. Zero changes to the export router or any other existing code.

The interface is intentionally narrow:
  - Accepts only canonical-model objects (RL-05).
  - Produces a GeneratedScript (text + metadata).
  - Has NO side effects (no I/O, no state mutation).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from packages.core.models.canonical_schema import CanonicalSchema
from packages.core.serialization.artifact import MappingArtifact
from packages.script_gen.models import GeneratedScript


@runtime_checkable
class ScriptGenerator(Protocol):
    """Protocol that all script generators must implement."""

    #: Stable identifier used to select this generator via the registry.
    generator_id: str

    #: Semver string incremented when the generator output format changes.
    generator_version: str

    def generate(
        self,
        artifact: MappingArtifact,
        source_schema: CanonicalSchema,
        target_schema: CanonicalSchema,
    ) -> GeneratedScript:
        """Generate a deterministic transformation script.

        Args:
            artifact:       Mapping artifact containing project + version data.
            source_schema:  Resolved canonical source schema.
            target_schema:  Resolved canonical target schema.

        Returns:
            A GeneratedScript with deterministic, byte-identical output for
            identical inputs.  The script MUST NOT be executed in v1 (RL-01).
        """
        ...
