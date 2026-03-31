# Architecture Constraints (Non-Negotiable)

## A. Flexibility is the primary design driver
The system MUST NOT enforce uniform workflows across Swedish regions.
The system MUST allow policy configuration per deployment/tenant/region for validation strictness, approvals, and catalog sync.

## B. Strict v1/v2 boundary
v1 MUST NOT execute transformations.
v1 MUST NOT require patient-level payload data.
v2 MAY add execution and data-assisted mapping; design must prepare but not include execution in v1.

## C. Extensibility / Plug-in model
All schema formats MUST be implemented via plug-in adapters:
- input schema adapters
- output schema adapters
- (optional) script generation targets

Core mapping logic MUST be format-agnostic (only use canonical model).

## D. Canonical model is the system contract
All downstream features MUST consume canonical schema representation:
- suggestions
- validation
- mapping UI
- script generation
No feature may parse format-specific schema directly.

## E. Security-by-design (healthcare)
Even in v1 POC:
- store only what is necessary (schemas, mappings, logs)
- avoid storing patient-level data
- encryption in transit and at rest must be supported
- audit logs must be tamper-evident or append-only in design

## F. Portability between central and on-prem
Mapping artifacts and scripts MUST be portable without modification.
Central vs on-prem differences MUST be configuration, not code forks.

## G. Online registries
FHIR profiles and OMOP CDM registries exist online.
The system MUST be able to:
- fetch and cache versions
- pin versions per project
- operate in restricted connectivity environments (on-prem), using cached registries

## H. Avoid vendor lock assumptions
Do not hardcode a single execution environment, storage engine, or identity provider.
Identity provider integration must be abstracted (simulated in v1; BankID/SITHS in v2).