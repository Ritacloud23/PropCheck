"""Schemas for verification cases, inspections, house-search requests, reservations and reports."""

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import (
    BookingStatus,
    CheckResult,
    CheckType,
    DocumentReviewStatus,
    EnquiryStatus,
    FurnishedPreference,
    HouseSearchStatus,
    PropertyType,
    Purpose,
    ReportReason,
    ReportStatus,
    ReservationStatus,
    SlotStatus,
    VerificationStatus,
)
from app.schemas.agents import AgentPublicOut
from app.schemas.common import Out, PhoneMixin, ensure_aware, validate_state
from app.schemas.properties import DocumentOut

# ------------------------------------------------------------------ verification


class PropertyRef(BaseModel):
    id: int
    title: str
    public_slug: str
    state: str
    city: str


class CheckOut(Out):
    id: int
    check_type: CheckType
    label: str = ""
    result: CheckResult
    evidence_note: str | None
    document_url: str | None
    completed_by: int | None
    completed_at: datetime | None


class CaseOut(BaseModel):
    id: int
    property: PropertyRef
    status: VerificationStatus
    effective_status: VerificationStatus
    verification_reference: str
    submitted_by: int
    submitted_by_name: str | None
    assigned_reviewer_id: int | None
    submitted_at: datetime | None
    inspection_booked_at: datetime | None
    inspection_scheduled_for: datetime | None
    inspected_at: datetime | None
    verified_at: datetime | None
    expires_at: datetime | None
    rejection_reason: str | None
    reviewer_notes: str | None
    created_at: datetime
    checks: list[CheckOut]
    documents: list[DocumentOut]
    allowed_transitions: list[str]
    listing_agent: AgentPublicOut | None = None


class CaseTransitionIn(BaseModel):
    to_status: VerificationStatus
    reason: str | None = Field(default=None, max_length=1000)
    reviewer_notes: str | None = Field(default=None, max_length=4000)
    expires_at: datetime | None = None
    inspection_scheduled_for: datetime | None = None
    inspected_at: datetime | None = None

    @field_validator("expires_at", "inspection_scheduled_for", "inspected_at")
    @classmethod
    def _aware(cls, v: datetime | None) -> datetime | None:
        return ensure_aware(v)


class CheckIn(BaseModel):
    check_type: CheckType
    result: CheckResult
    evidence_note: str | None = Field(default=None, max_length=2000)
    document_id: int | None = None


class DocumentReviewIn(BaseModel):
    review_status: DocumentReviewStatus
    reviewer_notes: str | None = Field(default=None, max_length=1000)

    @field_validator("review_status")
    @classmethod
    def _not_uploaded(cls, v: DocumentReviewStatus) -> DocumentReviewStatus:
        if v == DocumentReviewStatus.UPLOADED:
            raise ValueError("Choose REVIEWED, ACCEPTED or REJECTED.")
        return v


# ------------------------------------------------------------------ inspections


class SlotIn(BaseModel):
    start_time: datetime
    end_time: datetime

    @field_validator("start_time", "end_time")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        return ensure_aware(v)  # type: ignore[return-value]

    @model_validator(mode="after")
    def _order(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        if (self.end_time - self.start_time).total_seconds() > 4 * 3600:
            raise ValueError("An inspection slot cannot be longer than 4 hours.")
        return self


class SlotOut(Out):
    id: int
    property_id: int
    start_time: datetime
    end_time: datetime
    status: SlotStatus


class BookingIn(BaseModel):
    slot_id: int
    renter_note: str | None = Field(default=None, max_length=1000)


class BookingOut(BaseModel):
    id: int
    property: PropertyRef
    slot_id: int
    start_time: datetime
    end_time: datetime
    status: BookingStatus
    renter_note: str | None
    landlord_note: str | None
    created_at: datetime
    confirmed_at: datetime | None
    completed_at: datetime | None
    # Renter contact, only visible to the property's managers.
    renter_name: str | None = None
    renter_phone: str | None = None
    allowed_actions: list[str] = []


# ------------------------------------------------------------------ house-search


class HouseSearchIn(PhoneMixin):
    name: str = Field(min_length=2, max_length=120)
    phone: str
    whatsapp_number: str | None = None
    email: EmailStr | None = None
    state: str
    city: str = Field(min_length=2, max_length=80)
    local_government_area: str | None = Field(default=None, max_length=80)
    area: str | None = Field(default=None, max_length=80)
    property_type: PropertyType
    bedrooms: int = Field(default=1, ge=0, le=20)
    budget_min: int = Field(ge=0)
    budget_max: int = Field(gt=0)
    purpose: Purpose = Purpose.RENT
    preferred_move_in_date: date | None = None
    furnished_preference: FurnishedPreference = FurnishedPreference.EITHER
    description: str | None = Field(default=None, max_length=2000)
    consent_to_share: bool

    @field_validator("state")
    @classmethod
    def _state(cls, v: str) -> str:
        return validate_state(v)

    @field_validator("consent_to_share")
    @classmethod
    def _consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("We need your consent to share this request with selected agents.")
        return v

    @model_validator(mode="after")
    def _budget(self):
        if self.budget_min > self.budget_max:
            raise ValueError("Minimum budget cannot be more than maximum budget.")
        return self


class EnquiryOut(BaseModel):
    id: int
    house_search_request_id: int
    agent_id: int
    agent_name: str | None = None
    message: str | None
    status: EnquiryStatus
    created_at: datetime
    responded_at: datetime | None


class HouseSearchOut(BaseModel):
    id: int
    renter_id: int
    name: str
    phone: str
    whatsapp_number: str | None
    email: str | None
    state: str
    city: str
    local_government_area: str | None
    area: str | None
    property_type: PropertyType
    bedrooms: int
    budget_min: int
    budget_max: int
    purpose: Purpose
    preferred_move_in_date: date | None
    furnished_preference: FurnishedPreference
    description: str | None
    consent_to_share: bool
    status: HouseSearchStatus
    assigned_agent_id: int | None
    assigned_agent: AgentPublicOut | None = None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    enquiries: list[EnquiryOut] = []
    allowed_actions: list[str] = []


class AssignIn(BaseModel):
    agent_id: int
    note: str | None = Field(default=None, max_length=1000)


class RespondIn(BaseModel):
    message: str = Field(min_length=5, max_length=2000)


class AgentEnquiryOut(BaseModel):
    """What an assigned agent sees: the request the renter consented to share."""

    id: int
    status: EnquiryStatus
    message: str | None
    created_at: datetime
    responded_at: datetime | None
    request: HouseSearchOut


# ------------------------------------------------------------------ reservations


RESERVATION_TERMS = [
    "This is a TEST/DEMO reservation. No real money is collected and Paystack runs in test mode only.",
    "PropCheck is not an escrow service and this workflow is not legally protected escrow.",
    "The reservation amount is held in the demo as PENDING_RELEASE until you confirm you have received the keys.",
    "Once you confirm keys, the reservation is RELEASED and can no longer be refunded through this workflow.",
    "Before keys are confirmed you may request a refund; a PropCheck reviewer decides and records the reason.",
    "Do not send money before confirming the property, agent authority and payment terms.",
]


class ReservationIn(BaseModel):
    property_id: int
    accept_terms: bool

    @field_validator("accept_terms")
    @classmethod
    def _terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the demo reservation terms.")
        return v


class ReservationOut(BaseModel):
    id: int
    property: PropertyRef
    renter_id: int
    renter_name: str | None = None
    amount: int
    payment_reference: str | None
    payment_provider: str | None
    status: ReservationStatus
    terms_version: str
    terms: list[str]
    created_at: datetime
    paid_at: datetime | None
    released_at: datetime | None
    refunded_at: datetime | None
    refund_requested_at: datetime | None
    refund_request_reason: str | None
    cancellation_reason: str | None
    is_test_mode: bool = True
    allowed_actions: list[str] = []


class PayOut(BaseModel):
    reservation: ReservationOut
    authorization_url: str | None  # set when a real Paystack TEST checkout must be completed
    provider: str


class VerifyPaymentIn(BaseModel):
    reference: str = Field(min_length=5, max_length=80)


# ------------------------------------------------------------------ reports


class ReportOut(BaseModel):
    id: int
    reporter_id: int
    reporter_name: str | None = None
    agent_id: int | None
    agent_name: str | None = None
    property: PropertyRef | None = None
    reason: ReportReason
    description: str
    has_evidence: bool
    evidence_link: str | None = None
    status: ReportStatus
    reviewer_notes: str | None
    resolution_reason: str | None
    created_at: datetime
    resolved_at: datetime | None


class ReportDecisionIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    reviewer_notes: str | None = Field(default=None, max_length=4000)
    suspend_agent: bool = False
