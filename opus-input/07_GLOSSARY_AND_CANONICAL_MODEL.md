# Glossary & Canonical Model

## Glossary
- Schema Adapter: A plug-in module that converts a format-specific schema into the canonical model.
- Canonical Schema Model: Format-agnostic internal representation of fields, types, constraints.
- Mapping Artifact: A versioned mapping definition exportable between deployments.
- Script Generator: A plug-in module that converts mapping artifacts into transformation scripts/code.
- Central Deployment: Hosted/managed environment for regions to use.
- On-Prem Deployment: Local installation with optional controlled sync.

## Canonical Model (conceptual)
A canonical field must include:
- id (stable identifier)
- path (string, hierarchical)
- label (optional)
- description (optional)
- type (primitive/object/array + specifics)
- cardinality (min/max)
- constraints (required/enums/regex/range)
- terminology references (optional)
- metadata tags (domain, sensitivity, etc.)

## Mapping Rule (conceptual)
A mapping rule must include:
- targetFieldId
- sourceFieldIds (one or many)
- transform (optional; v1 minimal, but structure must exist)
- defaultValue (optional)
- constantValue (optional)
- notes/justification (optional)