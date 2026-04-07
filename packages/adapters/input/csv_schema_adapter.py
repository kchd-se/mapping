"""CSV Schema Input Adapter (production-quality for v1).

Accepts a CSV-based schema definition where each row describes one field.
The CSV is parsed with Python's built-in `csv` module — no external
dependencies (RL-08: safe structured parsing).

Expected CSV columns (header row required, case-insensitive):
  Required:
    name          — field name (becomes the path)
  Optional:
    type          — data type (string|integer|decimal|boolean|date|datetime|...)
    required      — "true"/"yes"/"1" = required, anything else = optional
    description   — human-readable description
    label         — display label (falls back to `name`)
    parent        — dot-separated parent path for hierarchical schemas
                    (e.g. parent="address" makes the field path "address.city")
    enum          — pipe-separated list of allowed values (e.g. "A|B|C")
    pattern       — regex pattern
    min_value     — numeric minimum
    max_value     — numeric maximum
    min_length    — string minimum length
    max_length    — string maximum length
    terminology_system — URI of a terminology system (optional)
    terminology_code   — code within that system (optional)

Stable ID generation:
  Same SHA-256 path hash used by the JSON Schema adapter so IDs are
  consistent and portable across imports of the same schema.

CSV input may be supplied as:
  - a str (raw CSV text, read as StringIO)
  - a list of dicts (already parsed by csv.DictReader or equivalent)
"""

from __future__ import annotations

import csv
import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from packages.adapters.base import AdapterMetadata, AdapterParseError, InputSchemaAdapter
from packages.core.models.canonical_schema import (
    CanonicalField,
    CanonicalSchema,
    Cardinality,
    FieldConstraints,
    FieldType,
    FieldTypeCategory,
    TerminologyReference,
)

# Recognised column headers after lower-casing and strip.
_COL_NAME = "name"
_COL_TYPE = "type"
_COL_REQUIRED = "required"
_COL_DESCRIPTION = "description"
_COL_LABEL = "label"
_COL_PARENT = "parent"
_COL_ENUM = "enum"
_COL_PATTERN = "pattern"
_COL_MIN_VALUE = "min_value"
_COL_MAX_VALUE = "max_value"
_COL_MIN_LENGTH = "min_length"
_COL_MAX_LENGTH = "max_length"
_COL_TERM_SYSTEM = "terminology_system"
_COL_TERM_CODE = "terminology_code"


def _stable_field_id(path: str) -> str:
    """Stable deterministic ID from path (consistent with JSON Schema adapter)."""
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "yes", "1")


def _parse_optional_float(value: str) -> Optional[float]:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def _parse_optional_int(value: str) -> Optional[int]:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def _map_type(type_str: str) -> FieldType:
    """Map a CSV type string to a CanonicalFieldType.

    The mapping is intentionally open-ended: unrecognised type strings are
    preserved as-is so adapters can introduce new types (AC-03 / RL-03).
    """
    t = type_str.strip().lower() if type_str else "string"
    if t == "object":
        return FieldType(category=FieldTypeCategory.OBJECT)
    if t.startswith("array"):
        # Support "array<string>" or just "array"
        inner_str = t[6:-1].strip() if t.startswith("array<") and t.endswith(">") else "string"
        return FieldType(
            category=FieldTypeCategory.ARRAY,
            items_type=FieldType(category=FieldTypeCategory.PRIMITIVE, primitive=inner_str),
        )
    # Normalise common aliases
    alias: Dict[str, str] = {
        "int": "integer",
        "float": "decimal",
        "number": "decimal",
        "bool": "boolean",
        "datetime": "datetime",
        "date": "date",
        "timestamp": "datetime",
        "varchar": "string",
        "text": "string",
        "nvarchar": "string",
        "char": "string",
    }
    primitive = alias.get(t, t)
    return FieldType(category=FieldTypeCategory.PRIMITIVE, primitive=primitive)


class CsvSchemaAdapter(InputSchemaAdapter):
    """Converts a CSV schema definition into a CanonicalSchema."""

    FORMAT_ID = "csv_schema"

    def __init__(self) -> None:
        self._meta = AdapterMetadata(
            adapter_id="csv_schema_adapter_v1",
            display_name="CSV Schema Adapter",
            version="1.0.0",
            supported_formats=[self.FORMAT_ID],
            description=(
                "Parses a CSV schema definition (one row per field) "
                "into the canonical schema model."
            ),
        )

    @property
    def metadata(self) -> AdapterMetadata:
        return self._meta

    def parse(
        self,
        raw_input: Any,
        schema_name: str = "",
        schema_version: str = "",
    ) -> CanonicalSchema:
        """Parse CSV schema input into a CanonicalSchema.

        Args:
            raw_input: Either a CSV string (str) or a list of row dicts.
            schema_name: Name for the resulting schema.
            schema_version: Version string for the resulting schema.

        Raises:
            AdapterParseError: If the input is not parseable or is missing
                               the required 'name' column.
        """
        rows = self._to_row_dicts(raw_input)
        if not rows:
            raise AdapterParseError("CSV schema input contains no data rows.")

        normalised = self._normalise_headers(rows)
        if _COL_NAME not in normalised[0]:
            raise AdapterParseError(
                f"CSV schema must contain a '{_COL_NAME}' column. "
                f"Found columns: {list(normalised[0].keys())}"
            )

        fields: List[CanonicalField] = []
        seen_paths: set = set()

        for row_idx, row in enumerate(normalised):
            raw_name = row.get(_COL_NAME, "").strip()
            if not raw_name:
                # Skip blank name rows silently
                continue

            parent = row.get(_COL_PARENT, "").strip()
            path = f"{parent}.{raw_name}" if parent else raw_name

            if path in seen_paths:
                raise AdapterParseError(
                    f"Duplicate field path {path!r} at row {row_idx + 2}."
                )
            seen_paths.add(path)

            is_required = _parse_bool(row.get(_COL_REQUIRED, "false"))
            type_str = row.get(_COL_TYPE, "string")
            field_type = _map_type(type_str)

            cardinality = Cardinality(
                min_occurs=1 if is_required else 0,
                max_occurs=None if field_type.category == FieldTypeCategory.ARRAY else 1,
            )

            enum_raw = row.get(_COL_ENUM, "").strip()
            enums = [v.strip() for v in enum_raw.split("|") if v.strip()] if enum_raw else None

            constraints = FieldConstraints(
                required=is_required,
                enums=enums,
                pattern=row.get(_COL_PATTERN, "").strip() or None,
                min_value=_parse_optional_float(row.get(_COL_MIN_VALUE, "")),
                max_value=_parse_optional_float(row.get(_COL_MAX_VALUE, "")),
                min_length=_parse_optional_int(row.get(_COL_MIN_LENGTH, "")),
                max_length=_parse_optional_int(row.get(_COL_MAX_LENGTH, "")),
            )

            terminology_refs: List[TerminologyReference] = []
            term_system = row.get(_COL_TERM_SYSTEM, "").strip()
            if term_system:
                terminology_refs.append(
                    TerminologyReference(
                        system=term_system,
                        code=row.get(_COL_TERM_CODE, "").strip() or None,
                    )
                )

            label = row.get(_COL_LABEL, "").strip() or raw_name
            description = row.get(_COL_DESCRIPTION, "").strip() or None

            fields.append(
                CanonicalField(
                    id=_stable_field_id(path),
                    path=path,
                    field_type=field_type,
                    cardinality=cardinality,
                    label=label,
                    description=description,
                    constraints=constraints,
                    terminology_references=terminology_refs,
                    metadata_tags={},
                )
            )

        return CanonicalSchema(
            id=str(uuid.uuid4()),
            name=schema_name,
            version=schema_version,
            fields=fields,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_row_dicts(raw_input: Any) -> List[Dict[str, str]]:
        """Convert raw_input to a list of str->str dicts."""
        if isinstance(raw_input, str):
            reader = csv.DictReader(io.StringIO(raw_input))
            try:
                return [dict(row) for row in reader]
            except csv.Error as exc:
                raise AdapterParseError(f"CSV parse error: {exc}") from exc
        if isinstance(raw_input, list):
            if not raw_input:
                return []
            if not isinstance(raw_input[0], dict):
                raise AdapterParseError(
                    "When raw_input is a list, each element must be a dict."
                )
            return [dict(row) for row in raw_input]
        raise AdapterParseError(
            f"CsvSchemaAdapter expects a str or list of dicts; received {type(raw_input).__name__}"
        )

    @staticmethod
    def _normalise_headers(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Lower-case and strip all header keys in place."""
        return [{k.strip().lower(): v for k, v in row.items()} for row in rows]
