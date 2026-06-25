"""File-based snapshot persistence for the v1 API.

The v1 application keeps all runtime state in memory (see ``state.py``).  This
module adds an *optional* durability layer so that operator-entered data —
projects, mapping versions, the audit trail, and user-imported (non-standard)
schemas with their version pins — survives a process restart.

Design / red lines
-------------------
- **Schema-/metadata only.**  Nothing here touches patient or individual data
  (RL-02); it serialises exactly the same objects the in-memory store already
  holds: schema descriptors, mapping rules, audit events, etc.
- **Pre-loaded standards are never snapshotted.**  The bundled FHIR/OMOP
  standard schemas are re-registered deterministically on every boot
  (``register_all`` / ``register_bundles``).  Persisting them would create
  duplicates and pin the catalog to a stale copy.  We therefore save only
  catalog entries whose ``schema_type`` is *not* ``STANDARD`` and, on load,
  skip any entry whose ``schema_id`` already exists (the standards win).
- **Opt-in via environment.**  Persistence is a no-op unless the data
  directory has been resolved.  Tests never set it, so ``npm run test:api``
  performs zero disk I/O and stays isolated.
- **Robust, never fatal.**  Saves write to a temp file and atomically rename
  into place; any failure is swallowed (logged) so a snapshot problem can
  never crash a request.

Serialisation uses each model's existing ``to_dict()`` / ``from_dict()``
seams (the domain models are dataclasses, not pydantic, but expose the same
round-trip contract), so the on-disk format mirrors the API/OpenAPI shapes.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: Name of the environment variable that selects the data directory.
DATA_DIR_ENV_VAR = "MAPPING_DATA_DIR"

#: Default directory (relative to the current working directory) used when the
#: environment variable is unset.  See ``resolve_data_dir`` for the exact
#: precedence rules.
DEFAULT_DATA_DIR = "./data"

#: Snapshot file name inside the data directory.
SNAPSHOT_FILENAME = "snapshot.json"

#: Snapshot schema version (bump if the on-disk layout changes incompatibly).
SNAPSHOT_VERSION = 1


def _running_under_pytest() -> bool:
    """True when executing inside a pytest session.

    Used as a belt-and-braces guard so the persistence layer never performs
    disk I/O during the test suite, regardless of ambient environment.
    """
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in os.environ.get(
        "_", ""
    )


def resolve_data_dir() -> Optional[Path]:
    """Resolve the persistence data directory, or ``None`` to disable.

    Precedence:
    1. If running under pytest → ``None`` (persistence disabled; tests stay
       isolated and write nothing to disk).
    2. If ``MAPPING_DATA_DIR`` is set (even to a relative path) → that path.
    3. Otherwise → the default ``./data`` directory relative to cwd.

    When a directory is resolved it is created (including parents) if missing.
    Returns ``None`` if the directory cannot be created.
    """
    if _running_under_pytest():
        return None

    raw = os.environ.get(DATA_DIR_ENV_VAR)
    path = Path(raw) if raw else Path(DEFAULT_DATA_DIR)

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - environment dependent
        logger.warning("Could not create data dir %s: %s", path, exc)
        return None
    return path


def snapshot_path(data_dir: Path) -> Path:
    return data_dir / SNAPSHOT_FILENAME


# ---------------------------------------------------------------------------
# Snapshot build / apply
# ---------------------------------------------------------------------------

def build_snapshot(
    *,
    projects: Dict[str, Any],
    mapping_versions: Dict[str, List[Any]],
    audit_log: List[Any],
    catalog: Any,
    project_pins: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Serialise the persistable slice of application state to a plain dict.

    Standard (pre-loaded) catalog entries are deliberately excluded; only
    user-imported schemas are captured.
    """
    from packages.catalog.models.schema_descriptor import SchemaType

    entries_out: List[Dict[str, Any]] = []
    pins_out: List[Dict[str, Any]] = []

    # catalog internals are accessed via a small accessor to keep the seam
    # explicit; fall back gracefully if the catalog shape changes.
    entries = getattr(catalog, "_entries", {}) or {}
    pins = getattr(catalog, "_pins", {}) or {}

    for entry in entries.values():
        if entry.descriptor.schema_type == SchemaType.STANDARD:
            continue  # standards are re-registered at boot, never persisted
        entries_out.append(entry.to_dict())

    for pin in pins.values():
        pins_out.append(pin.to_dict())

    project_pins_out: Dict[str, Dict[str, Any]] = {}
    for project_id, role_map in project_pins.items():
        project_pins_out[project_id] = {
            role: pin.to_dict() for role, pin in role_map.items()
        }

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "projects": [p.to_dict() for p in projects.values()],
        "mapping_versions": {
            pid: [v.to_dict() for v in versions]
            for pid, versions in mapping_versions.items()
        },
        "audit_log": [e.to_dict() for e in audit_log],
        "catalog_entries": entries_out,
        "version_pins": pins_out,
        "project_pins": project_pins_out,
    }


def apply_snapshot(
    data: Dict[str, Any],
    *,
    projects: Dict[str, Any],
    mapping_versions: Dict[str, List[Any]],
    audit_log: List[Any],
    catalog: Any,
    project_pins: Dict[str, Dict[str, Any]],
) -> None:
    """Restore *data* (a snapshot dict) into the live in-memory containers.

    Mutates the passed-in containers in place so the existing module-level
    singletons (and the lists/dicts other components already hold references
    to) keep working.  Standard schemas already registered at boot are
    preserved: catalog entries and pins whose ids already exist are skipped.
    """
    from packages.catalog.models.catalog_entry import CatalogEntry
    from packages.catalog.models.version_pin import VersionPin
    from packages.core.models.audit_event import AuditEvent
    from packages.core.models.mapping_project import MappingProject
    from packages.core.models.mapping_version import MappingVersion

    # -- Projects -----------------------------------------------------------
    for pdata in data.get("projects", []):
        project = MappingProject.from_dict(pdata)
        projects[project.id] = project

    # -- Mapping versions ---------------------------------------------------
    for pid, versions in data.get("mapping_versions", {}).items():
        mapping_versions[pid] = [MappingVersion.from_dict(v) for v in versions]

    # -- Audit log (append, preserving any boot-time events) ----------------
    for edata in data.get("audit_log", []):
        audit_log.append(AuditEvent.from_dict(edata))

    # -- Catalog entries (user-imported only; never clobber standards) ------
    entries = getattr(catalog, "_entries", None)
    if entries is not None:
        for edata in data.get("catalog_entries", []):
            entry = CatalogEntry.from_dict(edata)
            schema_id = entry.descriptor.id
            if schema_id in entries:
                continue  # standard / already present — keep the live one
            entries[schema_id] = entry

    # -- Version pins -------------------------------------------------------
    pins = getattr(catalog, "_pins", None)
    if pins is not None:
        for pdata in data.get("version_pins", []):
            pin = VersionPin.from_dict(pdata)
            if pin.id in pins:
                continue
            pins[pin.id] = pin

    # -- Per-project pin index (schemas router store) -----------------------
    for project_id, role_map in data.get("project_pins", {}).items():
        target = project_pins.setdefault(project_id, {})
        for role, pin_data in role_map.items():
            target[role] = VersionPin.from_dict(pin_data)


# ---------------------------------------------------------------------------
# Disk I/O
# ---------------------------------------------------------------------------

def write_snapshot(data_dir: Path, snapshot: Dict[str, Any]) -> bool:
    """Atomically write *snapshot* as JSON into *data_dir*.

    Writes to a temp file in the same directory then ``os.replace`` into the
    final location so a reader never observes a partial file.  Returns True on
    success; logs and returns False on any error (never raises).
    """
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        target = snapshot_path(data_dir)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(data_dir), prefix=".snapshot-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(snapshot, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, target)
        finally:
            # Clean up the temp file if the replace never happened.
            if os.path.exists(tmp_name):
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
        return True
    except Exception:  # noqa: BLE001 - persistence must never crash a request
        logger.exception("Failed to write state snapshot to %s", data_dir)
        return False


def read_snapshot(data_dir: Path) -> Optional[Dict[str, Any]]:
    """Read and parse the snapshot from *data_dir*, or ``None`` if absent/bad."""
    path = snapshot_path(data_dir)
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001 - a corrupt snapshot must not crash boot
        logger.exception("Failed to read state snapshot from %s", path)
        return None
