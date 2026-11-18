# FORGE AI — Deploying a Free Public Demo

**Status:** Procedure. The application changes it relies on are implemented and tested
(see *Verification* at the end); the hosting steps below are a written procedure and
have **not** been executed against live Render/Vercel/Neon accounts from this repo.

This guide covers one goal: a **free, public URL you can link people to**, using
Vercel (web) + Render (API) + Neon (Postgres). It is not a production hardening guide.

---

## 1. What actually gets hosted — and what a demo can show

The product has three parts, but only two are "hosted":

| Part | Where it runs | In this guide |
|------|---------------|---------------|
| `apps/web` (Next.js) | Vercel | Hosted |
| `apps/api` (FastAPI + WebSockets) | Render | Hosted |
| `services/local-agent` (Python) | **Each user's own machine** | Not hosted — by design |

**Be honest with visitors about the limits:**

- The **local agent runs on the visitor's own Windows machine** and dials into your
  API to pair. A random person clicking your link will not download and run it, so a
  public demo realistically shows the **UI and the API-backed state** (provider
  config, plan/approval screens, Code Intelligence, device list), **not** the live
  edit → test → repair loop end-to-end.
- **There is no sign-in / sign-up screen in the frontend.** Authentication is handled
  by an automatic login (see §5). With a public demo as-is, **all visitors share one
  account** (`dev@forge.local`). That means **anything one visitor types in — including
  provider API keys on the Models page — is visible to every other visitor.**
  Put a visible notice in the demo: *"Shared public demo — do not enter real API keys."*

If you need per-visitor isolation or a real login, that is additional work (a login/
register page plus removing the shared autologin); it is out of scope here.

---

## 2. Cost reality

- No inference cost on the host: FORGE AI is BYOK, so the server never pays for model
  calls. The host only runs the small API process + database.
- **Nothing in the recommended stack expires** if you use **Neon** for the database.
  (Render's *own* free Postgres is deleted after ~30 days — do not use it; use Neon.)
- Render's free web service **sleeps after ~15 min idle**; §4 adds a keep-alive ping so
  the demo link does not feel broken on first click. One always-awake service uses
  ~720 of Render's 750 free instance-hours/month.
- Vercel's Hobby plan is free and permanent, but is for **non-commercial** use per
  Vercel's terms. A demo of this open-source project is fine; a paid product is not.

---

## 3. Prerequisites

- GitHub repo pushed (Render and Vercel deploy from Git).
- Free accounts: [Neon](https://neon.tech), [Render](https://render.com),
  [Vercel](https://vercel.com).
- A password/key generator. For `SECRET_KEY`:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

---

## 4. Step-by-step

### Part A — Database (Neon)

1. Create a Neon project. Pick a region close to your Render region.
2. Copy the **connection string**. It looks like:
   ```
   postgresql://USER:PASSWORD@ep-xxxx.REGION.aws.neon.tech/DBNAME?sslmode=require
   ```
3. Use it **verbatim** as `DATABASE_URL`. The API normalizes it automatically:
   the `postgresql://` scheme is upgraded to the async driver and `sslmode=require`
   is translated to an SSL connection (see `apps/api/app/core/config.py`,
   `normalize_db_url`). You do **not** need to hand-edit it to `postgresql+asyncpg://`.
4. (Optional) To inspect the DB in TablePlus/DBeaver, use the **same credentials** but
   the plain `postgresql://` form — GUI clients do not want the `+asyncpg` driver.

### Part B — API (Render, Docker)

Create a new **Web Service** → **Build from a Dockerfile**.

- **Dockerfile path:** `infrastructure/Dockerfile.api`
- **Docker build context directory:** `apps/api`
- **Instance type:** Free

> **Docker Command (override).** The repo's Dockerfile hardcodes port 8000 and does
> **not** run migrations. With `DEBUG=false` the app does **not** auto-create tables
> (table creation is dev-only, see `apps/api/app/main.py`). Override the start command
> in Render so it runs migrations and binds to Render's injected `$PORT`:
> ```
> sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
> ```
> This keeps the repo's Dockerfile unchanged. (Alternative for other hosts: change the
> Dockerfile `CMD` to the shell form `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
> and run `alembic upgrade head` as a separate release step.)

**Environment variables** (Render → Environment):

| Key | Value | Notes |
|-----|-------|-------|
| `DATABASE_URL` | *Neon connection string from Part A* | Paste as-is (with `?sslmode=require`). |
| `SECRET_KEY` | *output of the generator above* | **Keep this stable.** It also derives the key that encrypts stored provider API keys — changing it makes previously saved provider keys undecryptable. |
| `DEBUG` | `false` | Disables SQL echo and dev-only table seeding. |
| `CORS_ORIGINS` | `https://YOUR-APP.vercel.app` | Your Vercel URL, **no trailing slash**. Comma-separate if more than one. Fill in after Part C, then redeploy. |
| `ENCRYPTION_KEY` | *optional* | If unset, the provider-key encryption key is derived from `SECRET_KEY`. Set an explicit stable value if you prefer to rotate it independently. |
| `REDIS_URL` | *leave unset* | Redis is optional. |

After the first deploy, note the service URL, e.g. `https://forge-ai-api.onrender.com`.

**Keep-alive (beat the 15-min sleep).** Create a free cron on
[cron-job.org](https://cron-job.org) (or similar) that GETs your health endpoint every
~10 minutes:
```
https://forge-ai-api.onrender.com/api/health
```

### Part C — Web (Vercel)

Import the repo in Vercel.

- **Root directory:** `apps/web`
- **Framework preset:** Next.js (auto-detected)

**Environment variables** (Vercel → Settings → Environment Variables):

| Key | Value | Notes |
|-----|-------|-------|
| `NEXT_PUBLIC_API_URL` | `https://forge-ai-api.onrender.com/api` | Keep the `/api` suffix. |
| `NEXT_PUBLIC_WS_URL` | `wss://forge-ai-api.onrender.com/ws/user` | Use `wss://` (TLS), not `ws://`. |
| `NEXT_PUBLIC_DEV_AUTOLOGIN` | `true` | Required for visitors to get in without a login screen (see §5). |
| `NEXT_PUBLIC_AGENT_SCRIPT` | *leave unset* | Local-dev only. |

Deploy, then copy the Vercel URL **back into Render's `CORS_ORIGINS`** and redeploy the
API, or the browser will block all API calls.

---

## 5. Sign-in with `DEBUG=false` — verified behavior

There is no login UI; the frontend signs in automatically on load
(`apps/web/src/components/providers/app-bootstrap.tsx`). With `DEBUG=false`:

1. The dev account is **not** seeded (seeding is `DEBUG`-only).
2. The frontend tries to log in as `dev@forge.local`; that fails on a fresh DB (`401`).
3. It then calls `/api/auth/register` (an **open**, non-`DEBUG`-gated endpoint) to
   create `dev@forge.local`, and logs in successfully.

**This was runtime-verified** against a fresh migrated DB with `DEBUG=false`:
`login → 401`, `register → 201`, `login → 200` (token works), `GET /me → 200`.

Consequence: the demo works, but **every visitor is the same shared `dev@forge.local`
user**. See the honesty notice in §1. If you set `NEXT_PUBLIC_DEV_AUTOLOGIN=false`
there is currently **no way to sign in** — the app loads signed-out with no login form.

---

## 6. Post-deploy smoke check

1. `GET https://<api>/api/health` returns OK; `GET https://<api>/api/health/db`
   confirms the Neon connection works.
2. Open the Vercel URL. The "Connecting to backend…" banner should clear to online.
   If it shows *"Can't reach the FORGE AI backend on https://<api>"*, check
   `NEXT_PUBLIC_API_URL` and the API's `CORS_ORIGINS`.
3. Browser devtools → Network: the WebSocket to `wss://<api>/ws/user/...` connects.
4. The provider/workspace/device panels load without errors (they will be empty).

See also `docs/smoke-test.md`.

---

## 7. Known limitations & security notes for a public demo

- **Shared account** (§1/§5): no per-visitor isolation; provider keys are shared.
  Display a "do not enter real API keys" notice.
- **Open registration:** `/api/auth/register` is unauthenticated and not rate-limited.
  Anyone can create accounts against your public API.
- **User WebSocket is unauthenticated:** `/ws/user/{user_id}` accepts any `user_id`
  with no token check (`apps/api/app/main.py`). The *agent* WebSocket is authenticated;
  the user one is not. Acceptable for a throwaway demo, not for real users.
- **Cold starts:** even with the keep-alive ping, a sleeping free service drops live
  WebSocket connections; a reconnect/refresh is sometimes needed.
- **Secret stability:** keep `SECRET_KEY` (and `ENCRYPTION_KEY` if set) stable across
  redeploys, or stored provider credentials become undecryptable.

These are consistent with the gaps tracked in `docs/roadmap.md` and `docs/security.md`;
this guide does not resolve them.

---

## 8. Verification status of the supporting code

Changes this deploy relies on (made in the branch that added this doc):

- `DATABASE_URL` normalization for managed Postgres DSNs — **unit-checked** against
  Neon/Supabase/Render/local/sqlite URL shapes.
- API test suite — **40 passed** (sqlite-backed).
- Web type-check (`tsc --noEmit`) — **clean**.
- `DEBUG=false` register → login path — **runtime-verified** (see §5).

**Not** verified: an actual end-to-end deploy to live Render/Vercel/Neon accounts, and
the full agent editing loop over a hosted connection.
