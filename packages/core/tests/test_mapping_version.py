"""Tests for the Mapping Version Model."""

from packages.core.models.mapping_rule import MappingRule, TransformHint, TransformKind
from packages.core.models.mapping_version import MappingVersion, SchemaReference


class TestSchemaReference:
    def test_roundtrip(self):
        ref = SchemaReference(
            schema_id="s1", schema_name="Source", schema_version="2.0"
        )
        assert SchemaReference.from_dict(ref.to_dict()) == ref

    def test_minimal(self):
        ref = SchemaReference(schema_id="s2")
        assert SchemaReference.from_dict(ref.to_dict()) == ref


class TestMappingVersion:
    def _make_version(self):
        return MappingVersion(
            id="ver-1",
            project_id="proj-1",
            version_label="1.0.0",
            created_at="2026-03-01T00:00:00+00:00",
            source_schema_refs=[
                SchemaReference(schema_id="s1", schema_name="SrcA", schema_version="1.0"),
            ],
            target_schema_ref=SchemaReference(
                schema_id="t1", schema_name="TargetX", schema_version="3.0"
            ),
            rules=[
                MappingRule(
                    id="r1",
                    target_field_id="tf1",
                    source_field_ids=["sf1"],
                    transform=TransformHint(kind=TransformKind.DIRECT),
                ),
                MappingRule(
                    id="r2",
                    target_field_id="tf2",
                    source_field_ids=["sf2", "sf3"],
                    transform=TransformHint(kind=TransformKind.CONCATENATE, expression="join(' ')"),
                    notes="Combine fields",
                ),
            ],
            notes="Initial version",
        )

    def test_roundtrip(self):
        v = self._make_version()
        restored = MappingVersion.from_dict(v.to_dict())
        assert restored.id == v.id
        assert restored.project_id == v.project_id
        assert restored.version_label == v.version_label
        assert len(restored.rules) == 2
        assert restored.rules[0] == v.rules[0]
        assert restored.rules[1] == v.rules[1]
        assert restored.target_schema_ref == v.target_schema_ref
        assert restored.source_schema_refs == v.source_schema_refs
        assert restored.notes == v.notes

    def test_no_target_schema(self):
        v = MappingVersion(
            id="ver-2",
            project_id="proj-2",
            created_at="2026-03-01T00:00:00+00:00",
        )
        restored = MappingVersion.from_dict(v.to_dict())
        assert restored.target_schema_ref is None
        assert restored.rules == []
