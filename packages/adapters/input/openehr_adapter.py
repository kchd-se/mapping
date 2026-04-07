"""OpenEHR Adapter — STUB.

TODO: placeholder for v2 / later phase.

This stub satisfies the adapter contract for the 'openehr' format.

Full implementation requires:
  - Parsing openEHR Archetype Definition Language (ADL) 1.4 and ADL 2 files.
  - Alternatively: parsing Operational Templates (OPT/OPT2) in XML format.
  - Extracting: node identifiers, rm_type_names, cardinality intervals,
    occurrences, terminology bindings, and language annotations.
  - Supporting multilingual labels (Swedish, English) from the language section.
  - Mapping openEHR reference model types (DV_TEXT, DV_CODED_TEXT, DV_DATE_TIME,
    DV_QUANTITY, etc.) to canonical primitive names.

Known gaps (to resolve when implementing):
  - ADL files require a specialised parser; no standard library support exists.
  - openEHR paths use '/'-delimited node identifiers (archetypeNodeId).
  - AT codes (at0001, etc.) need to be resolved via ontology section for labels.
"""

from __future__ import annotations

from typing import Any, Optional

from packages.adapters.base import AdapterMetadata, InputSchemaAdapter
from packages.core.models.canonical_schema import CanonicalSchema


class OpenEhrAdapter(InputSchemaAdapter):
    """Stub adapter for openEHR archetypes and operational templates.

    TODO: placeholder for v2 — not implemented.
    """

    FORMAT_ID = "openehr"

    def __init__(self) -> None:
        self._meta = AdapterMetadata(
            adapter_id="openehr_adapter_stub",
            display_name="openEHR Adapter (Stub)",
            version="0.0.0",
            supported_formats=[self.FORMAT_ID],
            description=(
                "TODO: placeholder for v2. "
                "Will parse openEHR archetypes/templates into the canonical model."
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
            "OpenEhrAdapter is a stub — TODO: placeholder for v2. "
            "Full implementation is deferred to a later phase."
        )
