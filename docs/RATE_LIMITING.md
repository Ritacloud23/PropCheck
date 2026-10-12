# Rate limiting

The API limits how often abuse-prone endpoints can be called. Code: `backend/app/services/ratelimit.py`.
Tests: `backend/tests/test_rate_limits.py`.

## Limits

Every rate is a setting (environment variable) in the form `<count>/<second|minute|hour|day>`,
for example `5/minute`, `20/hour` or `10/15 minutes`. The API refuses to start if a rate is malformed.

| Rule | Endpoints | Default | Counted per | Setting |
|---|---|---|---|---|
| `login` | `POST /api/auth/login` | 5/minute | IP address + account (email, hashed) | `RATE_LIMIT_LOGIN` |
| `login_ip` | `POST /api/auth/login` | 30/minute | IP address, across all accounts | `RATE_LIMIT_LOGIN_IP` |
| `register` | `POST /api/auth/register` | 5/hour | IP address | `RATE_LIMIT_REGISTER` |
| `password_reset` | none yet (see below) | 3/hour | IP address + account | `RATE_LIMIT_PASSWORD_RESET` |
| `property_search` | `GET /api/properties` | 60/minute | IP address | `RATE_LIMIT_PROPERTY_SEARCH` |
| `nearby_search` | `GET /api/nearby-places` | 60/minute | IP address | `RATE_LIMIT_NEARBY_SEARCH` |
| `house_search` | `POST /api/house-search-requests` | 5/hour | signed-in user | `RATE_LIMIT_HOUSE_SEARCH` |
| `reports` | `POST /api/agents/{id}/report`, `POST /api/properties/{id}/report` (shared); `POST /api/nearby-places/{id}/report` (own counter) | 5/hour | signed-in user | `RATE_LIMIT_REPORTS` |
| `uploads` | property photos and documents, agent photo, agent verification evidence | 20/hour | signed-in user | `RATE_LIMIT_UPLOADS` |
| `reservations` | every `POST` under `/api/reservations` (create, pay, verify payment, confirm keys, request refund, refund, cancel) | 10/minute | signed-in user | `RATE_LIMIT_RESERVATIONS` |

Notes:

* **Login** counts every attempt, before the password is checked. The `login` rule stops guessing
  one account's password. People sharing an IP address (offices, campus Wi-Fi, mobile carrier NAT)
  still have their own per-account allowance, and the real owner can sign in from another network.
  The looser `login_ip` rule stops one address from trying a few passwords on many accounts
  (password spraying).
* **Account identifiers** are normalised (trimmed, lower-case) and hashed before use as a key, so
  email addresses never appear in Redis.
* **User-based rules** follow the signed-in user, not the IP: changing networks does not reset them,
  and several users behind one IP do not share an allowance. An anonymous call to these endpoints
  falls back to the IP and is then refused by the endpoint's own login check.
* **Password reset**: PropCheck has no password-reset endpoint yet. The rule is defined so that the
  endpoint, when added, uses it per IP and per account:
  `await ratelimit.enforce("password_reset", f"ip:{ip}:account:{ratelimit.account_key(email)}")`.
* **Not limited**: public media (`/media/...`), private file downloads (`/api/files/...`), reference
  data, health checks, property and agent detail pages, and dashboards. HTML pages and static assets are
  served by Next.js and never reach this limiter.

## Response when a limit is hit

HTTP **429 Too Many Requests**, a `Retry-After` header (seconds) and a JSON body in the API's usual
error shape, which the frontend shows as-is:

```json
{
  "detail": "Too many login attempts for this account. Please wait 42 seconds and try again.",
  "code": "rate_limited",
  "retry_after": 42
}
```

Limits use fixed windows (for example, each clock minute). A client can therefore make up to twice the
limit across a window boundary. That is acceptable for an MVP and keeps the Redis cost to one
counter per window.

## Storage: Redis, or a development fallback

| Setting | Default | Meaning |
|---|---|---|
| `REDIS_URL` | empty | e.g. `redis://redis:6379/0`. When set, counters live in Redis and are shared by all API processes. |
| `RATE_LIMIT_ENABLED` | `true` | Set `false` to switch every limit off (for example, for a load test). |

Without `REDIS_URL`, the API uses an in-memory **development fallback** (`MemoryBackend`) and logs a
warning at the first limited request. Its counters live inside one process and reset on every restart.
With several API instances (multi-instance or multi-worker deployments), each one counts on its own,
so the real limit becomes N times the configured one. **Set `REDIS_URL` before running more than one
API instance in production.** The repository does not include a Redis service yet. Add one (or a managed
Redis) when you scale out.

If Redis becomes unreachable, the limiter **fails open**: requests are allowed and an error is logged.
An outage of the counter store therefore never locks users out of login or search.

## Client IP addresses behind proxies

Visitors normally reach the API through the Next.js server (server-rendered pages and the `/api`
rewrite), so the API's direct peer is the web server, not the visitor.

| Setting | Default | Meaning |
|---|---|---|
| `TRUSTED_PROXIES` | `127.0.0.1,::1` | Comma-separated IPs or CIDR ranges whose `X-Forwarded-For` header is believed. |

* The `X-Forwarded-For` header is only read when the direct peer is in `TRUSTED_PROXIES`. The API then
  uses the **right-most address that is not a trusted proxy**. Addresses further left were sent by
  the client and could be forged. A visitor calling the API directly cannot choose their own IP.
* Server-rendered pages forward the visitor's address (`frontend/src/lib/server-api.ts`).
* The Next.js `/api` rewrite passes `X-Forwarded-For` through unchanged and does not add the visitor's
  address. In production, run the web app behind a load balancer or platform that appends the client
  address to `X-Forwarded-For` (Render, Railway, Fly, Vercel, nginx and Caddy all do). Without one,
  browser API calls all appear to come from the web server's address. They then share one per-IP
  allowance, and a visitor could send a fake `X-Forwarded-For`.
* List only your real proxies in `TRUSTED_PROXIES`. `docker-compose.yml` trusts Docker's private
  ranges so the local stack works. Do not copy that into production.
