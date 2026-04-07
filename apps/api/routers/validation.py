"""Validation router — policy-configurable mapping quality gate."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from apps.api.auth import Principal, Role, require_role
from apps.api.deps import catalog_dep, mapping_versions_dep, projects_dep
from apps.api.routers.schemas import get_project_pins
from apps.api.schemas import (
    SeverityOverride,
    ValidateRequest,
    ValidationIssueDTO,
    ValidationResponse,
)
from packages.catalog.catalog_service import CatalogService, SchemaNotFoundError
from packages.core.models.mapping_project import MappingProject
from packages.core.models.mapping_version import MappingVersion
from packages.validation.engine import ValidationEngine
from packages.validation.models import Severity
from packages.validation.policy import ValidationPolicy
from packages.validation.rules import default_rules

router = APIRouter(prefix="/projects", tags=["validation"])


def _build_policy(overrides: List[SeverityOverride]) -> ValidationPolicy:
    """Convert API override DTOs to a ValidationPolicy (RL-03: no hardcoded severities)."""
    severity_map: Dict[str, Severity] = {}
    for ov in overrides:
        try:
            sev = Severity(ov.severity.lower())
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown severity '{ov.severity}'. Allowed: error, warn, info.",
            )
        severity_map[ov.rule_id] = sev
    return ValidationPolicy(
        id="request_policy",
        name="Per-request policy",
        severity_overrides=severity_map,
    )


@router.post("/{project_id}/validate", response_model=ValidationResponse)
def validate_mapping(
    project_id: str,
    body: ValidateRequest,
    principal: Principal = Depends(require_role(Role.ANALYST)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    mapping_store: Dict[str, List[MappingVersion]] = Depends(mapping_versions_dep),
    catalog: CatalogService = Depends(catalog_dep),
) -> ValidationResponse:
    """Validate a mapping version against pinned schemas with optional policy overrides."""
    _require_project(project_id, projects)

    # Resolve mapping version
    versions = mapping_store.get(project_id, [])
    mv: MappingVersion | None = next(
        (v for v in versions if v.id == body.mapping_version_id), None
    )
    if mv is None:
        raise HTTPException(
            status_code=404,
            detail=f"Mapping version '{body.mapping_version_id}' not found.",
        )

    # Resolve pinned schemas
    pins = get_project_pins().get(project_id, {})
    if "source" not in pins or "target" not in pins:
        raise HTTPException(
            status_code=422,
            detail="Both source and target schemas must be pinned before validation.",
        )
    try:
        source_schema = catalog.resolve_pin(pins["source"].id)
        target_schema = catalog.resolve_pin(pins["target"].id)
    except SchemaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    policy = _build_policy(body.severity_overrides)
    engine = ValidationEngine(rules=default_rules(), policy=policy)
    result = engine.validate(mv.rules, source_schema, target_schema)

    issue_dtos = [
        ValidationIssueDTO(
            rule_id=i.rule_id,
            severity=i.severity.value,
            message=i.message,
            affected_field_ids=list(i.affected_field_ids),
            affected_field_paths=list(i.affected_field_paths),
            remediation_hint=i.remediation_hint,
        )
        for i in result.issues
    ]

    return ValidationResponse(
        project_id=project_id,
        mapping_version_id=body.mapping_version_id,
        has_errors=result.has_errors,
        error_count=result.error_count,
        warning_count=result.warning_count,
        issues=issue_dtos,
    )


def _require_project(
    project_id: str, projects: Dict[str, MappingProject]
) -> MappingProject:
    p = projects.get(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return p
