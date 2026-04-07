"""Parquet Schema Input Adapter — STUB.

TODO: placeholder for v2 / later phase.

This stub satisfies the adapter contract for the 'parquet_schema' format.

Full implementation requires:
  - Accepting a Parquet schema representation and converting it to canonical fields.
  - The `pyarrow` library exposes `Schema` and `Field` objects with names, types,
    and nullability; this is the recommended parsing approach.
  - Alternatively, accept a serialised JSON representation of a Parquet schema
    (e.g. from `schema.to_arrow_schema().to_pydict()`) to avoid the pyarrow
    dependency in the core adapter package.
  - Mapping Parquet/Arrow physical types (INT32, UTF8, FLOAT, TIMESTAMP_MICROS, etc.)
    to canonical primitive names.
  - Handling nested schemas (STRUCT → OBJECT, LIST → ARRAY, MAP → special).

Known gaps (to resolve when implementing):
  - Parquet schemas carry no constraint metadata (no required/enum/pattern).
  - Logical type annotations (DATE, TIME, DECIMAL) need to map to canonical types.
  - Whether to take pyarrow as a runtime dependency or accept a dict representation
    must be decided before implementation.
"""

from __future__ import annotations

from typing import Any, Optional

from packages.adapters.base import AdapterMetadata, InputSchemaAdapter
from packages.core.models.canonical_schema import CanonicalSchema


class ParquetSchemaAdapter(InputSchemaAdapter):
    """Stub adapter for Parquet schemas.

    TODO: placeholder for v2 — not implemented.
    """

    FORMAT_ID = "parquet_schema"

    def __init__(self) -> None:
        self._meta = AdapterMetadata(
            adapter_id="parquet_schema_adapter_stub",
            display_name="Parquet Schema Adapter (Stub)",
            version="0.0.0",
            supported_formats=[self.FORMAT_ID],
            description=(
                "TODO: placeholder for v2. "
                "Will parse Parquet/Arrow schema definitions into the canonical model."
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
            "ParquetSchemaAdapter is a stub — TODO: placeholder for v2. "
            "Full implementation is deferred to a later phase."
        )
