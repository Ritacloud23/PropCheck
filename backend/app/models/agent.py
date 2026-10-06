from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.models.base import enum_field, str_list_field, ts_field, updated_field
from app.models.enums import AgentVerificationStatus


class AgentProfile(SQLModel, table=True):
    __tablename__ = "agent_profile"
    __table_args__ = tuple(
        Index(f"ix_agent_profile_{c}_gin", c, postgresql_using="gin")
        for c in ("states_covered", "cities_covered", "lgas_covered", "property_types", "service_types")
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    agency_name: str | None = Field(default=None, max_length=160)
    bio: str = Field(default="", max_length=2000)
    profile_photo_url: str | None = Field(default=None, max_length=500)
    phone_number: str = Field(max_length=20)
    whatsapp_number: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    states_covered: list[str] = str_list_field()
    cities_covered: list[str] = str_list_field()
    lgas_covered: list[str] = str_list_field()
    property_types: list[str] = str_list_field()
    service_types: list[str] = str_list_field()
    budget_min: int | None = Field(default=None, ge=0)
    budget_max: int | None = Field(default=None, ge=0)
    years_experience: int = Field(default=0, ge=0, le=60)
    # Mirrors the latest AgentVerification application (the state machine runs on that table).
    verification_status: AgentVerificationStatus = enum_field(
        AgentVerificationStatus, AgentVerificationStatus.DRAFT, index=True
    )
    verification_date: datetime | None = ts_field()
    verification_expiry_date: datetime | None = ts_field()
    display_phone_publicly: bool = Field(default=False)
    display_email_publicly: bool = Field(default=False)
    average_rating: float | None = Field(default=None)
    total_reviews: int = Field(default=0)
    completed_connections: int = Field(default=0)
    response_time_hours: int | None = Field(default=None)
    created_at: datetime = ts_field(default_now=True)
    updated_at: datetime = updated_field()


class AgentVerification(SQLModel, table=True):
    """One application for the Verified Agent badge. History is kept across re-applications."""

    __tablename__ = "agent_verification"

    id: int | None = Field(default=None, primary_key=True)
    agent_profile_id: int = Field(foreign_key="agent_profile.id", index=True)
    submitted_by: int = Field(foreign_key="user.id")
    assigned_reviewer_id: int | None = Field(default=None, foreign_key="user.id")
    # Private storage keys, never exposed directly; served only through signed URLs.
    identity_document_url: str | None = Field(default=None, max_length=500)
    business_document_url: str | None = Field(default=None, max_length=500)
    evidence_notes: str | None = Field(default=None, max_length=2000)
    status: AgentVerificationStatus = enum_field(
        AgentVerificationStatus, AgentVerificationStatus.DRAFT, index=True
    )
    rejection_reason: str | None = Field(default=None, max_length=1000)
    reviewer_notes: str | None = Field(default=None, max_length=2000)
    submitted_at: datetime | None = ts_field()
    verified_at: datetime | None = ts_field()
    expires_at: datetime | None = ts_field()
    created_at: datetime = ts_field(default_now=True)
