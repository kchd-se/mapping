import { useState, useMemo, useRef, useCallback } from "react";
import {
  useGetProjectSchemas,
  useImportSourceSchema,
  useSelectTargetSchema,
  useListCatalogSchemas,
  useListSchemaVersions,
  getGetProjectSchemasQueryKey,
  getListSchemaVersionsQueryKey,
} from "@/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Database, UploadCloud, FileJson, CheckCircle2, Search, Layers, Upload, Info } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/api/custom-fetch";
import type { CatalogSchemaResponse } from "@/api";

// ---------------------------------------------------------------------------
// Format configuration — single source of truth for adapter capabilities.
// Reflects packages/adapters/defaults.py (register_defaults).
//
// inputMode:
//   "json" — payload is a JSON object; the UI JSON.parses it before sending.
//   "text" — payload is sent as a raw string (CSV rows, SQL DDL, ADL text).
// implemented: true only for adapters that are fully working in v1.
// ---------------------------------------------------------------------------
const FORMAT_CONFIG = [
  {
    value: "json_schema",
    label: "JSON Schema",
    inputMode: "json" as const,
    implemented: true,
    accept: ".json",
    placeholder:
      '{\n  "type": "object",\n  "properties": {\n    "patient_id": { "type": "integer" },\n    "dob": { "type": "string", "format": "date" }\n  }\n}',
    hint: "Paste or upload a JSON Schema document (draft 4 / 7 / 2019-09 / 2020-12)",
  },
  {
    value: "csv_schema",
    label: "CSV Schema",
    inputMode: "text" as const,
    implemented: true,
    accept: ".csv",
    placeholder:
      "name,type,required,description\npatient_id,integer,true,Unique patient identifier\ndob,date,false,Date of birth\ngender,string,false,Patient gender",
    hint: "Required column: name. Optional: type, required, description, label, parent, enum, pattern, min_value, max_value",
  },
  {
    value: "fhir_profile",
    label: "FHIR Profile",
    inputMode: "json" as const,
    implemented: false,
    accept: ".json",
    placeholder:
      '{\n  "resourceType": "StructureDefinition",\n  "url": "http://hl7.org/fhir/StructureDefinition/Patient",\n  "type": "Patient"\n}',
    hint: "FHIR R4/R5 StructureDefinition JSON — adapter coming in a future release",
  },
  {
    value: "omop_cdm",
    label: "OMOP CDM",
    inputMode: "json" as const,
    implemented: false,
    accept: ".json",
    placeholder: '{ "tables": [{ "name": "person", "fields": [] }] }',
    hint: "OMOP CDM 5.x table definitions JSON — adapter coming in a future release",
  },
  {
    value: "openehr",
    label: "openEHR",
    inputMode: "text" as const,
    implemented: false,
    accept: ".xml,.adl",
    placeholder:
      "archetype (adl2)\nADL_VERSION=2.0.6\narchetype_id=openEHR-EHR-OBSERVATION.blood_pressure.v2\n...",
    hint: "openEHR ADL archetype or OPT XML — adapter coming in a future release",
  },
  {
    value: "parquet_schema",
    label: "Parquet Schema",
    inputMode: "json" as const,
    implemented: false,
    accept: ".json",
    placeholder:
      '{\n  "fields": [\n    { "name": "patient_id", "type": "INT64", "nullable": false }\n  ]\n}',
    hint: "Parquet / Arrow schema as JSON — adapter coming in a future release",
  },
  {
    value: "sql_ddl",
    label: "SQL DDL",
    inputMode: "text" as const,
    implemented: false,
    accept: ".sql",
    placeholder:
      "CREATE TABLE patient (\n  patient_id INT NOT NULL,\n  birth_date DATE,\n  gender VARCHAR(10),\n  PRIMARY KEY (patient_id)\n);",
    hint: "SQL DDL CREATE TABLE statement (ANSI / PostgreSQL / T-SQL) — adapter coming in a future release",
  },
] as const;

type FormatValue = (typeof FORMAT_CONFIG)[number]["value"];

function getFormatConfig(value: string) {
  return FORMAT_CONFIG.find((f) => f.value === value) ?? FORMAT_CONFIG[0];
}

// File extension → format auto-detection
const EXT_TO_FORMAT: Partial<Record<string, FormatValue>> = {
  ".json": "json_schema",
  ".csv": "csv_schema",
  ".sql": "sql_ddl",
  ".adl": "openehr",
  ".xml": "openehr",
};

function detectFormatFromFilename(filename: string): FormatValue | null {
  const ext = filename.slice(filename.lastIndexOf(".")).toLowerCase();
  return EXT_TO_FORMAT[ext] ?? null;
}

function apiErrorMessage(err: unknown): string {
  const e = err as ApiError;
  if (e?.data && typeof e.data === "object") {
    const d = e.data as Record<string, unknown>;
    if (typeof d["detail"] === "string") return d["detail"];
  }
  return (err as Error)?.message || "Unknown API error";
}

function SchemaImportForm({
  role,
  onImported,
  isPending,
}: {
  role: "source" | "target";
  onImported: (params: { schemaName: string; formatId: string; versionLabel: string; payload: string }) => void;
  isPending: boolean;
}) {
  const [schemaName, setSchemaName] = useState("");
  const [formatId, setFormatId] = useState<string>("json_schema");
  const [versionLabel, setVersionLabel] = useState("1.0");
  const [payload, setPayload] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentFormat = getFormatConfig(formatId);

  const loadFile = useCallback(
    (file: File) => {
      const detected = detectFormatFromFilename(file.name);
      if (detected) setFormatId(detected);
      if (!schemaName) setSchemaName(file.name.replace(/\.[^.]+$/, ""));
      const reader = new FileReader();
      reader.onload = (e) => setPayload((e.target?.result as string) ?? "");
      reader.readAsText(file);
    },
    [schemaName],
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) loadFile(file);
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) loadFile(file);
  };

  const handleSubmit = () => {
    onImported({ schemaName, formatId, versionLabel, payload });
  };

  const isDisabled = !currentFormat.implemented;

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label className="text-slate-700">Schema Name</Label>
        <Input
          value={schemaName}
          onChange={(e) => setSchemaName(e.target.value)}
          className="bg-slate-50"
          placeholder={role === "source" ? "e.g. RegionPatient" : "e.g. OMOP Person"}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label className="text-slate-700">Format</Label>
          <select
            value={formatId}
            onChange={(e) => {
              setFormatId(e.target.value);
              setPayload("");
            }}
            className="w-full h-9 rounded-md border border-input bg-slate-50 px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {FORMAT_CONFIG.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}{!f.implemented ? " (coming soon)" : ""}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label className="text-slate-700">Version Label</Label>
          <Input
            value={versionLabel}
            onChange={(e) => setVersionLabel(e.target.value)}
            className="bg-slate-50"
            placeholder="e.g. 1.0"
          />
        </div>
      </div>

      {/* File drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload schema file"
        className={`flex items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-3 transition-colors cursor-pointer ${
          dragging
            ? "border-indigo-400 bg-indigo-50"
            : "border-slate-200 bg-slate-50 hover:border-indigo-300 hover:bg-indigo-50/50"
        }`}
      >
        <Upload className="w-4 h-4 text-slate-400" />
        <span className="text-sm text-slate-500">
          Drop a file or{" "}
          <span className="text-indigo-600 font-medium">browse</span>
          <span className="text-slate-400 ml-1">({currentFormat.accept})</span>
        </span>
        <input
          ref={fileInputRef}
          type="file"
          accept={currentFormat.accept}
          className="hidden"
          onChange={handleFileChange}
          aria-label="Upload schema file"
        />
      </div>

      <div className="space-y-1">
        <Label className="text-slate-700">Schema Payload</Label>
        <Textarea
          className="font-mono text-xs h-40 bg-slate-50 resize-none"
          value={payload}
          onChange={(e) => setPayload(e.target.value)}
          placeholder={currentFormat.placeholder}
          disabled={isDisabled}
        />
        <p className="flex items-start gap-1 text-xs text-slate-400 mt-1">
          <Info className="w-3 h-3 mt-0.5 shrink-0" />
          {currentFormat.hint}
        </p>
      </div>

      {isDisabled && (
        <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-700">
          <strong>{currentFormat.label}</strong> adapter is not yet available. Select{" "}
          <strong>JSON Schema</strong> or <strong>CSV Schema</strong> to import.
        </div>
      )}

      <Button
        onClick={handleSubmit}
        disabled={isPending || !payload || !schemaName || !versionLabel || isDisabled}
        className="w-full"
      >
        <UploadCloud className="w-4 h-4 mr-2" />
        {isPending ? "Importing..." : role === "source" ? "Import Source Schema" : "Import & Set as Target"}
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// StandardBundleCard — one-click card for FHIR R4 / OMOP CDM 5.4 selection
// ---------------------------------------------------------------------------

function StandardBundleCard({
  bundle,
  onSelect,
  isPending,
}: {
  bundle: CatalogSchemaResponse;
  onSelect: () => void;
  isPending: boolean;
}) {
  const displayName = [
    bundle.metadata_tags.standard,
    bundle.metadata_tags.standard_version,
  ]
    .filter(Boolean)
    .join(" ") || bundle.name;

  // Convert "FHIR_Patient,FHIR_Organization" → "Patient · Organization"
  const includedSchemas = (bundle.metadata_tags.included_schemas ?? "")
    .split(",")
    .map((n) => n.replace(/^(FHIR_|OMOP_)/, "").replace(/_/g, "\u00A0"))
    .filter(Boolean);

  return (
    <button
      type="button"
      aria-label={`Select ${displayName} standard`}
      onClick={onSelect}
      disabled={isPending}
      className="w-full text-left p-4 rounded-lg border-2 border-indigo-200 bg-indigo-50 hover:border-indigo-400 hover:bg-indigo-100 transition-colors disabled:opacity-60"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-4 h-4 text-indigo-600 shrink-0" />
            <span className="font-semibold text-indigo-900 text-sm">{displayName}</span>
          </div>
          {includedSchemas.length > 0 && (
            <p className="text-xs text-indigo-600 truncate">
              {includedSchemas.join(" · ")}
            </p>
          )}
          {bundle.description && (
            <p className="text-xs text-slate-500 mt-1 line-clamp-2">{bundle.description}</p>
          )}
        </div>
        <span className="shrink-0 text-xs font-semibold text-indigo-700 whitespace-nowrap mt-0.5">
          Select →
        </span>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// CatalogPicker — lets users choose from catalog or select a whole standard
// ---------------------------------------------------------------------------

function CatalogPicker({
  projectId,
  onPinned,
}: {
  projectId: string;
  onPinned: () => void;
}) {
  const [q, setQ] = useState("");
  const [selectedSchemaId, setSelectedSchemaId] = useState<string | null>(null);
  const [selectedVersionLabel, setSelectedVersionLabel] = useState<string | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const selectTarget = useSelectTargetSchema();

  const {
    data: catalogSchemas,
    isLoading: schemasLoading,
    error: schemasError,
  } = useListCatalogSchemas({ q: q || undefined });

  const {
    data: versions,
    isLoading: versionsLoading,
    error: versionsError,
  } = useListSchemaVersions(selectedSchemaId ?? "", {
    query: { enabled: !!selectedSchemaId, queryKey: getListSchemaVersionsQueryKey(selectedSchemaId ?? "") },
  });

  // Separate pre-built standard bundles from individual schemas
  const { bundleSchemas, individualSchemas } = useMemo(() => {
    const all = catalogSchemas ?? [];
    return {
      bundleSchemas: all.filter((s) => s.metadata_tags?.bundle === "true"),
      individualSchemas: all.filter((s) => s.metadata_tags?.bundle !== "true"),
    };
  }, [catalogSchemas]);

  const selectedSchema = individualSchemas.find((s) => s.id === selectedSchemaId) ?? null;

  const pinSchema = (schemaId: string, versionLabel: string) => {
    selectTarget.mutate(
      { projectId, data: { schema_id: schemaId, version_label: versionLabel } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getGetProjectSchemasQueryKey(projectId) });
          toast({ title: "Target schema pinned" });
          onPinned();
        },
        onError: (err) => {
          const ae = err as ApiError;
          const msg = ae?.status === 401
            ? "Not authenticated"
            : apiErrorMessage(err);
          toast({ title: "Failed to pin target schema", description: msg, variant: "destructive" });
        },
      },
    );
  };

  const handleConfirm = () => {
    if (!selectedSchemaId || !selectedVersionLabel) return;
    pinSchema(selectedSchemaId, selectedVersionLabel);
  };

  const handleSelectBundle = (bundle: CatalogSchemaResponse) => {
    if (!bundle.latest_version_label) return;
    pinSchema(bundle.id, bundle.latest_version_label);
  };

  const schemasErrMsg = schemasError
    ? (() => {
        const ae = schemasError as ApiError;
        return ae?.status === 401 ? "Not authenticated" : apiErrorMessage(schemasError);
      })()
    : null;

  return (
    <div className="space-y-4">
      {/* Standard bundle cards — shown when available */}
      {!schemasLoading && !schemasErrMsg && bundleSchemas.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Map to entire standard
          </p>
          <div className="space-y-2">
            {bundleSchemas.map((bundle) => (
              <StandardBundleCard
                key={bundle.id}
                bundle={bundle}
                onSelect={() => handleSelectBundle(bundle)}
                isPending={selectTarget.isPending}
              />
            ))}
          </div>

          {/* Divider */}
          <div className="relative py-1">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-white px-3 text-xs text-slate-400">
                or select an individual schema
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <Input
          aria-label="Search catalog schemas"
          placeholder="Search schemas…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setSelectedSchemaId(null);
            setSelectedVersionLabel(null);
          }}
          className="pl-9 bg-slate-50"
        />
      </div>

      {/* Individual schema list (bundles excluded) */}
      {schemasErrMsg ? (
        <p className="text-sm text-red-600" role="alert">{schemasErrMsg}</p>
      ) : schemasLoading ? (
        <p className="text-sm text-slate-500">Loading schemas…</p>
      ) : !individualSchemas.length ? (
        <p className="text-sm text-slate-500">No schemas found.</p>
      ) : (
        <ul className="border border-slate-200 rounded-lg divide-y divide-slate-100 max-h-52 overflow-y-auto">
          {individualSchemas.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => {
                  setSelectedSchemaId(s.id);
                  setSelectedVersionLabel(null);
                }}
                className={`w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors ${
                  selectedSchemaId === s.id ? "bg-indigo-50 border-l-2 border-indigo-500" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-900 text-sm">{s.name}</span>
                  <Badge
                    variant="outline"
                    className={
                      s.approval_status === "approved"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : "bg-amber-50 text-amber-700 border-amber-200"
                    }
                  >
                    {s.approval_status}
                  </Badge>
                </div>
                <p className="text-xs text-slate-500 mt-0.5 font-mono">{s.format_id}</p>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Version selector — shown once an individual schema is selected */}
      {selectedSchemaId && (
        <div className="space-y-2">
          <Label className="text-slate-700">Version</Label>
          {versionsError ? (
            <p className="text-sm text-red-600" role="alert">
              {(() => {
                const ae = versionsError as ApiError;
                return ae?.status === 401 ? "Not authenticated" : apiErrorMessage(versionsError);
              })()}
            </p>
          ) : versionsLoading ? (
            <p className="text-sm text-slate-500">Loading versions…</p>
          ) : (
            <Select
              value={selectedVersionLabel ?? ""}
              onValueChange={setSelectedVersionLabel}
            >
              <SelectTrigger className="bg-slate-50">
                <SelectValue placeholder="Select version" />
              </SelectTrigger>
              <SelectContent>
                {versions?.map((v) => (
                  <SelectItem key={v.id} value={v.version_label}>
                    {v.version_label}
                    {v.notes ? ` — ${v.notes}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      )}

      {selectedSchemaId && (
        <Button
          onClick={handleConfirm}
          disabled={
            !selectedSchemaId ||
            !selectedVersionLabel ||
            selectTarget.isPending
          }
          className="w-full"
        >
          {selectTarget.isPending
            ? "Pinning…"
            : selectedSchema
            ? `Use "${selectedSchema.name}"`
            : "Select a schema above"}
        </Button>
      )}
    </div>
  );
}

export function ProjectSchemas({ projectId }: { projectId: string }) {
  const [targetMode, setTargetMode] = useState<"catalog" | "upload">("catalog");
  const { data: schemas, isLoading } = useGetProjectSchemas(projectId, {
    query: { enabled: !!projectId, queryKey: getGetProjectSchemasQueryKey(projectId) },
  });
  const importSource = useImportSourceSchema();
  const importForTarget = useImportSourceSchema();
  const selectTarget = useSelectTargetSchema();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Import + immediately register as source pin
  const handleImportSource = ({ schemaName, formatId, versionLabel, payload }: {
    schemaName: string; formatId: string; versionLabel: string; payload: string;
  }) => {
    const config = getFormatConfig(formatId);
    let parsed: unknown;
    if (config.inputMode === "text") {
      // CSV, SQL DDL, openEHR ADL — send raw string; adapter handles parsing.
      parsed = payload;
    } else {
      try {
        parsed = JSON.parse(payload);
      } catch {
        toast({ title: "Invalid JSON payload", description: "The schema payload is not valid JSON.", variant: "destructive" });
        return;
      }
    }
    importSource.mutate(
      { projectId, data: { format_id: formatId, schema_name: schemaName, version_label: versionLabel, schema_payload: parsed } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getGetProjectSchemasQueryKey(projectId) });
          toast({ title: "Source schema imported" });
        },
        onError: (err) => toast({
          title: "Import failed",
          description: apiErrorMessage(err),
          variant: "destructive",
        }),
      }
    );
  };

  // Import schema into catalog, then immediately pin it as target
  const handleImportTarget = ({ schemaName, formatId, versionLabel, payload }: {
    schemaName: string; formatId: string; versionLabel: string; payload: string;
  }) => {
    const config = getFormatConfig(formatId);
    let parsed: unknown;
    if (config.inputMode === "text") {
      parsed = payload;
    } else {
      try {
        parsed = JSON.parse(payload);
      } catch {
        toast({ title: "Invalid JSON payload", description: "The schema payload is not valid JSON.", variant: "destructive" });
        return;
      }
    }
    importForTarget.mutate(
      { projectId, data: { format_id: formatId, schema_name: schemaName, version_label: versionLabel, schema_payload: parsed } },
      {
        onSuccess: (ref) => {
          selectTarget.mutate(
            { projectId, data: { schema_id: ref.schema_id, version_label: ref.version_label } },
            {
              onSuccess: () => {
                queryClient.invalidateQueries({ queryKey: getGetProjectSchemasQueryKey(projectId) });
                toast({ title: "Target schema registered and pinned" });
              },
              onError: (err) => toast({
                title: "Failed to pin target schema",
                description: apiErrorMessage(err),
                variant: "destructive",
              }),
            }
          );
        },
        onError: (err) => toast({
          title: "Import failed",
          description: apiErrorMessage(err),
          variant: "destructive",
        }),
      }
    );
  };

  if (isLoading) return <div className="h-64 flex items-center justify-center text-slate-500">Loading schema configuration...</div>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Source Schema Panel */}
      <Card className="border-slate-200 shadow-none">
        <CardHeader className="bg-slate-50/50 border-b border-slate-100">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileJson className="w-5 h-5 text-indigo-500" /> Source Schema
          </CardTitle>
          <CardDescription>The raw structure of incoming data</CardDescription>
        </CardHeader>
        <CardContent className="p-6">
          {schemas?.source ? (
            <div className="space-y-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-slate-900 text-lg">{schemas.source.schema_name}</h3>
                  <p className="text-sm text-slate-500 font-mono mt-1">v{schemas.source.version_label}</p>
                </div>
                <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> Active
                </Badge>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Format</span>
                  <span className="font-medium text-slate-900">{schemas.source.format_id}</span>
                </div>
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Detected Fields</span>
                  <span className="font-medium text-slate-900 text-xl">{schemas.source.field_count}</span>
                </div>
              </div>
            </div>
          ) : (
            <SchemaImportForm
              role="source"
              isPending={importSource.isPending}
              onImported={handleImportSource}
            />
          )}
        </CardContent>
      </Card>

      {/* Target Schema Panel */}
      <Card className="border-slate-200 shadow-none">
        <CardHeader className="bg-slate-50/50 border-b border-slate-100">
          <CardTitle className="text-lg flex items-center gap-2">
            <Database className="w-5 h-5 text-teal-600" /> Target Schema
          </CardTitle>
          <CardDescription>The standardized destination format</CardDescription>
        </CardHeader>
        <CardContent className="p-6">
          {schemas?.target ? (
            <div className="space-y-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-slate-900 text-lg">{schemas.target.schema_name}</h3>
                  <p className="text-sm text-slate-500 font-mono mt-1">v{schemas.target.version_label}</p>
                </div>
                <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> Pinned
                </Badge>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Format</span>
                  <span className="font-medium text-slate-900">{schemas.target.format_id}</span>
                </div>
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Target Fields</span>
                  <span className="font-medium text-slate-900 text-xl">{schemas.target.field_count}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Mode toggle */}
              <div className="flex rounded-lg border border-slate-200 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setTargetMode("catalog")}
                  className={`flex-1 py-2 text-sm font-medium transition-colors ${
                    targetMode === "catalog"
                      ? "bg-indigo-600 text-white"
                      : "bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  Choose from Catalog
                </button>
                <button
                  type="button"
                  onClick={() => setTargetMode("upload")}
                  className={`flex-1 py-2 text-sm font-medium transition-colors ${
                    targetMode === "upload"
                      ? "bg-indigo-600 text-white"
                      : "bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  Upload New Schema
                </button>
              </div>

              {targetMode === "catalog" ? (
                <CatalogPicker projectId={projectId} onPinned={() => {}} />
              ) : (
                <SchemaImportForm
                  role="target"
                  isPending={importForTarget.isPending || selectTarget.isPending}
                  onImported={handleImportTarget}
                />
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
