# FORGE AI — Roadmap

**Planning basis:** free-first, self-hostable, BYOK coding agent for small-to-medium projects.  
**Rule:** milestones are acceptance gates, not calendar promises. Do not mark a milestone complete because its UI exists.

## Release philosophy

Ship a narrow end-to-end coding workflow that is safe and understandable. Do not expand into swarms, advanced code intelligence, or broad provider marketing until a new user can complete a real task and recover from mistakes.

## Phase 0 — Repository and release foundations

- [ ] Decide the public open-source license and add a root `LICENSE`.
- [ ] Resolve the README's current private/all-rights-reserved statement.
- [ ] Make setup instructions accurate for Windows PowerShell.
- [ ] Reconcile documented scripts with files that actually exist; add the missing test script or remove the reference.
- [ ] Define supported Windows version, Node.js, Python, database, and Git versions.
- [ ] Add a clear configuration reference and safe example environment files.
- [ ] Separate development defaults from production-safe configuration.
- [ ] Establish CI for frontend lint/type/build and backend/local-agent tests.

**Exit gate:** a clean clone can be installed using only documented instructions; no production secret or insecure default is required.

## Phase 1 — A reliable local workspace agent

- [ ] Complete device pairing, authentication, revocation, reconnect, and heartbeat handling.
- [ ] Validate workspace roots and every path operation, including symlink and protected-file cases.
- [ ] Ensure file reads/writes are scoped, size-limited, auditable, and return clear errors.
- [ ] Implement safe file editing with before/after diff data.
- [ ] Add command approval, execution timeout, output limits, cancellation, and process cleanup.
- [ ] Make Git status/diff/checkpoint/rollback reliable and preserve pre-existing changes.
- [ ] Add focused security tests for all local tools.

**Exit gate:** local agent can safely inspect, edit, test, and restore a throwaway repository while rejecting unauthorized paths and risky commands.

## Phase 2 — Dependable model and provider layer

- [ ] Implement one complete BYOK provider setup and validation flow.
- [ ] Keep credentials out of browser responses, logs, and error payloads.
- [ ] Reconcile the provider list in the UI, README, registry, and backend.
- [ ] Enforce provider allowlists and user model selection.
- [ ] Implement explicit fallback rules for provider errors/rate limits.
- [ ] Enforce Local-Only routing with tests proving no cloud call occurs.
- [ ] Add transparent model/provider/latency/fallback reporting.
- [ ] Add budget and context controls before broad automatic routing.

**Exit gate:** user can configure a provider, run a real request, see which model answered, and prove that Local-Only does not contact cloud providers.

## Phase 3 — End-to-end coding loop

- [ ] Connect Agent Studio prompt submission to the task API.
- [ ] Build structured plans from actual repository inspection.
- [ ] Add plan review and explicit approval before consequential edits.
- [ ] Retrieve relevant files only; apply ignore and privacy policies before provider transmission.
- [ ] Apply edits through local-agent tools and return exact diffs.
- [ ] Execute selected tests/builds and capture real output/exit codes.
- [ ] Implement bounded repair attempts based on real diagnostics.
- [ ] Add cancellation, disconnect recovery, task status persistence, and useful error states.
- [ ] Report changed files, commands, model/provider, verification, and remaining issues.

**Exit gate:** a user can ask FORGE to implement a small feature in a real project, review the plan and diff, run tests, and receive a truthful result.

## Phase 4 — Recovery, UX, and onboarding

- [ ] Implement safe Git checkpoints and rollback with pre-existing-work protection.
- [ ] Replace placeholder workspace file tree/editor/terminal with real data.
- [ ] Complete provider settings and credential validation UI.
- [ ] Replace fake/inactive project intelligence claims with implemented functionality or remove the claims.
- [ ] Add clear onboarding, connection status, privacy explanation, and troubleshooting.
- [ ] Add empty, loading, error, disconnected, denied, and interrupted states.
- [ ] Test keyboard accessibility and responsive layouts.

**Exit gate:** a first-time user can understand and operate the core product without developer intervention.

## Phase 5 — Public beta

- [ ] Run end-to-end tests on a clean Windows environment.
- [ ] Perform threat-model review and dependency/security review.
- [ ] Test malicious repository instructions and prompt-injection attempts.
- [ ] Test provider outages, rate limits, local-agent disconnects, and interrupted writes.
- [ ] Verify no secrets appear in logs, audit records, browser responses, or test artifacts.
- [ ] Publish known limitations and supported configurations.
- [ ] Add issue templates, contribution instructions, and release notes.
- [ ] Tag a version only after the v0.1 exit criteria pass.

**Exit gate:** an external developer can install, use, understand, and safely report issues against the release.

## Post-v0.1 — Only after the core is stable

Potential follow-on work:
- Better codebase indexing and symbol-aware retrieval.
- Stronger project memory with explicit user control.
- More model providers and capability-aware routing.
- Improved streaming and context management.
- Optional multi-agent workflows for tasks that justify them.
- Cross-platform local-agent support.
- Optional deployment workflows with explicit approvals.

## Priority rule

When choosing the next task, prefer work that closes a gap in the real user journey or reduces a security/reliability risk. Defer features that only make the product look more autonomous.
