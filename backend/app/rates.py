"""Rate strings such as "5/minute". No app imports, so settings can validate rates at startup."""

from dataclasses import dataclass
from functools import lru_cache

_UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


@dataclass(frozen=True)
class Rate:
    limit: int
    window_seconds: int


@lru_cache
def parse_rate(value: str) -> Rate:
    """'5/minute' -> Rate(5, 60). Also accepts plurals ('20/hours') and a count ('10/15 minutes')."""
    count, _, period = value.strip().lower().partition("/")
    parts = period.split()
    if (
        not count.strip().isdigit()
        or not parts
        or len(parts) > 2
        or (len(parts) == 2 and not parts[0].isdigit())
    ):
        raise ValueError(f"Invalid rate {value!r}; expected e.g. '5/minute' or '20/hour'.")
    multiplier = int(parts[0]) if len(parts) == 2 else 1
    unit = parts[-1].removesuffix("s")
    if unit not in _UNITS or multiplier < 1:
        raise ValueError(f"Invalid rate unit in {value!r}; use second, minute, hour or day.")
    return Rate(int(count), multiplier * _UNITS[unit])
