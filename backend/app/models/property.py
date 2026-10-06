from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel

from app.models.base import enum_field, ts_field, updated_field
from app.models.enums import (
    AvailabilityStatus,
    DocumentReviewStatus,
    DocumentType,
    MediaType,
    PropertyType,
    PropertyVerificationState,
)


def naira_field() -> Any:
    return Field(default=0, sa_column=Column(BigInteger, nullable=False, default=0))


class Property(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_user_id: int = Field(foreign_key="user.id", index=True)
    listing_agent_id: int | None = Field(default=None, foreign_key="agent_profile.id", index=True)
    title: str = Field(max_length=160)
    description: str = Field(default="", max_length=5000)
    address: str = Field(max_length=300)
    landmark: str | None = Field(default=None, max_length=200)
    city: str = Field(max_length=80, index=True)
    local_government_area: str | None = Field(default=None, max_length=80)
    area: str | None = Field(default=None, max_length=80, index=True)  # neighbourhood, e.g. Lekki
    state: str = Field(max_length=40, index=True)
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    property_type: PropertyType = enum_field(PropertyType, index=True)
    bedrooms: int = Field(default=0)
    bathrooms: int = Field(default=0)
    furnished: bool = Field(default=False)
    # All money in whole naira.
    rent_amount: int = naira_field()
    agency_fee: int = naira_field()
    legal_fee: int = naira_field()
    caution_fee: int = naira_field()
    other_fees: int = naira_field()
    other_fees_description: str | None = Field(default=None, max_length=300)
    total_move_in_cost: int = naira_field()
    availability_status: AvailabilityStatus = enum_field(AvailabilityStatus, AvailabilityStatus.AVAILABLE)
    is_listed: bool = Field(default=True)
    public_slug: str = Field(max_length=200, unique=True, index=True)
    # Denormalised from the latest VerificationCase so search can filter cheaply.
    verification_status: PropertyVerificationState = enum_field(
        PropertyVerificationState, PropertyVerificationState.NOT_SUBMITTED, index=True
    )
    verification_expires_at: datetime | None = ts_field()
    created_at: datetime = ts_field(default_now=True)
    updated_at: datetime = updated_field()


class PropertyMedia(SQLModel, table=True):
    __tablename__ = "property_media"

    id: int | None = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    media_type: MediaType = enum_field(MediaType, MediaType.PHOTO)
    url: str = Field(max_length=500)
    caption: str | None = Field(default=None, max_length=200)
    created_at: datetime = ts_field(default_now=True)


class PropertyDocument(SQLModel, table=True):
    """Supporting documents are PRIVATE. `url` holds a private storage key, never a public URL."""

    __tablename__ = "property_document"

    id: int | None = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    document_type: DocumentType = enum_field(DocumentType)
    url: str = Field(max_length=500)
    original_filename: str | None = Field(default=None, max_length=255)
    uploaded_by: int = Field(foreign_key="user.id")
    review_status: DocumentReviewStatus = enum_field(DocumentReviewStatus, DocumentReviewStatus.UPLOADED)
    reviewer_notes: str | None = Field(default=None, max_length=1000)
    uploaded_at: datetime = ts_field(default_now=True)
    reviewed_at: datetime | None = ts_field()
