"""Factories that drive the real API, so tests exercise the same paths as the frontend."""

import itertools
from datetime import timedelta

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import User
from app.models.base import utcnow
from app.models.enums import CheckResult, CheckType, Role
from app.security import create_access_token, hash_password

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"

_seq = itertools.count(1)


async def make_user(
    session: AsyncSession, role: Role = Role.RENTER, name: str | None = None
) -> tuple[User, dict]:
    n = next(_seq)
    user = User(
        full_name=name or f"{role.value.title()} {n}",
        email=f"{role.value.lower()}{n}@example.com",
        phone="+2348031234567",
        password_hash=await hash_password("Password123"),
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user, {"Authorization": f"Bearer {create_access_token(user.id, role.value)}"}


AGENT_PROFILE = {
    "agency_name": "Lekki Homes",
    "bio": "Rentals across Lekki and Ajah.",
    "phone_number": "0803 123 4567",
    "whatsapp_number": "08031234567",
    "email": "agent@example.com",
    "states_covered": ["Lagos"],
    "cities_covered": ["Lekki", "Ajah"],
    "property_types": ["FLAT", "MINI_FLAT"],
    "service_types": ["RENTAL"],
    "budget_min": 500_000,
    "budget_max": 10_000_000,
    "years_experience": 6,
}

PROPERTY = {
    "title": "Clean 2-bedroom flat in Lekki Phase 1",
    "description": "Serviced estate, 24h power.",
    "address": "12 Admiralty Way, Lekki Phase 1",
    "landmark": "Near Lekki Phase 1 gate",
    "state": "Lagos",
    "city": "Lagos",
    "area": "Lekki",
    "local_government_area": "Eti-Osa",
    "latitude": 6.4474,
    "longitude": 3.4727,
    "property_type": "FLAT",
    "bedrooms": 2,
    "bathrooms": 2,
    "rent_amount": 3_500_000,
    "agency_fee": 350_000,
    "legal_fee": 350_000,
    "caution_fee": 200_000,
    "other_fees": 50_000,
    "other_fees_description": "Estate due",
}


async def create_agent(client, session, **overrides) -> tuple[User, dict, dict]:
    user, headers = await make_user(session, Role.AGENT)
    r = await client.post("/api/agents/profile", json={**AGENT_PROFILE, **overrides}, headers=headers)
    assert r.status_code == 201, r.text
    return user, headers, r.json()


async def submit_agent_application(client, headers) -> dict:
    r = await client.post(
        "/api/agents/profile/verification",
        files={"identity_document": ("id.pdf", PDF, "application/pdf")},
        data={"evidence_notes": "NIN slip attached"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def verify_agent(client, session, agent_headers, agent_id, reviewer_headers=None) -> dict:
    if reviewer_headers is None:
        _, reviewer_headers = await make_user(session, Role.REVIEWER)
    await submit_agent_application(client, agent_headers)
    r = await client.post(f"/api/reviewer/agents/{agent_id}/start-review", json={}, headers=reviewer_headers)
    assert r.status_code == 200, r.text
    r = await client.post(f"/api/reviewer/agents/{agent_id}/approve", json={}, headers=reviewer_headers)
    assert r.status_code == 200, r.text
    return r.json()


async def create_property(client, headers, **overrides) -> dict:
    r = await client.post("/api/properties", json={**PROPERTY, **overrides}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def upload_evidence(client, headers, property_id) -> None:
    r = await client.post(
        f"/api/properties/{property_id}/media", files={"file": ("p.png", PNG, "image/png")}, headers=headers
    )
    assert r.status_code == 201, r.text
    r = await client.post(
        f"/api/properties/{property_id}/documents",
        files={"file": ("authority.pdf", PDF, "application/pdf")},
        data={"document_type": "AUTHORITY_LETTER"},
        headers=headers,
    )
    assert r.status_code == 201, r.text


async def open_and_submit_case(client, headers, property_id) -> dict:
    await upload_evidence(client, headers, property_id)
    r = await client.post(f"/api/properties/{property_id}/verification", headers=headers)
    assert r.status_code == 201, r.text
    case = r.json()
    r = await client.post(f"/api/verification-cases/{case['id']}/submit", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def pass_all_checks(client, reviewer_headers, case_id) -> dict:
    data = {}
    for ct in CheckType:
        r = await client.post(
            f"/api/verification-cases/{case_id}/checks",
            json={
                "check_type": ct.value,
                "result": CheckResult.PASSED.value,
                "evidence_note": "Seen on site",
            },
            headers=reviewer_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
    return data


async def move_case(client, headers, case_id, to_status, **extra):
    return await client.post(
        f"/api/verification-cases/{case_id}/transition",
        json={"to_status": to_status, **extra},
        headers=headers,
    )


async def verified_property(client, session) -> dict:
    """Verified agent + property verified by an independent reviewer. Returns ids and headers."""
    agent_user, agent_headers, profile = await create_agent(client, session)
    _, reviewer_headers = await make_user(session, Role.REVIEWER)
    await verify_agent(client, session, agent_headers, profile["id"], reviewer_headers)
    prop = await create_property(client, agent_headers)
    case = await open_and_submit_case(client, agent_headers, prop["id"])
    assert (await move_case(client, reviewer_headers, case["id"], "IN_REVIEW")).status_code == 200
    await pass_all_checks(client, reviewer_headers, case["id"])
    r = await move_case(client, reviewer_headers, case["id"], "VERIFIED")
    assert r.status_code == 200, r.text
    return {
        "agent_user": agent_user,
        "agent_headers": agent_headers,
        "agent_profile": profile,
        "reviewer_headers": reviewer_headers,
        "property": prop,
        "case": r.json(),
    }


def future(hours: float) -> str:
    return (utcnow() + timedelta(hours=hours)).isoformat()
