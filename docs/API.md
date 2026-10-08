# PropCheck API

Base path `/api`. JSON unless noted. Full, always-current schemas: **http://localhost:8000/docs** (OpenAPI).

**Auth:** session cookie `propcheck_session` (set by register/login), or `Authorization: Bearer <token>` (for scripts and tests).

**Errors:** `{"detail": "...", "code": "..."}`. Validation errors also include `errors: [{field, message}]`.

| Status | Meaning |
|---|---|
| 401 | Not logged in |
| 403 | Wrong role, or a guard failed (ownership, conflict of interest) |
| 404 | Not found **or not visible to you** (private records are never confirmed to outsiders) |
| 409 | Invalid or duplicate state transition, or a conflict (overlapping slot, slot already booked, already paid) |
| 422 | Validation failed |
| 429 | Rate limited (auth and report endpoints) |

Roles: R = renter, A = agent, L = landlord, S = staff (reviewer/admin), * = anyone (public).

## Auth

| Method | Path | Who | Notes |
|---|---|---|---|
| POST | `/auth/register` | * | `{full_name, email, password, phone?, role: RENTER\|AGENT\|LANDLORD}` |
| POST | `/auth/login` | * | `{email, password}` |
| POST | `/auth/logout` | * | Clears the cookie |
| GET | `/auth/me` | logged in | |

## Properties

| Method | Path | Who | Notes |
|---|---|---|---|
| GET | `/properties` | * | Filters: `q, state, city, area, lga, property_type, bedrooms (min), rent_min, rent_max, verification=any\|verified\|pending\|not_verified, verified_only, available_only, sort=newest\|rent_asc\|rent_desc, page, page_size`. Hides rejected listings and listings by suspended agents. |
| GET | `/properties/mine` | A, L | Owned or listed by me |
| POST | `/properties` | A, L | `total_move_in_cost` is always computed by the server |
| GET | `/properties/{id or slug}` | * | `documents` only for managers and staff |
| PATCH | `/properties/{id}` | owner / listing agent | Changing address, area, type, bedrooms, rent or fees after verification expires the verification |
| POST | `/properties/{id}/media` | manager | multipart `file` (JPG/PNG/WEBP, 5 MB), `caption?` |
| POST | `/properties/{id}/documents` | manager | multipart `file` (PDF/JPG/PNG/WEBP, 10 MB), `document_type`. Starts as `UPLOADED`. |
| GET | `/properties/{id or slug}/verification-report` | * | What was and was not checked, dates, limitations, timeline |
| GET | `/properties/{id or slug}/share` | * | Canonical URL and WhatsApp share link |
| POST | `/properties/{id}/report` | logged in | multipart `reason, description, evidence?` |

## Agents

| Method | Path | Who | Notes |
|---|---|---|---|
| GET | `/agents` | * | Filters: `state, city, lga, service, property_type, budget_min, budget_max, verified_only, q`. Hides draft, rejected and suspended agents. Contact fields are `null` without consent. |
| GET/POST/PATCH | `/agents/profile` | A, L | Own profile (private view includes contact details) |
| POST | `/agents/profile/photo` | A, L | multipart `file` |
| POST | `/agents/profile/verification` | A, L | multipart `identity_document`, `business_document?`, `evidence_notes?` → `SUBMITTED` |
| GET | `/agents/profile/verification` | A, L | Application history, with signed document links |
| GET | `/agents/{id}` | * | Public profile |
| GET | `/agents/{id}/properties` | * | Listings (each has its own verification badge) |
| POST | `/agents/{id}/report` | logged in | multipart `reason, description, evidence?` |

## Property verification cases

| Method | Path | Who | Notes |
|---|---|---|---|
| POST | `/properties/{id}/verification` | manager | Opens a `DRAFT` case (reference `PCV-YYYY-NNNNN`) with 8 checklist items. One open case per property. |
| GET | `/verification-cases` | A, L, S | Managers see their cases. Staff: `status`, `scope=all\|mine\|unassigned`. |
| GET | `/verification-cases/{id}` | manager, S | Includes `allowed_transitions` for your role |
| POST | `/verification-cases/{id}/submit` | manager | Needs ≥1 photo and ≥1 document |
| POST | `/verification-cases/{id}/transition` | S | `{to_status, reason?, reviewer_notes?, expires_at?, inspection_scheduled_for?, inspected_at?}`. `REJECTED` needs a reason. `VERIFIED` needs every check passed or not applicable, with the core checks passed. |
| POST | `/verification-cases/{id}/checks` | S | `{check_type, result, evidence_note?, document_id?}` (only while in review) |
| POST | `/verification-cases/{id}/documents/{doc_id}/review` | S | `{review_status: REVIEWED\|ACCEPTED\|REJECTED, reviewer_notes?}` |
| GET | `/verification-cases/{id}/audit-log` | manager, S | |

Transitions: `DRAFT→SUBMITTED→IN_REVIEW→(INSPECTION_BOOKED→)VERIFIED|REJECTED`, `VERIFIED→EXPIRED`.

## Inspections

| Method | Path | Who | Notes |
|---|---|---|---|
| GET | `/properties/{id}/inspection-slots` | * | Public: upcoming open slots. Managers: all slots. |
| POST | `/properties/{id}/inspection-slots` | manager | `{start_time, end_time}` in the future, ≤ 4 h. Overlaps → 409 (also enforced by a database exclusion constraint). |
| POST | `/inspection-slots/{id}/cancel` | manager | Only if no active booking |
| POST | `/inspection-bookings` | R | `{slot_id, renter_note?}`. A slot holds one live booking (row lock + partial unique index). |
| GET | `/inspection-bookings` | R, A, L, S | Scoped to your own bookings or properties |
| GET | `/inspection-bookings/{id}` | involved, S | |
| POST | `/inspection-bookings/{id}/confirm` · `/decline` (reason) · `/complete` · `/cancel` | manager / renter | |

## House-search requests

| Method | Path | Who | Notes |
|---|---|---|---|
| POST | `/house-search-requests` | R | `consent_to_share` must be true. Max 3 open requests. |
| GET | `/house-search-requests` | R (own), A (assigned), S (all) | `status`, `state` filters |
| GET | `/house-search-requests/{id}` | owner, assigned agent, S | The assigned agent's contact is revealed to the renter |
| GET | `/house-search-requests/{id}/candidate-agents` | S | Verified agents covering the state, ranked |
| POST | `/house-search-requests/{id}/matching` | S | |
| POST | `/house-search-requests/{id}/assign` | S | `{agent_id, note?}`. The agent must be currently verified. |
| POST | `/house-search-requests/{id}/respond` | assigned A | `{message}`. `ASSIGNED` moves to `CONTACTED`. |
| POST | `/house-search-requests/{id}/contacted` · `/complete` · `/cancel` | per state machine | |
| GET | `/agent/enquiries` | A | Only requests assigned to me |

## Reservations (TEST MODE — not escrow)

| Method | Path | Who | Notes |
|---|---|---|---|
| GET | `/reservations/terms?property_id=` | * | Terms, provider, exact amount for a listing |
| POST | `/reservations` | R | `{property_id, accept_terms: true}`. The property must be currently verified and available. |
| GET | `/reservations`, `/reservations/{id}` | R, A, L, S | Scoped |
| POST | `/reservations/{id}/pay` | owning R | Simulated: confirms at once. Paystack test: returns `authorization_url`. Second pay → 409. |
| POST | `/reservations/{id}/verify-payment` | owning R | `{reference}` after Paystack checkout |
| POST | `/reservations/{id}/confirm-keys` | owning R | `PENDING_RELEASE→RELEASED`, once |
| POST | `/reservations/{id}/request-refund` | owning R | `{reason}`; a reviewer decides |
| POST | `/reservations/{id}/refund` | S | `{reason}`. `PENDING_RELEASE→REFUNDED`, once. Released reservations cannot be refunded. |
| POST | `/reservations/{id}/cancel` | owning R, S | Only before payment |

## Reviewer console

| Method | Path | Notes |
|---|---|---|
| GET | `/reviewer/summary` | Queue counts |
| GET | `/reviewer/agents?status=` | Default: SUBMITTED + IN_REVIEW |
| GET | `/reviewer/agents/{id}` | With signed document links and `allowed_actions` |
| POST | `/reviewer/agents/{id}/{start-review\|approve\|reject\|suspend\|expire\|reinstate}` | `{reason?, reviewer_notes?, expires_at?}`. Reject and suspend need a reason. |
| GET | `/reviewer/reports?status=`, `/reviewer/reports/{id}` | |
| POST | `/reviewer/reports/{id}/start-review` | |
| POST | `/reviewer/reports/{id}/{resolve\|reject}` | `{reason, reviewer_notes?, suspend_agent?}`. Suspension happens in the same transaction. |
| GET | `/reviewer/audit-log` | `entity_type, entity_id, action, limit` |

## Nearby places

| Method | Path | Who | Notes |
|---|---|---|---|
| GET | `/nearby-places` | * | `latitude`, `longitude` (required), `category=MARKET\|RESTAURANT\|CHURCH\|CLUB`, `radius_km` (default 3, max 10), `limit` (≤ 50). Returns `{items, count, center, radius_km, category, notice}`, nearest first. Each item has `distance_km`, `distance_m`, `distance_label`, `is_demo_data`. An invalid category or radius gives 422; nothing nearby gives `items: []`. |
| POST | `/nearby-places/{id}/report` | logged in | `{reason: WRONG_LOCATION\|PERMANENTLY_CLOSED\|WRONG_OPENING_HOURS\|WRONG_PHONE_NUMBER\|WRONG_NAME_OR_CATEGORY\|DUPLICATE\|OTHER, description?}`. One open report per user and place (409). |
| GET | `/reviewer/place-reports?status=OPEN` | S | |
| POST | `/reviewer/place-reports/{id}/{resolve\|reject}` | S | `{reason, reviewer_notes?, deactivate_place?}` |

## Other

| Method | Path | Notes |
|---|---|---|
| GET | `/reports/mine` | Reports I filed |
| GET | `/files/{token}` | Private file download. Tokens are HMAC-signed and expire after 10 minutes. |
| GET | `/reference` | Active states (Lagos, Rivers, Enugu, Anambra, Imo), `locations` hierarchy (state → cities, major first → areas with LGA and coordinates), enums, notices |
| GET | `/health` | Liveness |
| GET | `/media/...` | Public photos (not under `/api`) |
