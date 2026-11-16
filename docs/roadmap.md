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
- [x] Implement safe file editing with before/after diff data. *(Implemented+tested: `apply_edit` with unified diff + dry-run preview; `revert_file` undo buffer.)*
- [ ] Add command approval, execution timeout, output limits, cancellation, and process cleanup. *(Partial: command approval gated in the loop; timeouts/output limits exist in the executor; cancellation not yet.)*
- [ ] Make Git status/diff/checkpoint/rollback reliable and preserve pre-existing changes. *(Partial: checkpoint-returns-hash and `git_rollback` added+tested; broader reliability unverified.)*
- [ ] Add focused security tests for all local tools.

**Exit gate:** local agent can safely inspect, edit, test, and restore a throwaway repository while rejecting unauthorized paths and risky commands.

## Phase 2 — Dependable model and provider layer

- [ ] Implement one complete BYOK provider setup and validation flow.
- [ ] Keep credentials out of browser responses, logs, and error payloads.
- [ ] Reconcile the provider list in the UI, README, registry, and backend.
- [ ] Enforce provider allowlists and user model selection.
- [ ] Implement explicit fallback rules for provider errors/rate limits.
- [x] Enforce Local-Only routing with tests proving no cloud call occurs. *(Implemented+tested: router strips non-Ollama candidates under `local_only`, discovery skipped, tests assert cloud is never attempted.)*
- [ ] Add transparent model/provider/latency/fallback reporting.
- [ ] Add budget and context controls before broad automatic routing.

**Exit gate:** user can configure a provider, run a real request, see which model answered, and prove that Local-Only does not contact cloud providers.

## Phase 3 — End-to-end coding loop

- [ ] Connect Agent Studio prompt submission to the task API.
- [ ] Build structured plans from actual repository inspection.
- [x] Add plan review and explicit approval before consequential edits. *(Implemented+tested: every write/command/commit is approval-gated over WebSocket; fail-closed on disconnect/timeout.)*
- [ ] Retrieve relevant files only; apply ignore and privacy policies before provider transmission. *(Partial: the agent reads files on demand via tools rather than dumping the repo; secret/ignore redaction exists but is not yet applied on every tool path.)*
- [x] Apply edits through local-agent tools and return exact diffs. *(Implemented+tested: the loop calls `apply_edit`; the UI shows the unified diff for approval.)*
- [x] Execute selected tests/builds and capture real output/exit codes. *(Implemented+tested: `verification_node` runs real `run_tests` and captures stdout/stderr/exit code.)*
- [x] Implement bounded repair attempts based on real diagnostics. *(Implemented+tested: test failure is fed back as `repair_context`; bounded by `max_retries`.)*
- [ ] Add cancellation, disconnect recovery, task status persistence, and useful error states. *(Not yet: the Task API is still CRUD and does not control the live run.)*
- [ ] Report changed files, commands, model/provider, verification, and remaining issues. *(Partial: completion event reports modified_files, executed_commands, and verification; model/provider surfacing pending.)*

**Exit gate:** a user can ask FORGE to implement a small feature in a real project, review the plan and diff, run tests, and receive a truthful result.

> **Status note (this iteration):** the plan→inspect→propose→approve→apply→test→repair loop is now
> implemented and unit-tested with injected fakes (33 tests across api + local-agent, web typecheck clean).
> It has **not** yet been exercised end-to-end against a live paired agent + real LLM; that integration
> run is the remaining gate before calling Phase 3 done.

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
