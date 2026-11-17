"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { ProviderAccount } from "@/types";
import {
  Cpu,
  Search,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ExternalLink,
  KeyRound,
  Loader2,
  ShieldCheck,
} from "lucide-react";

type Catalog = {
  id: string;
  type: string; // backend ProviderType enum value (what we persist)
  name: string;
  desc: string;
  keyUrl: string | null; // where to obtain an API key
  local?: boolean;
  custom?: boolean; // OpenAI-compatible endpoint: needs a base URL (freellmapi, LM Studio, vLLM…)
  free?: string; // short label if the provider offers free usage; omit if paid-only
};

// Provider catalog. `type` must match a backend ProviderType enum value.
// `keyUrl` points at each provider's official API-key console.
// `free` reflects the provider's free offering at the time of writing — these change,
// so the UI shows a "confirm current limits" caveat.
const PROVIDERS: Catalog[] = [
  { id: "nvidia", type: "NVIDIA", name: "NVIDIA NIM", desc: "Llama 3, DeepSeek-R1 and more via NVIDIA inference.", keyUrl: "https://build.nvidia.com/settings/api-keys", free: "Free credits to start" },
  { id: "gemini", type: "GOOGLE", name: "Google Gemini", desc: "Long-context, multimodal models.", keyUrl: "https://aistudio.google.com/app/apikey", free: "Free tier (rate-limited)" },
  { id: "groq", type: "GROQ", name: "Groq", desc: "Very low-latency inference on LPUs.", keyUrl: "https://console.groq.com/keys", free: "Free tier (rate-limited)" },
  { id: "cerebras", type: "CEREBRAS", name: "Cerebras", desc: "High-throughput token generation.", keyUrl: "https://cloud.cerebras.ai/platform/apikeys", free: "Free tier (daily limits)" },
  { id: "deepseek", type: "DEEPSEEK", name: "DeepSeek", desc: "DeepSeek-Coder and V3 reasoning models.", keyUrl: "https://platform.deepseek.com/api_keys" },
  { id: "openrouter", type: "OPENROUTER", name: "OpenRouter", desc: "One key, many models — unified gateway.", keyUrl: "https://openrouter.ai/keys", free: "Free models available (:free)" },
  { id: "mistral", type: "MISTRAL", name: "Mistral AI", desc: "Codestral and Mistral Large.", keyUrl: "https://console.mistral.ai/api-keys/", free: "Free experiment tier" },
  { id: "anthropic", type: "ANTHROPIC", name: "Anthropic", desc: "Claude models for coding and reasoning.", keyUrl: "https://console.anthropic.com/settings/keys" },
  { id: "openai", type: "OPENAI", name: "OpenAI", desc: "GPT models and tool use.", keyUrl: "https://platform.openai.com/api-keys" },
  { id: "github", type: "GITHUB", name: "GitHub Models", desc: "Free models (GPT-4o, Llama, Phi, Mistral) using a GitHub token.", keyUrl: "https://github.com/settings/tokens", free: "Free with a GitHub account" },
  { id: "sambanova", type: "SAMBANOVA", name: "SambaNova", desc: "Very fast Llama inference on RDUs.", keyUrl: "https://cloud.sambanova.ai/apis", free: "Free tier (rate-limited)" },
  { id: "ollama", type: "OLLAMA", name: "Ollama (Local)", desc: "Fully private, local inference — no key needed.", keyUrl: null, local: true, free: "Free — runs locally" },
  { id: "custom", type: "CUSTOM", name: "Custom / OpenAI-compatible", desc: "Any OpenAI-compatible endpoint — freellmapi router, LM Studio, vLLM, or a proxy.", keyUrl: null, custom: true, free: "Depends on endpoint" },
];

export default function ModelsPage() {
  const [query, setQuery] = useState("");
  const [accounts, setAccounts] = useState<ProviderAccount[]>([]);
  const [configuring, setConfiguring] = useState<Catalog | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: "ok" | "err"; msg: string } | null>(null);

  const refresh = async () => {
    try {
      setAccounts(await api.getProviders());
    } catch {
      /* unauthenticated or backend down — leave empty, cards still show */
    }
  };
  useEffect(() => {
    refresh();
  }, []);

  // Close the configure dialog on Escape.
  useEffect(() => {
    if (!configuring) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setConfiguring(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [configuring]);

  // Map ProviderType -> its configured accounts (multiple keys per provider → rotation).
  const byType = useMemo(() => {
    const m = new Map<string, ProviderAccount[]>();
    for (const a of accounts) {
      const k = a.provider_type.toUpperCase();
      m.set(k, [...(m.get(k) || []), a]);
    }
    return m;
  }, [accounts]);
  const acctsFor = (type: string) => byType.get(type) || [];

  const handleDelete = async (id: string) => {
    // Deleting a key is destructive and can't be undone — confirm first.
    if (!window.confirm("Remove this API key? The agent can no longer use this provider until you add a key again.")) return;
    try {
      await api.deleteProvider(id);
      await refresh();
    } catch (err: any) {
      setFeedback({ type: "err", msg: err.message || "Could not remove the key." });
    }
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return PROVIDERS;
    return PROVIDERS.filter((p) => `${p.name} ${p.id} ${p.desc}`.toLowerCase().includes(q));
  }, [query]);

  const openConfigure = (p: Catalog) => {
    setConfiguring(p);
    setApiKey("");
    setBaseUrl(p.custom && acctsFor(p.type)[0]?.base_url ? acctsFor(p.type)[0]!.base_url! : "");
    setFeedback(null);
  };

  const handleSave = async () => {
    if (!configuring) return;
    if (!apiKey.trim()) {
      setFeedback({ type: "err", msg: "Enter an API key first." });
      return;
    }
    if (configuring.custom && !baseUrl.trim()) {
      setFeedback({ type: "err", msg: "Enter the endpoint base URL (e.g. http://localhost:8080/v1)." });
      return;
    }
    setSaving(true);
    setFeedback(null);
    try {
      await api.createProvider({
        provider_type: configuring.type,
        display_name: configuring.name,
        api_key: apiKey.trim(),
        ...(configuring.custom ? { base_url: baseUrl.trim() } : {}),
      });
      setApiKey("");
      setFeedback({
        type: "ok",
        msg: configuring.custom
          ? "Endpoint saved (encrypted). Hit Test connection to confirm it reaches your models."
          : `${configuring.name} key saved (encrypted). You can test it below.`,
      });
      await refresh();
    } catch (err: any) {
      setFeedback({ type: "err", msg: err.message || "Could not save." });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (account: ProviderAccount) => {
    setTesting(account.id);
    setFeedback(null);
    try {
      const res = await api.testProvider(account.id);
      if (res.success) {
        setFeedback({ type: "ok", msg: `Connected — ${res.models_found ?? 0} models, ${res.latency_ms ?? "?"}ms.` });
      } else {
        setFeedback({ type: "err", msg: res.error || "Validation failed." });
      }
      await refresh();
    } catch (err: any) {
      setFeedback({ type: "err", msg: err.message || "Test request failed." });
    } finally {
      setTesting(null);
    }
  };

  const configuredCount = accounts.length;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Cpu className="h-5 w-5 text-ember" />
            Model Providers
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Bring your own keys. Stored encrypted on your machine, never sent to the browser.
          </p>
        </div>
        <Badge variant="outline" className="text-[11px]">
          {configuredCount} connected
        </Badge>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search providers…"
          className="w-full text-sm bg-surface border border-border rounded-lg pl-9 pr-3 py-2 text-slate-200 placeholder:text-muted-foreground focus:outline-none focus:border-ember/60 transition"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((prov) => {
          const accts = acctsFor(prov.type);
          const account = accts[0];
          const connected = accts.length > 0;
          const validated = accts.some((a) => a.is_validated);
          return (
            <Card
              key={prov.id}
              className={`flex flex-col justify-between transition ${
                connected ? "border-ember/30" : "hover:border-border-strong"
              }`}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between gap-2">
                  <CardTitle className="text-sm font-semibold">{prov.name}</CardTitle>
                  <div className="flex items-center gap-1.5">
                    {accts.length > 1 && (
                      <Badge variant="outline" className="text-[10px]">{accts.length} keys</Badge>
                    )}
                    {validated ? (
                      <Badge variant="success" className="text-[10px] gap-1">
                        <ShieldCheck className="h-3 w-3" /> Validated
                      </Badge>
                    ) : connected ? (
                      <Badge variant="ember" className="text-[10px]">Key saved</Badge>
                    ) : prov.local ? (
                      <Badge variant="info" className="text-[10px]">Local</Badge>
                    ) : null}
                  </div>
                </div>
                <CardDescription className="text-xs line-clamp-2">{prov.desc}</CardDescription>
                {prov.free && (
                  <div className="mt-1.5 inline-flex items-center gap-1 text-[10px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2 py-0.5 w-fit">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    {prov.free}
                  </div>
                )}
              </CardHeader>
              <CardContent className="pt-2 flex gap-2">
                <Button
                  variant={connected ? "outline" : "secondary"}
                  size="sm"
                  className="flex-1 text-xs"
                  onClick={() => openConfigure(prov)}
                >
                  <KeyRound className="h-3.5 w-3.5" />
                  {connected ? "Manage" : prov.local ? "Set up" : "Configure"}
                </Button>
                {account && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs"
                    onClick={() => handleTest(account)}
                    disabled={testing === account.id}
                    title="Validate the saved key against the provider"
                  >
                    {testing === account.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3.5 w-3.5" />
                    )}
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
        {filtered.length === 0 && (
          <div className="col-span-full text-center text-sm text-muted-foreground py-10">
            No providers match “{query}”.
          </div>
        )}
      </div>

      {/* Configure dialog — opens centered on click (two paths: get a key, or enter one) */}
      {configuring && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          onClick={() => setConfiguring(null)}
        >
          <div className="w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
            <Card className="border-ember/30 bg-surface-elevated shadow-2xl animate-in">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Configure {configuring.name}</CardTitle>
              <button
                onClick={() => setConfiguring(null)}
                className="text-xs text-muted-foreground hover:text-slate-200 transition"
              >
                Close
              </button>
            </div>
            <CardDescription>
              {configuring.local
                ? "Ollama runs locally — no API key required. Install it and pull a model to use private inference."
                : configuring.custom
                ? "Connect any OpenAI-compatible endpoint (freellmapi, LM Studio, vLLM, a proxy). FORGE routes through it and auto-discovers its models. Base URL + key are encrypted at rest."
                : "Two steps: get a key from the provider, then paste it here. Keys are encrypted at rest."}
            </CardDescription>
            {configuring.free ? (
              <div className="mt-2 flex items-start gap-2 text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-2.5 py-1.5">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" />
                <span>
                  <span className="font-medium">{configuring.free}.</span> Free tiers and credits change —
                  confirm current limits on the provider&apos;s site.
                </span>
              </div>
            ) : (
              !configuring.local && (
                <div className="mt-2 text-[11px] text-muted-foreground">
                  No free tier — this provider is paid (usage billed to your account).
                </div>
              )
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {configuring.custom && (
              <div className="space-y-3">
                <div>
                  <label className="text-[11px] text-muted-foreground font-medium block mb-1">Endpoint base URL</label>
                  <input
                    type="text"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="http://localhost:8080/v1  or  https://your-freellmapi/v1"
                    className="w-full text-xs font-mono bg-surface border border-border rounded-lg px-3 py-2 text-slate-200 placeholder:text-muted-foreground focus:outline-none focus:border-ember/60"
                  />
                  <p className="text-[11px] text-muted-foreground mt-1">
                    Point this at your freellmapi router, LM Studio, vLLM, or any OpenAI-compatible server. Include the
                    <span className="font-mono"> /v1</span> path. FORGE auto-discovers the models it serves.
                  </p>
                </div>
                <div>
                  <label className="text-[11px] text-muted-foreground font-medium block mb-1">API key</label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSave()}
                    placeholder="Router / endpoint key — use any value (e.g. 'none') if it needs no auth"
                    className="w-full text-xs font-mono bg-surface border border-border rounded-lg px-3 py-2 text-slate-200 placeholder:text-muted-foreground focus:outline-none focus:border-ember/60"
                  />
                </div>
                <Button size="sm" className="w-full text-xs" onClick={handleSave} disabled={saving || !apiKey.trim() || !baseUrl.trim()}>
                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                  Save endpoint
                </Button>
              </div>
            )}

            {!configuring.local && !configuring.custom && (
              <div className="grid gap-4 sm:grid-cols-2">
                {/* Option 1: where to get a key */}
                <div className="rounded-lg border border-border p-3 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-iris/15 text-iris text-[11px]">1</span>
                    Get an API key
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Opens {configuring.name}&apos;s key console in a new tab. Create a key, then copy it.
                  </p>
                  <a href={configuring.keyUrl ?? "#"} target="_blank" rel="noopener noreferrer">
                    <Button variant="secondary" size="sm" className="w-full text-xs">
                      Open {configuring.name} console
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Button>
                  </a>
                </div>

                {/* Option 2: enter the key */}
                <div className="rounded-lg border border-border p-3 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-ember/15 text-ember text-[11px]">2</span>
                    Enter your key
                  </div>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSave()}
                    placeholder={`${configuring.name} API key…`}
                    className="w-full text-xs bg-surface border border-border rounded-lg px-3 py-2 text-slate-200 placeholder:text-muted-foreground focus:outline-none focus:border-ember/60 font-mono"
                  />
                  <Button size="sm" className="w-full text-xs" onClick={handleSave} disabled={saving || !apiKey.trim()}>
                    {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                    Save key securely
                  </Button>
                </div>
              </div>
            )}

            {configuring.local && (
              <a href="https://ollama.com/download" target="_blank" rel="noopener noreferrer">
                <Button variant="secondary" size="sm" className="text-xs">
                  Get Ollama <ExternalLink className="h-3.5 w-3.5" />
                </Button>
              </a>
            )}

            {feedback && (
              <div
                className={`flex items-center gap-2 text-xs rounded-lg p-2.5 border ${
                  feedback.type === "ok"
                    ? "bg-success/10 border-success/25 text-emerald-300"
                    : "bg-danger/10 border-danger/25 text-rose-300"
                }`}
              >
                {feedback.type === "ok" ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                ) : (
                  <AlertCircle className="h-4 w-4 shrink-0" />
                )}
                <span>{feedback.msg}</span>
              </div>
            )}

            {/* Saved keys for this provider — add more for rate-limit rotation; test or remove each. */}
            {acctsFor(configuring.type).length > 0 && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <p className="text-[11px] font-medium text-slate-300">
                    Saved key{acctsFor(configuring.type).length > 1 ? "s" : ""} ({acctsFor(configuring.type).length})
                  </p>
                  {acctsFor(configuring.type).length > 1 && (
                    <span className="text-[10px] text-emerald-300">rotation active — spreads load & dodges rate limits</span>
                  )}
                </div>
                {acctsFor(configuring.type).map((a, i) => (
                  <div key={a.id} className="flex items-center gap-2 rounded-lg border border-border px-2.5 py-1.5">
                    <KeyRound className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    <span className="text-[11px] text-slate-300 flex-1">
                      Key {i + 1}
                      {a.is_validated && <span className="text-emerald-400"> · validated</span>}
                      {a.base_url && <span className="text-muted-foreground font-mono"> · {a.base_url}</span>}
                    </span>
                    <button
                      onClick={() => handleTest(a)}
                      disabled={testing === a.id}
                      className="text-[11px] text-slate-400 hover:text-slate-200 transition"
                    >
                      {testing === a.id ? "testing…" : "test"}
                    </button>
                    <button onClick={() => handleDelete(a.id)} className="text-[11px] text-rose-400 hover:text-rose-300 transition">
                      remove
                    </button>
                  </div>
                ))}
                <p className="text-[10px] text-muted-foreground">Add another key above to enable automatic rotation.</p>
              </div>
            )}
          </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
