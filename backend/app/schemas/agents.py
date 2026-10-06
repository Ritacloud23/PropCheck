from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import AgentVerificationStatus, PropertyType, ServiceType
from app.schemas.common import Out, PhoneMixin, validate_state


class AgentProfileBase(PhoneMixin):
    agency_name: str | None = Field(default=None, max_length=160)
    bio: str = Field(default="", max_length=2000)
    phone_number: str
    whatsapp_number: str | None = None
    email: EmailStr | None = None
    states_covered: list[str] = Field(min_length=1, max_length=37)
    cities_covered: list[str] = Field(default_factory=list, max_length=50)
    lgas_covered: list[str] = Field(default_factory=list, max_length=50)
    property_types: list[PropertyType] = Field(default_factory=list)
    service_types: list[ServiceType] = Field(default_factory=list)
    budget_min: int | None = Field(default=None, ge=0)
    budget_max: int | None = Field(default=None, ge=0)
    years_experience: int = Field(default=0, ge=0, le=60)
    # Phone and WhatsApp are only shown publicly when this is explicitly true.
    display_phone_publicly: bool = False
    display_email_publicly: bool = False

    @field_validator("states_covered")
    @classmethod
    def _states(cls, v: list[str]) -> list[str]:
        return [validate_state(s) for s in v]

    @model_validator(mode="after")
    def _budget(self):
        if self.budget_min is not None and self.budget_max is not None and self.budget_min > self.budget_max:
            raise ValueError("budget_min cannot be greater than budget_max")
        return self


class AgentProfileCreate(AgentProfileBase):
    pass


class AgentProfileUpdate(PhoneMixin):
    agency_name: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=2000)
    phone_number: str | None = None
    whatsapp_number: str | None = None
    email: EmailStr | None = None
    states_covered: list[str] | None = None
    cities_covered: list[str] | None = None
    lgas_covered: list[str] | None = None
    property_types: list[PropertyType] | None = None
    service_types: list[ServiceType] | None = None
    budget_min: int | None = Field(default=None, ge=0)
    budget_max: int | None = Field(default=None, ge=0)
    years_experience: int | None = Field(default=None, ge=0, le=60)
    display_phone_publicly: bool | None = None
    display_email_publicly: bool | None = None

    @field_validator("states_covered")
    @classmethod
    def _states(cls, v: list[str] | None) -> list[str] | None:
        return [validate_state(s) for s in v] if v is not None else v


class AgentSummary(BaseModel):
    """Small public card used inside property responses."""

    id: int
    name: str
    agency_name: str | None
    profile_photo_url: str | None
    verification_status: AgentVerificationStatus
    is_verified: bool
    verification_expiry_date: datetime | None


class AgentPublicOut(BaseModel):
    id: int
    name: str
    agency_name: str | None
    bio: str
    profile_photo_url: str | None
    # Contact fields are None unless the agent consented to public display.
    phone_number: str | None
    whatsapp_number: str | None
    email: str | None
    contact_public: bool
    states_covered: list[str]
    cities_covered: list[str]
    lgas_covered: list[str]
    property_types: list[str]
    service_types: list[str]
    budget_min: int | None
    budget_max: int | None
    years_experience: int
    verification_status: AgentVerificationStatus  # effective (expired shows EXPIRED)
    is_verified: bool
    verification_date: datetime | None
    verification_expiry_date: datetime | None
    active_listings: int
    completed_connections: int
    average_rating: float | None
    total_reviews: int
    complaint_status: str
    response_time_hours: int | None
    joined_at: datetime


class AgentVerificationOut(Out):
    id: int
    status: AgentVerificationStatus
    evidence_notes: str | None
    submitted_at: datetime | None
    verified_at: datetime | None
    expires_at: datetime | None
    rejection_reason: str | None
    reviewer_notes: str | None
    assigned_reviewer_id: int | None
    has_identity_document: bool = False
    has_business_document: bool = False
    # Signed, short-lived links. Only populated for the agent themself or reviewers.
    identity_document_link: str | None = None
    business_document_link: str | None = None
    created_at: datetime


class AgentPrivateOut(AgentPublicOut):
    """The agent's own view (and reviewers'): includes contact details regardless of consent."""

    user_id: int
    private_phone_number: str
    private_whatsapp_number: str | None
    private_email: str | None
    display_phone_publicly: bool
    display_email_publicly: bool
    latest_application: AgentVerificationOut | None


class ReviewerAgentOut(AgentPrivateOut):
    account_email: str
    open_reports: int
    allowed_actions: list[str]


class AgentDecisionIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
    reviewer_notes: str | None = Field(default=None, max_length=2000)
    expires_at: datetime | None = None
