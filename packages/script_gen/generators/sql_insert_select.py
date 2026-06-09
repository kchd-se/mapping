"""SQL INSERT … SELECT transformation script generator.

Produces a deterministic SQL script that describes how to move data from
source tables/columns to OMOP-style target tables.  The script is a
*description* — it is NOT executed in v1 (RL-01).

Design decisions
----------------
* **Schema-driven, not OMOP-hardcoded**: the generator reads column names
  from the canonical field `path` attribute.  The path convention is
  ``table.column`` (or just ``column`` for flat layouts).  This means the
  same generator works for any tabular target schema loaded through the
  catalog — OMOP, regional variants, custom tables — without any
  format-specific logic in the core (RL-03, RL-05).

* **Determinism**:
  - Fields in every clause are sorted lexicographically by target path.
  - No timestamps in the body; only in the metadata header comment block.
  - The header uses fixed values from the artifact/schema objects.
  - ``sort_keys=True`` in any JSON serialisation (none used here).
  - Floating-point values are never emitted.

* **TransformKind handling**:
  - DIRECT / DEFAULT → ``source_col``
  - CONSTANT          → literal ``'<constant_value>'``
  - CONCATENATE       → ``CONCAT(col1, col2, ...)``
  - SPLIT             → ``SPLIT_PART(col, ' ', 1)`` placeholder comment
  - LOOKUP            → ``/* LOOKUP: <expression> */ source_col``
  - CUSTOM            → ``/* CUSTOM: <expression> */ source_col``

* **Unmapped required fields**: rendered as ``NULL  -- UNMAPPED (required)``
  so validation failures are visible in the script.
* **Unmapped optional fields**: excluded from the SELECT (not even commented),
  keeping the script minimal.
"""

from __future__ import annotations

import textwrap
from typing import Dict, List, Optional

from packages.core.models.canonical_schema import CanonicalField, CanonicalSchema
from packages.core.models.mapping_rule import MappingRule, TransformKind
from packages.core.serialization.artifact import MappingArtifact
from packages.script_gen.models import GeneratedScript

_GENERATOR_ID = "sql_insert_select_v1"
_GENERATOR_VERSION = "1.0.0"

_V1_NOTICE = "Generated script – execution not supported in v1"

_HEADER_TEMPLATE = """\
-- =============================================================================
-- {notice}
-- =============================================================================
-- project_id          : {project_id}
-- mapping_version     : {mapping_version}
-- source_schema_id    : {source_schema_id}
-- source_schema_ver   : {source_schema_ver}
-- target_schema_id    : {target_schema_id}
-- target_schema_ver   : {target_schema_ver}
-- generator_id        : {generator_id}
-- generator_version   : {generator_version}
-- =============================================================================
"""


def _source_table(schema: CanonicalSchema) -> str:
    """Derive a stable source table name from a schema name."""
    return schema.name.lower().replace(" ", "_") or "source_table"


def _target_table(path: str) -> str:
    """Extract table name from a dotted path (table.column → table)."""
    parts = path.split(".", 1)
    return parts[0] if len(parts) == 2 else "target_table"


def _col(path: str) -> str:
    """Extract column name from a dotted path (table.column → column)."""
    parts = path.split(".", 1)
    return parts[-1]


def _render_source_expr(
    rule: MappingRule,
    source_path_by_id: Dict[str, str],
    target_col: str,
) -> str:
    """Render the SQL expression for the source side of one mapping rule.

    Returns a SQL fragment (no trailing comma or alias).
    """
    kind = rule.transform.kind

    # CONSTANT — emit a literal value, no source column needed.
    if kind == TransformKind.CONSTANT:
        val = rule.constant_value or ""
        return f"'{val}'"

    # Resolve source field paths from IDs.
    src_cols = [
        _col(source_path_by_id.get(fid, fid))
        for fid in sorted(rule.source_field_ids)  # sorted for determinism
    ]

    if not src_cols:
        return "NULL  -- no source field mapped"

    if kind == TransformKind.DIRECT or kind == TransformKind.DEFAULT:
        expr = src_cols[0]
        if kind == TransformKind.DEFAULT and rule.default_value is not None:
            expr = f"COALESCE({src_cols[0]}, '{rule.default_value}')"
        return expr

    if kind == TransformKind.CONCATENATE:
        concat_args = ", ".join(src_cols)
        return f"CONCAT({concat_args})"

    if kind == TransformKind.SPLIT:
        hint = rule.transform.expression or "separator, part_index"
        return f"SPLIT_PART({src_cols[0]}, {hint})  /* SPLIT */"

    if kind == TransformKind.LOOKUP:
        hint = rule.transform.expression or "lookup expression"
        return f"/* LOOKUP: {hint} */ {src_cols[0]}"

    if kind == TransformKind.CUSTOM:
        hint = rule.transform.expression or "custom expression"
        return f"/* CUSTOM: {hint} */ {src_cols[0]}"

    # Fallback — unknown kind, emit source column with a warning comment.
    return f"/* unknown transform: {kind} */ {src_cols[0]}"


class SqlInsertSelectGenerator:
    """Generates a SQL INSERT … SELECT script from a mapping artifact.

    The output groups rules by target table (derived from field path) and
    emits one INSERT … SELECT block per target table.  Fields within each
    block are sorted by target column name for deterministic ordering.
    """

    generator_id: str = _GENERATOR_ID
    generator_version: str = _GENERATOR_VERSION

    def generate(
        self,
        artifact: MappingArtifact,
        source_schema: CanonicalSchema,
        target_schema: CanonicalSchema,
    ) -> GeneratedScript:
        """Generate a deterministic SQL script.

        Same inputs always produce byte-identical output (see module docstring
        for the full determinism strategy).
        """
        project = artifact.project
        version = artifact.version

        # Build lookup maps for fast resolution by field ID.
        source_path_by_id: Dict[str, str] = {
            f.id: f.path for f in source_schema.fields
        }
        target_field_by_id: Dict[str, CanonicalField] = {
            f.id: f for f in target_schema.fields
        }

        # Index rules by target_field_id for O(1) lookup.
        rule_by_target: Dict[str, MappingRule] = {
            r.target_field_id: r for r in sorted(
                version.rules, key=lambda r: r.target_field_id
            )
        }

        # Group target fields by table (prefix before first ".").
        # Sort both groups and fields within groups for determinism.
        tables: Dict[str, List[CanonicalField]] = {}
        for f in sorted(target_schema.fields, key=lambda f: f.path):
            tbl = _target_table(f.path)
            tables.setdefault(tbl, []).append(f)

        src_table = _source_table(source_schema)

        header = _HEADER_TEMPLATE.format(
            notice=_V1_NOTICE,
            project_id=project.id,
            mapping_version=version.version_label,
            source_schema_id=source_schema.id,
            source_schema_ver=source_schema.version or "—",
            target_schema_id=target_schema.id,
            target_schema_ver=target_schema.version or "—",
            generator_id=self.generator_id,
            generator_version=self.generator_version,
        )

        blocks: List[str] = [header]

        for tbl_name in sorted(tables):
            tbl_fields = tables[tbl_name]
            select_lines: List[str] = []

            for tf in tbl_fields:  # already sorted by path
                col = _col(tf.path)
                rule: Optional[MappingRule] = rule_by_target.get(tf.id)

                if rule is not None:
                    expr = _render_source_expr(rule, source_path_by_id, col)
                    note = f"  -- {rule.notes}" if rule.notes else ""
                    select_lines.append(f"    {expr} AS {col}{note}")
                elif tf.constraints.required:
                    select_lines.append(
                        f"    NULL AS {col}  -- UNMAPPED (required)"
                    )
                # Optional unmapped fields are omitted entirely.

            if not select_lines:
                continue

            col_list = ",\n".join(
                f"    {_col(tf.path)}"
                for tf in tbl_fields
                if rule_by_target.get(tf.id) is not None
                or tf.constraints.required
            )
            select_body = ",\n".join(select_lines)

            block = textwrap.dedent(f"""\
                INSERT INTO {tbl_name} (
                {col_list}
                )
                SELECT
                {select_body}
                FROM {src_table};
            """)
            blocks.append(block)

        script_text = "\n".join(blocks)

        metadata = {
            "generator_id": self.generator_id,
            "generator_version": self.generator_version,
            "notice": _V1_NOTICE,
            "project_id": project.id,
            "mapping_version": version.version_label,
            "source_schema_id": source_schema.id,
            "source_schema_ver": source_schema.version or "",
            "target_schema_id": target_schema.id,
            "target_schema_ver": target_schema.version or "",
        }

        return GeneratedScript(
            generator_id=self.generator_id,
            generator_version=self.generator_version,
            script_text=script_text,
            metadata=metadata,
        )
