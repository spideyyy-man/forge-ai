import { create } from "zustand";

interface UIState {
  sidebarCollapsed: boolean;
  activeTab: string;
  isPairingDialogOpen: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActiveTab: (tab: string) => void;
  setIsPairingDialogOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  activeTab: "overview",
  isPairingDialogOpen: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setIsPairingDialogOpen: (open) => set({ isPairingDialogOpen: open }),
}));
