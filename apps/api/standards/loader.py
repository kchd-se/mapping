"""Standards bundle loader — registers pre-defined OMOP and FHIR schemas at
API startup.

Design:
- Schema definitions live in JSON files under apps/api/standards/omop/ and
  apps/api/standards/fhir/ in a lightweight "bundle definition" format
  (see README.md).
- Deterministic UUID5 identifiers are derived from (format_id, schema_name,
  version, field_path) so the same IDs are produced on every startup.
- Registration is idempotent: calling register_all() more than once is safe.
  Already-registered (name, format_id, version_label) combinations raise
  SchemaVersionConflictError internally; the loader catches and skips them.
- Each schema is auto-approved after registration so it appears as
  type=standard, status=approved in the catalog listing.

Extension point (Phase 5d):
  Drop a new JSON file in the appropriate subdirectory and restart the server.
  No code changes required.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List, Tuple

from packages.catalog.catalog_service import CatalogService, SchemaVersionConflictError
from packages.catalog.models.schema_descriptor import SchemaSource
from packages.core.models.canonical_schema import (
    CanonicalField,
    CanonicalSchema,
    Cardinality,
    FieldConstraints,
    FieldType,
    FieldTypeCategory,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fixed UUID5 namespace — never change; doing so would alter all bundled IDs.
_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # NAMESPACE_URL

_STANDARDS_DIR = Path(__file__).parent

# (subdirectory, format_id) pairs — order determines registration order.
_BUNDLE_DIRS: List[Tuple[Path, str]] = [
    (_STANDARDS_DIR / "omop", "omop_cdm"),
    (_STANDARDS_DIR / "fhir", "fhir_profile"),
]


# ---------------------------------------------------------------------------
# Deterministic ID helpers
# ---------------------------------------------------------------------------

def _det_id(key: str) -> str:
    """Return a deterministic UUID5 string for *key*."""
    return str(uuid.uuid5(_NAMESPACE, key))


def _schema_id(format_id: str, schema_name: str, version: str) -> str:
    return _det_id(f"{format_id}:{schema_name}:{version}")


def _field_id(format_id: str, schema_name: str, version: str, path: str) -> str:
    return _det_id(f"{format_id}:{schema_name}:{version}:{path}")


# ---------------------------------------------------------------------------
# Bundle → CanonicalSchema conversion
# ---------------------------------------------------------------------------

def _build_canonical(bundle: dict) -> CanonicalSchema:
    """Convert a bundle definition dict into a CanonicalSchema.

    Bundle format (see README.md):
    {
        "schema_name": str,
        "format_id": str,
        "version": str,
        "description": str (optional),
        "metadata_tags": dict (optional),
        "fields": [
            {
                "path": str,
                "label": str (optional),
                "description": str (optional),
                "type_category": "primitive" | "object" | "array",
                "type_primitive": str (optional),
                "required": bool (optional, default false)
            },
            ...
        ]
    }
    """
    schema_name: str = bundle["schema_name"]
    format_id: str = bundle["format_id"]
    version: str = bundle["version"]

    canonical_fields: List[CanonicalField] = []
    for fdef in bundle.get("fields", []):
        path: str = fdef["path"]
        required: bool = bool(fdef.get("required", False))

        cf = CanonicalField(
            id=_field_id(format_id, schema_name, version, path),
            path=path,
            label=fdef.get("label"),
            description=fdef.get("description"),
            field_type=FieldType(
                category=FieldTypeCategory(fdef.get("type_category", "primitive")),
                primitive=fdef.get("type_primitive"),
            ),
            cardinality=Cardinality(
                min_occurs=1 if required else 0,
                max_occurs=1,
            ),
            constraints=FieldConstraints(required=required),
        )
        canonical_fields.append(cf)

    return CanonicalSchema(
        id=_schema_id(format_id, schema_name, version),
        name=schema_name,
        version=version,
        description=bundle.get("description"),
        fields=canonical_fields,
        metadata_tags=bundle.get("metadata_tags", {}),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_bundles(catalog: CatalogService) -> int:
    """Create one merged "standard" schema per format+version group.

    After ``register_all()`` has populated the individual profiles/tables, this
    function merges them into composite schemas (FHIR_R4 and OMOP_CDM_5_4) so
    that users can map against an entire standard with a single selection rather
    than picking one profile at a time.

    Each bundle schema:
    - combines all fields from the individual constituent schemas
    - carries ``metadata_tags["bundle"] = "true"`` so the UI can surface it as
      a first-class standard card
    - is immediately approved (status = approved, type = standard)
    - is idempotent (safe to call multiple times)

    Returns:
        The number of composite schemas newly registered during this call.
    """
    _FHIR_INCLUDED = [
        "FHIR_Patient",
        "FHIR_Organization",
        "FHIR_Encounter",
        "FHIR_Condition",
        "FHIR_Observation",
        "FHIR_Procedure",
        "FHIR_Practitioner",
        "FHIR_PractitionerRole",
        "FHIR_Location",
    ]
    _OMOP_INCLUDED = [
        "OMOP_PERSON",
        "OMOP_CARE_SITE",
        "OMOP_VISIT_OCCURRENCE",
        "OMOP_PROCEDURE_OCCURRENCE",
        "OMOP_CONDITION_OCCURRENCE",
        "OMOP_DRUG_EXPOSURE",
        "OMOP_MEASUREMENT",
        "OMOP_OBSERVATION",
        "OMOP_DEATH",
        "OMOP_PROVIDER",
        "OMOP_LOCATION",
    ]
    _BUNDLE_SPECS = [
        {
            "name": "FHIR_R4",
            "format_id": "fhir_profile",
            "version": "R4",
            "description": (
                "Combined FHIR R4 standard — maps against Patient, Organization, "
                "Encounter, Condition, Observation, Procedure, Practitioner, "
                "PractitionerRole, and Location profiles."
            ),
            "included_names": _FHIR_INCLUDED,
            "metadata_tags": {
                "source": "bundled",
                "standard": "FHIR",
                "standard_version": "R4",
                "bundle": "true",
                "included_schemas": ",".join(_FHIR_INCLUDED),
            },
        },
        {
            "name": "OMOP_CDM_5_4",
            "format_id": "omop_cdm",
            "version": "5.4",
            "description": (
                "Combined OMOP CDM 5.4 standard — maps against PERSON, CARE_SITE, "
                "VISIT_OCCURRENCE, PROCEDURE_OCCURRENCE, CONDITION_OCCURRENCE, "
                "DRUG_EXPOSURE, MEASUREMENT, OBSERVATION, DEATH, PROVIDER, "
                "and LOCATION tables."
            ),
            "included_names": _OMOP_INCLUDED,
            "metadata_tags": {
                "source": "bundled",
                "standard": "OMOP CDM",
                "standard_version": "5.4",
                "bundle": "true",
                "included_schemas": ",".join(_OMOP_INCLUDED),
            },
        },
    ]

    entry_by_name = {e.descriptor.name: e for e in catalog.list_entries()}
    newly_registered = 0

    for spec in _BUNDLE_SPECS:
        merged_fields: List[CanonicalField] = []
        for included_name in spec["included_names"]:
            entry = entry_by_name.get(included_name)
            if entry is None:
                continue
            latest = entry.get_latest_version()
            if latest is None:
                continue
            merged_fields.extend(latest.resolve_canonical().fields)

        if not merged_fields:
            # Individual schemas not yet registered — skip.
            continue

        merged = CanonicalSchema(
            id=_schema_id(spec["format_id"], spec["name"], spec["version"]),
            name=spec["name"],
            version=spec["version"],
            description=spec["description"],
            fields=merged_fields,
            metadata_tags=spec["metadata_tags"],
        )

        try:
            sv = catalog.register_standard_schema(
                canonical=merged,
                format_id=spec["format_id"],
                schema_name=spec["name"],
                version_label=spec["version"],
                owner="system",
                description=spec["description"],
                notes="Auto-generated bundle of all constituent standard schemas.",
                metadata_tags=spec["metadata_tags"],
                source=SchemaSource.EXTERNAL_REGISTRY,
            )
            catalog.approve_schema(sv.schema_id, "system")
            newly_registered += 1
        except SchemaVersionConflictError:
            pass  # Already registered — idempotent.

    return newly_registered


def register_all(catalog: CatalogService) -> int:
    """Register all bundled standard schemas into *catalog*.

    Iterates over every JSON file in the configured bundle directories,
    converts each to a CanonicalSchema, and calls
    ``catalog.register_standard_schema()``.  Already-registered schemas are
    silently skipped (idempotent).  Newly registered schemas are immediately
    approved so they appear as ``status=approved`` in the catalog listing.

    Returns:
        The number of schemas newly registered during this call (0 if all
        were already present).
    """
    newly_registered = 0

    for bundle_dir, format_id in _BUNDLE_DIRS:
        if not bundle_dir.is_dir():
            continue

        for json_path in sorted(bundle_dir.glob("*.json")):
            with json_path.open(encoding="utf-8") as fh:
                bundle = json.load(fh)

            canonical = _build_canonical(bundle)

            try:
                version = catalog.register_standard_schema(
                    canonical=canonical,
                    format_id=bundle["format_id"],
                    schema_name=bundle["schema_name"],
                    version_label=bundle["version"],
                    owner="system",
                    description=bundle.get("description"),
                    notes=f"Bundled standard schema loaded from {json_path.name}",
                    metadata_tags=bundle.get("metadata_tags", {}),
                    source=SchemaSource.EXTERNAL_REGISTRY,
                )
                catalog.approve_schema(version.schema_id, "system")
                newly_registered += 1
            except SchemaVersionConflictError:
                # Already registered on a previous startup — skip silently.
                pass

    return newly_registered
