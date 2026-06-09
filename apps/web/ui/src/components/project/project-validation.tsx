import { useState } from "react";
import { useValidateMapping, useListMappingVersions, getListMappingVersionsQueryKey } from "@/api";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle, Info, CheckCircle2, ShieldAlert, PlayCircle, XCircle } from "lucide-react";
import type { ValidationResponse, ValidationIssueDTO } from "@/api";
import { format } from "date-fns";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/api/custom-fetch";

function apiErrorMessage(err: unknown): string {
  const e = err as ApiError;
  if (e?.data && typeof e.data === "object") {
    const d = e.data as Record<string, unknown>;
    if (typeof d["detail"] === "string") return d["detail"];
  }
  return (err as Error)?.message || "Unknown API error";
}

type IssueSeverity = "error" | "warn" | "info";

const SEVERITY_ORDER: IssueSeverity[] = ["error", "warn", "info"];

const SEVERITY_CONFIG: Record<IssueSeverity, {
  label: string;
  blocking: boolean;
  headerClass: string;
  rowClass: string;
  icon: React.ReactNode;
  badgeClass: string;
}> = {
  error: {
    label: "Errors",
    blocking: true,
    headerClass: "bg-red-50 border-red-200 text-red-800",
    rowClass: "hover:bg-red-50/40 border-red-100",
    icon: <XCircle className="w-5 h-5 text-red-500" />,
    badgeClass: "bg-red-100 text-red-700 border border-red-200",
  },
  warn: {
    label: "Warnings",
    blocking: false,
    headerClass: "bg-amber-50 border-amber-200 text-amber-800",
    rowClass: "hover:bg-amber-50/30 border-amber-100",
    icon: <AlertCircle className="w-5 h-5 text-amber-500" />,
    badgeClass: "bg-amber-100 text-amber-700 border border-amber-200",
  },
  info: {
    label: "Info",
    blocking: false,
    headerClass: "bg-blue-50 border-blue-200 text-blue-800",
    rowClass: "hover:bg-blue-50/30 border-blue-100",
    icon: <Info className="w-5 h-5 text-blue-500" />,
    badgeClass: "bg-blue-100 text-blue-700 border border-blue-200",
  },
};

export function ProjectValidation({ projectId }: { projectId: string }) {
  const { data: versions } = useListMappingVersions(projectId, { query: { enabled: !!projectId, queryKey: getListMappingVersionsQueryKey(projectId) } });
  const validateMapping = useValidateMapping();
  const { toast } = useToast();
  
  const [versionId, setVersionId] = useState<string>("");
  const [result, setResult] = useState<ValidationResponse | null>(null);

  const handleValidate = () => {
    if (!versionId) return;
    validateMapping.mutate(
      { projectId, data: { mapping_version_id: versionId } },
      {
        onSuccess: (data) => {
          const issues = Array.isArray(data.issues) ? data.issues : [];
          setResult({ ...data, issues });
        },
        onError: (err) => {
          setResult(null);
          toast({ title: "Validation failed", description: apiErrorMessage(err), variant: "destructive" });
        }
      }
    );
  };

  const groupedIssues = result
    ? SEVERITY_ORDER.reduce<Record<IssueSeverity, ValidationIssueDTO[]>>(
        (acc, sev) => {
          acc[sev] = result.issues.filter(i => i.severity === sev);
          return acc;
        },
        { error: [], warn: [], info: [] }
      )
    : null;

  const versionList = Array.isArray(versions) ? versions : [];

  return (
    <div className="space-y-8">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-end bg-slate-50 p-6 rounded-xl border border-slate-200">
        <div className="space-y-2 flex-1 w-full">
          <label className="text-sm font-semibold text-slate-800">Mapping Version to Validate</label>
          <Select value={versionId} onValueChange={(v) => { setVersionId(v); setResult(null); }}>
            <SelectTrigger className="bg-white border-slate-300">
              <SelectValue placeholder="Select a saved mapping draft..." />
            </SelectTrigger>
            <SelectContent>
              {versionList.map(v => (
                <SelectItem key={v.id} value={v.id}>
                  {v.version_label} &mdash; <span className="text-slate-400">{format(new Date(v.created_at), "MMM d, HH:mm")}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {versionList.length === 0 && (
            <p className="text-xs text-slate-400">No drafts yet — save a mapping in the previous tab first.</p>
          )}
          {versionList.length > 0 && !versionId && (
            <p className="text-xs text-slate-400">Choose a draft above, then click <strong>Run Validation Suite</strong>.</p>
          )}
        </div>
        <Button onClick={handleValidate} disabled={!versionId || validateMapping.isPending} className="w-full sm:w-auto">
          <PlayCircle className="w-4 h-4 mr-2" />
          {validateMapping.isPending ? "Executing Checks..." : "Run Validation Suite"}
        </Button>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-in fade-in duration-500">
          {/* Summary cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className={`border-l-4 shadow-sm ${result.has_errors ? "border-l-red-500" : "border-l-emerald-500"}`}>
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Overall Status</p>
                  <p className={`text-2xl font-bold ${result.has_errors ? "text-red-700" : "text-emerald-700"}`}>
                    {result.has_errors ? "Blocked" : "Passed"}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {result.has_errors ? "Fix errors before exporting" : "Ready to export"}
                  </p>
                </div>
                {result.has_errors
                  ? <ShieldAlert className="w-10 h-10 text-red-500 opacity-20" />
                  : <CheckCircle2 className="w-10 h-10 text-emerald-500 opacity-20" />}
              </CardContent>
            </Card>
            <Card className="shadow-sm border-l-4 border-l-red-400">
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Blocking Errors</p>
                  <p className="text-2xl font-bold text-slate-900">{result.error_count}</p>
                  <p className="text-xs text-red-600 mt-0.5 font-medium">Must fix to export</p>
                </div>
                <XCircle className="w-10 h-10 text-red-500 opacity-20" />
              </CardContent>
            </Card>
            <Card className="shadow-sm border-l-4 border-l-amber-400">
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Warnings</p>
                  <p className="text-2xl font-bold text-slate-900">{result.warning_count}</p>
                  <p className="text-xs text-amber-600 mt-0.5 font-medium">Review recommended</p>
                </div>
                <AlertCircle className="w-10 h-10 text-amber-500 opacity-20" />
              </CardContent>
            </Card>
          </div>

          {result.issues.length === 0 ? (
            <div className="text-center py-16 border border-emerald-200 rounded-xl bg-emerald-50/50">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-emerald-900">All Checks Passed</h3>
              <p className="text-emerald-700 mt-1 max-w-md mx-auto">No errors or warnings were found. This mapping version is ready to export.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {SEVERITY_ORDER.map((sev) => {
                const issues = groupedIssues![sev];
                if (issues.length === 0) return null;
                const cfg = SEVERITY_CONFIG[sev];
                return (
                  <div key={sev} className="border rounded-xl overflow-hidden shadow-sm bg-white">
                    {/* Group header */}
                    <div className={`flex items-center justify-between px-5 py-3 border-b text-sm font-semibold ${cfg.headerClass}`}>
                      <div className="flex items-center gap-2">
                        {cfg.icon}
                        <span>{cfg.label}</span>
                        {cfg.blocking && (
                          <span className="text-[10px] font-bold uppercase tracking-wider bg-red-200 text-red-800 px-1.5 py-0.5 rounded ml-1">
                            Blocks export
                          </span>
                        )}
                      </div>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${cfg.badgeClass}`}>
                        {issues.length} issue{issues.length !== 1 ? "s" : ""}
                      </span>
                    </div>
                    {/* Issue rows */}
                    <div className="divide-y divide-slate-100 max-h-72 overflow-auto">
                      {issues.map((issue, idx) => (
                        <div key={idx} className={`p-4 flex gap-3 transition-colors ${cfg.rowClass}`}>
                          <div className="shrink-0 mt-0.5">{cfg.icon}</div>
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-slate-900 text-sm">{issue.message}</p>
                            <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                              <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded shrink-0">Rule: {issue.rule_id}</span>
                              {issue.affected_field_paths.length > 0 && (
                                <span className="truncate">Fields: <span className="font-mono text-slate-700">{issue.affected_field_paths.join(", ")}</span></span>
                              )}
                            </div>
                            {issue.remediation_hint && (
                              <div className="mt-2 text-xs text-indigo-800 bg-indigo-50/50 border border-indigo-100 px-3 py-2 rounded-md flex items-start gap-2">
                                <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-indigo-500" />
                                <span>{issue.remediation_hint}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
