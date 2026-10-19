# Build log & decisions

Decisions made while building the MVP, with the reasoning, so they can be revisited.

## Backend

- **One state-machine engine for every workflow** (`services/state_machine.py` + `services/workflows.py`). Transitions are data. Each call locks the row, rejects unknown or duplicate moves (409), checks role (403) and guards, applies side effects and writes the audit row in the same transaction. Duplicate release, refund or approval therefore fails structurally, not through scattered `if`s.
- **Enums stored as VARCHAR**, not native Postgres enums, so new statuses don't need enum migrations.
- **Concurrency is enforced in the database too**: an `EXCLUDE USING gist` constraint for overlapping inspection slots (needs `btree_gist`), and a partial unique index so a slot has at most one live booking. API pre-checks exist only to give friendlier messages.
- **Effective status is computed on read.** A `VERIFIED` record past its expiry is shown as `EXPIRED` everywhere (search filters, badges, reports) without a cron job.
- **Material edits expire a verification.** Changing address, area, type, bedrooms, rent or any fee on a verified listing moves its case to `EXPIRED` as a system action (actor `null` in the audit log).
- **Mandatory checks** (identity, authority to market, location, fees, availability) must be `PASSED`. The other three may be `NOT_APPLICABLE`.
- **Conflict of interest**: staff cannot act on a case they submitted, a property they own or list, or an agent application of their own.
- **Reservations require a currently verified, available property.** Reserving an unverified listing would contradict the product promise. The property moves AVAILABLE → RESERVED on payment, → LET on release, → AVAILABLE on refund.
- **Refunds are requested by the renter and decided by staff.** The status stays `PENDING_RELEASE` until a reviewer acts, so refunds stay a human, audited decision.
- **Reservation amount** = 10% of annual rent, rounded to ₦1,000 (minimum ₦1,000), computed only on the server. `/reservations/terms?property_id=` exposes it so the UI never recalculates it.
- **Private files are never public URLs.** The DB stores storage keys. Links are HMAC-signed and expire in 10 minutes, and are issued only after an access check.
- **Contact consent**: agent phone/WhatsApp/email are `null` in public responses unless the agent opted in. They are revealed to a renter whose request was assigned to that agent, because the renter asked for that connection.
- **404 instead of 403** for private records you can't see (cases, bookings, reservations, requests), so ids aren't confirmed to outsiders.
- **Tests run against real Postgres** (the guarantees above are database features), migrated with Alembic, with each test in a rolled-back outer transaction using `join_transaction_mode="create_savepoint"`.

## Frontend

- **Next.js 16**: `middleware.ts` is now `proxy.ts`. `params`, `searchParams` and `cookies()` are async only. Error boundaries receive `retry` (not `reset`). The proxy only does an optimistic cookie check for `/dashboard/*`. Each dashboard section layout re-checks the role on the server.
- **Same-origin API via rewrites** (`/api/*`, `/media/*`). The httpOnly cookie is first-party, there are no CORS preflights, and signed file links (`/api/files/...`) work as relative URLs. Because rewrites are compiled at build time, `API_INTERNAL_URL` is a Docker build argument.
- **Server-rendered pages with small client islands.** Mutations call the API from the browser and then `router.refresh()`. The generic `ActionButton` handles optional reasons and dates for workflow actions.
- **Filters are plain GET forms**, so search works without JavaScript. The mobile filter sheet is progressive enhancement.
- **Dates are always shown in Africa/Lagos (WAT)**, whatever the server or browser timezone. A machine in another timezone showed 10:00 WAT slots as 06:00 before this fix.
- **Plain `<img>` for listing photos** rather than `next/image`. Photos come from the API or Cloudinary, and Next 16's image optimizer blocks local IPs by default.
- **Map shows an approximate circle**, not a pin, so exact addresses aren't broadcast.
- Vitest uses the `threads` pool. Forked workers timed out starting on Windows under load.

## Seed data

`python -m app.seed` creates 4 renters, 1 landlord, 2 reviewers, 1 admin and 7 agents (5 verified, 1 pending, 1 suspended); 16 listings across Lagos, Port Harcourt, Enugu, Awka/Onitsha and Owerri (10 verified, 5 awaiting review, 1 rejected with a failed check); inspection slots and bookings; test reservations in every state; house-search requests with agent enquiries; reports that are open, resolved and rejected; and about 330 fictional nearby places. Every status is reached through the real state machine, so the audit log looks like production data. 12 of the 16 listings use real house photos, resized into `backend/app/seed_assets` and mapped in `seed.REAL_PHOTOS`. Photos with third-party watermarks or logos were left out. The rest are generated PNG placeholders, and the rejected listing keeps a placeholder on purpose. Re-running the seed on an existing database only syncs listing photos. Password for all accounts: `PropCheck2026`.

## Five-state launch & nearby places (2026-10-06)

- **Coverage is app-wide, not just for nearby places** (product decision): only Lagos, Rivers, Enugu, Anambra and Imo are offered in filters and selectors, accepted by the API, or seeded. Abuja demo data was moved to Enugu, Anambra, Imo and Port Harcourt. `ACTIVE_STATES` plus the `LOCATIONS` data in `app/reference` control it, so re-enabling a state needs no migration.
- **Location hierarchy** State → City → Area (+ LGA). `property.area` and `house_search_request.area` were added in migration 0002. The `city` search filter also matches `area`, so old `?city=Lekki` links keep working.
- **Nearby places use seeded PostgreSQL data behind a provider interface.** Demos are predictable and work offline. Distance uses Haversine after an indexed bounding-box prefilter, which needs no PostGIS. The radius is capped at 10 km and results at 50.
- **Nothing implies nearby places are verified.** Demo rows are labelled, and every view carries the convenience notice. Wrong data is handled through `place_report` and the reviewer queue.
- **Directions use Google Maps URLs** (`/maps/dir/?api=1`), which open the Maps app on phones; tiles remain OpenStreetMap.

## Brief alignment (2026-10-07)

- **The five-state launch stays.** The original brief targeted Lagos and FCT, with seed data in Oyo and Kaduna. The later five-state decision supersedes it.
- **Brief paths are now canonical:** `/api/properties/{id}/inspection-slots`, `/dashboard/renter/house-search` (plus `[id]`), `/dashboard/agent/inspection-slots`, `/dashboard/agent/verification` and `/dashboard/reviewer/audit-log`. Old URLs stay as a hidden API alias and permanent redirects, so existing links keep working.
- **No shadcn/ui.** The app keeps its own small component set in `components/ui.tsx`, which already covers what the pages need. Moving now would rewrite every page with no change in behaviour.
- **The seed covers every workflow state** so each reviewer queue and dashboard has something to show. `tests/test_seed.py` runs the seed inside a rolled-back transaction to keep it working.

## Async backend & rate limiting (2026-10-12)

- **The whole backend is async**: routes, dependencies, state-machine guards, presenters, seed and the Alembic env. It uses `AsyncSession` with `expire_on_commit=False`, because touching an expired attribute would need implicit I/O. Sync and async sessions are never mixed.
- **asyncpg, not psycopg.** psycopg's async mode fails on the Windows Proactor event loop. Settings rewrite any `postgres://`, `postgresql://` or `+psycopg` URL to `postgresql+asyncpg://`, so a hosting provider's URL can be pasted as-is.
- **Blocking work stays off the event loop**: Argon2 hashing, disk writes, and the Paystack and Cloudinary calls.
- **Rate limits** (`services/ratelimit.py`, rules in `RATE_LIMIT_*` settings, see docs/RATE_LIMITING.md). Counters live in Redis when `REDIS_URL` is set, otherwise in memory for development. The limiter fails open, so an outage never locks users out, and returns 429 with `Retry-After`. Per-IP limits trust `X-Forwarded-For` only from `TRUSTED_PROXIES`.

## Landing hero carousel (2026-10-16)

- **Slides are config** (`hero-images.ts`). The client carousel autoplays every 5 s with a 900 ms crossfade, has prev/next/dots, pauses on hover and focus, and respects reduced motion. Missing files are dropped on the server, and with none the hero is plain green.
- The hero images themselves are the user's choice and are never replaced. See "Deployment on Render" for how they are served.

## CI (2026-10-18)

- **GitHub Actions only checks and never deploys** (`.github/workflows/ci.yml`, docs/CI.md). Frontend and backend jobs run against a `postgres:16` service, including `alembic upgrade head` and `alembic check`. It needs no secrets.
- **mypy is `continue-on-error`** until about 46 existing SQLModel typing errors are fixed.
- **`/` and `/health` routes** were added so hosts can health-check the API without touching the database.

## Deployment on Render (2026-10-19)

The live demo runs from `render.yaml` (a Render Blueprint): Postgres, Key Value (Redis), the API and the web app, all Docker, free plan, Frankfurt. Render added a `-5hn3` suffix to each name, so the site is https://propcheck-web-5hn3.onrender.com and the API https://propcheck-api-5hn3.onrender.com.

- **Public URLs are prompts, not derived.** A Blueprint cannot know a service's final URL, because Render suffixes a taken name. That suffix caused the first failure: `API_INTERNAL_URL` pointed at a name with no service behind it, and every page logged "Could not load reference data" (404). The values were then set to the real `-5hn3` URLs.
- **Database and Redis are private-network only** (`ipAllowList: []`). The internal `postgresql://` URL works unchanged. `?sslmode=require` must not be added: asyncpg rejects it, and `?ssl=require` is the equivalent.
- **Migrations run in the API image's CMD** (`alembic upgrade head` before uvicorn), so the Docker Command must stay empty. Overriding it skipped migrations on the first attempt, and every database route returned 500.
- **A Render build without `API_INTERNAL_URL` now fails** instead of falling back to `localhost:8000`. The frontend image also passes the build-time value into the runtime stage.
- **Stray whitespace in settings is ignored.** A leading space pasted into the dashboard made Next.js reject every rewrite ("destination does not start with http"). `next.config.ts`, `server-api.ts` and the backend settings (`str_strip_whitespace`) now trim values.
- **The demo seed runs on start** when `SEED_DEMO_DATA=true`, which is the Blueprint default. It is idempotent, and a failure does not stop the API. A one-off Shell job was not needed. Turn it off once the site holds real data.
- **Seed photos survive the free plan's disk wipe.** `sync_listing_photos` now re-saves a demo photo whose file is missing, or whose URL predates the current `API_PUBLIC_URL`, as well as one whose caption changed.
- **The web container owns `.next`** (`COPY --chown=app:app`), so Next.js can write `.next/cache`. Before this, it logged `EACCES` on every request.
- **`frontend/public/` is git-ignored except listed files.** The rule keeps the user's original, partly watermarked photos out of the repo, so the logo and two hero images never reached Render. Each served file now has an exception. **Any new public asset needs one too.**
- **Hero images are pre-sized WebP served `unoptimized`.** On the free instance, `next/image` took 8–85 s to resize each multi-megabyte hero, so the carousel stayed blank, and its cache is lost on restart. `frontend/scripts/optimize-hero-images.mjs` writes copies to `public/hero/` (2.5 MB → 170 KB for `hero.png`) and leaves the originals untouched. Rerun it after changing a hero photo.
- **Free-plan limits accepted for the demo:** services sleep after about 15 minutes idle (the first request takes about a minute), uploads are lost on restart, and only one free Postgres is allowed per workspace.

## Not built (deliberately)

- Land-registry or title searches, AI document analysis, real payments or escrow, email/SMS delivery, ratings and reviews submission, agency team accounts. See ARCHITECTURE §15 for where each would plug in.
