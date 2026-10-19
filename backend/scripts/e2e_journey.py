"""End-to-end journey against a RUNNING stack (API + seeded database).

    python scripts/e2e_journey.py [--api http://localhost:8000]

Registers a fresh agent and renter, uses the seeded reviewer (reviewer@propcheck.ng) and walks:
agent verification -> listing -> property verification -> search -> inspection booking ->
test reservation -> payment -> keys confirmed -> duplicate release refused.
"""

import argparse
import secrets
import sys
from datetime import UTC, datetime, timedelta

import httpx

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)
PDF = b"%PDF-1.4\n%%EOF\n"
PASSWORD = "PropCheck2026"


def step(msg: str) -> None:
    print(f"  - {msg}")


def check(resp: httpx.Response, status: int = 200) -> dict:
    if resp.status_code != status:
        print(f"FAILED {resp.request.method} {resp.request.url} -> {resp.status_code}: {resp.text}")
        sys.exit(1)
    return resp.json() if resp.content else {}


def client_for(api: str, email: str, password: str = PASSWORD, register: dict | None = None) -> httpx.Client:
    c = httpx.Client(base_url=api, timeout=30)
    if register:
        check(c.post("/api/auth/register", json={**register, "email": email, "password": password}), 201)
    else:
        check(c.post("/api/auth/login", json={"email": email, "password": password}))
    return c


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    api = parser.parse_args().api
    tag = secrets.token_hex(3)
    print(f"PropCheck E2E journey against {api}")

    agent = client_for(
        api, f"e2e-agent-{tag}@example.com", register={"full_name": "E2E Agent", "role": "AGENT"}
    )
    renter = client_for(
        api, f"e2e-renter-{tag}@example.com", register={"full_name": "E2E Renter", "role": "RENTER"}
    )
    reviewer = client_for(api, "reviewer@propcheck.ng")
    step("registered agent + renter, logged in seeded reviewer")

    profile = check(
        agent.post(
            "/api/agents/profile",
            json={
                "agency_name": f"E2E Realty {tag}",
                "phone_number": "08031234567",
                "states_covered": ["Lagos"],
                "cities_covered": ["Yaba"],
                "property_types": ["MINI_FLAT"],
                "service_types": ["RENTAL"],
                "display_phone_publicly": True,
            },
        ),
        201,
    )
    check(
        agent.post(
            "/api/agents/profile/verification",
            files={"identity_document": ("id.pdf", PDF, "application/pdf")},
        ),
        201,
    )
    check(reviewer.post(f"/api/reviewer/agents/{profile['id']}/start-review", json={}))
    check(reviewer.post(f"/api/reviewer/agents/{profile['id']}/approve", json={}))
    step("agent verified by reviewer")

    prop = check(
        agent.post(
            "/api/properties",
            json={
                "title": f"E2E mini flat {tag}",
                "address": "5 Herbert Macaulay Way, Yaba",
                "state": "Lagos",
                "city": "Yaba",
                "property_type": "MINI_FLAT",
                "bedrooms": 1,
                "bathrooms": 1,
                "rent_amount": 1_200_000,
                "agency_fee": 120_000,
            },
        ),
        201,
    )
    pid = prop["id"]
    check(agent.post(f"/api/properties/{pid}/media", files={"file": ("p.png", PNG, "image/png")}), 201)
    check(
        agent.post(
            f"/api/properties/{pid}/documents",
            files={"file": ("a.pdf", PDF, "application/pdf")},
            data={"document_type": "AUTHORITY_LETTER"},
        ),
        201,
    )
    case = check(agent.post(f"/api/properties/{pid}/verification"), 201)
    check(agent.post(f"/api/verification-cases/{case['id']}/submit"))
    check(reviewer.post(f"/api/verification-cases/{case['id']}/transition", json={"to_status": "IN_REVIEW"}))
    for c in case["checks"]:
        check(
            reviewer.post(
                f"/api/verification-cases/{case['id']}/checks",
                json={"check_type": c["check_type"], "result": "PASSED", "evidence_note": "E2E"},
            )
        )
    verified = check(
        reviewer.post(f"/api/verification-cases/{case['id']}/transition", json={"to_status": "VERIFIED"})
    )
    step(f"property verified ({verified['verification_reference']}, expires {verified['expires_at'][:10]})")

    found = check(
        renter.get("/api/properties", params={"verified_only": True, "city": "Yaba", "page_size": 50})
    )
    assert pid in [p["id"] for p in found["items"]], "verified property not found in search"
    step("renter found property with verified-only filter")

    start = datetime.now(UTC) + timedelta(days=2)
    slot = check(
        agent.post(
            f"/api/properties/{pid}/inspection-slots",
            json={"start_time": start.isoformat(), "end_time": (start + timedelta(hours=1)).isoformat()},
        ),
        201,
    )
    booking = check(renter.post("/api/inspection-bookings", json={"slot_id": slot["id"]}), 201)
    check(agent.post(f"/api/inspection-bookings/{booking['id']}/confirm"))
    step("inspection booked and confirmed")

    res = check(renter.post("/api/reservations", json={"property_id": pid, "accept_terms": True}), 201)
    paid = check(renter.post(f"/api/reservations/{res['id']}/pay"))
    if paid["authorization_url"]:
        print(f"  ! Paystack TEST checkout required: {paid['authorization_url']} - stopping here.")
        return
    step(f"test payment {paid['reservation']['payment_reference']} -> {paid['reservation']['status']}")
    check(renter.post(f"/api/reservations/{res['id']}/confirm-keys"))
    dup = renter.post(f"/api/reservations/{res['id']}/confirm-keys")
    assert dup.status_code == 409, f"duplicate release should be 409, got {dup.status_code}"
    step("keys confirmed -> RELEASED; duplicate release refused (409)")

    log = check(
        reviewer.get("/api/reviewer/audit-log", params={"entity_type": "Reservation", "entity_id": res["id"]})
    )
    step(f"audit log has {len(log)} reservation entries")
    print("E2E journey passed.")


if __name__ == "__main__":
    main()
