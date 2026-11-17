export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at?: string | null;
}

export type DeviceType = "WINDOWS" | "MACOS" | "LINUX";
export type DeviceStatus = "PENDING" | "ACTIVE" | "DISCONNECTED" | "REVOKED";

export interface Device {
  id: string;
  user_id: string;
  name: string;
  device_type: DeviceType;
  status: DeviceStatus;
  pairing_code?: string | null;
  last_seen_at?: string | null;
  agent_version?: string | null;
  os_info?: Record<string, any> | null;
  created_at: string;
  updated_at?: string | null;
  // Live: agent currently holds an open WebSocket (overlaid by the API, not stored).
  is_connected?: boolean;
}

export interface RunEvent {
  seq: number;
  type: string; // "tool_call" | "tool_result" | ...
  tool?: string;
  ok?: boolean;
  target?: string;
}

export type RunStatus = "RUNNING" | "COMPLETED" | "CANCELLED" | "FAILED" | null;

export interface RunRecord {
  conversation_id?: string;
  status: RunStatus;
  events: RunEvent[];
  modified_files: string[];
  executed_commands: any[];
  verification_passed?: boolean | null;
  error?: string | null;
  final_text?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface SymbolHit {
  name: string;
  kind: string;
  file_path: string;
  line: number;
  signature?: string;
}

export interface IndexStats {
  files: number;
  symbols: number;
  total_lines: number;
  languages: { language: string; files: number }[];
  symbol_kinds: { kind: string; count: number }[];
}

export interface IndexStatus {
  connected: boolean;
  workspace_path?: string | null;
  stats?: IndexStats | null;
  error?: string;
}

export type ApprovalMode = "auto" | "approve";

export interface ApprovalPolicyResponse {
  modes: Record<string, ApprovalMode>;
  classes: string[];
  defaults: Record<string, ApprovalMode>;
}

export interface Workspace {
  id: string;
  device_id: string;
  user_id: string;
  name: string;
  root_path: string;
  is_active: boolean;
  settings?: Record<string, any> | null;
  created_at: string;
  updated_at?: string | null;
}

export type PrivacyMode = "CLOUD_ASSISTED" | "LOCAL_ONLY" | "CONFIGURABLE";
export type ProjectStatus = "ACTIVE" | "ARCHIVED" | "INDEXING";

export interface Project {
  id: string;
  workspace_id: string;
  user_id: string;
  name: string;
  description?: string | null;
  root_path: string;
  detected_languages?: string[] | null;
  detected_frameworks?: string[] | null;
  privacy_mode: PrivacyMode;
  status: ProjectStatus;
  last_indexed_at?: string | null;
  settings?: Record<string, any> | null;
  created_at: string;
  updated_at?: string | null;
}

export interface ProviderAccount {
  id: string;
  user_id: string;
  provider_type: string;
  display_name: string;
  has_api_key: boolean;
  base_url?: string | null;
  is_enabled: boolean;
  is_validated: boolean;
  last_validated_at?: string | null;
  settings?: Record<string, any> | null;
  created_at: string;
  updated_at?: string | null;
}

export interface ModelEntry {
  id: string;
  provider_id: string;
  model_id_str: string;
  display_name: string;
  context_window?: number | null;
  supports_tools: boolean;
  supports_streaming: boolean;
  supports_structured_output: boolean;
  coding_score?: number | null;
  reasoning_score?: number | null;
  speed_tier?: string | null;
  is_available: boolean;
  cost_per_1k_input?: number | null;
  cost_per_1k_output?: number | null;
}

export interface Conversation {
  id: string;
  user_id: string;
  project_id?: string | null;
  title?: string | null;
  model_id?: string | null;
  agent_type?: string | null;
  status: string;
  created_at: string;
  updated_at?: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  model_used?: string | null;
  token_count?: number | null;
  tool_calls?: any[] | null;
  tool_results?: any[] | null;
  created_at: string;
}

export type TaskStatus =
  | "PENDING"
  | "PLANNING"
  | "EXECUTING"
  | "PAUSED"
  | "VERIFYING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type TaskComplexity = "SIMPLE" | "MODERATE" | "COMPLEX" | "CRITICAL";

export interface AgentTask {
  id: string;
  conversation_id: string;
  project_id: string;
  user_id: string;
  description: string;
  status: TaskStatus;
  complexity: TaskComplexity;
  priority: number;
  model_used?: string | null;
  agent_type?: string | null;
  plan?: Record<string, any> | null;
  completed_steps?: any[] | null;
  modified_files?: string[] | null;
  commands_executed?: any[] | null;
  verification_results?: Record<string, any> | null;
  token_usage?: Record<string, any> | null;
  error_info?: Record<string, any> | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface WSMessage {
  type: string;
  id?: string;
  timestamp?: string;
  correlation_id?: string;
  [key: string]: any;
}
