"use client";

import React, { useEffect } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useDeviceStore } from "@/stores/device-store";
import { useSystemStore } from "@/stores/system-store";
import { Loader2, WifiOff, RotateCw } from "lucide-react";

// Matches the seeded local account in the backend (DEBUG only).
const DEV_EMAIL = "dev@forge.local";
const DEV_USERNAME = "dev";
const DEV_PASSWORD = "forgedev123";

const AUTOLOGIN = process.env.NEXT_PUBLIC_DEV_AUTOLOGIN !== "false";

// The backend origin we actually try to reach, for an accurate offline message
// (works whether running against localhost or a deployed API URL).
const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(/\/api\/?$/, "");

/**
 * Runs once on load: confirms the backend is reachable, signs in with the local
 * dev account so the app has a valid token, then warms the core data stores.
 * Renders a connection banner while checking or when the backend is unreachable.
 */
export const AppBootstrap = () => {
  const { backendStatus, setBackendStatus, setAuthReady, setLastError, requestRetry, lastError, retryToken } =
    useSystemStore();

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      setBackendStatus("checking");
      setAuthReady(false);

      // 1. Is the backend up?
      try {
        await api.checkHealth();
      } catch {
        if (!cancelled) {
          setBackendStatus("offline");
          setLastError(`Can't reach the FORGE AI backend on ${API_ORIGIN}. Start it, then retry.`);
        }
        return;
      }
      if (cancelled) return;
      setBackendStatus("online");
      setLastError(null);

      // 2. Make sure we hold a valid token.
      const hasToken = typeof window !== "undefined" && !!localStorage.getItem("forge_access_token");
      const auth = useAuthStore.getState();
      if (AUTOLOGIN && !hasToken) {
        try {
          await auth.login({ email: DEV_EMAIL, password: DEV_PASSWORD });
        } catch {
          // The dev user may not be seeded yet — create it, then sign in.
          try {
            await auth.register({ email: DEV_EMAIL, username: DEV_USERNAME, password: DEV_PASSWORD });
          } catch {
            /* Continue unauthenticated; pages will show signed-out states. */
          }
        }
      } else {
        await auth.checkAuth();
      }
      if (cancelled) return;

      // 3. Warm the shared data stores (failures are handled inside each store).
      await Promise.allSettled([
        useDeviceStore.getState().fetchDevices(),
        useDeviceStore.getState().fetchWorkspaces(),
        useDeviceStore.getState().fetchProjects(),
        useDeviceStore.getState().fetchProviders(),
      ]);
      if (!cancelled) setAuthReady(true);
    }

    boot();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retryToken]);

  if (backendStatus === "online") return null;

  return (
    <div className="fixed inset-x-0 top-0 z-[60] flex justify-center px-4 pt-3 pointer-events-none">
      {backendStatus === "checking" ? (
        <div className="pointer-events-auto flex items-center gap-2 rounded-full border border-border bg-surface/90 px-4 py-1.5 text-xs text-muted-foreground shadow-lg backdrop-blur-md animate-in">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-ember" />
          Connecting to backend…
        </div>
      ) : (
        <div className="pointer-events-auto flex items-center gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-xs text-rose-200 shadow-lg backdrop-blur-md animate-in">
          <WifiOff className="h-4 w-4 shrink-0 text-rose-400" />
          <span className="max-w-sm">{lastError ?? "Backend offline."}</span>
          <button
            onClick={() => requestRetry()}
            className="flex items-center gap-1 rounded-md border border-rose-400/30 bg-rose-500/10 px-2 py-1 font-medium text-rose-100 transition hover:bg-rose-500/20"
          >
            <RotateCw className="h-3 w-3" />
            Retry
          </button>
        </div>
      )}
    </div>
  );
};
