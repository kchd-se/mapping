# Product Intent (Immutable)

## One-sentence purpose
Build a flexible, schema-driven healthcare data mapping tool that imports multiple schema formats, suggests mappings, allows users to verify/edit mappings, and generates deterministic transformation scripts (without executing them in v1).

## Target users
Swedish healthcare regions with diverse local implementations and standards maturity; the tool must support high variability without forced standardization.

## Deployment model
The tool must be usable both:
- from a central location (centrally hosted), and
- through local on-prem installations,
with consistent behavior and portable mapping artifacts.

## Version scope boundary
- v1 (POC): schema-only mapping; generates transformation scripts; does NOT execute transformations; simulated access control.
- v2: integrates into a larger ecosystem where scripts are executed by another tool (and potentially executed by this tool later); supports real data-based mapping and enterprise authentication (BankID/SITHS via existing services).

## Core success outcomes
- Users can import source schemas (multiple formats) and choose target schemas (FHIR, OMOP, custom).
- The system suggests mappings based on schemas only and provides explainability.
- Users can verify/override mappings with robust validation feedback.
- The system generates exportable scripts/artifacts usable downstream.
- New schema formats can be added without refactoring core logic.