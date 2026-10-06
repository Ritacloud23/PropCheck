from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import (
    AvailabilityStatus,
    CheckResult,
    DocumentReviewStatus,
    DocumentType,
    MediaType,
    PropertyType,
    PropertyVerificationState,
)
from app.schemas.agents import AgentPublicOut, AgentSummary
from app.schemas.common import Out, TimelineEntry, validate_state


class PropertyCreate(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    description: str = Field(default="", max_length=5000)
    address: str = Field(min_length=5, max_length=300)
    landmark: str | None = Field(default=None, max_length=200)
    state: str
    city: str = Field(min_length=2, max_length=80)
    local_government_area: str | None = Field(default=None, max_length=80)
    area: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=4.0, le=14.0)  # Nigeria's bounding box
    longitude: float | None = Field(default=None, ge=2.5, le=15.0)
    property_type: PropertyType
    bedrooms: int = Field(default=0, ge=0, le=20)
    bathrooms: int = Field(default=0, ge=0, le=20)
    furnished: bool = False
    rent_amount: int = Field(gt=0, le=10_000_000_000)
    agency_fee: int = Field(default=0, ge=0, le=10_000_000_000)
    legal_fee: int = Field(default=0, ge=0, le=10_000_000_000)
    caution_fee: int = Field(default=0, ge=0, le=10_000_000_000)
    other_fees: int = Field(default=0, ge=0, le=10_000_000_000)
    other_fees_description: str | None = Field(default=None, max_length=300)
    # Landlords may nominate a listing agent; agents are always set as their own listing agent.
    listing_agent_id: int | None = None

    @field_validator("state")
    @classmethod
    def _state(cls, v: str) -> str:
        return validate_state(v)


class PropertyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    address: str | None = Field(default=None, min_length=5, max_length=300)
    landmark: str | None = Field(default=None, max_length=200)
    state: str | None = None
    city: str | None = Field(default=None, min_length=2, max_length=80)
    local_government_area: str | None = Field(default=None, max_length=80)
    area: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=4.0, le=14.0)
    longitude: float | None = Field(default=None, ge=2.5, le=15.0)
    property_type: PropertyType | None = None
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    bathrooms: int | None = Field(default=None, ge=0, le=20)
    furnished: bool | None = None
    rent_amount: int | None = Field(default=None, gt=0, le=10_000_000_000)
    agency_fee: int | None = Field(default=None, ge=0, le=10_000_000_000)
    legal_fee: int | None = Field(default=None, ge=0, le=10_000_000_000)
    caution_fee: int | None = Field(default=None, ge=0, le=10_000_000_000)
    other_fees: int | None = Field(default=None, ge=0, le=10_000_000_000)
    other_fees_description: str | None = Field(default=None, max_length=300)
    availability_status: AvailabilityStatus | None = None
    is_listed: bool | None = None

    @field_validator("state")
    @classmethod
    def _state(cls, v: str | None) -> str | None:
        return validate_state(v) if v is not None else v


class MediaOut(Out):
    id: int
    media_type: MediaType
    url: str
    caption: str | None
    created_at: datetime


class DocumentOut(BaseModel):
    """Only ever returned to the property's managers and reviewers."""

    id: int
    document_type: DocumentType
    original_filename: str | None
    review_status: DocumentReviewStatus
    reviewer_notes: str | None
    uploaded_at: datetime
    reviewed_at: datetime | None
    link: str | None  # short-lived signed URL


class VerificationBadge(BaseModel):
    status: PropertyVerificationState  # effective: VERIFIED past expiry is reported as EXPIRED
    is_currently_verified: bool
    reference: str | None
    verified_at: datetime | None
    expires_at: datetime | None


class FeeBreakdown(BaseModel):
    rent_amount: int
    agency_fee: int
    legal_fee: int
    caution_fee: int
    other_fees: int
    other_fees_description: str | None
    total_move_in_cost: int


class PropertyCard(BaseModel):
    id: int
    public_slug: str
    title: str
    state: str
    city: str
    local_government_area: str | None
    area: str | None
    property_type: PropertyType
    bedrooms: int
    bathrooms: int
    furnished: bool
    rent_amount: int
    total_move_in_cost: int
    availability_status: AvailabilityStatus
    cover_photo_url: str | None
    verification: VerificationBadge
    agent: AgentSummary | None
    created_at: datetime


class PropertyDetail(PropertyCard):
    description: str
    address: str
    landmark: str | None
    latitude: float | None
    longitude: float | None
    fees: FeeBreakdown
    media: list[MediaOut]
    agent_profile: AgentPublicOut | None
    is_listed: bool
    share_url: str
    # Private section: only populated for owner / listing agent / reviewers.
    can_manage: bool = False
    documents: list[DocumentOut] | None = None
    owner_user_id: int | None = None
    latest_case_id: int | None = None


class CheckReportItem(BaseModel):
    check_type: str
    label: str
    result: CheckResult
    evidence_note: str | None
    completed_at: datetime | None


class DocumentReportItem(BaseModel):
    document_type: DocumentType
    review_status: DocumentReviewStatus
    reviewed_at: datetime | None


class VerificationReport(BaseModel):
    property_id: int
    property_slug: str
    property_title: str
    status: PropertyVerificationState
    is_currently_verified: bool
    verification_reference: str | None
    submitted_at: datetime | None
    inspection_date: datetime | None
    verified_at: datetime | None
    expires_at: datetime | None
    reviewer_reference: str | None
    checks: list[CheckReportItem]
    what_was_checked: list[str]
    what_was_not_checked: list[str]
    documents_reviewed: list[DocumentReportItem]
    limitations: list[str]
    rejection_reason: str | None
    timeline: list[TimelineEntry]
    agent_verified: bool
    agent_note: str
    disclaimer: str
    payment_warning: str


class ShareOut(BaseModel):
    url: str
    whatsapp_share_url: str
    title: str
    text: str
