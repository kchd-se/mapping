# Definition of Done (v1 POC)

## Functional DoD
- Import at least: JSON Schema, CSV schema, OMOP CDM schema
- Select target schema from: FHIR, OMOP, custom catalog
- Produce mapping suggestions with confidence and explainability
- Allow UI verification and manual overrides
- Validate mappings with configurable severity
- Generate deterministic scripts (no execution)
- Export mapping artifact + scripts
- Work in both central and on-prem configuration modes
- Support controlled catalog sync (standards + custom, policy-driven)
- Audit log key actions (import, edit, export, approvals)

## Security DoD (v1)
- No patient-level data ingestion required
- Encryption configuration hooks exist (even if simplified in POC)
- Audit logging is present and cannot be bypassed by normal flows

## Testing DoD
Minimum tests:
- adapter contract tests (parse => canonical model)
- suggestion engine tests (name/type matching)
- validation engine tests (required unmapped, type mismatch, cardinality mismatch)
- script generation determinism test (same input => same output)
- artifact portability test (export/import mapping config)

## Documentation DoD
- README with run instructions
- "How to add a new adapter" guide
- v1/v2 boundary explained clearly