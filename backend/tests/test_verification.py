from datetime import timedelta

from sqlmodel import select

from app.models import AuditLog, VerificationCase
from app.models.base import utcnow
from app.models.enums import Role
from tests.helpers import (
    create_agent,
    create_property,
    make_user,
    move_case,
    open_and_submit_case,
    pass_all_checks,
    verify_agent,
)


async def _submitted(client, session):
    _, agent, profile = await create_agent(client, session)
    prop = await create_property(client, agent)
    case = await open_and_submit_case(client, agent, prop["id"])
    _, reviewer = await make_user(session, Role.REVIEWER)
    return agent, profile, prop, case, reviewer


async def test_full_case_workflow_writes_audit(client, session):
    agent, _, prop, case, reviewer = await _submitted(client, session)
    assert case["status"] == "SUBMITTED"
    assert case["verification_reference"].startswith("PCV-")
    assert (await move_case(client, reviewer, case["id"], "IN_REVIEW")).json()[
        "assigned_reviewer_id"
    ] is not None
    r = await move_case(
        client,
        reviewer,
        case["id"],
        "INSPECTION_BOOKED",
        inspection_scheduled_for=(utcnow() + timedelta(days=1)).isoformat(),
    )
    assert r.status_code == 200 and r.json()["inspection_scheduled_for"]
    await pass_all_checks(client, reviewer, case["id"])
    r = await move_case(client, reviewer, case["id"], "VERIFIED", reviewer_notes="All good")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "VERIFIED" and body["expires_at"]

    actions = [
        a.action
        for a in (
            await session.exec(
                select(AuditLog).where(
                    AuditLog.entity_type == "VerificationCase", AuditLog.entity_id == case["id"]
                )
            )
        ).all()
    ]
    for expected in (
        "CASE_OPENED",
        "CASE_SUBMITTED",
        "REVIEW_STARTED",
        "INSPECTION_BOOKED",
        "CHECK_RECORDED",
        "PROPERTY_VERIFIED",
    ):
        assert expected in actions
    assert (await client.get(f"/api/properties/{prop['id']}")).json()["verification"]["status"] == "VERIFIED"

    # The agent can read the case's audit log; a stranger cannot even see the case exists.
    assert (
        await client.get(f"/api/verification-cases/{case['id']}/audit-log", headers=agent)
    ).status_code == 200
    _, stranger = await make_user(session, Role.AGENT)
    assert (await client.get(f"/api/verification-cases/{case['id']}", headers=stranger)).status_code == 404


async def test_submitter_cannot_approve_own_case(client, session):
    agent, _, _, case, _ = await _submitted(client, session)
    r = await move_case(client, agent, case["id"], "IN_REVIEW")
    assert r.status_code == 403
    r = await move_case(client, agent, case["id"], "VERIFIED")
    assert r.status_code == 409  # SUBMITTED -> VERIFIED is not a valid transition at all


async def test_reviewer_who_manages_property_is_blocked(client, session):
    """A staff member who is also the property's owner must not review it (conflict of interest)."""
    reviewer_user, reviewer = await make_user(session, Role.REVIEWER)
    _, agent, _ = await create_agent(client, session)
    prop = await create_property(client, agent)
    case = await open_and_submit_case(client, agent, prop["id"])
    db_case = await session.get(VerificationCase, case["id"])
    db_case.submitted_by = reviewer_user.id
    session.add(db_case)
    await session.commit()
    assert (await move_case(client, reviewer, case["id"], "IN_REVIEW")).status_code == 403


async def test_invalid_transitions_rejected(client, session):
    _, _, _, case, reviewer = await _submitted(client, session)
    assert (await move_case(client, reviewer, case["id"], "VERIFIED")).status_code == 409
    assert (await move_case(client, reviewer, case["id"], "IN_REVIEW")).status_code == 200
    assert (await move_case(client, reviewer, case["id"], "IN_REVIEW")).status_code == 409  # duplicate
    assert (await move_case(client, reviewer, case["id"], "DRAFT")).status_code == 409


async def test_cannot_verify_with_incomplete_checklist(client, session):
    _, _, _, case, reviewer = await _submitted(client, session)
    await move_case(client, reviewer, case["id"], "IN_REVIEW")
    r = await move_case(client, reviewer, case["id"], "VERIFIED")
    assert r.status_code == 400
    assert "Checklist incomplete" in r.json()["detail"]


async def test_mandatory_check_cannot_be_not_applicable(client, session):
    _, _, _, case, reviewer = await _submitted(client, session)
    await move_case(client, reviewer, case["id"], "IN_REVIEW")
    await pass_all_checks(client, reviewer, case["id"])
    await client.post(
        f"/api/verification-cases/{case['id']}/checks",
        json={"check_type": "AUTHORITY_TO_MARKET_SEEN", "result": "NOT_APPLICABLE"},
        headers=reviewer,
    )
    assert (await move_case(client, reviewer, case["id"], "VERIFIED")).status_code == 400


async def test_rejection_requires_reason_and_is_terminal(client, session):
    agent, _, prop, case, reviewer = await _submitted(client, session)
    await move_case(client, reviewer, case["id"], "IN_REVIEW")
    assert (await move_case(client, reviewer, case["id"], "REJECTED")).status_code == 400
    r = await move_case(
        client, reviewer, case["id"], "REJECTED", reason="Authority letter does not match the address"
    )
    assert r.status_code == 200 and r.json()["rejection_reason"]
    assert (await move_case(client, reviewer, case["id"], "IN_REVIEW")).status_code == 409
    # Rejected listings disappear from public search.
    ids = [p["id"] for p in (await client.get("/api/properties", params={"page_size": 50})).json()["items"]]
    assert prop["id"] not in ids
    # A brand-new case can be opened after rejection.
    assert (await client.post(f"/api/properties/{prop['id']}/verification", headers=agent)).status_code == 201


async def test_case_cannot_be_submitted_without_evidence(client, session):
    _, agent, _ = await create_agent(client, session)
    prop = await create_property(client, agent)
    case = (await client.post(f"/api/properties/{prop['id']}/verification", headers=agent)).json()
    r = await client.post(f"/api/verification-cases/{case['id']}/submit", headers=agent)
    assert r.status_code == 400


async def test_only_one_open_case_per_property(client, session):
    _, agent, _ = await create_agent(client, session)
    prop = await create_property(client, agent)
    assert (await client.post(f"/api/properties/{prop['id']}/verification", headers=agent)).status_code == 201
    assert (await client.post(f"/api/properties/{prop['id']}/verification", headers=agent)).status_code == 409


async def test_document_review_by_reviewer_only(client, session):
    agent, _, prop, case, reviewer = await _submitted(client, session)
    doc_id = case["documents"][0]["id"]
    url = f"/api/verification-cases/{case['id']}/documents/{doc_id}/review"
    assert (await client.post(url, json={"review_status": "ACCEPTED"}, headers=agent)).status_code == 403
    await move_case(client, reviewer, case["id"], "IN_REVIEW")
    r = await client.post(
        url, json={"review_status": "ACCEPTED", "reviewer_notes": "Matches owner ID"}, headers=reviewer
    )
    assert r.status_code == 200
    assert r.json()["documents"][0]["review_status"] == "ACCEPTED"


async def test_failed_transition_leaves_no_partial_update(client, session):
    """Expiry in the past fails inside on_apply: status, property summary and audit must all be untouched."""
    _, _, prop, case, reviewer = await _submitted(client, session)
    await move_case(client, reviewer, case["id"], "IN_REVIEW")
    await pass_all_checks(client, reviewer, case["id"])
    before = (
        await session.exec(
            select(AuditLog).where(
                AuditLog.entity_id == case["id"], AuditLog.entity_type == "VerificationCase"
            )
        )
    ).all()
    r = await move_case(
        client, reviewer, case["id"], "VERIFIED", expires_at=(utcnow() - timedelta(days=1)).isoformat()
    )
    assert r.status_code == 400
    session.expire_all()
    assert (await session.get(VerificationCase, case["id"])).status.value == "IN_REVIEW"
    assert (await client.get(f"/api/properties/{prop['id']}")).json()["verification"]["status"] == "IN_REVIEW"
    after = (
        await session.exec(
            select(AuditLog).where(
                AuditLog.entity_id == case["id"], AuditLog.entity_type == "VerificationCase"
            )
        )
    ).all()
    assert len(after) == len(before)


async def test_verified_agent_does_not_verify_listings(client, session):
    _, agent, profile = await create_agent(client, session)
    await verify_agent(client, session, agent, profile["id"])
    prop = await create_property(client, agent)
    detail = (await client.get(f"/api/properties/{prop['id']}")).json()
    assert detail["agent"]["is_verified"] is True
    assert detail["verification"]["status"] == "NOT_SUBMITTED"
    assert detail["verification"]["is_currently_verified"] is False
