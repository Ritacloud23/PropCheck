from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.reference import active_states, normalize_ng_phone

T = TypeVar("T")

DISCLAIMER = (
    "PropCheck verifies the documents, identity information and inspection evidence listed in this "
    "report. It is not a substitute for a formal title search, legal advice or an official "
    "land-registry search. Users should verify payment terms before sending money."
)
PAYMENT_WARNING = "Do not send money before confirming the property, agent authority and payment terms."


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ReasonIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class RequiredReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class AuditOut(Out):
    id: int
    actor_user_id: int | None
    actor_name: str | None = None
    entity_type: str
    entity_id: int
    action: str
    from_status: str | None
    to_status: str | None
    reason: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class TimelineEntry(BaseModel):
    """Public-safe audit view: no actor identities."""

    action: str
    from_status: str | None
    to_status: str | None
    at: datetime


def validate_phone(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    return normalize_ng_phone(v)


def validate_state(v: str) -> str:
    if v not in active_states():
        raise ValueError(f"PropCheck does not cover {v} yet. Available: {', '.join(active_states())}.")
    return v


def ensure_aware(v: datetime | None) -> datetime | None:
    if v is not None and v.tzinfo is None:
        return v.replace(tzinfo=UTC)
    return v


class PhoneMixin(BaseModel):
    @field_validator("phone", "phone_number", "whatsapp_number", mode="before", check_fields=False)
    @classmethod
    def _phones(cls, v: Any) -> Any:
        return validate_phone(v) if isinstance(v, str) else v
