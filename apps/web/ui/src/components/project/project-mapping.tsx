import { useState } from "react";
import { useGetSuggestions, useCreateMappingVersion, useGetProjectSchemas, getListMappingVersionsQueryKey, getGetProjectSchemasQueryKey } from "@/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { AlertTriangle, CheckCircle2, ChevronRight, Zap, Save, AlertCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import type { MappingRuleDTO, FieldSuggestionsDTO } from "@/api";
import type { ApiError } from "@/api/custom-fetch";

function apiErrorMessage(err: unknown): string {
  const e = err as ApiError;
  if (e?.data && typeof e.data === "object") {
    const d = e.data as Record<string, unknown>;
    if (typeof d["detail"] === "string") return d["detail"];
  }
  return (err as Error)?.message || "Unknown API error";
}

export function ProjectMapping({ projectId }: { projectId: string }) {
  const { data: schemas } = useGetProjectSchemas(projectId, { query: { enabled: !!projectId, queryKey: getGetProjectSchemasQueryKey(projectId) } });
  const getSuggestions = useGetSuggestions();
  const createMapping = useCreateMappingVersion();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [suggestions, setSuggestions] = useState<FieldSuggestionsDTO[]>([]);
  const [rules, setRules] = useState<Record<string, MappingRuleDTO>>({});
  const [versionLabel, setVersionLabel] = useState("Draft v1");

  const canMap = schemas?.source && schemas?.target;

  const handleGenerateSuggestions = () => {
    if (!schemas?.source || !schemas?.target) return;
    getSuggestions.mutate(
      { projectId, data: { top_k: 3, min_confidence: 0.1 } },
      {
        onSuccess: (res) => {
          const fieldSuggestions = Array.isArray(res.field_suggestions) ? res.field_suggestions : [];
          setSuggestions(fieldSuggestions);
          const initialRules: Record<string, MappingRuleDTO> = {};
          fieldSuggestions.forEach(fs => {
            const candidates = Array.isArray(fs.candidates) ? fs.candidates : [];
            const topCandidate = candidates[0];
            initialRules[fs.target_field_id] = {
              target_field_id: fs.target_field_id,
              source_field_ids: topCandidate ? topCandidate.source_field_ids : [],
              notes: ""
            };
          });
          setRules(initialRules);
          toast({ title: "Suggestions loaded", description: "Top candidates automatically applied." });
        },
        onError: (err) => {
          toast({ title: "Suggestion engine failed", description: apiErrorMessage(err), variant: "destructive" });
        }
      }
    );
  };

  const handleSave = () => {
    createMapping.mutate(
      { projectId, data: { version_label: versionLabel, rules: Object.values(rules) } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getListMappingVersionsQueryKey(projectId) });
          toast({ title: "Version saved successfully" });
        },
        onError: (err) => {
          toast({ title: "Failed to save mapping", description: apiErrorMessage(err), variant: "destructive" });
        }
      }
    );
  };

  if (!canMap) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-500 bg-slate-50/50 rounded-lg border border-dashed">
        <AlertCircle className="w-10 h-10 text-slate-300 mb-4" />
        <h3 className="text-lg font-medium text-slate-900 mb-1">Schemas Not Configured</h3>
        <p className="max-w-md text-center">Please define both Source and Target schemas in the first tab to begin mapping fields.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-slate-50 p-4 rounded-lg border border-slate-100">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            Field Mapping Editor
          </h2>
          <p className="text-sm text-slate-500 mt-1">Review AI suggestions and manually override field connections.</p>
        </div>
        <div className="flex gap-3 items-end">
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-500 uppercase">Version Label</label>
            <Input
              value={versionLabel}
              onChange={(e) => setVersionLabel(e.target.value)}
              placeholder="e.g. Draft v1"
              className="w-32 text-sm bg-white"
            />
          </div>
          <Button onClick={handleGenerateSuggestions} disabled={getSuggestions.isPending} className="bg-indigo-600 hover:bg-indigo-700 text-white">
            <Zap className="w-4 h-4 mr-2" />
            {getSuggestions.isPending ? "Running Engine..." : "Auto-Map Engine"}
          </Button>
          <Button variant="outline" onClick={handleSave} disabled={createMapping.isPending || suggestions.length === 0 || !versionLabel}>
            <Save className="w-4 h-4 mr-2" /> Save Draft
          </Button>
        </div>
      </div>

      {suggestions.length > 0 && (
        <div className="space-y-4">
          <div className="grid grid-cols-12 gap-4 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b pb-2">
            <div className="col-span-4">Target Schema Field</div>
            <div className="col-span-8">Source Mapping & Transformations</div>
          </div>
          
          {suggestions.map((fs) => {
            const rule = rules[fs.target_field_id];
            const hasSource = rule?.source_field_ids && rule.source_field_ids.length > 0;

            return (
              <div key={fs.target_field_id} className="grid grid-cols-12 border border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm transition-all focus-within:ring-1 focus-within:ring-primary">
                {/* Target Column */}
                <div className="col-span-4 bg-slate-50/50 p-4 border-r border-slate-100 flex flex-col justify-center">
                  <div className="flex items-center gap-2 mb-1.5">
                    {hasSource ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <AlertTriangle className="w-4 h-4 text-amber-500" />}
                    <span className="font-semibold text-slate-900 font-mono text-sm break-all">{fs.target_field_path}</span>
                  </div>
                  <div className="text-xs text-slate-500 flex items-center gap-2 pl-6">
                    <span>ID: {fs.target_field_id}</span>
                  </div>
                </div>

                {/* Mapping Column */}
                <div className="col-span-8 p-4 space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="flex-1 space-y-1.5">
                      <label className="text-[10px] font-bold text-slate-500 uppercase">Mapped Source Field</label>
                      <Input 
                        value={rule?.source_field_ids?.join(", ") || ""} 
                        onChange={(e) => setRules(prev => ({
                          ...prev, 
                          [fs.target_field_id]: { ...prev[fs.target_field_id], source_field_ids: e.target.value.split(",").map(s => s.trim()).filter(Boolean) }
                        }))} 
                        placeholder="e.g. patient.id"
                        className="font-mono text-sm bg-slate-50 focus-visible:bg-white transition-colors"
                      />
                    </div>
                    <div className="w-1/3 space-y-1.5">
                      <label className="text-[10px] font-bold text-slate-500 uppercase">Transformation Notes</label>
                      <Input 
                        value={rule?.notes || ""} 
                        onChange={(e) => setRules(prev => ({
                          ...prev, 
                          [fs.target_field_id]: { ...prev[fs.target_field_id], notes: e.target.value }
                        }))}
                        placeholder="Casting / limits..." 
                        className="text-sm bg-slate-50 focus-visible:bg-white"
                      />
                    </div>
                  </div>

                  {(Array.isArray(fs.candidates) ? fs.candidates : []).length > 0 && (
                    <div className="bg-indigo-50/40 rounded-md border border-indigo-100 p-3 mt-2">
                      <div className="text-[10px] font-bold text-indigo-800 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                        <Zap className="w-3 h-3" /> Top AI Candidates
                      </div>
                      <div className="space-y-2.5">
                        {(Array.isArray(fs.candidates) ? fs.candidates : []).map((cand, idx) => (
                          <div key={idx} className="flex flex-col sm:flex-row sm:items-center gap-3">
                            <Button 
                              variant={rule?.source_field_ids?.join() === cand.source_field_ids.join() ? "default" : "outline"}
                              size="sm" 
                              className={`h-8 text-xs font-mono shrink-0 justify-start w-48 ${rule?.source_field_ids?.join() === cand.source_field_ids.join() ? "bg-indigo-600 hover:bg-indigo-700" : "bg-white hover:bg-indigo-50 hover:text-indigo-700 border-indigo-200"}`}
                              onClick={() => setRules(prev => ({
                                ...prev, 
                                [fs.target_field_id]: { ...prev[fs.target_field_id], source_field_ids: cand.source_field_ids }
                              }))}
                            >
                              {cand.source_field_ids.join(" + ")}
                            </Button>
                            <div className="flex-1 grid grid-cols-[100px_1fr] items-center gap-4">
                              <div className="flex items-center gap-2" title={`${(cand.confidence * 100).toFixed(1)}% match`}>
                                <Progress value={cand.confidence * 100} className="h-1.5 bg-indigo-100" />
                                <span className="text-[10px] text-slate-500 font-medium">{(cand.confidence * 100).toFixed(0)}%</span>
                              </div>
                              <div className="flex flex-col gap-0.5">
                                {cand.reasons.length > 0 && (
                                  <div className="text-[11px] text-slate-600 flex items-start gap-1 leading-tight">
                                    <ChevronRight className="w-3 h-3 text-slate-400 shrink-0 mt-0.5" />
                                    {cand.reasons[0]}
                                  </div>
                                )}
                                {cand.warnings.length > 0 && (
                                  <div className="text-[11px] text-amber-700 flex items-start gap-1 leading-tight font-medium">
                                    <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" />
                                    {cand.warnings[0]}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
