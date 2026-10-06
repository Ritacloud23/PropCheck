from datetime import datetime
from typing import Any

from sqlalchemy import Column, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base import ts_field


class AuditLog(SQLModel, table=True):
    """Append-only. There are no update or delete code paths for this table."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    id: int | None = Field(default=None, primary_key=True)
    actor_user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    entity_type: str = Field(max_length=40)
    entity_id: int
    action: str = Field(max_length=60)
    from_status: str | None = Field(default=None, max_length=40)
    to_status: str | None = Field(default=None, max_length=40)
    reason: str | None = Field(default=None, max_length=1000)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )
    created_at: datetime = ts_field(default_now=True, index=True)
