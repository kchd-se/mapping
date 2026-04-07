"""Adapter interfaces (contracts) for Phase 2.

All adapters MUST implement InputSchemaAdapter or OutputSchemaSource.
Core logic remains format-agnostic (RL-05): it only ever consumes
CanonicalSchema from /packages/core — it never calls adapter internals.

Design principles:
- Interfaces are defined using ABCs so violations fail at class definition
  time, not at call time.
- Adapters are identified by a list of format identifiers they support
  (e.g. "json_schema", "csv_schema") so the registry can resolve without
  hardcoding (RL-03 / AC-03).
- parse() returns CanonicalSchema — the ONLY permitted unit of exchange
  with core.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from packages.core.models.canonical_schema import CanonicalSchema


@dataclass(frozen=True)
class AdapterMetadata:
    """Static metadata describing an adapter.

    Attributes:
        adapter_id: Unique string identifier for this adapter implementation.
        display_name: Human-readable name shown in UI and logs.
        version: Adapter implementation version (semver string).
        supported_formats: List of format identifiers this adapter handles
                           (e.g. ["json_schema"]).  One adapter may support
                           multiple closely related format variants.
        description: Optional human-readable description.
    """

    adapter_id: str
    display_name: str
    version: str
    supported_formats: List[str]
    description: Optional[str] = None


class InputSchemaAdapter(ABC):
    """Contract that every input format adapter MUST implement.

    An adapter converts format-specific schema input into a CanonicalSchema.
    No format parsing logic is permitted outside this package (RL-05).
    """

    @property
    @abstractmethod
    def metadata(self) -> AdapterMetadata:
        """Return static metadata describing this adapter."""

    @abstractmethod
    def parse(self, raw_input: Any, schema_name: str = "", schema_version: str = "") -> CanonicalSchema:
        """Parse format-specific input and return a CanonicalSchema.

        Args:
            raw_input: Format-specific input. The concrete type depends on
                       the adapter (dict for JSON Schema, str for CSV text,
                       etc.).  Type validation is the adapter's responsibility.
            schema_name: Optional caller-supplied name for the resulting schema.
            schema_version: Optional caller-supplied version string.

        Returns:
            A fully populated CanonicalSchema with stable, unique field IDs.

        Raises:
            AdapterParseError: If the input cannot be parsed.
        """


class OutputSchemaSource(ABC):
    """Contract for pluggable output schema sources (catalogs, registries).

    In v1 this is a structural placeholder.  Concrete implementations
    (FHIR registry fetcher, OMOP CDM loader, custom catalog) will be
    added in Phase 3 (catalog/sync).  This interface is defined here so
    that the adapter registry can accommodate both input and output adapters
    under one discovery mechanism.
    """

    @property
    @abstractmethod
    def metadata(self) -> AdapterMetadata:
        """Return static metadata describing this source."""

    @abstractmethod
    def load(self, schema_id: str, version: Optional[str] = None) -> CanonicalSchema:
        """Load a named target schema by ID and optional version.

        Implementations may fetch from a registry, read from a cache, or
        serve from a local catalog.  Network access is deferred to Phase 3.

        Args:
            schema_id: Format-specific identifier (e.g. FHIR profile URL,
                       OMOP CDM table name).
            version: Optional version to pin.  If None, the source returns
                     its latest cached version.

        Returns:
            CanonicalSchema representing the target schema.

        Raises:
            AdapterLoadError: If the schema cannot be loaded.
        """

    @abstractmethod
    def list_available(self) -> List[Dict[str, str]]:
        """Return a list of available schemas ({id, name, version} dicts).

        Used by the catalog browser in later phases.
        """


# ---------------------------------------------------------------------------
# Adapter-specific exceptions
# ---------------------------------------------------------------------------

class AdapterError(Exception):
    """Base class for all adapter errors."""


class AdapterParseError(AdapterError):
    """Raised when an adapter cannot parse the supplied raw input."""


class AdapterLoadError(AdapterError):
    """Raised when an OutputSchemaSource cannot load the requested schema."""


class AdapterNotFoundError(AdapterError):
    """Raised when no registered adapter supports the requested format."""
