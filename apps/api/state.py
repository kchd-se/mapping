"""In-memory application state for the v1 POC.

All storage is in-memory.  A persistence layer (SQL, NoSQL, files) can be
added in v2 by replacing the accessors here without changing any router
or domain-package code.

Singletons are module-level objects initialised once at import time and
shared across all requests through FastAPI dependency injection.
"""

from __future__ import annotations

from typing import Any, Dict, List

from packages.adapters.defaults import register_defaults
from packages.adapters.registry import AdapterRegistry
from packages.catalog.catalog_service import CatalogService
from packages.core.models.audit_event import AuditEvent
from packages.core.models.mapping_project import MappingProject
from packages.core.models.mapping_version import MappingVersion

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

# ---------------------------------------------------------------------------
# Project store and mapping store (in-memory)
# ---------------------------------------------------------------------------

_projects: Dict[str, MappingProject] = {}
_mapping_versions: Dict[str, List[MappingVersion]] = {}  # project_id → versions


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


def reset_state() -> None:
    """Reset all in-memory state.  Called by tests to isolate state."""
    global _audit_log, _catalog, _projects, _mapping_versions, _adapter_registry
    _audit_log.clear()
    _projects.clear()
    _mapping_versions.clear()
    # Re-create catalog so it shares the cleared audit_log list
    _catalog.__init__(  # type: ignore[misc]
        adapter_registry=_adapter_registry,
        audit_log=_audit_log,
    )
