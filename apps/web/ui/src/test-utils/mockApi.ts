import { vi, type Mock } from "vitest";
import type {
  CatalogSchemaResponse,
  CatalogVersionResponse,
  ExportResponse,
  MappingVersionResponse,
  ProjectResponse,
  ProjectSchemasResponse,
  SuggestionsResponse,
  ValidationResponse,
} from "@/api";

type MockRoute = {
  method: string;
  pattern: RegExp;
  response: unknown;
  status?: number;
};

let routes: MockRoute[] = [];

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    statusText: status === 200 ? "OK" : "Error",
    headers: { "content-type": "application/json" },
  });
}

export function setupFetchMock() {
  routes = [];
  const mockFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = (init?.method ?? "GET").toUpperCase();

    for (const route of routes) {
      if (route.method === method && route.pattern.test(url)) {
        return jsonResponse(route.response, route.status ?? 200);
      }
    }
    throw new Error(`Unmocked API call: ${method} ${url}`);
  }) as Mock;

  vi.stubGlobal("fetch", mockFetch);
  return mockFetch;
}

export function mockRoute(method: string, pattern: RegExp, response: unknown, status = 200) {
  routes.push({ method, pattern, response, status });
}

export const fixtures = {
  projects: (): ProjectResponse[] => [
    {
      id: "proj-001",
      name: "EHR Integration Pipeline",
      description: "Map source EHR to target standard",
      status: "draft",
      owner: "analyst-1",
      sensitivity: "healthcare_highly_sensitive",
      created_at: "2025-01-15T10:00:00Z",
    },
    {
      id: "proj-002",
      name: "Claims Data Migration",
      description: "Legacy claims to new format",
      status: "review",
      owner: "analyst-2",
      sensitivity: "healthcare_highly_sensitive",
      created_at: "2025-02-20T14:30:00Z",
    },
    {
      id: "proj-003",
      name: "Lab Results Mapping",
      description: null,
      status: "approved",
      owner: "analyst-1",
      sensitivity: "healthcare_highly_sensitive",
      created_at: "2025-03-01T09:00:00Z",
    },
    {
      id: "proj-004",
      name: "Pharmacy Records",
      description: "Pharmacy data transformation",
      status: "published",
      owner: "admin-1",
      sensitivity: "healthcare_highly_sensitive",
      created_at: "2025-03-10T16:00:00Z",
    },
    {
      id: "proj-005",
      name: "Retired Demographics Project",
      description: "Old demographics mapping",
      status: "archived",
      owner: "analyst-3",
      sensitivity: "healthcare_highly_sensitive",
      created_at: "2024-06-01T08:00:00Z",
    },
  ],

  schemas: (): ProjectSchemasResponse => ({
    project_id: "proj-001",
    source: {
      pin_id: "pin-src-001",
      schema_id: "src-schema-001",
      version_label: "v1.0",
      schema_name: "Source EHR Schema",
      format_id: "json_schema",
      field_count: 5,
    },
    target: {
      pin_id: "pin-tgt-001",
      schema_id: "tgt-schema-001",
      version_label: "v5.4",
      schema_name: "Target Standard Schema",
      format_id: "json_schema",
      field_count: 4,
    },
  }),

  suggestions: (): SuggestionsResponse => ({
    project_id: "proj-001",
    source_schema_id: "src-schema-001",
    target_schema_id: "tgt-schema-001",
    // source_fields lists ALL source schema fields — including ones with no AI candidates.
    source_fields: [
      { id: "src-account-id", path: "patient.avdelning" },
      { id: "src-birth-year", path: "patient.diagnosdatum" },
      { id: "src-dob", path: "patient.fodelsedatum" },
      { id: "src-patient-id", path: "patient.patientId" },
      { id: "src-mrn", path: "patient.personnummer" },
      { id: "src-gender", path: "patient.kon" },       // unmatched — no candidate
      { id: "src-address", path: "patient.adress" },   // unmatched — no candidate
    ],
    field_suggestions: [
      {
        target_field_id: "tgt-field-person-id",
        target_field_path: "person.person_id",
        candidates: [
          {
            source_field_ids: ["src-patient-id"],
            source_field_paths: ["patient.patientId"],
            confidence: 0.95,
            reasons: ["Exact name match after normalization"],
            warnings: [],
          },
          {
            source_field_ids: ["src-mrn"],
            source_field_paths: ["patient.personnummer"],
            confidence: 0.72,
            reasons: ["Both are identifier fields"],
            warnings: ["Different identifier schemes"],
          },
          {
            source_field_ids: ["src-account-id"],
            source_field_paths: ["patient.avdelning"],
            confidence: 0.45,
            reasons: ["Partial name overlap"],
            warnings: ["Low semantic similarity"],
          },
        ],
      },
      {
        target_field_id: "tgt-field-birth-date",
        target_field_path: "person.birth_datetime",
        candidates: [
          {
            source_field_ids: ["src-dob"],
            source_field_paths: ["patient.fodelsedatum"],
            confidence: 0.88,
            reasons: ["Date-of-birth semantic match"],
            warnings: [],
          },
          {
            source_field_ids: ["src-birth-year"],
            source_field_paths: ["patient.diagnosdatum"],
            confidence: 0.55,
            reasons: ["Partial date component"],
            warnings: ["Year-only; missing month and day"],
          },
        ],
      },
    ],
  }),

  mappingVersions: (): MappingVersionResponse[] => [
    {
      id: "mv-001",
      project_id: "proj-001",
      version_label: "Draft v1",
      created_at: "2025-04-01T12:00:00Z",
      rule_count: 2,
      notes: "Initial draft",
      rules: [
        {
          target_field_id: "tgt-field-person-id",
          source_field_ids: ["src-patient-id"],
          transform: { kind: "direct" },
          notes: null,
        },
        {
          target_field_id: "tgt-field-birth-date",
          source_field_ids: ["src-dob"],
          transform: { kind: "direct" },
          notes: null,
        },
      ],
    },
  ],

  validation: (): ValidationResponse => ({
    project_id: "proj-001",
    mapping_version_id: "mv-001",
    has_errors: true,
    error_count: 1,
    warning_count: 1,
    issues: [
      {
        rule_id: "REQUIRED_FIELD_UNMAPPED",
        severity: "error",
        message: "Required target field is not mapped to any source",
        affected_field_ids: ["tgt-field-person-id"],
        affected_field_paths: ["person.person_id"],
        remediation_hint: "Map a source identifier field to this target",
      },
      {
        rule_id: "TYPE_MISMATCH",
        severity: "warn",
        message: "Source and target field types differ",
        affected_field_ids: ["tgt-field-birth-date"],
        affected_field_paths: ["person.birth_datetime"],
        remediation_hint: "Add a type-cast transformation",
      },
      {
        rule_id: "NAMING_CONVENTION",
        severity: "info",
        message: "Field name does not follow target naming convention",
        affected_field_ids: ["tgt-field-gender"],
        affected_field_paths: ["person.gender_concept_id"],
        remediation_hint: null,
      },
    ],
  }),

  exportResult: (): ExportResponse => ({
    project_id: "proj-001",
    mapping_version_id: "mv-001",
    artifact_json: JSON.stringify(
      {
        version: "1.0",
        project_id: "proj-001",
        rules: [
          { target: "person.person_id", source: ["src-patient-id"] },
          { target: "person.birth_datetime", source: ["src-dob"] },
        ],
      },
      null,
      2,
    ),
    transformation_script:
      "# Generated script -- execution not supported in v1\n\ndef transform(record):\n    pass",
  }),

  catalogSchemas: (): CatalogSchemaResponse[] => [
    // Standard bundles — shown as one-click standard cards in the UI
    {
      id: "bundle-fhir-r4",
      name: "FHIR_R4",
      format_id: "fhir_profile",
      schema_type: "standard",
      approval_status: "approved",
      owner: "system",
      description: "Combined FHIR R4 standard — maps against Patient, Organization, and Encounter profiles.",
      latest_version_label: "R4",
      available_versions_count: 1,
      created_at: "2025-01-01T00:00:00Z",
      metadata_tags: {
        source: "bundled",
        standard: "FHIR",
        standard_version: "R4",
        bundle: "true",
        included_schemas: "FHIR_Patient,FHIR_Organization,FHIR_Encounter",
      },
    },
    {
      id: "bundle-omop-5-4",
      name: "OMOP_CDM_5_4",
      format_id: "omop_cdm",
      schema_type: "standard",
      approval_status: "approved",
      owner: "system",
      description: "Combined OMOP CDM 5.4 standard — maps against PERSON, CARE_SITE, VISIT_OCCURRENCE, and PROCEDURE_OCCURRENCE tables.",
      latest_version_label: "5.4",
      available_versions_count: 1,
      created_at: "2025-01-01T00:00:00Z",
      metadata_tags: {
        source: "bundled",
        standard: "OMOP CDM",
        standard_version: "5.4",
        bundle: "true",
        included_schemas: "OMOP_PERSON,OMOP_CARE_SITE,OMOP_VISIT_OCCURRENCE,OMOP_PROCEDURE_OCCURRENCE",
      },
    },
    // Individual schemas
    {
      id: "cat-001",
      name: "OMOP CDM Person",
      format_id: "omop_cdm",
      schema_type: "standard",
      approval_status: "approved",
      owner: "admin",
      description: "OMOP Common Data Model - Person table",
      latest_version_label: "v5.4",
      available_versions_count: 2,
      created_at: "2025-01-10T08:00:00Z",
      metadata_tags: { domain: "clinical" },
    },
    {
      id: "cat-002",
      name: "FHIR Patient R4",
      format_id: "fhir_r4",
      schema_type: "standard",
      approval_status: "approved",
      owner: "admin",
      description: "HL7 FHIR R4 Patient resource",
      latest_version_label: "r4",
      available_versions_count: 1,
      created_at: "2025-01-11T09:00:00Z",
      metadata_tags: {},
    },
    {
      id: "cat-003",
      name: "Custom Lab Schema",
      format_id: "json_schema",
      schema_type: "custom",
      approval_status: "draft",
      owner: "analyst-1",
      description: null,
      latest_version_label: "v1.0",
      available_versions_count: 1,
      created_at: "2025-02-01T10:00:00Z",
      metadata_tags: {},
    },
  ],

  catalogVersions: (schemaId: string): CatalogVersionResponse[] => [
    {
      id: `ver-${schemaId}-001`,
      schema_id: schemaId,
      version_label: "v5.4",
      created_at: "2025-01-10T08:00:00Z",
      checksum: "abc123def456abc123def456abc123def456abc123def456abc123def456abc123",
      notes: null,
    },
    {
      id: `ver-${schemaId}-002`,
      schema_id: schemaId,
      version_label: "v5.3",
      created_at: "2024-06-01T08:00:00Z",
      checksum: "bbb222ccc333bbb222ccc333bbb222ccc333bbb222ccc333bbb222ccc333bbb222",
      notes: "Previous stable release",
    },
  ],
};
