"""Default adapter registration.

Calling register_defaults() wires all built-in adapters into the provided
(or default) registry.  Application startup code calls this once; tests
create a fresh registry to avoid shared state.

Adapters are registered in a deterministic order so list_input_formats()
returns a stable result.
"""

from __future__ import annotations

from packages.adapters.input.csv_schema_adapter import CsvSchemaAdapter
from packages.adapters.input.fhir_profile_adapter import FhirProfileAdapter
from packages.adapters.input.json_schema_adapter import JsonSchemaAdapter
from packages.adapters.input.omop_cdm_adapter import OmopCdmAdapter
from packages.adapters.input.openehr_adapter import OpenEhrAdapter
from packages.adapters.input.parquet_schema_adapter import ParquetSchemaAdapter
from packages.adapters.input.sql_ddl_adapter import SqlDdlAdapter
from packages.adapters.registry import AdapterRegistry, get_default_registry


def register_defaults(registry: AdapterRegistry | None = None) -> AdapterRegistry:
    """Register all built-in adapters into *registry*.

    Args:
        registry: Target registry.  Defaults to the module-level default.

    Returns:
        The registry after registration (convenient for chaining in tests).
    """
    if registry is None:
        registry = get_default_registry()

    for adapter in [
        JsonSchemaAdapter(),
        CsvSchemaAdapter(),
        FhirProfileAdapter(),
        OmopCdmAdapter(),
        SqlDdlAdapter(),
        OpenEhrAdapter(),
        ParquetSchemaAdapter(),
    ]:
        registry.register_input(adapter)

    return registry
