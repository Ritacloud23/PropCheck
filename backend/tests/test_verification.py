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


def _submitted(client, session):
    _, agent, profile = create_agent(client, session)
    prop = create_property(client, agent)
    case = open_and_submit_case(client, agent, prop["id"])
    _, reviewer = make_user(session, Role.REVIEWER)
    return agent, profile, prop, case, reviewer


def test_full_case_workflow_writes_audit(client, session):
    agent, _, prop, case, reviewer = _submitted(client, session)
    assert case["status"] == "SUBMITTED"
    assert case["verification_reference"].startswith("PCV-")
    assert move_case(client, reviewer, case["id"], "IN_REVIEW").json()["assigned_reviewer_id"] is not None
    r = move_case(
        client,
        reviewer,
        case["id"],
        "INSPECTION_BOOKED",
        inspection_scheduled_for=(utcnow() + timedelta(days=1)).isoformat(),
    )
    assert r.status_code == 200 and r.json()["inspection_scheduled_for"]
    pass_all_checks(client, reviewer, case["id"])
    r = move_case(client, reviewer, case["id"], "VERIFIED", reviewer_notes="All good")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "VERIFIED" and body["expires_at"]

    actions = [
        a.action
        for a in session.exec(
            select(AuditLog).where(
                AuditLog.entity_type == "VerificationCase", AuditLog.entity_id == case["id"]
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
    assert client.get(f"/api/properties/{prop['id']}").json()["verification"]["status"] == "VERIFIED"

    # The agent can read the case's audit log; a stranger cannot even see the case exists.
    assert client.get(f"/api/verification-cases/{case['id']}/audit-log", headers=agent).status_code == 200
    _, stranger = make_user(session, Role.AGENT)
    assert client.get(f"/api/verification-cases/{case['id']}", headers=stranger).status_code == 404


def test_submitter_cannot_approve_own_case(client, session):
    agent, _, _, case, _ = _submitted(client, session)
    r = move_case(client, agent, case["id"], "IN_REVIEW")
    assert r.status_code == 403
    r = move_case(client, agent, case["id"], "VERIFIED")
    assert r.status_code == 409  # SUBMITTED -> VERIFIED is not a valid transition at all


def test_reviewer_who_manages_property_is_blocked(client, session):
    """A staff member who is also the property's owner must not review it (conflict of interest)."""
    reviewer_user, reviewer = make_user(session, Role.REVIEWER)
    _, agent, _ = create_agent(client, session)
    prop = create_property(client, agent)
    case = open_and_submit_case(client, agent, prop["id"])
    db_case = session.get(VerificationCase, case["id"])
    db_case.submitted_by = reviewer_user.id
    session.add(db_case)
    session.commit()
    assert move_case(client, reviewer, case["id"], "IN_REVIEW").status_code == 403


def test_invalid_transitions_rejected(client, session):
    _, _, _, case, reviewer = _submitted(client, session)
    assert move_case(client, reviewer, case["id"], "VERIFIED").status_code == 409
    assert move_case(client, reviewer, case["id"], "IN_REVIEW").status_code == 200
    assert move_case(client, reviewer, case["id"], "IN_REVIEW").status_code == 409  # duplicate
    assert move_case(client, reviewer, case["id"], "DRAFT").status_code == 409


def test_cannot_verify_with_incomplete_checklist(client, session):
    _, _, _, case, reviewer = _submitted(client, session)
    move_case(client, reviewer, case["id"], "IN_REVIEW")
    r = move_case(client, reviewer, case["id"], "VERIFIED")
    assert r.status_code == 400
    assert "Checklist incomplete" in r.json()["detail"]


def test_mandatory_check_cannot_be_not_applicable(client, session):
    _, _, _, case, reviewer = _submitted(client, session)
    move_case(client, reviewer, case["id"], "IN_REVIEW")
    pass_all_checks(client, reviewer, case["id"])
    client.post(
        f"/api/verification-cases/{case['id']}/checks",
        json={"check_type": "AUTHORITY_TO_MARKET_SEEN", "result": "NOT_APPLICABLE"},
        headers=reviewer,
    )
    assert move_case(client, reviewer, case["id"], "VERIFIED").status_code == 400


def test_rejection_requires_reason_and_is_terminal(client, session):
    agent, _, prop, case, reviewer = _submitted(client, session)
    move_case(client, reviewer, case["id"], "IN_REVIEW")
    assert move_case(client, reviewer, case["id"], "REJECTED").status_code == 400
    r = move_case(
        client, reviewer, case["id"], "REJECTED", reason="Authority letter does not match the address"
    )
    assert r.status_code == 200 and r.json()["rejection_reason"]
    assert move_case(client, reviewer, case["id"], "IN_REVIEW").status_code == 409
    # Rejected listings disappear from public search.
    ids = [p["id"] for p in client.get("/api/properties", params={"page_size": 50}).json()["items"]]
    assert prop["id"] not in ids
    # A brand-new case can be opened after rejection.
    assert client.post(f"/api/properties/{prop['id']}/verification", headers=agent).status_code == 201


def test_case_cannot_be_submitted_without_evidence(client, session):
    _, agent, _ = create_agent(client, session)
    prop = create_property(client, agent)
    case = client.post(f"/api/properties/{prop['id']}/verification", headers=agent).json()
    r = client.post(f"/api/verification-cases/{case['id']}/submit", headers=agent)
    assert r.status_code == 400


def test_only_one_open_case_per_property(client, session):
    _, agent, _ = create_agent(client, session)
    prop = create_property(client, agent)
    assert client.post(f"/api/properties/{prop['id']}/verification", headers=agent).status_code == 201
    assert client.post(f"/api/properties/{prop['id']}/verification", headers=agent).status_code == 409


def test_document_review_by_reviewer_only(client, session):
    agent, _, prop, case, reviewer = _submitted(client, session)
    doc_id = case["documents"][0]["id"]
    url = f"/api/verification-cases/{case['id']}/documents/{doc_id}/review"
    assert client.post(url, json={"review_status": "ACCEPTED"}, headers=agent).status_code == 403
    move_case(client, reviewer, case["id"], "IN_REVIEW")
    r = client.post(
        url, json={"review_status": "ACCEPTED", "reviewer_notes": "Matches owner ID"}, headers=reviewer
    )
    assert r.status_code == 200
    assert r.json()["documents"][0]["review_status"] == "ACCEPTED"


def test_failed_transition_leaves_no_partial_update(client, session):
    """Expiry in the past fails inside on_apply: status, property summary and audit must all be untouched."""
    _, _, prop, case, reviewer = _submitted(client, session)
    move_case(client, reviewer, case["id"], "IN_REVIEW")
    pass_all_checks(client, reviewer, case["id"])
    before = session.exec(
        select(AuditLog).where(AuditLog.entity_id == case["id"], AuditLog.entity_type == "VerificationCase")
    ).all()
    r = move_case(
        client, reviewer, case["id"], "VERIFIED", expires_at=(utcnow() - timedelta(days=1)).isoformat()
    )
    assert r.status_code == 400
    session.expire_all()
    assert session.get(VerificationCase, case["id"]).status.value == "IN_REVIEW"
    assert client.get(f"/api/properties/{prop['id']}").json()["verification"]["status"] == "IN_REVIEW"
    after = session.exec(
        select(AuditLog).where(AuditLog.entity_id == case["id"], AuditLog.entity_type == "VerificationCase")
    ).all()
    assert len(after) == len(before)


def test_verified_agent_does_not_verify_listings(client, session):
    _, agent, profile = create_agent(client, session)
    verify_agent(client, session, agent, profile["id"])
    prop = create_property(client, agent)
    detail = client.get(f"/api/properties/{prop['id']}").json()
    assert detail["agent"]["is_verified"] is True
    assert detail["verification"]["status"] == "NOT_SUBMITTED"
    assert detail["verification"]["is_currently_verified"] is False
