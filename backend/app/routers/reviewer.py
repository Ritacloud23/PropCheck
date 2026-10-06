"""Reviewer / admin console: agent applications, reports, audit log and dashboard counts."""

from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import func
from sqlmodel import col, select

from app.deps import SessionDep, StaffUser
from app.errors import Conflict, NotFound
from app.models import (
    AgentProfile,
    AgentReport,
    AuditLog,
    HouseSearchRequest,
    PlaceReport,
    Reservation,
    User,
    VerificationCase,
)
from app.models.enums import (
    AgentVerificationStatus,
    HouseSearchStatus,
    PlaceReportStatus,
    ReportStatus,
    ReservationStatus,
    VerificationStatus,
)
from app.routers.reports import report_out
from app.schemas.agents import AgentDecisionIn, ReviewerAgentOut
from app.schemas.common import AuditOut
from app.schemas.workflow import ReportDecisionIn, ReportOut
from app.services import presenters
from app.services.notifications import notify
from app.services.state_machine import transition
from app.services.workflows import AGENT_REPORT, AGENT_VERIFICATION

router = APIRouter(prefix="/api/reviewer", tags=["reviewer"])

AgentAction = Literal["start-review", "approve", "reject", "suspend", "expire", "reinstate"]
ACTION_TARGET = {
    "start-review": AgentVerificationStatus.IN_REVIEW,
    "approve": AgentVerificationStatus.VERIFIED,
    "reject": AgentVerificationStatus.REJECTED,
    "suspend": AgentVerificationStatus.SUSPENDED,
    "expire": AgentVerificationStatus.EXPIRED,
    "reinstate": AgentVerificationStatus.IN_REVIEW,
}


# ---------------------------------------------------------------- dashboard


@router.get("/summary")
def summary(user: StaffUser, session: SessionDep) -> dict:
    def count(model, *where) -> int:
        return int(session.exec(select(func.count()).select_from(model).where(*where)).one())

    return {
        "agent_applications_waiting": count(
            AgentProfile,
            col(AgentProfile.verification_status).in_(
                [AgentVerificationStatus.SUBMITTED, AgentVerificationStatus.IN_REVIEW]
            ),
        ),
        "property_cases_waiting": count(
            VerificationCase,
            col(VerificationCase.status).in_(
                [
                    VerificationStatus.SUBMITTED,
                    VerificationStatus.IN_REVIEW,
                    VerificationStatus.INSPECTION_BOOKED,
                ]
            ),
        ),
        "house_search_unassigned": count(
            HouseSearchRequest,
            col(HouseSearchRequest.status).in_([HouseSearchStatus.SUBMITTED, HouseSearchStatus.MATCHING]),
        ),
        "open_place_reports": count(PlaceReport, PlaceReport.status == PlaceReportStatus.OPEN),
        "open_reports": count(
            AgentReport, col(AgentReport.status).in_([ReportStatus.OPEN, ReportStatus.IN_REVIEW])
        ),
        "refund_requests": count(
            Reservation,
            Reservation.status == ReservationStatus.PENDING_RELEASE,
            col(Reservation.refund_requested_at).is_not(None),
        ),
    }


# ---------------------------------------------------------------- agent applications


def _reviewer_agent(session, profile: AgentProfile, viewer: User) -> ReviewerAgentOut:
    user = session.get(User, profile.user_id)
    private = presenters.agent_private(session, profile, user)
    latest = presenters.latest_application(session, profile.id)
    open_reports = presenters.agent_stats(session, [profile.id]).get(profile.id, (0, 0))[1]
    actions: list[str] = []
    if latest and viewer.id not in (profile.user_id, latest.submitted_by):
        targets = set(presenters.allowed_actions(AGENT_VERIFICATION, latest.status, viewer))
        for name, target in ACTION_TARGET.items():
            if target.value in targets:
                if name == "start-review" and latest.status == AgentVerificationStatus.SUSPENDED:
                    continue
                if name == "reinstate" and latest.status != AgentVerificationStatus.SUSPENDED:
                    continue
                actions.append(name)
    return ReviewerAgentOut(
        **private.model_dump(), account_email=user.email, open_reports=open_reports, allowed_actions=actions
    )


@router.get("/agents", response_model=list[ReviewerAgentOut])
def list_agent_applications(
    user: StaffUser,
    session: SessionDep,
    status: AgentVerificationStatus | None = Query(
        default=None, description="Defaults to SUBMITTED + IN_REVIEW"
    ),
    limit: int = Query(default=100, ge=1, le=200),
) -> list[ReviewerAgentOut]:
    query = select(AgentProfile)
    if status:
        query = query.where(AgentProfile.verification_status == status)
    else:
        query = query.where(
            col(AgentProfile.verification_status).in_(
                [AgentVerificationStatus.SUBMITTED, AgentVerificationStatus.IN_REVIEW]
            )
        )
    rows = session.exec(query.order_by(col(AgentProfile.updated_at).asc()).limit(limit)).all()
    return [_reviewer_agent(session, p, user) for p in rows]


@router.get("/agents/{agent_id}", response_model=ReviewerAgentOut)
def get_agent_application(agent_id: int, user: StaffUser, session: SessionDep) -> ReviewerAgentOut:
    profile = session.get(AgentProfile, agent_id)
    if not profile:
        raise NotFound("Agent not found.")
    return _reviewer_agent(session, profile, user)


@router.post("/agents/{agent_id}/{action}", response_model=ReviewerAgentOut)
def decide_agent(
    agent_id: int, action: AgentAction, body: AgentDecisionIn, user: StaffUser, session: SessionDep
) -> ReviewerAgentOut:
    profile = session.get(AgentProfile, agent_id)
    if not profile:
        raise NotFound("Agent not found.")
    latest = presenters.latest_application(session, profile.id)  # type: ignore[arg-type]
    if latest is None:
        raise Conflict("This agent has not submitted a verification application.")
    if action == "reinstate" and latest.status != AgentVerificationStatus.SUSPENDED:
        raise Conflict("Only suspended agents can be reinstated for review.")
    meta = {}
    if body.reviewer_notes:
        meta["reviewer_notes"] = body.reviewer_notes
    if body.expires_at:
        meta["expires_at"] = body.expires_at.isoformat()
    transition(
        session, AGENT_VERIFICATION, latest.id, ACTION_TARGET[action], user, reason=body.reason, metadata=meta
    )  # type: ignore[arg-type]
    session.commit()
    session.refresh(profile)
    notify(
        profile.user_id,
        f"AGENT_{action.upper().replace('-', '_')}",
        f"Agent verification is now {profile.verification_status.value}",
    )
    return _reviewer_agent(session, profile, user)


# ---------------------------------------------------------------- reports


@router.get("/reports", response_model=list[ReportOut])
def list_reports(
    user: StaffUser,
    session: SessionDep,
    status: ReportStatus | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[ReportOut]:
    query = select(AgentReport)
    if status:
        query = query.where(AgentReport.status == status)
    rows = session.exec(query.order_by(col(AgentReport.id).desc()).limit(limit)).all()
    return [report_out(session, r, user) for r in rows]


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, user: StaffUser, session: SessionDep) -> ReportOut:
    report = session.get(AgentReport, report_id)
    if not report:
        raise NotFound("Report not found.")
    return report_out(session, report, user)


@router.post("/reports/{report_id}/start-review", response_model=ReportOut)
def start_report_review(report_id: int, user: StaffUser, session: SessionDep) -> ReportOut:
    report = transition(session, AGENT_REPORT, report_id, ReportStatus.IN_REVIEW, user)
    session.commit()
    session.refresh(report)
    return report_out(session, report, user)


@router.post("/reports/{report_id}/{decision}", response_model=ReportOut)
def decide_report(
    report_id: int,
    decision: Literal["resolve", "reject"],
    body: ReportDecisionIn,
    user: StaffUser,
    session: SessionDep,
) -> ReportOut:
    """Resolve or reject a report (reason required). Resolving may also suspend the agent, atomically."""
    target = ReportStatus.RESOLVED if decision == "resolve" else ReportStatus.REJECTED
    meta = {"reviewer_notes": body.reviewer_notes} if body.reviewer_notes else {}
    report = transition(session, AGENT_REPORT, report_id, target, user, reason=body.reason, metadata=meta)
    if body.suspend_agent:
        if decision != "resolve" or not report.agent_id:
            raise Conflict("Only a resolved report about an agent can suspend that agent.")
        latest = presenters.latest_application(session, report.agent_id)
        if latest is None:
            raise Conflict("This agent has no verification to suspend.")
        transition(
            session, AGENT_VERIFICATION, latest.id, AgentVerificationStatus.SUSPENDED, user,  # type: ignore[arg-type]
            reason=f"Report #{report.id}: {body.reason}", metadata={"report_id": report.id},
        )  # fmt: skip
    session.commit()
    session.refresh(report)
    notify(report.reporter_id, "REPORT_DECIDED", f"Your report {report.id} is now {report.status.value}")
    return report_out(session, report, user)


# ---------------------------------------------------------------- audit log


@router.get("/audit-log", response_model=list[AuditOut])
def audit_log(
    user: StaffUser,
    session: SessionDep,
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditOut]:
    query = select(AuditLog)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
    if action:
        query = query.where(AuditLog.action == action)
    rows = session.exec(query.order_by(col(AuditLog.id).desc()).limit(limit)).all()
    names = presenters.user_names(session, [r.actor_user_id for r in rows])
    out = []
    for r in rows:
        item = AuditOut.model_validate(r)
        item.actor_name = names.get(r.actor_user_id) if r.actor_user_id else "System"  # type: ignore[arg-type]
        out.append(item)
    return out
