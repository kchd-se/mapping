"""Tests for the Mapping Rule Model."""

from packages.core.models.mapping_rule import (
    MappingRule,
    TransformHint,
    TransformKind,
)


class TestTransformHint:
    def test_default_is_direct(self):
        th = TransformHint()
        assert th.kind == TransformKind.DIRECT
        assert th.expression is None

    def test_roundtrip_with_expression(self):
        th = TransformHint(kind=TransformKind.CONCATENATE, expression="join(' ')")
        assert TransformHint.from_dict(th.to_dict()) == th

    def test_all_kinds_serializable(self):
        for kind in TransformKind:
            th = TransformHint(kind=kind)
            restored = TransformHint.from_dict(th.to_dict())
            assert restored.kind == kind


class TestMappingRule:
    def test_roundtrip_full(self):
        rule = MappingRule(
            id="rule-001",
            target_field_id="target-f1",
            source_field_ids=["src-f1", "src-f2"],
            transform=TransformHint(
                kind=TransformKind.CONCATENATE, expression="join(', ')"
            ),
            default_value="N/A",
            constant_value=None,
            notes="Combine first and last name",
        )
        restored = MappingRule.from_dict(rule.to_dict())
        assert restored == rule

    def test_roundtrip_minimal(self):
        rule = MappingRule(
            id="rule-002",
            target_field_id="target-f2",
            source_field_ids=["src-f3"],
        )
        restored = MappingRule.from_dict(rule.to_dict())
        assert restored == rule
        assert restored.transform.kind == TransformKind.DIRECT

    def test_constant_value(self):
        rule = MappingRule(
            id="rule-003",
            target_field_id="target-f3",
            source_field_ids=[],
            transform=TransformHint(kind=TransformKind.CONSTANT),
            constant_value="SWEDEN",
        )
        d = rule.to_dict()
        assert d["constant_value"] == "SWEDEN"
        assert "default_value" not in d
        assert MappingRule.from_dict(d) == rule

    def test_optional_fields_omitted_from_dict(self):
        rule = MappingRule(
            id="r", target_field_id="t", source_field_ids=["s"]
        )
        d = rule.to_dict()
        assert "default_value" not in d
        assert "constant_value" not in d
        assert "notes" not in d
