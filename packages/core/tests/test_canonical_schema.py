"""Tests for the Canonical Schema Model."""

import pytest

from packages.core.models.canonical_schema import (
    CanonicalField,
    CanonicalSchema,
    Cardinality,
    FieldConstraints,
    FieldType,
    FieldTypeCategory,
    TerminologyReference,
)


def _make_field(**overrides):
    defaults = dict(
        id="field-001",
        path="Patient.name.given",
        field_type=FieldType(
            category=FieldTypeCategory.PRIMITIVE, primitive="string"
        ),
        cardinality=Cardinality(min_occurs=1, max_occurs=None),
        label="Given name",
        description="Patient's given (first) name",
        constraints=FieldConstraints(required=True, max_length=200),
        terminology_references=[
            TerminologyReference(
                system="http://example.org/codesystem",
                code="given",
                display="Given Name",
            )
        ],
        metadata_tags={"domain": "demographics", "sensitivity": "high"},
    )
    defaults.update(overrides)
    return CanonicalField(**defaults)


class TestFieldType:
    def test_primitive_roundtrip(self):
        ft = FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="integer")
        assert ft == FieldType.from_dict(ft.to_dict())

    def test_array_with_nested_type(self):
        inner = FieldType(category=FieldTypeCategory.PRIMITIVE, primitive="string")
        ft = FieldType(category=FieldTypeCategory.ARRAY, items_type=inner)
        restored = FieldType.from_dict(ft.to_dict())
        assert restored == ft
        assert restored.items_type.primitive == "string"

    def test_object_type(self):
        ft = FieldType(category=FieldTypeCategory.OBJECT)
        d = ft.to_dict()
        assert d == {"category": "object"}
        assert FieldType.from_dict(d) == ft


class TestCardinality:
    def test_unbounded(self):
        c = Cardinality(min_occurs=0, max_occurs=None)
        assert c.to_dict() == {"min_occurs": 0, "max_occurs": None}
        assert Cardinality.from_dict(c.to_dict()) == c

    def test_bounded(self):
        c = Cardinality(min_occurs=1, max_occurs=5)
        assert Cardinality.from_dict(c.to_dict()) == c


class TestFieldConstraints:
    def test_all_fields(self):
        fc = FieldConstraints(
            required=True,
            enums=["A", "B"],
            pattern="^[A-Z]+$",
            min_value=0,
            max_value=100,
            min_length=1,
            max_length=50,
        )
        assert FieldConstraints.from_dict(fc.to_dict()) == fc

    def test_minimal(self):
        fc = FieldConstraints()
        assert fc.required is False
        assert FieldConstraints.from_dict(fc.to_dict()) == fc


class TestTerminologyReference:
    def test_roundtrip(self):
        tr = TerminologyReference(system="sys", code="c", display="d")
        assert TerminologyReference.from_dict(tr.to_dict()) == tr

    def test_minimal(self):
        tr = TerminologyReference(system="sys")
        d = tr.to_dict()
        assert "code" not in d
        assert TerminologyReference.from_dict(d) == tr


class TestCanonicalField:
    def test_full_roundtrip(self):
        f = _make_field()
        assert CanonicalField.from_dict(f.to_dict()) == f

    def test_metadata_tags_sorted_in_dict(self):
        f = _make_field(metadata_tags={"z": "1", "a": "2"})
        keys = list(f.to_dict()["metadata_tags"].keys())
        assert keys == ["a", "z"]

    def test_swedish_characters_in_label(self):
        f = _make_field(label="Förnamn", description="Patientens förnamn (Å Ä Ö)")
        restored = CanonicalField.from_dict(f.to_dict())
        assert restored.label == "Förnamn"
        assert "Å Ä Ö" in restored.description


class TestCanonicalSchema:
    def test_roundtrip(self):
        schema = CanonicalSchema(
            id="schema-1",
            name="TestSchema",
            version="1.0",
            description="A test schema",
            fields=[_make_field()],
            metadata_tags={"source": "test"},
            created_at="2026-01-01T00:00:00+00:00",
        )
        restored = CanonicalSchema.from_dict(schema.to_dict())
        assert restored.id == schema.id
        assert restored.name == schema.name
        assert restored.version == schema.version
        assert len(restored.fields) == 1
        assert restored.fields[0] == schema.fields[0]

    def test_empty_fields(self):
        schema = CanonicalSchema(
            id="s", name="n", version="v",
            created_at="2026-01-01T00:00:00+00:00",
        )
        restored = CanonicalSchema.from_dict(schema.to_dict())
        assert restored.fields == []
