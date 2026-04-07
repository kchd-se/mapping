"""Tests for the Mapping Project Model — lifecycle transitions."""

import pytest

from packages.core.models.mapping_project import (
    InvalidStatusTransition,
    MappingProject,
    ProjectStatus,
    SensitivityClassification,
)


class TestProjectStatusLifecycle:
    def test_valid_transitions_draft_to_review(self):
        p = MappingProject(status=ProjectStatus.DRAFT)
        p.transition_to(ProjectStatus.REVIEW)
        assert p.status == ProjectStatus.REVIEW

    def test_valid_transition_review_to_approved(self):
        p = MappingProject(status=ProjectStatus.REVIEW)
        p.transition_to(ProjectStatus.APPROVED)
        assert p.status == ProjectStatus.APPROVED

    def test_valid_transition_review_back_to_draft(self):
        p = MappingProject(status=ProjectStatus.REVIEW)
        p.transition_to(ProjectStatus.DRAFT)
        assert p.status == ProjectStatus.DRAFT

    def test_valid_transition_approved_to_published(self):
        p = MappingProject(status=ProjectStatus.APPROVED)
        p.transition_to(ProjectStatus.PUBLISHED)
        assert p.status == ProjectStatus.PUBLISHED

    def test_valid_transition_approved_back_to_draft(self):
        p = MappingProject(status=ProjectStatus.APPROVED)
        p.transition_to(ProjectStatus.DRAFT)
        assert p.status == ProjectStatus.DRAFT

    def test_valid_transition_published_to_archived(self):
        p = MappingProject(status=ProjectStatus.PUBLISHED)
        p.transition_to(ProjectStatus.ARCHIVED)
        assert p.status == ProjectStatus.ARCHIVED

    def test_invalid_draft_to_approved(self):
        p = MappingProject(status=ProjectStatus.DRAFT)
        with pytest.raises(InvalidStatusTransition):
            p.transition_to(ProjectStatus.APPROVED)

    def test_invalid_draft_to_published(self):
        p = MappingProject(status=ProjectStatus.DRAFT)
        with pytest.raises(InvalidStatusTransition):
            p.transition_to(ProjectStatus.PUBLISHED)

    def test_invalid_archived_to_anything(self):
        p = MappingProject(status=ProjectStatus.ARCHIVED)
        for status in ProjectStatus:
            if status == ProjectStatus.ARCHIVED:
                continue
            with pytest.raises(InvalidStatusTransition):
                p.transition_to(status)

    def test_invalid_published_to_draft(self):
        p = MappingProject(status=ProjectStatus.PUBLISHED)
        with pytest.raises(InvalidStatusTransition):
            p.transition_to(ProjectStatus.DRAFT)

    def test_full_happy_path(self):
        p = MappingProject(status=ProjectStatus.DRAFT)
        p.transition_to(ProjectStatus.REVIEW)
        p.transition_to(ProjectStatus.APPROVED)
        p.transition_to(ProjectStatus.PUBLISHED)
        p.transition_to(ProjectStatus.ARCHIVED)
        assert p.status == ProjectStatus.ARCHIVED

    def test_transition_updates_timestamp(self):
        p = MappingProject(status=ProjectStatus.DRAFT)
        old_ts = p.updated_at
        p.transition_to(ProjectStatus.REVIEW)
        assert p.updated_at >= old_ts


class TestProjectValidTransitions:
    def test_valid_transitions_returns_correct_list(self):
        assert MappingProject.valid_transitions(ProjectStatus.DRAFT) == [
            ProjectStatus.REVIEW
        ]
        assert ProjectStatus.DRAFT in MappingProject.valid_transitions(
            ProjectStatus.REVIEW
        )
        assert MappingProject.valid_transitions(ProjectStatus.ARCHIVED) == []


class TestProjectSerialization:
    def test_roundtrip(self):
        p = MappingProject(
            id="proj-1",
            name="Test Project",
            description="Description",
            owner="user@example.com",
            status=ProjectStatus.REVIEW,
            sensitivity=SensitivityClassification.HEALTHCARE_SENSITIVE,
            source_schema_ids=["s1", "s2"],
            target_schema_id="t1",
            version_ids=["v1"],
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-02T00:00:00+00:00",
        )
        restored = MappingProject.from_dict(p.to_dict())
        assert restored.id == p.id
        assert restored.name == p.name
        assert restored.status == p.status
        assert restored.sensitivity == p.sensitivity
        assert restored.source_schema_ids == p.source_schema_ids
        assert restored.target_schema_id == p.target_schema_id

    def test_default_sensitivity(self):
        p = MappingProject()
        assert p.sensitivity == SensitivityClassification.HEALTHCARE_HIGHLY_SENSITIVE
