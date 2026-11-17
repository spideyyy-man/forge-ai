import { create } from "zustand";
import { Device, Workspace, Project, ProviderAccount } from "@/types";
import { api } from "@/lib/api";

interface DeviceState {
  devices: Device[];
  workspaces: Workspace[];
  projects: Project[];
  providers: ProviderAccount[];
  activeDevice: Device | null;
  activeWorkspace: Workspace | null;
  activeProject: Project | null;
  isLoading: boolean;
  error: string | null;

  fetchDevices: () => Promise<void>;
  fetchWorkspaces: () => Promise<void>;
  fetchProjects: () => Promise<void>;
  fetchProviders: () => Promise<void>;
  registerDevice: (name: string, device_type?: string) => Promise<Device>;
  createWorkspace: (data: { device_id: string; name: string; root_path: string }) => Promise<Workspace>;
  activateWorkspace: (workspace: Workspace) => Promise<void>;
  pairDevice: (pairing_code: string, device_id: string) => Promise<void>;
  revokeDevice: (id: string) => Promise<void>;
  setActiveDevice: (device: Device | null) => void;
  setActiveWorkspace: (workspace: Workspace | null) => void;
  setActiveProject: (project: Project | null) => void;
}

export const useDeviceStore = create<DeviceState>((set, get) => ({
  devices: [],
  workspaces: [],
  projects: [],
  providers: [],
  activeDevice: null,
  activeWorkspace: null,
  activeProject: null,
  isLoading: false,
  error: null,

  fetchDevices: async () => {
    set({ isLoading: true, error: null });
    try {
      const devices = await api.getDevices();
      set({ devices, isLoading: false });
      const currentActive = get().activeDevice;
      if (!currentActive && devices.length > 0) {
        // Prefer a live (connected) agent, then a paired one, else the first row.
        const active =
          devices.find((d) => d.is_connected) ||
          devices.find((d) => d.status === "ACTIVE") ||
          devices[0];
        set({ activeDevice: active });
      } else if (currentActive) {
        // Keep the active device's live fields fresh after a refetch.
        const refreshed = devices.find((d) => d.id === currentActive.id);
        if (refreshed) set({ activeDevice: refreshed });
      }
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchProviders: async () => {
    try {
      const providers = await api.getProviders();
      set({ providers });
    } catch (err: any) {
      console.error("Error fetching providers:", err);
    }
  },

  fetchWorkspaces: async () => {
    try {
      const workspaces = await api.getWorkspaces();
      set({ workspaces });
      if (!get().activeWorkspace && workspaces.length > 0) {
        set({ activeWorkspace: workspaces[0] });
      }
    } catch (err: any) {
      console.error("Error fetching workspaces:", err);
    }
  },

  fetchProjects: async () => {
    try {
      const projects = await api.getProjects();
      set({ projects });
      if (!get().activeProject && projects.length > 0) {
        set({ activeProject: projects[0] });
      }
    } catch (err: any) {
      console.error("Error fetching projects:", err);
    }
  },

  registerDevice: async (name, device_type = "WINDOWS") => {
    const device = await api.registerDevice({ name, device_type });
    await get().fetchDevices();
    return device;
  },

  createWorkspace: async (data) => {
    const workspace = await api.createWorkspace(data);
    // A freshly opened folder becomes THE active workspace the agent targets.
    try {
      await api.activateWorkspace(workspace.id);
    } catch (err) {
      console.error("Failed to activate new workspace:", err);
    }
    await get().fetchWorkspaces();
    set({ activeWorkspace: { ...workspace, is_active: true } });
    return workspace;
  },

  activateWorkspace: async (workspace) => {
    // Optimistic local switch, then persist single-active on the backend so the
    // agent works in this folder.
    set((state) => ({
      activeWorkspace: workspace,
      workspaces: state.workspaces.map((w) => ({ ...w, is_active: w.id === workspace.id })),
    }));
    try {
      await api.activateWorkspace(workspace.id);
    } catch (err) {
      console.error("Failed to activate workspace:", err);
    }
  },

  pairDevice: async (pairing_code, device_id) => {
    await api.pairDevice({ pairing_code, device_id });
    await get().fetchDevices();
  },

  revokeDevice: async (id) => {
    await api.revokeDevice(id);
    await get().fetchDevices();
    if (get().activeDevice?.id === id) {
      set({ activeDevice: null });
    }
  },

  setActiveDevice: (device) => set({ activeDevice: device }),
  setActiveWorkspace: (workspace) => set({ activeWorkspace: workspace }),
  setActiveProject: (project) => set({ activeProject: project }),
}));
