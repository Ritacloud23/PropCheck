from datetime import datetime

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.models.base import enum_field, ts_field
from app.models.enums import ReportReason, ReportStatus


class AgentReport(SQLModel, table=True):
    """A report about an agent and/or a property."""

    __tablename__ = "agent_report"
    __table_args__ = (
        CheckConstraint("agent_id IS NOT NULL OR property_id IS NOT NULL", name="ck_report_has_target"),
    )

    id: int | None = Field(default=None, primary_key=True)
    reporter_id: int = Field(foreign_key="user.id", index=True)
    agent_id: int | None = Field(default=None, foreign_key="agent_profile.id", index=True)
    property_id: int | None = Field(default=None, foreign_key="property.id", index=True)
    reason: ReportReason = enum_field(ReportReason)
    description: str = Field(max_length=4000)
    evidence_url: str | None = Field(default=None, max_length=500)  # private storage key
    status: ReportStatus = enum_field(ReportStatus, ReportStatus.OPEN, index=True)
    reviewer_notes: str | None = Field(default=None, max_length=4000)
    resolution_reason: str | None = Field(default=None, max_length=1000)
    created_at: datetime = ts_field(default_now=True)
    resolved_at: datetime | None = ts_field()
