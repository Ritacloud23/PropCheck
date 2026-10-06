import secrets
from typing import Literal

from fastapi import APIRouter, Query
from sqlmodel import col, func, select

from app.deps import CurrentUser, ListerUser, SessionDep, StaffUser
from app.errors import BadRequest, Conflict, Forbidden, NotFound
from app.models import (
    AgentProfile,
    AuditLog,
    Property,
    PropertyDocument,
    PropertyMedia,
    User,
    VerificationCase,
    VerificationCheck,
)
from app.models.base import utcnow
from app.models.enums import CHECK_LABELS, CheckType, PropertyVerificationState, Role, VerificationStatus
from app.routers.properties import load_property, require_manager
from app.schemas.agents import AgentPublicOut
from app.schemas.common import AuditOut
from app.schemas.workflow import CaseOut, CaseTransitionIn, CheckIn, CheckOut, DocumentReviewIn, PropertyRef
from app.services import audit, presenters
from app.services.state_machine import transition
from app.services.workflows import VERIFICATION_CASE, property_manager_ids

router = APIRouter(tags=["verification"])

ACTIVE_CASE_STATUSES = (
    VerificationStatus.DRAFT,
    VerificationStatus.SUBMITTED,
    VerificationStatus.IN_REVIEW,
    VerificationStatus.INSPECTION_BOOKED,
)
REVIEWABLE = (VerificationStatus.IN_REVIEW, VerificationStatus.INSPECTION_BOOKED)


def _case_or_404(session, case_id: int) -> VerificationCase:
    case = session.get(VerificationCase, case_id)
    if not case:
        raise NotFound("Verification case not found.")
    return case


def _require_case_access(session, case: VerificationCase, user: User) -> Property:
    prop = session.get(Property, case.property_id)
    if user.role in (Role.REVIEWER, Role.ADMIN):
        return prop  # type: ignore[return-value]
    if user.id not in property_manager_ids(session, prop):  # type: ignore[arg-type]
        # 404 rather than 403 so private case ids are not confirmed to outsiders.
        raise NotFound("Verification case not found.")
    return prop  # type: ignore[return-value]


def _assert_reviewer_independent(session, case: VerificationCase, prop: Property, user: User) -> None:
    if user.id in ({case.submitted_by} | property_manager_ids(session, prop)):
        raise Forbidden(
            "Conflict of interest: you cannot review a case you submitted or a property you manage."
        )


def case_out(session, case: VerificationCase, viewer: User) -> CaseOut:
    prop = session.get(Property, case.property_id)
    checks = session.exec(
        select(VerificationCheck)
        .where(VerificationCheck.verification_case_id == case.id)
        .order_by(col(VerificationCheck.id))
    ).all()
    docs = session.exec(
        select(PropertyDocument)
        .where(PropertyDocument.property_id == prop.id)
        .order_by(col(PropertyDocument.id))
    ).all()
    names = presenters.user_names(session, [case.submitted_by])
    listing_agent: AgentPublicOut | None = None
    if prop.listing_agent_id:
        profile = session.get(AgentProfile, prop.listing_agent_id)
        if profile:
            listing_agent = presenters.agent_public(profile, session.get(User, profile.user_id))
    check_out = []
    for c in checks:
        item = CheckOut.model_validate(c)
        item.label = CHECK_LABELS[c.check_type]
        check_out.append(item)
    allowed = [
        t
        for t in VERIFICATION_CASE.allowed_targets(case.status)
        if viewer.role in VERIFICATION_CASE.transitions[(case.status.value, t)].roles
    ]
    return CaseOut(
        id=case.id,
        property=PropertyRef(
            id=prop.id, title=prop.title, public_slug=prop.public_slug, state=prop.state, city=prop.city
        ),
        status=case.status,
        effective_status=presenters.effective_case_status(case),
        verification_reference=case.verification_reference,
        submitted_by=case.submitted_by,
        submitted_by_name=names.get(case.submitted_by),
        assigned_reviewer_id=case.assigned_reviewer_id,
        submitted_at=case.submitted_at,
        inspection_booked_at=case.inspection_booked_at,
        inspection_scheduled_for=case.inspection_scheduled_for,
        inspected_at=case.inspected_at,
        verified_at=case.verified_at,
        expires_at=case.expires_at,
        rejection_reason=case.rejection_reason,
        reviewer_notes=case.reviewer_notes,
        created_at=case.created_at,
        checks=check_out,
        documents=[presenters.document_out(d) for d in docs],
        allowed_transitions=allowed,
        listing_agent=listing_agent,
    )


@router.post("/api/properties/{property_id}/verification", response_model=CaseOut, status_code=201)
def open_case(property_id: int, user: ListerUser, session: SessionDep) -> CaseOut:
    """Open a new DRAFT verification case (with the 8 checklist items) for your property."""
    prop = load_property(session, property_id)
    require_manager(session, prop, user)
    session.exec(select(Property).where(Property.id == prop.id).with_for_update()).one()
    existing = session.exec(
        select(VerificationCase).where(
            VerificationCase.property_id == prop.id, col(VerificationCase.status).in_(ACTIVE_CASE_STATUSES)
        )
    ).first()
    if existing:
        raise Conflict(f"This property already has an open case ({existing.verification_reference}).")
    if presenters.effective_property_status(prop) == PropertyVerificationState.VERIFIED:
        raise Conflict("This property is currently verified. A new case can be opened after it expires.")

    case = VerificationCase(
        property_id=prop.id,  # type: ignore[arg-type]
        submitted_by=user.id,  # type: ignore[arg-type]
        verification_reference=f"TMP-{secrets.token_hex(8)}",
    )
    session.add(case)
    session.flush()
    case.verification_reference = f"PCV-{utcnow().year}-{case.id:05d}"
    for ct in CheckType:
        session.add(VerificationCheck(verification_case_id=case.id, check_type=ct))  # type: ignore[arg-type]
    prop.verification_status = PropertyVerificationState.DRAFT
    prop.verification_expires_at = None
    session.add(prop)
    audit.record(
        session, actor_id=user.id, entity_type="VerificationCase", entity_id=case.id,  # type: ignore[arg-type]
        action="CASE_OPENED", to_status="DRAFT", metadata={"property_id": prop.id},
    )  # fmt: skip
    session.commit()
    session.refresh(case)
    return case_out(session, case, user)


@router.get("/api/verification-cases", response_model=list[CaseOut])
def list_cases(
    user: CurrentUser,
    session: SessionDep,
    status: VerificationStatus | None = None,
    scope: Literal["all", "mine", "unassigned"] = "all",
    limit: int = Query(default=100, ge=1, le=200),
) -> list[CaseOut]:
    query = select(VerificationCase)
    if user.role in (Role.REVIEWER, Role.ADMIN):
        if scope == "mine":
            query = query.where(VerificationCase.assigned_reviewer_id == user.id)
        elif scope == "unassigned":
            query = query.where(col(VerificationCase.assigned_reviewer_id).is_(None))
        query = query.where(VerificationCase.status != VerificationStatus.DRAFT)
    elif user.role in (Role.AGENT, Role.LANDLORD):
        agent = session.exec(select(AgentProfile).where(AgentProfile.user_id == user.id)).first()
        own = select(Property.id).where(
            (Property.owner_user_id == user.id) | (Property.listing_agent_id == (agent.id if agent else -1))
        )
        query = query.where(col(VerificationCase.property_id).in_(own))
    else:
        raise Forbidden("Renters do not have verification cases.")
    if status:
        query = query.where(VerificationCase.status == status)
    cases = session.exec(query.order_by(col(VerificationCase.id).desc()).limit(limit)).all()
    return [case_out(session, c, user) for c in cases]


@router.get("/api/verification-cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int, user: CurrentUser, session: SessionDep) -> CaseOut:
    case = _case_or_404(session, case_id)
    _require_case_access(session, case, user)
    return case_out(session, case, user)


@router.post("/api/verification-cases/{case_id}/submit", response_model=CaseOut)
def submit_case(case_id: int, user: ListerUser, session: SessionDep) -> CaseOut:
    case = _case_or_404(session, case_id)
    prop = _require_case_access(session, case, user)
    photos = session.exec(select(func.count()).where(PropertyMedia.property_id == prop.id)).one()
    docs = session.exec(select(func.count()).where(PropertyDocument.property_id == prop.id)).one()
    if photos < 1 or docs < 1:
        raise BadRequest("Upload at least one photo and one supporting document before submitting.")
    transition(session, VERIFICATION_CASE, case.id, VerificationStatus.SUBMITTED, user)  # type: ignore[arg-type]
    session.commit()
    session.refresh(case)
    return case_out(session, case, user)


@router.post("/api/verification-cases/{case_id}/transition", response_model=CaseOut)
def transition_case(case_id: int, body: CaseTransitionIn, user: CurrentUser, session: SessionDep) -> CaseOut:
    """Move a case through the workflow. Allowed moves, roles and conflict rules are enforced centrally."""
    case = _case_or_404(session, case_id)
    _require_case_access(session, case, user)
    meta = {
        k: (v.isoformat() if hasattr(v, "isoformat") else v)
        for k, v in body.model_dump(
            include={"expires_at", "inspection_scheduled_for", "inspected_at", "reviewer_notes"}
        ).items()
        if v is not None
    }
    transition(session, VERIFICATION_CASE, case.id, body.to_status, user, reason=body.reason, metadata=meta)  # type: ignore[arg-type]
    session.commit()
    session.refresh(case)
    return case_out(session, case, user)


@router.post("/api/verification-cases/{case_id}/checks", response_model=CaseOut)
def record_check(case_id: int, body: CheckIn, user: StaffUser, session: SessionDep) -> CaseOut:
    case = session.exec(
        select(VerificationCase).where(VerificationCase.id == case_id).with_for_update()
    ).first()
    if not case:
        raise NotFound("Verification case not found.")
    prop = session.get(Property, case.property_id)
    _assert_reviewer_independent(session, case, prop, user)  # type: ignore[arg-type]
    if case.status not in REVIEWABLE:
        raise Conflict(
            f"Checklist can only be updated while the case is in review (currently {case.status.value})."
        )
    check = session.exec(
        select(VerificationCheck).where(
            VerificationCheck.verification_case_id == case.id, VerificationCheck.check_type == body.check_type
        )
    ).first()
    if check is None:
        check = VerificationCheck(verification_case_id=case.id, check_type=body.check_type)  # type: ignore[arg-type]
    doc_key = None
    if body.document_id is not None:
        doc = session.get(PropertyDocument, body.document_id)
        if not doc or doc.property_id != prop.id:  # type: ignore[union-attr]
            raise BadRequest("That document does not belong to this property.")
        doc_key = f"property_document:{doc.id}"
    previous = check.result.value if check.result else None
    check.result = body.result
    check.evidence_note = body.evidence_note
    check.document_url = doc_key
    check.completed_by = user.id
    check.completed_at = utcnow()
    session.add(check)
    if case.assigned_reviewer_id is None:
        case.assigned_reviewer_id = user.id
        session.add(case)
    audit.record(
        session, actor_id=user.id, entity_type="VerificationCase", entity_id=case.id,  # type: ignore[arg-type]
        action="CHECK_RECORDED", from_status=previous, to_status=body.result.value,
        metadata={"check_type": body.check_type.value},
    )  # fmt: skip
    session.commit()
    session.refresh(case)
    return case_out(session, case, user)


@router.post("/api/verification-cases/{case_id}/documents/{document_id}/review", response_model=CaseOut)
def review_document(
    case_id: int, document_id: int, body: DocumentReviewIn, user: StaffUser, session: SessionDep
) -> CaseOut:
    """Mark a document as REVIEWED / ACCEPTED / REJECTED. Uploading alone never makes a document trusted."""
    case = _case_or_404(session, case_id)
    prop = session.get(Property, case.property_id)
    _assert_reviewer_independent(session, case, prop, user)  # type: ignore[arg-type]
    if case.status not in REVIEWABLE:
        raise Conflict("Documents can only be reviewed while the case is in review.")
    doc = session.get(PropertyDocument, document_id)
    if not doc or doc.property_id != prop.id:  # type: ignore[union-attr]
        raise NotFound("Document not found on this property.")
    previous = doc.review_status.value
    doc.review_status = body.review_status
    doc.reviewer_notes = body.reviewer_notes
    doc.reviewed_at = utcnow()
    session.add(doc)
    audit.record(
        session, actor_id=user.id, entity_type="VerificationCase", entity_id=case.id,  # type: ignore[arg-type]
        action="DOCUMENT_REVIEWED", from_status=previous, to_status=body.review_status.value,
        metadata={"document_id": doc.id, "document_type": doc.document_type.value},
    )  # fmt: skip
    session.commit()
    return case_out(session, case, user)


@router.get("/api/verification-cases/{case_id}/audit-log", response_model=list[AuditOut])
def case_audit_log(case_id: int, user: CurrentUser, session: SessionDep) -> list[AuditOut]:
    case = _case_or_404(session, case_id)
    _require_case_access(session, case, user)
    rows = session.exec(
        select(AuditLog)
        .where(AuditLog.entity_type == "VerificationCase", AuditLog.entity_id == case.id)
        .order_by(col(AuditLog.id))
    ).all()
    names = presenters.user_names(session, [r.actor_user_id for r in rows])
    out = []
    for r in rows:
        item = AuditOut.model_validate(r)
        item.actor_name = names.get(r.actor_user_id) if r.actor_user_id else "System"  # type: ignore[arg-type]
        out.append(item)
    return out
