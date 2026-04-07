import { useState } from "react";
import { useExportMapping, useListMappingVersions, getListMappingVersionsQueryKey } from "@/api";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Download, TerminalSquare, DatabaseZap } from "lucide-react";
import type { ExportResponse } from "@/api";
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

export function ProjectExport({ projectId }: { projectId: string }) {
  const { data: versions } = useListMappingVersions(projectId, { query: { enabled: !!projectId, queryKey: getListMappingVersionsQueryKey(projectId) } });
  const exportMapping = useExportMapping();
  const { toast } = useToast();
  
  const [versionId, setVersionId] = useState<string>("");
  const [result, setResult] = useState<ExportResponse | null>(null);

  const handleExport = () => {
    if (!versionId) return;
    exportMapping.mutate(
      { projectId, params: { mapping_version_id: versionId } },
      {
        onSuccess: (data) => setResult(data),
        onError: (err) => {
          setResult(null);
          toast({ title: "Export failed", description: apiErrorMessage(err), variant: "destructive" });
        }
      }
    );
  };

  const handleDownload = () => {
    if (!result) return;
    const blob = new Blob([result.artifact_json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `hdm_export_${projectId}_v${versionId.slice(0,6)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row gap-4 items-end bg-slate-50 p-6 rounded-xl border border-slate-200">
        <div className="space-y-2 flex-1 w-full">
          <label className="text-sm font-semibold text-slate-800">Target Mapping Version</label>
          <Select value={versionId} onValueChange={setVersionId}>
            <SelectTrigger className="bg-white border-slate-300">
              <SelectValue placeholder="Select validated mapping..." />
            </SelectTrigger>
            <SelectContent>
              {(Array.isArray(versions) ? versions : []).map(v => (
                <SelectItem key={v.id} value={v.id}>
                  {v.version_label} &mdash; <span className="text-slate-400">{format(new Date(v.created_at), "MMM d, yyyy")}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button onClick={handleExport} disabled={!versionId || exportMapping.isPending} className="w-full sm:w-auto text-white">
          <DatabaseZap className="w-4 h-4 mr-2" />
          {exportMapping.isPending ? "Compiling Artifact..." : "Compile Export"}
        </Button>
      </div>

      {result && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 animate-in fade-in duration-500">
          {/* JSON Artifact Panel */}
          <Card className="shadow-sm border-slate-200 flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-slate-100 bg-slate-50/50">
              <CardTitle className="text-lg flex items-center gap-2">
                <DatabaseZap className="w-5 h-5 text-indigo-500" /> Compiled Mapping
              </CardTitle>
              <Button size="sm" onClick={handleDownload} className="h-8">
                <Download className="w-3.5 h-3.5 mr-2" /> Download JSON
              </Button>
            </CardHeader>
            <CardContent className="p-0 flex-1 relative group">
              <pre className="p-5 bg-[#0d1117] text-slate-300 text-[11px] font-mono overflow-auto h-[500px] w-full m-0 leading-relaxed selection:bg-indigo-500/30">
                {result.artifact_json}
              </pre>
            </CardContent>
          </Card>
          
          {/* Script Execution Panel */}
          <Card className="shadow-sm border-slate-200 flex flex-col">
            <CardHeader className="pb-4 border-b border-slate-100 bg-slate-50/50">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <TerminalSquare className="w-5 h-5 text-slate-500" /> Transformation Script
                </CardTitle>
              </div>
              <div className="text-xs font-medium text-amber-700 bg-amber-100/50 border border-amber-200 px-3 py-1.5 rounded-md inline-flex items-center w-fit mt-3">
                Execution environment coming in v2.0
              </div>
            </CardHeader>
            <CardContent className="p-0 flex-1">
              <pre className="p-5 bg-slate-50 text-slate-600 text-[11px] font-mono overflow-auto h-[500px] w-full m-0 leading-relaxed">
                {result.transformation_script || "# Runtime execution script will be generated here."}
              </pre>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
