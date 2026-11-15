"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { wsClient } from "@/lib/ws";
import { Message } from "@/types";
import { useDeviceStore } from "@/stores/device-store";
import { useAuthStore } from "@/stores/auth-store";
import { Bot, Send, Sparkles, FolderOpen, User2, Loader2, CornerDownLeft, Cpu, ArrowRight, ChevronDown, Check, Plus } from "lucide-react";

type ChatMsg = { id: string; role: "user" | "assistant" | "system"; content: string; pending?: boolean };

// Minimal, dependency-free Markdown rendering for agent replies (headings, bold,
// inline code, and bullet/numbered lists) so output reads cleanly instead of raw ###/**.
function renderInline(text: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) {
      out.push(<strong key={k++} className="font-semibold text-white">{tok.slice(2, -2)}</strong>);
    } else {
      out.push(<code key={k++} className="font-mono text-[0.92em] bg-black/40 px-1 py-0.5 rounded text-ember-hot">{tok.slice(1, -1)}</code>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function MarkdownLite({ text }: { text: string }) {
  const blocks: React.ReactNode[] = [];
  let list: React.ReactNode[] = [];
  const flush = () => {
    if (list.length) {
      blocks.push(<ul key={`l${blocks.length}`} className="list-disc pl-5 space-y-1 my-1.5">{list}</ul>);
      list = [];
    }
  };
  text.split("\n").forEach((line, i) => {
    const h = line.match(/^(#{1,4})\s+(.*)/);
    const li = line.match(/^\s*(?:[-*]|\d+\.)\s+(.*)/);
    if (h) {
      flush();
      blocks.push(
        <div key={i} className={`font-semibold text-white ${h[1].length <= 2 ? "text-sm mt-3" : "text-[13px] mt-2"}`}>
          {renderInline(h[2])}
        </div>
      );
    } else if (li) {
      list.push(<li key={i}>{renderInline(li[1])}</li>);
    } else if (line.trim() === "") {
      flush();
    } else {
      flush();
      blocks.push(<p key={i} className="my-1">{renderInline(line)}</p>);
    }
  });
  flush();
  return <div className="space-y-0.5">{blocks}</div>;
}

const MODES = [
  { id: "autonomous", label: "Autonomous", hint: "Plan, edit, and verify on its own" },
  { id: "plan_only", label: "Plan only", hint: "Propose a plan, make no changes" },
  { id: "review", label: "Review", hint: "Pause for approval before each edit" },
] as const;

const EXAMPLES = [
  "Add input validation to the signup form and write tests for it.",
  "Find where API errors are swallowed and surface them to the user.",
  "Refactor the data layer to use async/await and fix any race conditions.",
  "Write a README section explaining how to run this project locally.",
];

export default function AgentStudioPage() {
  const { activeDevice, activeWorkspace, workspaces, activateWorkspace } = useDeviceStore();
  const [prompt, setPrompt] = useState("");
  const [folderMenu, setFolderMenu] = useState(false);
  const [mode, setMode] = useState<(typeof MODES)[number]["id"]>("autonomous");
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [convId, setConvId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [needsProvider, setNeedsProvider] = useState(false);

  const user = useAuthStore((s) => s.user);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const convRef = useRef<string | null>(null); // conversation currently streaming
  const streamRef = useRef<string>(""); // accumulated streamed text

  // Connect the user WebSocket and render streamed tokens live as they arrive.
  useEffect(() => {
    if (!user?.id) return;
    wsClient.connect(user.id);
    const unsub = wsClient.subscribe((msg: any) => {
      if (msg?.type === "agent_delta" && msg.conversation_id && msg.conversation_id === convRef.current) {
        streamRef.current += msg.delta || "";
        const text = streamRef.current;
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== "pending"),
          { id: "pending", role: "assistant", content: text, pending: false },
        ]);
      }
    });
    return () => {
      unsub();
    };
  }, [user?.id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // The agent needs at least one model provider to think. Surface setup up front
  // instead of letting a task spin with no LLM behind it.
  useEffect(() => {
    api
      .getProviders()
      .then((p) => setNeedsProvider(p.length === 0))
      .catch(() => {});
  }, []);

  const ensureConversation = async (): Promise<string> => {
    if (convId) return convId;
    const conv = await api.createConversation({
      title: "Agent Studio session",
      agent_type: mode === "plan_only" ? "planner" : mode === "review" ? "reviewer" : "engineer",
    });
    setConvId(conv.id);
    return conv.id;
  };

  // Poll for the agent's reply the backend produces in the background. The agent
  // replies as "assistant"; failures are recorded as "system" — surface both.
  const waitForReply = async (id: string, baseline: number) => {
    for (let i = 0; i < 80; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      try {
        const msgs = await api.getMessages(id);
        // The API returns roles in upper-case (USER/ASSISTANT/SYSTEM) — compare case-insensitively.
        const replies = msgs.filter((m: Message) => {
          const r = String(m.role).toLowerCase();
          return r === "assistant" || r === "system";
        });
        if (replies.length > baseline) {
          const latest = replies[replies.length - 1];
          setMessages((prev) => [
            ...prev.filter((m) => m.id !== "pending"),
            { id: latest.id, role: String(latest.role).toLowerCase() === "system" ? "system" : "assistant", content: latest.content },
          ]);
          return true;
        }
      } catch {
        /* keep polling */
      }
    }
    return false;
  };

  const handleSend = async () => {
    const text = prompt.trim();
    if (!text || sending) return;
    setError(null);
    setSending(true);
    setPrompt("");

    const userMsg: ChatMsg = { id: `u-${Date.now()}`, role: "user", content: text };
    streamRef.current = "";
    setMessages((prev) => [...prev, userMsg, { id: "pending", role: "assistant", content: "", pending: true }]);

    try {
      const id = await ensureConversation();
      convRef.current = id; // route incoming stream deltas to this conversation
      const existing = await api.getMessages(id).catch(() => []);
      const baseline = existing.filter((m: Message) => {
        const r = String(m.role).toLowerCase();
        return r === "assistant" || r === "system";
      }).length;
      await api.sendMessage(id, { content: text, role: "user" });
      const got = await waitForReply(id, baseline);
      if (!got) {
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== "pending"),
          {
            id: `t-${Date.now()}`,
            role: "assistant",
            content: "The agent is still working — this task is taking a while. It will appear here when it finishes.",
          },
        ]);
      }
    } catch (err: any) {
      setMessages((prev) => prev.filter((m) => m.id !== "pending"));
      setError(err.message || "Could not reach the agent. Is the backend running and a model provider configured?");
    } finally {
      setSending(false);
      textareaRef.current?.focus();
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const agentLinked = activeDevice?.status === "ACTIVE";

  return (
    <div className="max-w-3xl mx-auto flex flex-col h-[calc(100vh-7rem)]">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-border">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Bot className="h-5 w-5 text-ember" />
            Agent Studio
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">Describe a task; the agent plans, edits, and verifies.</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Folder switcher — pick the folder the agent works in, without leaving Studio */}
          {workspaces.length > 0 ? (
            <div className="relative">
              <button
                onClick={() => setFolderMenu((v) => !v)}
                className="flex items-center gap-1.5 text-[11px] rounded-lg border border-ember/30 bg-ember/10 text-ember-hot px-2.5 py-1.5 hover:bg-ember/15 transition max-w-[220px]"
                title="Choose the folder the agent works in"
              >
                <FolderOpen className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate font-medium">{activeWorkspace ? activeWorkspace.name : "Select a folder"}</span>
                <ChevronDown className="h-3 w-3 shrink-0 opacity-70" />
              </button>
              {folderMenu && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setFolderMenu(false)} />
                  <div className="absolute right-0 mt-1.5 z-20 w-64 rounded-xl border border-border bg-surface-elevated shadow-2xl p-1.5 animate-in">
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground px-2 py-1">Agent works in</p>
                    {workspaces.map((ws) => {
                      const active = activeWorkspace?.id === ws.id;
                      return (
                        <button
                          key={ws.id}
                          onClick={() => {
                            activateWorkspace(ws);
                            setFolderMenu(false);
                          }}
                          className={`w-full text-left rounded-lg px-2 py-1.5 transition ${
                            active ? "bg-ember/10" : "hover:bg-surface"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <FolderOpen className={`h-3.5 w-3.5 shrink-0 ${active ? "text-ember" : "text-muted-foreground"}`} />
                            <span className="text-xs text-slate-200 truncate flex-1">{ws.name}</span>
                            {active && <Check className="h-3.5 w-3.5 text-ember shrink-0" />}
                          </div>
                          <p className="text-[10px] font-mono text-muted-foreground truncate pl-5">{ws.root_path}</p>
                        </button>
                      );
                    })}
                    <Link
                      href="/workspace"
                      className="flex items-center gap-2 w-full text-left rounded-lg px-2 py-1.5 text-xs text-iris hover:bg-surface transition mt-0.5 border-t border-border pt-2"
                    >
                      <Plus className="h-3.5 w-3.5" /> Open another folder…
                    </Link>
                  </div>
                </>
              )}
            </div>
          ) : (
            <Link href="/workspace">
              <Badge variant="outline" className="text-[11px] gap-1 cursor-pointer hover:text-slate-200">
                <FolderOpen className="h-3 w-3" /> Open a folder
              </Badge>
            </Link>
          )}
          <Badge variant={agentLinked ? "success" : "warning"} className="text-[11px]">
            {agentLinked ? "Agent linked" : "Agent offline"}
          </Badge>
        </div>
      </div>

      {/* Mode selector */}
      <div className="flex items-center gap-1.5 py-2.5">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            title={m.hint}
            className={`text-[11px] px-3 py-1.5 rounded-lg font-medium transition ${
              mode === m.id
                ? "bg-ember/15 text-ember-hot border border-ember/30"
                : "text-muted-foreground hover:text-slate-200 border border-transparent"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Conversation */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center gap-5">
            <div className="p-3 rounded-2xl bg-ember/10 text-ember">
              <Sparkles className="h-7 w-7" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-slate-200">What should we build?</h3>
              <p className="text-xs text-muted-foreground max-w-sm">
                {activeWorkspace
                  ? `Working in ${activeWorkspace.name}. Describe a change and the agent takes it from plan to verified edit.`
                  : "Open a folder first so the agent has code to work on, then describe a task."}
              </p>
            </div>
            <div className="w-full max-w-lg grid gap-2 sm:grid-cols-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => {
                    setPrompt(ex);
                    textareaRef.current?.focus();
                  }}
                  className="text-left text-[11px] text-slate-300 rounded-lg border border-border hover:border-ember/40 hover:bg-surface-elevated px-3 py-2 transition"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m) =>
            m.role === "system" ? (
              <div key={m.id} className="animate-in mx-auto max-w-[90%] text-center text-[11px] text-amber-300/90 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                {m.content}
              </div>
            ) : (
            <div key={m.id} className={`flex gap-3 animate-in ${m.role === "user" ? "flex-row-reverse" : ""}`}>
              <div
                className={`h-7 w-7 shrink-0 rounded-lg flex items-center justify-center ${
                  m.role === "user" ? "bg-iris/15 text-iris" : "bg-ember/15 text-ember"
                }`}
              >
                {m.role === "user" ? <User2 className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>
              <div
                className={`rounded-xl px-3.5 py-2.5 text-xs leading-relaxed max-w-[80%] ${
                  m.role === "user"
                    ? "bg-iris/10 border border-iris/20 text-slate-100"
                    : "bg-surface border border-border text-slate-200"
                }`}
              >
                {m.pending ? (
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> Planning…
                  </span>
                ) : m.role === "assistant" ? (
                  <MarkdownLite text={m.content} />
                ) : (
                  <p className="whitespace-pre-wrap break-words">{m.content}</p>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-border pt-3 pb-1">
        {needsProvider && (
          <Link href="/models" className="block mb-2">
            <div className="flex items-center gap-2 text-[11px] text-ember-hot bg-ember/10 border border-ember/25 rounded-lg px-3 py-2 hover:bg-ember/15 transition">
              <Cpu className="h-3.5 w-3.5 shrink-0" />
              <span className="flex-1">Add a model provider so the agent has an LLM to think with.</span>
              <span className="flex items-center gap-1 font-medium">Set up <ArrowRight className="h-3 w-3" /></span>
            </div>
          </Link>
        )}
        {error && <div className="text-[11px] text-rose-300 bg-danger/10 border border-danger/25 rounded-lg px-3 py-2 mb-2">{error}</div>}
        <div className="flex items-end gap-2 bg-surface border border-border rounded-xl p-2 focus-within:border-ember/50 transition">
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Describe the task…  (Enter to send, Shift+Enter for a new line)"
            rows={2}
            className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-muted-foreground focus:outline-none resize-none px-2 py-1.5 max-h-40"
          />
          <Button
            size="md"
            className="shrink-0 h-10 px-4"
            onClick={handleSend}
            disabled={!prompt.trim() || sending}
            aria-label="Send task to the agent"
          >
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            <span className="hidden sm:inline">Send</span>
          </Button>
        </div>
        <div className="flex items-center justify-center gap-1 text-[10px] text-muted-foreground mt-1.5">
          <CornerDownLeft className="h-3 w-3" /> Enter to send · Shift+Enter for a new line
        </div>
      </div>
    </div>
  );
}
