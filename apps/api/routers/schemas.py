"""Schemas router — source import, target selection, pin retrieval."""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.auth import Principal, Role, require_role
from apps.api.deps import audit_dep, catalog_dep, projects_dep
from apps.api.schemas import (
    ImportSourceSchemaRequest,
    PinnedSchemaRef,
    ProjectSchemasResponse,
    SelectTargetSchemaRequest,
)
from packages.adapters.base import AdapterNotFoundError, AdapterParseError
from packages.catalog.catalog_service import (
    CatalogService,
    SchemaNotFoundError,
    SchemaVersionConflictError,
)
from packages.catalog.models.version_pin import VersionPin
from packages.core.models.audit_event import AuditAction, AuditEvent
from packages.core.models.mapping_project import MappingProject

router = APIRouter(prefix="/projects", tags=["schemas"])

# ---------------------------------------------------------------------------
# Per-project pin store: project_id → {role: VersionPin}
# We store these in the catalog (which already has a pin store) but we also
# keep a project-scoped index for fast lookup.
# ---------------------------------------------------------------------------

# Module-level dict used as a simple store (reset by tests via state.reset_state)
_project_pins: Dict[str, Dict[str, VersionPin]] = {}  # project_id → {role → pin}


def _get_pins(project_id: str) -> Dict[str, VersionPin]:
    return _project_pins.setdefault(project_id, {})


def _pin_to_ref(
    pin: VersionPin, catalog: CatalogService
) -> PinnedSchemaRef:
    entry = catalog.get_entry(pin.schema_id)
    version = catalog.get_schema_version(pin.schema_id, pin.version_label)
    canonical = version.resolve_canonical()
    return PinnedSchemaRef(
        pin_id=pin.id,
        schema_id=pin.schema_id,
        version_label=pin.version_label,
        schema_name=entry.descriptor.name,
        format_id=entry.descriptor.format_id,
        field_count=len(canonical.fields),
    )


@router.post(
    "/{project_id}/schemas/source/import",
    status_code=status.HTTP_201_CREATED,
    response_model=PinnedSchemaRef,
)
def import_source_schema(
    project_id: str,
    body: ImportSourceSchemaRequest,
    principal: Principal = Depends(require_role(Role.ANALYST)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    catalog: CatalogService = Depends(catalog_dep),
    audit: List = Depends(audit_dep),
) -> PinnedSchemaRef:
    """Import a source schema via the adapter registry, register in catalog, pin to project."""
    _require_project(project_id, projects)

    try:
        schema_version = catalog.register_custom_schema(
            raw_input=body.schema_payload,
            format_id=body.format_id,
            schema_name=body.schema_name,
            version_label=body.version_label,
            owner=principal.user_id,
            notes=body.notes,
        )
    except AdapterNotFoundError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown format_id '{body.format_id}': {exc}")
    except AdapterParseError as exc:
        raise HTTPException(status_code=422, detail=f"Schema parse error: {exc}")
    except SchemaVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown format_id '{body.format_id}': {exc}",
        )

    pin = catalog.pin_version(
        project_id=project_id,
        schema_role="source",
        schema_id=schema_version.schema_id,
        version_label=body.version_label,
        actor=principal.user_id,
    )
    # Only set source pin if not already assigned (preserves existing pin when
    # this endpoint is used solely to register a schema in the catalog).
    pins = _get_pins(project_id)
    if "source" not in pins:
        pins["source"] = pin

    audit.append(
        AuditEvent(
            actor=principal.user_id,
            action=AuditAction.SCHEMA_IMPORT,
            object_type="schema_version",
            object_id=schema_version.id,
            after={
                "project_id": project_id,
                "schema_name": body.schema_name,
                "format_id": body.format_id,
                "version_label": body.version_label,
                "pin_id": pin.id,
            },
        )
    )

    return _pin_to_ref(pin, catalog)


@router.post(
    "/{project_id}/schemas/target/select",
    status_code=status.HTTP_201_CREATED,
    response_model=PinnedSchemaRef,
)
def select_target_schema(
    project_id: str,
    body: SelectTargetSchemaRequest,
    principal: Principal = Depends(require_role(Role.ANALYST)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    catalog: CatalogService = Depends(catalog_dep),
    audit: List = Depends(audit_dep),
) -> PinnedSchemaRef:
    """Pin an already-registered catalog schema as the target for this project."""
    _require_project(project_id, projects)

    try:
        pin = catalog.pin_version(
            project_id=project_id,
            schema_role="target",
            schema_id=body.schema_id,
            version_label=body.version_label,
            actor=principal.user_id,
        )
    except SchemaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    _get_pins(project_id)["target"] = pin

    audit.append(
        AuditEvent(
            actor=principal.user_id,
            action=AuditAction.SCHEMA_IMPORT,
            object_type="version_pin",
            object_id=pin.id,
            after={
                "project_id": project_id,
                "schema_id": body.schema_id,
                "version_label": body.version_label,
                "role": "target",
            },
        )
    )

    return _pin_to_ref(pin, catalog)


@router.get("/{project_id}/schemas", response_model=ProjectSchemasResponse)
def get_project_schemas(
    project_id: str,
    principal: Principal = Depends(require_role(Role.VIEWER)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    catalog: CatalogService = Depends(catalog_dep),
) -> ProjectSchemasResponse:
    """Return pinned source and target schema references for a project."""
    _require_project(project_id, projects)
    pins = _get_pins(project_id)

    source_ref: Optional[PinnedSchemaRef] = None
    target_ref: Optional[PinnedSchemaRef] = None

    if "source" in pins:
        source_ref = _pin_to_ref(pins["source"], catalog)
    if "target" in pins:
        target_ref = _pin_to_ref(pins["target"], catalog)

    return ProjectSchemasResponse(
        project_id=project_id,
        source=source_ref,
        target=target_ref,
    )


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _require_project(
    project_id: str, projects: Dict[str, MappingProject]
) -> MappingProject:
    p = projects.get(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return p


def get_project_pins() -> Dict[str, Dict[str, VersionPin]]:
    """Expose pin store so other routers can access source/target pins."""
    return _project_pins


def reset_pins() -> None:
    """Called by tests to clear pin state."""
    _project_pins.clear()
