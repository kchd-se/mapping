# Standards Bundle — Preloaded Schemas (Phase 5c)

This directory contains the bundled standard schemas that are automatically
registered into the catalog at API startup (`apps/api/state.py`).

---

## Bundled Standards

### OMOP CDM — version 5.4

| Schema Name                    | OMOP Table              | Fields |
|--------------------------------|-------------------------|--------|
| `OMOP_PERSON`                  | PERSON                  | 18     |
| `OMOP_CARE_SITE`               | CARE_SITE               | 6      |
| `OMOP_VISIT_OCCURRENCE`        | VISIT_OCCURRENCE        | 17     |
| `OMOP_PROCEDURE_OCCURRENCE`    | PROCEDURE_OCCURRENCE    | 16     |
| `OMOP_CONDITION_OCCURRENCE`    | CONDITION_OCCURRENCE    | 15     |
| `OMOP_DRUG_EXPOSURE`           | DRUG_EXPOSURE           | 20     |
| `OMOP_MEASUREMENT`             | MEASUREMENT             | 18     |
| `OMOP_OBSERVATION`             | OBSERVATION             | 16     |
| `OMOP_DEATH`                   | DEATH                   | 7      |
| `OMOP_PROVIDER`                | PROVIDER                | 13     |
| `OMOP_LOCATION`                | LOCATION                | 11     |

Source: [OHDSI OMOP CDM v5.4](https://ohdsi.github.io/CommonDataModel/cdm54.html)
Format ID: `omop_cdm`

### FHIR — version R4

| Schema Name              | FHIR Resource    | Fields |
|--------------------------|------------------|--------|
| `FHIR_Patient`           | Patient          | 15     |
| `FHIR_Organization`      | Organization     | 11     |
| `FHIR_Encounter`         | Encounter        | 16     |
| `FHIR_Condition`         | Condition        | 14     |
| `FHIR_Observation`       | Observation      | 18     |
| `FHIR_Procedure`         | Procedure        | 15     |
| `FHIR_Practitioner`      | Practitioner     | 10     |
| `FHIR_PractitionerRole`  | PractitionerRole | 11     |
| `FHIR_Location`          | Location         | 14     |

Source: [HL7 FHIR R4](https://hl7.org/fhir/R4/)
Format ID: `fhir_profile`

---

## Schema Metadata

All bundled schemas are registered with:
- `schema_type = standard`
- `approval_status = approved`
- `owner = system`
- `metadata_tags.source = bundled`
- `metadata_tags.standard` = the standard name (e.g. `"OMOP CDM"` or `"FHIR"`)
- `metadata_tags.standard_version` = version string (e.g. `"5.4"` or `"R4"`)

---

## Bundle Definition Format

Each JSON file in `omop/` or `fhir/` follows this schema:

```json
{
  "schema_name": "OMOP_PERSON",
  "format_id": "omop_cdm",
  "version": "5.4",
  "description": "Human-readable description of the schema.",
  "metadata_tags": {
    "source": "bundled",
    "standard": "OMOP CDM",
    "standard_version": "5.4",
    "table": "PERSON"
  },
  "fields": [
    {
      "path": "person.person_id",
      "label": "Person ID",
      "description": "Field description.",
      "type_category": "primitive",
      "type_primitive": "integer",
      "required": true
    }
  ]
}
```

### Field properties

| Property         | Required | Description |
|------------------|----------|-------------|
| `path`           | yes      | Dot-notation path: `table.column` for OMOP, `Resource.element` for FHIR |
| `label`          | no       | Human-readable display name |
| `description`    | no       | Brief field description |
| `type_category`  | no       | `"primitive"` (default), `"object"`, or `"array"` |
| `type_primitive` | no       | Scalar type: `"string"`, `"integer"`, `"boolean"`, `"date"`, `"datetime"`, `"decimal"` |
| `required`       | no       | `true` = NOT NULL / mandatory; `false` (default) = optional |

---

## Registration Logic

`loader.py` implements `register_all(catalog: CatalogService) -> int`:

1. Iterates all `*.json` files in `omop/` then `fhir/` (alphabetical order).
2. Converts each bundle definition to a `CanonicalSchema` using deterministic
   UUID5 identifiers derived from `(format_id, schema_name, version, field_path)`.
3. Calls `catalog.register_standard_schema()`.
4. Immediately calls `catalog.approve_schema()` to set `status=approved`.
5. If the schema was already registered (`SchemaVersionConflictError`), skips silently.

**Idempotency**: Calling `register_all()` multiple times is always safe.
The return value is the count of schemas newly registered (0 on subsequent calls).

**Deterministic IDs**: The same UUID5 namespace (`6ba7b810-9dad-11d1-80b4-00c04fd430c8`)
is used for all schema and field IDs. IDs are stable across restarts and environments.

---

## API Access

Bundled schemas appear immediately in:

- `GET /catalog/schemas` — all schemas
- `GET /catalog/schemas?type=standard` — filter to standard schemas only
- `GET /catalog/schemas?format=omop_cdm` — filter to OMOP schemas
- `GET /catalog/schemas?format=fhir_profile` — filter to FHIR schemas

---

## Extending the Bundle (Phase 5d)

To add a new standard schema:

1. Create a JSON file in the appropriate subdirectory:
   - `apps/api/standards/omop/` for OMOP tables
   - `apps/api/standards/fhir/` for FHIR resources
   - Or create a new subdirectory and add it to `_BUNDLE_DIRS` in `loader.py`

2. Follow the bundle definition format above.

3. Restart the API server. The new schema is automatically registered.

No Python code changes are required for adding schemas within existing formats.
To support a **new format** (e.g. `hl7_v2`, `cda`):
- Add a new subdirectory
- Add a `(_STANDARDS_DIR / "new_dir", "new_format_id")` entry to `_BUNDLE_DIRS`
  in `loader.py`

---

## Scope Constraints (v1)

- No live network calls — schemas are statically defined in JSON files.
- No terminology bindings — concept IDs are plain integers, no ValueSet references.
- No example data — structural schema only.
- Adapters (`omop_cdm_adapter`, `fhir_profile_adapter`) remain stubs;
  the loader bypasses them by using `register_standard_schema()` directly
  with pre-built `CanonicalSchema` objects.
