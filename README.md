# PropCheck Nigeria

> **Verify the property and agent before you pay rent.**

PropCheck is an MVP web platform for renters in **Lagos, Rivers (Port Harcourt), Enugu, Anambra and Imo**. It has two independent checks:

- **Verified Agent** — a reviewer checks an agent's identity (and business registration where available).
- **Verified Property** — a reviewer checks a specific listing: the agent's authority to let it, the location, the photos and the full fee breakdown. Every report has a reference number, an expiry date and an explicit list of what was **not** checked.

Renters can search listings and agents, see **what is nearby** (markets, restaurants, churches, clubs) on every listing and at `/nearby`, book inspections, ask PropCheck to match them with a verified agent, report problems, and try a **test-mode** reservation flow (Paystack test keys or a built-in simulator; no real money, not escrow).

> PropCheck verifies the documents, identity information and inspection evidence listed in this report. It is not a substitute for a formal title search, legal advice or an official land-registry search. Users should verify payment terms before sending money.

## Stack

| Part | Tech |
|---|---|
| Frontend | Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS 4, React Hook Form + Zod, Leaflet/OpenStreetMap |
| Backend | FastAPI, SQLModel/SQLAlchemy 2, Alembic, PostgreSQL 16, psycopg 3, Argon2 |
| Tests | pytest (80 API tests) · Vitest + Testing Library (40 tests) · `backend/scripts/e2e_journey.py` |

Design and data model: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Endpoints: [docs/API.md](docs/API.md) · Hosting: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) · Decisions: [LOG.md](LOG.md) · Product notes: [RESEARCH.md](RESEARCH.md)

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
| `renter@propcheck.ng` | Renter | Book an inspection, reserve a verified property, ask for an agent |
| `agent@propcheck.ng` | Agent (verified) | Manage listings, confirm bookings, start a property verification |
| `landlord@propcheck.ng` | Landlord | Own listings managed by an agent |
| `reviewer@propcheck.ng` | Reviewer | Approve agents, run the property checklist, assign requests, decide reports, refunds |
| `admin@propcheck.ng` | Admin | Same console as reviewers |

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

## What is in the MVP

- Public: home, property search with filters (state, city, area, type, bedrooms, rent, verification status), property page with fee breakdown, verification report, "What is nearby?" map and list, inspection booking, share links; `/nearby` search by state/city/area or your location; agent directory and profiles; "help me find a house" requests; report a problem; how it works, pricing, about.
- Renter dashboard: requests, inspections, test reservations (pay, confirm keys, request refund), reports.
- Agent / landlord dashboard: profile and ID verification, listings, photos, private documents, verification cases, inspection slots and bookings, matched renters, reservations.
- Reviewer console: agent applications, property cases with checklist and document review, house-search matching, reports (with optional suspension), nearby-place reports, refunds, audit log.

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
- Known limits: the auth rate limiter is in-memory (one process). Use a shared store such as Redis before running several API replicas. Notifications only log to the console.

## Project layout

```
backend/   FastAPI app (app/), Alembic migrations, tests, scripts
frontend/  Next.js app (src/app routes, src/components, src/lib), Vitest tests
docs/      Architecture, API and deployment docs
```
