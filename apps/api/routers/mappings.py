"""Mappings router — create, list, retrieve mapping versions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.auth import Principal, Role, require_role
from apps.api.deps import audit_dep, mapping_versions_dep, projects_dep
from apps.api.schemas import (
    CreateMappingVersionRequest,
    UpdateMappingVersionRequest,
    MappingVersionResponse,
    MappingRuleDTO,
    TransformHintDTO,
)
from packages.core.models.audit_event import AuditAction, AuditEvent
from packages.core.models.mapping_project import MappingProject
from packages.core.models.mapping_rule import MappingRule, TransformHint, TransformKind
from packages.core.models.mapping_version import MappingVersion

router = APIRouter(prefix="/projects", tags=["mappings"])


def _dto_to_rule(dto: MappingRuleDTO) -> MappingRule:
    try:
        kind = TransformKind(dto.transform.kind.lower())
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown transform kind '{dto.transform.kind}'.",
        )
    return MappingRule(
        id=str(uuid.uuid4()),
        target_field_id=dto.target_field_id,
        source_field_ids=list(dto.source_field_ids),
        transform=TransformHint(kind=kind, expression=dto.transform.expression),
        default_value=dto.default_value,
        constant_value=dto.constant_value,
        notes=dto.notes,
    )


def _version_to_response(v: MappingVersion) -> MappingVersionResponse:
    return MappingVersionResponse(
        id=v.id,
        project_id=v.project_id,
        version_label=v.version_label,
        created_at=v.created_at,
        rule_count=len(v.rules),
        notes=v.notes,
        rules=[
            MappingRuleDTO(
                target_field_id=r.target_field_id,
                source_field_ids=list(r.source_field_ids),
                transform=TransformHintDTO(
                    kind=r.transform.kind.value,
                    expression=r.transform.expression,
                ),
                default_value=r.default_value,
                constant_value=r.constant_value,
                notes=r.notes,
            )
            for r in v.rules
        ],
    )


@router.post(
    "/{project_id}/mappings",
    status_code=status.HTTP_201_CREATED,
    response_model=MappingVersionResponse,
)
def create_mapping_version(
    project_id: str,
    body: CreateMappingVersionRequest,
    principal: Principal = Depends(require_role(Role.ANALYST)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    mapping_store: Dict[str, List[MappingVersion]] = Depends(mapping_versions_dep),
    audit: List = Depends(audit_dep),
) -> MappingVersionResponse:
    _require_project(project_id, projects)

    rules = [_dto_to_rule(r) for r in body.rules]

    version = MappingVersion(
        id=str(uuid.uuid4()),
        project_id=project_id,
        version_label=body.version_label,
        created_at=datetime.now(timezone.utc).isoformat(),
        rules=rules,
        notes=body.notes,
    )

    versions = mapping_store.setdefault(project_id, [])
    # Guard: version label must be unique within a project
    if any(v.version_label == body.version_label for v in versions):
        raise HTTPException(
            status_code=409,
            detail=f"Mapping version '{body.version_label}' already exists for this project.",
        )

    versions.append(version)

    audit.append(
        AuditEvent(
            actor=principal.user_id,
            action=AuditAction.MAPPING_EDIT,
            object_type="mapping_version",
            object_id=version.id,
            after={
                "project_id": project_id,
                "version_label": body.version_label,
                "rule_count": len(rules),
            },
        )
    )

    return _version_to_response(version)


@router.get("/{project_id}/mappings", response_model=List[MappingVersionResponse])
def list_mapping_versions(
    project_id: str,
    principal: Principal = Depends(require_role(Role.VIEWER)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    mapping_store: Dict[str, List[MappingVersion]] = Depends(mapping_versions_dep),
) -> List[MappingVersionResponse]:
    _require_project(project_id, projects)
    versions = mapping_store.get(project_id, [])
    return [_version_to_response(v) for v in versions]


@router.get(
    "/{project_id}/mappings/{version_id}",
    response_model=MappingVersionResponse,
)
def get_mapping_version(
    project_id: str,
    version_id: str,
    principal: Principal = Depends(require_role(Role.VIEWER)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    mapping_store: Dict[str, List[MappingVersion]] = Depends(mapping_versions_dep),
) -> MappingVersionResponse:
    _require_project(project_id, projects)
    versions = mapping_store.get(project_id, [])
    for v in versions:
        if v.id == version_id:
            return _version_to_response(v)
    raise HTTPException(
        status_code=404,
        detail=f"Mapping version '{version_id}' not found in project '{project_id}'.",
    )


@router.put(
    "/{project_id}/mappings/{version_id}",
    response_model=MappingVersionResponse,
)
def update_mapping_version(
    project_id: str,
    version_id: str,
    body: UpdateMappingVersionRequest,
    principal: Principal = Depends(require_role(Role.ANALYST)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    mapping_store: Dict[str, List[MappingVersion]] = Depends(mapping_versions_dep),
    audit: List = Depends(audit_dep),
) -> MappingVersionResponse:
    """Replace the rules (and optionally notes) of an existing mapping version in-place."""
    _require_project(project_id, projects)
    versions = mapping_store.get(project_id, [])
    for i, v in enumerate(versions):
        if v.id == version_id:
            new_rules = [_dto_to_rule(r) for r in body.rules]
            updated = MappingVersion(
                id=v.id,
                project_id=v.project_id,
                version_label=v.version_label,
                created_at=v.created_at,
                rules=new_rules,
                notes=body.notes if body.notes is not None else v.notes,
            )
            versions[i] = updated

            audit.append(
                AuditEvent(
                    actor=principal.user_id,
                    action=AuditAction.MAPPING_EDIT,
                    object_type="mapping_version",
                    object_id=version_id,
                    after={
                        "project_id": project_id,
                        "version_label": v.version_label,
                        "rule_count": len(new_rules),
                    },
                )
            )

            return _version_to_response(updated)

    raise HTTPException(
        status_code=404,
        detail=f"Mapping version '{version_id}' not found in project '{project_id}'.",
    )


# ---------------------------------------------------------------------------
# Internal accessor used by validation + export routers
# ---------------------------------------------------------------------------

def _require_project(
    project_id: str, projects: Dict[str, MappingProject]
) -> MappingProject:
    p = projects.get(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return p
