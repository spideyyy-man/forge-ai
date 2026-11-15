# FORGE AI — Claude Code Instructions

## 1. Product identity

FORGE AI is an open-source, free-first coding-agent project intended to help students, beginners, indie hackers, and developers build and modify small-to-medium software projects without depending on a single paid coding-agent subscription.

The intended product is self-hostable and BYOK (Bring Your Own Key), with support for cloud model providers and optional local inference through Ollama. It is being built alongside Spideyy-Free. Do not assume Spideyy-Free is a runtime dependency unless the code explicitly establishes that relationship.

The product direction is:
- User-owned model credentials; no shared inference API in the initial release.
- Hybrid cloud/local model routing, with an explicit Local-Only mode.
- A bounded engineering loop: plan → inspect → propose/approve → edit → test → repair → report.
- User visibility and control over filesystem changes and terminal execution.
- Git-aware diffs, checkpoints, and rollback as core safety capabilities.
- A usable, understandable v0.1 before advanced agent orchestration.

## 2. Source of truth and honesty

Before changing code:
1. Read this file and the relevant docs.
2. Inspect the actual implementation, not only the product descriptions.
3. Check the current Git status and preserve existing user changes.
4. Trace the full path across frontend, API, WebSocket protocol, and local agent before modifying cross-service behaviour.
5. Identify whether the requested feature is implemented, partial, mocked, or only planned.

Documentation:
- `README.md`: user-facing project overview and setup.
- `docs/product-spec.md`: product goals, users, scope, and acceptance criteria.
- `docs/architecture.md`: system boundaries and component architecture.
- `docs/security.md`: security model and requirements.
- `docs/roadmap.md`: staged delivery plan and known gaps.
- `docs/decisions.md`: durable technical/product decisions.

Never present a planned, mocked, placeholder, or unverified feature as working. Update documentation when implementation changes. Prefer explicit status labels: Implemented, Partial, Prototype, Planned, Blocked, or Not verified.

## 3. Current repository shape

- `apps/web/`: Next.js frontend (React, TypeScript, Tailwind CSS).
- `apps/api/`: FastAPI backend, SQLAlchemy/Alembic, provider routing, agent workflow, WebSocket coordination.
- `services/local-agent/`: Python local Windows agent for filesystem, terminal, Git, indexing/search, testing, and security enforcement.
- `packages/shared-types/`: shared TypeScript contracts.
- `infrastructure/`: Docker-related configuration.
- `scripts/`: PowerShell setup and development scripts.
- `docs/`: product and engineering documentation.

Verify package manifests and actual source before assuming a dependency or feature. The frontend currently contains prototype surfaces; do not assume a visible control is wired to a working API.

## 4. Engineering principles

- Prefer the smallest complete implementation over broad abstractions.
- Keep the three service boundaries explicit; avoid duplicating business logic across frontend, backend, and local agent.
- Keep shared protocol types and payloads explicit, validated, versionable, and backward-compatible where practical.
- Use async I/O for network and long-running service operations.
- Add timeouts, cancellation, bounded retries, and clear error states to remote operations.
- Avoid unbounded agent loops, uncontrolled tool calls, and hidden background execution.
- Keep provider adapters isolated behind a stable interface.
- Make model capability claims from verified provider/model metadata, not guesses.
- Do not introduce a new framework or agent framework without a concrete need.

## 5. Agent workflow requirements

The target user journey is:
1. Install and start the application.
2. Configure at least one model provider using the user's own credentials, or connect a local Ollama model.
3. Pair the local agent securely.
4. Open or create an approved project workspace.
5. Submit a coding task.
6. Receive a clear plan and approve the intended changes.
7. Let the agent inspect relevant files and make bounded edits.
8. Review diffs and command requests.
9. Run relevant tests/builds.
10. Review a truthful result summary and revert when needed.

The model must not be the security boundary. Enforce permissions in trusted application code and the local agent. Require explicit approval for destructive, sensitive, external, or high-risk operations. Preserve the user's ability to stop execution.

Do not claim the current workflow fully satisfies this journey until the end-to-end path is implemented and tested. The current LangGraph workflow contains simplified planning/inspection/coding/verification nodes; inspect it before extending it.

## 6. Local agent and tool safety

- Restrict filesystem access to explicitly approved workspace roots.
- Canonicalize paths and defend against traversal, symlink escape, and protected files.
- Treat repository contents, terminal output, model responses, and tool arguments as untrusted input.
- Validate tool names and argument schemas at the execution boundary.
- Classify terminal commands, but do not treat regex classification alone as a complete sandbox.
- Do not execute shell commands constructed from untrusted strings without safe argument handling.
- Use command timeouts, output limits, process cleanup, and cancellation.
- Protect secrets such as `.env`, private keys, credentials, tokens, and provider keys.
- Never log plaintext credentials or sensitive file contents.
- Audit security-relevant operations without leaking secrets.
- Do not weaken a security check to make a demo pass.

## 7. Model providers, BYOK, and privacy

- Provider credentials must remain server-side or in an appropriately protected local credential store; never expose secrets to browser state, logs, or client responses.
- Never silently route Local-Only requests to a cloud provider.
- Make provider fallback visible and respect user-selected privacy, budget, capability, and latency constraints.
- A fallback must not bypass a user's configured provider allowlist or privacy mode.
- Avoid sending complete repositories by default; retrieve only relevant, permitted context.
- Apply secret redaction and ignore rules before cloud transmission, while acknowledging redaction is defence-in-depth rather than a guarantee.
- Do not promise zero cost: BYOK cloud providers may charge users. Describe local inference as dependent on user hardware and model availability.

## 8. Git and change management

- Inspect `git status` before modifying files.
- Never discard, overwrite, reset, clean, or rewrite user changes without explicit approval.
- Show a diff for every agent-authored file modification.
- Build checkpoints/rollback so they do not destroy pre-existing user work.
- Do not automatically commit or push without user approval.
- Treat Git operations that alter history or publish code as high-risk.

## 9. Frontend and UX

- A button must perform its advertised action. Avoid decorative controls that imply functionality.
- Every async action needs loading, success, empty, and error states as appropriate.
- Clearly show selected workspace, connected device, model/provider, privacy mode, task status, and approval state.
- Make plan review, file diffs, terminal commands, and test output inspectable.
- Keep destructive actions distinct and require confirmation.
- Support keyboard navigation, accessible labels, readable contrast, and responsive layouts.
- Never display fake live status, fake model availability, fabricated file trees, or invented execution results.

## 10. Testing and verification

- Add focused tests for every new security-sensitive or workflow behaviour.
- Test path containment, protected files, command classification, authorization, provider filtering, privacy modes, WebSocket authentication, timeouts, retries, and audit redaction.
- Test both allowed and denied cases.
- Run the relevant backend tests, frontend lint/type/build checks, and local-agent tests where available.
- Do not invent commands. Inspect each package's scripts and test configuration first.
- Report exactly what was run, what passed, what failed, and what remains unverified.

## 11. Important repository gaps to keep visible

At the time these instructions were written:
- The UI contains prototype/placeholder states; visible controls are not proof of end-to-end functionality.
- The API test directory showed only a health test in the inspected tree; coverage of critical flows needs expansion.
- The root README references `scripts/test.ps1`, but that script was not present in the inspected root scripts directory.
- The README's setup instructions include shell syntax that should be checked for PowerShell compatibility.
- Provider support claims in the README and UI do not exactly match the model registry inspected in code.
- The repository's README says the project is private/all-rights-reserved, which conflicts with the intended public open-source release. Do not choose or add a license without the owner's decision.
- Security documentation contains intended controls; verify each claim against implementation and tests before treating it as a guarantee.

Re-check these items before release; do not assume they remain unchanged.

## 12. Definition of done

A change is done only when:
- The requested behaviour works across the relevant service boundaries.
- Permission and privacy rules are enforced outside the model.
- Errors, timeouts, cancellation, and partial failure are handled.
- Tests cover normal, failure, and security-denial paths.
- The UI reports real state rather than placeholders.
- Documentation and setup instructions match the implementation.
- No unrelated user changes were lost.
- Remaining limitations are stated plainly.

**Core principle:** Make FORGE AI genuinely useful before making it look autonomous. User control, safe local execution, honest capability claims, and reliable small-project workflows come first.
