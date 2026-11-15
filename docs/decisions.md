# FORGE AI — Product & Technical Decisions

This file records durable decisions and the reasoning behind them. Update it when a decision changes; do not silently rewrite history.

## D-001 — Free-first, BYOK product model

**Status:** Accepted  
**Decision:** FORGE AI should be usable without a FORGE subscription and should initially use user-supplied provider credentials or local inference. No shared FORGE inference API is part of the initial release.  
**Reason:** Keeps the project accessible and avoids operating a costly shared inference service.  
**Trade-off:** Users may still pay their selected cloud provider. Local models depend on user hardware.

## D-002 — Self-hostable architecture with local workspace execution

**Status:** Accepted as product direction; implementation must be verified  
**Decision:** Keep a web UI, orchestration API, and local workspace agent as distinct responsibilities. The local agent performs filesystem and terminal operations on the user's machine.  
**Reason:** Separates user interface/model orchestration from access to local project files.  
**Trade-off:** More setup and operational complexity than a single-process desktop application. The trust boundary between API and local agent must be carefully enforced.

## D-003 — Hybrid cloud/local model routing

**Status:** Accepted  
**Decision:** Support BYOK cloud providers and optional Ollama/local models. Provide a strict Local-Only mode that cannot silently fall back to a cloud provider.  
**Reason:** Gives users a choice between model capability, cost, latency, and privacy.  
**Trade-off:** Provider capabilities differ; routing and fallback must respect explicit user constraints.

## D-004 — Bounded plan–inspect–edit–verify loop

**Status:** Accepted  
**Decision:** The primary agent workflow is plan → inspect → propose/approve → edit → test → bounded repair → report.  
**Reason:** A transparent workflow is easier to trust and debug than unrestricted autonomy.  
**Trade-off:** Requires approval and review UX and may be slower than unrestricted tool execution.

## D-005 — Local agent is the security enforcement point

**Status:** Accepted  
**Decision:** The model does not decide whether an operation is safe. Trusted local-agent code validates paths, protected files, command risk, authorization, and execution limits.  
**Reason:** Model output and repository content are untrusted.  
**Trade-off:** Security rules require ongoing maintenance and adversarial testing.

## D-006 — Git-aware recovery is a core capability

**Status:** Accepted as v0.1 requirement  
**Decision:** Provide inspectable diffs, safe checkpoints, and rollback. Do not automatically commit or push.  
**Reason:** Users need a reliable way to review and recover from agent changes.  
**Trade-off:** Checkpoint design must preserve pre-existing uncommitted work and avoid destructive Git operations.

## D-007 — Keep v0.1 deliberately narrow

**Status:** Accepted  
**Decision:** Prioritize a complete small-project coding workflow over agent swarms, advanced AST graphs, analytics, or broad integrations.  
**Reason:** A working end-to-end product is more valuable than a large list of disconnected capabilities.  
**Trade-off:** Some ambitious features remain explicitly out of scope until the core is reliable.

## D-008 — Open-source license must be explicitly chosen

**Status:** Open / owner decision required  
**Observation:** The product is intended for public Git repository release, but the current README states "Private — All rights reserved" and no root LICENSE file appeared in the inspected root listing.  
**Decision:** Do not infer or select a license automatically. The owner must choose the license and ensure all dependencies/assets are compatible before public release.
