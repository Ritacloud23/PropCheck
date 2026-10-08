from fastapi import APIRouter
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select

from app.deps import CurrentUser, ListerUser, OptionalUser, RenterUser, SessionDep
from app.errors import BadRequest, Conflict, Forbidden, NotFound
from app.models import AgentProfile, InspectionBooking, InspectionSlot, Property, User
from app.models.base import utcnow
from app.models.enums import ACTIVE_BOOKING_STATUSES, BookingStatus, Role, SlotStatus
from app.routers.properties import load_property, require_manager
from app.schemas.common import ReasonIn, RequiredReasonIn
from app.schemas.workflow import BookingIn, BookingOut, SlotIn, SlotOut
from app.services import audit, presenters
from app.services.notifications import notify
from app.services.state_machine import transition
from app.services.workflows import INSPECTION_BOOKING, property_manager_ids

router = APIRouter(tags=["inspections"])


def _booking_out(session, booking: InspectionBooking, viewer: User) -> BookingOut:
    prop = session.get(Property, booking.property_id)
    slot = session.get(InspectionSlot, booking.slot_id)
    is_manager = viewer.id in property_manager_ids(session, prop) or viewer.role in (
        Role.REVIEWER,
        Role.ADMIN,
    )
    renter = session.get(User, booking.renter_id) if is_manager else None
    return BookingOut(
        id=booking.id,  # type: ignore[arg-type]
        property=presenters.property_ref(prop),
        slot_id=booking.slot_id,
        start_time=slot.start_time,
        end_time=slot.end_time,
        status=booking.status,
        renter_note=booking.renter_note,
        landlord_note=booking.landlord_note,
        created_at=booking.created_at,
        confirmed_at=booking.confirmed_at,
        completed_at=booking.completed_at,
        renter_name=renter.full_name if renter else None,
        renter_phone=renter.phone if renter else None,
        allowed_actions=presenters.allowed_actions(INSPECTION_BOOKING, booking.status, viewer),
    )


# ---------------------------------------------------------------- slots


@router.get("/api/properties/{property_id}/inspection-slots", response_model=list[SlotOut])
@router.get("/api/properties/{property_id}/slots", response_model=list[SlotOut], include_in_schema=False)
def list_slots(property_id: int, session: SessionDep, viewer: OptionalUser) -> list[InspectionSlot]:
    """Public: upcoming OPEN slots. Owner / listing agent: every slot."""
    prop = load_property(session, property_id)
    query = select(InspectionSlot).where(InspectionSlot.property_id == prop.id)
    if not presenters.can_manage_property(session, prop, viewer):
        if not prop.is_listed:
            raise NotFound("Property not found.")
        query = query.where(InspectionSlot.status == SlotStatus.OPEN, InspectionSlot.start_time > utcnow())
    return list(session.exec(query.order_by(col(InspectionSlot.start_time))).all())


@router.post("/api/properties/{property_id}/inspection-slots", response_model=SlotOut, status_code=201)
@router.post(
    "/api/properties/{property_id}/slots", response_model=SlotOut, status_code=201, include_in_schema=False
)
def create_slot(property_id: int, body: SlotIn, user: ListerUser, session: SessionDep) -> InspectionSlot:
    prop = load_property(session, property_id)
    require_manager(session, prop, user)
    if body.start_time <= utcnow():
        raise BadRequest("Inspection slots must be in the future.")
    # Friendly pre-check; the EXCLUDE constraint is the real guarantee under concurrency.
    overlap = session.exec(
        select(InspectionSlot).where(
            InspectionSlot.property_id == prop.id,
            InspectionSlot.status != SlotStatus.CANCELLED,
            col(InspectionSlot.start_time) < body.end_time,
            col(InspectionSlot.end_time) > body.start_time,
        )
    ).first()
    if overlap:
        raise Conflict("This slot overlaps an existing inspection slot for the property.")
    slot = InspectionSlot(
        property_id=prop.id,  # type: ignore[arg-type]
        landlord_user_id=user.id,  # type: ignore[arg-type]
        start_time=body.start_time,
        end_time=body.end_time,
    )
    session.add(slot)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise Conflict("This slot overlaps an existing inspection slot for the property.")
    audit.record(
        session, actor_id=user.id, entity_type="InspectionSlot", entity_id=slot.id,  # type: ignore[arg-type]
        action="SLOT_CREATED", to_status=SlotStatus.OPEN.value,
        metadata={"property_id": prop.id, "start_time": body.start_time.isoformat()},
    )  # fmt: skip
    session.commit()
    session.refresh(slot)
    return slot


@router.post("/api/inspection-slots/{slot_id}/cancel", response_model=SlotOut)
def cancel_slot(slot_id: int, user: ListerUser, session: SessionDep) -> InspectionSlot:
    slot = session.exec(select(InspectionSlot).where(InspectionSlot.id == slot_id).with_for_update()).first()
    if not slot:
        raise NotFound("Slot not found.")
    require_manager(session, session.get(Property, slot.property_id), user)  # type: ignore[arg-type]
    if slot.status == SlotStatus.CANCELLED:
        raise Conflict("This slot is already cancelled.")
    active = session.exec(
        select(InspectionBooking).where(
            InspectionBooking.slot_id == slot.id, col(InspectionBooking.status).in_(ACTIVE_BOOKING_STATUSES)
        )
    ).first()
    if active:
        raise Conflict("This slot has an active booking. Decline or cancel the booking first.")
    old = slot.status.value
    slot.status = SlotStatus.CANCELLED
    session.add(slot)
    audit.record(
        session, actor_id=user.id, entity_type="InspectionSlot", entity_id=slot.id,  # type: ignore[arg-type]
        action="SLOT_CANCELLED", from_status=old, to_status=SlotStatus.CANCELLED.value,
    )  # fmt: skip
    session.commit()
    session.refresh(slot)
    return slot


# ---------------------------------------------------------------- bookings


@router.post("/api/inspection-bookings", response_model=BookingOut, status_code=201)
def book_slot(body: BookingIn, user: RenterUser, session: SessionDep) -> BookingOut:
    # Lock the slot row so two renters booking at the same moment are serialised.
    slot = session.exec(
        select(InspectionSlot).where(InspectionSlot.id == body.slot_id).with_for_update()
    ).first()
    if not slot:
        raise NotFound("Slot not found.")
    prop = session.get(Property, slot.property_id)
    if not prop or not prop.is_listed:
        raise NotFound("Slot not found.")
    if slot.status != SlotStatus.OPEN:
        raise Conflict("This slot is no longer available. Please choose another time.")
    if slot.start_time <= utcnow():
        raise Conflict("This slot is in the past.")
    booking = InspectionBooking(
        property_id=prop.id,  # type: ignore[arg-type]
        slot_id=slot.id,  # type: ignore[arg-type]
        renter_id=user.id,  # type: ignore[arg-type]
        renter_note=body.renter_note,
    )
    slot.status = SlotStatus.BOOKED
    session.add(slot)
    session.add(booking)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise Conflict("This slot is no longer available. Please choose another time.")
    audit.record(
        session, actor_id=user.id, entity_type="InspectionBooking", entity_id=booking.id,  # type: ignore[arg-type]
        action="BOOKING_REQUESTED", to_status=BookingStatus.REQUESTED.value,
        metadata={"slot_id": slot.id, "property_id": prop.id},
    )  # fmt: skip
    session.commit()
    session.refresh(booking)
    for manager_id in property_manager_ids(session, prop):
        notify(manager_id, "BOOKING_REQUESTED", f"New inspection request for property {prop.id}")
    return _booking_out(session, booking, user)


@router.get("/api/inspection-bookings", response_model=list[BookingOut])
def list_bookings(
    user: CurrentUser, session: SessionDep, status: BookingStatus | None = None
) -> list[BookingOut]:
    """Renters see their own bookings; agents/landlords see bookings on properties they manage."""
    query = select(InspectionBooking)
    if user.role == Role.RENTER:
        query = query.where(InspectionBooking.renter_id == user.id)
    elif user.role in (Role.AGENT, Role.LANDLORD):
        agent = session.exec(select(AgentProfile).where(AgentProfile.user_id == user.id)).first()
        managed = select(Property.id).where(
            or_(Property.owner_user_id == user.id, Property.listing_agent_id == (agent.id if agent else -1))
        )
        query = query.where(col(InspectionBooking.property_id).in_(managed))
    if status:
        query = query.where(InspectionBooking.status == status)
    rows = session.exec(query.order_by(col(InspectionBooking.created_at).desc()).limit(200)).all()
    return [_booking_out(session, b, user) for b in rows]


def _visible_booking(session, booking_id: int, user: User) -> InspectionBooking:
    booking = session.get(InspectionBooking, booking_id)
    if not booking:
        raise NotFound("Booking not found.")
    if user.role in (Role.REVIEWER, Role.ADMIN):
        return booking
    prop = session.get(Property, booking.property_id)
    if booking.renter_id != user.id and user.id not in property_manager_ids(session, prop):
        raise NotFound("Booking not found.")
    return booking


@router.get("/api/inspection-bookings/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, user: CurrentUser, session: SessionDep) -> BookingOut:
    return _booking_out(session, _visible_booking(session, booking_id, user), user)


def _move(
    session, booking_id: int, user: User, to: BookingStatus, reason: str | None, event: str
) -> BookingOut:
    booking = _visible_booking(session, booking_id, user)
    transition(session, INSPECTION_BOOKING, booking.id, to, user, reason=reason)  # type: ignore[arg-type]
    session.commit()
    session.refresh(booking)
    notify(booking.renter_id, event, f"Inspection booking {booking.id} is now {booking.status.value}")
    return _booking_out(session, booking, user)


@router.post("/api/inspection-bookings/{booking_id}/confirm", response_model=BookingOut)
def confirm_booking(
    booking_id: int, user: CurrentUser, session: SessionDep, body: ReasonIn | None = None
) -> BookingOut:
    return _move(
        session, booking_id, user, BookingStatus.CONFIRMED, body.reason if body else None, "BOOKING_CONFIRMED"
    )


@router.post("/api/inspection-bookings/{booking_id}/decline", response_model=BookingOut)
def decline_booking(
    booking_id: int, body: RequiredReasonIn, user: CurrentUser, session: SessionDep
) -> BookingOut:
    return _move(session, booking_id, user, BookingStatus.DECLINED, body.reason, "BOOKING_DECLINED")


@router.post("/api/inspection-bookings/{booking_id}/complete", response_model=BookingOut)
def complete_booking(booking_id: int, user: CurrentUser, session: SessionDep) -> BookingOut:
    booking = _visible_booking(session, booking_id, user)
    slot = session.get(InspectionSlot, booking.slot_id)
    if slot and slot.start_time > utcnow():
        raise Conflict("An inspection cannot be marked completed before its scheduled start time.")
    return _move(session, booking_id, user, BookingStatus.COMPLETED, None, "BOOKING_COMPLETED")


@router.post("/api/inspection-bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: int, user: CurrentUser, session: SessionDep, body: ReasonIn | None = None
) -> BookingOut:
    if user.role in (Role.REVIEWER, Role.ADMIN):
        raise Forbidden("Reviewers do not cancel inspection bookings.")
    return _move(
        session, booking_id, user, BookingStatus.CANCELLED, body.reason if body else None, "BOOKING_CANCELLED"
    )
