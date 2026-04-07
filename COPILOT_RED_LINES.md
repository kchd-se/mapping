# COPILOT RED LINES — Non-Negotiable Guardrails for AI Code Generation

> **Purpose:** This document defines absolute constraints that AI coding tools (GitHub Copilot, Factory AI, or any LLM-based code generator) MUST NOT violate when implementing the Healthcare Data Mapping Tool v1.
>
> **Enforcement:** Any generated code that violates a red line below MUST be rejected and regenerated.

---

## RL-01 — No Transformation Execution in v1

- MUST NOT execute transformation scripts in v1.
- MUST NOT include execution engines, runtime interpreters, or script runners in v1.
- Script generation is the v1 boundary. Execution belongs to v2.

## RL-02 — No Patient-Level Data Ingestion

- MUST NOT ingest, process, store, or require patient-level payload data in v1.
- v1 operates on **schema metadata only** (field names, types, cardinality, constraints).
- No sample patient data, no test fixtures containing PII, no data previews.

## RL-03 — No Hardcoded Standards, Schemas, or Policies

- MUST NOT hardcode FHIR resource definitions, OMOP table structures, or any standard schema into core logic.
- Standards MUST be loaded dynamically through adapters and catalogs.
- Validation severities MUST NOT be hardcoded; they MUST be policy-configurable.
- Approval workflow requirements MUST NOT be globally mandated; they MUST be configurable per project/policy.

## RL-04 — No Assumption of Uniform Regional Workflows

- MUST NOT assume all Swedish regions use the same schema structure, naming conventions, workflow, or approval process.
- MUST NOT embed region-specific logic in core modules.
- Regional variability MUST be handled through configuration and adapters.

## RL-05 — No Format-Specific Logic in Core

- Core mapping, suggestion, validation, and script generation engines MUST consume only the canonical model.
- MUST NOT parse JSON Schema, CSV, FHIR, SQL, or any format-specific structure outside of its designated adapter.
- If generated code bypasses the canonical model to access format-specific data, it violates this red line.

## RL-06 — No Vendor or Technology Lock-In

- MUST NOT hardcode a specific database engine, cloud provider, LLM provider, or identity provider.
- Storage, identity, and AI/LLM integrations MUST be abstracted behind interfaces.
- v1 uses simulated auth; the abstraction MUST allow replacement with BankID/SITHS in v2.

## RL-07 — No Code Forks for Deployment Modes

- Central and on-prem deployment MUST be the same codebase.
- Deployment mode differences MUST be expressed as configuration, not as separate code paths or branches.
- Mapping artifacts and scripts MUST be portable across deployments without modification.

## RL-08 — No Unsafe Parsing

- MUST NOT use `eval()`, `exec()`, or equivalent dynamic code execution to parse LLM responses or user input.
- LLM/AI outputs MUST be parsed using structured JSON parsing with schema validation.
- All external input (schema files, user input, API responses) MUST be validated before use.

## RL-09 — No Bypassing Audit Logging

- All auditable actions (import, edit, approve, publish, export, sync) MUST pass through the audit logging layer.
- MUST NOT create code paths that perform auditable actions without generating audit log entries.
- Audit logs MUST be append-only or tamper-evident by design.

## RL-10 — No Placeholder Core Logic Without Explicit Marking

- MUST NOT ship placeholder implementations as if they are complete.
- Any stub or placeholder MUST be explicitly marked with `TODO: placeholder for v2` or equivalent.
- Functional requirements marked as MUST in v1 MUST have real implementations, not stubs.

## RL-11 — No Hardcoded Configuration

- MUST NOT hardcode endpoints, file paths, schema locations, API keys, thresholds, or policy values.
- All configuration MUST be externalized through environment variables or configuration files.

## RL-12 — No Single-Suggestion Mapping

- The suggestion engine MUST return top-k candidates per target field with confidence scores.
- MUST NOT surface only a single suggestion per field without alternatives.
- Each suggestion MUST include explainability (human-readable reasons).

## RL-13 — No POC Architecture Inheritance

- MUST NOT replicate the POC's architecture, file structure, or technology stack by default.
- This is a greenfield build. Every technology and pattern choice MUST be justified against v1 constraints.
- SQL-only assumptions from the POC MUST NOT propagate into the new codebase.

## RL-14 — No Skipping Validation of Mapped Target Fields

- The system MUST validate that every mapped target field actually exists in the selected target schema.
- MUST NOT allow mapping to nonexistent target fields without raising a validation error.

## RL-15 — No Removing Flexibility for Convenience

- MUST NOT simplify architecture by removing adapter extensibility, policy configurability, or deployment portability.
- If an implementation shortcut would reduce regional flexibility, it MUST NOT be taken.
- Convenience MUST NOT override the flexibility-first design principle.

---

## Summary Matrix

| Red Line | One-Line Rule |
|---|---|
| RL-01 | No script execution in v1 |
| RL-02 | No patient data in v1 |
| RL-03 | No hardcoded standards or policies |
| RL-04 | No uniform-region assumptions |
| RL-05 | No format-specific logic in core |
| RL-06 | No vendor/technology lock-in |
| RL-07 | No code forks for deployment modes |
| RL-08 | No unsafe parsing (eval/exec) |
| RL-09 | No audit log bypass |
| RL-10 | No unlabeled placeholders |
| RL-11 | No hardcoded configuration |
| RL-12 | No single-suggestion-only mapping |
| RL-13 | No POC architecture inheritance |
| RL-14 | No unvalidated target field mappings |
| RL-15 | No sacrificing flexibility for convenience |
