"""Catalog browse router.

Exposes read-only views of schemas already registered in the internal catalog
(Phase 3).  No network calls to external registries are made.

Endpoints:
  GET /catalog/schemas              — list with optional filtering + search
  GET /catalog/schemas/{schema_id}/versions — versions for one schema
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.api.auth import Principal, Role, require_role
from apps.api.deps import catalog_dep
from apps.api.schemas import CatalogSchemaResponse, CatalogVersionResponse
from packages.catalog.catalog_service import CatalogService, SchemaNotFoundError
from packages.catalog.models.schema_descriptor import ApprovalStatus, SchemaType

router = APIRouter(prefix="/catalog", tags=["catalog"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry_to_response(entry) -> CatalogSchemaResponse:
    d = entry.descriptor
    latest = entry.get_latest_version()
    return CatalogSchemaResponse(
        id=d.id,
        name=d.name,
        format_id=d.format_id,
        schema_type=d.schema_type.value,
        approval_status=d.approval_status.value,
        owner=d.owner,
        description=d.description,
        latest_version_label=latest.version_label if latest else None,
        available_versions_count=len(entry.versions),
        created_at=d.created_at,
        metadata_tags=dict(d.metadata_tags),
    )


# ---------------------------------------------------------------------------
# GET /catalog/schemas
# ---------------------------------------------------------------------------

@router.get(
    "/schemas",
    response_model=List[CatalogSchemaResponse],
    summary="List Catalog Schemas",
    description=(
        "Return all schemas registered in the internal catalog. "
        "Supports optional filtering by schema type, format ID, approval status, "
        "and a case-insensitive substring search on schema name. "
        "Results are ordered deterministically: approved before draft, "
        "then alphabetically by name, then by created_at ascending."
    ),
)
def list_catalog_schemas(
    schema_type: Optional[str] = Query(
        None,
        alias="type",
        description="Filter by schema type: 'custom' or 'standard'.",
    ),
    format_id: Optional[str] = Query(
        None,
        alias="format",
        description="Filter by adapter format identifier (e.g. 'json_schema').",
    ),
    q: Optional[str] = Query(
        None,
        description="Case-insensitive substring search on schema name.",
    ),
    approval_status: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by approval status: 'draft' or 'approved'.",
    ),
    principal: Principal = Depends(require_role(Role.VIEWER)),
    catalog: CatalogService = Depends(catalog_dep),
) -> List[CatalogSchemaResponse]:
    # Validate enum query params early so we return 422, not 500.
    resolved_type: Optional[SchemaType] = None
    if schema_type is not None:
        try:
            resolved_type = SchemaType(schema_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown schema type '{schema_type}'. Allowed: custom, standard.",
            )

    resolved_status: Optional[ApprovalStatus] = None
    if approval_status is not None:
        try:
            resolved_status = ApprovalStatus(approval_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown approval status '{approval_status}'. Allowed: draft, approved.",
            )

    entries = catalog.list_entries(
        schema_type=resolved_type,
        format_id=format_id,
        approval_status=resolved_status,
    )

    # Optional name-substring filter (not in CatalogService.list_entries)
    if q:
        q_lower = q.lower()
        entries = [e for e in entries if q_lower in e.descriptor.name.lower()]

    # Deterministic ordering: approved before draft, then name asc, then
    # created_at asc (stable total order regardless of insertion sequence).
    def _sort_key(entry):
        status_order = 0 if entry.descriptor.approval_status == ApprovalStatus.APPROVED else 1
        return (status_order, entry.descriptor.name.lower(), entry.descriptor.created_at)

    entries.sort(key=_sort_key)

    return [_entry_to_response(e) for e in entries]


# ---------------------------------------------------------------------------
# GET /catalog/schemas/{schema_id}/versions
# ---------------------------------------------------------------------------

@router.get(
    "/schemas/{schema_id}/versions",
    response_model=List[CatalogVersionResponse],
    summary="List Schema Versions",
    description=(
        "Return all registered versions for a catalog schema. "
        "Results are ordered by registration sequence (oldest first)."
    ),
)
def list_schema_versions(
    schema_id: str,
    principal: Principal = Depends(require_role(Role.VIEWER)),
    catalog: CatalogService = Depends(catalog_dep),
) -> List[CatalogVersionResponse]:
    try:
        entry = catalog.get_entry(schema_id)
    except SchemaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return [
        CatalogVersionResponse(
            id=v.id,
            schema_id=v.schema_id,
            version_label=v.version_label,
            created_at=v.created_at,
            checksum=v.checksum,
            notes=v.notes,
        )
        for v in entry.versions  # already in insertion (chronological) order
    ]
