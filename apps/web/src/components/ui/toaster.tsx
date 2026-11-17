"use client";

import React, { useEffect } from "react";
import { useUIStore, ToastKind } from "@/stores/ui-store";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

const ICONS = { success: CheckCircle2, error: AlertCircle, info: Info } as const;
const STYLES: Record<ToastKind, string> = {
  success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
  error: "border-rose-500/30 bg-rose-500/10 text-rose-200",
  info: "border-indigo-500/30 bg-indigo-500/10 text-indigo-200",
};

function ToastItem({
  id,
  kind,
  message,
  onDismiss,
}: {
  id: string;
  kind: ToastKind;
  message: string;
  onDismiss: (id: string) => void;
}) {
  const Icon = ICONS[kind];
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(id), 4000);
    return () => clearTimeout(timer);
  }, [id, onDismiss]);
  return (
    <div
      role="status"
      className={`pointer-events-auto flex items-center gap-2 rounded-lg border px-3 py-2 text-xs shadow-lg backdrop-blur-md animate-in ${STYLES[kind]}`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="max-w-xs">{message}</span>
      <button onClick={() => onDismiss(id)} className="ml-1 opacity-60 hover:opacity-100" aria-label="Dismiss">
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

export const Toaster = () => {
  const { toasts, dismissToast } = useUIStore();
  if (toasts.length === 0) return null;
  return (
    <div className="fixed bottom-4 right-4 z-[80] flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <ToastItem key={t.id} id={t.id} kind={t.kind} message={t.message} onDismiss={dismissToast} />
      ))}
    </div>
  );
};
