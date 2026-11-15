"use client";

import React from "react";
import { useAuthStore } from "@/stores/auth-store";
import { useDeviceStore } from "@/stores/device-store";
import { useUIStore } from "@/stores/ui-store";
import { useSystemStore } from "@/stores/system-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Laptop, Cpu, LogOut } from "lucide-react";

export const Topbar = () => {
  const { user, isAuthenticated, logout } = useAuthStore();
  const { activeDevice, activeWorkspace } = useDeviceStore();
  const { setIsPairingDialogOpen } = useUIStore();
  const requestRetry = useSystemStore((s) => s.requestRetry);

  return (
    <header className="h-14 border-b border-border bg-surface/70 backdrop-blur-md px-6 flex items-center justify-between z-20">
      <div className="flex items-center gap-3">
        {activeWorkspace ? (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Workspace:</span>
            <span className="font-mono font-medium text-slate-200 bg-[#161626] px-2 py-1 rounded border border-[#262640]">
              {activeWorkspace.name}
            </span>
          </div>
        ) : (
          <span className="text-xs text-slate-400">No active workspace selected</span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Model Indicator */}
        <Badge variant="outline" className="text-[11px] gap-1.5 py-1 px-2.5 bg-[#12121e]">
          <Cpu className="h-3 w-3 text-indigo-400" />
          <span>Auto-Routing Active</span>
        </Badge>

        {/* Pair Device Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsPairingDialogOpen(true)}
          className="text-xs h-8 gap-1.5 border-[#282844] hover:bg-[#1b1b30]"
        >
          <Laptop className="h-3.5 w-3.5 text-slate-400" />
          <span>{activeDevice ? "Agent Paired" : "Connect Agent"}</span>
        </Button>

        {/* User / Auth Info */}
        {isAuthenticated && user ? (
          <div className="flex items-center gap-2 pl-2 border-l border-border">
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <div className="h-7 w-7 rounded-full bg-gradient-to-b from-ember-hot to-ember-deep flex items-center justify-center text-white font-bold text-xs">
                {user.username.charAt(0).toUpperCase()}
              </div>
              <span className="font-medium hidden sm:inline">{user.username}</span>
            </div>
            <button
              onClick={logout}
              className="text-slate-400 hover:text-rose-400 p-1.5 rounded-md hover:bg-surface-elevated transition"
              title="Logout"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 pl-2 border-l border-border">
            <Button variant="secondary" size="sm" className="text-xs h-8" onClick={() => requestRetry()}>
              Sign In
            </Button>
          </div>
        )}
      </div>
    </header>
  );
};
