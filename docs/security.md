# FORGE AI Security Documentation

## Security Architecture

### 1. Authentication

**User Authentication:**
- JWT-based authentication with access and refresh tokens
- Passwords hashed with bcrypt (12 rounds)
- Tokens expire after configurable duration (default: 24 hours)
- Refresh tokens for seamless session continuation

**Device Authentication:**
- Device pairing via 6-character codes (expires in 10 minutes)
- After pairing, devices receive a long-lived auth token
- Auth tokens are hashed before storage (only the device has the plaintext)
- Devices can be revoked instantly

### 2. Workspace Security

**Approved Roots:**
- Only explicitly approved directories are accessible
- All paths are canonicalized (resolved to absolute paths)
- Path traversal prevention (no `..` escapes)
- Symlink escape prevention (resolved paths must stay within approved roots)

**Protected Patterns:**
- `.env`, `.env.*` files
- Private keys (`*.pem`, `*.key`, `id_rsa`, `id_ed25519`)
- Custom patterns configurable per-project

### 3. Terminal Security

**Command Risk Classification:**

| Risk Level | Examples | Default Policy |
|------------|----------|----------------|
| SAFE | `ls`, `cat`, `git status`, `npm test` | Auto-execute |
| LOW | `git log`, `tree`, `find` | Auto-execute |
| MEDIUM | `npm install`, `pip install`, `git commit` | Policy-controlled |
| HIGH | `rm -rf`, `del /s`, `DROP TABLE` | Require approval |
| CRITICAL | `sudo`, `admin`, `format` | Blocked by default |

### 4. Credential Security

- API keys encrypted at rest using Fernet symmetric encryption
- Encryption keys derived from server secret
- Keys never included in API responses after initial storage
- Keys never logged or included in error messages
- Environment variable leakage prevention in terminal output

### 5. Network Security

- TLS for all external communications
- WebSocket connections authenticated with device tokens
- Message replay protection via timestamps and nonces
- Rate limiting on all API endpoints
- CORS restricted to configured origins

### 6. Agent Security

- Model-generated tool arguments are always validated
- Repository file content is treated as untrusted input
- Permission enforcement is independent of model reasoning
- Tool execution limits (max retries, max duration)
- All tool invocations are logged

## Privacy Modes

| Mode | Description |
|------|-------------|
| Cloud-Assisted | Code can be sent to cloud providers for AI processing |
| Local-Only | Code stays on device; only local models (Ollama) are used |
| Configurable | Per-file and per-directory rules for what can be transmitted |

## Audit Logging

All security-relevant operations are logged:
- File reads/writes
- Terminal commands
- Device connections
- Authentication events
- Provider API calls
- Permission denials
