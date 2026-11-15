# FORGE AI — Product Specification

**Status:** Product direction / v0.1 target  
**Implementation status:** Mixed; parts of the platform exist, but the end-to-end user journey is not yet verified.

## 1. Product summary

FORGE AI is a free-first, open-source coding-agent environment for people who want to build and modify software projects without relying on one paid coding-agent subscription.

It should let a user connect their own model provider or a local model, give the agent access to an explicitly approved project, request a change, inspect the plan, approve actions, review code diffs, run tests, and recover from mistakes.

FORGE AI is not an attempt to reproduce every feature of Claude Code. The initial product should be a smaller, dependable tool for everyday coding tasks and small-to-medium projects.

## 2. Target users

- Students and beginners learning software development.
- Indie hackers building prototypes and small products.
- Developers who want a configurable coding assistant.
- Users who prefer local execution and control over their source code.
- Users who need an alternative workflow when a hosted coding assistant reaches its usage limits.

## 3. Product principles

1. **Free-first, not falsely free:** the software should be usable without a FORGE subscription. Users may still pay their chosen cloud provider for API usage.
2. **BYOK by default:** users supply and control their own provider credentials.
3. **Local control:** code changes and terminal execution happen through the user's local agent within approved workspaces.
4. **Privacy is a setting with enforcement:** Local-Only must never silently fall back to cloud inference.
5. **Approval before impact:** plans and risky operations are reviewable; destructive actions require explicit approval.
6. **Visible changes:** show files changed, diffs, commands, test output, and execution status.
7. **Bounded autonomy:** retries, tool calls, execution time, and context use have explicit limits.
8. **Honest status:** never label a prototype, mock, or unverified integration as complete.

## 4. Core v0.1 user journey

1. Install FORGE AI and its required services.
2. Start the application and complete initial configuration.
3. Add a provider key, or connect an available local Ollama model.
4. Pair the local workspace agent.
5. Approve one or more project directories.
6. Select a project and submit a coding task.
7. Receive a structured plan and the relevant files the agent intends to inspect.
8. Approve or revise the plan before writes or risky commands.
9. Agent reads relevant files and proposes/applies bounded edits.
10. User reviews a per-file diff and approves changes.
11. Agent runs relevant tests or build commands under policy.
12. Agent may perform a limited repair cycle using actual failure output.
13. User receives a completion report with changed files, commands, test results, model/provider used, and remaining issues.
14. User can revert the agent's changes without losing pre-existing work.

## 5. Must-have capabilities

| Capability | v0.1 acceptance criteria |
|---|---|
| Setup | Clear Windows-first setup, prerequisite checks, actionable errors, documented manual setup |
| Model configuration | Configure and validate at least one BYOK cloud provider and one optional local provider |
| Provider routing | Respect user-selected provider, model capability, privacy mode, and fallback policy |
| Device pairing | Authenticated pairing, revocation, reconnect handling, and visible connection state |
| Workspace access | User explicitly approves roots; path containment and protected-file rules enforced |
| Project context | List and read permitted files; ignore generated/dependency folders by default |
| Planning | Produce a structured, inspectable plan before consequential changes |
| File edits | Apply scoped edits and produce accurate diffs |
| Terminal | Request/execute commands under policy with visible output, timeout, and cancellation |
| Verification | Run selected tests/builds and report actual exit status and output |
| Repair | Bounded retries based on real diagnostic output; stop when limits are reached |
| Git safety | Create recoverable checkpoints and support rollback without erasing pre-existing work |
| Auditability | Record security-relevant actions with redaction and useful timestamps |
| Privacy | Local-Only enforcement and configurable excluded paths |
| Failure handling | Clear errors for offline agent, provider failures, timeouts, denied permissions, and failed tests |

## 6. Explicitly out of scope for v0.1

- Multi-agent swarms and complex agent-to-agent delegation.
- Advanced AST/call-graph visualizations.
- Autonomous deployment to production.
- Shared hosted inference or a FORGE-operated model API.
- Team billing, enterprise administration, and cloud collaboration.
- Automatic commits, pushes, or destructive cleanup without approval.
- Claims of compatibility with every language, framework, operating system, or model provider.

These may be considered after the core user journey is dependable.

## 7. Product surfaces

The current frontend has routes/surfaces for:
- Dashboard / home
- Agent Studio
- Code Workspace
- Model Control Center
- Project Intelligence
- Settings

These are current UI surfaces, not a statement that every associated capability is integrated. Agent Studio, workspace, model configuration, and project intelligence must be connected to real backend and local-agent behaviour before release claims are made.

## 8. Non-functional requirements

### Safety
- Enforce workspace boundaries in the local agent.
- Validate every tool request at execution time.
- Default to deny when authorization or workspace context is missing.
- Require approval for destructive/high-risk operations.
- Preserve user changes and support recovery.

### Privacy
- Never send source code to cloud providers in Local-Only mode.
- Exclude secrets and user-configured sensitive paths from model context.
- Keep provider credentials out of frontend responses and logs.
- Explain when cloud providers receive code context.

### Reliability
- Bound timeouts, retries, output sizes, and concurrent work.
- Handle disconnects and interrupted tasks without leaving ambiguous state.
- Make task state recoverable or explicitly mark it interrupted.

### Usability
- Setup should be possible from documented steps without editing source code.
- The user should always know which project, model, device, and privacy mode are active.
- All consequential actions and their results should be visible.

## 9. Success criteria for first public release

A new user on a clean supported Windows machine can:
- Follow the README and install the required components.
- Configure their own model credentials or a local model.
- Pair the local agent and approve a project.
- Complete a small real coding task from prompt to verified diff.
- See actual test output and understand failures.
- Revert the agent's changes safely.
- Understand what data is sent to a cloud model and what stays local.

A polished dashboard alone does not satisfy this definition.

## 10. Current implementation observations

Based on source inspection during documentation work:
- The repository already has a Next.js frontend, FastAPI API, and Python local-agent structure.
- The API includes authentication, device, workspace, project, provider, conversation, task, and health route modules.
- The backend includes a LangGraph workflow, LiteLLM-based model router, privacy filtering, and WebSocket tool dispatch.
- The local agent includes filesystem, terminal, Git, search/indexing, testing, pairing, audit, and command/path security modules.
- The inspected Agent Studio page is largely a static prototype; its send button is not wired to task submission.
- The inspected workspace page uses placeholder file entries and placeholder editor/terminal output.
- The inspected model page has a credential form UI that does not demonstrate a completed save/validation flow.
- The inspected project intelligence page displays placeholder/inactive states.
- The inspected API test directory contained only a health test file.

These are inspection observations, not a full runtime audit. Re-verify before changing status labels.
