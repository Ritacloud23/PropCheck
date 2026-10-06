from datetime import datetime

from sqlalchemy import CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlmodel import Field, SQLModel

from app.models.base import enum_field, ts_field
from app.models.enums import BookingStatus, SlotStatus


class InspectionSlot(SQLModel, table=True):
    __tablename__ = "inspection_slot"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_slot_time_order"),
        # Database-level guarantee: no two live slots for the same property may overlap in time.
        ExcludeConstraint(
            ("property_id", "="),
            (text("tstzrange(start_time, end_time, '[)')"), "&&"),
            using="gist",
            where=text("status <> 'CANCELLED'"),
            name="ex_slot_no_overlap",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    landlord_user_id: int = Field(foreign_key="user.id")
    start_time: datetime = ts_field(nullable=False)
    end_time: datetime = ts_field(nullable=False)
    status: SlotStatus = enum_field(SlotStatus, SlotStatus.OPEN)
    created_at: datetime = ts_field(default_now=True)


class InspectionBooking(SQLModel, table=True):
    __tablename__ = "inspection_booking"
    __table_args__ = (
        # Database-level guarantee: a slot can hold at most one live booking.
        Index(
            "uq_booking_active_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("status IN ('REQUESTED', 'CONFIRMED')"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    slot_id: int = Field(foreign_key="inspection_slot.id", index=True)
    renter_id: int = Field(foreign_key="user.id", index=True)
    status: BookingStatus = enum_field(BookingStatus, BookingStatus.REQUESTED)
    renter_note: str | None = Field(default=None, max_length=1000)
    landlord_note: str | None = Field(default=None, max_length=1000)
    created_at: datetime = ts_field(default_now=True)
    confirmed_at: datetime | None = ts_field()
    completed_at: datetime | None = ts_field()
    cancelled_at: datetime | None = ts_field()
