"""Unit tests specific to the CSV Schema Input Adapter.

Covers basic types, required/optional columns, constraints, hierarchical
paths via the 'parent' column, Swedish schema content, array type syntax,
alias types, and error cases.
"""

from __future__ import annotations

import pytest

from packages.adapters.base import AdapterParseError
from packages.adapters.input.csv_schema_adapter import CsvSchemaAdapter
from packages.core.models.canonical_schema import FieldTypeCategory


@pytest.fixture
def adapter():
    return CsvSchemaAdapter()


class TestMetadata:
    def test_format_id(self, adapter):
        assert CsvSchemaAdapter.FORMAT_ID in adapter.metadata.supported_formats

    def test_version_present(self, adapter):
        assert adapter.metadata.version


class TestBasicParsing:
    _CSV = (
        "name,type,required,label,description\n"
        "patient_id,integer,true,Patient ID,Primary key\n"
        "given_name,string,true,Given Name,First name of patient\n"
        "family_name,string,false,Family Name,\n"
        "birth_date,date,false,,\n"
        "weight_kg,decimal,false,Weight (kg),\n"
    )

    def test_field_count(self, adapter):
        schema = adapter.parse(self._CSV, schema_name="PatientSchema")
        assert len(schema.fields) == 5

    def test_schema_name(self, adapter):
        schema = adapter.parse(self._CSV, schema_name="PatientSchema", schema_version="2.0")
        assert schema.name == "PatientSchema"
        assert schema.version == "2.0"

    def test_required_field_min_occurs(self, adapter):
        schema = adapter.parse(self._CSV)
        field_map = {f.path: f for f in schema.fields}
        assert field_map["patient_id"].cardinality.min_occurs == 1
        assert field_map["given_name"].cardinality.min_occurs == 1
        assert field_map["family_name"].cardinality.min_occurs == 0

    def test_field_types(self, adapter):
        schema = adapter.parse(self._CSV)
        field_map = {f.path: f for f in schema.fields}
        assert field_map["patient_id"].field_type.primitive == "integer"
        assert field_map["given_name"].field_type.primitive == "string"
        assert field_map["birth_date"].field_type.primitive == "date"
        assert field_map["weight_kg"].field_type.primitive == "decimal"

    def test_label_falls_back_to_name(self, adapter):
        schema = adapter.parse(self._CSV)
        field_map = {f.path: f for f in schema.fields}
        # birth_date has no label column value -> falls back to field name
        assert field_map["birth_date"].label == "birth_date"

    def test_description_populated(self, adapter):
        schema = adapter.parse(self._CSV)
        field_map = {f.path: f for f in schema.fields}
        assert field_map["patient_id"].description == "Primary key"
        assert field_map["family_name"].description is None


class TestConstraints:
    def test_enum_pipe_separated(self, adapter):
        csv = "name,type,required,enum\ngender,string,false,Male|Female|Unknown\n"
        schema = adapter.parse(csv)
        f = schema.fields[0]
        assert f.constraints.enums == ["Male", "Female", "Unknown"]

    def test_pattern_constraint(self, adapter):
        csv = "name,type,required,pattern\npnr,string,true,^\\d{6}-\\d{4}$\n"
        schema = adapter.parse(csv)
        f = schema.fields[0]
        assert f.constraints.pattern == r"^\d{6}-\d{4}$"

    def test_min_max_length(self, adapter):
        csv = "name,type,required,min_length,max_length\ncode,string,true,2,10\n"
        schema = adapter.parse(csv)
        f = schema.fields[0]
        assert f.constraints.min_length == 2
        assert f.constraints.max_length == 10

    def test_min_max_value(self, adapter):
        csv = "name,type,required,min_value,max_value\nage,integer,false,0,150\n"
        schema = adapter.parse(csv)
        f = schema.fields[0]
        assert f.constraints.min_value == 0.0
        assert f.constraints.max_value == 150.0

    def test_required_sets_constraint_flag(self, adapter):
        csv = "name,type,required\nreq_field,string,true\nopt_field,string,false\n"
        schema = adapter.parse(csv)
        field_map = {f.path: f for f in schema.fields}
        assert field_map["req_field"].constraints.required is True
        assert field_map["opt_field"].constraints.required is False


class TestTypeAliases:
    @pytest.mark.parametrize("alias,expected", [
        ("int", "integer"),
        ("float", "decimal"),
        ("number", "decimal"),
        ("bool", "boolean"),
        ("varchar", "string"),
        ("text", "string"),
        ("nvarchar", "string"),
        ("timestamp", "datetime"),
    ])
    def test_alias_mapping(self, adapter, alias, expected):
        csv = f"name,type\nfield,{alias}\n"
        schema = adapter.parse(csv)
        assert schema.fields[0].field_type.primitive == expected


class TestArrayType:
    def test_array_type(self, adapter):
        csv = "name,type\ntags,array\n"
        schema = adapter.parse(csv)
        f = schema.fields[0]
        assert f.field_type.category == FieldTypeCategory.ARRAY

    def test_array_with_item_type(self, adapter):
        csv = "name,type\ncodes,array<integer>\n"
        schema = adapter.parse(csv)
        f = schema.fields[0]
        assert f.field_type.category == FieldTypeCategory.ARRAY
        assert f.field_type.items_type.primitive == "integer"

    def test_array_cardinality_unbounded(self, adapter):
        csv = "name,type,required\nitems,array,false\n"
        schema = adapter.parse(csv)
        f = schema.fields[0]
        assert f.cardinality.max_occurs is None


class TestHierarchicalPaths:
    def test_parent_column_builds_path(self, adapter):
        csv = (
            "name,type,parent\n"
            "given,string,name\n"
            "family,string,name\n"
            "street,string,address\n"
        )
        schema = adapter.parse(csv)
        paths = {f.path for f in schema.fields}
        assert "name.given" in paths
        assert "name.family" in paths
        assert "address.street" in paths

    def test_no_parent_gives_flat_path(self, adapter):
        csv = "name,type\npatient_id,integer\n"
        schema = adapter.parse(csv)
        assert schema.fields[0].path == "patient_id"


class TestTerminologyColumns:
    def test_terminology_system_and_code(self, adapter):
        csv = (
            "name,type,terminology_system,terminology_code\n"
            "gender,string,http://example.org/gender-vs,GENDER\n"
        )
        schema = adapter.parse(csv)
        f = schema.fields[0]
        assert len(f.terminology_references) == 1
        assert f.terminology_references[0].system == "http://example.org/gender-vs"
        assert f.terminology_references[0].code == "GENDER"

    def test_no_terminology_columns_ok(self, adapter):
        csv = "name,type\nfield,string\n"
        schema = adapter.parse(csv)
        assert schema.fields[0].terminology_references == []


class TestSwedishContent:
    def test_swedish_field_names_and_labels(self, adapter):
        csv = "name,type,label,description\nförnamn,string,Förnamn,Patientens förnamn\n"
        schema = adapter.parse(csv, schema_name="Patientschema")
        assert schema.name == "Patientschema"
        f = schema.fields[0]
        assert f.path == "förnamn"
        assert f.label == "Förnamn"
        assert "förnamn" in f.description

    def test_swedisg_enum_values(self, adapter):
        csv = "name,type,enum\nkön,string,Man|Kvinna|Okänt\n"
        schema = adapter.parse(csv)
        assert schema.fields[0].constraints.enums == ["Man", "Kvinna", "Okänt"]


class TestListOfDictsInput:
    def test_accepts_list_of_dicts(self, adapter):
        rows = [
            {"name": "id", "type": "integer", "required": "true"},
            {"name": "name", "type": "string", "required": "false"},
        ]
        schema = adapter.parse(rows, schema_name="DictInput")
        assert len(schema.fields) == 2
        assert schema.fields[0].path == "id"

    def test_empty_list_raises(self, adapter):
        with pytest.raises(AdapterParseError):
            adapter.parse([])


class TestErrorHandling:
    def test_missing_name_column_raises(self, adapter):
        csv = "type,required\nstring,true\n"
        with pytest.raises(AdapterParseError, match="name"):
            adapter.parse(csv)

    def test_duplicate_path_raises(self, adapter):
        csv = "name,type\nfield_a,string\nfield_a,integer\n"
        with pytest.raises(AdapterParseError, match="Duplicate"):
            adapter.parse(csv)

    def test_invalid_type_raises_parse_error(self, adapter):
        with pytest.raises(AdapterParseError):
            adapter.parse({"not": "a string or list"})

    def test_empty_string_raises(self, adapter):
        with pytest.raises(AdapterParseError, match="no data rows"):
            adapter.parse("")

    def test_header_only_raises(self, adapter):
        with pytest.raises(AdapterParseError, match="no data rows"):
            adapter.parse("name,type,required\n")

    def test_blank_name_rows_are_skipped(self, adapter):
        csv = "name,type\nvalid,string\n,integer\n\n"
        schema = adapter.parse(csv)
        assert len(schema.fields) == 1
        assert schema.fields[0].path == "valid"


class TestStableIds:
    def test_same_path_same_id_across_parses(self, adapter):
        csv = "name,type\npatient_id,integer\n"
        schema1 = adapter.parse(csv)
        schema2 = adapter.parse(csv)
        assert schema1.fields[0].id == schema2.fields[0].id

    def test_csv_and_json_produce_same_id_for_same_path(self):
        """JSON Schema and CSV adapters share the same _stable_field_id function."""
        from packages.adapters.input.csv_schema_adapter import _stable_field_id as csv_id
        from packages.adapters.input.json_schema_adapter import _stable_field_id as json_id
        assert csv_id("patient.name") == json_id("patient.name")
