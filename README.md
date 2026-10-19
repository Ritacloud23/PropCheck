# PropCheck Nigeria

[![CI](https://github.com/Ritacloud23/PropCheck/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Ritacloud23/PropCheck/actions/workflows/ci.yml)

> **Verify the property and agent before you pay rent.**

**Live demo:** https://propcheck-web-5hn3.onrender.com (free hosting, so the first visit after a quiet spell takes about a minute). Log in with any [demo account](#demo-accounts).

PropCheck is an MVP web platform for renters in **Lagos, Rivers (Port Harcourt), Enugu, Anambra and Imo**. It has two independent checks:

- **Verified Agent** - a reviewer checks an agent's identity (and business registration where available).
- **Verified Property** - a reviewer checks a specific listing: the agent's authority to let it, the location, the photos and the full fee breakdown. Every report has a reference number, an expiry date and an explicit list of what was **not** checked.

Renters can search listings and agents, see **what is nearby** (markets, restaurants, churches, clubs) on every listing and at `/nearby`, book inspections, ask PropCheck to match them with a verified agent, report problems, and try a **test-mode** reservation flow (Paystack test keys or a built-in simulator; no real money, not escrow).

> PropCheck verifies the documents, identity information and inspection evidence listed in this report. It is not a substitute for a formal title search, legal advice or an official land-registry search. Users should verify payment terms before sending money.

## Stack

| Part | Tech |
|---|---|
| Frontend | Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS 4, React Hook Form + Zod, Leaflet/OpenStreetMap |
| Backend | FastAPI (async), SQLModel/SQLAlchemy 2 AsyncSession, Alembic, PostgreSQL 16, asyncpg, Argon2 |
| Tests | pytest (113 API tests) · Vitest + Testing Library (53 tests) · `backend/scripts/e2e_journey.py` |

Design and data model: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Endpoints: [docs/API.md](docs/API.md) · Hosting: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) · CI: [docs/CI.md](docs/CI.md) · Decisions: [LOG.md](LOG.md) · Product notes: [RESEARCH.md](RESEARCH.md)

## Quick start (Docker)

```bash
cp .env.example .env            # optional; defaults work for local use
docker compose up --build       # db :5434, api :8000, web :3000
docker compose exec api python -m app.seed
```

Open http://localhost:3000. API docs: http://localhost:8000/docs.

### Demo accounts

All seeded accounts use the password **`PropCheck2026`**.

| Email | Role | Try |
|---|---|---|
| `renter@propcheck.ng` | Renter | Book an inspection, reserve a verified property, ask for an agent. Has a released test reservation. |
| `renter2@propcheck.ng` | Renter | A refunded test reservation and a cancelled request |
| `renter3@propcheck.ng` | Renter | A confirmed inspection, an assigned request in Enugu, a reservation awaiting test payment |
| `renter4@propcheck.ng` | Renter | A reservation awaiting "keys received", a request the agent has already answered |
| `agent@propcheck.ng` | Agent (verified, Lagos) | Manage listings, confirm bookings, start a property verification |
| `agent3@propcheck.ng` | Agent (verified, Enugu/Anambra, phone private) | Has a newly assigned renter enquiry to answer |
| `agent4@propcheck.ng` | Agent (verified, Rivers) | Owns the rejected listing; has answered an enquiry |
| `agent6@propcheck.ng` | Agent (suspended) | Shows what suspension hides |
| `agent7@propcheck.ng` | Agent (application submitted, Imo) | Waiting in the reviewer's queue |
| `landlord@propcheck.ng` | Landlord | Own listings managed by an agent |
| `reviewer@propcheck.ng` · `reviewer2@propcheck.ng` | Reviewer | Approve agents, run the property checklist, assign requests, decide reports, refunds |
| `admin@propcheck.ng` | Admin | Same console as reviewers |

The seed covers every workflow state: 16 listings across the five launch states (10 verified, 5 awaiting review, 1 rejected), test reservations in all four states, requested and confirmed inspections, house-search requests (new, assigned, contacted, cancelled) and reports (open, resolved, rejected). Everything is fictional.

Reviewer and admin accounts cannot be self-registered.

## Local development (without Docker for the apps)

Requirements: Python 3.11+ with [uv](https://docs.astral.sh/uv/), Node.js 20.9+, and PostgreSQL (the compose `db` service is easiest: `docker compose up -d db`).

```bash
# Backend
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev                      # http://localhost:3000, proxies /api and /media to :8000
```

## Tests and checks

```bash
cd backend
uv run pytest                    # uses the propcheck_test database (created by the db container)
uv run ruff check . && uv run ruff format --check .
uv run python scripts/e2e_journey.py   # against a running, seeded stack

cd frontend
npm test                         # Vitest
npm run typecheck && npm run lint && npm run build
```

The backend tests migrate `propcheck_test` with Alembic once per run and wrap every test in a rolled-back transaction.

GitHub Actions runs these checks, plus `alembic upgrade head` and `alembic check` on a throwaway Postgres, on every push and pull request to `main`. The workflow only runs checks and never deploys. See [docs/CI.md](docs/CI.md) for the full list, how to read failed runs and how to handle CI variables.

## Deployment (Render)

`render.yaml` is a Render Blueprint that creates the whole stack: Postgres, Key Value (Redis, for rate limits), the API and the web app. In Render, choose **New → Blueprint**, pick this repo, and enter the public URLs it asks for. The API runs migrations on every start and, with `SEED_DEMO_DATA=true` (the default), loads the demo data. The full guide, including what each setting is for and the free plan's limits, is in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). The problems hit during the first deploy are in [LOG.md](LOG.md#deployment-on-render-2026-10-19).

Two rules for the frontend:

- `frontend/public/` is git-ignored except for listed files. A new image needs an exception in `frontend/.gitignore`, or it won't exist on the deployed site.
- The landing hero serves pre-sized copies from `public/hero/`. After changing a hero photo, run `node scripts/optimize-hero-images.mjs` in `frontend/` and commit the result.

## What is in the MVP

- Public: home, property search with filters (state, city, area, type, bedrooms, rent, verification status), property page with fee breakdown, verification report, "What is nearby?" map and list, inspection booking, share links; `/nearby` search by state/city/area or your location; agent directory and profiles; "help me find a house" requests; report a problem; how it works, pricing, about.
- Renter dashboard (`/dashboard/renter`): house-search requests with a detail page (`/house-search/[id]`), inspections, test reservations (pay, confirm keys, request refund), reports.
- Agent / landlord dashboard (`/dashboard/agent`): profile, verification (`/verification`: agent badge application plus property cases), listings, photos, private documents, inspection slots and bookings (`/inspection-slots`), matched renters (`/enquiries`), reservations.
- Reviewer console (`/dashboard/reviewer`): agent applications, property cases with checklist and document review, house-search matching, reports (with optional suspension), nearby-place reports, refunds, audit log (`/audit-log`).

The older paths `/dashboard/renter/requests`, `/dashboard/agent/bookings` and `/dashboard/reviewer/audit` redirect permanently to the new ones.

## Coverage

The MVP serves five states: **Lagos, Rivers (Port Harcourt), Enugu, Anambra and Imo**. Location levels are State → City → Area/neighbourhood, with each area's LGA. To add a state, add its cities and areas (with coordinates) to `backend/app/reference/__init__.py`, then list it in `ACTIVE_STATES`. No migration is needed.

Nearby places are fictional **demo data** seeded into PostgreSQL (`source = DEMO_SEED`, labelled "Demo data" in the UI) and are **not verified** by PropCheck. Lookups go through a provider interface (`app/services/nearby.py`), so an OpenStreetMap/Overpass provider can be added later without the app depending on a live API.

## Security notes

- Session JWT in an httpOnly, SameSite=Lax cookie (Secure in production). The frontend reaches the API through same-origin rewrites.
- Role and ownership checks live in the API's services; a reviewer can never decide a case or application they submitted or a property they manage.
- Private files (IDs, authority letters, report evidence) are stored outside the public directory and served only through 10-minute HMAC-signed links issued after an access check. Uploads are type-checked by magic bytes and size-limited.
- Agent phone/email appear publicly only with consent.
- Every status change runs through one state machine that locks the row, validates the transition and writes an audit entry in the same transaction.
- Paystack live keys are refused at startup.
- Rate limits protect login, registration, searches, house-search requests, reports, uploads and reservation/payment actions (HTTP 429 with `Retry-After`). See [docs/RATE_LIMITING.md](docs/RATE_LIMITING.md).
- Known limits: without `REDIS_URL` the rate limiter uses an in-memory development fallback (one process). Set `REDIS_URL` before running several API replicas. Notifications only log to the console.

## Known limitations

- **Verification is evidence-based, not a legal guarantee.** PropCheck does not search titles, surveys or land registries, and gives no legal opinion on ownership. Every report says what was and was not checked.
- **Reservations are a test/demo workflow.** No real money moves (Paystack test keys or the built-in simulator only). It is not escrow and not legally protected.
- **Reviewer work is manual**: agent matching, inspections and document review. Automatic matching is on the roadmap.
- **Notifications** (email/SMS) are an interface that only logs to the console.
- **Ratings and reviews** are seeded figures. Renters cannot submit reviews yet.
- **Rate limiting** shares its counters through Redis on Render. Without `REDIS_URL` (local development) it is in-memory and works for a single API process only.
- **The live demo runs on Render's free plan.** Services sleep when idle, and files uploaded there are lost on every restart. Demo photos are restored on start, but nothing else is. Real use needs a paid plan with a persistent disk or Cloudinary storage.
- **Coverage** is limited to Lagos, Rivers, Enugu, Anambra and Imo. FCT and northern states are deliberately out of the first release.
- **Nearby places** are fictional demo data and are not verified.

## Business model (proposed, nothing is charged in the MVP)

| Who | Item | Pilot |
|---|---|---|
| Renters | Browse properties and agents | Free |
| Renters | House-search request, inspection booking | Free during pilot |
| Renters | Reservation | Test/demo terms only |
| Agents and landlords | Agent profile and first verification | Free during pilot |
| Agents and landlords | Verified property | Proposed per-listing fee (to be set after the pilot) |
| Property managers | Professional plan | Coming soon |

Future revenue models to test: per-property verification fee, agent membership subscription, property-manager subscription, qualified-lead fee, premium agent placement, corporate relocation partnerships, maintenance-management subscription and a rent-collection service fee. No prices have been validated. See the open questions in [RESEARCH.md](RESEARCH.md).

## Roadmap

These features are **not** part of the MVP. Extension points are described in [ARCHITECTURE §15](docs/ARCHITECTURE.md).

**Phase 2: basic property management.** Rent reminders, tenant records, maintenance requests, payment receipts, a simple landlord dashboard.

**Phase 3: professional property management.** Full maintenance management, rent collection, landlord accounting, multi-property portfolios, agent permissions, contractor management, reports and analytics, advanced agent dashboards.

**Phase 4: advanced verification and expansion.** Official land-registry integrations where available, AI-assisted document analysis, expansion to more states, corporate relocation partnerships, diaspora renter services, agency team accounts, automated agent matching, better ratings and reviews.

AI document analysis, when it comes, will only **assist human reviewers**. It will never be presented as a replacement for lawyers or official verification.

## Project layout

```
backend/   FastAPI app (app/), Alembic migrations, tests, scripts
frontend/  Next.js app (src/app routes, src/components, src/lib), Vitest tests
docs/      Architecture, API and deployment docs
```
