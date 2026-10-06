from app.models.enums import Role
from tests.helpers import PNG, create_agent, create_property, make_user, verify_agent

REQUEST = {
    "name": "Chioma Eze",
    "phone": "0803 555 1234",
    "state": "Lagos",
    "city": "Lekki",
    "property_type": "FLAT",
    "bedrooms": 2,
    "budget_min": 2_000_000,
    "budget_max": 4_000_000,
    "consent_to_share": True,
}


def test_house_search_requires_consent_and_valid_budget(client, session):
    _, renter = make_user(session, Role.RENTER)
    assert (
        client.post(
            "/api/house-search-requests", json={**REQUEST, "consent_to_share": False}, headers=renter
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/house-search-requests", json={**REQUEST, "budget_min": 5_000_000}, headers=renter
        ).status_code
        == 422
    )
    r = client.post("/api/house-search-requests", json=REQUEST, headers=renter)
    assert r.status_code == 201 and r.json()["phone"] == "+2348035551234"


def test_assignment_flow_and_agent_visibility(client, session):
    _, renter = make_user(session, Role.RENTER)
    _, reviewer = make_user(session, Role.REVIEWER)
    _, agent, profile = create_agent(client, session, display_phone_publicly=False)
    _, other_agent, other_profile = create_agent(client, session)
    verify_agent(client, session, agent, profile["id"], reviewer)
    req = client.post("/api/house-search-requests", json=REQUEST, headers=renter).json()

    # Agents never see unassigned requests.
    assert client.get("/api/agent/enquiries", headers=agent).json() == []
    assert client.get(f"/api/house-search-requests/{req['id']}", headers=agent).status_code == 404

    candidates = client.get(
        f"/api/house-search-requests/{req['id']}/candidate-agents", headers=reviewer
    ).json()
    assert profile["id"] in [c["id"] for c in candidates]
    # Unverified agents cannot be assigned.
    r = client.post(
        f"/api/house-search-requests/{req['id']}/assign",
        json={"agent_id": other_profile["id"]},
        headers=reviewer,
    )
    assert r.status_code == 400
    r = client.post(
        f"/api/house-search-requests/{req['id']}/assign", json={"agent_id": profile["id"]}, headers=reviewer
    )
    assert r.status_code == 200 and r.json()["status"] == "ASSIGNED"

    # Renter now sees the assigned agent's contact even though the agent hides it publicly.
    mine = client.get(f"/api/house-search-requests/{req['id']}", headers=renter).json()
    assert mine["assigned_agent"]["phone_number"] == "+2348031234567"

    enquiries = client.get("/api/agent/enquiries", headers=agent).json()
    assert len(enquiries) == 1 and enquiries[0]["request"]["id"] == req["id"]
    assert client.get("/api/agent/enquiries", headers=other_agent).json() == []
    assert (
        client.post(
            f"/api/house-search-requests/{req['id']}/respond",
            json={"message": "I have 3 options"},
            headers=other_agent,
        ).status_code
        == 404
    )

    r = client.post(
        f"/api/house-search-requests/{req['id']}/respond",
        json={"message": "I have 3 options for you"},
        headers=agent,
    )
    assert r.status_code == 200 and r.json()["status"] == "CONTACTED"
    r = client.post(f"/api/house-search-requests/{req['id']}/complete", headers=renter)
    assert r.status_code == 200 and r.json()["status"] == "COMPLETED"
    assert (
        client.post(f"/api/house-search-requests/{req['id']}/cancel", json={}, headers=renter).status_code
        == 409
    )


def test_renter_cancels_and_cannot_touch_others(client, session):
    _, r1 = make_user(session, Role.RENTER)
    _, r2 = make_user(session, Role.RENTER)
    req = client.post("/api/house-search-requests", json=REQUEST, headers=r1).json()
    assert (
        client.post(f"/api/house-search-requests/{req['id']}/cancel", json={}, headers=r2).status_code == 404
    )
    r = client.post(
        f"/api/house-search-requests/{req['id']}/cancel", json={"reason": "Found a place"}, headers=r1
    )
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"


def test_report_agent_and_resolve_with_suspension(client, session):
    _, renter = make_user(session, Role.RENTER)
    _, reviewer = make_user(session, Role.REVIEWER)
    _, agent, profile = create_agent(client, session)
    verify_agent(client, session, agent, profile["id"], reviewer)
    r = client.post(
        f"/api/agents/{profile['id']}/report",
        data={"reason": "PAYMENT_PRESSURE", "description": "Asked me to pay before inspection."},
        files={"evidence": ("chat.png", PNG, "image/png")},
        headers=renter,
    )
    assert r.status_code == 201, r.text
    report = r.json()
    assert report["status"] == "OPEN" and report["has_evidence"]
    assert client.get(f"/api/agents/{profile['id']}").json()["complaint_status"] == "COMPLAINT_UNDER_REVIEW"

    assert client.get("/api/reviewer/reports", headers=agent).status_code == 403
    assert (
        client.post(
            f"/api/reviewer/reports/{report['id']}/resolve", json={"reason": ""}, headers=reviewer
        ).status_code
        == 422
    )
    r = client.post(
        f"/api/reviewer/reports/{report['id']}/resolve",
        json={"reason": "Confirmed via chat logs", "suspend_agent": True},
        headers=reviewer,
    )
    assert r.status_code == 200 and r.json()["status"] == "RESOLVED"
    assert client.get(f"/api/agents/{profile['id']}").json()["verification_status"] == "SUSPENDED"
    assert (
        client.post(
            f"/api/reviewer/reports/{report['id']}/reject", json={"reason": "again"}, headers=reviewer
        ).status_code
        == 409
    )
    assert client.get("/api/reports/mine", headers=renter).json()[0]["status"] == "RESOLVED"


def test_report_property_links_listing_agent(client, session):
    _, renter = make_user(session, Role.RENTER)
    _, agent, profile = create_agent(client, session)
    prop = create_property(client, agent)
    r = client.post(
        f"/api/properties/{prop['id']}/report",
        data={"reason": "MISLEADING_PHOTOS", "description": "Photos are of a different building."},
        headers=renter,
    )
    assert r.status_code == 201
    assert r.json()["agent_id"] == profile["id"] and r.json()["property"]["id"] == prop["id"]
    assert (
        client.post(
            f"/api/properties/{prop['id']}/report",
            data={"reason": "NOT_A_REASON", "description": "xxxxxxxxxxxx"},
            headers=renter,
        ).status_code
        == 422
    )


def test_reviewer_audit_log_and_summary(client, session):
    _, reviewer = make_user(session, Role.REVIEWER)
    _, agent, profile = create_agent(client, session)
    verify_agent(client, session, agent, profile["id"], reviewer)
    log = client.get(
        "/api/reviewer/audit-log", params={"entity_type": "AgentVerification"}, headers=reviewer
    ).json()
    assert log and all(entry["actor_name"] for entry in log)
    summary = client.get("/api/reviewer/summary", headers=reviewer).json()
    assert set(summary) >= {"agent_applications_waiting", "property_cases_waiting", "open_reports"}
