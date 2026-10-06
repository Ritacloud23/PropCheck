"""TEST/DEMO reservations. Not escrow; no real money moves (see services/payments.py)."""

from fastapi import APIRouter
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select

from app.config import settings
from app.deps import CurrentUser, RenterUser, SessionDep, StaffUser
from app.errors import BadRequest, Conflict, NotFound
from app.models import AgentProfile, Property, Reservation, User
from app.models.base import utcnow
from app.models.enums import AvailabilityStatus, PropertyVerificationState, ReservationStatus, Role
from app.schemas.common import ReasonIn, RequiredReasonIn
from app.schemas.workflow import RESERVATION_TERMS, PayOut, ReservationIn, ReservationOut, VerifyPaymentIn
from app.services import audit, payments, presenters
from app.services.fees import reservation_deposit
from app.services.notifications import notify
from app.services.state_machine import transition
from app.services.workflows import RESERVATION, property_manager_ids

router = APIRouter(prefix="/api/reservations", tags=["reservations"])

LIVE_STATUSES = (ReservationStatus.PENDING_PAYMENT, ReservationStatus.PENDING_RELEASE)


def _out(session, res: Reservation, viewer: User) -> ReservationOut:
    prop = session.get(Property, res.property_id)
    renter = session.get(User, res.renter_id)
    return ReservationOut(
        id=res.id,  # type: ignore[arg-type]
        property=presenters.property_ref(prop),
        renter_id=res.renter_id,
        renter_name=renter.full_name if renter else None,
        amount=res.amount,
        payment_reference=res.payment_reference,
        payment_provider=res.payment_provider,
        status=res.status,
        terms_version=res.terms_version,
        terms=RESERVATION_TERMS,
        created_at=res.created_at,
        paid_at=res.paid_at,
        released_at=res.released_at,
        refunded_at=res.refunded_at,
        refund_requested_at=res.refund_requested_at,
        refund_request_reason=res.refund_request_reason,
        cancellation_reason=res.cancellation_reason,
        allowed_actions=presenters.allowed_actions(RESERVATION, res.status, viewer),
    )


def _visible(session, reservation_id: int, user: User) -> Reservation:
    res = session.get(Reservation, reservation_id)
    if not res:
        raise NotFound("Reservation not found.")
    if user.role in (Role.REVIEWER, Role.ADMIN) or res.renter_id == user.id:
        return res
    if user.id in property_manager_ids(session, session.get(Property, res.property_id)):
        return res
    raise NotFound("Reservation not found.")


@router.get("/terms")
def reservation_terms(session: SessionDep, property_id: int | None = None) -> dict:
    """Demo terms; with `property_id`, also the exact reservation amount for that listing."""
    amount = None
    if property_id is not None:
        prop = session.get(Property, property_id)
        if prop and prop.is_listed:
            amount = reservation_deposit(prop.rent_amount)
    return {
        "terms_version": settings.reservation_terms_version,
        "terms": RESERVATION_TERMS,
        "deposit_percent": settings.reservation_deposit_percent,
        "amount": amount,
        "provider": payments.get_provider().name,
        "is_test_mode": True,
    }


@router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(body: ReservationIn, user: RenterUser, session: SessionDep) -> ReservationOut:
    prop = session.exec(select(Property).where(Property.id == body.property_id).with_for_update()).first()
    if not prop or not prop.is_listed:
        raise NotFound("Property not found.")
    if presenters.effective_property_status(prop) != PropertyVerificationState.VERIFIED:
        raise Conflict("Only currently verified properties can be reserved through PropCheck.")
    if prop.availability_status != AvailabilityStatus.AVAILABLE:
        raise Conflict("This property is not available for reservation.")
    existing = session.exec(
        select(Reservation).where(
            Reservation.property_id == prop.id,
            Reservation.renter_id == user.id,
            col(Reservation.status).in_(LIVE_STATUSES),
        )
    ).first()
    if existing:
        raise Conflict("You already have an active reservation for this property.")
    res = Reservation(
        property_id=prop.id,  # type: ignore[arg-type]
        renter_id=user.id,  # type: ignore[arg-type]
        amount=reservation_deposit(prop.rent_amount),
        terms_version=settings.reservation_terms_version,
    )
    session.add(res)
    session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="Reservation", entity_id=res.id,  # type: ignore[arg-type]
        action="RESERVATION_CREATED", to_status=res.status.value,
        metadata={"property_id": prop.id, "amount": res.amount, "terms_version": res.terms_version, "test_mode": True},
    )  # fmt: skip
    session.commit()
    session.refresh(res)
    return _out(session, res, user)


@router.get("", response_model=list[ReservationOut])
def list_reservations(
    user: CurrentUser, session: SessionDep, status: ReservationStatus | None = None
) -> list[ReservationOut]:
    query = select(Reservation)
    if user.role == Role.RENTER:
        query = query.where(Reservation.renter_id == user.id)
    elif user.role in (Role.AGENT, Role.LANDLORD):
        agent = session.exec(select(AgentProfile).where(AgentProfile.user_id == user.id)).first()
        managed = select(Property.id).where(
            or_(Property.owner_user_id == user.id, Property.listing_agent_id == (agent.id if agent else -1))
        )
        query = query.where(col(Reservation.property_id).in_(managed))
    if status:
        query = query.where(Reservation.status == status)
    rows = session.exec(query.order_by(col(Reservation.created_at).desc()).limit(200)).all()
    return [_out(session, r, user) for r in rows]


@router.get("/{reservation_id}", response_model=ReservationOut)
def get_reservation(reservation_id: int, user: CurrentUser, session: SessionDep) -> ReservationOut:
    return _out(session, _visible(session, reservation_id, user), user)


def _confirm_payment(session, res: Reservation, user: User, result: payments.PaymentResult) -> None:
    """Move PENDING_PAYMENT -> PENDING_RELEASE. Row lock + state machine make this happen at most once."""
    if not result.success:
        raise BadRequest("The test payment could not be verified.")
    prop = session.exec(select(Property).where(Property.id == res.property_id).with_for_update()).one()
    if prop.availability_status != AvailabilityStatus.AVAILABLE:
        raise Conflict("This property has just been reserved by someone else. No payment was taken.")
    transition(
        session, RESERVATION, res.id, ReservationStatus.PENDING_RELEASE, user,
        metadata={"payment_reference": result.reference, "payment_provider": result.provider, "test_mode": True},
    )  # fmt: skip


@router.post("/{reservation_id}/pay", response_model=PayOut)
def pay(reservation_id: int, user: RenterUser, session: SessionDep) -> PayOut:
    """Start a TEST payment. The simulated provider confirms immediately; Paystack test mode returns a checkout URL."""
    res = session.exec(select(Reservation).where(Reservation.id == reservation_id).with_for_update()).first()
    if not res or res.renter_id != user.id:
        raise NotFound("Reservation not found.")
    if res.status != ReservationStatus.PENDING_PAYMENT:
        raise Conflict(f"This reservation is already {res.status.value}; it cannot be paid again.")
    provider = payments.get_provider()
    init = provider.initialize(email=user.email, amount_naira=res.amount, reservation_id=res.id)  # type: ignore[arg-type]
    authorization_url = init.authorization_url
    if authorization_url is None:
        _confirm_payment(session, res, user, provider.verify(init.reference))
    else:
        res.payment_reference = init.reference
        res.payment_provider = provider.name
        session.add(res)
        audit.record(
            session, actor_id=user.id, entity_type="Reservation", entity_id=res.id,  # type: ignore[arg-type]
            action="TEST_PAYMENT_STARTED", metadata={"payment_reference": init.reference, "provider": provider.name},
        )  # fmt: skip
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise Conflict("Duplicate payment reference.")
    session.refresh(res)
    if res.status == ReservationStatus.PENDING_RELEASE:
        notify(res.renter_id, "TEST_PAYMENT_CONFIRMED", f"Reservation {res.id} test payment confirmed")
    return PayOut(
        reservation=_out(session, res, user), authorization_url=authorization_url, provider=provider.name
    )


@router.post("/{reservation_id}/verify-payment", response_model=ReservationOut)
def verify_payment(
    reservation_id: int, body: VerifyPaymentIn, user: RenterUser, session: SessionDep
) -> ReservationOut:
    """Called after returning from Paystack TEST checkout. Idempotent per reference."""
    res = session.exec(select(Reservation).where(Reservation.id == reservation_id).with_for_update()).first()
    if not res or res.renter_id != user.id:
        raise NotFound("Reservation not found.")
    if res.status != ReservationStatus.PENDING_PAYMENT:
        raise Conflict(f"This reservation is already {res.status.value}.")
    if res.payment_reference and res.payment_reference != body.reference:
        raise BadRequest("Payment reference does not match this reservation.")
    _confirm_payment(session, res, user, payments.get_provider().verify(body.reference))
    session.commit()
    session.refresh(res)
    return _out(session, res, user)


@router.post("/{reservation_id}/confirm-keys", response_model=ReservationOut)
def confirm_keys(reservation_id: int, user: RenterUser, session: SessionDep) -> ReservationOut:
    """Renter confirms they received the keys. Releases the demo reservation (one time only)."""
    res = _visible(session, reservation_id, user)
    transition(session, RESERVATION, res.id, ReservationStatus.RELEASED, user)  # type: ignore[arg-type]
    session.commit()
    session.refresh(res)
    return _out(session, res, user)


@router.post("/{reservation_id}/request-refund", response_model=ReservationOut)
def request_refund(
    reservation_id: int, body: RequiredReasonIn, user: RenterUser, session: SessionDep
) -> ReservationOut:
    """Ask a reviewer to refund. The status stays PENDING_RELEASE until a reviewer decides."""
    res = session.exec(select(Reservation).where(Reservation.id == reservation_id).with_for_update()).first()
    if not res or res.renter_id != user.id:
        raise NotFound("Reservation not found.")
    if res.status != ReservationStatus.PENDING_RELEASE:
        raise Conflict("A refund can only be requested while the reservation is PENDING_RELEASE.")
    if res.refund_requested_at:
        raise Conflict("A refund has already been requested for this reservation.")
    res.refund_requested_at = utcnow()
    res.refund_request_reason = body.reason
    session.add(res)
    audit.record(
        session, actor_id=user.id, entity_type="Reservation", entity_id=res.id,  # type: ignore[arg-type]
        action="REFUND_REQUESTED", reason=body.reason,
    )  # fmt: skip
    session.commit()
    session.refresh(res)
    return _out(session, res, user)


@router.post("/{reservation_id}/refund", response_model=ReservationOut)
def refund(
    reservation_id: int, body: RequiredReasonIn, user: StaffUser, session: SessionDep
) -> ReservationOut:
    res = _visible(session, reservation_id, user)
    transition(session, RESERVATION, res.id, ReservationStatus.REFUNDED, user, reason=body.reason)  # type: ignore[arg-type]
    session.commit()
    session.refresh(res)
    notify(res.renter_id, "RESERVATION_REFUNDED", f"Reservation {res.id} was refunded (test mode)")
    return _out(session, res, user)


@router.post("/{reservation_id}/cancel", response_model=ReservationOut)
def cancel(
    reservation_id: int, user: CurrentUser, session: SessionDep, body: ReasonIn | None = None
) -> ReservationOut:
    res = _visible(session, reservation_id, user)
    transition(
        session,
        RESERVATION,
        res.id,
        ReservationStatus.CANCELLED,
        user,
        reason=body.reason if body else None,  # type: ignore[arg-type]
    )
    session.commit()
    session.refresh(res)
    return _out(session, res, user)
