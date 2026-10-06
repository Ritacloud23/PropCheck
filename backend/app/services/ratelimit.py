"""Basic in-memory fixed-window rate limiter for auth endpoints.

Fine for a single API process. For multiple replicas, replace with a Redis-backed limiter
(documented in README "Security considerations").
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import Request

from app.config import settings
from app.errors import TooManyRequests

_hits: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def reset() -> None:
    with _lock:
        _hits.clear()


def auth_rate_limit(request: Request) -> None:
    limit = settings.auth_rate_limit_per_minute
    if limit <= 0:
        return
    ip = request.client.host if request.client else "unknown"
    key = f"{ip}:{request.url.path}"
    now = time.monotonic()
    with _lock:
        window = [t for t in _hits[key] if now - t < 60]
        if len(window) >= limit:
            _hits[key] = window
            raise TooManyRequests("Too many attempts. Please wait a minute and try again.")
        window.append(now)
        _hits[key] = window
