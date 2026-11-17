# FORGE AI — End-to-End Smoke Test

**Purpose:** manually exercise the full `plan → inspect → propose → approve → apply → test → repair → rollback`
loop against a **live paired agent + a real model**. This is the integration gate the roadmap flags as the
remaining step before Phase 3 can be called done — the loop is unit-tested (33 tests) but, until this checklist
passes, it has not been proven end-to-end.

Work top to bottom. Each step lists what to do, the **expected** result, and how to tell it actually worked.
If a step fails, stop and record what you saw — a green checkbox only counts when you observed the result.

---

## 0. Prerequisites

- [ ] Windows, with the three service venvs/node_modules already installed (`scripts\setup.ps1` if not).
- [ ] `apps/api/.env` exists with a stable `SECRET_KEY` (provider-key encryption derives from it; changing it later
      makes previously stored keys undecryptable).
- [ ] A **real model credential** to test with — either:
  - a cloud provider API key (OpenAI / Anthropic / Gemini / Groq / etc.), **or**
  - a running [Ollama](https://ollama.com) with at least one model pulled (e.g. `ollama pull llama3.1`) for the
    Local-Only path.
- [ ] A **throwaway git repo** to act as the workspace (never point this at real work for the first run). Create one:
      ```
      mkdir C:\tmp\forge-smoke && cd C:\tmp\forge-smoke && git init && echo print("hi") > app.py && git add -A && git commit -m init
      ```

---

## 1. Start the stack

- [ ] From the repo root: `powershell -ExecutionPolicy Bypass -File scripts\dev.ps1`
      (or start the two services by hand — see below).
- [ ] **API** — open http://localhost:8000/api/health → `{"status":"healthy",...}`.
- [ ] **DB** — http://localhost:8000/api/health/db → `{"status":"healthy","database":"connected"}`.
- [ ] **API docs** — http://localhost:8000/docs loads the Swagger UI.
- [ ] **Web** — http://localhost:3000 renders the app shell (no console errors blocking render).

Manual start (equivalent to `dev.ps1`):
```
# terminal 1 — API
cd apps\api;  .\venv\Scripts\python.exe run.py
# terminal 2 — web
cd apps\web;  npm run dev
# terminal 3 — local agent (after pairing, step 3)
powershell -ExecutionPolicy Bypass -File scripts\run-agent.ps1
```

---

## 2. Account + provider key (BYOK)

- [ ] Register / log in through the web UI. Expected: you land in an authenticated session (token stored).
- [ ] Go to provider settings and add your model credential.
- [ ] **Security check:** reload the page, open DevTools → Network/Application. The raw API key must **not** appear
      in any response body, local storage, or cookie. It is encrypted server-side; the UI should only ever show a
      masked/"configured" state.
- [ ] (Cloud path) The provider should validate — the app discovers which models the key can actually call.

---

## 3. Pair the local agent

- [ ] In the web UI, open **Connect Agent**. It shows a **pairing code** and a **device ID**.
- [ ] In a terminal, from the repo root:
      ```
      powershell -ExecutionPolicy Bypass -File scripts\run-agent.ps1 -PairingCode <CODE> -DeviceId <DEVICE_ID>
      ```
- [ ] Expected agent output: `Paired successfully. Credentials saved. Starting agent...` then a connected/ready log.
      The token is written encrypted to `services/local-agent/.forge_agent_token`.
- [ ] Expected UI: the device flips to **connected** (live status, not a hardcoded badge).
- [ ] Reconnect test: Ctrl+C the agent, rerun `run-agent.ps1` **with no arguments** → it reconnects using the saved
      token (no re-pairing needed).

---

## 4. Workspace + task submission

- [ ] Create/select a workspace pointing at the throwaway repo from step 0 (`C:\tmp\forge-smoke`).
      Expected: the selected workspace is clearly shown in the UI.
- [ ] In Agent Studio, submit a small, concrete task, e.g.
      *"Add a function `greet(name)` to app.py that returns `Hello, <name>!`, and a quick test for it."*
- [ ] Expected: a task starts; you see **live tool activity** (read_file / list_directory / search_text) stream in
      as the agent inspects the repo — not a frozen spinner, not fabricated file names.

---

## 5. Approval gating (the core safety property)

- [ ] When the agent proposes an **edit**, an **Approval card** appears showing a **unified diff** (green `+` / red `-`).
      Nothing is written to disk yet (confirm: `git status` in the workspace is still clean at this point).
- [ ] **Reject** once. Expected: no file change; the agent is told the edit was rejected and reacts (re-plans or stops).
      Verify `git status` shows no modification.
- [ ] Re-run the task and **Approve** the edit. Expected: only now does `app.py` change on disk, and the diff shown
      matches the actual change (`git diff` in the workspace equals what you approved).
- [ ] When the agent proposes a **command** or a **git commit**, it must likewise ask first, showing the exact command.
      Approve a test command; reject a commit to confirm commits are not automatic.

**Fail-closed check:** stop the local agent mid-task while an approval is pending (or just let an approval sit).
Expected: the operation is **denied**, not silently applied — approvals default to "no" on disconnect/timeout.

---

## 6. Verify → repair

- [ ] After an approved edit, the agent runs the project's **real** tests/build and shows real output + exit code
      (not a canned "tests passed").
- [ ] Force a failure to exercise repair: give a task you expect to break a test (or approve an edit you know is wrong).
      Expected: the failure output is fed back, the agent attempts a **bounded** repair (capped by `max_retries`, default 2),
      and either fixes it or reports the failure honestly — it must not loop forever or claim success without evidence.
- [ ] Final summary lists **changed files**, **executed commands**, and **verification pass/fail** that match reality.

---

## 7. Rollback / undo

- [ ] Use the per-file **revert** (undo buffer) on a file the agent edited. Expected: the file returns to its
      pre-edit content; a file the agent *created* is removed on revert.
- [ ] If you created a FORGE checkpoint, test `git_rollback` on the throwaway repo. Expected: `git reset --hard` to the
      checkpoint. **Confirm it does not destroy pre-existing uncommitted work** — this is a coarse net; prefer per-file revert.

---

## 8. Local-Only privacy mode (negative test)

- [ ] Set the project's privacy mode to **LOCAL_ONLY** (requires Ollama from step 0).
- [ ] Watch the API log while submitting a task. Expected: **no cloud provider is contacted** — model discovery is
      skipped and only `ollama/...` models are attempted. (Unit test `test_router_local_only.py` asserts this; here you
      confirm it on a live run.)
- [ ] With Local-Only on and **no** local model available, expected: a clear error
      (*"Local-Only mode: no local (Ollama) model is available..."*) — it must **not** fall back to cloud.

---

## 9. Teardown

- [ ] Ctrl+C `dev.ps1` (or each terminal). Confirm ports 8000/3000 are released.
- [ ] The throwaway repo can be deleted. `services/local-agent/forge-audit.jsonl` will contain this run's audit
      entries (it is now git-ignored, so it won't dirty the repo).

---

## Known gaps to expect (not failures)

These are documented-open, so don't log them as smoke-test failures:

- **Task API is still CRUD** — pause/resume/cancel in the Task API do **not** control a live run yet. Cancellation
  mid-run is not implemented.
- **Secret redaction** is not yet applied on every tool path before cloud transmission (defence-in-depth, not a guarantee).
- **Model/provider attribution** in the final report is partial (changed files / commands / verification are reported;
  which model answered is not fully surfaced).
- **ESLint** is currently broken in `node_modules` (a pre-existing `object-keys` issue); `npx tsc --noEmit` is the
  meaningful type gate.

If steps 1–8 pass on a live agent + real model, the Phase 3 end-to-end gate in `docs/roadmap.md` is met and can be ticked.
