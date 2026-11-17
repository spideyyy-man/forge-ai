"use client";

import React, { useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { DevicePairingModal } from "@/components/devices/device-pairing-modal";
import { AppBootstrap } from "@/components/providers/app-bootstrap";
import { Toaster } from "@/components/ui/toaster";
import { useAuthStore } from "@/stores/auth-store";
import { useDeviceStore } from "@/stores/device-store";
import { useUIStore } from "@/stores/ui-store";
import { wsClient } from "@/lib/ws";

export const AppShell = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuthStore();
  const addToast = useUIStore((s) => s.addToast);

  useEffect(() => {
    if (user?.id) {
      wsClient.connect(user.id);
    }
    return () => {
      wsClient.disconnect();
    };
  }, [user?.id]);

  // Keep agent connection status live across the whole app, and toast on
  // connect/disconnect transitions so "agent connected" has real feedback.
  useEffect(() => {
    if (!user?.id) return;
    let active = true;
    let connectedIds = new Set<string>();
    let initialized = false;

    const poll = async () => {
      await useDeviceStore.getState().fetchDevices();
      if (!active) return;
      const devices = useDeviceStore.getState().devices;
      const nowConnected = new Set(devices.filter((d) => d.is_connected).map((d) => d.id));
      if (initialized) {
        for (const d of devices) {
          if (d.is_connected && !connectedIds.has(d.id)) addToast("success", `Agent “${d.name}” connected`);
        }
        for (const id of connectedIds) {
          if (!nowConnected.has(id)) {
            const d = devices.find((x) => x.id === id);
            addToast("info", `Agent ${d ? `“${d.name}” ` : ""}disconnected`);
          }
        }
      }
      connectedIds = nowConnected;
      initialized = true;
    };

    poll();
    const timer = setInterval(poll, 8000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [user?.id, addToast]);

  return (
    <div className="flex h-screen w-screen overflow-hidden text-foreground">
      <AppBootstrap />
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
      <DevicePairingModal />
      <Toaster />
    </div>
  );
};
