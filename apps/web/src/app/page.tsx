"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useDeviceStore } from "@/stores/device-store";
import { useUIStore } from "@/stores/ui-store";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Laptop,
  FolderGit2,
  Cpu,
  Zap,
  Play,
  Plus,
  Terminal,
  Activity,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { AgentTask, ProviderAccount } from "@/types";

export default function DashboardPage() {
  const { devices, activeDevice, workspaces, activeWorkspace } = useDeviceStore();
  const { setIsPairingDialogOpen } = useUIStore();
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [providers, setProviders] = useState<ProviderAccount[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [fetchedTasks, fetchedProviders] = await Promise.allSettled([
          api.getTasks(),
          api.getProviders(),
        ]);
        if (fetchedTasks.status === "fulfilled") setTasks(fetchedTasks.value);
        if (fetchedProviders.status === "fulfilled") setProviders(fetchedProviders.value);
      } catch (e) {
        console.error("Dashboard data load error:", e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const isAgentActive = activeDevice && activeDevice.status === "ACTIVE";

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in">
      {/* Hero — forge status */}
      <div className="relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-6 rounded-2xl border border-border bg-surface/70">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-ember/70 to-transparent" />
        <div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-ember/10 blur-3xl" />
        <div className="relative space-y-2">
          <div className="flex items-center gap-2.5">
            <h1 className="font-display text-xl font-bold text-white tracking-tight">Autonomous Engineering Console</h1>
            <Badge variant="ember" className="gap-1 text-[10px]">
              <ShieldCheck className="h-3 w-3" /> Secure sandbox
            </Badge>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                isAgentActive ? "bg-emerald-400 ember-dot" : "bg-slate-600"
              )}
            />
            {isAgentActive ? (
              <span>
                Local agent <span className="font-medium text-emerald-400">live</span> — file operations routed through your paired Windows daemon.
              </span>
            ) : (
              <span>No local agent connected. Pair one to let FORGE work on real files and run commands.</span>
            )}
          </div>
        </div>
        <div className="relative flex items-center gap-2.5">
          <Button
            size="sm"
            onClick={() => setIsPairingDialogOpen(true)}
            className="text-xs gap-1.5 shadow-indigo-600/30"
          >
            <Plus className="h-3.5 w-3.5" />
            Connect Agent
          </Button>
          <Link href="/agent-studio">
            <Button variant="secondary" size="sm" className="text-xs gap-1.5 border-[#2b2b48]">
              <Play className="h-3.5 w-3.5 text-indigo-400" />
              New Coding Task
            </Button>
          </Link>
        </div>
      </div>

      {/* 4 Primary Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <Card className="hover:border-indigo-500/30 transition">
          <CardContent className="flex items-center gap-3 pt-5">
            <div className={`p-3 rounded-xl ${isAgentActive ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"}`}>
              <Laptop className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Local Agent</p>
              <h4 className="text-base font-bold text-slate-100 flex items-center gap-1.5 mt-0.5">
                {isAgentActive ? activeDevice?.name : "Offline / Unpaired"}
              </h4>
              <p className="text-[10px] text-slate-500 mt-0.5">
                {devices.length} registered workstation{devices.length === 1 ? "" : "s"}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Metric 2 */}
        <Card className="hover:border-indigo-500/30 transition">
          <CardContent className="flex items-center gap-3 pt-5">
            <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400">
              <FolderGit2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Active Workspace</p>
              <h4 className="text-base font-bold text-slate-100 truncate max-w-[130px] mt-0.5">
                {activeWorkspace ? activeWorkspace.name : "None Selected"}
              </h4>
              <p className="text-[10px] text-slate-500 mt-0.5">
                {workspaces.length} allowed root path{workspaces.length === 1 ? "" : "s"}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Metric 3 */}
        <Card className="hover:border-indigo-500/30 transition">
          <CardContent className="flex items-center gap-3 pt-5">
            <div className="p-3 rounded-xl bg-violet-500/10 text-violet-400">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Model Providers</p>
              <h4 className="text-base font-bold text-slate-100 mt-0.5">
                {providers.filter((p) => p.is_enabled).length} Enabled
              </h4>
              <p className="text-[10px] text-slate-500 mt-0.5">Multi-Provider Router</p>
            </div>
          </CardContent>
        </Card>

        {/* Metric 4 */}
        <Card className="hover:border-indigo-500/30 transition">
          <CardContent className="flex items-center gap-3 pt-5">
            <div className="p-3 rounded-xl bg-ember/10 text-ember-hot">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Active Tasks</p>
              <h4 className="text-base font-bold text-slate-100 mt-0.5">
                {tasks.filter((t) => t.status === "EXECUTING" || t.status === "PLANNING").length} Running
              </h4>
              <p className="text-[10px] text-slate-500 mt-0.5">{tasks.length} total sessions</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid: Recent Sessions & Agent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Recent Tasks / Sessions (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle>Autonomous Tasks</CardTitle>
                <CardDescription>Multi-step coding sessions and verification status</CardDescription>
              </div>
              <Link href="/agent-studio" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium">
                Open Studio <ArrowRight className="h-3 w-3" />
              </Link>
            </CardHeader>
            <CardContent>
              {tasks.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <div className="h-10 w-10 rounded-full bg-[#1c1c2c] flex items-center justify-center text-slate-400 mb-3">
                    <Terminal className="h-5 w-5 text-indigo-400" />
                  </div>
                  <h4 className="text-sm font-semibold text-slate-200">No active engineering tasks</h4>
                  <p className="text-xs text-slate-500 max-w-sm mt-1 mb-4">
                    Give FORGE AI a feature to implement, a bug to diagnose, or an entire repo to inspect.
                  </p>
                  <Link href="/agent-studio">
                    <Button size="sm" variant="outline" className="text-xs">
                      Create First Task
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {tasks.slice(0, 5).map((task) => (
                    <div
                      key={task.id}
                      className="flex items-center justify-between p-3 rounded-lg bg-[#151522] border border-[#212136] hover:border-indigo-500/30 transition"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-200">{task.description}</span>
                          <Badge variant={task.status === "COMPLETED" ? "success" : "default"} className="text-[10px]">
                            {task.status}
                          </Badge>
                        </div>
                        <div className="text-[10px] text-slate-500 flex items-center gap-2">
                          <span>Complexity: {task.complexity}</span>
                          <span>•</span>
                          <span>Steps: {task.completed_steps?.length || 0}</span>
                        </div>
                      </div>
                      <Link href={`/agent-studio?task=${task.id}`}>
                        <Button variant="ghost" size="sm" className="h-7 text-xs">
                          Inspect
                        </Button>
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Actions Panel */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Link href="/workspace" className="block group">
              <div className="p-4 rounded-xl border border-[#232338] bg-[#12121a]/70 hover:border-indigo-500/40 hover:bg-[#161624] transition space-y-1.5">
                <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs group-hover:text-indigo-300">
                  <Terminal className="h-4 w-4" /> Code Workspace
                </div>
                <p className="text-[11px] text-slate-400">Browse repo tree, inspect files, and review git diffs.</p>
              </div>
            </Link>

            <Link href="/models" className="block group">
              <div className="p-4 rounded-xl border border-[#232338] bg-[#12121a]/70 hover:border-indigo-500/40 hover:bg-[#161624] transition space-y-1.5">
                <div className="flex items-center gap-2 text-violet-400 font-semibold text-xs group-hover:text-violet-300">
                  <Cpu className="h-4 w-4" /> Multi-Model Hub
                </div>
                <p className="text-[11px] text-slate-400">Configure NIM, Gemini, Groq, DeepSeek, or local Ollama.</p>
              </div>
            </Link>

            <Link href="/intelligence" className="block group">
              <div className="p-4 rounded-xl border border-[#232338] bg-[#12121a]/70 hover:border-indigo-500/40 hover:bg-[#161624] transition space-y-1.5">
                <div className="flex items-center gap-2 text-cyan-400 font-semibold text-xs group-hover:text-cyan-300">
                  <Activity className="h-4 w-4" /> Architecture Map
                </div>
                <p className="text-[11px] text-slate-400">Tree-sitter symbol indexing and codebase diagnostics.</p>
              </div>
            </Link>
          </div>
        </div>

        {/* Right: Connected Agent Diagnostics (1 col) */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Agent Health & Sandbox</CardTitle>
              <CardDescription>Security and execution status</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between text-xs py-1 border-b border-[#1c1c2e]">
                <span className="text-slate-400">Status</span>
                <span className={`font-semibold ${isAgentActive ? "text-emerald-400" : "text-rose-400"}`}>
                  {isAgentActive ? "ONLINE & READY" : "DISCONNECTED"}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs py-1 border-b border-[#1c1c2e]">
                <span className="text-slate-400">OS Target</span>
                <span className="text-slate-200 font-mono text-[11px]">
                  {activeDevice?.device_type || "Windows x64"}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs py-1 border-b border-[#1c1c2e]">
                <span className="text-slate-400">Sandbox Boundary</span>
                <span className="text-emerald-400 font-medium">Path Confinement</span>
              </div>
              <div className="flex items-center justify-between text-xs py-1 border-b border-[#1c1c2e]">
                <span className="text-slate-400">Terminal Policy</span>
                <span className="text-indigo-400 font-medium">5-Tier Risk Filter</span>
              </div>

              {!isAgentActive && (
                <div className="pt-2">
                  <Button
                    size="sm"
                    className="w-full text-xs"
                    onClick={() => setIsPairingDialogOpen(true)}
                  >
                    Pair Local Workspace
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Supported Providers List */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Configured Adapters</CardTitle>
              <CardDescription>Active model routing nodes</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-1.5">
                {["NVIDIA NIM", "Google Gemini", "Groq", "Cerebras", "DeepSeek", "Mistral", "Ollama"].map((name) => (
                  <Badge key={name} variant="outline" className="text-[10px] bg-[#141420]">
                    {name}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
