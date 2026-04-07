import { useState } from "react";
import { useValidateMapping, useListMappingVersions, getListMappingVersionsQueryKey } from "@/api";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle, Info, CheckCircle2, ShieldAlert, PlayCircle } from "lucide-react";
import type { ValidationResponse } from "@/api";
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

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row gap-4 items-end bg-slate-50 p-6 rounded-xl border border-slate-200">
        <div className="space-y-2 flex-1 w-full">
          <label className="text-sm font-semibold text-slate-800">Target Mapping Version</label>
          <Select value={versionId} onValueChange={setVersionId}>
            <SelectTrigger className="bg-white border-slate-300">
              <SelectValue placeholder="Select a saved draft..." />
            </SelectTrigger>
            <SelectContent>
              {(Array.isArray(versions) ? versions : []).map(v => (
                <SelectItem key={v.id} value={v.id}>
                  {v.version_label} &mdash; <span className="text-slate-400">{format(new Date(v.created_at), "MMM d, HH:mm")}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button onClick={handleValidate} disabled={!versionId || validateMapping.isPending} className="w-full sm:w-auto">
          <PlayCircle className="w-4 h-4 mr-2" />
          {validateMapping.isPending ? "Executing Checks..." : "Run Validation Suite"}
        </Button>
      </div>

      {result && (
        <div className="space-y-6 animate-in fade-in duration-500">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className={`border-l-4 shadow-sm ${result.has_errors ? "border-l-red-500" : "border-l-emerald-500"}`}>
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Status</p>
                  <p className={`text-2xl font-bold ${result.has_errors ? "text-red-700" : "text-emerald-700"}`}>
                    {result.has_errors ? "Checks Failed" : "Passed"}
                  </p>
                </div>
                {result.has_errors ? <ShieldAlert className="w-10 h-10 text-red-500 opacity-20" /> : <CheckCircle2 className="w-10 h-10 text-emerald-500 opacity-20" />}
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Errors</p>
                  <p className="text-2xl font-bold text-slate-900">{result.error_count}</p>
                </div>
                <AlertCircle className="w-10 h-10 text-red-500 opacity-20" />
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Warnings</p>
                  <p className="text-2xl font-bold text-slate-900">{result.warning_count}</p>
                </div>
                <Info className="w-10 h-10 text-amber-500 opacity-20" />
              </CardContent>
            </Card>
          </div>

          {result.issues.length > 0 ? (
            <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm bg-white">
              <div className="bg-slate-50 p-4 text-sm font-semibold text-slate-800 border-b flex justify-between items-center">
                Detailed Diagnostic Report
                <span className="text-xs font-normal text-slate-500">{result.issues.length} items found</span>
              </div>
              <div className="divide-y divide-slate-100 max-h-[500px] overflow-auto">
                {result.issues.map((issue, idx) => (
                  <div key={idx} className="p-5 flex gap-4 hover:bg-slate-50/50 transition-colors">
                    <div className="shrink-0 mt-0.5">
                      {issue.severity === "error" && <ShieldAlert className="w-5 h-5 text-red-500" />}
                      {issue.severity === "warn" && <AlertCircle className="w-5 h-5 text-amber-500" />}
                      {issue.severity === "info" && <Info className="w-5 h-5 text-blue-500" />}
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-slate-900">{issue.message}</p>
                      <div className="mt-1.5 flex items-center gap-3 text-xs">
                        <span className="text-slate-500 font-mono bg-slate-100 px-1.5 py-0.5 rounded">Rule: {issue.rule_id}</span>
                        <span className="text-slate-500">Targets: <span className="font-mono text-slate-700">{issue.affected_field_paths.join(", ")}</span></span>
                      </div>
                      {issue.remediation_hint && (
                        <div className="mt-3 text-sm text-indigo-800 bg-indigo-50/50 border border-indigo-100 px-4 py-2.5 rounded-md flex items-start gap-2">
                          <Info className="w-4 h-4 shrink-0 mt-0.5 text-indigo-500" />
                          <span>{issue.remediation_hint}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
             <div className="text-center py-16 border border-emerald-200 rounded-xl bg-emerald-50/50">
               <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
               <h3 className="text-lg font-semibold text-emerald-900">Validation Passed</h3>
               <p className="text-emerald-700 mt-1 max-w-md mx-auto">No errors or warnings were found in this mapping version. It is ready for export.</p>
             </div>
          )}
        </div>
      )}
    </div>
  );
}
