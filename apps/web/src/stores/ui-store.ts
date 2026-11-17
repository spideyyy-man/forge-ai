import { create } from "zustand";

export type ToastKind = "success" | "error" | "info";
export interface Toast {
  id: string;
  kind: ToastKind;
  message: string;
}

interface UIState {
  sidebarCollapsed: boolean;
  activeTab: string;
  isPairingDialogOpen: boolean;
  toasts: Toast[];
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActiveTab: (tab: string) => void;
  setIsPairingDialogOpen: (open: boolean) => void;
  addToast: (kind: ToastKind, message: string) => void;
  dismissToast: (id: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  activeTab: "overview",
  isPairingDialogOpen: false,
  toasts: [],
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setIsPairingDialogOpen: (open) => set({ isPairingDialogOpen: open }),
  addToast: (kind, message) =>
    set((state) => {
      // De-dupe an identical message already on screen (avoids poller spam).
      if (state.toasts.some((t) => t.message === message && t.kind === kind)) return state;
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      return { toasts: [...state.toasts, { id, kind, message }] };
    }),
  dismissToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
