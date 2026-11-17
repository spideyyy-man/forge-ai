"use client";

import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Settings, Shield, Loader2, AlertTriangle, Check } from "lucide-react";
import { api } from "@/lib/api";
import { ApprovalMode } from "@/types";

// Human-facing copy for each operation class the policy governs.
const CLASS_META: Record<string, { title: string; desc: string }> = {
  file_read: { title: "Read Files & Symbols", desc: "Inspect code within approved workspace roots." },
  file_write: { title: "File Writes & Patches", desc: "Modify or create files (each write is recorded and revertable)." },
  command_exec: { title: "Run Commands", desc: "Run shell commands such as tests, builds, and linters." },
  git_commit: { title: "Git Commits", desc: "Commit changes in the workspace repository." },
};
const CLASS_ORDER = ["file_read", "file_write", "command_exec", "git_commit"];

export default function SettingsPage() {
  const [modes, setModes] = useState<Record<string, ApprovalMode> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .getApprovalPolicy()
      .then((p) => setModes(p.modes))
      .catch((e) => setError(e.message || "Could not load settings."))
      .finally(() => setLoading(false));
  }, []);

  const setMode = async (cls: string, mode: ApprovalMode) => {
    if (!modes || modes[cls] === mode) return;
    const next = { ...modes, [cls]: mode };
    const prev = modes;
    setModes(next); // optimistic
    setSaving(cls);
    setError(null);
    setSaved(false);
    try {
      const res = await api.updateApprovalPolicy(next);
      setModes(res.modes); // server-normalized (floor can't be weakened here)
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } catch (e: any) {
      setModes(prev); // roll back on failure
      setError(e.message || "Could not save. Change not applied.");
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="pb-2 border-b border-[#202035]">
        <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          <Settings className="h-5 w-5 text-indigo-400" />
          Settings & Policies
        </h1>
        <p className="text-xs text-slate-400">Control when the agent may act on its own versus ask you first.</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-400" />
            <CardTitle className="text-sm">Autonomy & Human Approval</CardTitle>
            {saved && (
              <span className="flex items-center gap-1 text-[11px] text-emerald-400">
                <Check className="h-3 w-3" /> Saved
              </span>
            )}
          </div>
          <CardDescription>
            Enforced by FORGE AI itself, not the model. “Approve” pauses the run for your decision; “Auto” lets it proceed.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          {error && (
            <div className="text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/25 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
          {loading || !modes ? (
            <div className="flex items-center gap-2 text-slate-400 py-4">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading policy…
            </div>
          ) : (
            CLASS_ORDER.filter((c) => c in modes).map((cls) => (
              <div key={cls} className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-[#151522]">
                <div className="min-w-0">
                  <span className="font-semibold text-slate-200">{CLASS_META[cls]?.title ?? cls}</span>
                  <p className="text-[11px] text-slate-400">{CLASS_META[cls]?.desc}</p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {saving === cls && <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-400" />}
                  {(["approve", "auto"] as ApprovalMode[]).map((m) => {
                    const active = modes[cls] === m;
                    return (
                      <button
                        key={m}
                        onClick={() => setMode(cls, m)}
                        disabled={saving === cls}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition border ${
                          active
                            ? m === "auto"
                              ? "bg-amber-500/15 border-amber-500/40 text-amber-300"
                              : "bg-emerald-500/15 border-emerald-500/40 text-emerald-300"
                            : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-[#1c1c2c]"
                        } disabled:opacity-50`}
                        aria-pressed={active}
                      >
                        {m === "auto" ? "Auto" : "Ask first"}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          )}
          <div className="flex items-start gap-2 text-[11px] text-slate-400 pt-1">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400 mt-px" />
            <span>
              Safety floor: high-risk commands (<code>git push</code>, <code>rm -rf</code>, <code>git reset --hard</code>,
              piped installers, …) always require approval, even with “Run Commands” set to Auto.
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
