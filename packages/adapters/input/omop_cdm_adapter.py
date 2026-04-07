"""OMOP CDM Input Adapter — STUB.

TODO: placeholder for v2 / later phase.

This stub satisfies the adapter contract so the registry can list the 'omop_cdm'
format.

Full implementation requires:
  - Fetching OMOP CDM definitions from the OHDSI GitHub or a local cache (Phase 3).
  - Parsing CDM table/field descriptors (vocabulary, domain, field type, required, etc.)
    into canonical fields.
  - Supporting multiple CDM versions (5.3, 5.4, 6.0).
  - Translating OMOP concept domain references into TerminologyReferences.

Known gaps (to resolve when implementing):
  - OMOP uses integer concept_ids rather than string codes.
  - Vocabulary references (vocabulary_id, domain_id) need to map to terminology systems.
  - CDM has compound PKs and FK references that need structural representation.
"""

from __future__ import annotations

from typing import Any, Optional

from packages.adapters.base import AdapterMetadata, InputSchemaAdapter
from packages.core.models.canonical_schema import CanonicalSchema


class OmopCdmAdapter(InputSchemaAdapter):
    """Stub adapter for OMOP CDM schemas.

    TODO: placeholder for v2 — not implemented.
    """

    FORMAT_ID = "omop_cdm"

    def __init__(self) -> None:
        self._meta = AdapterMetadata(
            adapter_id="omop_cdm_adapter_stub",
            display_name="OMOP CDM Adapter (Stub)",
            version="0.0.0",
            supported_formats=[self.FORMAT_ID],
            description=(
                "TODO: placeholder for v2. "
                "Will parse OMOP CDM table definitions into the canonical model."
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
            "OmopCdmAdapter is a stub — TODO: placeholder for v2. "
            "Full implementation is deferred to the catalog/sync phase."
        )
