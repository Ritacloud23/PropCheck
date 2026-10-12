"""Rate limiting: limits, identities (IP, IP + account, user), 429 responses and documentation.

The in-process ASGI client connects from 127.0.0.1, a trusted proxy by default, so tests pick the
"visitor" IP with X-Forwarded-For, the way the Next.js server forwards it.
"""

import pathlib

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, settings
from app.main import app
from app.models.enums import Role
from app.rates import Rate, parse_rate
from app.services import ratelimit
from app.services.ratelimit import RULES, MemoryBackend, RedisBackend, client_ip
from tests.helpers import PNG, create_agent, create_property, make_user
from tests.test_house_search_reports import REQUEST

REPO = pathlib.Path(__file__).resolve().parents[2]


def ip(address: str) -> dict:
    return {"X-Forwarded-For": address}


def register_payload(n: int) -> dict:
    return {"full_name": "Rate Tester", "email": f"rate{n}@example.com", "password": "secret123"}


def assert_rate_limited(r, *, mentions: str) -> int:
    assert r.status_code == 429, r.text
    body = r.json()
    assert body["code"] == "rate_limited"
    assert mentions in body["detail"] and "try again" in body["detail"]
    retry_after = int(r.headers["Retry-After"])
    assert retry_after >= 1 and body["retry_after"] == retry_after
    return retry_after


# ---------------------------------------------------------------- per-IP limits


async def test_registration_allows_five_per_hour_per_ip(client):
    for n in range(5):  # below and at the limit: all succeed
        r = await client.post("/api/auth/register", json=register_payload(n), headers=ip("198.51.100.7"))
        assert r.status_code == 201, r.text
    r = await client.post("/api/auth/register", json=register_payload(5), headers=ip("198.51.100.7"))
    assert assert_rate_limited(r, mentions="accounts created") <= 3600
    # A different visitor is unaffected.
    r = await client.post("/api/auth/register", json=register_payload(6), headers=ip("198.51.100.8"))
    assert r.status_code == 201


async def test_property_search_allows_sixty_per_minute_per_ip(client):
    for _ in range(60):
        assert (await client.get("/api/properties", headers=ip("198.51.100.20"))).status_code == 200
    r = await client.get("/api/properties", headers=ip("198.51.100.20"))
    assert assert_rate_limited(r, mentions="property searches") <= 60
    assert (await client.get("/api/properties", headers=ip("198.51.100.21"))).status_code == 200


async def test_nearby_search_is_limited_per_ip(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_nearby_search", "3/minute")
    params = {"latitude": 6.45, "longitude": 3.47}
    for _ in range(3):
        r = await client.get("/api/nearby-places", params=params, headers=ip("198.51.100.30"))
        assert r.status_code == 200
    r = await client.get("/api/nearby-places", params=params, headers=ip("198.51.100.30"))
    assert_rate_limited(r, mentions="nearby-place searches")


async def test_static_reference_and_detail_pages_are_not_limited(client, session, monkeypatch):
    for setting in ("rate_limit_property_search", "rate_limit_nearby_search"):
        monkeypatch.setattr(settings, setting, "1/minute")
    _, agent, _ = await create_agent(client, session)
    prop = await create_property(client, agent)
    for _ in range(5):
        assert (await client.get("/api/reference")).status_code == 200
        assert (await client.get("/api/health")).status_code == 200
        assert (await client.get(f"/api/properties/{prop['public_slug']}")).status_code == 200
        assert (await client.get("/media/does-not-exist.jpg")).status_code == 404  # static mount, never 429


# ---------------------------------------------------------------- login: IP + account identifier


async def test_login_limit_uses_ip_and_account(client, session):
    user, _ = await make_user(session, Role.RENTER)
    other, _ = await make_user(session, Role.RENTER)
    wrong = {"email": user.email, "password": "not-the-password"}
    right = {"email": user.email, "password": "Password123"}

    for _ in range(5):
        r = await client.post("/api/auth/login", json=wrong, headers=ip("203.0.113.1"))
        assert r.status_code == 401
    # Attempts are counted before the password check: even the right password is refused now.
    r = await client.post("/api/auth/login", json=right, headers=ip("203.0.113.1"))
    assert_rate_limited(r, mentions="login attempts for this account")
    # The account identifier is normalised, so changing the case does not reset the counter.
    r = await client.post(
        "/api/auth/login", json={**right, "email": user.email.upper()}, headers=ip("203.0.113.1")
    )
    assert r.status_code == 429

    # Same IP, different account: separate counter (shared networks / CGNAT keep working).
    r = await client.post(
        "/api/auth/login", json={"email": other.email, "password": "Password123"}, headers=ip("203.0.113.1")
    )
    assert r.status_code == 200, r.text
    # Same account from another IP: separate counter, so the real owner can still sign in.
    r = await client.post("/api/auth/login", json=right, headers=ip("203.0.113.2"))
    assert r.status_code == 200, r.text


async def test_login_ip_limit_stops_password_spraying(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_login_ip", "3/minute")
    for n in range(3):
        r = await client.post(
            "/api/auth/login",
            json={"email": f"victim{n}@example.com", "password": "guess123"},
            headers=ip("203.0.113.9"),
        )
        assert r.status_code == 401
    r = await client.post(
        "/api/auth/login",
        json={"email": "victim9@example.com", "password": "guess123"},
        headers=ip("203.0.113.9"),
    )
    assert_rate_limited(r, mentions="from your network")


# ---------------------------------------------------------------- authenticated writes: user identity


async def test_uploads_are_limited_per_user_not_per_ip(client, session, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_uploads", "2/hour")
    _, agent_a, _ = await create_agent(client, session)
    _, agent_b, _ = await create_agent(client, session)
    prop_a = await create_property(client, agent_a)
    prop_b = await create_property(client, agent_b)

    def upload(prop, headers, address):
        return client.post(
            f"/api/properties/{prop['id']}/media",
            files={"file": ("p.png", PNG, "image/png")},
            headers={**headers, **ip(address)},
        )

    assert (await upload(prop_a, agent_a, "198.51.100.40")).status_code == 201
    assert (await upload(prop_a, agent_a, "198.51.100.40")).status_code == 201
    assert_rate_limited(await upload(prop_a, agent_a, "198.51.100.40"), mentions="file uploads")
    # Changing IP does not help: the counter follows the signed-in user.
    assert (await upload(prop_a, agent_a, "198.51.100.99")).status_code == 429
    # Another user on the same IP has their own allowance.
    assert (await upload(prop_b, agent_b, "198.51.100.40")).status_code == 201


async def test_reservation_actions_allow_ten_per_minute_per_user(client, session):
    _, renter_a = await make_user(session, Role.RENTER)
    _, renter_b = await make_user(session, Role.RENTER)
    for _ in range(10):  # the limit counts every action, even ones that then fail
        assert (await client.post("/api/reservations/999999/cancel", headers=renter_a)).status_code == 404
    r = await client.post("/api/reservations/999999/pay", headers=renter_a)  # shared across actions
    assert_rate_limited(r, mentions="reservation and payment actions")
    assert (await client.post("/api/reservations/999999/cancel", headers=renter_b)).status_code == 404


async def test_house_search_requests_are_limited_per_user(client, session, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_house_search", "2/hour")
    _, renter = await make_user(session, Role.RENTER)
    _, other = await make_user(session, Role.RENTER)
    for _ in range(2):
        assert (
            await client.post("/api/house-search-requests", json=REQUEST, headers=renter)
        ).status_code == 201
    r = await client.post("/api/house-search-requests", json=REQUEST, headers=renter)
    assert_rate_limited(r, mentions="house-search requests")
    assert (await client.post("/api/house-search-requests", json=REQUEST, headers=other)).status_code == 201


async def test_reports_allow_five_per_hour_per_user(client, session):
    _, renter = await make_user(session, Role.RENTER)
    _, agent, profile = await create_agent(client, session)
    prop = await create_property(client, agent)
    form = {"reason": "PAYMENT_PRESSURE", "description": "Asked me to pay before inspection."}
    for n in range(5):  # agent and property reports share one allowance
        url = f"/api/agents/{profile['id']}/report" if n % 2 else f"/api/properties/{prop['id']}/report"
        assert (await client.post(url, data=form, headers=renter)).status_code == 201
    r = await client.post(f"/api/agents/{profile['id']}/report", data=form, headers=renter)
    assert_rate_limited(r, mentions="reports")
    # Nearby-place reports reuse the rate with their own counter (unknown place -> 404, not 429).
    r = await client.post(
        "/api/nearby-places/999999/report", json={"reason": "WRONG_OPENING_HOURS"}, headers=renter
    )
    assert r.status_code == 404


# ---------------------------------------------------------------- client IP, backends, failure mode


async def test_forwarded_for_ignored_from_untrusted_peers(client, monkeypatch):
    """A visitor talking to the API directly cannot pick a new IP per request to dodge limits."""
    monkeypatch.setattr(settings, "rate_limit_register", "1/hour")
    transport = ASGITransport(app=app, client=("203.0.113.50", 40000))
    async with AsyncClient(transport=transport, base_url="http://testserver") as direct:
        r = await direct.post("/api/auth/register", json=register_payload(100), headers=ip("192.0.2.1"))
        assert r.status_code == 201
        r = await direct.post("/api/auth/register", json=register_payload(101), headers=ip("192.0.2.2"))
        assert r.status_code == 429


def test_client_ip_takes_rightmost_untrusted_hop():
    class Req:
        def __init__(self, peer, xff=None):
            self.client = type("C", (), {"host": peer})()
            self.headers = {"x-forwarded-for": xff} if xff else {}

    assert (
        client_ip(Req("127.0.0.1", "6.6.6.6, 198.51.100.5, 127.0.0.1")) == "198.51.100.5"
    )  # left part forgeable
    assert client_ip(Req("127.0.0.1")) == "127.0.0.1"
    assert client_ip(Req("127.0.0.1", "not-an-ip")) == "127.0.0.1"
    assert client_ip(Req("198.51.100.9", "1.2.3.4")) == "198.51.100.9"  # untrusted peer: header ignored


async def test_memory_backend_window_resets():
    now = [1000.0]
    backend = MemoryBackend(clock=lambda: now[0])
    rate = Rate(2, 60)
    assert await backend.hit("k", rate) is None
    assert await backend.hit("k", rate) is None
    assert await backend.hit("k", rate) == 20  # window 960-1020 ends in 20 s
    assert await backend.hit("other", rate) is None
    now[0] = 1020.0  # next window
    assert await backend.hit("k", rate) is None


class FakeRedis:
    """Just enough of redis.asyncio for RedisBackend: a transactional pipeline of INCR + EXPIRE."""

    def __init__(self):
        self.values: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def pipeline(self, transaction=True):
        fake = self

        class Pipe:
            def __init__(self):
                self.ops = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            def incr(self, key):
                self.ops.append(("incr", key))

            def expire(self, key, seconds):
                self.ops.append(("expire", key, seconds))

            async def execute(self):
                out = []
                for op in self.ops:
                    if op[0] == "incr":
                        fake.values[op[1]] = fake.values.get(op[1], 0) + 1
                        out.append(fake.values[op[1]])
                    else:
                        fake.ttls[op[1]] = op[2]
                        out.append(True)
                return out

        return Pipe()


async def test_redis_backend_counts_in_shared_expiring_keys():
    redis = FakeRedis()
    now = [3600.0 * 10 + 5]
    backend = RedisBackend(redis, clock=lambda: now[0])
    rate = Rate(2, 3600)
    key = f"login:ip:1.2.3.4:account:{ratelimit.account_key('Ada@Example.com')}"
    assert await backend.hit(key, rate) is None
    assert await backend.hit(key, rate) is None
    assert await backend.hit(key, rate) == 3595
    (stored,) = redis.values
    assert stored.startswith("propcheck:rl:login:") and "@" not in stored  # no email addresses in Redis
    assert redis.ttls[stored] == 3601
    now[0] += 3600
    assert await backend.hit(key, rate) is None  # new window, new key


async def test_storage_outage_fails_open(client):
    class Broken:
        async def hit(self, key, rate):
            raise ConnectionError("redis down")

    ratelimit.set_backend(Broken())
    try:
        r = await client.post("/api/auth/register", json=register_payload(200))
        assert r.status_code == 201
    finally:
        ratelimit.set_backend(None)


async def test_disabled_flag_turns_limits_off(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_property_search", "1/minute")
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    for _ in range(3):
        assert (await client.get("/api/properties")).status_code == 200


# ---------------------------------------------------------------- configuration & documentation


def test_defaults_match_the_agreed_limits():
    expected = {
        "login": Rate(5, 60),
        "register": Rate(5, 3600),
        "password_reset": Rate(3, 3600),
        "property_search": Rate(60, 60),
        "nearby_search": Rate(60, 60),
        "house_search": Rate(5, 3600),
        "reports": Rate(5, 3600),
        "uploads": Rate(20, 3600),
        "reservations": Rate(10, 60),
    }
    for name, rate in expected.items():
        default = Settings.model_fields[RULES[name].setting].default  # ignores any local .env override
        assert parse_rate(default) == rate, name


@pytest.mark.parametrize("value", ["5", "5/fortnight", "x/minute", "5/0 minutes", "/hour"])
def test_invalid_rates_rejected(value):
    with pytest.raises(ValueError):
        parse_rate(value)


def test_rate_limit_configuration_is_documented():
    doc = (REPO / "docs" / "RATE_LIMITING.md").read_text(encoding="utf-8")
    env_example = (REPO / ".env.example").read_text(encoding="utf-8")
    for name, rule in RULES.items():
        env_var = rule.setting.upper()
        assert env_var in doc, f"{env_var} missing from docs/RATE_LIMITING.md"
        assert env_var in env_example, f"{env_var} missing from .env.example"
        assert f"`{name}`" in doc, f"rule {name} not described in docs/RATE_LIMITING.md"
    for setting in ("REDIS_URL", "TRUSTED_PROXIES", "RATE_LIMIT_ENABLED", "Retry-After"):
        assert setting in doc
    assert "development fallback" in doc.lower() and "multi" in doc.lower()
