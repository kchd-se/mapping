"""FastAPI dependency providers.

Each function is a FastAPI dependency that injects shared application
state into route handlers.  Swapping in-memory for persistent storage
in v2 only requires changing these functions.
"""

from __future__ import annotations

from typing import Dict, List

from fastapi import Depends

from apps.api import state
from packages.adapters.registry import AdapterRegistry
from packages.catalog.catalog_service import CatalogService
from packages.core.models.audit_event import AuditEvent
from packages.core.models.mapping_project import MappingProject
from packages.core.models.mapping_version import MappingVersion


def catalog_dep() -> CatalogService:
    return state.get_catalog()


def registry_dep() -> AdapterRegistry:
    return state.get_adapter_registry()


def audit_dep() -> List[AuditEvent]:
    return state.get_audit_log()


def projects_dep() -> Dict[str, MappingProject]:
    return state.get_projects()


def mapping_versions_dep() -> Dict[str, List[MappingVersion]]:
    return state.get_mapping_versions()


def semantic_provider_dep() -> object:
    return state.get_semantic_provider()
