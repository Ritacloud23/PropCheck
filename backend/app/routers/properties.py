import re
import secrets
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy import or_
from sqlmodel import col, func, select

from app.deps import ListerUser, OptionalUser, SessionDep
from app.errors import BadRequest, Conflict, Forbidden, NotFound
from app.models import (
    AgentProfile,
    AuditLog,
    Property,
    PropertyDocument,
    PropertyMedia,
    User,
    VerificationCheck,
)
from app.models.enums import (
    CHECK_LABELS,
    AgentVerificationStatus,
    AvailabilityStatus,
    CheckResult,
    CheckType,
    DocumentReviewStatus,
    DocumentType,
    PropertyType,
    PropertyVerificationState,
    Role,
    VerificationStatus,
)
from app.schemas.common import DISCLAIMER, PAYMENT_WARNING, Page, TimelineEntry
from app.schemas.properties import (
    CheckReportItem,
    DocumentOut,
    DocumentReportItem,
    MediaOut,
    PropertyCard,
    PropertyCreate,
    PropertyDetail,
    PropertyUpdate,
    ShareOut,
    VerificationReport,
)
from app.services import audit, presenters, storage
from app.services.fees import total_move_in_cost
from app.services.state_machine import transition
from app.services.workflows import VERIFICATION_CASE

router = APIRouter(prefix="/api/properties", tags=["properties"])

MAX_PHOTOS = 15
# Changing any of these after verification invalidates the verification (it no longer matches).
MATERIAL_FIELDS = {
    "address", "state", "city", "area", "property_type", "bedrooms",
    "rent_amount", "agency_fee", "legal_fee", "caution_fee", "other_fees",
}  # fmt: skip

NOT_CHECKED_ALWAYS = [
    "Legal ownership or title (no land-registry or title search was carried out)",
    "Legal validity or authenticity of title documents beyond visual review",
    "Pending court cases, family disputes or government acquisition",
    "Structural, electrical or plumbing condition (no building survey)",
    "Service charge, utility or estate-levy history",
    "Payment terms agreed privately between you and the agent or landlord",
]
LIMITATIONS = [
    "Verification reflects what a PropCheck reviewer saw on the dates shown and can become outdated.",
    "Uploaded documents are not automatically trusted; only documents marked ACCEPTED or REVIEWED were examined.",
    "A Verified Agent badge does not mean every property listed by that agent is verified.",
    "PropCheck does not guarantee that a rental is free of fraud and is not a substitute for legal advice.",
]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:120]


def _new_slug(title: str, city: str) -> str:
    return f"{_slugify(f'{title} {city}')}-{secrets.token_hex(3)}"


def load_property(session, id_or_slug: str | int) -> Property:
    prop = None
    if isinstance(id_or_slug, int) or str(id_or_slug).isdigit():
        prop = session.get(Property, int(id_or_slug))
    if prop is None:
        prop = session.exec(select(Property).where(Property.public_slug == str(id_or_slug))).first()
    if prop is None:
        raise NotFound("Property not found.")
    return prop


def require_manager(session, prop: Property, user: User) -> None:
    """Owner or listing agent only. Reviewers do not edit listings."""
    if user.role in (Role.REVIEWER, Role.ADMIN) or not presenters.can_manage_property(session, prop, user):
        raise Forbidden("You can only manage your own property listings.")


def _public_filter(query):
    agent_ok = or_(
        col(Property.listing_agent_id).is_(None),
        col(Property.listing_agent_id).in_(
            select(AgentProfile.id).where(
                AgentProfile.verification_status != AgentVerificationStatus.SUSPENDED
            )
        ),
    )
    return query.where(
        Property.is_listed == True,  # noqa: E712
        Property.verification_status != PropertyVerificationState.REJECTED,
        agent_ok,
    )


@router.get("", response_model=Page[PropertyCard])
def list_properties(
    session: SessionDep,
    q: str | None = Query(default=None, max_length=80),
    state: str | None = None,
    city: str | None = None,
    lga: str | None = None,
    area: str | None = None,
    property_type: PropertyType | None = None,
    bedrooms: int | None = Query(default=None, ge=0, description="Minimum bedrooms"),
    rent_min: int | None = Query(default=None, ge=0),
    rent_max: int | None = Query(default=None, ge=0),
    verification: Literal["any", "verified", "pending", "not_verified"] = "any",
    verified_only: bool = False,
    available_only: bool = False,
    sort: Literal["newest", "rent_asc", "rent_desc"] = "newest",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
) -> Page[PropertyCard]:
    from app.models.base import utcnow

    query = _public_filter(select(Property))
    if q:
        like = f"%{q.strip()}%"
        query = query.where(
            or_(
                col(Property.title).ilike(like),
                col(Property.city).ilike(like),
                col(Property.area).ilike(like),
                col(Property.landmark).ilike(like),
            )
        )
    if state:
        query = query.where(Property.state == state)
    if city:
        # Accept a city ("Port Harcourt") or, for older links, a neighbourhood ("Lekki").
        query = query.where(or_(col(Property.city).ilike(city), col(Property.area).ilike(city)))
    if area:
        query = query.where(col(Property.area).ilike(area))
    if lga:
        query = query.where(col(Property.local_government_area).ilike(lga))
    if property_type:
        query = query.where(Property.property_type == property_type)
    if bedrooms is not None:
        query = query.where(Property.bedrooms >= bedrooms)
    if rent_min is not None:
        query = query.where(Property.rent_amount >= rent_min)
    if rent_max is not None:
        query = query.where(Property.rent_amount <= rent_max)
    if available_only:
        query = query.where(Property.availability_status == AvailabilityStatus.AVAILABLE)
    now = utcnow()
    is_verified = (Property.verification_status == PropertyVerificationState.VERIFIED) & (
        col(Property.verification_expires_at) > now
    )
    if verified_only or verification == "verified":
        query = query.where(is_verified)
    elif verification == "pending":
        query = query.where(
            col(Property.verification_status).in_(
                [
                    PropertyVerificationState.SUBMITTED,
                    PropertyVerificationState.IN_REVIEW,
                    PropertyVerificationState.INSPECTION_BOOKED,
                ]
            )
        )
    elif verification == "not_verified":
        query = query.where(~is_verified)

    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    order = {
        "newest": col(Property.created_at).desc(),
        "rent_asc": col(Property.rent_amount).asc(),
        "rent_desc": col(Property.rent_amount).desc(),
    }[sort]
    rows = session.exec(
        query.order_by(order, col(Property.id)).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page(
        items=presenters.property_cards(session, list(rows)), total=total, page=page, page_size=page_size
    )


@router.get("/mine", response_model=list[PropertyCard])
def my_properties(user: ListerUser, session: SessionDep) -> list[PropertyCard]:
    agent = session.exec(select(AgentProfile).where(AgentProfile.user_id == user.id)).first()
    cond = Property.owner_user_id == user.id
    if agent:
        cond = or_(cond, Property.listing_agent_id == agent.id)
    props = session.exec(select(Property).where(cond).order_by(col(Property.created_at).desc())).all()
    return presenters.property_cards(session, list(props))


@router.post("", response_model=PropertyDetail, status_code=201)
def create_property(body: PropertyCreate, user: ListerUser, session: SessionDep) -> PropertyDetail:
    agent = session.exec(select(AgentProfile).where(AgentProfile.user_id == user.id)).first()
    if user.role == Role.AGENT:
        if agent is None:
            raise BadRequest("Create your agent profile before listing a property.")
        listing_agent_id = agent.id
    else:
        listing_agent_id = body.listing_agent_id or (agent.id if agent else None)
        if listing_agent_id:
            nominated = session.get(AgentProfile, listing_agent_id)
            if nominated is None or nominated.verification_status == AgentVerificationStatus.SUSPENDED:
                raise BadRequest("The nominated listing agent does not exist or is suspended.")
    if agent and agent.verification_status == AgentVerificationStatus.SUSPENDED:
        raise Forbidden("Suspended agents cannot create listings.")

    data = body.model_dump(exclude={"listing_agent_id"})
    prop = Property(
        **data,
        owner_user_id=user.id,
        listing_agent_id=listing_agent_id,
        public_slug=_new_slug(body.title, body.city),
        total_move_in_cost=total_move_in_cost(
            body.rent_amount, body.agency_fee, body.legal_fee, body.caution_fee, body.other_fees
        ),
    )
    session.add(prop)
    session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="Property", entity_id=prop.id, action="PROPERTY_CREATED",
        metadata={"state": prop.state, "city": prop.city, "total_move_in_cost": prop.total_move_in_cost},
    )  # fmt: skip
    session.commit()
    session.refresh(prop)
    return presenters.property_detail(session, prop, user)


@router.get("/{id_or_slug}", response_model=PropertyDetail)
def get_property(id_or_slug: str, session: SessionDep, viewer: OptionalUser) -> PropertyDetail:
    prop = load_property(session, id_or_slug)
    if not prop.is_listed and not presenters.can_manage_property(session, prop, viewer):
        raise NotFound("Property not found.")
    return presenters.property_detail(session, prop, viewer)


@router.patch("/{property_id}", response_model=PropertyDetail)
def update_property(
    property_id: int, body: PropertyUpdate, user: ListerUser, session: SessionDep
) -> PropertyDetail:
    prop = load_property(session, property_id)
    require_manager(session, prop, user)
    changes = body.model_dump(exclude_unset=True)
    changed_material = sorted(
        k for k, v in changes.items() if k in MATERIAL_FIELDS and v is not None and getattr(prop, k) != v
    )
    for key, value in changes.items():
        if value is None and key in ("title", "address", "state", "city", "property_type", "rent_amount"):
            continue
        setattr(prop, key, value)
    prop.total_move_in_cost = total_move_in_cost(
        prop.rent_amount, prop.agency_fee, prop.legal_fee, prop.caution_fee, prop.other_fees
    )
    session.add(prop)
    audit.record(
        session, actor_id=user.id, entity_type="Property", entity_id=prop.id, action="PROPERTY_UPDATED",  # type: ignore[arg-type]
        metadata={"fields": sorted(changes.keys())},
    )  # fmt: skip
    if changed_material and prop.verification_status == PropertyVerificationState.VERIFIED:
        case = presenters.latest_case(session, prop.id)  # type: ignore[arg-type]
        if case and case.status == VerificationStatus.VERIFIED:
            # System action: the verified facts no longer match the listing.
            transition(
                session, VERIFICATION_CASE, case.id, VerificationStatus.EXPIRED, None,  # type: ignore[arg-type]
                reason="Listing details changed after verification: " + ", ".join(changed_material),
                metadata={"triggered_by_user_id": user.id},
            )  # fmt: skip
    session.commit()
    session.refresh(prop)
    return presenters.property_detail(session, prop, user)


@router.post("/{property_id}/media", response_model=MediaOut, status_code=201)
async def upload_media(
    property_id: int,
    user: ListerUser,
    session: SessionDep,
    file: Annotated[UploadFile, File(description="JPG, PNG or WEBP, max 5 MB")],
    caption: Annotated[str | None, Form(max_length=200)] = None,
) -> PropertyMedia:
    prop = load_property(session, property_id)
    require_manager(session, prop, user)
    count = session.exec(select(func.count()).where(PropertyMedia.property_id == prop.id)).one()
    if count >= MAX_PHOTOS:
        raise Conflict(f"A property can have at most {MAX_PHOTOS} photos.")
    validated = await storage.read_validated(file, kind="image")
    media = PropertyMedia(
        property_id=prop.id, url=storage.save_public(validated, "properties"), caption=caption
    )  # type: ignore[arg-type]
    session.add(media)
    session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="Property", entity_id=prop.id, action="PHOTO_UPLOADED"
    )  # type: ignore[arg-type]
    session.commit()
    session.refresh(media)
    return media


@router.post("/{property_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    property_id: int,
    user: ListerUser,
    session: SessionDep,
    file: Annotated[UploadFile, File(description="PDF, JPG, PNG or WEBP, max 10 MB")],
    document_type: Annotated[DocumentType, Form()],
) -> DocumentOut:
    """Supporting documents are stored privately and start as UPLOADED (not reviewed, not trusted)."""
    prop = load_property(session, property_id)
    require_manager(session, prop, user)
    validated = await storage.read_validated(file, kind="document")
    doc = PropertyDocument(
        property_id=prop.id,  # type: ignore[arg-type]
        document_type=document_type,
        url=storage.save_private(validated, "property-docs"),
        original_filename=(validated.original_filename or "")[:255] or None,
        uploaded_by=user.id,  # type: ignore[arg-type]
        review_status=DocumentReviewStatus.UPLOADED,
    )
    session.add(doc)
    session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="PropertyDocument", entity_id=doc.id,  # type: ignore[arg-type]
        action="DOCUMENT_UPLOADED", to_status="UPLOADED", metadata={"document_type": document_type.value},
    )  # fmt: skip
    session.commit()
    session.refresh(doc)
    return presenters.document_out(doc)


@router.get("/{id_or_slug}/verification-report", response_model=VerificationReport)
def verification_report(id_or_slug: str, session: SessionDep) -> VerificationReport:
    """Public, transparent report of exactly what was (and was not) checked."""
    prop = load_property(session, id_or_slug)
    case = presenters.latest_case(session, prop.id, exclude_draft=True)  # type: ignore[arg-type]
    status = presenters.effective_property_status(prop)
    current = status == PropertyVerificationState.VERIFIED

    checks: list[CheckReportItem] = []
    timeline: list[TimelineEntry] = []
    if case:
        rows = session.exec(
            select(VerificationCheck).where(VerificationCheck.verification_case_id == case.id)
        ).all()
        by_type = {c.check_type: c for c in rows}
        for ct in CheckType:
            c = by_type.get(ct)
            checks.append(
                CheckReportItem(
                    check_type=ct.value,
                    label=CHECK_LABELS[ct],
                    result=c.result if c else CheckResult.NOT_STARTED,
                    evidence_note=c.evidence_note if c else None,
                    completed_at=c.completed_at if c else None,
                )
            )
        timeline = [
            TimelineEntry(action=a.action, from_status=a.from_status, to_status=a.to_status, at=a.created_at)
            for a in session.exec(
                select(AuditLog)
                .where(AuditLog.entity_type == "VerificationCase", AuditLog.entity_id == case.id)
                .order_by(col(AuditLog.id))
            ).all()
        ]

    checked = [c.label for c in checks if c.result == CheckResult.PASSED]
    not_checked = [
        f"{c.label} ({c.result.value.replace('_', ' ').lower()})"
        for c in checks
        if c.result != CheckResult.PASSED
    ]
    docs = session.exec(select(PropertyDocument).where(PropertyDocument.property_id == prop.id)).all()

    agent_verified = False
    if prop.listing_agent_id:
        agent = session.get(AgentProfile, prop.listing_agent_id)
        agent_verified = bool(
            agent and presenters.effective_agent_status(agent) == AgentVerificationStatus.VERIFIED
        )

    return VerificationReport(
        property_id=prop.id,  # type: ignore[arg-type]
        property_slug=prop.public_slug,
        property_title=prop.title,
        status=status,
        is_currently_verified=current,
        verification_reference=case.verification_reference if case else None,
        submitted_at=case.submitted_at if case else None,
        inspection_date=(case.inspected_at or case.inspection_scheduled_for) if case else None,
        verified_at=case.verified_at if case else None,
        expires_at=case.expires_at if case else None,
        reviewer_reference=f"REV-{case.assigned_reviewer_id:04d}"
        if case and case.assigned_reviewer_id
        else None,
        checks=checks,
        what_was_checked=checked,
        what_was_not_checked=not_checked + NOT_CHECKED_ALWAYS,
        documents_reviewed=[
            DocumentReportItem(
                document_type=d.document_type, review_status=d.review_status, reviewed_at=d.reviewed_at
            )
            for d in docs
        ],
        limitations=LIMITATIONS,
        rejection_reason=case.rejection_reason
        if case and case.status == VerificationStatus.REJECTED
        else None,
        timeline=timeline,
        agent_verified=agent_verified,
        agent_note="Agent verification and property verification are separate checks.",
        disclaimer=DISCLAIMER,
        payment_warning=PAYMENT_WARNING,
    )


@router.get("/{id_or_slug}/share", response_model=ShareOut)
def share_property(id_or_slug: str, session: SessionDep) -> ShareOut:
    prop = load_property(session, id_or_slug)
    url = presenters.share_url(prop)
    text = f"Check out this property on PropCheck Nigeria: {prop.title} ({prop.city}, {prop.state}) {url}"
    return ShareOut(
        url=url, title=prop.title, text=text, whatsapp_share_url=f"https://wa.me/?text={quote(text)}"
    )
