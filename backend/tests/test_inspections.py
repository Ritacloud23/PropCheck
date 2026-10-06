from datetime import timedelta

from app.models import InspectionSlot
from app.models.base import utcnow
from app.models.enums import Role
from tests.helpers import create_agent, create_property, future, make_user


def _prop(client, session):
    _, agent, _ = create_agent(client, session)
    return agent, create_property(client, agent)


def _slot(client, headers, pid, start_h=24, end_h=25):
    return client.post(
        f"/api/properties/{pid}/slots",
        json={"start_time": future(start_h), "end_time": future(end_h)},
        headers=headers,
    )


def test_overlapping_slots_rejected(client, session):
    agent, prop = _prop(client, session)
    assert _slot(client, agent, prop["id"], 24, 25).status_code == 201
    assert _slot(client, agent, prop["id"], 24.5, 25.5).status_code == 409
    assert _slot(client, agent, prop["id"], 25, 26).status_code == 201  # touching is fine


def test_db_exclusion_constraint_blocks_overlap(client, session):
    """Bypass the API pre-check: the database itself refuses overlapping live slots."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    agent, prop = _prop(client, session)
    slot = _slot(client, agent, prop["id"]).json()
    start = utcnow() + timedelta(hours=24, minutes=30)
    session.add(
        InspectionSlot(
            property_id=prop["id"], landlord_user_id=1, start_time=start, end_time=start + timedelta(hours=1)
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
    assert slot["id"]


def test_slot_validation(client, session):
    agent, prop = _prop(client, session)
    r = client.post(
        f"/api/properties/{prop['id']}/slots",
        json={"start_time": future(5), "end_time": future(4)},
        headers=agent,
    )
    assert r.status_code == 422
    assert _slot(client, agent, prop["id"], -2, -1).status_code == 400


def test_double_booking_prevented(client, session):
    agent, prop = _prop(client, session)
    slot = _slot(client, agent, prop["id"]).json()
    _, r1 = make_user(session, Role.RENTER)
    _, r2 = make_user(session, Role.RENTER)
    assert (
        client.post("/api/inspection-bookings", json={"slot_id": slot["id"]}, headers=r1).status_code == 201
    )
    assert (
        client.post("/api/inspection-bookings", json={"slot_id": slot["id"]}, headers=r2).status_code == 409
    )
    public_slots = client.get(f"/api/properties/{prop['id']}/slots").json()
    assert slot["id"] not in [s["id"] for s in public_slots]


def test_booking_lifecycle_and_ownership(client, session):
    agent, prop = _prop(client, session)
    _, other_agent, _ = create_agent(client, session)
    slot = _slot(client, agent, prop["id"]).json()
    _, renter = make_user(session, Role.RENTER)
    booking = client.post(
        "/api/inspection-bookings", json={"slot_id": slot["id"], "renter_note": "After 5pm"}, headers=renter
    ).json()

    assert (
        client.post(f"/api/inspection-bookings/{booking['id']}/confirm", headers=other_agent).status_code
        == 404
    )
    assert client.post(f"/api/inspection-bookings/{booking['id']}/confirm", headers=renter).status_code == 403

    mine = client.get("/api/inspection-bookings", headers=agent).json()
    assert mine[0]["renter_name"] and "confirm" not in mine[0]["allowed_actions"]
    assert "CONFIRMED" in mine[0]["allowed_actions"]
    r = client.post(f"/api/inspection-bookings/{booking['id']}/confirm", headers=agent)
    assert r.status_code == 200 and r.json()["status"] == "CONFIRMED"
    assert client.post(f"/api/inspection-bookings/{booking['id']}/confirm", headers=agent).status_code == 409
    # Can't complete before the start time.
    assert client.post(f"/api/inspection-bookings/{booking['id']}/complete", headers=agent).status_code == 409
    # Renter cancels -> slot reopens for others.
    assert (
        client.post(f"/api/inspection-bookings/{booking['id']}/cancel", json={}, headers=renter).status_code
        == 200
    )
    _, renter2 = make_user(session, Role.RENTER)
    assert (
        client.post("/api/inspection-bookings", json={"slot_id": slot["id"]}, headers=renter2).status_code
        == 201
    )


def test_decline_requires_reason(client, session):
    agent, prop = _prop(client, session)
    slot = _slot(client, agent, prop["id"]).json()
    _, renter = make_user(session, Role.RENTER)
    booking = client.post("/api/inspection-bookings", json={"slot_id": slot["id"]}, headers=renter).json()
    assert (
        client.post(f"/api/inspection-bookings/{booking['id']}/decline", json={}, headers=agent).status_code
        == 422
    )
    r = client.post(
        f"/api/inspection-bookings/{booking['id']}/decline", json={"reason": "Tenant still in"}, headers=agent
    )
    assert r.status_code == 200 and r.json()["status"] == "DECLINED"


def test_renter_sees_only_own_bookings(client, session):
    agent, prop = _prop(client, session)
    s1 = _slot(client, agent, prop["id"], 24, 25).json()
    s2 = _slot(client, agent, prop["id"], 26, 27).json()
    _, r1 = make_user(session, Role.RENTER)
    _, r2 = make_user(session, Role.RENTER)
    b1 = client.post("/api/inspection-bookings", json={"slot_id": s1["id"]}, headers=r1).json()
    client.post("/api/inspection-bookings", json={"slot_id": s2["id"]}, headers=r2)
    assert [b["id"] for b in client.get("/api/inspection-bookings", headers=r1).json()] == [b1["id"]]
    assert client.get(f"/api/inspection-bookings/{b1['id']}", headers=r2).status_code == 404
    assert client.get("/api/inspection-bookings", headers=r1).json()[0]["renter_phone"] is None
