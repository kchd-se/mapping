import { useState } from "react";
import { useLocation } from "wouter";
import { useListProjects, useCreateProject, getListProjectsQueryKey } from "@/api";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Plus, Folder, ArrowRight, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/api/custom-fetch";

export function ProjectsList() {
  const { data: projects, isLoading, error } = useListProjects();
  const createProject = useCreateProject();
  const queryClient = useQueryClient();
  const [, setLocation] = useLocation();
  const [open, setOpen] = useState(false);
  const { toast } = useToast();
  
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleCreate = () => {
    createProject.mutate(
      { data: { name, description, sensitivity: "healthcare_highly_sensitive" } },
      {
        onSuccess: (newProject) => {
          queryClient.invalidateQueries({ queryKey: getListProjectsQueryKey() });
          setOpen(false);
          setName("");
          setDescription("");
          setLocation(`/projects/${newProject.id}`);
        },
        onError: (err) => {
          const ae = err as ApiError;
          const detail =
            ae?.data && typeof ae.data === "object"
              ? (ae.data as Record<string, unknown>)["detail"] as string | undefined
              : undefined;
          toast({
            title: "Failed to create project",
            description: detail ?? ae?.message ?? "Unable to reach the API. Check that the server is running.",
            variant: "destructive",
          });
        },
      }
    );
  };

  const projectList = Array.isArray(projects) ? projects : [];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900" data-testid="text-page-title">Data Mapping Projects</h1>
          <p className="text-slate-500 mt-1">Manage integration pipelines and schema transformations.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button className="shadow-sm" data-testid="button-new-project">
              <Plus className="w-4 h-4 mr-2" /> New Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Initialize Project</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Project Name</Label>
                <Input data-testid="input-project-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Cerner to OMOP Phase 1" autoFocus />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input data-testid="input-project-description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional context..." />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button data-testid="button-create-project" onClick={handleCreate} disabled={!name || createProject.isPending}>
                {createProject.isPending ? "Creating..." : "Create Project"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {error ? (
        <div className="text-center py-16 border border-destructive/30 rounded-xl bg-destructive/5" data-testid="text-api-error">
          <AlertTriangle className="w-10 h-10 text-destructive mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900">API Connection Error</h3>
          <p className="text-slate-600 mt-2 max-w-lg mx-auto">
            Unable to reach the API server. Please verify the API base URL is configured correctly in Settings.
          </p>
          <p className="text-sm text-slate-500 mt-2 font-mono bg-slate-100 inline-block px-3 py-1 rounded">
            {(error as Error).message || "Unknown error"}
          </p>
          <div className="mt-6">
            <Button variant="outline" onClick={() => setLocation("/settings")} data-testid="link-go-to-settings">
              Go to Settings
            </Button>
          </div>
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1,2,3].map((i) => (
            <Card key={i} className="h-40 animate-pulse bg-slate-100/50 border-slate-200" />
          ))}
        </div>
      ) : projectList.length === 0 ? (
        <div className="text-center py-24 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
          <div className="bg-white w-16 h-16 rounded-full flex items-center justify-center mx-auto shadow-sm border border-slate-100 mb-4">
            <Folder className="w-8 h-8 text-slate-400" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900">No active projects</h3>
          <p className="text-slate-500 mt-2 mb-6 max-w-md mx-auto">Create a new mapping project to import your source schemas and begin the transformation process.</p>
          <Button onClick={() => setOpen(true)} data-testid="button-create-first"><Plus className="w-4 h-4 mr-2" /> Initialize First Project</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projectList.map(p => (
            <Card 
              key={p.id} 
              data-testid={`card-project-${p.id}`}
              className="group hover:border-primary/50 hover:shadow-md transition-all cursor-pointer flex flex-col h-full bg-white" 
              onClick={() => setLocation(`/projects/${p.id}`)}
            >
              <CardHeader className="pb-4">
                <div className="flex items-start justify-between gap-4">
                  <CardTitle className="text-lg font-semibold leading-tight group-hover:text-primary transition-colors">
                    {p.name}
                  </CardTitle>
                  <Badge variant={p.status === "published" ? "default" : p.status === "archived" ? "secondary" : "outline"} className="capitalize shrink-0">
                    {p.status}
                  </Badge>
                </div>
                <CardDescription className="line-clamp-2 mt-2 h-10 text-sm">
                  {p.description || "No description provided."}
                </CardDescription>
              </CardHeader>
              <div className="px-6 pb-6 pt-2 text-xs text-slate-500 mt-auto flex items-center justify-between">
                <span>Updated {format(new Date(p.created_at), "MMM d, yyyy")}</span>
                <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-primary transition-colors group-hover:translate-x-1" />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
