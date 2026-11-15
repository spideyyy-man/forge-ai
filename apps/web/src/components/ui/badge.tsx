import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "success" | "warning" | "error" | "info" | "ember" | "outline";
}

export const Badge = ({ className, variant = "default", children, ...props }: BadgeProps) => {
  const variants = {
    default: "bg-surface-elevated text-slate-300 border border-border-strong",
    success: "bg-emerald-500/10 text-emerald-300 border border-emerald-500/25",
    warning: "bg-amber-500/10 text-amber-300 border border-amber-500/25",
    error: "bg-rose-500/10 text-rose-300 border border-rose-500/25",
    info: "bg-indigo-500/10 text-indigo-300 border border-indigo-500/25",
    ember: "bg-ember/10 text-ember-hot border border-ember/30",
    outline: "border border-border-strong text-slate-400",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium transition-colors",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};
