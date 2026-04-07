"""Shared adapter contract test suite.

Every InputSchemaAdapter that returns a real CanonicalSchema (i.e. non-stub)
MUST satisfy these invariants.  Tests are parameterised over (adapter, input)
pairs so new adapters get coverage automatically.

Invariants verified per adapter:
  1. Returns a CanonicalSchema instance (type check).
  2. All fields have non-empty, non-None IDs.
  3. All field IDs are unique within the schema.
  4. All field paths are unique within the schema.
  5. All field paths are non-empty strings.
  6. No field has category=PRIMITIVE with a None/empty primitive type.
  7. Cardinality min_occurs >= 0.
  8. Cardinality max_occurs is None (unbounded) or >= min_occurs.
  9. Calling parse() twice with identical input produces identical field IDs
     and paths (determinism).
 10. CanonicalSchema.fields ordering is stable across repeated calls.
"""

from __future__ import annotations

from typing import Any, List, Tuple

import pytest

from packages.adapters.base import InputSchemaAdapter
from packages.adapters.input.csv_schema_adapter import CsvSchemaAdapter
from packages.adapters.input.json_schema_adapter import JsonSchemaAdapter
from packages.core.models.canonical_schema import CanonicalSchema, FieldTypeCategory

# ---------------------------------------------------------------------------
# Fixtures: (adapter_instance, raw_input, schema_name)
# ---------------------------------------------------------------------------

_SIMPLE_JSON_SCHEMA = {
    "title": "ContractTest",
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["id", "name"],
    "properties": {
        "id": {"type": "integer", "description": "Primary key"},
        "name": {
            "type": "object",
            "properties": {
                "given": {"type": "string", "title": "Given name"},
                "family": {"type": "string"},
            },
            "required": ["given"],
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "status": {
            "type": "string",
            "enum": ["active", "inactive"],
        },
    },
}

_SIMPLE_CSV_SCHEMA = (
    "name,type,required,label,description\n"
    "patient_id,integer,true,Patient ID,Unique identifier\n"
    "given_name,string,true,Given Name,First name\n"
    "family_name,string,false,Family Name,Last name\n"
    "birth_date,date,false,Birth Date,\n"
    "gender,string,false,Gender,\n"
)

# All (adapter, raw_input, description) triples to run through contract tests
_ADAPTER_CASES: List[Tuple[InputSchemaAdapter, Any, str]] = [
    (JsonSchemaAdapter(), _SIMPLE_JSON_SCHEMA, "JsonSchemaAdapter"),
    (CsvSchemaAdapter(), _SIMPLE_CSV_SCHEMA, "CsvSchemaAdapter"),
]

_ADAPTER_IDS = [case[2] for case in _ADAPTER_CASES]


@pytest.fixture(params=_ADAPTER_CASES, ids=_ADAPTER_IDS)
def adapter_and_input(request):
    adapter, raw_input, _ = request.param
    return adapter, raw_input


# ---------------------------------------------------------------------------
# Contract invariants
# ---------------------------------------------------------------------------

class TestAdapterContractInvariants:
    """Shared invariants that every non-stub InputSchemaAdapter MUST satisfy."""

    def test_returns_canonical_schema(self, adapter_and_input):
        adapter, raw_input = adapter_and_input
        result = adapter.parse(raw_input, schema_name="TestSchema", schema_version="1.0")
        assert isinstance(result, CanonicalSchema), (
            f"{type(adapter).__name__}.parse() must return a CanonicalSchema"
        )

    def test_all_fields_have_non_empty_id(self, adapter_and_input):
        adapter, raw_input = adapter_and_input
        schema = adapter.parse(raw_input)
        for f in schema.fields:
            assert f.id, f"Field at path {f.path!r} has empty ID"
            assert f.id.strip(), f"Field at path {f.path!r} has whitespace-only ID"

    def test_field_ids_are_unique(self, adapter_and_input):
        adapter, raw_input = adapter_and_input
        schema = adapter.parse(raw_input)
        ids = [f.id for f in schema.fields]
        assert len(ids) == len(set(ids)), (
            f"Duplicate field IDs found: {[i for i in ids if ids.count(i) > 1]}"
        )

    def test_field_paths_are_unique(self, adapter_and_input):
        adapter, raw_input = adapter_and_input
        schema = adapter.parse(raw_input)
        paths = [f.path for f in schema.fields]
        assert len(paths) == len(set(paths)), (
            f"Duplicate field paths found: {[p for p in paths if paths.count(p) > 1]}"
        )

    def test_all_field_paths_are_non_empty(self, adapter_and_input):
        adapter, raw_input = adapter_and_input
        schema = adapter.parse(raw_input)
        for f in schema.fields:
            assert f.path and f.path.strip(), "Field has empty or blank path"

    def test_primitive_fields_have_primitive_type(self, adapter_and_input):
        adapter, raw_input = adapter_and_input
        schema = adapter.parse(raw_input)
        for f in schema.fields:
            if f.field_type.category == FieldTypeCategory.PRIMITIVE:
                assert f.field_type.primitive, (
                    f"Field {f.path!r} is PRIMITIVE but has no primitive type string"
                )

    def test_cardinality_min_non_negative(self, adapter_and_input):
        adapter, raw_input = adapter_and_input
        schema = adapter.parse(raw_input)
        for f in schema.fields:
            assert f.cardinality.min_occurs >= 0, (
                f"Field {f.path!r} has negative min_occurs"
            )

    def test_cardinality_max_gte_min_or_none(self, adapter_and_input):
        adapter, raw_input = adapter_and_input
        schema = adapter.parse(raw_input)
        for f in schema.fields:
            mx = f.cardinality.max_occurs
            if mx is not None:
                assert mx >= f.cardinality.min_occurs, (
                    f"Field {f.path!r}: max_occurs ({mx}) < min_occurs ({f.cardinality.min_occurs})"
                )

    def test_deterministic_ids_across_calls(self, adapter_and_input):
        """Same input => same field IDs on every call."""
        adapter, raw_input = adapter_and_input
        schema1 = adapter.parse(raw_input)
        schema2 = adapter.parse(raw_input)
        ids1 = [f.id for f in schema1.fields]
        ids2 = [f.id for f in schema2.fields]
        assert ids1 == ids2, "Field IDs differ between repeated parses of identical input"

    def test_deterministic_paths_across_calls(self, adapter_and_input):
        """Same input => same field paths in same order on every call."""
        adapter, raw_input = adapter_and_input
        schema1 = adapter.parse(raw_input)
        schema2 = adapter.parse(raw_input)
        paths1 = [f.path for f in schema1.fields]
        paths2 = [f.path for f in schema2.fields]
        assert paths1 == paths2, "Field paths differ between repeated parses of identical input"

    def test_adapter_metadata_is_complete(self, adapter_and_input):
        """Metadata must have non-empty required fields."""
        adapter, _ = adapter_and_input
        meta = adapter.metadata
        assert meta.adapter_id, "adapter_id must not be empty"
        assert meta.display_name, "display_name must not be empty"
        assert meta.version, "version must not be empty"
        assert meta.supported_formats, "supported_formats must not be empty"
        for fmt in meta.supported_formats:
            assert fmt, "Each format identifier must be a non-empty string"


class TestRegistryContract:
    """The registry must satisfy resolution and introspection contracts."""

    def test_register_and_resolve(self):
        from packages.adapters.registry import AdapterRegistry
        registry = AdapterRegistry()
        adapter = JsonSchemaAdapter()
        registry.register_input(adapter)
        resolved = registry.resolve_input(JsonSchemaAdapter.FORMAT_ID)
        assert resolved is adapter

    def test_last_wins(self):
        from packages.adapters.registry import AdapterRegistry
        registry = AdapterRegistry()
        a1 = JsonSchemaAdapter()
        a2 = JsonSchemaAdapter()
        registry.register_input(a1)
        registry.register_input(a2)
        assert registry.resolve_input(JsonSchemaAdapter.FORMAT_ID) is a2

    def test_not_found_raises(self):
        from packages.adapters.base import AdapterNotFoundError
        from packages.adapters.registry import AdapterRegistry
        registry = AdapterRegistry()
        with pytest.raises(AdapterNotFoundError):
            registry.resolve_input("nonexistent_format_xyz")

    def test_list_formats(self):
        from packages.adapters.registry import AdapterRegistry
        registry = AdapterRegistry()
        registry.register_input(JsonSchemaAdapter())
        registry.register_input(CsvSchemaAdapter())
        fmts = registry.list_input_formats()
        assert JsonSchemaAdapter.FORMAT_ID in fmts
        assert CsvSchemaAdapter.FORMAT_ID in fmts
        assert fmts == sorted(fmts), "list_input_formats() must return sorted list"

    def test_is_supported(self):
        from packages.adapters.registry import AdapterRegistry
        registry = AdapterRegistry()
        registry.register_input(JsonSchemaAdapter())
        assert registry.is_input_format_supported(JsonSchemaAdapter.FORMAT_ID)
        assert not registry.is_input_format_supported("not_registered")

    def test_defaults_registration(self):
        """register_defaults() must register all 7 input adapters."""
        from packages.adapters.defaults import register_defaults
        from packages.adapters.registry import AdapterRegistry
        registry = AdapterRegistry()
        register_defaults(registry)
        expected_formats = [
            "csv_schema", "fhir_profile", "json_schema",
            "omop_cdm", "openehr", "parquet_schema", "sql_ddl",
        ]
        for fmt in expected_formats:
            assert registry.is_input_format_supported(fmt), (
                f"Format {fmt!r} not registered after register_defaults()"
            )


class TestStubAdaptersRaiseNotImplemented:
    """Stub adapters must compile, register, and raise NotImplementedError on parse()."""

    @pytest.mark.parametrize("format_id", [
        "fhir_profile", "omop_cdm", "sql_ddl", "openehr", "parquet_schema"
    ])
    def test_stub_raises(self, format_id):
        from packages.adapters.defaults import register_defaults
        from packages.adapters.registry import AdapterRegistry
        registry = AdapterRegistry()
        register_defaults(registry)
        stub = registry.resolve_input(format_id)
        with pytest.raises(NotImplementedError):
            stub.parse({})
