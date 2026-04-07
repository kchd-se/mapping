"""Pydantic request/response DTOs for the v1 API.

These are deliberately thin wrappers around the domain models so that
the API contract is stable even if internal representations evolve.

No domain logic lives here — DTOs validate shape/types only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    sensitivity: Optional[str] = "healthcare_highly_sensitive"


class UpdateProjectStatusRequest(BaseModel):
    status: str = Field(
        ...,
        description="Target status. Allowed: review, approved, published, archived",
    )


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    owner: str
    sensitivity: str
    created_at: str


# ---------------------------------------------------------------------------
# Schema import / selection
# ---------------------------------------------------------------------------


class ImportSourceSchemaRequest(BaseModel):
    format_id: str = Field(
        ...,
        description=(
            "Adapter format identifier. "
            "Examples: 'json_schema', 'csv_schema'. "
            "Open string — no hardcoded list."
        ),
    )
    schema_name: str = Field(..., min_length=1)
    version_label: str = Field(..., min_length=1)
    schema_payload: Any = Field(
        ...,
        description=(
            "Raw schema payload to parse. "
            "Shape depends on format_id: JSON object for json_schema, "
            "CSV string or list-of-dicts for csv_schema."
        ),
    )
    notes: Optional[str] = None


class SelectTargetSchemaRequest(BaseModel):
    schema_id: str = Field(
        ...,
        description="Catalog schema_id of the schema to pin as target.",
    )
    version_label: str = Field(..., min_length=1)


class PinnedSchemaRef(BaseModel):
    pin_id: str
    schema_id: str
    version_label: str
    schema_name: str
    format_id: str
    field_count: int


class ProjectSchemasResponse(BaseModel):
    project_id: str
    source: Optional[PinnedSchemaRef]
    target: Optional[PinnedSchemaRef]


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------


class SuggestionsRequest(BaseModel):
    top_k: int = Field(default=5, ge=1, le=50)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SuggestionCandidateDTO(BaseModel):
    source_field_ids: List[str]
    confidence: float
    reasons: List[str]
    warnings: List[str]


class FieldSuggestionsDTO(BaseModel):
    target_field_id: str
    target_field_path: str
    candidates: List[SuggestionCandidateDTO]


class SuggestionsResponse(BaseModel):
    project_id: str
    source_schema_id: str
    target_schema_id: str
    field_suggestions: List[FieldSuggestionsDTO]


# ---------------------------------------------------------------------------
# Mapping rules
# ---------------------------------------------------------------------------


class TransformHintDTO(BaseModel):
    kind: str = "direct"
    expression: Optional[str] = None


class MappingRuleDTO(BaseModel):
    target_field_id: str
    source_field_ids: List[str] = Field(default_factory=list)
    transform: TransformHintDTO = Field(default_factory=TransformHintDTO)
    default_value: Optional[str] = None
    constant_value: Optional[str] = None
    notes: Optional[str] = None


class CreateMappingVersionRequest(BaseModel):
    version_label: str = Field(..., min_length=1)
    rules: List[MappingRuleDTO]
    notes: Optional[str] = None


class MappingVersionResponse(BaseModel):
    id: str
    project_id: str
    version_label: str
    created_at: str
    rule_count: int
    notes: Optional[str]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class SeverityOverride(BaseModel):
    rule_id: str
    severity: str = Field(..., description="error | warn | info")


class ValidateRequest(BaseModel):
    mapping_version_id: str
    severity_overrides: List[SeverityOverride] = Field(default_factory=list)


class ValidationIssueDTO(BaseModel):
    rule_id: str
    severity: str
    message: str
    affected_field_ids: List[str]
    affected_field_paths: List[str]
    remediation_hint: Optional[str]


class ValidationResponse(BaseModel):
    project_id: str
    mapping_version_id: str
    has_errors: bool
    error_count: int
    warning_count: int
    issues: List[ValidationIssueDTO]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class ExportResponse(BaseModel):
    project_id: str
    mapping_version_id: str
    artifact_json: str = Field(
        ..., description="Deterministic JSON export of the mapping artifact."
    )
    transformation_script: str = Field(
        default="TODO: Phase 6 — script generation not yet implemented.",
        description="Placeholder. Script generation will be implemented in Phase 6.",
    )


# ---------------------------------------------------------------------------
# Catalog browse (Phase 5a extension)
# ---------------------------------------------------------------------------


class CatalogSchemaResponse(BaseModel):
    """Summary descriptor for a catalog entry returned by GET /catalog/schemas."""

    id: str = Field(..., description="Schema identifier in the catalog.")
    name: str
    format_id: str = Field(..., description="Open adapter format identifier.")
    schema_type: str = Field(..., description="'custom' or 'standard'.")
    approval_status: str = Field(..., description="'draft' or 'approved'.")
    owner: str
    description: Optional[str]
    latest_version_label: Optional[str] = Field(
        None, description="Version label of the most recently registered version."
    )
    available_versions_count: int = Field(
        ..., description="Total number of registered versions for this schema."
    )
    created_at: str
    metadata_tags: Dict[str, str] = Field(default_factory=dict)


class CatalogVersionResponse(BaseModel):
    """Version summary returned by GET /catalog/schemas/{id}/versions."""

    id: str = Field(..., description="Version UUID.")
    schema_id: str
    version_label: str
    created_at: str
    checksum: str = Field(
        ...,
        description=(
            "SHA-256 content fingerprint. "
            "Identical schemas always share the same checksum regardless of "
            "when or where they were registered."
        ),
    )
    notes: Optional[str]
