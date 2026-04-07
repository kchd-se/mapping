"""Suggestions router — schema-only TOP-K mapping candidates."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from apps.api.auth import Principal, Role, require_role
from apps.api.deps import catalog_dep, projects_dep
from apps.api.routers.schemas import get_project_pins
from apps.api.schemas import (
    FieldSuggestionsDTO,
    SuggestionCandidateDTO,
    SuggestionsRequest,
    SuggestionsResponse,
)
from packages.catalog.catalog_service import CatalogService, SchemaNotFoundError
from packages.core.models.mapping_project import MappingProject
from packages.suggestions.engine import SuggestionEngine

router = APIRouter(prefix="/projects", tags=["suggestions"])


@router.post("/{project_id}/suggestions", response_model=SuggestionsResponse)
def get_suggestions(
    project_id: str,
    body: SuggestionsRequest,
    principal: Principal = Depends(require_role(Role.ANALYST)),
    projects: Dict[str, MappingProject] = Depends(projects_dep),
    catalog: CatalogService = Depends(catalog_dep),
) -> SuggestionsResponse:
    """Generate TOP-K mapping suggestions for every target field.

    Uses pinned source & target schemas — no raw schema parsing here (RL-05).
    No patient data is accessed (RL-02).
    """
    _require_project(project_id, projects)
    pins = get_project_pins().get(project_id, {})

    if "source" not in pins:
        raise HTTPException(
            status_code=422,
            detail="No source schema pinned for this project. Import one first.",
        )
    if "target" not in pins:
        raise HTTPException(
            status_code=422,
            detail="No target schema pinned for this project. Select one first.",
        )

    try:
        source_schema = catalog.resolve_pin(pins["source"].id)
        target_schema = catalog.resolve_pin(pins["target"].id)
    except SchemaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    engine = SuggestionEngine(top_k=body.top_k, min_confidence=body.min_confidence)
    result = engine.suggest(source_schema, target_schema)

    field_dtos = [
        FieldSuggestionsDTO(
            target_field_id=fs.target_field_id,
            target_field_path=fs.target_field_path,
            candidates=[
                SuggestionCandidateDTO(
                    source_field_ids=c.source_field_ids,
                    confidence=c.confidence,
                    reasons=c.reasons,
                    warnings=c.warnings,
                )
                for c in fs.candidates
            ],
        )
        for fs in result.field_suggestions
    ]

    return SuggestionsResponse(
        project_id=project_id,
        source_schema_id=result.source_schema_id,
        target_schema_id=result.target_schema_id,
        field_suggestions=field_dtos,
    )


def _require_project(
    project_id: str, projects: Dict[str, MappingProject]
) -> MappingProject:
    p = projects.get(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return p
