# Deployment

The MVP runs as three pieces: PostgreSQL 16, the FastAPI container (`backend/Dockerfile`) and the Next.js container (`frontend/Dockerfile`, standalone output).

## Local / single host: Docker Compose

```bash
cp .env.example .env     # set real secrets (see below)
docker compose up --build -d
docker compose exec api python -m app.seed   # demo data, optional
```

The `api` container runs `alembic upgrade head` on every start, then uvicorn on :8000. `web` serves on :3000 and proxies `/api/*` and `/media/*` to `http://api:8000`.

## Suggested hosted setup

| Piece | Option | Notes |
|---|---|---|
| Database | Managed Postgres (Neon, Supabase, Render, RDS…) | Needs the `btree_gist` extension, which the first migration creates. The DB user must be allowed to `CREATE EXTENSION`, or pre-create it. |
| API | Render, Fly.io, Railway or any container host | Build `backend/`. Mount a **persistent volume** at `STORAGE_DIR` for private documents. |
| Web | Vercel or a container host | Set `API_INTERNAL_URL` at **build time** (rewrites are compiled in) and at runtime. |
| Photos | Cloudinary (`STORAGE_BACKEND=cloudinary`) | Only public photos go to Cloudinary. Private documents always stay on the API's volume. |

Put the web app and the API behind HTTPS. Because the browser only talks to the web origin, the API can stay private (reachable only from the web service) except for `/media` photos if you use local storage. The web app proxies those too.

## Required environment

| Variable | Service | Production value |
|---|---|---|
| `DATABASE_URL` | api | `postgresql+asyncpg://user:pass@host:5432/db` |
| `JWT_SECRET` | api | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `FILE_SIGNING_SECRET` | api | Another long random string |
| `COOKIE_SECURE` | api | `true` |
| `CORS_ORIGINS` | api | The public web origin, e.g. `https://propcheck.ng` |
| `API_PUBLIC_URL` | api | The API's own base URL (used in local photo URLs) |
| `FRONTEND_URL` | api, web | The public web origin (share links, metadata) |
| `STORAGE_BACKEND`, `STORAGE_DIR` | api | `local` + a volume path, or `cloudinary` + `CLOUDINARY_*` |
| `PAYSTACK_SECRET_KEY`, `PAYSTACK_PUBLIC_KEY` | api | **Test keys only** (`sk_test_…`/`pk_test_…`). Leave empty for the simulator. Live keys are rejected at startup. |
| `PAYSTACK_CALLBACK_URL` | api | `https://<web>/dashboard/renter/reservations` |
| `REDIS_URL` | api | `redis://<host>:6379/0`. Required before running more than one API instance; without it rate limits are per process (development fallback). See [RATE_LIMITING.md](RATE_LIMITING.md). |
| `TRUSTED_PROXIES` | api | The address(es) of the web server / load balancer in front of the API, so per-IP limits see the visitor's IP. |
| `API_INTERNAL_URL` | web (build + run) | How the web server reaches the API, e.g. `http://api:8000` or the private service URL |

## Render Blueprint

`render.yaml` creates the database (`propcheck-db`), a Key Value (Redis) instance for rate limits (`propcheck-redis`), the API (`propcheck-api`) and the web app (`propcheck-web`) in Frankfurt on the free plan. Secrets are generated, and `DATABASE_URL` and `REDIS_URL` are wired automatically. Render allows **one free Postgres per workspace**: delete an older free database first, or the Blueprint sync fails. Render can't derive public URLs in a Blueprint, so it asks for these on creation:

| Prompt | Value |
|---|---|
| `API_PUBLIC_URL` (api), `API_INTERNAL_URL` (web) | the API's URL, e.g. `https://propcheck-api.onrender.com` |
| `FRONTEND_URL` (api + web), `CORS_ORIGINS` (api) | the web URL, e.g. `https://propcheck-web.onrender.com` |
| `PAYSTACK_CALLBACK_URL` | `<web URL>/dashboard/renter/reservations` |
| `PAYSTACK_*_KEY` | empty (simulator) or test keys |

URLs are `https://<service name>.onrender.com` unless the name is taken. If Render adds a suffix, correct the values afterwards and redeploy the web app with **Clear build cache & deploy**. Seed demo data from the API's **Shell**: `python -m app.seed`.

## Render notes

- **Web service:** set `API_INTERNAL_URL` to the API's URL, e.g. `https://propcheck-1.onrender.com`, with no trailing slash and no `/api`. It is read at build time (rewrites) and at runtime (server-rendered pages), so after changing it use **Manual Deploy → Clear build cache & deploy**. If it is missing, the web server falls back to `http://localhost:8000` and pages fail with `TypeError: fetch failed` / `ECONNREFUSED`, so on Render (detected via its `RENDER` variable) `next.config.ts` now fails the build instead. The Docker image also carries the build-time value into the runtime stage as a default. There is no `NEXT_PUBLIC_` API variable on purpose: the browser only calls the web origin, which keeps the session cookie first-party.
- **API service:** set `DATABASE_URL` to the Render Postgres **internal** URL (any `postgres://` URL is converted to `postgresql+asyncpg://` automatically). Keep the Docker start command so `alembic upgrade head` runs before uvicorn. If `/api/health` and `/api/reference` answer but login or `/api/properties` return 500, the API cannot reach its database or the migrations have not run.

## Operations checklist

- Back up Postgres and the private storage volume together (documents are referenced by key from the DB).
- The auth rate limiter is in-memory. Run one API replica, or replace it with a shared store before scaling out.
- Create staff accounts directly in the database or with a one-off script (`role` = `REVIEWER`/`ADMIN`). They cannot be self-registered.
- Verifications expire by date automatically in every response. No cron job is needed for correctness. A scheduled job that persists `EXPIRED` would only tidy the stored status.
- Notifications currently log to stdout (`propcheck.notifications`). Plug email/SMS providers into `app/services/notifications.py`.
- Before any real money: legal and regulatory review, live-key handling, and a proper ledger. The reservation flow is a demo.
