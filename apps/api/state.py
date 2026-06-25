"""In-memory application state for the v1 POC.

All storage is in-memory.  A persistence layer (SQL, NoSQL, files) can be
added in v2 by replacing the accessors here without changing any router
or domain-package code.

Singletons are module-level objects initialised once at import time and
shared across all requests through FastAPI dependency injection.
"""

from __future__ import annotations

from typing import Any, Dict, List

from apps.api.standards.loader import register_all as _register_standards
from apps.api.standards.loader import register_bundles as _register_bundles
from packages.adapters.defaults import register_defaults
from packages.adapters.registry import AdapterRegistry
from packages.catalog.catalog_service import CatalogService
from packages.core.models.audit_event import AuditEvent
from packages.core.models.mapping_project import MappingProject
from packages.core.models.mapping_version import MappingVersion
from packages.suggestions.semantic.azure_openai_provider import build_semantic_provider

# ---------------------------------------------------------------------------
# Shared adapter registry
# ---------------------------------------------------------------------------

_adapter_registry = AdapterRegistry()
register_defaults(_adapter_registry)

# ---------------------------------------------------------------------------
# Shared audit log (append-only list, injected into catalog + returned by GET)
# ---------------------------------------------------------------------------

_audit_log: List[AuditEvent] = []

# ---------------------------------------------------------------------------
# Catalog service (in-memory)
# ---------------------------------------------------------------------------

_catalog = CatalogService(
    adapter_registry=_adapter_registry,
    audit_log=_audit_log,
)

# Preload bundled standard schemas (OMOP CDM 5.4 + FHIR R4) — idempotent.
_register_standards(_catalog)
# Create merged composite schemas (FHIR_R4, OMOP_CDM_5_4) for single-click standard selection.
_register_bundles(_catalog)

# ---------------------------------------------------------------------------
# Project store and mapping store (in-memory)
# ---------------------------------------------------------------------------

_projects: Dict[str, MappingProject] = {}
_mapping_versions: Dict[str, List[MappingVersion]] = {}  # project_id → versions

# ---------------------------------------------------------------------------
# Semantic similarity provider (singleton, shared across all requests)
# ---------------------------------------------------------------------------

_semantic_provider = build_semantic_provider()


# ---------------------------------------------------------------------------
# Accessors (clean seams for future persistence swap)
# ---------------------------------------------------------------------------

def get_adapter_registry() -> AdapterRegistry:
    return _adapter_registry


def get_catalog() -> CatalogService:
    return _catalog


def get_audit_log() -> List[AuditEvent]:
    return _audit_log


def get_projects() -> Dict[str, MappingProject]:
    return _projects


def get_mapping_versions() -> Dict[str, List[MappingVersion]]:
    return _mapping_versions


def get_semantic_provider() -> object:
    return _semantic_provider


def reset_state() -> None:
    """Reset all in-memory state.  Called by tests to isolate state.

    Deliberately performs **no disk I/O** so tests stay isolated and the
    persistence layer is never engaged from here.
    """
    global _audit_log, _catalog, _projects, _mapping_versions, _adapter_registry
    _audit_log.clear()
    _projects.clear()
    _mapping_versions.clear()
    # Re-create catalog so it shares the cleared audit_log list
    _catalog.__init__(  # type: ignore[misc]
        adapter_registry=_adapter_registry,
        audit_log=_audit_log,
    )


# ---------------------------------------------------------------------------
# Persistence (optional, file-based snapshot)
# ---------------------------------------------------------------------------

def _project_pins() -> Dict[str, Dict[str, Any]]:
    """Lazily reach the schemas router's per-project pin index.

    Imported lazily to avoid a circular import (the schemas router imports
    ``deps`` which imports this module).
    """
    from apps.api.routers.schemas import get_project_pins

    return get_project_pins()


def save_state() -> bool:
    """Persist the current mutable state to disk (no-op if persistence off).

    Returns True if a snapshot was written, False otherwise (including the
    common case where persistence is disabled, e.g. during tests).  Never
    raises — persistence failures must not break a request.
    """
    from apps.api import persistence

    data_dir = persistence.resolve_data_dir()
    if data_dir is None:
        return False

    try:
        snapshot = persistence.build_snapshot(
            projects=_projects,
            mapping_versions=_mapping_versions,
            audit_log=_audit_log,
            catalog=_catalog,
            project_pins=_project_pins(),
        )
    except Exception:  # noqa: BLE001 - persistence must never crash a request
        import logging

        logging.getLogger(__name__).exception("Failed to build state snapshot")
        return False

    return persistence.write_snapshot(data_dir, snapshot)


def load_state() -> bool:
    """Load a persisted snapshot from disk into the live state, if present.

    Must be called AFTER the bundled standard schemas have been registered so
    that standards are never duplicated and always win over snapshot copies.
    Returns True if a snapshot was applied, False otherwise.  Never raises.
    """
    from apps.api import persistence

    data_dir = persistence.resolve_data_dir()
    if data_dir is None:
        return False

    snapshot = persistence.read_snapshot(data_dir)
    if not snapshot:
        return False

    try:
        persistence.apply_snapshot(
            snapshot,
            projects=_projects,
            mapping_versions=_mapping_versions,
            audit_log=_audit_log,
            catalog=_catalog,
            project_pins=_project_pins(),
        )
    except Exception:  # noqa: BLE001 - a bad snapshot must not crash boot
        import logging

        logging.getLogger(__name__).exception("Failed to apply state snapshot")
        return False

    return True


# Load any persisted snapshot AFTER standards have been registered above.
# This is a no-op under pytest / when persistence is disabled.
load_state()
