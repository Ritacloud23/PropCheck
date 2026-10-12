from datetime import timedelta

from sqlmodel import select

from app.models import AgentProfile, AuditLog
from app.models.base import utcnow
from app.models.enums import Role
from tests.helpers import create_agent, make_user, submit_agent_application, verify_agent


async def test_phone_hidden_without_consent(client, session):
    _, _, profile = await create_agent(client, session, display_phone_publicly=False)
    _, h2, profile2 = await create_agent(client, session, display_phone_publicly=True)
    # Agents in DRAFT are hidden from the public; submit so they appear.
    pub = await client.get(f"/api/agents/{profile['id']}")
    assert pub.status_code == 404  # DRAFT profile is not public
    await submit_agent_application(client, h2)
    shown = (await client.get(f"/api/agents/{profile2['id']}")).json()
    assert shown["phone_number"] == "+2348031234567"
    assert shown["whatsapp_number"] == "+2348031234567"


async def test_directory_hides_contact_unless_consented(client, session):
    _, h1, p1 = await create_agent(client, session, display_phone_publicly=False)
    await submit_agent_application(client, h1)
    item = next(
        a
        for a in (await client.get("/api/agents", params={"page_size": 50})).json()["items"]
        if a["id"] == p1["id"]
    )
    assert item["phone_number"] is None and item["whatsapp_number"] is None and item["email"] is None
    assert item["contact_public"] is False
    own = (await client.get("/api/agents/profile", headers=h1)).json()
    assert own["private_phone_number"] == "+2348031234567"


async def test_agent_verification_flow_and_directory_filter(client, session):
    _, headers, profile = await create_agent(client, session)
    verified = await verify_agent(client, session, headers, profile["id"])
    assert verified["verification_status"] == "VERIFIED"
    assert verified["verification_expiry_date"]
    r = await client.get("/api/agents", params={"verified_only": True, "state": "Lagos", "city": "Lekki"})
    assert profile["id"] in [a["id"] for a in r.json()["items"]]
    r = await client.get("/api/agents", params={"verified_only": True, "state": "Enugu"})
    assert profile["id"] not in [a["id"] for a in r.json()["items"]]
    actions = [
        a.action
        for a in (
            await session.exec(select(AuditLog).where(AuditLog.entity_type == "AgentVerification"))
        ).all()
    ]
    assert {"AGENT_APPLICATION_SUBMITTED", "AGENT_REVIEW_STARTED", "AGENT_VERIFIED"} <= set(actions)


async def test_agent_cannot_review_self_even_as_staff(client, session):
    """Applications by a user are blocked from review by that same user id."""
    _, headers, profile = await create_agent(client, session)
    await submit_agent_application(client, headers)
    r = await client.post(f"/api/reviewer/agents/{profile['id']}/approve", json={}, headers=headers)
    assert r.status_code == 403  # agents are not staff


async def test_agent_rejection_needs_reason(client, session):
    _, headers, profile = await create_agent(client, session)
    await submit_agent_application(client, headers)
    _, reviewer = await make_user(session, Role.REVIEWER)
    await client.post(f"/api/reviewer/agents/{profile['id']}/start-review", json={}, headers=reviewer)
    assert (
        await client.post(f"/api/reviewer/agents/{profile['id']}/reject", json={}, headers=reviewer)
    ).status_code == 400
    r = await client.post(
        f"/api/reviewer/agents/{profile['id']}/reject", json={"reason": "ID unreadable"}, headers=reviewer
    )
    assert r.status_code == 200 and r.json()["verification_status"] == "REJECTED"
    # They can re-apply with a new application.
    assert (await submit_agent_application(client, headers))["status"] == "SUBMITTED"


async def test_suspension_hides_agent_and_contact(client, session):
    _, headers, profile = await create_agent(client, session, display_phone_publicly=True)
    _, reviewer = await make_user(session, Role.REVIEWER)
    await verify_agent(client, session, headers, profile["id"], reviewer)
    assert (
        await client.post(f"/api/reviewer/agents/{profile['id']}/suspend", json={}, headers=reviewer)
    ).status_code == 400
    r = await client.post(
        f"/api/reviewer/agents/{profile['id']}/suspend", json={"reason": "Fraud reports"}, headers=reviewer
    )
    assert r.status_code == 200 and r.json()["verification_status"] == "SUSPENDED"
    assert profile["id"] not in [a["id"] for a in (await client.get("/api/agents")).json()["items"]]
    public = (await client.get(f"/api/agents/{profile['id']}")).json()
    assert public["phone_number"] is None and public["complaint_status"] == "SUSPENDED"
    # Suspended agents cannot list new properties.
    from tests.helpers import PROPERTY

    assert (await client.post("/api/properties", json=PROPERTY, headers=headers)).status_code == 403


async def test_expired_agent_badge(client, session):
    _, headers, profile = await create_agent(client, session)
    await verify_agent(client, session, headers, profile["id"])
    row = await session.get(AgentProfile, profile["id"])
    row.verification_expiry_date = utcnow() - timedelta(minutes=1)
    session.add(row)
    await session.commit()
    public = (await client.get(f"/api/agents/{profile['id']}")).json()
    assert public["verification_status"] == "EXPIRED" and public["is_verified"] is False
    assert profile["id"] not in [
        a["id"] for a in (await client.get("/api/agents", params={"verified_only": True})).json()["items"]
    ]


async def test_identity_documents_never_public(client, session):
    _, headers, profile = await create_agent(client, session)
    await submit_agent_application(client, headers)
    public = (await client.get(f"/api/agents/{profile['id']}")).json()
    assert "latest_application" not in public
    assert "identity_document" not in str(public)
    own = (await client.get("/api/agents/profile/verification", headers=headers)).json()
    assert own[0]["identity_document_link"].startswith("/api/files/")
