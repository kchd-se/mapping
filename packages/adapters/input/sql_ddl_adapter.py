"""SQL DDL Input Adapter — STUB.

TODO: placeholder for v2 / later phase.

This stub satisfies the adapter contract so the registry can list the 'sql_ddl'
format.

Full implementation requires:
  - Parsing SQL DDL statements (CREATE TABLE, column definitions, constraints).
  - Handling at least: ANSI SQL, T-SQL, PostgreSQL, and MySQL dialects.
  - Extracting: column name, SQL type, NOT NULL, DEFAULT, CHECK constraints,
    PRIMARY KEY, FOREIGN KEY references.
  - Converting SQL types to canonical primitive names.

Known gaps (to resolve when implementing):
  - SQL dialects diverge significantly in type names and constraint syntax.
  - A robust parser (e.g. sqlparse or a hand-written recursive descent parser)
    is needed — regex-only approaches break on edge cases (lesson from POC).
  - FOREIGN KEY references should produce TerminologyReferences or structural links.
  - Multi-schema (catalog.schema.table) qualified names need path normalisation.
"""

from __future__ import annotations

from typing import Any, Optional

from packages.adapters.base import AdapterMetadata, InputSchemaAdapter
from packages.core.models.canonical_schema import CanonicalSchema


class SqlDdlAdapter(InputSchemaAdapter):
    """Stub adapter for SQL DDL schemas.

    TODO: placeholder for v2 — not implemented.
    """

    FORMAT_ID = "sql_ddl"

    def __init__(self) -> None:
        self._meta = AdapterMetadata(
            adapter_id="sql_ddl_adapter_stub",
            display_name="SQL DDL Adapter (Stub)",
            version="0.0.0",
            supported_formats=[self.FORMAT_ID],
            description=(
                "TODO: placeholder for v2. "
                "Will parse SQL DDL CREATE TABLE statements into the canonical model."
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
            "SqlDdlAdapter is a stub — TODO: placeholder for v2. "
            "Full implementation is deferred to a later phase."
        )
