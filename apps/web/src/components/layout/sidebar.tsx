"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";
import { useDeviceStore } from "@/stores/device-store";
import {
  LayoutDashboard,
  Bot,
  Code2,
  Cpu,
  FolderTree,
  Settings,
  ChevronLeft,
  ChevronRight,
  Laptop,
  Flame,
} from "lucide-react";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Agent Studio", href: "/agent-studio", icon: Bot },
  { label: "Code Workspace", href: "/workspace", icon: Code2 },
  { label: "Model Center", href: "/models", icon: Cpu },
  { label: "Intelligence", href: "/intelligence", icon: FolderTree },
  { label: "Settings", href: "/settings", icon: Settings },
];

export const Sidebar = () => {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar, setIsPairingDialogOpen } = useUIStore();
  const { activeDevice, devices } = useDeviceStore();

  const isConnected = activeDevice && activeDevice.status === "ACTIVE";

  return (
    <aside
      className={cn(
        "relative flex flex-col border-r border-[#232338] bg-[#0d0d15]/90 backdrop-blur-md transition-all duration-300 z-30 select-none",
        sidebarCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Brand Header */}
      <div className="flex h-14 items-center justify-between px-4 border-b border-[#202035]">
        <Link href="/" className="flex items-center gap-2.5 overflow-hidden">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-b from-ember-hot to-ember-deep shadow-[0_2px_14px_-4px_rgba(249,115,22,0.7)]">
            <Flame className="h-4 w-4 text-white" />
          </div>
          {!sidebarCollapsed && (
            <span className="font-display font-bold text-sm tracking-wide text-white flex items-center gap-1.5">
              FORGE <span className="text-ember-hot font-mono text-xs">AI</span>
            </span>
          )}
        </Link>
        <button
          onClick={toggleSidebar}
          className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-[#1a1a2e] transition"
        >
          {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Nav List */}
      <div className="flex-1 py-4 px-2 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all group",
                isActive
                  ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-[#161624]"
              )}
              title={sidebarCollapsed ? item.label : undefined}
            >
              <Icon className={cn("h-4 w-4 shrink-0 transition-colors", isActive ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200")} />
              {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </div>

      {/* Device Status Bar */}
      <div className="p-3 border-t border-[#202035] bg-[#0c0c14]">
        <button
          onClick={() => setIsPairingDialogOpen(true)}
          className={cn(
            "w-full flex items-center gap-2.5 p-2 rounded-lg border border-[#232338] bg-[#13131f] hover:border-indigo-500/30 transition text-left cursor-pointer",
            sidebarCollapsed && "justify-center p-2"
          )}
          title="Manage Local Agent"
        >
          <div className="relative">
            <Laptop className="h-4 w-4 text-slate-300" />
            <span
              className={cn(
                "absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full",
                isConnected ? "bg-emerald-400 ring-2 ring-[#0c0c14]" : "bg-rose-500"
              )}
            />
          </div>
          {!sidebarCollapsed && (
            <div className="flex-1 overflow-hidden">
              <div className="text-[11px] font-semibold text-slate-200 truncate">
                {activeDevice ? activeDevice.name : "No Device Paired"}
              </div>
              <div className="text-[10px] text-slate-400 flex items-center gap-1">
                <span className={isConnected ? "text-emerald-400" : "text-rose-400"}>
                  {isConnected ? "Connected" : "Offline"}
                </span>
                <span>• {devices.length} registered</span>
              </div>
            </div>
          )}
        </button>
      </div>
    </aside>
  );
};
