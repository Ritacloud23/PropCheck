from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PlaceCategory, PlaceReportReason, PlaceReportStatus


class NearbyPlaceOut(BaseModel):
    """Public view of a place. Internal fields (is_active, source, timestamps) are not exposed."""

    id: int
    name: str
    category: PlaceCategory
    description: str | None
    address: str | None
    area: str | None
    city: str
    local_government_area: str | None
    state: str
    latitude: float
    longitude: float
    phone_number: str | None
    website_url: str | None
    opening_hours: str | None
    distance_km: float
    distance_m: int
    distance_label: str
    is_demo_data: bool


class GeoPoint(BaseModel):
    latitude: float
    longitude: float


class NearbyResponse(BaseModel):
    items: list[NearbyPlaceOut]
    count: int
    center: GeoPoint
    radius_km: float
    category: PlaceCategory | None
    notice: str


class PlaceReportIn(BaseModel):
    reason: PlaceReportReason
    description: str | None = Field(default=None, max_length=2000)


class PlaceReportOut(BaseModel):
    id: int
    nearby_place_id: int
    place_name: str
    place_category: PlaceCategory
    place_area: str | None
    place_city: str
    reason: PlaceReportReason
    description: str | None
    status: PlaceReportStatus
    reporter_name: str | None = None
    reviewer_notes: str | None = None
    place_is_active: bool | None = None
    created_at: datetime
    resolved_at: datetime | None


class PlaceReportDecisionIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    reviewer_notes: str | None = Field(default=None, max_length=2000)
    deactivate_place: bool = False
