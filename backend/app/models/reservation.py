from datetime import datetime

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel

from app.models.base import enum_field, ts_field
from app.models.enums import ReservationStatus


class Reservation(SQLModel, table=True):
    """TEST/DEMO reservation. Not escrow, not legally protected; no real money moves."""

    id: int | None = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    renter_id: int = Field(foreign_key="user.id", index=True)
    amount: int = Field(sa_column=Column(BigInteger, nullable=False))
    payment_reference: str | None = Field(default=None, max_length=80, unique=True)
    payment_provider: str | None = Field(default=None, max_length=30)
    status: ReservationStatus = enum_field(ReservationStatus, ReservationStatus.PENDING_PAYMENT, index=True)
    terms_version: str = Field(max_length=40)
    created_at: datetime = ts_field(default_now=True)
    paid_at: datetime | None = ts_field()
    released_at: datetime | None = ts_field()
    refunded_at: datetime | None = ts_field()
    refund_requested_at: datetime | None = ts_field()
    refund_request_reason: str | None = Field(default=None, max_length=1000)
    cancellation_reason: str | None = Field(default=None, max_length=1000)
