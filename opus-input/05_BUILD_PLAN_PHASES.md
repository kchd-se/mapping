# Build Plan (AI Execution Phases)

## Rule for generation
The AI MUST implement the system incrementally, phase by phase.
Each phase must produce compiling code + tests before moving to next.

---

## Phase 1 — Core domain model
Deliver:
- canonical schema model
- mapping model + versioning model
- project model + status lifecycle
- audit event model
- serialization format for mapping artifact (tool-native)

---

## Phase 2 — Adapter framework + reference adapters
Deliver:
- adapter interfaces (input/output)
- JSON Schema adapter
- CSV schema adapter
- minimal FHIR profile adapter stub (or partial, depending on library availability)
- adapter registry/discovery mechanism
- tests for adapter contract

---

## Phase 3 — Catalog + version pinning + sync
Deliver:
- internal catalog for custom schemas (upload + validation)
- caching of online standards (FHIR, OMOP) as external sources
- controlled sync policy model and sync jobs
- audit events for sync actions

---

## Phase 4 — Suggestion + validation engines
Deliver:
- suggestion engine using canonical model only
- confidence scoring + explainability
- validation engine with policy-configurable severities
- unit tests for common mismatches (type, cardinality, required fields)

---

## Phase 5 — Mapping editor UI
Deliver:
- schema browser UI (side-by-side)
- mapping table view (target-centric)
- accept/reject suggestions
- manual mapping actions
- validation feedback in UI

---

## Phase 6 — Script generation engine (v1)
Deliver:
- pluggable script generator interface
- at least one working generator target (define target with you; e.g. SQL or tool-native DSL)
- deterministic generation guarantee
- export mapping + script

---

## Phase 7 — Central vs On-prem configuration modes
Deliver:
- deployment mode config flags
- ensure portability of artifacts
- ensure restricted connectivity works (cached registry usage)

---

## Phase 8 — Optional approvals + governance toggles
Deliver:
- configurable approval workflows (enabled for some projects/policies)
- minimal UI & API support
- audit logging for approvals and publish actions