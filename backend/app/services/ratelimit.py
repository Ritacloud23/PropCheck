"""Rate limiting for abuse-prone API endpoints.

Rules are named and configured in settings (`RATE_LIMIT_<RULE>`, e.g. "5/minute"); see
docs/RATE_LIMITING.md. Each rule counts hits per identity (client IP, user id, or IP + account)
in a fixed time window. Over the limit -> HTTP 429 with a Retry-After header.

Storage backends:
* `RedisBackend` when REDIS_URL is set. Required in production with more than one API process,
  because every process must see the same counters.
* `MemoryBackend` otherwise. DEVELOPMENT FALLBACK ONLY: counters live in this one process, are lost
  on restart, and are not shared between replicas. A warning is logged when it is selected.

Only API endpoints opt in (via `limit()` / `enforce()`). Static media, private file downloads,
reference data and health checks are never limited.
"""

import hashlib
import ipaddress
import logging
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, Protocol

from fastapi import Request

from app.config import settings
from app.deps import OptionalUser
from app.errors import TooManyRequests
from app.rates import Rate, parse_rate

log = logging.getLogger("propcheck.ratelimit")


@dataclass(frozen=True)
class Rule:
    setting: str  # settings attribute holding the rate string
    what: str  # used in the 429 message: "Too many <what>."

    @property
    def rate(self) -> Rate:
        return parse_rate(getattr(settings, self.setting))


RULES: dict[str, Rule] = {
    "login": Rule("rate_limit_login", "login attempts for this account"),
    "login_ip": Rule("rate_limit_login_ip", "login attempts from your network"),
    "register": Rule("rate_limit_register", "accounts created from your network"),
    "password_reset": Rule("rate_limit_password_reset", "password reset requests"),
    "property_search": Rule("rate_limit_property_search", "property searches"),
    "nearby_search": Rule("rate_limit_nearby_search", "nearby-place searches"),
    "house_search": Rule("rate_limit_house_search", "house-search requests"),
    "reports": Rule("rate_limit_reports", "reports"),
    "uploads": Rule("rate_limit_uploads", "file uploads"),
    "reservations": Rule("rate_limit_reservations", "reservation and payment actions"),
}


# ---------------------------------------------------------------- storage backends


class Backend(Protocol):
    async def hit(self, key: str, rate: Rate) -> int | None:
        """Count one hit. Returns None if allowed, else seconds until the window resets."""
        ...


def _window(rate: Rate, now: float) -> tuple[int, int]:
    """(window index, seconds until the window ends, at least 1)."""
    index = int(now // rate.window_seconds)
    remaining = math.ceil((index + 1) * rate.window_seconds - now)
    return index, max(1, remaining)


class MemoryBackend:
    """DEVELOPMENT FALLBACK. Single-process, non-persistent. Replace with Redis for production.

    Fine on one event loop without locks: `hit()` never awaits, so each call runs atomically.
    """

    MAX_KEYS = 50_000  # expired counters are purged once the table grows past this

    def __init__(self, clock: Callable[[], float] = time.time):
        self._clock = clock
        self._counts: dict[str, tuple[int, int]] = {}  # key -> (window index, count)

    async def hit(self, key: str, rate: Rate) -> int | None:
        now = self._clock()
        index, retry_after = _window(rate, now)
        bucket = f"{key}:{rate.window_seconds}"
        prev_index, count = self._counts.get(bucket, (index, 0))
        count = count + 1 if prev_index == index else 1
        self._counts[bucket] = (index, count)
        if len(self._counts) > self.MAX_KEYS:
            self._purge(now)
        return retry_after if count > rate.limit else None

    def _purge(self, now: float) -> None:
        for bucket, (index, _) in list(self._counts.items()):
            window = int(bucket.rsplit(":", 1)[1])
            if index < int(now // window):
                del self._counts[bucket]

    def reset(self) -> None:
        self._counts.clear()


class RedisBackend:
    """Shared counters in Redis: one key per identity and window, expiring with the window."""

    def __init__(self, client: Any, clock: Callable[[], float] = time.time, prefix: str = "propcheck:rl"):
        self._redis = client
        self._clock = clock
        self._prefix = prefix

    async def hit(self, key: str, rate: Rate) -> int | None:
        index, retry_after = _window(rate, self._clock())
        redis_key = f"{self._prefix}:{key}:{rate.window_seconds}:{index}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, rate.window_seconds + 1)
            count, _ = await pipe.execute()
        return retry_after if int(count) > rate.limit else None


_backend: Backend | None = None


def get_backend() -> Backend:
    global _backend
    if _backend is None:
        if settings.redis_url:
            import redis.asyncio as redis

            _backend = RedisBackend(redis.from_url(settings.redis_url))
            log.info("Rate limiting: using Redis.")
        else:
            _backend = MemoryBackend()
            log.warning(
                "Rate limiting: REDIS_URL is not set, using the in-memory DEVELOPMENT fallback. "
                "Counters are per process and reset on restart; set REDIS_URL in production."
            )
    return _backend


def set_backend(backend: Backend | None) -> None:
    """Swap the backend (tests). None means 'choose from settings again on next use'."""
    global _backend
    _backend = backend


def reset() -> None:
    """Clear in-memory counters (tests / local development)."""
    if isinstance(_backend, MemoryBackend):
        _backend.reset()


# ---------------------------------------------------------------- client identity


@lru_cache
def _trusted_networks(value: str) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return tuple(ipaddress.ip_network(v.strip(), strict=False) for v in value.split(",") if v.strip())


def _is_trusted(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in net for net in _trusted_networks(settings.trusted_proxies))


def client_ip(request: Request) -> str:
    """The visitor's IP address.

    X-Forwarded-For is only believed when the direct peer is a trusted proxy (TRUSTED_PROXIES,
    e.g. the Next.js server). We then take the right-most address that is not itself a trusted
    proxy: entries further left were supplied by the client and could be forged.
    """
    peer = request.client.host if request.client else "unknown"
    if not _is_trusted(peer):
        return peer
    chain = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    for address in reversed(chain):
        try:
            ipaddress.ip_address(address)
        except ValueError:
            break  # malformed hop: do not trust anything to its left
        if not _is_trusted(address):
            return address
    return peer


def account_key(identifier: str) -> str:
    """Stable, non-reversible key for an account identifier (no email addresses in Redis keys)."""
    return hashlib.sha256(identifier.strip().lower().encode()).hexdigest()[:32]


# ---------------------------------------------------------------- enforcement


async def enforce(rule_name: str, identity: str) -> None:
    """Count a hit for `identity` under `rule_name`; raise HTTP 429 when over the limit."""
    if not settings.rate_limit_enabled:
        return
    rule = RULES[rule_name]
    try:
        retry_after = await get_backend().hit(f"{rule_name}:{identity}", rule.rate)
    except Exception:
        # Fail open: a storage outage must not take logins and searches down with it.
        log.exception("Rate limiting unavailable for rule %s; allowing the request.", rule_name)
        return
    if retry_after is not None:
        raise TooManyRequests(
            f"Too many {rule.what}. Please wait {_human(retry_after)} and try again.",
            retry_after=retry_after,
        )


def _human(seconds: int) -> str:
    if seconds < 90:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    minutes = math.ceil(seconds / 60)
    return f"{minutes} minutes"


Identity = Literal["ip", "user"]


def limit(rule_name: str, *, by: Identity, scope: str | None = None) -> Callable[..., Awaitable[None]]:
    """Route dependency. by="ip": per client IP. by="user": per signed-in user, falling back to the
    client IP for anonymous requests (those are then refused by the route's own auth check).
    `scope` gives an endpoint its own counter while reusing a rule's rate."""
    if rule_name not in RULES:
        raise KeyError(rule_name)
    prefix = f"{scope}:" if scope else ""

    async def per_ip(request: Request) -> None:
        await enforce(rule_name, f"{prefix}ip:{client_ip(request)}")

    async def per_user(request: Request, user: OptionalUser) -> None:
        identity = f"user:{user.id}" if user is not None else f"ip:{client_ip(request)}"
        await enforce(rule_name, prefix + identity)

    return per_user if by == "user" else per_ip
