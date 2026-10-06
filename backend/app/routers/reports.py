from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlmodel import col, select

from app.deps import CurrentUser, SessionDep
from app.errors import BadRequest, NotFound
from app.models import AgentProfile, AgentReport, Property, User
from app.models.enums import ReportReason, Role
from app.routers.properties import load_property
from app.schemas.workflow import ReportOut
from app.services import audit, presenters, storage
from app.services.ratelimit import auth_rate_limit

router = APIRouter(tags=["reports"])


def report_out(session, report: AgentReport, viewer: User) -> ReportOut:
    is_staff = viewer.role in (Role.REVIEWER, Role.ADMIN)
    names = presenters.user_names(session, [report.reporter_id])
    agent_name = None
    if report.agent_id:
        profile = session.get(AgentProfile, report.agent_id)
        if profile:
            agent_name = presenters.user_names(session, [profile.user_id]).get(profile.user_id)
    prop = session.get(Property, report.property_id) if report.property_id else None
    return ReportOut(
        id=report.id,  # type: ignore[arg-type]
        reporter_id=report.reporter_id,
        reporter_name=names.get(report.reporter_id),
        agent_id=report.agent_id,
        agent_name=agent_name,
        property=presenters.property_ref(prop) if prop else None,
        reason=report.reason,
        description=report.description,
        has_evidence=bool(report.evidence_url),
        evidence_link=storage.signed_url(report.evidence_url)
        if (is_staff or viewer.id == report.reporter_id)
        else None,
        status=report.status,
        reviewer_notes=report.reviewer_notes if is_staff else None,
        resolution_reason=report.resolution_reason,
        created_at=report.created_at,
        resolved_at=report.resolved_at,
    )


async def _create(
    session,
    user: User,
    *,
    agent_id: int | None,
    property_id: int | None,
    reason: ReportReason,
    description: str,
    evidence: UploadFile | None,
) -> ReportOut:
    if len(description.strip()) < 10:
        raise BadRequest("Please describe what happened (at least 10 characters).")
    evidence_key = None
    if evidence is not None and evidence.filename:
        evidence_key = storage.save_private(
            await storage.read_validated(evidence, kind="document"), "report-evidence"
        )
    report = AgentReport(
        reporter_id=user.id,  # type: ignore[arg-type]
        agent_id=agent_id,
        property_id=property_id,
        reason=reason,
        description=description.strip(),
        evidence_url=evidence_key,
    )
    session.add(report)
    session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="AgentReport", entity_id=report.id,  # type: ignore[arg-type]
        action="REPORT_FILED", to_status=report.status.value,
        metadata={"reason": reason.value, "agent_id": agent_id, "property_id": property_id, "evidence": bool(evidence_key)},
    )  # fmt: skip
    session.commit()
    session.refresh(report)
    return report_out(session, report, user)


ReasonForm = Annotated[ReportReason, Form()]
DescriptionForm = Annotated[str, Form(min_length=10, max_length=4000)]
EvidenceFile = Annotated[UploadFile | None, File(description="Optional screenshot or PDF, max 10 MB")]


@router.post(
    "/api/agents/{agent_id}/report",
    response_model=ReportOut,
    status_code=201,
    dependencies=[Depends(auth_rate_limit)],
)
async def report_agent(
    agent_id: int,
    user: CurrentUser,
    session: SessionDep,
    reason: ReasonForm,
    description: DescriptionForm,
    evidence: EvidenceFile = None,
) -> ReportOut:
    profile = session.get(AgentProfile, agent_id)
    if not profile:
        raise NotFound("Agent not found.")
    if profile.user_id == user.id:
        raise BadRequest("You cannot report your own profile.")
    return await _create(
        session,
        user,
        agent_id=agent_id,
        property_id=None,
        reason=reason,
        description=description,
        evidence=evidence,
    )


@router.post(
    "/api/properties/{property_id}/report",
    response_model=ReportOut,
    status_code=201,
    dependencies=[Depends(auth_rate_limit)],
)
async def report_property(
    property_id: int,
    user: CurrentUser,
    session: SessionDep,
    reason: ReasonForm,
    description: DescriptionForm,
    evidence: EvidenceFile = None,
) -> ReportOut:
    prop = load_property(session, property_id)
    return await _create(
        session,
        user,
        agent_id=prop.listing_agent_id,
        property_id=prop.id,
        reason=reason,
        description=description,
        evidence=evidence,
    )


@router.get("/api/reports/mine", response_model=list[ReportOut])
def my_reports(user: CurrentUser, session: SessionDep) -> list[ReportOut]:
    rows = session.exec(
        select(AgentReport).where(AgentReport.reporter_id == user.id).order_by(col(AgentReport.id).desc())
    ).all()
    return [report_out(session, r, user) for r in rows]
