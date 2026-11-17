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
import { Bot, Send, Sparkles, FolderOpen, User2, Loader2, CornerDownLeft, Cpu, ArrowRight, ChevronDown, Check, Plus, Square } from "lucide-react";

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

// A pending change the agent wants to make; the user must approve it before it is applied.
type Proposal = {
  kind: "edit" | "command" | "commit";
  path?: string;
  diff?: string;
  additions?: number;
  deletions?: number;
  created?: boolean;
  command?: string;
  cwd?: string;
  repo_path?: string;
  message?: string;
};
type Approval = { approval_id: string; proposal: Proposal };

// Render a unified diff with +/- line coloring. Dependency-free.
function DiffView({ diff }: { diff: string }) {
  const lines = diff.split("\n");
  return (
    <pre className="text-[11px] font-mono leading-relaxed max-h-72 overflow-auto rounded-lg bg-black/50 border border-border p-2.5">
      {lines.map((ln, i) => {
        let cls = "text-slate-400";
        if (ln.startsWith("+") && !ln.startsWith("+++")) cls = "text-emerald-300 bg-emerald-500/10";
        else if (ln.startsWith("-") && !ln.startsWith("---")) cls = "text-rose-300 bg-rose-500/10";
        else if (ln.startsWith("@@")) cls = "text-cyan-300";
        else if (ln.startsWith("+++") || ln.startsWith("---")) cls = "text-slate-500";
        return (
          <div key={i} className={`${cls} whitespace-pre-wrap break-all px-1`}>
            {ln || " "}
          </div>
        );
      })}
    </pre>
  );
}

// The approval card shown when the agent proposes a write/command/commit.
function ApprovalCard({ approval, onDecide }: { approval: Approval; onDecide: (approved: boolean) => void }) {
  const p = approval.proposal;
  const title =
    p.kind === "edit"
      ? `${p.created ? "Create" : "Edit"} ${p.path}`
      : p.kind === "command"
      ? "Run command"
      : "Commit changes";
  return (
    <div className="animate-in rounded-xl border border-ember/40 bg-ember/5 p-3 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="h-4 w-4 text-ember shrink-0" />
          <span className="text-xs font-semibold text-white truncate" title={title}>{title}</span>
        </div>
        {p.kind === "edit" && (
          <span className="text-[10px] font-mono shrink-0">
            <span className="text-emerald-300">+{p.additions ?? 0}</span>{" "}
            <span className="text-rose-300">−{p.deletions ?? 0}</span>
          </span>
        )}
      </div>

      {p.kind === "edit" && p.diff && <DiffView diff={p.diff} />}
      {p.kind === "command" && (
        <pre className="text-[11px] font-mono rounded-lg bg-black/50 border border-border p-2.5 text-amber-200 whitespace-pre-wrap break-all">
          $ {p.command}
          {p.cwd ? `\n(in ${p.cwd})` : ""}
        </pre>
      )}
      {p.kind === "commit" && (
        <pre className="text-[11px] font-mono rounded-lg bg-black/50 border border-border p-2.5 text-slate-200 whitespace-pre-wrap break-all">
          {p.message}
        </pre>
      )}

      <div className="flex items-center justify-end gap-2 pt-0.5">
        <button
          onClick={() => onDecide(false)}
          className="text-[11px] px-3 py-1.5 rounded-lg border border-border text-slate-300 hover:bg-surface transition"
        >
          Reject
        </button>
        <button
          onClick={() => onDecide(true)}
          className="text-[11px] px-3 py-1.5 rounded-lg bg-ember/20 border border-ember/40 text-ember-hot font-medium hover:bg-ember/30 transition"
        >
          {p.kind === "edit" ? "Approve & apply" : "Approve"}
        </button>
      </div>
    </div>
  );
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
  const [approval, setApproval] = useState<Approval | null>(null);
  const [activity, setActivity] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const user = useAuthStore((s) => s.user);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const convRef = useRef<string | null>(null); // conversation currently streaming
  const streamRef = useRef<string>(""); // accumulated streamed text

  const decideApproval = (approvalId: string, approved: boolean) => {
    wsClient.send({ type: "approval_decision", approval_id: approvalId, approved });
    setApproval((cur) => (cur?.approval_id === approvalId ? null : cur));
    setActivity(approved ? "Applying change…" : "Change rejected — adapting…");
  };

  // Ask the backend to stop the running task. Cooperative: it halts at the next
  // step/tool boundary; any edits already applied remain revertable.
  const handleCancel = () => {
    const id = convRef.current;
    if (!id) return;
    wsClient.send({ type: "cancel", conversation_id: id });
    setCancelling(true);
    setApproval(null);
    setActivity("Stopping…");
  };

  // Short human label for a live tool event.
  const toolLabel = (tool: string, args: any): string => {
    const name = args?.path || args?.command || args?.query || args?.repo_path || "";
    const verbs: Record<string, string> = {
      read_file: "Reading", list_directory: "Listing", search_text: "Searching",
      git_status: "Checking git status", git_diff: "Reading git diff",
      apply_edit: "Proposing an edit to", execute_command: "Proposing command",
      git_commit: "Proposing commit",
    };
    return `${verbs[tool] || tool} ${name}`.trim();
  };

  // Connect the user WebSocket: render streamed tokens, tool activity, and approval prompts.
  useEffect(() => {
    if (!user?.id) return;
    wsClient.connect(user.id);
    const unsub = wsClient.subscribe((msg: any) => {
      const forThisConv = msg?.conversation_id && msg.conversation_id === convRef.current;

      if (msg?.type === "agent_delta" && forThisConv) {
        streamRef.current += msg.delta || "";
        const text = streamRef.current;
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== "pending"),
          { id: "pending", role: "assistant", content: text, pending: false },
        ]);
      } else if (msg?.type === "approval_request" && forThisConv) {
        setApproval({ approval_id: msg.approval_id, proposal: msg.proposal });
        setActivity(null);
      } else if (msg?.type === "agent_event" && forThisConv) {
        if (msg.event_type === "tool_call") {
          setActivity(toolLabel(msg.tool, msg.arguments));
        } else if (msg.event_type === "completion") {
          setActivity(null);
          setApproval(null);
          setCancelling(false);
          setSending(false);
          if (msg.content) {
            setMessages((prev) => [
              ...prev.filter((m) => m.id !== "pending"),
              { id: `done-${Date.now()}`, role: "assistant", content: msg.content },
            ]);
          }
        } else if (msg.event_type === "error") {
          // Surface a failed run immediately, even if the poll window has closed.
          setActivity(null);
          setApproval(null);
          setCancelling(false);
          setSending(false);
          setError(msg.content || "The agent run failed.");
          setMessages((prev) => prev.filter((m) => m.id !== "pending"));
        }
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

  // Rebuild chat + live state for a conversation referenced in the URL, so a page
  // refresh resumes an in-flight run (status, activity, Stop) instead of losing it.
  const hydrateConversation = async (id: string) => {
    convRef.current = id;
    try {
      const [msgs, run] = await Promise.all([
        api.getMessages(id).catch(() => [] as Message[]),
        api.getConversationRun(id).catch(() => null),
      ]);
      const chat: ChatMsg[] = msgs
        .filter((m) => {
          const r = String(m.role).toLowerCase();
          return r === "user" || r === "assistant" || r === "system";
        })
        .map((m) => {
          const r = String(m.role).toLowerCase();
          return {
            id: m.id,
            role: (r === "user" ? "user" : r === "system" ? "system" : "assistant") as ChatMsg["role"],
            content: m.content,
          };
        });
      if (run && run.status === "RUNNING") {
        const last = run.events?.[run.events.length - 1];
        setActivity(last?.tool ? toolLabel(last.tool, { path: last.target }) : "Working…");
        setMessages([...chat, { id: "pending", role: "assistant", content: "", pending: true }]);
        setSending(true); // show Stop + spinner; live WS events + completion will resolve it
      } else {
        setMessages(chat);
        if (run?.error) setError(run.error);
      }
    } catch {
      /* best-effort replay */
    }
  };

  useEffect(() => {
    if (!user?.id) return;
    const url = new URL(window.location.href);
    const existing = url.searchParams.get("c");
    if (existing && !convId) {
      setConvId(existing);
      hydrateConversation(existing);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  const ensureConversation = async (): Promise<string> => {
    if (convId) return convId;
    const conv = await api.createConversation({
      title: "Agent Studio session",
      agent_type: mode === "plan_only" ? "planner" : mode === "review" ? "reviewer" : "engineer",
    });
    setConvId(conv.id);
    // Put the conversation in the URL so a refresh can resume this run.
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("c", conv.id);
      window.history.replaceState(null, "", url.toString());
    } catch {
      /* non-fatal */
    }
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
      setActivity(null);
      setCancelling(false);
      textareaRef.current?.focus();
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const agentLinked = !!activeDevice?.is_connected;

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
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> {activity || "Planning…"}
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

        {/* Approval prompt: the agent is blocked waiting for this decision. */}
        {approval && (
          <div className="pl-10">
            <ApprovalCard approval={approval} onDecide={(ok) => decideApproval(approval.approval_id, ok)} />
          </div>
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
          {sending ? (
            <Button
              size="md"
              variant="danger"
              className="shrink-0 h-10 px-4"
              onClick={handleCancel}
              disabled={cancelling}
              aria-label="Stop the running task"
            >
              {cancelling ? <Loader2 className="h-4 w-4 animate-spin" /> : <Square className="h-4 w-4" />}
              <span className="hidden sm:inline">{cancelling ? "Stopping…" : "Stop"}</span>
            </Button>
          ) : (
            <Button
              size="md"
              className="shrink-0 h-10 px-4"
              onClick={handleSend}
              disabled={!prompt.trim()}
              aria-label="Send task to the agent"
            >
              <Send className="h-4 w-4" />
              <span className="hidden sm:inline">Send</span>
            </Button>
          )}
        </div>
        <div className="flex items-center justify-center gap-1 text-[10px] text-muted-foreground mt-1.5">
          <CornerDownLeft className="h-3 w-3" /> Enter to send · Shift+Enter for a new line
        </div>
      </div>
    </div>
  );
}
