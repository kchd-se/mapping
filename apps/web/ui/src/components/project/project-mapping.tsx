import { useMemo, useState } from "react";
import { useGetSuggestions, useCreateMappingVersion, useUpdateMappingVersion, useGetProjectSchemas, useListMappingVersions, getListMappingVersionsQueryKey, getGetProjectSchemasQueryKey } from "@/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertTriangle, CheckCircle2, ChevronRight, Zap, Save, AlertCircle, Clock, FolderOpen, RefreshCw, Pencil } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import type { MappingRuleDTO, FieldSuggestionsDTO, MappingVersionResponse, SourceFieldRef } from "@/api";
import type { ApiError } from "@/api/custom-fetch";

function apiErrorMessage(err: unknown): string {
  const e = err as ApiError;
  if (e?.data && typeof e.data === "object") {
    const d = e.data as Record<string, unknown>;
    if (typeof d["detail"] === "string") return d["detail"];
  }
  return (err as Error)?.message || "Unknown API error";
}

type TargetCandidate = {
  target_field_id: string;
  target_field_path: string;
  confidence: number;
  reasons: string[];
  warnings: string[];
};

type SourceRow = {
  source_field_id: string;
  source_field_path: string;
  candidates: TargetCandidate[]; // sorted by confidence desc
};

export function ProjectMapping({ projectId }: { projectId: string }) {
  const { data: schemas } = useGetProjectSchemas(projectId, { query: { enabled: !!projectId, queryKey: getGetProjectSchemasQueryKey(projectId) } });
  const { data: drafts } = useListMappingVersions(projectId, { query: { enabled: !!projectId, queryKey: getListMappingVersionsQueryKey(projectId) } });
  const getSuggestions = useGetSuggestions();
  const createMapping = useCreateMappingVersion();
  const updateMapping = useUpdateMappingVersion();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [suggestions, setSuggestions] = useState<FieldSuggestionsDTO[]>([]);
  const [sourceFields, setSourceFields] = useState<SourceFieldRef[]>([]);
  const [rules, setRules] = useState<Record<string, MappingRuleDTO>>({});
  const [versionLabel, setVersionLabel] = useState("Draft v1");
  const [loadedDraftLabel, setLoadedDraftLabel] = useState<string | null>(null);
  const [loadedDraftId, setLoadedDraftId] = useState<string | null>(null);
  const [expandedCandidates, setExpandedCandidates] = useState<Record<string, boolean>>({});
  const [browseTableSelections, setBrowseTableSelections] = useState<Record<string, string>>({});

  // Build source-centric rows: every source field gets a row, even those with no AI candidates.
  const sourceRows = useMemo<SourceRow[]>(() => {
    // Step 1: build a candidates map keyed by source field id.
    const candidatesMap: Record<string, TargetCandidate[]> = {};
    suggestions.forEach(fs => {
      (Array.isArray(fs.candidates) ? fs.candidates : []).forEach(cand => {
        (cand.source_field_ids ?? []).forEach((srcId) => {
          if (!candidatesMap[srcId]) candidatesMap[srcId] = [];
          if (!candidatesMap[srcId].some(c => c.target_field_id === fs.target_field_id)) {
            candidatesMap[srcId].push({
              target_field_id: fs.target_field_id,
              target_field_path: fs.target_field_path,
              confidence: cand.confidence,
              reasons: cand.reasons ?? [],
              warnings: cand.warnings ?? [],
            });
          }
        });
      });
    });

    // Step 2: build a row for EVERY source field.
    // If sourceFields is populated (from the API response), use it as the authoritative list.
    // Otherwise fall back to only fields that appear in suggestions (pre-API-change compatibility).
    const fieldList: SourceFieldRef[] =
      sourceFields.length > 0
        ? sourceFields
        : Object.keys(candidatesMap).map(id => ({ id, path: id }));

    return fieldList
      .map(sf => ({
        source_field_id: sf.id,
        source_field_path: sf.path,
        candidates: (candidatesMap[sf.id] ?? []).sort((a, b) => b.confidence - a.confidence),
      }))
      .sort((a, b) => a.source_field_path.localeCompare(b.source_field_path));
  }, [suggestions, sourceFields]);

  // Flat list of all target fields known from the suggestions response.
  const allTargetFields = useMemo(
    () => suggestions.map(fs => ({ id: fs.target_field_id, path: fs.target_field_path })),
    [suggestions]
  );

  // Target fields grouped by table name (split on first ".").
  const tableGroups = useMemo(() => {
    const groups: Record<string, Array<{ id: string; path: string; fieldName: string }>> = {};
    allTargetFields.forEach(tf => {
      const dot = tf.path.indexOf(".");
      const table = dot > -1 ? tf.path.slice(0, dot) : "Other";
      const field = dot > -1 ? tf.path.slice(dot + 1) : tf.path;
      if (!groups[table]) groups[table] = [];
      groups[table].push({ id: tf.id, path: tf.path, fieldName: field });
    });
    return groups;
  }, [allTargetFields]);

  const PILLS_VISIBLE = 3;

  const canMap = schemas?.source && schemas?.target;

  const handleGenerateSuggestions = () => {
    if (!schemas?.source || !schemas?.target) return;
    getSuggestions.mutate(
      { projectId, data: { top_k: 3, min_confidence: 0.1 } },
      {
        onSuccess: (res) => {
          const fieldSuggestions = Array.isArray(res.field_suggestions) ? res.field_suggestions : [];
          setSuggestions(fieldSuggestions);
          setSourceFields(Array.isArray(res.source_fields) ? res.source_fields : []);

          // Preserve any rules already loaded from a saved draft; only fall back to
          // the top AI candidate when a target has no existing rule.
          setRules(existingRules => {
            const merged: Record<string, MappingRuleDTO> = {};
            fieldSuggestions.forEach(fs => {
              const candidates = Array.isArray(fs.candidates) ? fs.candidates : [];
              const topCandidate = candidates[0];
              merged[fs.target_field_id] = existingRules[fs.target_field_id] ?? {
                target_field_id: fs.target_field_id,
                source_field_ids: topCandidate ? topCandidate.source_field_ids : [],
                notes: "",
              };
            });
            return merged;
          });
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

  const handleUpdate = () => {
    if (!loadedDraftId) return;
    updateMapping.mutate(
      { projectId, versionId: loadedDraftId, data: { rules: Object.values(rules) } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getListMappingVersionsQueryKey(projectId) });
          toast({ title: `"${versionLabel}" updated` });
        },
        onError: (err) => {
          toast({ title: "Failed to update mapping", description: apiErrorMessage(err), variant: "destructive" });
        }
      }
    );
  };

  const handleLoadDraft = (draft: MappingVersionResponse) => {
    const restoredRules: Record<string, MappingRuleDTO> = {};
    (draft.rules ?? []).forEach(r => {
      restoredRules[r.target_field_id] = r;
    });
    setRules(restoredRules);
    setVersionLabel(draft.version_label);
    setLoadedDraftLabel(draft.version_label);
    setLoadedDraftId(draft.id);
    toast({
      title: `Draft "${draft.version_label}" loaded`,
      description: suggestions.length > 0
        ? "Saved selections applied to editor."
        : "Click Auto-Map Engine to view in editor.",
    });
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
          {loadedDraftId ? (
            <>
              <Button
                onClick={handleUpdate}
                disabled={updateMapping.isPending || sourceRows.length === 0}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                {updateMapping.isPending ? "Updating..." : "Update Draft"}
              </Button>
              <Button
                variant="outline"
                onClick={handleSave}
                disabled={createMapping.isPending || sourceRows.length === 0 || !versionLabel}
              >
                <Save className="w-4 h-4 mr-2" /> Save as New
              </Button>
            </>
          ) : (
            <Button variant="outline" onClick={handleSave} disabled={createMapping.isPending || sourceRows.length === 0 || !versionLabel}>
              <Save className="w-4 h-4 mr-2" /> Save Draft
            </Button>
          )}
        </div>
      </div>

      {/* Saved Drafts panel */}
      {drafts && drafts.length > 0 && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-400" /> Saved Drafts
          </h3>
          <div className="space-y-2">
            {drafts.map(draft => (
              <div key={draft.id} className="flex items-center justify-between bg-white rounded-md p-3 border border-slate-100 hover:border-indigo-200 transition-colors">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="font-medium text-sm text-slate-800 truncate">{draft.version_label}</span>
                  <Badge variant="secondary" className="text-[10px] shrink-0">{draft.rule_count} rules</Badge>
                  <span className="text-xs text-slate-400 shrink-0">{format(new Date(draft.created_at), "MMM d, HH:mm")}</span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="shrink-0 ml-4 hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700"
                  onClick={() => handleLoadDraft(draft)}
                >
                  <FolderOpen className="w-3.5 h-3.5 mr-1.5" /> Load
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Banner when a draft is loaded but suggestions not yet generated */}
      {loadedDraftLabel && sourceRows.length === 0 && (
        <div className="flex items-center gap-3 bg-indigo-50 border border-indigo-200 rounded-lg p-4 text-sm text-indigo-800">
          <CheckCircle2 className="w-5 h-5 text-indigo-500 shrink-0" />
          <span>
            Draft <strong>"{loadedDraftLabel}"</strong> loaded with {Object.keys(rules).length} rule{Object.keys(rules).length !== 1 ? "s" : ""}.
            Click Auto-Map Engine to visualise your saved selections in the editor.
          </span>
        </div>
      )}

      {sourceRows.length === 0 && canMap && !getSuggestions.isPending && (
        <div className="flex flex-col items-center justify-center py-14 text-slate-400 bg-slate-50/60 rounded-lg border border-dashed border-slate-200">
          <Zap className="w-8 h-8 mb-3 text-indigo-300" />
          <p className="text-sm font-medium text-slate-600">No suggestions loaded yet.</p>
          <p className="text-xs mt-1 text-slate-400">Click Auto-Map Engine to generate AI field-matching suggestions, or load a saved draft.</p>
        </div>
      )}

      {sourceRows.length > 0 && (() => {
        const mappedCount = sourceRows.filter(row =>
          row.candidates.some(c => rules[c.target_field_id]?.source_field_ids?.includes(row.source_field_id)) ||
          (row.candidates.length === 0 && Object.values(rules).some(r => (r.source_field_ids ?? []).includes(row.source_field_id)))
        ).length;
        const unmappedCount = sourceRows.length - mappedCount;
        return (
        <div className="space-y-4">
          <div className="flex items-center justify-between px-4 border-b pb-2">
            <div className="grid grid-cols-12 gap-4 flex-1 text-xs font-semibold text-slate-500 uppercase tracking-wider">
              <div className="col-span-4">Source Field</div>
              <div className="col-span-8">Target Field Suggestions</div>
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-4">
              <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">{mappedCount} mapped</span>
              {unmappedCount > 0 && (
                <span className="text-xs font-semibold text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">{unmappedCount} unmapped</span>
              )}
            </div>
          </div>

          {sourceRows.map((row) => {
            const candidateTargetIds = new Set(row.candidates.map(c => c.target_field_id));

            // AI-matched candidate rule
            const selectedCandidate = row.candidates.find(
              c => rules[c.target_field_id]?.source_field_ids?.includes(row.source_field_id)
            ) ?? null;

            // Manual override: a rule whose target is NOT in the AI candidates list
            const manualOverrideTargetId = Object.keys(rules).find(
              tid => !candidateTargetIds.has(tid) && (rules[tid]?.source_field_ids ?? []).includes(row.source_field_id)
            ) ?? null;
            const manualOverrideTarget = manualOverrideTargetId
              ? allTargetFields.find(t => t.id === manualOverrideTargetId) ?? null
              : null;

            const hasTarget = !!selectedCandidate || !!manualOverrideTarget;
            const isOverridden = (!!selectedCandidate && selectedCandidate.target_field_id !== row.candidates[0]?.target_field_id)
              || !!manualOverrideTarget;

            // Pills
            const isExpanded = !!expandedCandidates[row.source_field_id];
            const visiblePills = isExpanded ? row.candidates : row.candidates.slice(0, PILLS_VISIBLE);
            const hiddenPillCount = row.candidates.length - PILLS_VISIBLE;

            // Browse two-step
            const browseTable = browseTableSelections[row.source_field_id] ?? "";
            const browseTableFields = browseTable ? (tableGroups[browseTable] ?? []) : [];

            const handlePillClick = (candId: string) => {
              setRules(prev => {
                // Remove all existing rules for this source field
                const next = Object.fromEntries(
                  Object.entries(prev).filter(([, rule]) =>
                    !(rule.source_field_ids ?? []).includes(row.source_field_id)
                  )
                );
                // If clicking the already-selected pill → deselect (return without re-adding)
                if (prev[candId]?.source_field_ids?.includes(row.source_field_id)) {
                  return next;
                }
                const cand = row.candidates.find(c => c.target_field_id === candId);
                if (!cand) return next;
                return {
                  ...next,
                  [candId]: {
                    target_field_id: candId,
                    source_field_ids: [row.source_field_id],
                    notes: prev[candId]?.notes ?? "",
                  },
                };
              });
            };

            const handleBrowseFieldSelect = (newTargetId: string) => {
              setRules(prev => {
                const next = Object.fromEntries(
                  Object.entries(prev).filter(([, rule]) =>
                    !(rule.source_field_ids ?? []).includes(row.source_field_id)
                  )
                );
                if (!newTargetId) return next;
                return {
                  ...next,
                  [newTargetId]: {
                    target_field_id: newTargetId,
                    source_field_ids: [row.source_field_id],
                    notes: prev[newTargetId]?.notes ?? "",
                  },
                };
              });
              setBrowseTableSelections(prev => {
                const next = { ...prev };
                delete next[row.source_field_id];
                return next;
              });
            };

            return (
              <div
                key={row.source_field_id}
                className={`grid grid-cols-12 border rounded-lg overflow-hidden bg-white shadow-sm transition-all ${
                  hasTarget ? "border-slate-200" : "border-red-200 bg-red-50/30"
                }`}
              >
                {/* Source column */}
                <div className={`col-span-4 p-4 border-r border-slate-100 flex flex-col justify-center ${hasTarget ? "bg-slate-50/50" : "bg-red-50/40"}`}>
                  <div className="flex items-center gap-2 mb-1.5">
                    {hasTarget
                      ? <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                      : <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />}
                    <span className="font-semibold text-slate-900 font-mono text-sm break-all">{row.source_field_path}</span>
                  </div>
                  {isOverridden && (
                    <div className="flex items-center gap-1 mt-1">
                      <Pencil className="w-3 h-3 text-violet-500" />
                      <span className="text-[10px] font-semibold text-violet-600 uppercase tracking-wide">User override</span>
                    </div>
                  )}
                  {!hasTarget && (
                    <span className="text-[11px] text-red-500 mt-1">Unmapped — required field</span>
                  )}
                </div>

                {/* Target column */}
                <div className="col-span-8 p-4 space-y-3">

                  {/* 1. Summary card */}
                  {selectedCandidate ? (
                    <div className="bg-indigo-50/50 border border-indigo-200 rounded-md px-3 py-2.5 space-y-1.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono font-semibold text-sm text-indigo-900 break-all">{selectedCandidate.target_field_path}</span>
                        <div
                          className={`flex items-center gap-1 shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            selectedCandidate.confidence >= 0.75 ? "bg-emerald-100 text-emerald-700" :
                            selectedCandidate.confidence >= 0.4  ? "bg-amber-100 text-amber-700" :
                                                                    "bg-red-100 text-red-600"
                          }`}
                          title={`${(selectedCandidate.confidence * 100).toFixed(1)}% confidence`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            selectedCandidate.confidence >= 0.75 ? "bg-emerald-500" :
                            selectedCandidate.confidence >= 0.4  ? "bg-amber-500" :
                                                                    "bg-red-500"
                          }`} />
                          {(selectedCandidate.confidence * 100).toFixed(1)}% match
                        </div>
                        {isOverridden ? (
                          <div className="flex items-center gap-1">
                            <Pencil className="w-3 h-3 text-violet-500" />
                            <span className="text-[10px] font-semibold text-violet-600 uppercase tracking-wide">Override</span>
                          </div>
                        ) : (
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 shrink-0">Best</Badge>
                        )}
                      </div>
                      {selectedCandidate.reasons[0] && (
                        <div className="flex items-center gap-1 text-[11px] text-slate-600">
                          <ChevronRight className="w-3 h-3 text-slate-400 shrink-0" />
                          <span>{selectedCandidate.reasons[0]}</span>
                        </div>
                      )}
                      {selectedCandidate.warnings[0] && (
                        <div className="flex items-center gap-1 text-[11px] text-amber-700 font-medium">
                          <AlertTriangle className="w-3 h-3 shrink-0" />
                          <span>{selectedCandidate.warnings[0]}</span>
                        </div>
                      )}
                      <Input
                        value={rules[selectedCandidate.target_field_id]?.notes ?? ""}
                        onChange={(e) => setRules(prev => ({
                          ...prev,
                          [selectedCandidate.target_field_id]: { ...prev[selectedCandidate.target_field_id], notes: e.target.value }
                        }))}
                        placeholder="e.g. Casting / limits..."
                        className="text-xs bg-white focus-visible:bg-white h-7 mt-1"
                      />
                    </div>
                  ) : manualOverrideTarget ? (
                    <div className="bg-slate-50 border border-slate-200 rounded-md px-3 py-2.5 space-y-1.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono font-semibold text-sm text-slate-900 break-all">{manualOverrideTarget.path}</span>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 shrink-0 border-violet-300 text-violet-700">Manual</Badge>
                      </div>
                      <Input
                        value={rules[manualOverrideTarget.id]?.notes ?? ""}
                        onChange={(e) => setRules(prev => ({
                          ...prev,
                          [manualOverrideTarget.id]: { ...prev[manualOverrideTarget.id], notes: e.target.value }
                        }))}
                        placeholder="e.g. Casting / limits..."
                        className="text-xs bg-white focus-visible:bg-white h-7 mt-1"
                      />
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-[11px] text-slate-400 italic bg-slate-50 border border-dashed border-slate-200 rounded-md px-3 py-2">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>{row.candidates.length > 0 ? "No target selected — choose a recommendation or browse below." : "No AI suggestion — browse all fields below."}</span>
                    </div>
                  )}

                  {/* 2. AI recommendation pills */}
                  {row.candidates.length > 0 && (
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">AI Recommendations</label>
                      <div className="flex flex-wrap gap-1.5">
                        {visiblePills.map((cand) => {
                          const isSelected = selectedCandidate?.target_field_id === cand.target_field_id;
                          return (
                            <button
                              key={cand.target_field_id}
                              type="button"
                              role="button"
                              aria-pressed={isSelected}
                              aria-label={cand.target_field_path}
                              onClick={() => handlePillClick(cand.target_field_id)}
                              title={cand.target_field_path}
                              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-mono transition-all ${
                                isSelected
                                  ? "bg-indigo-600 text-white border-indigo-600 shadow-sm"
                                  : "bg-white text-slate-700 border-slate-300 hover:border-indigo-400 hover:text-indigo-700 hover:bg-indigo-50"
                              }`}
                            >
                              {isSelected && <CheckCircle2 className="w-3 h-3 shrink-0" />}
                              <span className="max-w-45 truncate">{cand.target_field_path}</span>
                              <span className={`shrink-0 text-[10px] font-bold font-sans ${
                                isSelected ? "text-indigo-200" :
                                cand.confidence >= 0.75 ? "text-emerald-600" :
                                cand.confidence >= 0.4  ? "text-amber-600" :
                                                          "text-red-500"
                              }`}>
                                {(cand.confidence * 100).toFixed(0)}%
                              </span>
                            </button>
                          );
                        })}
                        {!isExpanded && hiddenPillCount > 0 && (
                          <button
                            type="button"
                            onClick={() => setExpandedCandidates(prev => ({ ...prev, [row.source_field_id]: true }))}
                            className="flex items-center gap-1 px-2.5 py-1 rounded-full border border-dashed border-slate-300 text-xs text-slate-500 hover:border-indigo-400 hover:text-indigo-600 transition-all"
                          >
                            +{hiddenPillCount} more
                          </button>
                        )}
                        {isExpanded && row.candidates.length > PILLS_VISIBLE && (
                          <button
                            type="button"
                            onClick={() => setExpandedCandidates(prev => ({ ...prev, [row.source_field_id]: false }))}
                            className="flex items-center gap-1 px-2.5 py-1 rounded-full border border-dashed border-slate-300 text-xs text-slate-500 hover:border-indigo-400 hover:text-indigo-600 transition-all"
                          >
                            Show less
                          </button>
                        )}
                      </div>
                      {/* Reason hints for unselected candidates */}
                      {visiblePills.some(c => selectedCandidate?.target_field_id !== c.target_field_id && c.reasons[0]) && (
                        <div className="flex flex-col gap-0.5 pl-1 mt-0.5">
                          {visiblePills
                            .filter(c => selectedCandidate?.target_field_id !== c.target_field_id && c.reasons[0])
                            .map(c => (
                              <div key={c.target_field_id} className="flex gap-1 text-[10px] text-slate-400">
                                <span className="font-mono text-slate-500 shrink-0">{c.target_field_path}:</span>
                                <span>{c.reasons[0]}</span>
                              </div>
                            ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* 3. Browse all fields — two-step: table then field */}
                  <div className="space-y-1.5 pt-1">
                    <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                      {row.candidates.length > 0 ? "Or browse all fields" : "Browse all fields"}
                    </label>
                    <div className="flex gap-2">
                      <Select
                        value={browseTable}
                        onValueChange={(t) => setBrowseTableSelections(prev => ({ ...prev, [row.source_field_id]: t }))}
                      >
                        <SelectTrigger className="bg-white border-slate-300 h-9 text-xs w-44 hover:border-indigo-400 data-placeholder:text-slate-400">
                          <SelectValue placeholder="Select table…" />
                        </SelectTrigger>
                        <SelectContent className="max-h-56 overflow-y-auto">
                          {Object.keys(tableGroups).sort().map(t => (
                            <SelectItem key={t} value={t} className="text-xs">
                              <span className="font-mono">{t}</span>
                              <span className="ml-1.5 text-slate-400 font-sans">({tableGroups[t].length})</span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select
                        value=""
                        onValueChange={handleBrowseFieldSelect}
                        disabled={!browseTable}
                      >
                        <SelectTrigger className={`bg-white border-slate-300 h-9 text-xs flex-1 hover:border-indigo-400 data-placeholder:text-slate-400 ${!browseTable ? "opacity-50 cursor-not-allowed" : ""}`}>
                          <SelectValue placeholder={browseTable ? "Select field…" : "— Pick table first —"} />
                        </SelectTrigger>
                        <SelectContent className="max-h-56 overflow-y-auto">
                          {browseTableFields.map(f => (
                            <SelectItem key={f.id} value={f.id} className="text-xs">
                              <span className="font-mono">{f.fieldName}</span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                </div>
              </div>
            );
          })}
        </div>
        );
      })()}
    </div>
  );
}
