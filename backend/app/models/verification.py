from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import enum_field, ts_field
from app.models.enums import CheckResult, CheckType, VerificationStatus


class VerificationCase(SQLModel, table=True):
    __tablename__ = "verification_case"

    id: int | None = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    submitted_by: int = Field(foreign_key="user.id")
    assigned_reviewer_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    status: VerificationStatus = enum_field(VerificationStatus, VerificationStatus.DRAFT, index=True)
    verification_reference: str = Field(max_length=30, unique=True)
    submitted_at: datetime | None = ts_field()
    inspection_booked_at: datetime | None = ts_field()
    inspection_scheduled_for: datetime | None = ts_field()
    inspected_at: datetime | None = ts_field()
    verified_at: datetime | None = ts_field()
    expires_at: datetime | None = ts_field()
    rejection_reason: str | None = Field(default=None, max_length=1000)
    reviewer_notes: str | None = Field(default=None, max_length=4000)
    created_at: datetime = ts_field(default_now=True)


class VerificationCheck(SQLModel, table=True):
    __tablename__ = "verification_check"
    __table_args__ = (UniqueConstraint("verification_case_id", "check_type", name="uq_case_check_type"),)

    id: int | None = Field(default=None, primary_key=True)
    verification_case_id: int = Field(foreign_key="verification_case.id", index=True)
    check_type: CheckType = enum_field(CheckType)
    result: CheckResult = enum_field(CheckResult, CheckResult.NOT_STARTED)
    evidence_note: str | None = Field(default=None, max_length=2000)
    document_url: str | None = Field(default=None, max_length=500)
    completed_by: int | None = Field(default=None, foreign_key="user.id")
    completed_at: datetime | None = ts_field()
