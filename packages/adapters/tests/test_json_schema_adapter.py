"""Unit tests specific to the JSON Schema Input Adapter.

Covers nested objects, arrays, $ref resolution, allOf, constraints,
format hints, Swedish characters, and error handling.
"""

from __future__ import annotations

import pytest

from packages.adapters.base import AdapterParseError
from packages.adapters.input.json_schema_adapter import JsonSchemaAdapter, _stable_field_id
from packages.core.models.canonical_schema import FieldTypeCategory


@pytest.fixture
def adapter():
    return JsonSchemaAdapter()


class TestMetadata:
    def test_format_id(self, adapter):
        assert JsonSchemaAdapter.FORMAT_ID in adapter.metadata.supported_formats

    def test_version_present(self, adapter):
        assert adapter.metadata.version


class TestFlatSchema:
    def test_simple_flat_schema(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "title": "Patient",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
                "required": ["id"],
            },
            schema_name="Patient",
            schema_version="1.0",
        )
        assert schema.name == "Patient"
        assert schema.version == "1.0"
        paths = {f.path for f in schema.fields}
        assert "id" in paths
        assert "name" in paths

    def test_required_field_has_min_occurs_1(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {"req": {"type": "string"}, "opt": {"type": "string"}},
                "required": ["req"],
            }
        )
        field_map = {f.path: f for f in schema.fields}
        assert field_map["req"].cardinality.min_occurs == 1
        assert field_map["opt"].cardinality.min_occurs == 0

    def test_boolean_field_type(self, adapter):
        schema = adapter.parse(
            {"type": "object", "properties": {"active": {"type": "boolean"}}}
        )
        f = next(f for f in schema.fields if f.path == "active")
        assert f.field_type.category == FieldTypeCategory.PRIMITIVE
        assert f.field_type.primitive == "boolean"

    def test_number_maps_to_decimal(self, adapter):
        schema = adapter.parse(
            {"type": "object", "properties": {"weight": {"type": "number"}}}
        )
        f = next(f for f in schema.fields if f.path == "weight")
        assert f.field_type.primitive == "decimal"

    def test_format_hint_datetime(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "created": {"type": "string", "format": "date-time"}
                },
            }
        )
        f = next(f for f in schema.fields if f.path == "created")
        assert f.field_type.primitive == "datetime"

    def test_format_hint_date(self, adapter):
        schema = adapter.parse(
            {"type": "object", "properties": {"dob": {"type": "string", "format": "date"}}}
        )
        f = next(f for f in schema.fields if f.path == "dob")
        assert f.field_type.primitive == "date"


class TestNestedObjects:
    def test_nested_object_emits_object_and_child_fields(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                        },
                        "required": ["city"],
                    }
                },
            }
        )
        paths = {f.path for f in schema.fields}
        assert "address" in paths
        assert "address.street" in paths
        assert "address.city" in paths
        addr_field = next(f for f in schema.fields if f.path == "address")
        assert addr_field.field_type.category == FieldTypeCategory.OBJECT

    def test_nested_required_propagates(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "object",
                        "properties": {
                            "given": {"type": "string"},
                            "family": {"type": "string"},
                        },
                        "required": ["given"],
                    }
                },
            }
        )
        field_map = {f.path: f for f in schema.fields}
        assert field_map["name.given"].cardinality.min_occurs == 1
        assert field_map["name.family"].cardinality.min_occurs == 0

    def test_triple_nesting(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "object",
                        "properties": {
                            "b": {
                                "type": "object",
                                "properties": {
                                    "c": {"type": "string"}
                                },
                            }
                        },
                    }
                },
            }
        )
        paths = {f.path for f in schema.fields}
        assert "a" in paths
        assert "a.b" in paths
        assert "a.b.c" in paths


class TestArrayFields:
    def test_array_of_primitives(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
            }
        )
        f = next(f for f in schema.fields if f.path == "tags")
        assert f.field_type.category == FieldTypeCategory.ARRAY
        assert f.field_type.items_type is not None
        assert f.field_type.items_type.primitive == "string"
        assert f.cardinality.max_occurs is None  # unbounded

    def test_array_required_has_min_occurs_1(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "required": ["codes"],
                "properties": {
                    "codes": {"type": "array", "items": {"type": "integer"}}
                },
            }
        )
        f = next(f for f in schema.fields if f.path == "codes")
        assert f.cardinality.min_occurs == 1

    def test_array_of_objects_items_type_is_object(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "contacts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"phone": {"type": "string"}},
                        },
                    }
                },
            }
        )
        f = next(f for f in schema.fields if f.path == "contacts")
        assert f.field_type.category == FieldTypeCategory.ARRAY
        assert f.field_type.items_type.category == FieldTypeCategory.OBJECT


class TestConstraints:
    def test_enum_constraint(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["active", "inactive"]}
                },
            }
        )
        f = next(f for f in schema.fields if f.path == "status")
        assert f.constraints.enums == ["active", "inactive"]

    def test_string_length_constraints(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "minLength": 2, "maxLength": 10}
                },
            }
        )
        f = next(f for f in schema.fields if f.path == "code")
        assert f.constraints.min_length == 2
        assert f.constraints.max_length == 10

    def test_numeric_range_constraints(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "age": {"type": "integer", "minimum": 0, "maximum": 150}
                },
            }
        )
        f = next(f for f in schema.fields if f.path == "age")
        assert f.constraints.min_value == 0
        assert f.constraints.max_value == 150

    def test_pattern_constraint(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "ssn": {"type": "string", "pattern": r"^\d{6}-\d{4}$"}
                },
            }
        )
        f = next(f for f in schema.fields if f.path == "ssn")
        assert f.constraints.pattern == r"^\d{6}-\d{4}$"


class TestRefResolution:
    def test_defs_ref_resolution(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "$defs": {
                    "Name": {
                        "type": "object",
                        "properties": {
                            "given": {"type": "string"},
                            "family": {"type": "string"},
                        },
                    }
                },
                "properties": {
                    "name": {"$ref": "#/$defs/Name"}
                },
            }
        )
        paths = {f.path for f in schema.fields}
        assert "name" in paths
        assert "name.given" in paths
        assert "name.family" in paths

    def test_definitions_ref_resolution(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "definitions": {
                    "Address": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                    }
                },
                "properties": {"addr": {"$ref": "#/definitions/Address"}},
            }
        )
        paths = {f.path for f in schema.fields}
        assert "addr.city" in paths


class TestAllOf:
    def test_allof_single_entry_merged(self, adapter):
        """allOf with a single entry (common for draft-07 descriptions) is merged."""
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "value": {
                        "allOf": [{"type": "string", "description": "A value"}]
                    }
                },
            }
        )
        f = next(f for f in schema.fields if f.path == "value")
        assert f.description == "A value"


class TestTerminologyExtension:
    def test_x_terminology_extracted(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "properties": {
                    "gender": {
                        "type": "string",
                        "x-terminology": {
                            "system": "http://hl7.org/fhir/ValueSet/administrative-gender",
                            "code": "gender",
                            "display": "Administrative Gender",
                        },
                    }
                },
            }
        )
        f = next(f for f in schema.fields if f.path == "gender")
        assert len(f.terminology_references) == 1
        assert f.terminology_references[0].system.startswith("http://hl7.org")


class TestSwedishContent:
    def test_swedish_title_and_description(self, adapter):
        schema = adapter.parse(
            {
                "type": "object",
                "title": "Patientschema",
                "properties": {
                    "fornamn": {
                        "type": "string",
                        "title": "Förnamn",
                        "description": "Patientens förnamn (Å Ä Ö)",
                    }
                },
            },
            schema_name="PatientSchema",
        )
        f = next(f for f in schema.fields if f.path == "fornamn")
        assert f.label == "Förnamn"
        assert "Å Ä Ö" in f.description


class TestStableIds:
    def test_same_path_always_same_id(self, adapter):
        schema1 = adapter.parse(
            {"type": "object", "properties": {"patient_id": {"type": "integer"}}}
        )
        schema2 = adapter.parse(
            {"type": "object", "properties": {"patient_id": {"type": "integer"}}}
        )
        id1 = next(f.id for f in schema1.fields if f.path == "patient_id")
        id2 = next(f.id for f in schema2.fields if f.path == "patient_id")
        assert id1 == id2

    def test_different_paths_different_ids(self):
        id_a = _stable_field_id("Patient.name.given")
        id_b = _stable_field_id("Patient.name.family")
        assert id_a != id_b

    def test_id_length_is_24(self):
        assert len(_stable_field_id("some.path")) == 24


class TestErrorHandling:
    def test_non_dict_raises_parse_error(self, adapter):
        with pytest.raises(AdapterParseError):
            adapter.parse("not a dict")

    def test_non_dict_list_raises_parse_error(self, adapter):
        with pytest.raises(AdapterParseError):
            adapter.parse(["a", "b"])

    def test_empty_properties_yields_no_fields(self, adapter):
        schema = adapter.parse({"type": "object", "properties": {}})
        assert schema.fields == []
