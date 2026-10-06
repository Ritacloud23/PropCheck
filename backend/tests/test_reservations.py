from sqlmodel import select

from app.models import AuditLog, Property
from app.models.enums import Role
from tests.helpers import create_agent, create_property, make_user, verified_property


def _reserve(client, session):
    world = verified_property(client, session)
    _, renter = make_user(session, Role.RENTER)
    r = client.post(
        "/api/reservations",
        json={"property_id": world["property"]["id"], "accept_terms": True},
        headers=renter,
    )
    assert r.status_code == 201, r.text
    return world, renter, r.json()


def test_reservation_requires_terms_and_verified_property(client, session):
    _, agent, _ = create_agent(client, session)
    prop = create_property(client, agent)
    _, renter = make_user(session, Role.RENTER)
    r = client.post(
        "/api/reservations", json={"property_id": prop["id"], "accept_terms": False}, headers=renter
    )
    assert r.status_code == 422
    r = client.post(
        "/api/reservations", json={"property_id": prop["id"], "accept_terms": True}, headers=renter
    )
    assert r.status_code == 409


def test_pay_then_release_once(client, session):
    world, renter, res = _reserve(client, session)
    assert res["status"] == "PENDING_PAYMENT" and res["is_test_mode"] is True
    assert res["amount"] == 350_000
    terms = client.get("/api/reservations/terms", params={"property_id": world["property"]["id"]}).json()
    assert terms["amount"] == res["amount"] and terms["is_test_mode"] is True
    paid = client.post(f"/api/reservations/{res['id']}/pay", headers=renter).json()
    assert paid["provider"] == "simulated"
    assert paid["reservation"]["status"] == "PENDING_RELEASE"
    assert paid["reservation"]["payment_reference"].startswith("PCK-TEST-")
    assert session.get(Property, world["property"]["id"]).availability_status.value == "RESERVED"

    # Duplicate payment is refused.
    assert client.post(f"/api/reservations/{res['id']}/pay", headers=renter).status_code == 409

    r = client.post(f"/api/reservations/{res['id']}/confirm-keys", headers=renter)
    assert r.status_code == 200 and r.json()["status"] == "RELEASED"
    # Second release and refund-after-release are both refused.
    assert client.post(f"/api/reservations/{res['id']}/confirm-keys", headers=renter).status_code == 409
    r = client.post(
        f"/api/reservations/{res['id']}/refund",
        json={"reason": "Changed mind"},
        headers=world["reviewer_headers"],
    )
    assert r.status_code == 409
    session.expire_all()
    assert session.get(Property, world["property"]["id"]).availability_status.value == "LET"


def test_refund_once_by_reviewer_only(client, session):
    world, renter, res = _reserve(client, session)
    client.post(f"/api/reservations/{res['id']}/pay", headers=renter)
    r = client.post(
        f"/api/reservations/{res['id']}/request-refund", json={"reason": "Keys not given"}, headers=renter
    )
    assert r.status_code == 200 and r.json()["refund_requested_at"]
    assert (
        client.post(
            f"/api/reservations/{res['id']}/refund", json={"reason": "x refund"}, headers=renter
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/reservations/{res['id']}/refund",
            json={"reason": "x refund"},
            headers=world["agent_headers"],
        ).status_code
        == 403
    )
    r = client.post(
        f"/api/reservations/{res['id']}/refund",
        json={"reason": "Keys not handed over"},
        headers=world["reviewer_headers"],
    )
    assert r.status_code == 200 and r.json()["status"] == "REFUNDED"
    assert (
        client.post(
            f"/api/reservations/{res['id']}/refund",
            json={"reason": "again"},
            headers=world["reviewer_headers"],
        ).status_code
        == 409
    )
    assert client.post(f"/api/reservations/{res['id']}/confirm-keys", headers=renter).status_code == 409
    session.expire_all()
    assert session.get(Property, world["property"]["id"]).availability_status.value == "AVAILABLE"
    actions = [
        a.action for a in session.exec(select(AuditLog).where(AuditLog.entity_type == "Reservation")).all()
    ]
    assert {
        "RESERVATION_CREATED",
        "TEST_PAYMENT_CONFIRMED",
        "REFUND_REQUESTED",
        "RESERVATION_REFUNDED",
    } <= set(actions)


def test_second_renter_cannot_pay_for_reserved_property(client, session):
    world, renter, res = _reserve(client, session)
    _, renter2 = make_user(session, Role.RENTER)
    res2 = client.post(
        "/api/reservations",
        json={"property_id": world["property"]["id"], "accept_terms": True},
        headers=renter2,
    ).json()
    client.post(f"/api/reservations/{res['id']}/pay", headers=renter)
    r = client.post(f"/api/reservations/{res2['id']}/pay", headers=renter2)
    assert r.status_code == 409
    assert (
        client.get(f"/api/reservations/{res2['id']}", headers=renter2).json()["status"] == "PENDING_PAYMENT"
    )


def test_other_renter_cannot_touch_reservation(client, session):
    _, renter, res = _reserve(client, session)
    _, intruder = make_user(session, Role.RENTER)
    assert client.get(f"/api/reservations/{res['id']}", headers=intruder).status_code == 404
    assert client.post(f"/api/reservations/{res['id']}/pay", headers=intruder).status_code == 404
    assert client.post(f"/api/reservations/{res['id']}/cancel", json={}, headers=intruder).status_code == 404


def test_cancel_only_before_payment(client, session):
    _, renter, res = _reserve(client, session)
    r = client.post(
        f"/api/reservations/{res['id']}/cancel", json={"reason": "Found another place"}, headers=renter
    )
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert client.post(f"/api/reservations/{res['id']}/pay", headers=renter).status_code == 409
