"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FolderTree, Layers, Loader2, RefreshCw, Search, Boxes, FileCode } from "lucide-react";
import { api } from "@/lib/api";
import { IndexStatus, SymbolHit } from "@/types";

export default function IntelligencePage() {
  const [status, setStatus] = useState<IndexStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [indexing, setIndexing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SymbolHit[] | null>(null);
  const [searching, setSearching] = useState(false);

  const load = useCallback(async () => {
    try {
      setStatus(await api.getIndexStatus());
      setError(null);
    } catch (e: any) {
      setError(e.message || "Could not load index status.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const reindex = async () => {
    setIndexing(true);
    setError(null);
    try {
      await api.reindexWorkspace();
      await load();
    } catch (e: any) {
      setError(e.message || "Indexing failed.");
    } finally {
      setIndexing(false);
    }
  };

  const runSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    setError(null);
    try {
      const res = await api.searchSymbols(q);
      setResults(res.results);
    } catch (e: any) {
      setError(e.message || "Search failed.");
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const stats = status?.stats;
  const connected = status?.connected;
  const hasIndex = !!stats && stats.files > 0;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-3 pb-2 border-b border-[#202035]">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <FolderTree className="h-5 w-5 text-indigo-400" />
            Code Intelligence
          </h1>
          <p className="text-xs text-slate-400">
            Symbol index of your active workspace, built by the local agent.
            {status?.workspace_path ? <span className="font-mono text-slate-500"> · {status.workspace_path}</span> : null}
          </p>
        </div>
        {connected && (
          <Button size="sm" variant="outline" onClick={reindex} disabled={indexing} className="shrink-0">
            {indexing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{indexing ? "Indexing…" : hasIndex ? "Reindex" : "Index now"}</span>
          </Button>
        )}
      </div>

      {error && (
        <div className="text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/25 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-slate-400 py-10 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading index…
        </div>
      ) : !connected ? (
        <Card>
          <CardContent className="h-56 flex flex-col items-center justify-center text-center text-slate-500">
            <Layers className="h-8 w-8 text-indigo-400/50 mb-2" />
            <p className="text-xs font-semibold text-slate-300">No local agent connected</p>
            <p className="text-[11px] text-slate-500 max-w-sm mt-1">
              Connect a paired agent and select a workspace to index your codebase. Indexing runs entirely on your
              machine.
            </p>
          </CardContent>
        </Card>
      ) : !hasIndex ? (
        <Card>
          <CardContent className="h-56 flex flex-col items-center justify-center text-center text-slate-500">
            <Boxes className="h-8 w-8 text-indigo-400/50 mb-2" />
            <p className="text-xs font-semibold text-slate-300">Workspace not indexed yet</p>
            <p className="text-[11px] text-slate-500 max-w-sm mt-1">
              Click <span className="text-slate-300 font-medium">Index now</span> to scan the active workspace and build
              the symbol index (Python &amp; TypeScript/JavaScript).
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Real stats from the agent's index */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatTile label="Files indexed" value={stats!.files} />
            <StatTile label="Symbols" value={stats!.symbols} />
            <StatTile label="Lines of code" value={stats!.total_lines} />
            <StatTile label="Languages" value={stats!.languages.length} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Symbol search */}
            <Card className="md:col-span-2">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Symbol Search</CardTitle>
                <CardDescription>Find functions, classes, and components across the codebase.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <form onSubmit={runSearch} className="flex items-center gap-2">
                  <div className="flex items-center gap-2 flex-1 bg-[#151522] border border-[#26263d] rounded-lg px-2.5">
                    <Search className="h-3.5 w-3.5 text-slate-500" />
                    <input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="e.g. handleSave, ConnectionManager…"
                      className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none py-2"
                    />
                  </div>
                  <Button size="sm" type="submit" disabled={searching || !query.trim()}>
                    {searching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Search"}
                  </Button>
                </form>
                {results !== null && (
                  <div className="space-y-1 max-h-80 overflow-y-auto">
                    {results.length === 0 ? (
                      <p className="text-[11px] text-slate-500 py-2">No symbols matched “{query}”.</p>
                    ) : (
                      results.map((r, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs rounded-lg bg-[#151522] px-2.5 py-1.5">
                          <FileCode className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                          <span className="font-mono text-slate-200">{r.name}</span>
                          <Badge variant="outline" className="text-[9px] py-0 px-1.5">{r.kind}</Badge>
                          <span className="text-[10px] text-slate-500 truncate ml-auto font-mono">
                            {r.file_path}:{r.line}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Language + symbol-kind breakdown */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Breakdown</CardTitle>
                <CardDescription>By language &amp; symbol kind</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div>
                  <p className="text-[11px] font-medium text-slate-400 mb-1.5">Languages</p>
                  <div className="flex flex-wrap gap-1.5">
                    {stats!.languages.map((l) => (
                      <Badge key={l.language} variant="outline" className="text-[10px] bg-[#141420]">
                        {l.language} · {l.files}
                      </Badge>
                    ))}
                  </div>
                </div>
                {stats!.symbol_kinds.length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium text-slate-400 mb-1.5">Symbol kinds</p>
                    <div className="flex flex-wrap gap-1.5">
                      {stats!.symbol_kinds.map((k) => (
                        <Badge key={k.kind} variant="outline" className="text-[10px] bg-[#141420]">
                          {k.kind} · {k.count}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-surface/70 p-3">
      <p className="text-[11px] text-slate-400">{label}</p>
      <p className="text-xl font-bold text-white tabular-nums">{value.toLocaleString()}</p>
    </div>
  );
}
