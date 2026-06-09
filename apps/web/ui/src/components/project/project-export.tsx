import { useState } from "react";
import { useExportMapping, useListMappingVersions, getListMappingVersionsQueryKey } from "@/api";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Download, TerminalSquare, DatabaseZap, Info, Copy, Check } from "lucide-react";
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
  const [scriptCopied, setScriptCopied] = useState(false);

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

  const handleCopyScript = async () => {
    if (!result?.transformation_script) return;
    await navigator.clipboard.writeText(result.transformation_script);
    setScriptCopied(true);
    setTimeout(() => setScriptCopied(false), 2000);
  };

  const versionList = Array.isArray(versions) ? versions : [];

  return (
    <div className="space-y-6">
      {/* v1 scope banner — always visible */}
      <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-lg px-5 py-4 text-sm text-amber-900">
        <Info className="w-5 h-5 shrink-0 mt-0.5 text-amber-600" />
        <div>
          <p className="font-semibold">v1 scope: script generation only</p>
          <p className="mt-0.5 text-amber-800">
            Export produces a portable <strong>mapping artifact (JSON)</strong> and a <strong>transformation script</strong>.
            The script is ready to copy into your ETL pipeline — it is not executed here.
            Runtime execution is planned for v2.
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-end bg-slate-50 p-6 rounded-xl border border-slate-200">
        <div className="space-y-2 flex-1 w-full">
          <label className="text-sm font-semibold text-slate-800">Mapping Version to Export</label>
          <Select value={versionId} onValueChange={(v) => { setVersionId(v); setResult(null); }}>
            <SelectTrigger className="bg-white border-slate-300">
              <SelectValue placeholder="Select validated mapping..." />
            </SelectTrigger>
            <SelectContent>
              {versionList.map(v => (
                <SelectItem key={v.id} value={v.id}>
                  {v.version_label} &mdash; <span className="text-slate-400">{format(new Date(v.created_at), "MMM d, yyyy")}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {versionList.length === 0 && (
            <p className="text-xs text-slate-400">No drafts yet — save and validate a mapping first.</p>
          )}
          {versionList.length > 0 && !versionId && (
            <p className="text-xs text-slate-400">Choose a validated draft, then click <strong>Compile Export</strong>.</p>
          )}
        </div>
        <Button
          onClick={handleExport}
          disabled={!versionId || exportMapping.isPending}
          className="w-full sm:w-auto text-white"
          title={!versionId ? "Select a mapping version to enable export" : undefined}
        >
          <DatabaseZap className="w-4 h-4 mr-2" />
          {exportMapping.isPending ? "Compiling Artifact..." : "Compile Export"}
        </Button>
      </div>

      {result && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 animate-in fade-in duration-500">
          {/* JSON Artifact Panel */}
          <Card className="shadow-sm border-slate-200 flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-slate-100 bg-slate-50/50">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <DatabaseZap className="w-4 h-4 text-indigo-500" /> Mapping Artifact
                </CardTitle>
                <p className="text-xs text-slate-500 mt-1">Portable JSON — import this into any compatible tool or store in your version control.</p>
              </div>
              <Button size="sm" onClick={handleDownload} className="h-8 shrink-0">
                <Download className="w-3.5 h-3.5 mr-2" /> Download JSON
              </Button>
            </CardHeader>
            <CardContent className="p-0 flex-1 relative">
              <pre className="p-5 bg-[#0d1117] text-slate-300 text-[11px] font-mono overflow-auto h-120 w-full m-0 leading-relaxed selection:bg-indigo-500/30">
                {result.artifact_json}
              </pre>
            </CardContent>
          </Card>
          
          {/* Transformation Script Panel */}
          <Card className="shadow-sm border-slate-200 flex flex-col">
            <CardHeader className="pb-4 border-b border-slate-100 bg-slate-50/50">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <TerminalSquare className="w-4 h-4 text-slate-500" /> Transformation Script
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">Copy this into your ETL pipeline. Execution runs in your environment, not here.</p>
                </div>
                {result.transformation_script && (
                  <Button size="sm" variant="outline" onClick={handleCopyScript} className="h-8 shrink-0">
                    {scriptCopied
                      ? <><Check className="w-3.5 h-3.5 mr-1.5 text-emerald-600" /> Copied</>
                      : <><Copy className="w-3.5 h-3.5 mr-1.5" /> Copy</>}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0 flex-1">
              <pre className="p-5 bg-slate-50 text-slate-600 text-[11px] font-mono overflow-auto h-120 w-full m-0 leading-relaxed">
                {result.transformation_script || "# No transformation script was generated for this mapping version."}
              </pre>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
