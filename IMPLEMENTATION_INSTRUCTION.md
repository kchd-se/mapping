# IMPLEMENTATION INSTRUCTION — Healthcare Data Mapping Tool v1

> **Document status:** Consolidated, authoritative implementation instruction.
> **Priority resolution order:** Product Intent > Architecture Constraints > Functional Requirements > Build Plan > POC Context.
> **Iteration posture:** GREENFIELD. No POC architecture, code, or technology is required. Reuse is optional and must be explicitly justified against the constraints below.

---

## 1. Purpose and Scope

### 1.1 One-Sentence Purpose

Build a flexible, schema-driven healthcare data mapping tool that imports multiple schema formats, suggests mappings via a canonical model, allows users to verify and edit mappings, and generates deterministic transformation scripts — without executing them in v1.

### 1.2 Target Users

Swedish healthcare regions with diverse local implementations and varying standards maturity. The tool MUST support high variability across regions without forcing workflow uniformity.

### 1.3 Deployment Model

The tool MUST be deployable and fully functional in both:

- **Central deployment** (hosted/managed environment for multiple regions).
- **On-prem deployment** (local installation with optional controlled sync to central).

Core mapping and script generation features MUST have full parity across both deployment modes. Differences between modes MUST be configuration, MUST NOT be code forks.

### 1.4 Version Scope Boundary (v1 vs v2)

| Capability | v1 (this build) | v2 (future) |
|---|---|---|
| Schema import (multiple formats via adapters) | MUST | Extend |
| Target schema selection (FHIR, OMOP, custom) | MUST | Extend |
| Canonical schema model | MUST | Extend |
| Schema-only mapping suggestions with explainability | MUST | Enhance with data-assisted mapping |
| Mapping review UI (verify, override, manual map) | MUST | Enhance |
| Validation with configurable severity | MUST | Extend |
| Transformation script generation (deterministic) | MUST | Extend with additional targets |
| Transformation script **execution** | **MUST NOT** | MAY add |
| Patient-level payload data ingestion | **MUST NOT** | MAY add (with safeguards) |
| Simulated access control (RBAC) | MUST | Replace with BankID/SITHS integration |
| Central + on-prem parity | MUST | Extend |
| Controlled catalog sync | MUST | Extend |
| Approval workflows (configurable, optional) | MUST | Extend |
| Audit logging (healthcare-grade) | MUST | Extend |
| Export of mapping artifacts + scripts | MUST | Extend |

**Hard boundary:** v1 MUST NOT include transformation execution. v1 MUST NOT require or ingest patient-level payload data. The architecture MUST prepare for v2 capabilities without including them in v1.

---

## 2. Hard Architectural Constraints

These constraints are non-negotiable and take precedence over all implementation convenience.

### AC-01 — Flexibility Is the Primary Design Driver

- The system MUST NOT enforce uniform workflows across Swedish regions.
- The system MUST allow per-deployment/tenant/region policy configuration for: validation strictness, approval requirements, catalog sync direction and scope.

### AC-02 — Strict v1/v2 Boundary

- v1 MUST NOT execute transformations.
- v1 MUST NOT require patient-level payload data.
- v2 features (execution, data-assisted mapping, enterprise auth) MUST be anticipated in architecture but MUST NOT be implemented in v1.

### AC-03 — Extensibility via Plug-In Adapters

- All schema formats MUST be implemented as pluggable adapters (input adapters, output adapters).
- Script generation targets MUST be pluggable.
- Adding a new schema format or script target MUST NOT require changes to core mapping logic.
- An adapter registry/discovery mechanism MUST exist.

### AC-04 — Canonical Model Is the System Contract

- All downstream features (suggestions, validation, mapping UI, script generation) MUST consume only the canonical schema representation.
- No feature MUST parse format-specific schema directly.
- The canonical model is the single internal contract between adapters and the core domain.

### AC-05 — Security-by-Design (Healthcare)

- v1 MUST store only what is necessary: schemas, mappings, audit logs, scripts.
- v1 MUST NOT store patient-level data.
- Encryption in transit and at rest MUST be supported (configuration hooks at minimum in v1).
- Audit logs MUST be tamper-evident or append-only in design.
- Audit logging MUST NOT be bypassable by normal application flows.

### AC-06 — Portability Between Central and On-Prem

- Mapping artifacts and scripts MUST be portable between central and on-prem without modification.
- Central vs on-prem differences MUST be expressed as configuration only.

### AC-07 — Online Registry Support with Offline Fallback

- The system MUST fetch and cache FHIR profiles and OMOP CDM schemas from online registries.
- The system MUST support version pinning per project.
- The system MUST operate in restricted-connectivity environments using cached registries (on-prem requirement).

### AC-08 — No Vendor Lock-In Assumptions

- MUST NOT hardcode a single execution environment, storage engine, or identity provider.
- Identity provider integration MUST be abstracted (simulated in v1; BankID/SITHS in v2).

### AC-09 — Greenfield Posture

- This is a greenfield implementation. The POC codebase MUST NOT be a dependency.
- POC technologies (Streamlit, LangChain, FAISS, regex parsing, etc.) are NOT requirements.
- Individual POC technologies MAY be reused only if explicitly justified against the constraints in this document.
- The POC's SQL-only focus MUST NOT be replicated; SQL is one adapter among many.

---

## 3. Functional Requirements (v1)

### FR-001 — Mapping Project Management

The system MUST allow users to create and manage a Mapping Project containing:

- Project name, description, owner.
- One or more source schemas.
- Exactly one selected target schema.
- Project status lifecycle: Draft → Review → Approved → Published → Archived.
- Version history for mappings.
- Sensitivity classification (default: Healthcare / Highly sensitive).

### FR-002 — Input Schema Import

The system MUST support importing schemas in the following formats in v1:

| Format | Notes |
|---|---|
| JSON Schema | Standard JSON Schema files |
| CSV schema | Structured import: headers + types + constraints |
| FHIR profiles | From online registry or local cache |
| OpenEHR | Archetypes/templates as applicable |
| SQL schemas | DDL or equivalent structured representation |
| Parquet schema | Parquet file metadata |
| OMOP CDM schema | From online registry or local cache |

Each imported schema MUST be converted into the canonical internal representation via a format-specific adapter.

### FR-003 — Output Schema Selection

The system MUST allow selection of a target schema from:

- **FHIR profiles** — fetched from an online registry, cached locally.
- **OMOP CDM** — fetched from an online registry, cached locally.
- **Custom formats** — uploaded by users in a structured way, stored in the internal catalog.

### FR-004 — Extensible Format Support

- Each schema format MUST be implemented as a pluggable adapter.
- New input/output formats MUST be addable without changes to the core mapping engine.
- An adapter contract (interface) MUST be defined and enforced via tests.

### FR-005 — Canonical Schema Model

The canonical model MUST represent:

- **id** — stable identifier.
- **path** — string, hierarchical (e.g., `Patient.name.given`).
- **label** — optional display label.
- **description** — optional human-readable description.
- **type** — primitive/object/array with specifics.
- **cardinality** — min/max occurrence.
- **constraints** — required, enums, regex, min/max range, etc.
- **terminology references** — optional (e.g., FHIR code systems, OMOP concept hints).
- **metadata tags** — domain, sensitivity classification, etc.

### FR-006 — Mapping Rule Model

A mapping rule MUST include:

- **targetFieldId** — reference to canonical target field.
- **sourceFieldIds** — one or many source field references.
- **transform** — optional transformation hint (v1: structure must exist; minimal logic).
- **defaultValue** — optional.
- **constantValue** — optional.
- **notes/justification** — optional free-text.

### FR-007 — Suggested Mapping (Schema-Only)

The system MUST generate mapping suggestions without using real payload data.

Suggestion strategies MUST include:

- Field name similarity (normalized match, synonym dictionaries where configured).
- Structural similarity (hierarchy position).
- Data type compatibility.
- Cardinality compatibility.
- Terminology reference alignment (where available).

Each suggestion MUST include:

- Suggested source field(s).
- Confidence score (numeric).
- Explainability: human-readable reason(s) for the suggestion.
- Warnings: type mismatch, required field unmapped, cardinality conflict, etc.

The system MUST surface top-k candidate matches per target field (not just the single best match).

### FR-008 — Mapping Review UI

The system MUST provide a user interface that allows users to:

- View source and target schemas side-by-side.
- Browse schema hierarchies.
- View suggested mappings with confidence scores and explanations.
- Accept/reject suggestions individually or in bulk.
- Manually map fields (select source field(s) for a target field).
- Override existing mappings and remove mappings.
- Add free-text comments/notes per mapping.
- See validation results in real time.
- Search and filter fields in large schemas.

### FR-009 — Validation and Quality Gates

The system MUST validate:

- Schema parsing success (report errors clearly).
- Mapping completeness for required target fields.
- Type compatibility between mapped source and target fields.
- Cardinality compatibility.
- Constraint conflicts (warn or error based on policy).
- Mapped target fields actually exist in the chosen target schema.

Validation severity MUST be configurable per deployment/region/project policy.

### FR-010 — Transformation Script Generation

The system MUST generate deterministic transformation scripts based on the finalized mapping.

Generated scripts MUST include metadata:

- Mapping project identifier.
- Mapping version identifier.
- Source/target schema identifiers + versions.
- Generation timestamp.

Determinism guarantee: identical inputs MUST produce identical script output.

The script generator interface MUST be pluggable (multiple target formats possible).

At least one working script generator target MUST be delivered in v1.

**The system MUST NOT execute transformation scripts in v1.**

### FR-011 — Export Artifacts

The system MUST allow exporting:

- The mapping definition in a tool-native canonical format.
- The generated transformation script(s).

Exports MUST be portable between central and on-prem installations without modification.

### FR-012 — Controlled Catalog Sync

The system MUST support controlled synchronization of schema catalogs between central and on-prem deployments:

- Configurable sync direction (pull/push/both).
- Configurable scope (standards only, custom only, approved only).
- Version-aware syncing.
- Audit logged.

### FR-013 — Simulated Access Control (v1)

v1 MUST implement simulated RBAC sufficient for development and demos.

The auth abstraction MUST be designed so that BankID/SITHS integration can replace it in v2 without refactoring core logic.

### FR-014 — Configurable Approval Workflows

- The system MUST support optional approval workflows for mapping projects.
- Approval requirements MUST be configurable per project, template, or policy.
- Not all projects require approval; this MUST NOT be globally mandated.

### FR-015 — Audit Logging (Healthcare-Grade)

The system MUST audit-log the following actions:

- Schema imports and updates.
- Mapping edits (with before/after metadata).
- Approvals and publishing events.
- Exports.
- Catalog sync actions.

Each log entry MUST include: actor identity, timestamp, action type, and before/after metadata where applicable.

Audit logs MUST be append-only or tamper-evident in design.

---

## 4. Non-Functional Requirements

### NFR-01 — Security

- No patient-level data ingestion in v1.
- Encryption in transit and at rest MUST be configurable.
- Simulated auth in v1; abstracted for real auth in v2.
- Audit logs MUST NOT be bypassable or mutable through normal application flows.
- Safe structured parsing for any LLM/AI responses (JSON schema validation, not `eval()` or similar).

### NFR-02 — Flexibility and Regional Variability

- Policy configuration per deployment/tenant/region.
- No assumption of uniform regional workflows, naming, or schema structures.
- Multi-language robustness: Swedish/English schema names; Å/Ä/Ö normalization.
- UI language MUST be English; Swedish schema content MUST be supported.

### NFR-03 — Portability

- Mapping artifacts and scripts portable between deployments without modification.
- No code forks for central vs on-prem.
- Restricted-connectivity operation via cached registries.

### NFR-04 — Usability for Large Schemas

- UI MUST support search/filter for fields in large schemas.
- Efficient rendering for schemas with hundreds of fields.
- Clear, real-time validation feedback.

### NFR-05 — Determinism and Auditability

- Script generation MUST be deterministic (same mapping → same script, every time).
- All user actions on mappings and approvals MUST be auditable.
- Mapping artifacts MUST be versioned.

### NFR-06 — Testability

- Each major module MUST include unit tests.
- Adapter contract tests (parse → canonical model).
- Suggestion engine tests (name/type matching).
- Validation engine tests (required unmapped, type mismatch, cardinality mismatch).
- Script generation determinism tests (same input → same output).
- Artifact portability tests (export/import mapping between deployments).

### NFR-07 — Configuration Externalization

- All configuration MUST be externalized (environment variables, config files).
- No hardcoded values for standards, schema paths, endpoints, or policies.

---

## 5. Modular Component Responsibilities

### 5.1 Core Domain (`/packages/core`)

- Canonical schema model (format-agnostic field representation).
- Mapping model (mapping rules, versions, project lifecycle).
- Mapping artifact serialization (tool-native portable format).
- Audit event model.
- Project model with status lifecycle (Draft → Review → Approved → Published → Archived).

### 5.2 Adapters (`/packages/adapters`)

- Adapter interface contract (input adapter, output adapter).
- Adapter registry/discovery mechanism.
- Reference adapters for v1: JSON Schema, CSV schema, FHIR profiles, OpenEHR, SQL DDL, Parquet, OMOP CDM.
- Each adapter: format-specific parsing → canonical model conversion.
- Adapter contract enforced via shared test suite.

### 5.3 Suggestion Engine (`/packages/suggestions`)

- Schema-only suggestion logic (no payload data).
- Strategies: field name similarity, structural similarity, type compatibility, cardinality compatibility, terminology alignment.
- Top-k candidate generation with confidence scoring.
- Explainability: human-readable reasons per suggestion.
- Warning generation (type mismatch, unmapped required fields, etc.).
- Extensible: new strategies addable.

### 5.4 Validation Engine (`/packages/validation`)

- Validation rules: schema parse success, mapping completeness, type compatibility, cardinality compatibility, constraint conflicts, target field existence.
- Policy-configurable severity per rule (error/warning/info).
- Policy configuration per deployment/region/project.

### 5.5 Script Generation Engine (`/packages/script-gen`)

- Pluggable script generator interface.
- At least one working generator target in v1.
- Deterministic output guarantee.
- Script metadata injection (project ID, mapping version, schema versions, timestamp).

### 5.6 Catalog and Sync (`/packages/catalog`)

- Internal catalog for custom schemas (upload, validate, store).
- External source caching for FHIR and OMOP registries.
- Version pinning per project.
- Controlled sync policy model (direction, scope, version-aware).
- Offline operation support (cached registries for on-prem).
- Audit logging for all sync actions.

### 5.7 API Backend (`/apps/api`)

- REST API exposing all core capabilities.
- Auth abstraction layer (simulated RBAC in v1).
- Approval workflow endpoints (configurable per project/policy).
- Audit log endpoints.

### 5.8 Web UI (`/apps/web`)

- Schema browser (hierarchical, searchable).
- Side-by-side source/target schema view.
- Mapping table (target-centric).
- Suggestion display with confidence, explanations, and warnings.
- Accept/reject/override/manual-map interactions.
- Validation feedback (real-time).
- Export controls (mapping artifact + scripts).
- Project management (create, status lifecycle, version history).

---

## 6. Repository Structure

```
/
├── apps/
│   ├── web/                    # UI application
│   └── api/                    # Backend API service
├── packages/
│   ├── core/                   # Canonical model, mapping model, project model, audit model
│   ├── adapters/               # Format adapters (pluggable)
│   ├── suggestions/            # Suggestion engine + explainability
│   ├── validation/             # Validation rules + policy configuration
│   ├── script-gen/             # Script generators (pluggable)
│   └── catalog/                # Schema catalog + sync logic
├── docs/
│   ├── architecture.md
│   ├── adapters.md             # "How to add a new adapter" guide
│   └── script-generation.md
├── README.md                   # Setup, run, build instructions
└── [config files]              # Externalized configuration
```

---

## 7. Build Phases (Incremental AI-Assisted Implementation)

Each phase MUST produce compiling code with tests before proceeding to the next phase.

### Phase 1 — Core Domain Model

**Deliver:**

- Canonical schema model (all fields per FR-005).
- Mapping rule model (all fields per FR-006).
- Mapping project model with status lifecycle (FR-001).
- Mapping version model.
- Audit event model.
- Serialization format for mapping artifact (tool-native, portable).
- Unit tests for all models.

### Phase 2 — Adapter Framework + Reference Adapters

**Deliver:**

- Adapter interface contract (input adapter, output adapter).
- Adapter registry/discovery mechanism.
- Working adapters: JSON Schema, CSV schema.
- Stub/partial adapters: FHIR profile, OMOP CDM, SQL DDL, OpenEHR, Parquet.
- Adapter contract test suite (parse → canonical model for each adapter).

### Phase 3 — Catalog, Version Pinning, and Sync

**Deliver:**

- Internal catalog for custom schemas (upload + validate).
- External source caching for FHIR and OMOP registries.
- Version pinning per project.
- Controlled sync policy model (direction, scope, versioning).
- Offline fallback using cached registries.
- Audit events for sync actions.
- Unit tests.

### Phase 4 — Suggestion and Validation Engines

**Deliver:**

- Suggestion engine consuming canonical model only.
- Top-k candidate generation with confidence scoring.
- Explainability output per suggestion.
- Validation engine with configurable severity per rule/policy.
- Validation rules: completeness, type compatibility, cardinality, constraint conflicts, target field existence.
- Unit tests for common scenarios (type mismatch, cardinality mismatch, required unmapped, name similarity ranking).

### Phase 5 — Mapping Editor UI

**Deliver:**

- Schema browser (hierarchical, searchable, filterable).
- Side-by-side source/target schema view.
- Mapping table view (target-centric).
- Accept/reject/override suggestion interactions.
- Manual mapping actions.
- Validation feedback in UI (real-time).
- Search/filter for large schemas.

### Phase 6 — Script Generation Engine

**Deliver:**

- Pluggable script generator interface.
- At least one working generator target (target format to be determined at implementation time).
- Deterministic generation guarantee (verified by test).
- Export mapping artifact + generated script.
- Unit tests including determinism test.

### Phase 7 — Central vs On-Prem Configuration Modes

**Deliver:**

- Deployment mode configuration flags.
- Verification that all artifacts are portable across modes.
- Verification that restricted-connectivity operation works (cached registries).
- No code forks — configuration only.

### Phase 8 — Approval Workflows and Governance Toggles

**Deliver:**

- Configurable approval workflows (enabled per project/policy, not globally mandated).
- API and minimal UI support for approvals.
- Audit logging for approval and publish actions.
- Unit tests.

---

## 8. Definition of Done (v1)

### Functional DoD

- [ ] Import at least: JSON Schema, CSV schema, OMOP CDM schema.
- [ ] Select target schema from: FHIR, OMOP, custom catalog.
- [ ] Produce mapping suggestions with confidence scores and explainability.
- [ ] Allow UI verification, manual overrides, and comments.
- [ ] Validate mappings with configurable severity.
- [ ] Generate deterministic transformation scripts (no execution).
- [ ] Export mapping artifact + scripts.
- [ ] Work in both central and on-prem configuration modes.
- [ ] Support controlled catalog sync (standards + custom, policy-driven).
- [ ] Audit-log key actions (import, edit, export, approvals, sync).

### Security DoD

- [ ] No patient-level data ingestion.
- [ ] Encryption configuration hooks exist.
- [ ] Audit logging present and not bypassable.
- [ ] No unsafe parsing (no `eval()`, no unvalidated LLM output).

### Testing DoD

- [ ] Adapter contract tests (parse → canonical model).
- [ ] Suggestion engine tests (name/type matching, top-k ranking).
- [ ] Validation engine tests (required unmapped, type mismatch, cardinality mismatch).
- [ ] Script generation determinism test (same input → same output).
- [ ] Artifact portability test (export/import mapping between deployments).

### Documentation DoD

- [ ] README with setup and run instructions.
- [ ] "How to add a new adapter" developer guide.
- [ ] v1/v2 boundary documented clearly.
- [ ] Security note: v1 constraints (schema-only, no data ingestion).

---

## 9. Glossary

| Term | Definition |
|---|---|
| **Schema Adapter** | A pluggable module that converts a format-specific schema into the canonical model (input adapter) or from canonical to a format (output adapter). |
| **Canonical Schema Model** | The format-agnostic internal representation of schema fields, types, cardinality, constraints, and metadata. The single contract between adapters and core logic. |
| **Mapping Artifact** | A versioned, portable mapping definition (in tool-native format) exportable between deployments. |
| **Mapping Rule** | A single source-to-target field mapping with optional transform, default/constant values, and justification. |
| **Script Generator** | A pluggable module that converts a mapping artifact into a deterministic transformation script in a target language/format. |
| **Central Deployment** | A hosted/managed environment where multiple regions access the tool. |
| **On-Prem Deployment** | A local installation operated by a single region, with optional controlled sync to central. |
| **Controlled Sync** | Policy-driven, version-aware, audit-logged synchronization of schema catalogs between central and on-prem deployments. |
| **Mapping Project** | The top-level organizational unit containing source schemas, a target schema, mapping rules, versions, status, and audit history. |
| **Validation Gate** | A configurable validation checkpoint that enforces mapping quality rules with policy-driven severity levels. |

---

## 10. POC Lessons Learned (Reference Only)

The following lessons from the existing POC inform this build but do not constrain it:

### Validated Patterns (preserve as principles)

- Retrieval-augmented constraint of candidate targets reduces hallucinations in AI-assisted mapping.
- Human-in-the-loop mapping with override, comment, and audit trail is essential.
- Deterministic, versioned mapping artifacts and scripts are critical for healthcare governance.
- Multi-language robustness (Swedish/English naming, Å/Ä/Ö normalization) is required.

### Known Risks to Eliminate

- LLM hallucination of target field names → MUST validate mapped fields exist in target schema.
- Single-suggestion-per-field → MUST surface top-k candidates with confidence scores.
- Raw text embeddings only → MUST persist and use structured schema metadata.
- Unsafe parsing (`eval()`) → MUST use structured JSON parsing with schema validation.
- Fragile regex-based parsing → MUST use proper parsers per format (adapters).
- SQL-only assumptions → MUST generalize to canonical model + multiple adapters.

### Technologies NOT Required

The following POC technologies are explicitly not required: Streamlit, LangChain, FAISS, regex-based SQL parsing, pandas-based persistence, CSV/Excel storage. Any may be used only if explicitly justified against v1 constraints.
