"use client";

import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Settings, Shield, Terminal, Key, Database } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="pb-2 border-b border-[#202035]">
        <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          <Settings className="h-5 w-5 text-indigo-400" />
          System Settings & Policies
        </h1>
        <p className="text-xs text-slate-400">
          Autonomy thresholds, security boundaries, and telemetry controls.
        </p>
      </div>

      <div className="space-y-4">
        {/* Security Policies */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-emerald-400" />
              <CardTitle className="text-sm">Autonomy & Human Approval</CardTitle>
            </div>
            <CardDescription>Configure which operations can proceed automatically without prompting.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-2 rounded-lg bg-[#151522]">
              <div>
                <span className="font-semibold text-slate-200">Read Files & Symbols</span>
                <p className="text-[11px] text-slate-400">Inspect codebase within approved roots.</p>
              </div>
              <Badge variant="success">Automatic</Badge>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-[#151522]">
              <div>
                <span className="font-semibold text-slate-200">File Writes & Patches</span>
                <p className="text-[11px] text-slate-400">Modify existing source files with rollback checkpoint.</p>
              </div>
              <Badge variant="success">Automatic</Badge>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-[#151522]">
              <div>
                <span className="font-semibold text-slate-200">Execute Safe Commands</span>
                <p className="text-[11px] text-slate-400">Testing (pytest, npm test) and linting commands.</p>
              </div>
              <Badge variant="success">Automatic</Badge>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-[#151522]">
              <div>
                <span className="font-semibold text-slate-200">Destructive Actions & Deletion</span>
                <p className="text-[11px] text-slate-400">rm -rf, git reset --hard, DROP TABLE operations.</p>
              </div>
              <Badge variant="warning">Requires Approval</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Database & Local Cache */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-indigo-400" />
              <CardTitle className="text-sm">Local Storage & State</CardTitle>
            </div>
            <CardDescription>Local agent cache and temporary logs.</CardDescription>
          </CardHeader>
          <CardContent className="flex justify-between items-center text-xs">
            <div>
              <span className="font-semibold text-slate-200">Purge Agent Audit Cache</span>
              <p className="text-[11px] text-slate-400">Clear local SQLite cache without impacting project memory.</p>
            </div>
            <Button variant="secondary" size="sm" className="text-xs">
              Clear Cache
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
