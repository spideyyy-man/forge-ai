import { create } from "zustand";

export type BackendStatus = "checking" | "online" | "offline";

interface SystemState {
  backendStatus: BackendStatus;
  authReady: boolean;
  lastError: string | null;
  retryToken: number;
  setBackendStatus: (status: BackendStatus) => void;
  setAuthReady: (ready: boolean) => void;
  setLastError: (error: string | null) => void;
  requestRetry: () => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  backendStatus: "checking",
  authReady: false,
  lastError: null,
  retryToken: 0,
  setBackendStatus: (backendStatus) => set({ backendStatus }),
  setAuthReady: (authReady) => set({ authReady }),
  setLastError: (lastError) => set({ lastError }),
  requestRetry: () => set((s) => ({ retryToken: s.retryToken + 1, backendStatus: "checking" })),
}));
