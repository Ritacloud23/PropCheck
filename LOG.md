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

`python -m app.seed` creates 4 renters, 1 landlord, 2 reviewers, 1 admin and 7 agents (5 verified, 1 pending, 1 suspended); 16 listings across Lagos, Port Harcourt, Enugu, Awka/Onitsha and Owerri (10 verified, 5 awaiting review, 1 rejected with a failed check); inspection slots and bookings; test reservations in every state; house-search requests with agent enquiries; reports that are open, resolved and rejected; and about 330 fictional nearby places. Every status is reached through the real state machine, so the audit log looks like production data. Photos are generated PNG placeholders (no external downloads). Password for all accounts: `PropCheck2026`.

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

## Not built (deliberately)

- Land-registry or title searches, AI document analysis, real payments or escrow, email/SMS delivery, ratings and reviews submission, agency team accounts. See ARCHITECTURE §15 for where each would plug in.
