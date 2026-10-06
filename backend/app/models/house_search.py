from datetime import date, datetime
from typing import Any

from sqlalchemy import Column, Date
from sqlmodel import Field, SQLModel

from app.models.base import enum_field, ts_field, updated_field
from app.models.enums import EnquiryStatus, FurnishedPreference, HouseSearchStatus, PropertyType, Purpose


def _date_field() -> Any:
    return Field(default=None, sa_column=Column(Date, nullable=True))


class HouseSearchRequest(SQLModel, table=True):
    __tablename__ = "house_search_request"

    id: int | None = Field(default=None, primary_key=True)
    renter_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(max_length=120)
    phone: str = Field(max_length=20)
    whatsapp_number: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    state: str = Field(max_length=40, index=True)
    city: str = Field(max_length=80)
    local_government_area: str | None = Field(default=None, max_length=80)
    area: str | None = Field(default=None, max_length=80)
    property_type: PropertyType = enum_field(PropertyType)
    bedrooms: int = Field(default=0)
    budget_min: int = Field(default=0)
    budget_max: int = Field(default=0)
    purpose: Purpose = enum_field(Purpose, Purpose.RENT)
    preferred_move_in_date: date | None = _date_field()
    furnished_preference: FurnishedPreference = enum_field(FurnishedPreference, FurnishedPreference.EITHER)
    description: str | None = Field(default=None, max_length=2000)
    consent_to_share: bool = Field(default=False)
    status: HouseSearchStatus = enum_field(HouseSearchStatus, HouseSearchStatus.SUBMITTED, index=True)
    assigned_agent_id: int | None = Field(default=None, foreign_key="agent_profile.id", index=True)
    cancellation_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = ts_field(default_now=True)
    updated_at: datetime = updated_field()


class AgentEnquiry(SQLModel, table=True):
    __tablename__ = "agent_enquiry"

    id: int | None = Field(default=None, primary_key=True)
    house_search_request_id: int = Field(foreign_key="house_search_request.id", index=True)
    agent_id: int = Field(foreign_key="agent_profile.id", index=True)
    message: str | None = Field(default=None, max_length=2000)
    status: EnquiryStatus = enum_field(EnquiryStatus, EnquiryStatus.PENDING)
    created_at: datetime = ts_field(default_now=True)
    responded_at: datetime | None = ts_field()
