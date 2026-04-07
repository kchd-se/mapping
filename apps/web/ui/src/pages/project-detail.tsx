import { useParams } from "wouter";
import { useGetProject, useUpdateProjectStatus, getGetProjectQueryKey } from "@/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useQueryClient } from "@tanstack/react-query";
import { ProjectSchemas } from "@/components/project/project-schemas";
import { ProjectMapping } from "@/components/project/project-mapping";
import { ProjectValidation } from "@/components/project/project-validation";
import { ProjectExport } from "@/components/project/project-export";
import { Skeleton } from "@/components/ui/skeleton";
import { Database, ActivitySquare, CheckCircle, Code2, AlertTriangle } from "lucide-react";
import { format } from "date-fns";

export function ProjectDetail() {
  const params = useParams();
  const id = params.id as string;
  const { data: project, isLoading, error } = useGetProject(id, { query: { enabled: !!id, queryKey: getGetProjectQueryKey(id) } });
  const updateStatus = useUpdateProjectStatus();
  const queryClient = useQueryClient();

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-6xl mx-auto">
        <Skeleton className="h-16 w-1/2" />
        <Skeleton className="h-10 w-full max-w-2xl" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="text-center py-16 max-w-6xl mx-auto border border-destructive/30 rounded-xl bg-destructive/5" data-testid="text-project-error">
        <AlertTriangle className="w-10 h-10 text-destructive mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-slate-900">Failed to load project</h3>
        <p className="text-slate-600 mt-2">
          {(error as Error)?.message || "Project not found or API unavailable."}
        </p>
      </div>
    );
  }

  const handleStatusChange = (newStatus: string) => {
    updateStatus.mutate(
      { projectId: id, data: { status: newStatus } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getGetProjectQueryKey(id) });
        }
      }
    );
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">{project.name}</h1>
            <Badge variant={project.sensitivity === "healthcare_highly_sensitive" ? "destructive" : "secondary"} className="uppercase text-[10px]">
              {project.sensitivity.replace(/_/g, " ")}
            </Badge>
          </div>
          <p className="text-slate-500 text-lg">{project.description}</p>
          <div className="flex items-center gap-4 mt-4 text-sm text-slate-500">
            <span className="font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-600">ID: {project.id.slice(0,12)}</span>
            <span>Created {format(new Date(project.created_at), "MMM d, yyyy")}</span>
            <span>Owner: {project.owner}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-3 bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-sm font-semibold text-slate-700 pl-1">Status</span>
          <Select value={project.status} onValueChange={handleStatusChange} disabled={updateStatus.isPending}>
            <SelectTrigger className="w-[140px] font-medium bg-slate-50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="review">In Review</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="published">Published</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Tabs defaultValue="schemas" className="w-full">
        <TabsList className="grid w-full grid-cols-4 max-w-3xl mb-8 p-1 bg-slate-100/80 h-auto">
          <TabsTrigger value="schemas" className="py-2.5 data-[state=active]:shadow-sm">
            <Database className="w-4 h-4 mr-2 opacity-70" /> 1. Schemas
          </TabsTrigger>
          <TabsTrigger value="mapping" className="py-2.5 data-[state=active]:shadow-sm">
            <ActivitySquare className="w-4 h-4 mr-2 opacity-70" /> 2. Map Fields
          </TabsTrigger>
          <TabsTrigger value="validation" className="py-2.5 data-[state=active]:shadow-sm">
            <CheckCircle className="w-4 h-4 mr-2 opacity-70" /> 3. Validate
          </TabsTrigger>
          <TabsTrigger value="export" className="py-2.5 data-[state=active]:shadow-sm">
            <Code2 className="w-4 h-4 mr-2 opacity-70" /> 4. Export
          </TabsTrigger>
        </TabsList>
        <div className="mt-6 bg-white rounded-xl shadow-sm border border-slate-200 p-6 min-h-[500px]">
          <TabsContent value="schemas" className="mt-0 focus-visible:outline-none">
            <ProjectSchemas projectId={id} />
          </TabsContent>
          <TabsContent value="mapping" className="mt-0 focus-visible:outline-none">
            <ProjectMapping projectId={id} />
          </TabsContent>
          <TabsContent value="validation" className="mt-0 focus-visible:outline-none">
            <ProjectValidation projectId={id} />
          </TabsContent>
          <TabsContent value="export" className="mt-0 focus-visible:outline-none">
            <ProjectExport projectId={id} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
