"""Projects router — CRUD + status lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.auth import Principal, Role, require_role
from apps.api.deps import audit_dep, projects_dep
from apps.api.schemas import CreateProjectRequest, ProjectResponse, UpdateProjectStatusRequest
from packages.core.models.audit_event import AuditAction, AuditEvent
from packages.core.models.mapping_project import (
    InvalidStatusTransition,
    MappingProject,
    ProjectStatus,
    SensitivityClassification,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_response(p: MappingProject) -> ProjectResponse:
    return ProjectResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        status=p.status.value,
        owner=p.owner,
        sensitivity=p.sensitivity.value,
        created_at=p.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
def create_project(
    body: CreateProjectRequest,
    principal: Principal = Depends(require_role(Role.ANALYST)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    audit: List = Depends(audit_dep),
) -> ProjectResponse:
    try:
        sensitivity = SensitivityClassification(
            body.sensitivity or "healthcare_highly_sensitive"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown sensitivity '{body.sensitivity}'.",
        )

    project = MappingProject(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        owner=principal.user_id,
        sensitivity=sensitivity,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    projects[project.id] = project

    audit.append(
        AuditEvent(
            actor=principal.user_id,
            action=AuditAction.PROJECT_CREATE,
            object_type="project",
            object_id=project.id,
            after={"name": project.name, "status": project.status.value},
        )
    )

    return _to_response(project)


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    principal: Principal = Depends(require_role(Role.VIEWER)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
) -> List[ProjectResponse]:
    return [_to_response(p) for p in sorted(projects.values(), key=lambda p: p.created_at)]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    principal: Principal = Depends(require_role(Role.VIEWER)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
) -> ProjectResponse:
    p = projects.get(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return _to_response(p)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project_status(
    project_id: str,
    body: UpdateProjectStatusRequest,
    principal: Principal = Depends(require_role(Role.ANALYST)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    audit: List = Depends(audit_dep),
) -> ProjectResponse:
    p = projects.get(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    try:
        new_status = ProjectStatus(body.status.lower())
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown status '{body.status}'.",
        )

    before_status = p.status.value
    try:
        p.transition_to(new_status)
    except InvalidStatusTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    audit.append(
        AuditEvent(
            actor=principal.user_id,
            action=AuditAction.PROJECT_STATUS_CHANGE,
            object_type="project",
            object_id=project_id,
            before={"status": before_status},
            after={"status": new_status.value},
        )
    )

    return _to_response(p)
