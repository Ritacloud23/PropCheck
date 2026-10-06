from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.models.base import enum_field, ts_field, updated_field
from app.models.enums import PlaceCategory, PlaceReportReason, PlaceReportStatus


class NearbyPlace(SQLModel, table=True):
    """A point of interest near listings. Informational only: NOT verified by PropCheck."""

    __tablename__ = "nearby_place"
    # Bounding-box prefilter for radius searches uses these two columns together.
    __table_args__ = (Index("ix_nearby_place_lat_lng", "latitude", "longitude"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=160)
    category: PlaceCategory = enum_field(PlaceCategory, index=True)
    description: str | None = Field(default=None, max_length=1000)
    address: str | None = Field(default=None, max_length=300)
    state: str = Field(max_length=40, index=True)
    city: str = Field(max_length=80, index=True)
    local_government_area: str | None = Field(default=None, max_length=80)
    area: str | None = Field(default=None, max_length=80)
    latitude: float
    longitude: float
    phone_number: str | None = Field(default=None, max_length=20)
    website_url: str | None = Field(default=None, max_length=300)
    opening_hours: str | None = Field(default=None, max_length=200)
    is_active: bool = Field(default=True, index=True)
    # Where the record came from: DEMO_SEED, MANUAL, OSM, ...
    source: str = Field(default="MANUAL", max_length=30)
    created_at: datetime = ts_field(default_now=True)
    updated_at: datetime = updated_field()


class PlaceReport(SQLModel, table=True):
    """A user's report that a nearby place's details are wrong."""

    __tablename__ = "place_report"

    id: int | None = Field(default=None, primary_key=True)
    nearby_place_id: int = Field(foreign_key="nearby_place.id", index=True)
    reporter_id: int = Field(foreign_key="user.id", index=True)
    reason: PlaceReportReason = enum_field(PlaceReportReason)
    description: str | None = Field(default=None, max_length=2000)
    status: PlaceReportStatus = enum_field(PlaceReportStatus, PlaceReportStatus.OPEN, index=True)
    reviewer_notes: str | None = Field(default=None, max_length=2000)
    created_at: datetime = ts_field(default_now=True)
    resolved_at: datetime | None = ts_field()
