"""CatalogService — manages schema registration, versioning, and pinning.

Design:
- Storage is in-memory (dict) — a persistence layer can be added in v2
  without changing this interface (AC-06).
- The adapter registry is injected so the catalog has no hardcoded format
  dependencies (RL-03, AC-03).
- Audit events are appended to an injected list, keeping the service
  independent of storage/transport concerns.
- Version overwrite is prevented at the service level: once a version label
  is registered for a schema, it is immutable.
- Pinning reads from the immutable SchemaVersion.canonical_schema_snapshot
  so resolution is independent of future catalog state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from packages.adapters.registry import AdapterRegistry
from packages.catalog.models.catalog_entry import CatalogEntry
from packages.catalog.models.schema_descriptor import (
    ApprovalStatus,
    SchemaDescriptor,
    SchemaSource,
    SchemaType,
)
from packages.catalog.models.schema_version import SchemaVersion, compute_checksum
from packages.catalog.models.version_pin import VersionPin
from packages.core.models.audit_event import AuditAction, AuditEvent
from packages.core.models.canonical_schema import CanonicalSchema


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CatalogError(Exception):
    """Base class for catalog errors."""


class SchemaNotFoundError(CatalogError):
    """Raised when a schema id or version label is not found."""


class SchemaVersionConflictError(CatalogError):
    """Raised when attempting to overwrite an existing immutable schema version."""


class PinNotFoundError(CatalogError):
    """Raised when a pin_id does not exist in this catalog."""


# ---------------------------------------------------------------------------
# CatalogService
# ---------------------------------------------------------------------------

class CatalogService:
    """In-process schema catalog for v1 POC.

    Manages:
    - Custom schema registration via pluggable adapters.
    - Standard schema references (pre-parsed, e.g. from cache/sync).
    - Immutable version history with overwrite protection.
    - Version pinning for mapping projects.
    - Healthcare-grade audit logging.
    """

    def __init__(
        self,
        adapter_registry: AdapterRegistry,
        audit_log: Optional[List[AuditEvent]] = None,
        catalog_id: str = "",
    ) -> None:
        self._registry = adapter_registry
        self._audit: List[AuditEvent] = audit_log if audit_log is not None else []
        self._entries: Dict[str, CatalogEntry] = {}   # schema_id → CatalogEntry
        self._pins: Dict[str, VersionPin] = {}         # pin_id → VersionPin
        self.catalog_id = catalog_id or str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Registration: custom schemas (parsed via adapter)
    # ------------------------------------------------------------------

    def register_custom_schema(
        self,
        raw_input: Any,
        format_id: str,
        schema_name: str,
        version_label: str,
        owner: str,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        metadata_tags: Optional[Dict[str, str]] = None,
    ) -> SchemaVersion:
        """Parse raw_input via the matching adapter and register as a new version.

        Uses the injected adapter registry to resolve and call the adapter.
        Version overwrite raises SchemaVersionConflictError.

        Returns:
            The newly created SchemaVersion (use .schema_id to access the entry).
        """
        adapter = self._registry.resolve_input(format_id)
        canonical = adapter.parse(
            raw_input,
            schema_name=schema_name,
            schema_version=version_label,
        )
        return self._create_version(
            canonical=canonical,
            schema_name=schema_name,
            format_id=format_id,
            version_label=version_label,
            owner=owner,
            schema_type=SchemaType.CUSTOM,
            source=SchemaSource.UPLOADED,
            description=description,
            notes=notes,
            metadata_tags=metadata_tags or {},
        )

    # ------------------------------------------------------------------
    # Registration: standard schemas (pre-parsed, no adapter call needed)
    # ------------------------------------------------------------------

    def register_standard_schema(
        self,
        canonical: CanonicalSchema,
        format_id: str,
        schema_name: str,
        version_label: str,
        owner: str = "system",
        description: Optional[str] = None,
        notes: Optional[str] = None,
        metadata_tags: Optional[Dict[str, str]] = None,
        source: SchemaSource = SchemaSource.EXTERNAL_REGISTRY,
    ) -> SchemaVersion:
        """Register a pre-parsed standard schema (e.g. cached FHIR profile).

        Used when the CanonicalSchema was produced externally (catalog sync,
        offline cache) and adapter parsing is not needed.
        """
        return self._create_version(
            canonical=canonical,
            schema_name=schema_name,
            format_id=format_id,
            version_label=version_label,
            owner=owner,
            schema_type=SchemaType.STANDARD,
            source=source,
            description=description,
            notes=notes,
            metadata_tags=metadata_tags or {},
        )

    # ------------------------------------------------------------------
    # Registration: sync import (preserves source schema_id)
    # ------------------------------------------------------------------

    def import_synced_version(
        self,
        descriptor_dict: Dict[str, Any],
        version: SchemaVersion,
        actor: str,
    ) -> str:
        """Import a version received from a sync operation.

        Creates the catalog entry if it doesn't exist, using the SAME
        schema_id as the source catalog so that cross-catalog version pins
        remain resolvable.

        Returns:
            One of: "added" | "skipped" | "conflict"

        This method is the v2 extension point: a real sync implementation
        replaces network transfer but calls this same method on the target.
        """
        schema_id = descriptor_dict["id"]

        if schema_id not in self._entries:
            descriptor = SchemaDescriptor.from_dict(descriptor_dict)
            descriptor.source = SchemaSource.SYNC_RECEIVED
            self._entries[schema_id] = CatalogEntry(descriptor=descriptor)

        entry = self._entries[schema_id]

        if entry.has_version(version.version_label):
            existing = entry.get_version(version.version_label)
            if existing.checksum != version.checksum:
                return "conflict"
            return "skipped"

        # Preserve original version id so pins from source catalog still resolve
        new_version = SchemaVersion(
            id=version.id,
            schema_id=schema_id,
            version_label=version.version_label,
            created_at=version.created_at,
            checksum=version.checksum,
            canonical_schema_snapshot=version.canonical_schema_snapshot,
            notes=version.notes,
        )
        entry.versions.append(new_version)
        entry.default_version_id = new_version.id

        self._emit(
            actor=actor,
            action=AuditAction.CATALOG_SYNC,
            object_type="schema_version",
            object_id=new_version.id,
            after={
                "schema_id": schema_id,
                "version_label": version.version_label,
                "checksum": version.checksum,
            },
        )
        return "added"

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_entry(self, schema_id: str) -> CatalogEntry:
        entry = self._entries.get(schema_id)
        if entry is None:
            raise SchemaNotFoundError(
                f"No catalog entry found with schema_id {schema_id!r}."
            )
        return entry

    def get_schema_version(self, schema_id: str, version_label: str) -> SchemaVersion:
        """Retrieve a specific version by schema_id and version_label."""
        entry = self.get_entry(schema_id)
        version = entry.get_version(version_label)
        if version is None:
            available = [v.version_label for v in entry.versions]
            raise SchemaNotFoundError(
                f"Schema {schema_id!r} has no version {version_label!r}. "
                f"Available: {available}"
            )
        return version

    def get_latest_version(self, schema_id: str) -> SchemaVersion:
        """Retrieve the most recently registered version for a schema."""
        entry = self.get_entry(schema_id)
        version = entry.get_latest_version()
        if version is None:
            raise SchemaNotFoundError(
                f"Schema {schema_id!r} has no versions registered."
            )
        return version

    def list_entries(
        self,
        schema_type: Optional[SchemaType] = None,
        format_id: Optional[str] = None,
        approval_status: Optional[ApprovalStatus] = None,
    ) -> List[CatalogEntry]:
        """List catalog entries with optional filters."""
        result = list(self._entries.values())
        if schema_type is not None:
            result = [e for e in result if e.descriptor.schema_type == schema_type]
        if format_id is not None:
            result = [e for e in result if e.descriptor.format_id == format_id]
        if approval_status is not None:
            result = [
                e for e in result
                if e.descriptor.approval_status == approval_status
            ]
        return result

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------

    def approve_schema(self, schema_id: str, actor: str) -> None:
        """Mark a schema as approved (required for APPROVED_ONLY sync scope)."""
        entry = self.get_entry(schema_id)
        before_status = entry.descriptor.approval_status.value
        entry.descriptor.approval_status = ApprovalStatus.APPROVED
        self._emit(
            actor=actor,
            action=AuditAction.APPROVAL,
            object_type="schema_descriptor",
            object_id=schema_id,
            before={"approval_status": before_status},
            after={"approval_status": ApprovalStatus.APPROVED.value},
        )

    # ------------------------------------------------------------------
    # Version Pinning
    # ------------------------------------------------------------------

    def pin_version(
        self,
        project_id: str,
        schema_role: str,
        schema_id: str,
        version_label: str,
        actor: str,
    ) -> VersionPin:
        """Pin a specific schema version to a mapping project role.

        The pin is immutable.  The pinned CanonicalSchema is always resolved
        from the SchemaVersion.canonical_schema_snapshot, which is independent
        of future catalog state.

        Raises:
            SchemaNotFoundError: If schema_id or version_label don't exist.
        """
        version = self.get_schema_version(schema_id, version_label)
        pin = VersionPin(
            id=str(uuid.uuid4()),
            project_id=project_id,
            schema_role=schema_role,
            schema_id=schema_id,
            schema_version_id=version.id,
            version_label=version_label,
            pinned_at=datetime.now(timezone.utc).isoformat(),
            pinned_by=actor,
        )
        self._pins[pin.id] = pin
        self._emit(
            actor=actor,
            action=AuditAction.VERSION_PIN,
            object_type="version_pin",
            object_id=pin.id,
            after={
                "project_id": project_id,
                "schema_role": schema_role,
                "schema_id": schema_id,
                "version_label": version_label,
                "schema_version_id": version.id,
            },
        )
        return pin

    def resolve_pin(self, pin_id: str) -> CanonicalSchema:
        """Resolve a pin to the exact CanonicalSchema that was pinned.

        Resolution reads from SchemaVersion.canonical_schema_snapshot — it
        is NOT affected by subsequent catalog registrations or deletions.
        """
        pin = self._pins.get(pin_id)
        if pin is None:
            raise PinNotFoundError(f"No version pin found with id {pin_id!r}.")

        entry = self.get_entry(pin.schema_id)
        version = entry.get_version_by_id(pin.schema_version_id)
        if version is None:
            raise SchemaNotFoundError(
                f"Version {pin.schema_version_id!r} not found in schema "
                f"{pin.schema_id!r}."
            )
        return version.resolve_canonical()

    def get_pin(self, pin_id: str) -> VersionPin:
        pin = self._pins.get(pin_id)
        if pin is None:
            raise PinNotFoundError(f"No version pin found with id {pin_id!r}.")
        return pin

    def get_pins_for_project(self, project_id: str) -> List[VersionPin]:
        """Return all pins owned by *project_id*."""
        return [p for p in self._pins.values() if p.project_id == project_id]

    # ------------------------------------------------------------------
    # Audit log access
    # ------------------------------------------------------------------

    @property
    def audit_log(self) -> List[AuditEvent]:
        """Return a defensive copy of the audit log (append-only by contract)."""
        return list(self._audit)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_version(
        self,
        canonical: CanonicalSchema,
        schema_name: str,
        format_id: str,
        version_label: str,
        owner: str,
        schema_type: SchemaType,
        source: SchemaSource,
        description: Optional[str],
        notes: Optional[str],
        metadata_tags: Dict[str, str],
    ) -> SchemaVersion:
        """Create or extend a CatalogEntry with a new immutable version."""
        existing_entry = self._find_entry_by_name_and_format(schema_name, format_id)

        if existing_entry is None:
            descriptor = SchemaDescriptor(
                id=str(uuid.uuid4()),
                name=schema_name,
                schema_type=schema_type,
                format_id=format_id,
                source=source,
                owner=owner,
                description=description,
                metadata_tags=metadata_tags,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            entry = CatalogEntry(descriptor=descriptor)
            self._entries[descriptor.id] = entry
        else:
            entry = existing_entry
            # Guard: version labels are immutable — no overwrite allowed
            if entry.has_version(version_label):
                raise SchemaVersionConflictError(
                    f"Schema {schema_name!r} (format: {format_id!r}) already "
                    f"has version {version_label!r}. Versioned schemas are "
                    "immutable. Use a new version label."
                )

        version = SchemaVersion.create(
            schema_id=entry.descriptor.id,
            version_label=version_label,
            canonical_schema=canonical,
            notes=notes,
        )
        entry.versions.append(version)
        entry.default_version_id = version.id

        self._emit(
            actor=owner,
            action=AuditAction.SCHEMA_VERSION_CREATE,
            object_type="schema_version",
            object_id=version.id,
            after={
                "schema_id": entry.descriptor.id,
                "schema_name": schema_name,
                "format_id": format_id,
                "version_label": version_label,
                "checksum": version.checksum,
            },
        )
        return version

    def _find_entry_by_name_and_format(
        self, schema_name: str, format_id: str
    ) -> Optional[CatalogEntry]:
        """Find an existing entry by (name, format_id) composite key."""
        for entry in self._entries.values():
            if (
                entry.descriptor.name == schema_name
                and entry.descriptor.format_id == format_id
            ):
                return entry
        return None

    def _emit(
        self,
        actor: str,
        action: AuditAction,
        object_type: str,
        object_id: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event. Append-only — never modifies existing entries."""
        event = AuditEvent(
            id=str(uuid.uuid4()),
            actor=actor,
            action=action,
            timestamp=datetime.now(timezone.utc).isoformat(),
            object_type=object_type,
            object_id=object_id,
            before=before,
            after=after,
        )
        self._audit.append(event)
