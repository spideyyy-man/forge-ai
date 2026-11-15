"use client";

import React, { useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { DevicePairingModal } from "@/components/devices/device-pairing-modal";
import { AppBootstrap } from "@/components/providers/app-bootstrap";
import { useAuthStore } from "@/stores/auth-store";
import { wsClient } from "@/lib/ws";

export const AppShell = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuthStore();

  useEffect(() => {
    if (user?.id) {
      wsClient.connect(user.id);
    }
    return () => {
      wsClient.disconnect();
    };
  }, [user?.id]);

  return (
    <div className="flex h-screen w-screen overflow-hidden text-foreground">
      <AppBootstrap />
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
      <DevicePairingModal />
    </div>
  );
};
