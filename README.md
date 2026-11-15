# FORGE AI

> Your personal autonomous software engineer.

A multi-model autonomous AI coding agent platform that provides an alternative coding environment with support for multiple AI model providers, intelligent model selection and fallback, real local filesystem access, autonomous multi-step coding, codebase understanding, terminal execution, automated testing and debugging, persistent project memory, and multiple specialized agents.

## Architecture

FORGE AI consists of three independent systems:

1. **Web Application** (`apps/web/`) — Next.js frontend providing the user interface
2. **Cloud Backend** (`apps/api/`) — FastAPI backend for agent orchestration, model routing, and session management
3. **Local Workspace Agent** (`services/local-agent/`) — Python service running on your machine for filesystem access, terminal execution, and git operations

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Git

### Development Setup

```powershell
# 1. Clone and setup
cd forge-ai

# 2. Start the backend
cd apps/api
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database credentials
alembic upgrade head
python run.py

# 3. Start the frontend
cd apps/web
npm install
npm run dev

# 4. Start the local agent
cd services/local-agent
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py --config forge-agent.toml
```

### Development Scripts

```powershell
# Run all services
.\scripts\dev.ps1

# Run tests
.\scripts\test.ps1

# Setup development environment
.\scripts\setup.ps1
```

## Project Structure

```
forge-ai/
├── apps/
│   ├── web/                  # Next.js web application
│   └── api/                  # FastAPI backend
├── services/
│   └── local-agent/          # Windows local workspace agent
├── packages/
│   └── shared-types/         # Shared TypeScript types
├── infrastructure/           # Docker, deployment configs
├── docs/                     # Documentation
├── scripts/                  # Development scripts
└── tests/                    # Integration tests
```

## Supported Model Providers

| Provider | Status |
|----------|--------|
| NVIDIA NIM | Adapter ready |
| Google Gemini | Adapter ready |
| Groq | Adapter ready |
| Cerebras | Adapter ready |
| DeepSeek | Adapter ready |
| OpenRouter | Adapter ready |
| Mistral | Adapter ready |
| ModelScope | Adapter ready |
| Ollama | Adapter ready |

## Security

- All filesystem access is restricted to explicitly approved workspace directories
- Terminal commands are classified by risk level with configurable policies
- API keys are encrypted at rest and never exposed to the browser
- Device pairing uses short-lived codes with authenticated WebSocket connections
- Path traversal and symlink escape prevention
- Audit logging for all operations

## License

Private — All rights reserved.
