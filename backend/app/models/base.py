from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import Column, DateTime, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field


def utcnow() -> datetime:
    return datetime.now(UTC)


def enum_field(
    enum_cls: type[Enum], default: Any = None, *, index: bool = False, nullable: bool = False
) -> Any:
    """Enum stored as VARCHAR (no native Postgres ENUM types -> painless migrations)."""
    return Field(
        default=default,
        sa_column=Column(
            SAEnum(enum_cls, native_enum=False, length=40, validate_strings=True),
            nullable=nullable,
            index=index,
        ),
    )


def ts_field(*, nullable: bool = True, default_now: bool = False, index: bool = False) -> Any:
    if default_now:
        return Field(
            default_factory=utcnow,
            sa_column=Column(DateTime(timezone=True), nullable=False, default=utcnow, index=index),
        )
    return Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=nullable, index=index))


def str_list_field() -> Any:
    return Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(80)), nullable=False, server_default="{}"),
    )


def updated_field() -> Any:
    return Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow),
    )
