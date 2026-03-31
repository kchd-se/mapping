# Deliverables & Repository Structure (What the AI must output)

## Required deliverables
1) A working application skeleton that compiles and runs locally.
2) Modular architecture with explicit boundaries:
   - core domain (canonical schema model, mapping model)
   - adapters (per input/output format)
   - suggestion engine (core, extensible)
   - validation engine (policy-configurable)
   - script generation engine (targets pluggable)
   - UI mapping editor
   - catalog + sync (central/on-prem configuration)
3) Documentation:
   - README: setup, run, build
   - Developer guide: adding a new format adapter
   - Security note: v1 constraints (schema-only, no data ingestion)

## Repo structure (recommended)
- /apps
  - /web (UI)
  - /api (backend service)
- /packages
  - /core (canonical model + mapping domain)
  - /adapters (format adapters, pluggable)
  - /suggestions (engine + explainability)
  - /validation (rules + policy config)
  - /script-gen (script generators)
  - /catalog (schema catalog + sync logic)
- /docs
  - architecture.md
  - adapters.md
  - script-generation.md

## Quality requirements
- No placeholder logic unless explicitly marked "TODO: placeholder for v2".
- Each major module must include at least basic unit tests.
- All configuration must be externalized (env/config files), not hardcoded.
- UI labels and internal documentation must be in English.
``