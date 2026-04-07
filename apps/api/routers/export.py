"""Export router — mapping artifact export (script generation: Phase 6 placeholder)."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from apps.api.auth import Principal, Role, require_role
from apps.api.deps import audit_dep, mapping_versions_dep, projects_dep
from apps.api.schemas import ExportResponse
from packages.core.models.audit_event import AuditAction, AuditEvent
from packages.core.models.mapping_project import MappingProject
from packages.core.models.mapping_version import MappingVersion
from packages.core.serialization.artifact import MappingArtifact

router = APIRouter(prefix="/projects", tags=["export"])

_SCRIPT_PLACEHOLDER = (
    "# TODO: Phase 6 — transformation script generation not yet implemented.\n"
    "# This file will contain a deterministic transformation script produced\n"
    "# from the mapping rules above once Phase 6 is complete.\n"
)


@router.post("/{project_id}/export", response_model=ExportResponse)
def export_mapping(
    project_id: str,
    mapping_version_id: str,
    principal: Principal = Depends(require_role(Role.ANALYST)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    mapping_store: Dict[str, List[MappingVersion]] = Depends(mapping_versions_dep),
    audit: List = Depends(audit_dep),
) -> ExportResponse:
    """Export a mapping artifact as deterministic JSON.

    Script generation is a Phase 6 concern.  The transformation_script field
    contains a clearly-marked placeholder (RL-10, RL-01).
    """
    project = projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    versions = mapping_store.get(project_id, [])
    mv: MappingVersion | None = next(
        (v for v in versions if v.id == mapping_version_id), None
    )
    if mv is None:
        raise HTTPException(
            status_code=404,
            detail=f"Mapping version '{mapping_version_id}' not found.",
        )

    artifact = MappingArtifact(
        project=project,
        version=mv,
    )
    artifact_json = artifact.serialize()

    audit.append(
        AuditEvent(
            actor=principal.user_id,
            action=AuditAction.EXPORT,
            object_type="mapping_version",
            object_id=mv.id,
            after={
                "project_id": project_id,
                "version_label": mv.version_label,
            },
        )
    )

    return ExportResponse(
        project_id=project_id,
        mapping_version_id=mv.id,
        artifact_json=artifact_json,
        transformation_script=_SCRIPT_PLACEHOLDER,
    )
