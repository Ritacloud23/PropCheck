from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import enum_field, ts_field, updated_field
from app.models.enums import Role


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=120)
    email: str = Field(max_length=254, unique=True, index=True)
    phone: str | None = Field(default=None, max_length=20)
    password_hash: str = Field(max_length=255)
    role: Role = enum_field(Role, Role.RENTER, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = ts_field(default_now=True)
    updated_at: datetime = updated_field()
