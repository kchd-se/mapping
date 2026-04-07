"""FHIR Profile Input Adapter — STUB.

TODO: placeholder for v2 / later phase.

This stub satisfies the adapter contract so the registry can list the 'fhir_profile'
format and raise a clear NotImplementedError rather than failing silently.

Full implementation requires:
  - Fetching FHIR StructureDefinition resources from an online registry (Phase 3 catalog).
  - Parsing ElementDefinition trees into canonical fields.
  - Resolving FHIR type codes, binding strengths, and cardinality notation (x..y).
  - Supporting FHIR versions R4 and R5 profiles.

Known gaps (to resolve when implementing):
  - FHIR element paths use '.' notation with slicing (e.g. Patient.name:official).
  - Cardinality is expressed as strings ("0..*", "1..1") not integers.
  - Terminology bindings map to ValueSets, not inline enums.
"""

from __future__ import annotations

from typing import Any, Optional

from packages.adapters.base import AdapterMetadata, InputSchemaAdapter
from packages.core.models.canonical_schema import CanonicalSchema


class FhirProfileAdapter(InputSchemaAdapter):
    """Stub adapter for FHIR StructureDefinition profiles.

    TODO: placeholder for v2 — not implemented.
    """

    FORMAT_ID = "fhir_profile"

    def __init__(self) -> None:
        self._meta = AdapterMetadata(
            adapter_id="fhir_profile_adapter_stub",
            display_name="FHIR Profile Adapter (Stub)",
            version="0.0.0",
            supported_formats=[self.FORMAT_ID],
            description=(
                "TODO: placeholder for v2. "
                "Will parse FHIR StructureDefinition resources into the canonical model."
            ),
        )

    @property
    def metadata(self) -> AdapterMetadata:
        return self._meta

    def parse(
        self,
        raw_input: Any,
        schema_name: str = "",
        schema_version: str = "",
    ) -> CanonicalSchema:
        raise NotImplementedError(
            "FhirProfileAdapter is a stub — TODO: placeholder for v2. "
            "Full implementation is deferred to the catalog/sync phase."
        )
