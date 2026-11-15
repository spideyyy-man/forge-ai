import React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg" | "icon";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", children, ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-0";

    const variants = {
      // The forge spark: warm molten action against the cool console.
      primary:
        "bg-gradient-to-b from-ember-hot to-ember-deep text-white shadow-[0_3px_18px_-6px_rgba(249,115,22,0.75)] hover:brightness-110 active:scale-[0.98] focus-visible:ring-ember/50",
      secondary:
        "bg-surface-elevated hover:bg-[#1f1f2e] text-slate-200 border border-border-strong focus-visible:ring-iris/40",
      outline:
        "border border-border-strong hover:bg-surface-elevated text-slate-300 hover:text-white focus-visible:ring-iris/40",
      ghost: "hover:bg-surface-elevated text-slate-300 hover:text-white focus-visible:ring-iris/30",
      danger:
        "bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/25 focus-visible:ring-rose-500/40",
    };

    const sizes = {
      sm: "text-xs px-2.5 py-1.5 h-8 gap-1.5",
      md: "text-sm px-4 py-2 h-9 gap-2",
      lg: "text-base px-5 py-2.5 h-11 gap-2.5",
      icon: "h-9 w-9 p-0",
    };

    return (
      <button ref={ref} className={cn(baseStyles, variants[variant], sizes[size], className)} {...props}>
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
