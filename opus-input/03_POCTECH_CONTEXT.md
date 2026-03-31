# Existing POC Technical Context (Inspiration; Optional Reuse Only)

## IMPORTANT: Greenfield rebuild posture (non-negotiable)
This document describes the existing Proof of Concept (POC) to provide inspiration and validated learnings.  
**The next iteration is a greenfield implementation** and MUST NOT depend on the POC’s codebase or require any of its components to function.

### Reuse policy (explicit)
- Reuse of individual technologies or patterns from the POC is **NOT required**.
- Reuse is **allowed** only if it clearly supports the new tool’s primary requirements:
  - extreme flexibility across Swedish regions
  - canonical schema + adapter architecture
  - deterministic, portable mapping artifacts and script outputs
  - central + on-prem parity with controlled sync
  - healthcare-grade governance (auditability, validation gates)
- Any reused component must be evaluated against known POC limitations and must not reintroduce them.

**Anti-requirement:** Do not replicate the POC’s architecture simply because it exists.

---

## 1) POC summary (what it proved, not what to copy)
The POC is an AI-assisted data model harmonisation tool for Swedish healthcare. It demonstrates how Generative AI can accelerate onboarding of heterogeneous regional schemas into a shared standardized model by:
- parsing a regional SQL schema into structured metadata,
- suggesting field-level mappings via retrieval + LLM resolution,
- enabling human verification and override,
- persisting mapping decisions,
- generating SQL transformation scripts.

### What the POC demonstrated successfully (validated learnings)
- Viable end-to-end workflow: schema ingest → mapping suggestions → user overrides → script generation.
- Effective AI pattern: retrieval narrows candidate space, reducing hallucination risk and improving relevance.
- Human-in-the-loop is essential: editable mapping grid, searchable dropdown overrides, field comments.
- Multi-language handling matters: Swedish/English schema names and normalization of Å/Ä/Ö.
- Determinism and traceability are critical in healthcare integration contexts.

### What NOT to infer from the POC
- The POC’s technology choices (Streamlit, LangChain, FAISS, regex parsing, etc.) are NOT requirements.
- The POC’s SQL-only focus is NOT a requirement for the next iteration (v1 supports multiple schema formats through adapters).
- The POC’s persistence approach (CSV/Excel) is NOT a requirement; only portability and versioning are.

---

## 2) POC core workflow (conceptual)
This describes how the POC worked conceptually. The next iteration may implement these steps differently.

### Step 1 — Schema Field Mapping
1. User selects a region.
2. Tool loads the region’s SQL schema and parses it into metadata (table name, fields, data types, PKs, FKs).
3. Tool uses a two-stage AI pipeline per field:
   - **Semantic retrieval:** vector search over standardized schema representations to find candidate target table(s).
   - **LLM match resolution:** LLM proposes the exact target field and flags transformation notes.
4. Suggestions are presented in an editable grid:
   - user overrides via dropdown of all `standard_table.field` options
   - user adds a free-text comment per field
5. Tool persists mappings per region; cross-region mapping can be exported to Excel.

### Step 2 — SQL Transformation Script Generation
1. Tool reads the saved mappings (including overrides and comments).
2. Tool generates SQL INSERT scripts per target table.
3. Transformation logic is incorporated when indicated by mapping comments.
4. SQL is displayed with syntax highlighting and line numbers.

---

## 3) POC technical stack (optional inspiration; not binding)
The POC used:
- UI: Streamlit (two-tab layout)
- LLM: Azure OpenAI GPT-4o
- Embeddings: Azure OpenAI text-embedding-3-large
- Vector DB: FAISS (local, pre-built)
- Orchestration: LangChain
- Schema parsing: custom regex-based SQL parser
- Data handling: pandas, openpyxl
- Config: `.env` via python-dotenv

### Reuse guidance
- These technologies may be reused only if they fit the new architecture constraints and do not reintroduce POC limitations.
- The next iteration is free to select different technologies and should prioritize modularity and extensibility.

---

## 4) Data domain (still relevant)
The standardized schema and regional schemas represent a hospital management domain with five core entities:
- **Hospital**: name, address, city, postcode, contact, category
- **Room/Ward**: linked to hospital, room number, type, capacity
- **Patient**: name, personal identity number (personnummer/SSN), birth date, gender, contact
- **Visit**: linked to patient and hospital, date, reason, type/status
- **Treatment**: linked to visit, type, date, notes, treating doctor

Regional schemas vary in naming (Swedish/English), structure, and granularity, but represent the same underlying domain concepts.

---

## 5) Known limitations and gaps (treat as risks to eliminate)
These issues should be treated as problems to solve, not behaviors to preserve:

### Correctness risks
- LLM occasionally hallucinated target field names not present in target tables.
- No formal validation step confirming mapped target fields exist in the target schema.
- Vector index stored embeddings of SQL text only, not structured schema metadata.
- UI surfaces only one suggestion per field (no top-k candidates with scores).

### Engineering/robustness gaps
- Regex SQL parser edge cases (e.g., REFERENCES/FOREIGN parsed incorrectly).
- Fragile handling of user manual overrides in pandas.
- Minimal handling of LLM failures (fallback string only).
- Unsafe parsing approach in places (e.g., `eval()` suggested; should be structured JSON parsing).
- Dependency list may be stale (`requirements.txt`).

---

## 6) What to preserve (principles and patterns only)
The next iteration SHOULD preserve these high-level principles:
- Retrieval-augmented constraint of candidate targets to reduce hallucinations.
- Human-in-the-loop mapping UI with override, comment, and audit trail.
- Deterministic, versioned mapping artifacts and script outputs.
- Multi-language robustness (Swedish/English naming; Å/Ä/Ö normalization).

Implementation details are not binding.

---

## 7) What must change (explicit rebuild goals)
The next iteration MUST:
- Implement formal validation gates ensuring:
  - mapped target fields exist in the chosen target schema,
  - type and cardinality compatibility are enforced (policy-configurable severities).
- Surface top-k candidate matches with confidence scores and explainability.
- Persist structured schema metadata for retrieval (not only raw text).
- Use safe structured parsing for LLM responses (JSON schema + json parsing).
- Improve parsing robustness (use proper parsers/adapters per format).
- Unify UI language to English (while supporting Swedish schema content).
- Generalize beyond SQL-only into canonical schema + adapter architecture.
- Prepare for central + on-prem parity and controlled catalog sync (policy-driven).

---

## 8) Non-functional expectations (derived from POC usage)
- Regional variability is high; flexibility is the primary design driver.
- UI must remain usable for large schemas: search/filter, efficient rendering, clear validation feedback.
- Outputs must be deterministic and auditable (healthcare governance).
- v1 must avoid patient-level data ingestion; persist only schemas, mappings, logs, and scripts.
- v1 simulated auth; v2 will integrate BankID/SITHS via external services.

---

## 9) Rebuild posture (guidance for AI code generation)
When generating the new system:
- Treat the POC as inspiration and lessons learned.
- Do not assume POC architecture, libraries, or code must be used.
- You may reuse individual technologies only when they clearly support the new requirements and architecture constraints.
- Do not bake in SQL-only assumptions; SQL is only one adapter among many.
- Prioritize modular adapters, canonical schema representation, validation gates, deterministic script generation, and portability.
``