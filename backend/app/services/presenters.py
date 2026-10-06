"""Turn database rows into API responses.

Privacy rules live here so that every endpoint applies them the same way:
* agent phone/WhatsApp/email only appear in public output with explicit consent;
* document links are only produced for authorised viewers, as short-lived signed URLs;
* VERIFIED records past their expiry date are always presented as EXPIRED.
"""

from collections.abc import Iterable
from urllib.parse import quote

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.config import settings
from app.models import (
    AgentProfile,
    AgentReport,
    AgentVerification,
    Property,
    PropertyDocument,
    PropertyMedia,
    User,
    VerificationCase,
)
from app.models.base import utcnow
from app.models.enums import (
    AgentVerificationStatus,
    PropertyVerificationState,
    ReportStatus,
    Role,
    VerificationStatus,
)
from app.schemas.agents import (
    AgentPrivateOut,
    AgentPublicOut,
    AgentSummary,
    AgentVerificationOut,
)
from app.schemas.properties import (
    DocumentOut,
    FeeBreakdown,
    MediaOut,
    PropertyCard,
    PropertyDetail,
    VerificationBadge,
)
from app.services import storage

STAFF = (Role.REVIEWER, Role.ADMIN)

# ------------------------------------------------------------------ effective statuses


def effective_agent_status(profile: AgentProfile) -> AgentVerificationStatus:
    if (
        profile.verification_status == AgentVerificationStatus.VERIFIED
        and profile.verification_expiry_date is not None
        and profile.verification_expiry_date <= utcnow()
    ):
        return AgentVerificationStatus.EXPIRED
    return profile.verification_status


def effective_property_status(prop: Property) -> PropertyVerificationState:
    if prop.verification_status == PropertyVerificationState.VERIFIED and (
        prop.verification_expires_at is None or prop.verification_expires_at <= utcnow()
    ):
        return PropertyVerificationState.EXPIRED
    return prop.verification_status


def effective_case_status(case: VerificationCase) -> VerificationStatus:
    if case.status == VerificationStatus.VERIFIED and (
        case.expires_at is None or case.expires_at <= utcnow()
    ):
        return VerificationStatus.EXPIRED
    return case.status


# ------------------------------------------------------------------ agents


def agent_stats(session: Session, agent_ids: Iterable[int]) -> dict[int, tuple[int, int]]:
    """agent_id -> (active public listings, open reports)."""
    ids = list(set(agent_ids))
    if not ids:
        return {}
    listings = dict(
        session.exec(
            select(Property.listing_agent_id, func.count())
            .where(col(Property.listing_agent_id).in_(ids), Property.is_listed == True)  # noqa: E712
            .group_by(Property.listing_agent_id)
        ).all()
    )
    reports = dict(
        session.exec(
            select(AgentReport.agent_id, func.count())
            .where(
                col(AgentReport.agent_id).in_(ids),
                col(AgentReport.status).in_([ReportStatus.OPEN, ReportStatus.IN_REVIEW]),
            )
            .group_by(AgentReport.agent_id)
        ).all()
    )
    return {i: (int(listings.get(i, 0)), int(reports.get(i, 0))) for i in ids}


def _complaint_status(status: AgentVerificationStatus, open_reports: int) -> str:
    if status == AgentVerificationStatus.SUSPENDED:
        return "SUSPENDED"
    return "COMPLAINT_UNDER_REVIEW" if open_reports else "NO_OPEN_COMPLAINTS"


def agent_summary(profile: AgentProfile, user: User) -> AgentSummary:
    status = effective_agent_status(profile)
    return AgentSummary(
        id=profile.id,  # type: ignore[arg-type]
        name=user.full_name,
        agency_name=profile.agency_name,
        profile_photo_url=profile.profile_photo_url,
        verification_status=status,
        is_verified=status == AgentVerificationStatus.VERIFIED,
        verification_expiry_date=profile.verification_expiry_date,
    )


def agent_public(
    profile: AgentProfile, user: User, stats: tuple[int, int] = (0, 0), *, reveal_contact: bool = False
) -> AgentPublicOut:
    """`reveal_contact` is only true for a renter whose request has been assigned to this agent."""
    status = effective_agent_status(profile)
    active_listings, open_reports = stats
    contactable = status != AgentVerificationStatus.SUSPENDED and (
        profile.display_phone_publicly or reveal_contact
    )
    show_email = status != AgentVerificationStatus.SUSPENDED and (
        profile.display_email_publicly or reveal_contact
    )
    return AgentPublicOut(
        id=profile.id,  # type: ignore[arg-type]
        name=user.full_name,
        agency_name=profile.agency_name,
        bio=profile.bio,
        profile_photo_url=profile.profile_photo_url,
        phone_number=profile.phone_number if contactable else None,
        whatsapp_number=(profile.whatsapp_number or profile.phone_number) if contactable else None,
        email=profile.email if show_email else None,
        contact_public=contactable,
        states_covered=profile.states_covered,
        cities_covered=profile.cities_covered,
        lgas_covered=profile.lgas_covered,
        property_types=profile.property_types,
        service_types=profile.service_types,
        budget_min=profile.budget_min,
        budget_max=profile.budget_max,
        years_experience=profile.years_experience,
        verification_status=status,
        is_verified=status == AgentVerificationStatus.VERIFIED,
        verification_date=profile.verification_date,
        verification_expiry_date=profile.verification_expiry_date,
        active_listings=active_listings,
        completed_connections=profile.completed_connections,
        average_rating=profile.average_rating,
        total_reviews=profile.total_reviews,
        complaint_status=_complaint_status(status, open_reports),
        response_time_hours=profile.response_time_hours,
        joined_at=profile.created_at,
    )


def latest_application(session: Session, profile_id: int) -> AgentVerification | None:
    return session.exec(
        select(AgentVerification)
        .where(AgentVerification.agent_profile_id == profile_id)
        .order_by(col(AgentVerification.id).desc())
    ).first()


def application_out(app: AgentVerification | None, *, with_links: bool) -> AgentVerificationOut | None:
    if app is None:
        return None
    out = AgentVerificationOut.model_validate(app)
    out.has_identity_document = bool(app.identity_document_url)
    out.has_business_document = bool(app.business_document_url)
    if with_links:
        out.identity_document_link = storage.signed_url(app.identity_document_url)
        out.business_document_link = storage.signed_url(app.business_document_url)
    return out


def agent_private(session: Session, profile: AgentProfile, user: User) -> AgentPrivateOut:
    stats = agent_stats(session, [profile.id]).get(profile.id, (0, 0))  # type: ignore[arg-type]
    public = agent_public(profile, user, stats)
    return AgentPrivateOut(
        **public.model_dump(),
        user_id=user.id,  # type: ignore[arg-type]
        private_phone_number=profile.phone_number,
        private_whatsapp_number=profile.whatsapp_number,
        private_email=profile.email,
        display_phone_publicly=profile.display_phone_publicly,
        display_email_publicly=profile.display_email_publicly,
        latest_application=application_out(latest_application(session, profile.id), with_links=True),  # type: ignore[arg-type]
    )


# ------------------------------------------------------------------ properties


def can_manage_property(session: Session, prop: Property, user: User | None) -> bool:
    if user is None:
        return False
    if user.role in STAFF:
        return True
    if prop.owner_user_id == user.id:
        return True
    if prop.listing_agent_id:
        agent = session.get(AgentProfile, prop.listing_agent_id)
        return bool(agent and agent.user_id == user.id)
    return False


def latest_case(
    session: Session, property_id: int, *, exclude_draft: bool = False
) -> VerificationCase | None:
    q = select(VerificationCase).where(VerificationCase.property_id == property_id)
    if exclude_draft:
        q = q.where(VerificationCase.status != VerificationStatus.DRAFT)
    return session.exec(q.order_by(col(VerificationCase.id).desc())).first()


def verification_badge(prop: Property, case: VerificationCase | None) -> VerificationBadge:
    status = effective_property_status(prop)
    current = status == PropertyVerificationState.VERIFIED
    return VerificationBadge(
        status=status,
        is_currently_verified=current,
        reference=case.verification_reference if case and case.status != VerificationStatus.DRAFT else None,
        verified_at=case.verified_at if case and case.verified_at else None,
        expires_at=case.expires_at if case else None,
    )


def _cover_photos(session: Session, property_ids: list[int]) -> dict[int, str]:
    if not property_ids:
        return {}
    rows = session.exec(
        select(PropertyMedia)
        .where(col(PropertyMedia.property_id).in_(property_ids))
        .order_by(col(PropertyMedia.id).asc())
    ).all()
    covers: dict[int, str] = {}
    for m in rows:
        covers.setdefault(m.property_id, m.url)
    return covers


def property_cards(session: Session, props: list[Property]) -> list[PropertyCard]:
    ids = [p.id for p in props]
    covers = _cover_photos(session, ids)  # type: ignore[arg-type]
    agent_ids = {p.listing_agent_id for p in props if p.listing_agent_id}
    agents: dict[int, tuple[AgentProfile, User]] = {}
    if agent_ids:
        for profile, user in session.exec(
            select(AgentProfile, User)
            .join(User, User.id == AgentProfile.user_id)  # type: ignore[arg-type]
            .where(col(AgentProfile.id).in_(agent_ids))
        ).all():
            agents[profile.id] = (profile, user)  # type: ignore[index]
    cases: dict[int, VerificationCase] = {}
    if ids:
        for case in session.exec(
            select(VerificationCase)
            .where(
                col(VerificationCase.property_id).in_(ids),
                VerificationCase.status != VerificationStatus.DRAFT,
            )
            .order_by(col(VerificationCase.id).asc())
        ).all():
            cases[case.property_id] = case  # last one wins = latest
    out = []
    for p in props:
        agent = agents.get(p.listing_agent_id) if p.listing_agent_id else None
        out.append(
            PropertyCard(
                id=p.id,  # type: ignore[arg-type]
                public_slug=p.public_slug,
                title=p.title,
                state=p.state,
                city=p.city,
                local_government_area=p.local_government_area,
                area=p.area,
                property_type=p.property_type,
                bedrooms=p.bedrooms,
                bathrooms=p.bathrooms,
                furnished=p.furnished,
                rent_amount=p.rent_amount,
                total_move_in_cost=p.total_move_in_cost,
                availability_status=p.availability_status,
                cover_photo_url=covers.get(p.id),  # type: ignore[arg-type]
                verification=verification_badge(p, cases.get(p.id)),  # type: ignore[arg-type]
                agent=agent_summary(*agent) if agent else None,
                created_at=p.created_at,
            )
        )
    return out


def document_out(doc: PropertyDocument) -> DocumentOut:
    return DocumentOut(
        id=doc.id,  # type: ignore[arg-type]
        document_type=doc.document_type,
        original_filename=doc.original_filename,
        review_status=doc.review_status,
        reviewer_notes=doc.reviewer_notes,
        uploaded_at=doc.uploaded_at,
        reviewed_at=doc.reviewed_at,
        link=storage.signed_url(doc.url),
    )


def share_url(prop: Property) -> str:
    return f"{settings.frontend_url}/properties/{quote(prop.public_slug)}"


def property_detail(session: Session, prop: Property, viewer: User | None) -> PropertyDetail:
    card = property_cards(session, [prop])[0]
    media = session.exec(
        select(PropertyMedia).where(PropertyMedia.property_id == prop.id).order_by(col(PropertyMedia.id))
    ).all()
    agent_profile = None
    if prop.listing_agent_id:
        profile = session.get(AgentProfile, prop.listing_agent_id)
        if profile:
            user = session.get(User, profile.user_id)
            stats = agent_stats(session, [profile.id]).get(profile.id, (0, 0))  # type: ignore[arg-type]
            agent_profile = agent_public(profile, user, stats)  # type: ignore[arg-type]
    manage = can_manage_property(session, prop, viewer)
    documents = None
    case_id = None
    if manage:
        documents = [
            document_out(d)
            for d in session.exec(
                select(PropertyDocument)
                .where(PropertyDocument.property_id == prop.id)
                .order_by(col(PropertyDocument.id))
            ).all()
        ]
        case = latest_case(session, prop.id)  # type: ignore[arg-type]
        case_id = case.id if case else None
    return PropertyDetail(
        **card.model_dump(),
        description=prop.description,
        address=prop.address,
        landmark=prop.landmark,
        latitude=prop.latitude,
        longitude=prop.longitude,
        fees=FeeBreakdown(
            rent_amount=prop.rent_amount,
            agency_fee=prop.agency_fee,
            legal_fee=prop.legal_fee,
            caution_fee=prop.caution_fee,
            other_fees=prop.other_fees,
            other_fees_description=prop.other_fees_description,
            total_move_in_cost=prop.total_move_in_cost,
        ),
        media=[MediaOut.model_validate(m) for m in media],
        agent_profile=agent_profile,
        is_listed=prop.is_listed,
        share_url=share_url(prop),
        can_manage=manage,
        documents=documents,
        owner_user_id=prop.owner_user_id if manage else None,
        latest_case_id=case_id,
    )


def user_names(session: Session, ids: Iterable[int | None]) -> dict[int, str]:
    wanted = {i for i in ids if i}
    if not wanted:
        return {}
    return {u.id: u.full_name for u in session.exec(select(User).where(col(User.id).in_(wanted))).all()}  # type: ignore[misc]


def property_ref(prop: Property):
    from app.schemas.workflow import PropertyRef

    return PropertyRef(
        id=prop.id, title=prop.title, public_slug=prop.public_slug, state=prop.state, city=prop.city
    )  # type: ignore[arg-type]


def allowed_actions(machine, current, user: User) -> list[str]:
    """Targets the viewer's role could move to (guards such as ownership are still checked on submit)."""
    value = current.value if hasattr(current, "value") else str(current)
    return [t for t in machine.allowed_targets(value) if user.role in machine.transitions[(value, t)].roles]
