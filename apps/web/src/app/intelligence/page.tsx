"use client";

import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FolderTree, GitBranch, Layers, ShieldCheck, Binary } from "lucide-react";
import { useDeviceStore } from "@/stores/device-store";

export default function IntelligencePage() {
  const { activeWorkspace } = useDeviceStore();

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between pb-2 border-b border-[#202035]">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <FolderTree className="h-5 w-5 text-indigo-400" />
            Project Intelligence & Memory
          </h1>
          <p className="text-xs text-slate-400">
            Tree-sitter AST symbol graphs, module relationships, and persistent project knowledge.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm">Architectural Graph</CardTitle>
            <CardDescription>Detected module dependencies and call hierarchy</CardDescription>
          </CardHeader>
          <CardContent className="h-64 flex flex-col items-center justify-center text-center text-slate-500">
            <Layers className="h-8 w-8 text-indigo-400/50 mb-2" />
            <p className="text-xs font-semibold text-slate-300">Codebase Indexing Inactive</p>
            <p className="text-[11px] text-slate-500 max-w-sm mt-1">
              Select an approved workspace in the dashboard to trigger Tree-sitter AST extraction.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Persistent Memory</CardTitle>
            <CardDescription>Learned conventions & past decisions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 rounded-lg bg-[#151522] border border-[#212136] text-xs space-y-1">
              <span className="font-semibold text-indigo-400">Project Privacy Mode</span>
              <p className="text-[11px] text-slate-400">Cloud-assisted with path confinement active.</p>
            </div>
            <div className="p-3 rounded-lg bg-[#151522] border border-[#212136] text-xs space-y-1">
              <span className="font-semibold text-indigo-400">Code Conventions</span>
              <p className="text-[11px] text-slate-400">TypeScript strict mode, async/await, modular separation.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
