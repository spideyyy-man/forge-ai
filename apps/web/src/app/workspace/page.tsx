"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useDeviceStore } from "@/stores/device-store";
import { useUIStore } from "@/stores/ui-store";
import {
  Code2,
  Folder,
  FolderOpen,
  FolderPlus,
  Laptop,
  ArrowRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

export default function WorkspacePage() {
  const { devices, workspaces, activeDevice, activeWorkspace, createWorkspace, activateWorkspace } = useDeviceStore();
  const { setIsPairingDialogOpen } = useUIStore();

  const [name, setName] = useState("");
  const [rootPath, setRootPath] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const linkedDevice = activeDevice && activeDevice.status === "ACTIVE" ? activeDevice : devices.find((d) => d.status === "ACTIVE") || null;
  const canOpen = !!linkedDevice;

  // Browser dir picker can give us the folder NAME, but not an absolute path (by design).
  // We use it only to prefill the label; the user confirms the real path the agent will use.
  const handleBrowse = async () => {
    setError(null);
    const picker = (window as any).showDirectoryPicker;
    if (!picker) {
      setError("Your browser can't open a folder picker — type the folder's full path below instead.");
      return;
    }
    try {
      const handle = await picker();
      if (handle?.name && !name) setName(handle.name);
      if (handle?.name) {
        setError(
          `Picked “${handle.name}”. Browsers can't read the full path for security — paste the absolute path to this folder below (e.g. D:\\code\\${handle.name}).`
        );
      }
    } catch {
      /* user cancelled */
    }
  };

  const handleOpen = async () => {
    if (!linkedDevice || !rootPath.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const derivedName = name.trim() || rootPath.trim().replace(/[\\/]+$/, "").split(/[\\/]/).pop() || "Workspace";
      await createWorkspace({ device_id: linkedDevice.id, name: derivedName, root_path: rootPath.trim() });
      setName("");
      setRootPath("");
    } catch (err: any) {
      setError(err.message || "Could not open that folder.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Code2 className="h-5 w-5 text-ember" />
            Workspace
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Pick a folder on your paired machine. The agent works only inside folders you open here.
          </p>
        </div>
        {activeWorkspace && (
          <Badge variant="ember" className="text-[11px] font-mono max-w-[260px] truncate">
            {activeWorkspace.root_path}
          </Badge>
        )}
      </div>

      {/* No agent → must pair first (folder access runs through the local agent). */}
      {!canOpen ? (
        <Card className="border-ember/20">
          <CardContent className="py-10 flex flex-col items-center text-center gap-3">
            <div className="p-3 rounded-xl bg-ember/10 text-ember">
              <Laptop className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-slate-200">Connect your machine first</h3>
              <p className="text-xs text-muted-foreground max-w-sm">
                Opening a folder needs a paired local agent — that&apos;s what gives the agent safe, scoped access to
                your files and terminal.
              </p>
            </div>
            <Button size="sm" onClick={() => setIsPairingDialogOpen(true)}>
              <Laptop className="h-4 w-4" />
              Connect Agent
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          {/* Open a folder */}
          <Card className="lg:col-span-3">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <FolderPlus className="h-4 w-4 text-ember" />
                Open a folder
              </CardTitle>
              <CardDescription>
                Bound to <span className="text-slate-300 font-medium">{linkedDevice!.name}</span>. Use the folder&apos;s full
                path on that machine.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className="text-[11px] text-muted-foreground font-medium block mb-1">Folder path</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={rootPath}
                    onChange={(e) => setRootPath(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleOpen()}
                    placeholder="D:\code\my-project"
                    className="flex-1 text-xs font-mono bg-surface border border-border rounded-lg px-3 py-2 text-slate-200 placeholder:text-muted-foreground focus:outline-none focus:border-ember/60"
                  />
                  <Button variant="outline" size="sm" className="text-xs shrink-0" onClick={handleBrowse}>
                    <FolderOpen className="h-3.5 w-3.5" />
                    Browse
                  </Button>
                </div>
              </div>
              <div>
                <label className="text-[11px] text-muted-foreground font-medium block mb-1">
                  Label <span className="text-slate-600">(optional)</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleOpen()}
                  placeholder="Defaults to the folder name"
                  className="w-full text-xs bg-surface border border-border rounded-lg px-3 py-2 text-slate-200 placeholder:text-muted-foreground focus:outline-none focus:border-ember/60"
                />
              </div>

              {error && (
                <div className="flex items-start gap-2 text-[11px] rounded-lg p-2.5 bg-amber-500/10 border border-amber-500/25 text-amber-300">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <Button size="sm" className="w-full" onClick={handleOpen} disabled={busy || !rootPath.trim()}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FolderOpen className="h-4 w-4" />}
                Open workspace
              </Button>
            </CardContent>
          </Card>

          {/* Open folders + next step */}
          <Card className="lg:col-span-2">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Folder className="h-4 w-4 text-iris" />
                Your folders
              </CardTitle>
              <CardDescription>{workspaces.length} open</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {workspaces.length === 0 ? (
                <p className="text-xs text-muted-foreground py-4 text-center">No folders open yet.</p>
              ) : (
                workspaces.map((ws) => {
                  const isActive = activeWorkspace?.id === ws.id;
                  return (
                    <button
                      key={ws.id}
                      onClick={() => activateWorkspace(ws)}
                      className={`w-full text-left rounded-lg border px-3 py-2 transition ${
                        isActive
                          ? "border-ember/40 bg-ember/5"
                          : "border-border hover:border-border-strong hover:bg-surface-elevated"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Folder className={`h-3.5 w-3.5 ${isActive ? "text-ember" : "text-muted-foreground"}`} />
                        <span className="text-xs font-medium text-slate-200 truncate">{ws.name}</span>
                        {isActive && <CheckCircle2 className="h-3.5 w-3.5 text-ember ml-auto" />}
                      </div>
                      <p className="text-[10px] font-mono text-muted-foreground truncate mt-0.5 pl-5">{ws.root_path}</p>
                    </button>
                  );
                })
              )}

              {activeWorkspace && (
                <Link href="/agent-studio" className="block pt-2">
                  <Button size="sm" className="w-full">
                    Start coding in Agent Studio
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
