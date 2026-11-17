import { User, Device, Workspace, Project, ProviderAccount, ModelEntry, Conversation, Message, AgentTask, RunRecord, ApprovalPolicyResponse, IndexStatus, IndexStats, SymbolHit } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

class ApiClient {
  private getAuthHeader(): Record<string, string> {
    if (typeof window === "undefined") return {};
    const token = localStorage.getItem("forge_access_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...this.getAuthHeader(),
      ...((options.headers as Record<string, string>) || {}),
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `HTTP Error ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        // Fallback to response status text
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Auth
  async login(credentials: { email: string; password: string }): Promise<{ access_token: string; token_type: string }> {
    return this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
  }

  async register(data: { email: string; username: string; password: string }): Promise<User> {
    return this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getCurrentUser(): Promise<User> {
    return this.request("/auth/me");
  }

  // Devices
  async getDevices(): Promise<Device[]> {
    return this.request("/devices/");
  }

  async getDevice(id: string): Promise<Device> {
    return this.request(`/devices/${id}`);
  }

  async registerDevice(data: { name: string; device_type?: string; os_info?: any }): Promise<Device> {
    return this.request("/devices/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async pairDevice(data: { pairing_code: string; device_id: string }): Promise<{ device_id: string; auth_token: string; status: string }> {
    return this.request("/devices/pair", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async revokeDevice(id: string): Promise<void> {
    return this.request(`/devices/${id}`, {
      method: "DELETE",
    });
  }

  // Workspaces
  async getWorkspaces(): Promise<Workspace[]> {
    return this.request("/workspaces/");
  }

  async createWorkspace(data: { device_id: string; name: string; root_path: string }): Promise<Workspace> {
    return this.request("/workspaces/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async activateWorkspace(id: string): Promise<Workspace> {
    return this.request(`/workspaces/${id}/activate`, { method: "POST" });
  }

  async deleteWorkspace(id: string): Promise<void> {
    return this.request(`/workspaces/${id}`, {
      method: "DELETE",
    });
  }

  // Projects
  async getProjects(): Promise<Project[]> {
    return this.request("/projects/");
  }

  async createProject(data: {
    workspace_id: string;
    name: string;
    description?: string;
    root_path: string;
    privacy_mode?: string;
  }): Promise<Project> {
    return this.request("/projects/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Providers
  async getProviders(): Promise<ProviderAccount[]> {
    return this.request("/providers/");
  }

  async createProvider(data: {
    provider_type: string;
    display_name: string;
    api_key: string;
    base_url?: string;
  }): Promise<ProviderAccount> {
    return this.request("/providers/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async testProvider(id: string): Promise<{ success: boolean; latency_ms?: number; models_found?: number; error?: string }> {
    return this.request(`/providers/${id}/test`, {
      method: "POST",
    });
  }

  async deleteProvider(id: string): Promise<void> {
    return this.request(`/providers/${id}`, { method: "DELETE" });
  }

  async getProviderModels(id: string): Promise<ModelEntry[]> {
    return this.request(`/providers/${id}/models`);
  }

  // Conversations & Messages
  async getConversations(): Promise<Conversation[]> {
    return this.request("/conversations/");
  }

  async createConversation(data: { project_id?: string; title?: string; model_id?: string; agent_type?: string }): Promise<Conversation> {
    return this.request("/conversations/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getMessages(conversationId: string): Promise<Message[]> {
    return this.request(`/conversations/${conversationId}/messages`);
  }

  async getConversationRun(conversationId: string): Promise<RunRecord> {
    return this.request(`/conversations/${conversationId}/run`);
  }

  // Code intelligence
  async getIndexStatus(): Promise<IndexStatus> {
    return this.request(`/intelligence/status`);
  }

  async reindexWorkspace(): Promise<IndexStats & { success: boolean }> {
    return this.request(`/intelligence/index`, { method: "POST" });
  }

  async searchSymbols(q: string): Promise<{ results: SymbolHit[] }> {
    return this.request(`/intelligence/search?q=${encodeURIComponent(q)}`);
  }

  // Settings
  async getApprovalPolicy(): Promise<ApprovalPolicyResponse> {
    return this.request(`/settings/approval-policy`);
  }

  async updateApprovalPolicy(modes: Record<string, string>): Promise<ApprovalPolicyResponse> {
    return this.request(`/settings/approval-policy`, {
      method: "PUT",
      body: JSON.stringify({ modes }),
    });
  }

  async sendMessage(conversationId: string, data: { content: string; role?: string }): Promise<Message> {
    return this.request(`/conversations/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Tasks
  async getTasks(statusFilter?: string): Promise<AgentTask[]> {
    const query = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
    return this.request(`/tasks/${query}`);
  }

  async getTask(id: string): Promise<AgentTask> {
    return this.request(`/tasks/${id}`);
  }

  async pauseTask(id: string): Promise<AgentTask> {
    return this.request(`/tasks/${id}/pause`, { method: "POST" });
  }

  async resumeTask(id: string): Promise<AgentTask> {
    return this.request(`/tasks/${id}/resume`, { method: "POST" });
  }

  async cancelTask(id: string): Promise<AgentTask> {
    return this.request(`/tasks/${id}/cancel`, { method: "POST" });
  }

  // Health
  async checkHealth(): Promise<{ status: string; service: string; version: string }> {
    return this.request("/health");
  }
}

export const api = new ApiClient();
