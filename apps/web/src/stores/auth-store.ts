import { create } from "zustand";
import { User } from "@/types";
import { api } from "@/lib/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  register: (data: { email: string; username: string; password: string }) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: typeof window !== "undefined" ? localStorage.getItem("forge_access_token") : null,
  isLoading: true,
  isAuthenticated: false,

  login: async (credentials) => {
    set({ isLoading: true });
    try {
      const { access_token } = await api.login(credentials);
      localStorage.setItem("forge_access_token", access_token);
      set({ token: access_token, isAuthenticated: true });
      const user = await api.getCurrentUser();
      set({ user, isLoading: false });
    } catch (error) {
      set({ isLoading: false, isAuthenticated: false, user: null });
      throw error;
    }
  },

  register: async (data) => {
    set({ isLoading: true });
    try {
      await api.register(data);
      // Auto login after register
      const { access_token } = await api.login({ email: data.email, password: data.password });
      localStorage.setItem("forge_access_token", access_token);
      set({ token: access_token, isAuthenticated: true });
      const user = await api.getCurrentUser();
      set({ user, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem("forge_access_token");
    set({ user: null, token: null, isAuthenticated: false, isLoading: false });
  },

  checkAuth: async () => {
    const token = localStorage.getItem("forge_access_token");
    if (!token) {
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
      return;
    }

    try {
      const user = await api.getCurrentUser();
      set({ user, token, isAuthenticated: true, isLoading: false });
    } catch (e) {
      localStorage.removeItem("forge_access_token");
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
