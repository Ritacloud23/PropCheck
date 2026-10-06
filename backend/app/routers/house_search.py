from fastapi import APIRouter, Query
from sqlalchemy import or_
from sqlmodel import col, select

from app.deps import AgentUser, CurrentUser, RenterUser, SessionDep, StaffUser
from app.errors import BadRequest, Conflict, NotFound
from app.models import AgentEnquiry, AgentProfile, HouseSearchRequest, User
from app.models.base import utcnow
from app.models.enums import (
    AgentVerificationStatus,
    EnquiryStatus,
    HouseSearchStatus,
    Purpose,
    Role,
    ServiceType,
)
from app.schemas.agents import AgentPublicOut
from app.schemas.common import ReasonIn
from app.schemas.workflow import (
    AgentEnquiryOut,
    AssignIn,
    EnquiryOut,
    HouseSearchIn,
    HouseSearchOut,
    RespondIn,
)
from app.services import audit, presenters
from app.services.notifications import notify
from app.services.state_machine import transition
from app.services.workflows import HOUSE_SEARCH

router = APIRouter(tags=["house-search"])


def _own_agent(session, user: User) -> AgentProfile | None:
    return session.exec(select(AgentProfile).where(AgentProfile.user_id == user.id)).first()


def _enquiries(session, request_id: int) -> list[EnquiryOut]:
    rows = session.exec(
        select(AgentEnquiry, AgentProfile, User)
        .join(AgentProfile, AgentProfile.id == AgentEnquiry.agent_id)  # type: ignore[arg-type]
        .join(User, User.id == AgentProfile.user_id)  # type: ignore[arg-type]
        .where(AgentEnquiry.house_search_request_id == request_id)
        .order_by(col(AgentEnquiry.id))
    ).all()
    return [
        EnquiryOut(
            id=e.id,  # type: ignore[arg-type]
            house_search_request_id=e.house_search_request_id,
            agent_id=e.agent_id,
            agent_name=u.full_name,
            message=e.message,
            status=e.status,
            created_at=e.created_at,
            responded_at=e.responded_at,
        )
        for e, _, u in rows
    ]


def _out(session, req: HouseSearchRequest, viewer: User) -> HouseSearchOut:
    assigned: AgentPublicOut | None = None
    if req.assigned_agent_id:
        profile = session.get(AgentProfile, req.assigned_agent_id)
        if profile:
            stats = presenters.agent_stats(session, [profile.id]).get(profile.id, (0, 0))
            # The renter asked for help, so the assigned agent's contact details are shared with them.
            reveal = viewer.id == req.renter_id or viewer.role in (Role.REVIEWER, Role.ADMIN)
            assigned = presenters.agent_public(
                profile, session.get(User, profile.user_id), stats, reveal_contact=reveal
            )
    data = req.model_dump()
    return HouseSearchOut(
        **data,
        assigned_agent=assigned,
        enquiries=_enquiries(session, req.id),  # type: ignore[arg-type]
        allowed_actions=presenters.allowed_actions(HOUSE_SEARCH, req.status, viewer),
    )


def _visible(session, request_id: int, user: User) -> HouseSearchRequest:
    req = session.get(HouseSearchRequest, request_id)
    if not req:
        raise NotFound("Request not found.")
    if user.role in (Role.REVIEWER, Role.ADMIN) or req.renter_id == user.id:
        return req
    agent = _own_agent(session, user)
    if agent and req.assigned_agent_id == agent.id:
        return req
    raise NotFound("Request not found.")


# ---------------------------------------------------------------- renter


@router.post("/api/house-search-requests", response_model=HouseSearchOut, status_code=201)
def create_request(body: HouseSearchIn, user: RenterUser, session: SessionDep) -> HouseSearchOut:
    """'I need help finding a house.' Shared only with the agent PropCheck assigns (consent required)."""
    open_count = len(
        session.exec(
            select(HouseSearchRequest.id).where(
                HouseSearchRequest.renter_id == user.id,
                col(HouseSearchRequest.status).in_(
                    [HouseSearchStatus.SUBMITTED, HouseSearchStatus.MATCHING, HouseSearchStatus.ASSIGNED]
                ),
            )
        ).all()
    )
    if open_count >= 3:
        raise Conflict("You already have 3 open requests. Cancel or complete one before submitting another.")
    req = HouseSearchRequest(**body.model_dump(), renter_id=user.id)  # type: ignore[arg-type]
    session.add(req)
    session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="HouseSearchRequest", entity_id=req.id,  # type: ignore[arg-type]
        action="REQUEST_SUBMITTED", to_status=req.status.value,
        metadata={"state": req.state, "city": req.city, "consent_to_share": True},
    )  # fmt: skip
    session.commit()
    session.refresh(req)
    return _out(session, req, user)


@router.get("/api/house-search-requests", response_model=list[HouseSearchOut])
def list_requests(
    user: CurrentUser,
    session: SessionDep,
    status: HouseSearchStatus | None = None,
    state: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[HouseSearchOut]:
    query = select(HouseSearchRequest)
    if user.role == Role.RENTER:
        query = query.where(HouseSearchRequest.renter_id == user.id)
    elif user.role == Role.AGENT:
        agent = _own_agent(session, user)
        query = query.where(HouseSearchRequest.assigned_agent_id == (agent.id if agent else -1))
    elif user.role == Role.LANDLORD:
        return []
    if status:
        query = query.where(HouseSearchRequest.status == status)
    if state:
        query = query.where(HouseSearchRequest.state == state)
    rows = session.exec(query.order_by(col(HouseSearchRequest.created_at).desc()).limit(limit)).all()
    return [_out(session, r, user) for r in rows]


@router.get("/api/house-search-requests/{request_id}", response_model=HouseSearchOut)
def get_request(request_id: int, user: CurrentUser, session: SessionDep) -> HouseSearchOut:
    return _out(session, _visible(session, request_id, user), user)


def _move(session, request_id: int, user: User, to: HouseSearchStatus, reason: str | None = None, **meta):
    req = _visible(session, request_id, user)
    transition(session, HOUSE_SEARCH, req.id, to, user, reason=reason, metadata=meta)  # type: ignore[arg-type]
    return req


@router.post("/api/house-search-requests/{request_id}/cancel", response_model=HouseSearchOut)
def cancel_request(
    request_id: int, user: CurrentUser, session: SessionDep, body: ReasonIn | None = None
) -> HouseSearchOut:
    req = _move(session, request_id, user, HouseSearchStatus.CANCELLED, body.reason if body else None)
    for enquiry in session.exec(
        select(AgentEnquiry).where(
            AgentEnquiry.house_search_request_id == req.id, AgentEnquiry.status != EnquiryStatus.CLOSED
        )
    ).all():
        enquiry.status = EnquiryStatus.CLOSED
        session.add(enquiry)
    session.commit()
    session.refresh(req)
    return _out(session, req, user)


@router.post("/api/house-search-requests/{request_id}/complete", response_model=HouseSearchOut)
def complete_request(request_id: int, user: CurrentUser, session: SessionDep) -> HouseSearchOut:
    req = _move(session, request_id, user, HouseSearchStatus.COMPLETED)
    if req.assigned_agent_id:
        profile = session.get(AgentProfile, req.assigned_agent_id)
        if profile:
            profile.completed_connections += 1
            session.add(profile)
    session.commit()
    session.refresh(req)
    return _out(session, req, user)


# ---------------------------------------------------------------- reviewer: matching & assignment


@router.get("/api/house-search-requests/{request_id}/candidate-agents", response_model=list[AgentPublicOut])
def candidate_agents(request_id: int, user: StaffUser, session: SessionDep) -> list[AgentPublicOut]:
    """Verified agents whose coverage matches the request, best matches first (manual matching aid)."""
    req = _visible(session, request_id, user)
    service = ServiceType.SALES if req.purpose == Purpose.PURCHASE else ServiceType.RENTAL
    rows = session.exec(
        select(AgentProfile, User)
        .join(User, User.id == AgentProfile.user_id)  # type: ignore[arg-type]
        .where(
            AgentProfile.verification_status == AgentVerificationStatus.VERIFIED,
            col(AgentProfile.verification_expiry_date) > utcnow(),
            col(AgentProfile.states_covered).contains([req.state]),
            User.is_active == True,  # noqa: E712
            User.id != req.renter_id,
            or_(col(AgentProfile.budget_max).is_(None), col(AgentProfile.budget_max) >= req.budget_min),
        )
    ).all()

    def score(row) -> tuple:
        p, _ = row
        return (
            req.city in p.cities_covered or (req.area or "") in p.cities_covered,
            req.property_type.value in p.property_types,
            service.value in p.service_types,
            p.years_experience,
        )

    ranked = sorted(rows, key=score, reverse=True)[:20]
    stats = presenters.agent_stats(session, [p.id for p, _ in ranked])  # type: ignore[misc]
    return [presenters.agent_public(p, u, stats.get(p.id, (0, 0)), reveal_contact=True) for p, u in ranked]  # type: ignore[arg-type]


@router.post("/api/house-search-requests/{request_id}/matching", response_model=HouseSearchOut)
def start_matching(request_id: int, user: StaffUser, session: SessionDep) -> HouseSearchOut:
    req = _move(session, request_id, user, HouseSearchStatus.MATCHING)
    session.commit()
    session.refresh(req)
    return _out(session, req, user)


@router.post("/api/house-search-requests/{request_id}/assign", response_model=HouseSearchOut)
def assign_agent(request_id: int, body: AssignIn, user: StaffUser, session: SessionDep) -> HouseSearchOut:
    """Assign a currently verified agent. A SUBMITTED request moves through MATCHING automatically."""
    req = _visible(session, request_id, user)
    agent = session.get(AgentProfile, body.agent_id)
    if not agent or presenters.effective_agent_status(agent) != AgentVerificationStatus.VERIFIED:
        raise BadRequest("Requests can only be assigned to a currently verified agent.")
    if agent.user_id == req.renter_id:
        raise BadRequest("A request cannot be assigned to the renter's own agent profile.")
    if req.status == HouseSearchStatus.SUBMITTED:
        transition(session, HOUSE_SEARCH, req.id, HouseSearchStatus.MATCHING, user)  # type: ignore[arg-type]
    transition(
        session, HOUSE_SEARCH, req.id, HouseSearchStatus.ASSIGNED, user,  # type: ignore[arg-type]
        reason=body.note, metadata={"agent_id": agent.id},
    )  # fmt: skip
    session.add(AgentEnquiry(house_search_request_id=req.id, agent_id=agent.id))  # type: ignore[arg-type]
    session.commit()
    session.refresh(req)
    notify(agent.user_id, "REQUEST_ASSIGNED", f"House-search request {req.id} was assigned to you")
    notify(req.renter_id, "REQUEST_ASSIGNED", f"An agent was assigned to your request {req.id}")
    return _out(session, req, user)


# ---------------------------------------------------------------- assigned agent


@router.post("/api/house-search-requests/{request_id}/contacted", response_model=HouseSearchOut)
def mark_contacted(request_id: int, user: CurrentUser, session: SessionDep) -> HouseSearchOut:
    req = _move(session, request_id, user, HouseSearchStatus.CONTACTED)
    session.commit()
    session.refresh(req)
    return _out(session, req, user)


@router.post("/api/house-search-requests/{request_id}/respond", response_model=HouseSearchOut)
def respond(request_id: int, body: RespondIn, user: AgentUser, session: SessionDep) -> HouseSearchOut:
    """Assigned agent sends a response. An ASSIGNED request moves to CONTACTED."""
    req = _visible(session, request_id, user)
    agent = _own_agent(session, user)
    if not agent or req.assigned_agent_id != agent.id:
        raise NotFound("Request not found.")
    enquiry = session.exec(
        select(AgentEnquiry)
        .where(AgentEnquiry.house_search_request_id == req.id, AgentEnquiry.agent_id == agent.id)
        .order_by(col(AgentEnquiry.id).desc())
    ).first()
    if enquiry is None or enquiry.status == EnquiryStatus.CLOSED:
        raise Conflict("This enquiry is closed.")
    enquiry.message = body.message
    enquiry.status = EnquiryStatus.RESPONDED
    enquiry.responded_at = utcnow()
    session.add(enquiry)
    audit.record(
        session, actor_id=user.id, entity_type="HouseSearchRequest", entity_id=req.id,  # type: ignore[arg-type]
        action="AGENT_RESPONDED", metadata={"enquiry_id": enquiry.id},
    )  # fmt: skip
    if req.status == HouseSearchStatus.ASSIGNED:
        transition(session, HOUSE_SEARCH, req.id, HouseSearchStatus.CONTACTED, user)  # type: ignore[arg-type]
    session.commit()
    session.refresh(req)
    notify(req.renter_id, "AGENT_RESPONDED", f"Your assigned agent responded to request {req.id}")
    return _out(session, req, user)


@router.get("/api/agent/enquiries", response_model=list[AgentEnquiryOut])
def my_enquiries(user: AgentUser, session: SessionDep) -> list[AgentEnquiryOut]:
    """Only requests assigned to this agent, never the whole request pool."""
    agent = _own_agent(session, user)
    if not agent:
        return []
    rows = session.exec(
        select(AgentEnquiry, HouseSearchRequest)
        .join(HouseSearchRequest, HouseSearchRequest.id == AgentEnquiry.house_search_request_id)  # type: ignore[arg-type]
        .where(AgentEnquiry.agent_id == agent.id, HouseSearchRequest.assigned_agent_id == agent.id)
        .order_by(col(AgentEnquiry.created_at).desc())
    ).all()
    return [
        AgentEnquiryOut(
            id=e.id,  # type: ignore[arg-type]
            status=e.status,
            message=e.message,
            created_at=e.created_at,
            responded_at=e.responded_at,
            request=_out(session, r, user),
        )
        for e, r in rows
    ]
