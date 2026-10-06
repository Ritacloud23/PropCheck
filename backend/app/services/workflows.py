"""Transition tables, guards and side effects for every PropCheck workflow."""

from datetime import datetime, timedelta

from sqlmodel import select

from app.config import settings
from app.errors import BadRequest, Forbidden
from app.models import (
    AgentProfile,
    AgentReport,
    AgentVerification,
    HouseSearchRequest,
    InspectionBooking,
    InspectionSlot,
    PlaceReport,
    Property,
    Reservation,
    VerificationCase,
    VerificationCheck,
)
from app.models.base import utcnow
from app.models.enums import (
    MANDATORY_CHECKS,
    AgentVerificationStatus,
    AvailabilityStatus,
    BookingStatus,
    CheckResult,
    HouseSearchStatus,
    PropertyVerificationState,
    ReportStatus,
    ReservationStatus,
    Role,
    SlotStatus,
    VerificationStatus,
)
from app.services import audit
from app.services.state_machine import Rule, StateMachine, TransitionContext

STAFF = frozenset({Role.REVIEWER, Role.ADMIN})
LISTERS = frozenset({Role.AGENT, Role.LANDLORD})
RENTER = frozenset({Role.RENTER})


# ---------------------------------------------------------------- shared helpers


def property_manager_ids(session, prop: Property) -> set[int]:
    """User ids allowed to manage a property: the owner and the listing agent's user."""
    ids = {prop.owner_user_id}
    if prop.listing_agent_id:
        agent = session.get(AgentProfile, prop.listing_agent_id)
        if agent:
            ids.add(agent.user_id)
    return ids


def _set_property_availability(ctx: TransitionContext, prop: Property, status: AvailabilityStatus) -> None:
    if prop.availability_status == status:
        return
    old = prop.availability_status
    prop.availability_status = status
    ctx.session.add(prop)
    audit.record(
        ctx.session,
        actor_id=ctx.actor_id,
        entity_type="Property",
        entity_id=prop.id,  # type: ignore[arg-type]
        action="AVAILABILITY_CHANGED",
        from_status=old.value,
        to_status=status.value,
        reason=f"Reservation {ctx.entity.id} moved to {ctx.to_status}",
    )


# ---------------------------------------------------------------- property verification cases


def _case_property(ctx: TransitionContext) -> Property:
    return ctx.session.get(Property, ctx.entity.property_id)  # type: ignore[return-value]


def _guard_case_submitter(ctx: TransitionContext) -> None:
    prop = _case_property(ctx)
    if ctx.actor_id not in property_manager_ids(ctx.session, prop):
        raise Forbidden("Only the property owner or listing agent can submit this case.")


def _guard_case_no_conflict(ctx: TransitionContext) -> None:
    """A reviewer must never decide a case they submitted or a property they own or list."""
    prop = _case_property(ctx)
    conflicted = {ctx.entity.submitted_by} | property_manager_ids(ctx.session, prop)
    if ctx.actor_id in conflicted:
        raise Forbidden(
            "Conflict of interest: you cannot review a case you submitted or a property you manage."
        )


def _guard_checks_complete(ctx: TransitionContext) -> None:
    checks = ctx.session.exec(
        select(VerificationCheck).where(VerificationCheck.verification_case_id == ctx.entity.id)
    ).all()
    by_type = {c.check_type: c.result for c in checks}
    problems = []
    for check in checks:
        if check.result in (CheckResult.NOT_STARTED, CheckResult.FAILED):
            problems.append(f"{check.check_type.value} is {check.result.value}")
    for mandatory in MANDATORY_CHECKS:
        if by_type.get(mandatory) != CheckResult.PASSED:
            problems.append(f"{mandatory.value} must be PASSED")
    if problems:
        raise BadRequest("Checklist incomplete, cannot verify: " + "; ".join(sorted(set(problems))))


def _parse_dt(value) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _on_case_apply(ctx: TransitionContext) -> None:
    case: VerificationCase = ctx.entity
    now = utcnow()
    to = ctx.to_status
    if to == VerificationStatus.SUBMITTED:
        case.submitted_at = now
    elif to == VerificationStatus.IN_REVIEW:
        if case.assigned_reviewer_id is None and ctx.actor_id:
            case.assigned_reviewer_id = ctx.actor_id
    elif to == VerificationStatus.INSPECTION_BOOKED:
        case.inspection_booked_at = now
        case.inspection_scheduled_for = _parse_dt(ctx.metadata.get("inspection_scheduled_for"))
    elif to == VerificationStatus.VERIFIED:
        case.verified_at = now
        case.inspected_at = _parse_dt(ctx.metadata.get("inspected_at")) or case.inspected_at or now
        expires = _parse_dt(ctx.metadata.get("expires_at"))
        if expires is None:
            expires = now + timedelta(days=settings.property_verification_days)
        if expires <= now:
            raise BadRequest("Verification expiry must be in the future.")
        if expires > now + timedelta(days=366):
            raise BadRequest("Verification expiry cannot be more than 12 months away.")
        case.expires_at = expires
        ctx.metadata["expires_at"] = expires.isoformat()
    elif to == VerificationStatus.REJECTED:
        case.rejection_reason = ctx.reason
    if ctx.metadata.get("reviewer_notes"):
        case.reviewer_notes = str(ctx.metadata["reviewer_notes"])

    prop = _case_property(ctx)
    prop.verification_status = PropertyVerificationState(to)
    prop.verification_expires_at = case.expires_at if to == VerificationStatus.VERIFIED else None
    ctx.session.add(prop)


_review = (_guard_case_no_conflict,)
VERIFICATION_CASE = StateMachine(
    entity_type="VerificationCase",
    model=VerificationCase,
    on_apply=_on_case_apply,
    transitions={
        ("DRAFT", "SUBMITTED"): Rule(LISTERS, (_guard_case_submitter,), action="CASE_SUBMITTED"),
        ("SUBMITTED", "IN_REVIEW"): Rule(STAFF, _review, action="REVIEW_STARTED"),
        ("IN_REVIEW", "INSPECTION_BOOKED"): Rule(STAFF, _review, action="INSPECTION_BOOKED"),
        ("IN_REVIEW", "VERIFIED"): Rule(
            STAFF, _review + (_guard_checks_complete,), action="PROPERTY_VERIFIED"
        ),
        ("IN_REVIEW", "REJECTED"): Rule(STAFF, _review, reason_required=True, action="PROPERTY_REJECTED"),
        ("INSPECTION_BOOKED", "VERIFIED"): Rule(
            STAFF, _review + (_guard_checks_complete,), action="PROPERTY_VERIFIED"
        ),
        ("INSPECTION_BOOKED", "REJECTED"): Rule(
            STAFF, _review, reason_required=True, action="PROPERTY_REJECTED"
        ),
        ("VERIFIED", "EXPIRED"): Rule(STAFF, action="VERIFICATION_EXPIRED"),
    },
)


# ---------------------------------------------------------------- agent verification


def _application_profile(ctx: TransitionContext) -> AgentProfile:
    return ctx.session.get(AgentProfile, ctx.entity.agent_profile_id)  # type: ignore[return-value]


def _guard_agent_owner(ctx: TransitionContext) -> None:
    if _application_profile(ctx).user_id != ctx.actor_id:
        raise Forbidden("You can only submit your own verification application.")


def _guard_agent_no_conflict(ctx: TransitionContext) -> None:
    profile = _application_profile(ctx)
    if ctx.actor_id in (profile.user_id, ctx.entity.submitted_by):
        raise Forbidden("Conflict of interest: you cannot review your own agent application.")


def _on_agent_apply(ctx: TransitionContext) -> None:
    app: AgentVerification = ctx.entity
    profile = _application_profile(ctx)
    now = utcnow()
    to = ctx.to_status
    if to == AgentVerificationStatus.SUBMITTED:
        app.submitted_at = now
    elif to == AgentVerificationStatus.IN_REVIEW:
        app.assigned_reviewer_id = app.assigned_reviewer_id or ctx.actor_id
    elif to == AgentVerificationStatus.VERIFIED:
        app.verified_at = now
        expires = _parse_dt(ctx.metadata.get("expires_at")) or now + timedelta(
            days=settings.agent_verification_days
        )
        if expires <= now:
            raise BadRequest("Verification expiry must be in the future.")
        app.expires_at = expires
        ctx.metadata["expires_at"] = expires.isoformat()
    elif to == AgentVerificationStatus.REJECTED:
        app.rejection_reason = ctx.reason
    if ctx.metadata.get("reviewer_notes"):
        app.reviewer_notes = str(ctx.metadata["reviewer_notes"])

    profile.verification_status = AgentVerificationStatus(to)
    if to == AgentVerificationStatus.VERIFIED:
        profile.verification_date = app.verified_at
        profile.verification_expiry_date = app.expires_at
    ctx.session.add(profile)


AGENT_VERIFICATION = StateMachine(
    entity_type="AgentVerification",
    model=AgentVerification,
    on_apply=_on_agent_apply,
    transitions={
        ("DRAFT", "SUBMITTED"): Rule(LISTERS, (_guard_agent_owner,), action="AGENT_APPLICATION_SUBMITTED"),
        ("SUBMITTED", "IN_REVIEW"): Rule(STAFF, (_guard_agent_no_conflict,), action="AGENT_REVIEW_STARTED"),
        ("IN_REVIEW", "VERIFIED"): Rule(STAFF, (_guard_agent_no_conflict,), action="AGENT_VERIFIED"),
        ("IN_REVIEW", "REJECTED"): Rule(
            STAFF, (_guard_agent_no_conflict,), reason_required=True, action="AGENT_REJECTED"
        ),
        ("VERIFIED", "EXPIRED"): Rule(STAFF, action="AGENT_VERIFICATION_EXPIRED"),
        ("VERIFIED", "SUSPENDED"): Rule(
            STAFF, (_guard_agent_no_conflict,), reason_required=True, action="AGENT_SUSPENDED"
        ),
        ("SUSPENDED", "IN_REVIEW"): Rule(
            STAFF, (_guard_agent_no_conflict,), action="AGENT_REINSTATEMENT_REVIEW"
        ),
    },
)


# ---------------------------------------------------------------- inspection bookings


def _booking_property(ctx: TransitionContext) -> Property:
    return ctx.session.get(Property, ctx.entity.property_id)  # type: ignore[return-value]


def _guard_booking_manager(ctx: TransitionContext) -> None:
    if ctx.actor_id not in property_manager_ids(ctx.session, _booking_property(ctx)):
        raise Forbidden("Only the property owner or listing agent can manage this booking.")


def _guard_booking_cancel(ctx: TransitionContext) -> None:
    if ctx.actor and ctx.actor.role == Role.RENTER:
        if ctx.entity.renter_id != ctx.actor_id:
            raise Forbidden("You can only cancel your own bookings.")
        return
    _guard_booking_manager(ctx)


def _on_booking_apply(ctx: TransitionContext) -> None:
    booking: InspectionBooking = ctx.entity
    now = utcnow()
    to = ctx.to_status
    if to == BookingStatus.CONFIRMED:
        booking.confirmed_at = now
    elif to == BookingStatus.COMPLETED:
        booking.completed_at = now
    elif to in (BookingStatus.DECLINED, BookingStatus.CANCELLED):
        if to == BookingStatus.DECLINED or (ctx.actor and ctx.actor.role != Role.RENTER):
            booking.landlord_note = ctx.reason or booking.landlord_note
        if to == BookingStatus.CANCELLED:
            booking.cancelled_at = now
        slot = ctx.session.get(InspectionSlot, booking.slot_id)
        if slot and slot.status == SlotStatus.BOOKED:
            slot.status = SlotStatus.OPEN
            ctx.session.add(slot)
    if ctx.metadata.get("landlord_note"):
        booking.landlord_note = str(ctx.metadata["landlord_note"])


INSPECTION_BOOKING = StateMachine(
    entity_type="InspectionBooking",
    model=InspectionBooking,
    on_apply=_on_booking_apply,
    transitions={
        ("REQUESTED", "CONFIRMED"): Rule(LISTERS, (_guard_booking_manager,), action="BOOKING_CONFIRMED"),
        ("REQUESTED", "DECLINED"): Rule(
            LISTERS, (_guard_booking_manager,), reason_required=True, action="BOOKING_DECLINED"
        ),
        ("CONFIRMED", "COMPLETED"): Rule(LISTERS, (_guard_booking_manager,), action="BOOKING_COMPLETED"),
        ("REQUESTED", "CANCELLED"): Rule(
            RENTER | LISTERS, (_guard_booking_cancel,), action="BOOKING_CANCELLED"
        ),
        ("CONFIRMED", "CANCELLED"): Rule(
            RENTER | LISTERS, (_guard_booking_cancel,), action="BOOKING_CANCELLED"
        ),
    },
)


# ---------------------------------------------------------------- reservations (TEST/DEMO only)


def _guard_reservation_renter(ctx: TransitionContext) -> None:
    if ctx.entity.renter_id != ctx.actor_id:
        raise Forbidden("Only the renter who made this reservation can do this.")


def _guard_reservation_cancel(ctx: TransitionContext) -> None:
    if ctx.actor and ctx.actor.role in STAFF:
        return
    _guard_reservation_renter(ctx)


def _on_reservation_apply(ctx: TransitionContext) -> None:
    res: Reservation = ctx.entity
    now = utcnow()
    prop = ctx.session.get(Property, res.property_id)
    to = ctx.to_status
    if to == ReservationStatus.PENDING_RELEASE:
        res.paid_at = now
        res.payment_reference = ctx.metadata["payment_reference"]
        res.payment_provider = ctx.metadata.get("payment_provider")
        _set_property_availability(ctx, prop, AvailabilityStatus.RESERVED)  # type: ignore[arg-type]
    elif to == ReservationStatus.RELEASED:
        res.released_at = now
        _set_property_availability(ctx, prop, AvailabilityStatus.LET)  # type: ignore[arg-type]
    elif to == ReservationStatus.REFUNDED:
        res.refunded_at = now
        _set_property_availability(ctx, prop, AvailabilityStatus.AVAILABLE)  # type: ignore[arg-type]
    elif to == ReservationStatus.CANCELLED:
        res.cancellation_reason = ctx.reason


RESERVATION = StateMachine(
    entity_type="Reservation",
    model=Reservation,
    on_apply=_on_reservation_apply,
    transitions={
        ("PENDING_PAYMENT", "PENDING_RELEASE"): Rule(
            RENTER, (_guard_reservation_renter,), action="TEST_PAYMENT_CONFIRMED"
        ),
        ("PENDING_RELEASE", "RELEASED"): Rule(
            RENTER, (_guard_reservation_renter,), action="KEYS_CONFIRMED_RELEASED"
        ),
        ("PENDING_RELEASE", "REFUNDED"): Rule(STAFF, reason_required=True, action="RESERVATION_REFUNDED"),
        ("PENDING_PAYMENT", "CANCELLED"): Rule(
            RENTER | STAFF, (_guard_reservation_cancel,), action="RESERVATION_CANCELLED"
        ),
    },
)


# ---------------------------------------------------------------- house-search requests


def _guard_request_owner_or_staff(ctx: TransitionContext) -> None:
    if ctx.actor and ctx.actor.role in STAFF:
        return
    if ctx.entity.renter_id != ctx.actor_id:
        raise Forbidden("You can only change your own house-search request.")


def _guard_assigned_agent_or_staff(ctx: TransitionContext) -> None:
    if ctx.actor and ctx.actor.role in STAFF:
        return
    agent = ctx.session.exec(select(AgentProfile).where(AgentProfile.user_id == ctx.actor_id)).first()
    if agent is None or agent.id != ctx.entity.assigned_agent_id:
        raise Forbidden("Only the assigned agent can update this request.")


def _guard_complete(ctx: TransitionContext) -> None:
    if ctx.actor and ctx.actor.role == Role.RENTER:
        _guard_request_owner_or_staff(ctx)
    else:
        _guard_assigned_agent_or_staff(ctx)


def _on_request_apply(ctx: TransitionContext) -> None:
    req: HouseSearchRequest = ctx.entity
    if ctx.to_status == HouseSearchStatus.ASSIGNED:
        req.assigned_agent_id = int(ctx.metadata["agent_id"])
    elif ctx.to_status == HouseSearchStatus.CANCELLED:
        req.cancellation_reason = ctx.reason


HOUSE_SEARCH = StateMachine(
    entity_type="HouseSearchRequest",
    model=HouseSearchRequest,
    on_apply=_on_request_apply,
    transitions={
        ("SUBMITTED", "MATCHING"): Rule(STAFF, action="REQUEST_MATCHING"),
        ("MATCHING", "ASSIGNED"): Rule(STAFF, action="REQUEST_ASSIGNED"),
        ("ASSIGNED", "CONTACTED"): Rule(
            frozenset({Role.AGENT}) | STAFF, (_guard_assigned_agent_or_staff,), action="RENTER_CONTACTED"
        ),
        ("CONTACTED", "COMPLETED"): Rule(
            RENTER | frozenset({Role.AGENT}) | STAFF, (_guard_complete,), action="REQUEST_COMPLETED"
        ),
        ("SUBMITTED", "CANCELLED"): Rule(
            RENTER | STAFF, (_guard_request_owner_or_staff,), action="REQUEST_CANCELLED"
        ),
        ("MATCHING", "CANCELLED"): Rule(
            RENTER | STAFF, (_guard_request_owner_or_staff,), action="REQUEST_CANCELLED"
        ),
        ("ASSIGNED", "CANCELLED"): Rule(
            RENTER | STAFF, (_guard_request_owner_or_staff,), action="REQUEST_CANCELLED"
        ),
    },
)


# ---------------------------------------------------------------- reports


def _on_report_apply(ctx: TransitionContext) -> None:
    report: AgentReport = ctx.entity
    if ctx.to_status in (ReportStatus.RESOLVED, ReportStatus.REJECTED):
        report.resolved_at = utcnow()
        report.resolution_reason = ctx.reason
    if ctx.metadata.get("reviewer_notes"):
        report.reviewer_notes = str(ctx.metadata["reviewer_notes"])


AGENT_REPORT = StateMachine(
    entity_type="AgentReport",
    model=AgentReport,
    on_apply=_on_report_apply,
    transitions={
        ("OPEN", "IN_REVIEW"): Rule(STAFF, action="REPORT_REVIEW_STARTED"),
        ("OPEN", "RESOLVED"): Rule(STAFF, reason_required=True, action="REPORT_RESOLVED"),
        ("OPEN", "REJECTED"): Rule(STAFF, reason_required=True, action="REPORT_REJECTED"),
        ("IN_REVIEW", "RESOLVED"): Rule(STAFF, reason_required=True, action="REPORT_RESOLVED"),
        ("IN_REVIEW", "REJECTED"): Rule(STAFF, reason_required=True, action="REPORT_REJECTED"),
    },
)


# ---------------------------------------------------------------- nearby-place reports


def _on_place_report_apply(ctx: TransitionContext) -> None:
    report: PlaceReport = ctx.entity
    report.resolved_at = utcnow()
    if ctx.metadata.get("reviewer_notes"):
        report.reviewer_notes = str(ctx.metadata["reviewer_notes"])


PLACE_REPORT = StateMachine(
    entity_type="PlaceReport",
    model=PlaceReport,
    on_apply=_on_place_report_apply,
    transitions={
        ("OPEN", "RESOLVED"): Rule(STAFF, reason_required=True, action="PLACE_REPORT_RESOLVED"),
        ("OPEN", "REJECTED"): Rule(STAFF, reason_required=True, action="PLACE_REPORT_REJECTED"),
    },
)
