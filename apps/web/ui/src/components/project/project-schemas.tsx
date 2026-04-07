import { useState } from "react";
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
import { Database, UploadCloud, FileJson, CheckCircle2, Search } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/api/custom-fetch";

// Adapter format IDs supported by the backend registry.
// Source of truth: packages/adapters/__init__.py (register_defaults).
const FORMAT_OPTIONS = [
  { value: "json_schema", label: "JSON Schema" },
  { value: "csv_schema", label: "CSV Schema" },
  { value: "fhir_profile", label: "FHIR Profile" },
  { value: "omop_cdm", label: "OMOP CDM" },
  { value: "openehr", label: "openEHR" },
  { value: "parquet_schema", label: "Parquet Schema" },
  { value: "sql_ddl", label: "SQL DDL" },
] as const;

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
  const [formatId, setFormatId] = useState("json_schema");
  const [versionLabel, setVersionLabel] = useState("1.0");
  const [payload, setPayload] = useState("");

  const handleSubmit = () => {
    onImported({ schemaName, formatId, versionLabel, payload });
  };

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
            onChange={(e) => setFormatId(e.target.value)}
            className="w-full h-9 rounded-md border border-input bg-slate-50 px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {FORMAT_OPTIONS.map((f) => (
              <option key={f.value} value={f.value}>{f.label}</option>
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
      <div className="space-y-2">
        <Label className="text-slate-700">Schema Payload</Label>
        <Textarea
          className="font-mono text-xs h-40 bg-slate-50 resize-none"
          value={payload}
          onChange={(e) => setPayload(e.target.value)}
          placeholder='{"type":"object","properties":{"id":{"type":"integer"}}}'
        />
      </div>
      <Button
        onClick={handleSubmit}
        disabled={isPending || !payload || !schemaName || !versionLabel}
        className="w-full"
      >
        <UploadCloud className="w-4 h-4 mr-2" />
        {isPending ? "Importing..." : role === "source" ? "Import Source Schema" : "Import & Set as Target"}
      </Button>
    </div>
  );
}

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

  const selectedSchema = catalogSchemas?.find((s) => s.id === selectedSchemaId) ?? null;

  const handleConfirm = () => {
    if (!selectedSchemaId || !selectedVersionLabel) return;
    selectTarget.mutate(
      { projectId, data: { schema_id: selectedSchemaId, version_label: selectedVersionLabel } },
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

  const schemasErrMsg = schemasError
    ? (() => {
        const ae = schemasError as ApiError;
        return ae?.status === 401 ? "Not authenticated" : apiErrorMessage(schemasError);
      })()
    : null;

  return (
    <div className="space-y-4">
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

      {/* Schema list */}
      {schemasErrMsg ? (
        <p className="text-sm text-red-600" role="alert">{schemasErrMsg}</p>
      ) : schemasLoading ? (
        <p className="text-sm text-slate-500">Loading schemas…</p>
      ) : !catalogSchemas?.length ? (
        <p className="text-sm text-slate-500">No schemas found.</p>
      ) : (
        <ul className="border border-slate-200 rounded-lg divide-y divide-slate-100 max-h-52 overflow-y-auto">
          {catalogSchemas.map((s) => (
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

      {/* Version selector — shown once a schema is selected */}
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
    let parsed: unknown;
    try {
      parsed = JSON.parse(payload);
    } catch {
      toast({ title: "Invalid JSON payload", variant: "destructive" });
      return;
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
    let parsed: unknown;
    try {
      parsed = JSON.parse(payload);
    } catch {
      toast({ title: "Invalid JSON payload", variant: "destructive" });
      return;
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
