# Functional Requirements (v1 POC) — Authoritative

## Scope statement
This document defines the functional requirements for v1. v1 must generate scripts for transformations but must not execute transformations. v1 must operate without patient-level payload data.

---

## FR-001 — Mapping Project Management
The system MUST allow users to create a Mapping Project that includes:
- project name, description, owner
- one or more source schemas
- exactly one selected target schema
- project status (Draft, Review, Approved, Published, Archived)
- version history for mappings
- sensitivity classification (default: Healthcare / Highly sensitive)

## FR-002 — Input Schema Import (v1)
The system MUST support importing schemas for the following input formats in v1:
- JSON Schema
- CSV schema (structured import: headers + types + constraints)
- FHIR profiles
- OpenEHR (archetypes/templates as applicable)
- SQL schemas (DDL or equivalent structured representation)
- Parquet schema
- OMOP CDM schema

The system MUST convert each input schema into a canonical internal representation.

## FR-003 — Output Schema Selection (v1)
The system MUST allow selection of target schema from:
- FHIR profiles (from an online registry; cached locally)
- OMOP CDM (from an online registry; cached locally)
- Custom formats uploaded by users in a structured way (stored in internal catalog)

## FR-004 — Extensible Format Support (critical)
The system MUST implement each schema format as a pluggable adapter.
The system MUST allow new input/output formats to be added in the future without changes to the core mapping engine.

## FR-005 — Canonical Schema Model
The canonical model MUST represent:
- field path and hierarchy
- data types
- cardinality
- constraints (required, enums, regex, min/max, etc.)
- descriptions/labels if present
- terminology references when available (e.g., FHIR code systems, OMOP concept hints)

## FR-006 — Suggested Mapping (schema-only)
The system MUST generate mapping suggestions without using real payload values, using:
- field name similarity (normalized match, synonyms where configured)
- structural similarity
- datatype compatibility
- cardinality compatibility
- terminology reference alignment where available

Each suggestion MUST include:
- suggested source field(s)
- confidence score
- explainability: reason(s) for suggestion
- warnings (type mismatch, required unmapped, etc.)

## FR-007 — Mapping Review UI
The system MUST provide a user interface that allows users to:
- view source schema and target schema side-by-side
- view suggested mappings
- accept/reject suggestions individually or in bulk
- manually map fields (select source field(s) for a target field)
- override mappings and remove mappings
- see validation results in real time

## FR-008 — Validation & Quality Gates
The system MUST validate:
- schema parsing success and report errors
- mapping completeness for required target fields
- type and cardinality compatibility
- constraint conflicts (warn or error based on policy)

Validation severity MUST be configurable per deployment/region policy (flexibility requirement).

## FR-009 — Transformation Script Generation (v1 core)
The system MUST generate deterministic transformation scripts/code based on the mapping.
Scripts MUST include:
- mapping project identifier
- mapping version identifier
- source/target schema identifiers + versions
- generation timestamp
- deterministic output (same inputs => same script)

The system MUST NOT execute transformations in v1.

## FR-010 — Export Artifacts
The system MUST allow exporting:
- the mapping definition (tool-native canonical format)
- the generated transformation script(s)

Exports MUST be portable between central and on-prem installations.

## FR-011 — Central + On-Prem Support
The system MUST be deployable:
- centrally hosted
- as a local on-prem installation
with feature parity for core mapping and script generation.

## FR-012 — Controlled Catalog Sync
The system MUST support controlled sync of schema catalogs between central and on-prem:
- configurable direction (pull/push/both)
- configurable scope (standards only, custom only, approved only)
- version-aware syncing
- audit logged

## FR-013 — Simulated Access Control (v1)
v1 MUST simulate access control (RBAC) to support development and demos.
The design MUST allow replacement with BankID/SITHS integrations in v2 (integration exists externally).

## FR-014 — Optional Approval Workflows
The system MUST support approval workflows for some mapping workflows but not all.
Approval requirements MUST be configurable per project/template/policy.

## FR-015 — Audit Logging (healthcare-grade)
The system MUST audit-log:
- schema imports/updates
- mapping edits
- approvals/publishing
- exports
with actor identity, timestamp, and before/after metadata.