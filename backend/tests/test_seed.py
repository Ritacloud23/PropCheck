from collections import Counter

from sqlmodel import Session, select

import app.seed as seed_module
from app.models import (
    AgentProfile,
    AgentReport,
    AuditLog,
    HouseSearchRequest,
    InspectionBooking,
    Property,
    Reservation,
    User,
    VerificationCase,
)
from app.reference import active_states


def test_demo_seed_covers_every_workflow_state(session, monkeypatch):
    """The demo data gives reviewers something to look at in every queue, using launch states only."""
    monkeypatch.setattr(
        seed_module,
        "Session",
        lambda _engine: Session(bind=session.connection(), join_transaction_mode="create_savepoint"),
    )
    seed_module.seed()

    def count(model, field):
        return Counter(getattr(row, field).value for row in session.exec(select(model)).all())

    roles = count(User, "role")
    assert roles["RENTER"] >= 4 and roles["AGENT"] + roles["LANDLORD"] >= 5
    assert roles["REVIEWER"] == 2 and roles["ADMIN"] == 1

    assert {p.state for p in session.exec(select(Property)).all()} == set(active_states())
    cases = count(VerificationCase, "status")
    assert cases["VERIFIED"] >= 3 and cases["SUBMITTED"] + cases["IN_REVIEW"] >= 2 and cases["REJECTED"] >= 1
    rejected = session.exec(select(VerificationCase).where(VerificationCase.status == "REJECTED")).one()
    assert rejected.rejection_reason

    agents = count(AgentProfile, "verification_status")
    assert agents["VERIFIED"] >= 4 and agents["SUSPENDED"] + agents["REJECTED"] >= 1

    assert set(count(Reservation, "status")) >= {"PENDING_PAYMENT", "PENDING_RELEASE", "RELEASED", "REFUNDED"}
    assert set(count(InspectionBooking, "status")) >= {"REQUESTED", "CONFIRMED"}
    assert set(count(HouseSearchRequest, "status")) >= {"SUBMITTED", "ASSIGNED", "CONTACTED", "CANCELLED"}
    assert set(count(AgentReport, "status")) >= {"OPEN", "RESOLVED", "REJECTED"}

    # Seeded transitions went through the state machine, so they are audited like real ones.
    actions = {a.action for a in session.exec(select(AuditLog)).all()}
    assert {
        "PROPERTY_VERIFIED",
        "KEYS_CONFIRMED_RELEASED",
        "RESERVATION_REFUNDED",
        "REQUEST_ASSIGNED",
    } <= actions
