import { Link, useLocation } from "wouter";
import { Database, Settings, Activity } from "lucide-react";

export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();

  return (
    <div className="flex min-h-screen bg-slate-50 w-full text-slate-900">
      <aside className="w-64 border-r bg-white flex flex-col h-screen sticky top-0 shrink-0 shadow-sm z-10">
        <div className="h-16 flex items-center px-6 border-b border-slate-100">
          <Activity className="w-6 h-6 text-primary mr-3" />
          <span className="font-bold tracking-tight text-slate-800">HDM Engine</span>
        </div>
        <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
          <Link href="/">
            <div className={`flex items-center gap-3 px-3 py-2.5 rounded-md cursor-pointer transition-all ${location === "/" || location.startsWith("/projects") ? "bg-primary text-primary-foreground font-medium shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"}`}>
              <Database className="w-4.5 h-4.5" />
              <span className="text-sm">Projects</span>
            </div>
          </Link>
          <Link href="/settings">
            <div className={`flex items-center gap-3 px-3 py-2.5 rounded-md cursor-pointer transition-all ${location === "/settings" ? "bg-primary text-primary-foreground font-medium shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"}`}>
              <Settings className="w-4.5 h-4.5" />
              <span className="text-sm">Settings</span>
            </div>
          </Link>
        </nav>
        <div className="p-4 border-t border-slate-100 text-xs text-slate-400">
          Healthcare Data Mapping v1.0
        </div>
      </aside>
      <main className="flex-1 flex flex-col min-w-0">
        <div className="p-8 max-w-7xl mx-auto w-full">
          {children}
        </div>
      </main>
    </div>
  );
}
