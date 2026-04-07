import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Shield, Globe } from "lucide-react";
import { setBaseUrl } from "@/api";

export function Settings() {
  const { toast } = useToast();
  const [userId, setUserId] = useState("");
  const [userRole, setUserRole] = useState("viewer");
  const [apiUrl, setApiUrl] = useState("");

  useEffect(() => {
    setUserId(localStorage.getItem("mapping-user-id") || "anonymous");
    setUserRole(localStorage.getItem("mapping-user-role") || "viewer");
    setApiUrl(localStorage.getItem("mapping-api-base-url") || import.meta.env.VITE_API_BASE_URL || "");
  }, []);

  const handleSaveIdentity = () => {
    localStorage.setItem("mapping-user-id", userId);
    localStorage.setItem("mapping-user-role", userRole);
    toast({ title: "Identity saved", description: "API access credentials updated." });
  };

  const handleSaveApiUrl = () => {
    localStorage.setItem("mapping-api-base-url", apiUrl);
    setBaseUrl(apiUrl || null);
    toast({ title: "API URL saved", description: apiUrl ? `Requests will be sent to ${apiUrl}` : "Base URL cleared. Using relative paths." });
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900" data-testid="text-settings-title">System Configuration</h1>
        <p className="text-slate-500 mt-2">Manage API connection and simulated RBAC headers.</p>
      </div>

      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="bg-slate-50/50 border-b border-slate-100 pb-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <Globe className="w-5 h-5 text-blue-500" /> API Connection
          </CardTitle>
          <CardDescription>The base URL of the Healthcare Data Mapping API server.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5 pt-6">
          <div className="space-y-2">
            <Label htmlFor="apiUrl" className="text-slate-700">API Base URL</Label>
            <Input 
              id="apiUrl" 
              data-testid="input-api-url"
              value={apiUrl} 
              onChange={(e) => setApiUrl(e.target.value)} 
              placeholder="e.g. http://localhost:8000 or https://api.example.com" 
              className="font-mono bg-slate-50"
            />
            <p className="text-xs text-slate-500">
              Leave empty to use relative paths. Set to the full URL of your API server (without trailing slash).
            </p>
          </div>
        </CardContent>
        <CardFooter className="bg-slate-50/50 border-t border-slate-100 pt-4">
          <Button onClick={handleSaveApiUrl} className="w-full sm:w-auto" data-testid="button-save-api-url">Save API URL</Button>
        </CardFooter>
      </Card>

      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="bg-slate-50/50 border-b border-slate-100 pb-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-500" /> API Access Identity
          </CardTitle>
          <CardDescription>Sent with every REST request via X-User-Id and X-User-Role headers.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5 pt-6">
          <div className="space-y-2">
            <Label htmlFor="userId" className="text-slate-700">X-User-Id</Label>
            <Input 
              id="userId" 
              data-testid="input-user-id"
              value={userId} 
              onChange={(e) => setUserId(e.target.value)} 
              placeholder="e.g. jdoe-456" 
              className="font-mono bg-slate-50"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="userRole" className="text-slate-700">X-User-Role</Label>
            <Select value={userRole} onValueChange={setUserRole}>
              <SelectTrigger className="bg-slate-50" data-testid="select-user-role">
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="viewer">Viewer (Read-only)</SelectItem>
                <SelectItem value="analyst">Analyst (Mapping Editor)</SelectItem>
                <SelectItem value="approver">Approver (Status Admin)</SelectItem>
                <SelectItem value="admin">Administrator (Full Access)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
        <CardFooter className="bg-slate-50/50 border-t border-slate-100 pt-4">
          <Button onClick={handleSaveIdentity} className="w-full sm:w-auto" data-testid="button-save-identity">Update Identity</Button>
        </CardFooter>
      </Card>
    </div>
  );
}
