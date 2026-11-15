# FORGE AI Architecture

## System Overview

FORGE AI is a three-tier architecture consisting of a web application, a cloud intelligence backend, and local workspace agents.

## Components

### 1. Web Application (Next.js)

The frontend provides the developer interface including:
- Dashboard with system status and quick actions
- Agent Studio for AI-assisted coding conversations
- Code Workspace with Monaco Editor integration
- Model Control Center for provider management
- Project Intelligence for codebase visualization
- Settings for system configuration

**Key Technologies:** Next.js 15+, React, TypeScript, Tailwind CSS, shadcn/ui, Zustand, TanStack Query

### 2. Cloud Backend (FastAPI)

The backend handles:
- User authentication (JWT)
- Device management and pairing
- Agent orchestration (LangGraph)
- Model routing and provider management (LiteLLM)
- Session and task persistence (PostgreSQL)
- WebSocket communication hub
- Memory retrieval and management

**Key Technologies:** FastAPI, SQLAlchemy 2.0, Alembic, LangGraph, LiteLLM, WebSockets

### 3. Local Workspace Agent (Python)

The agent runs on the developer's machine and provides:
- Filesystem operations (read, write, create, delete)
- Terminal command execution
- Git operations
- Code search and indexing
- Test discovery and execution
- Security enforcement

**Key Technologies:** Python, AsyncIO, WebSockets, Watchdog, GitPython

## Communication Flow

```
User Browser ←→ Next.js Frontend ←→ FastAPI Backend ←→ Local Agent
                                         ↕
                                   AI Model Providers
```

1. User interacts with the web UI
2. Frontend sends API requests to the backend
3. Backend orchestrates agent workflows
4. Agent tasks requiring local operations are dispatched via WebSocket to the local agent
5. Local agent executes operations within approved workspaces and returns results
6. Backend processes results through the agent graph
7. Streaming events are pushed to the frontend via WebSocket/SSE

## Security Boundaries

- **Frontend → Backend:** HTTPS + JWT authentication
- **Backend → Local Agent:** Authenticated WebSocket (device pairing + tokens)
- **Local Agent → Filesystem:** Approved workspace roots + path validation
- **Local Agent → Terminal:** Command risk classification + policy enforcement
- **Backend → Providers:** Encrypted API keys, never exposed to frontend

## Database Architecture

- **PostgreSQL (Cloud):** Users, devices, workspaces, projects, conversations, tasks, providers, usage
- **SQLite (Local Agent):** Connection state, audit logs, local caches, indexing data
