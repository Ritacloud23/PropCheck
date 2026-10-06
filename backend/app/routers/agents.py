from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy import or_
from sqlmodel import col, func, select

from app.deps import ListerUser, OptionalUser, SessionDep
from app.errors import Conflict, NotFound
from app.models import AgentProfile, AgentVerification, Property, User
from app.models.base import utcnow
from app.models.enums import (
    AgentVerificationStatus,
    PropertyType,
    PropertyVerificationState,
    Role,
    ServiceType,
)
from app.schemas.agents import (
    AgentPrivateOut,
    AgentProfileCreate,
    AgentProfileUpdate,
    AgentPublicOut,
    AgentVerificationOut,
)
from app.schemas.common import Page
from app.schemas.properties import PropertyCard
from app.services import audit, presenters, storage
from app.services.state_machine import transition
from app.services.workflows import AGENT_VERIFICATION

router = APIRouter(prefix="/api/agents", tags=["agents"])

HIDDEN_FROM_DIRECTORY = (
    AgentVerificationStatus.DRAFT,
    AgentVerificationStatus.REJECTED,
    AgentVerificationStatus.SUSPENDED,
)


def _own_profile(session, user: User) -> AgentProfile:
    profile = session.exec(select(AgentProfile).where(AgentProfile.user_id == user.id)).first()
    if not profile:
        raise NotFound("You have not created an agent profile yet.")
    return profile


@router.get("", response_model=Page[AgentPublicOut])
def list_agents(
    session: SessionDep,
    state: str | None = None,
    city: str | None = None,
    lga: str | None = None,
    service: ServiceType | None = Query(
        default=None, description="RENTAL (rent), SALES (purchase), COMMERCIAL..."
    ),
    property_type: PropertyType | None = None,
    budget_min: int | None = Query(default=None, ge=0),
    budget_max: int | None = Query(default=None, ge=0),
    verified_only: bool = False,
    q: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
) -> Page[AgentPublicOut]:
    """Public 'Find a Verified Agent' directory. Suspended, rejected and draft profiles are hidden."""
    query = (
        select(AgentProfile, User)
        .join(User, User.id == AgentProfile.user_id)  # type: ignore[arg-type]
        .where(col(AgentProfile.verification_status).not_in(HIDDEN_FROM_DIRECTORY), User.is_active == True)  # noqa: E712
    )
    if state:
        query = query.where(col(AgentProfile.states_covered).contains([state]))
    if city:
        query = query.where(col(AgentProfile.cities_covered).contains([city]))
    if lga:
        query = query.where(col(AgentProfile.lgas_covered).contains([lga]))
    if service:
        query = query.where(col(AgentProfile.service_types).contains([service.value]))
    if property_type:
        query = query.where(col(AgentProfile.property_types).contains([property_type.value]))
    if budget_min is not None:
        query = query.where(
            or_(col(AgentProfile.budget_max).is_(None), col(AgentProfile.budget_max) >= budget_min)
        )
    if budget_max is not None:
        query = query.where(
            or_(col(AgentProfile.budget_min).is_(None), col(AgentProfile.budget_min) <= budget_max)
        )
    if verified_only:
        query = query.where(
            AgentProfile.verification_status == AgentVerificationStatus.VERIFIED,
            col(AgentProfile.verification_expiry_date) > utcnow(),
        )
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(col(User.full_name).ilike(like), col(AgentProfile.agency_name).ilike(like)))

    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    rows = session.exec(
        query.order_by(
            (AgentProfile.verification_status == AgentVerificationStatus.VERIFIED).desc(),  # type: ignore[union-attr]
            col(AgentProfile.years_experience).desc(),
            col(AgentProfile.id),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    stats = presenters.agent_stats(session, [p.id for p, _ in rows])  # type: ignore[misc]
    items = [presenters.agent_public(p, u, stats.get(p.id, (0, 0))) for p, u in rows]  # type: ignore[arg-type]
    return Page(items=items, total=total, page=page, page_size=page_size)


# ---------------------------------------------------------------- own profile (agents & landlords)


@router.get("/profile", response_model=AgentPrivateOut)
def get_own_profile(user: ListerUser, session: SessionDep) -> AgentPrivateOut:
    return presenters.agent_private(session, _own_profile(session, user), user)


@router.post("/profile", response_model=AgentPrivateOut, status_code=201)
def create_profile(body: AgentProfileCreate, user: ListerUser, session: SessionDep) -> AgentPrivateOut:
    if session.exec(select(AgentProfile).where(AgentProfile.user_id == user.id)).first():
        raise Conflict("You already have an agent profile. Use PATCH to update it.")
    data = body.model_dump()
    data["property_types"] = [p.value for p in body.property_types]
    data["service_types"] = [s.value for s in body.service_types]
    profile = AgentProfile(user_id=user.id, **data)  # type: ignore[arg-type]
    session.add(profile)
    session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="AgentProfile", entity_id=profile.id, action="AGENT_PROFILE_CREATED",
        to_status=profile.verification_status.value,
        metadata={"display_phone_publicly": profile.display_phone_publicly},
    )  # fmt: skip
    session.commit()
    session.refresh(profile)
    return presenters.agent_private(session, profile, user)


@router.patch("/profile", response_model=AgentPrivateOut)
def update_profile(body: AgentProfileUpdate, user: ListerUser, session: SessionDep) -> AgentPrivateOut:
    profile = _own_profile(session, user)
    changes = body.model_dump(exclude_unset=True)
    for key in ("property_types", "service_types"):
        if changes.get(key) is not None:
            changes[key] = [v.value if hasattr(v, "value") else v for v in changes[key]]
    before_consent = profile.display_phone_publicly
    for key, value in changes.items():
        if value is None and key in ("phone_number", "states_covered"):
            continue
        setattr(profile, key, value)
    if (
        profile.budget_min is not None
        and profile.budget_max is not None
        and profile.budget_min > profile.budget_max
    ):
        raise Conflict("budget_min cannot be greater than budget_max")
    session.add(profile)
    audit.record(
        session, actor_id=user.id, entity_type="AgentProfile", entity_id=profile.id, action="AGENT_PROFILE_UPDATED",
        metadata={
            "fields": sorted(changes.keys()),
            "phone_consent_changed": before_consent != profile.display_phone_publicly,
        },
    )  # fmt: skip
    session.commit()
    session.refresh(profile)
    return presenters.agent_private(session, profile, user)


@router.post("/profile/photo", response_model=AgentPrivateOut)
async def upload_profile_photo(
    user: ListerUser, session: SessionDep, file: Annotated[UploadFile, File()]
) -> AgentPrivateOut:
    profile = _own_profile(session, user)
    validated = await storage.read_validated(file, kind="image")
    profile.profile_photo_url = storage.save_public(validated, "agents")
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return presenters.agent_private(session, profile, user)


@router.post("/profile/verification", response_model=AgentVerificationOut, status_code=201)
async def submit_agent_verification(
    user: ListerUser,
    session: SessionDep,
    identity_document: Annotated[UploadFile, File(description="Government ID (PDF/JPG/PNG/WEBP, max 10 MB)")],
    business_document: Annotated[
        UploadFile | None, File(description="Optional CAC / business document")
    ] = None,
    evidence_notes: Annotated[str | None, Form(max_length=2000)] = None,
) -> AgentVerificationOut:
    """Submit evidence for the Verified Agent badge. Files are stored privately and reviewed by a human."""
    profile = _own_profile(session, user)
    latest = presenters.latest_application(session, profile.id)  # type: ignore[arg-type]
    if latest and latest.status in (
        AgentVerificationStatus.SUBMITTED,
        AgentVerificationStatus.IN_REVIEW,
        AgentVerificationStatus.SUSPENDED,
    ):
        raise Conflict(f"You already have an application in status {latest.status.value}.")
    if latest and presenters.effective_agent_status(profile) == AgentVerificationStatus.VERIFIED:
        raise Conflict("Your profile is already verified.")

    identity = await storage.read_validated(identity_document, kind="document")
    business = (
        await storage.read_validated(business_document, kind="document")
        if business_document and business_document.filename
        else None
    )
    application = AgentVerification(
        agent_profile_id=profile.id,  # type: ignore[arg-type]
        submitted_by=user.id,  # type: ignore[arg-type]
        identity_document_url=storage.save_private(identity, "agent-docs"),
        business_document_url=storage.save_private(business, "agent-docs") if business else None,
        evidence_notes=evidence_notes,
    )
    session.add(application)
    session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="AgentVerification", entity_id=application.id,
        action="AGENT_EVIDENCE_UPLOADED", to_status="DRAFT",
        metadata={"identity_document": True, "business_document": business is not None},
    )  # fmt: skip
    transition(session, AGENT_VERIFICATION, application.id, AgentVerificationStatus.SUBMITTED, user)  # type: ignore[arg-type]
    session.commit()
    session.refresh(application)
    return presenters.application_out(application, with_links=True)  # type: ignore[return-value]


@router.get("/profile/verification", response_model=list[AgentVerificationOut])
def list_own_verifications(user: ListerUser, session: SessionDep) -> list[AgentVerificationOut]:
    profile = _own_profile(session, user)
    apps = session.exec(
        select(AgentVerification)
        .where(AgentVerification.agent_profile_id == profile.id)
        .order_by(col(AgentVerification.id).desc())
    ).all()
    return [presenters.application_out(a, with_links=True) for a in apps]  # type: ignore[misc]


# ---------------------------------------------------------------- public profile


def _visible_profile(session, agent_id: int, viewer: User | None) -> tuple[AgentProfile, User]:
    profile = session.get(AgentProfile, agent_id)
    if not profile:
        raise NotFound("Agent not found.")
    is_owner = viewer is not None and viewer.id == profile.user_id
    is_staff = viewer is not None and viewer.role in (Role.REVIEWER, Role.ADMIN)
    if profile.verification_status == AgentVerificationStatus.DRAFT and not (is_owner or is_staff):
        raise NotFound("Agent not found.")
    return profile, session.get(User, profile.user_id)


@router.get("/{agent_id}", response_model=AgentPublicOut)
def get_agent(agent_id: int, session: SessionDep, viewer: OptionalUser) -> AgentPublicOut:
    profile, user = _visible_profile(session, agent_id, viewer)
    stats = presenters.agent_stats(session, [profile.id]).get(profile.id, (0, 0))  # type: ignore[arg-type]
    return presenters.agent_public(profile, user, stats)


@router.get("/{agent_id}/properties", response_model=list[PropertyCard])
def agent_properties(agent_id: int, session: SessionDep, viewer: OptionalUser) -> list[PropertyCard]:
    """Listings by this agent. Note: a Verified Agent's listings are NOT automatically verified."""
    profile, _ = _visible_profile(session, agent_id, viewer)
    props = session.exec(
        select(Property)
        .where(
            Property.listing_agent_id == profile.id,
            Property.is_listed == True,  # noqa: E712
            Property.verification_status != PropertyVerificationState.REJECTED,
        )
        .order_by(col(Property.created_at).desc())
    ).all()
    return presenters.property_cards(session, list(props))
