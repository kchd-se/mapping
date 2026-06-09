"""Export router — mapping artifact export with deterministic script generation."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from apps.api.auth import Principal, Role, require_role
from apps.api.deps import audit_dep, catalog_dep, mapping_versions_dep, projects_dep
from apps.api.routers.schemas import get_project_pins
from apps.api.schemas import ExportResponse
from packages.catalog.catalog_service import CatalogService, SchemaNotFoundError
from packages.core.models.audit_event import AuditAction, AuditEvent
from packages.core.models.mapping_project import MappingProject
from packages.core.models.mapping_version import MappingVersion
from packages.core.serialization.artifact import MappingArtifact
from packages.script_gen import registry as script_registry

router = APIRouter(prefix="/projects", tags=["export"])

_NO_SCHEMAS_FALLBACK = (
    "-- Script generation skipped: source or target schema not pinned for this project.\n"
    "-- Pin schemas via /projects/{project_id}/schemas/* endpoints first.\n"
)


@router.post("/{project_id}/export", response_model=ExportResponse)
def export_mapping(
    project_id: str,
    mapping_version_id: str,
    principal: Principal = Depends(require_role(Role.ANALYST)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    mapping_store: Dict[str, List[MappingVersion]] = Depends(mapping_versions_dep),
    catalog: CatalogService = Depends(catalog_dep),
    audit: List = Depends(audit_dep),
) -> ExportResponse:
    """Export a mapping artifact as deterministic JSON + SQL transformation script."""
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

    # --- Phase 6: script generation ---
    transformation_script = _NO_SCHEMAS_FALLBACK
    pins = get_project_pins().get(project_id, {})
    if "source" in pins and "target" in pins:
        try:
            source_schema = catalog.resolve_pin(pins["source"].id)
            target_schema = catalog.resolve_pin(pins["target"].id)
            generator = script_registry.get_default()
            result = generator.generate(artifact, source_schema, target_schema)
            transformation_script = result.script_text
        except SchemaNotFoundError as exc:
            transformation_script = f"-- Script generation error: {exc}\n"

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
        transformation_script=transformation_script,
    )
