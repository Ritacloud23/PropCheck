"""nearby places and areas

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-06 09:30:09.578545
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nearby_place",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=160), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "MARKET", "RESTAURANT", "CHURCH", "CLUB", name="placecategory", native_enum=False, length=40
            ),
            nullable=False,
        ),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("address", sqlmodel.sql.sqltypes.AutoString(length=300), nullable=True),
        sa.Column("state", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
        sa.Column("city", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("local_government_area", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=True),
        sa.Column("area", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("phone_number", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column("website_url", sqlmodel.sql.sqltypes.AutoString(length=300), nullable=True),
        sa.Column("opening_hours", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_nearby_place_category"), "nearby_place", ["category"], unique=False)
    op.create_index(op.f("ix_nearby_place_city"), "nearby_place", ["city"], unique=False)
    op.create_index(op.f("ix_nearby_place_is_active"), "nearby_place", ["is_active"], unique=False)
    op.create_index("ix_nearby_place_lat_lng", "nearby_place", ["latitude", "longitude"], unique=False)
    op.create_index(op.f("ix_nearby_place_state"), "nearby_place", ["state"], unique=False)
    op.create_table(
        "place_report",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nearby_place_id", sa.Integer(), nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column(
            "reason",
            sa.Enum(
                "WRONG_LOCATION",
                "PERMANENTLY_CLOSED",
                "WRONG_OPENING_HOURS",
                "WRONG_PHONE_NUMBER",
                "WRONG_NAME_OR_CATEGORY",
                "DUPLICATE",
                "OTHER",
                name="placereportreason",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column(
            "status",
            sa.Enum("OPEN", "RESOLVED", "REJECTED", name="placereportstatus", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column("reviewer_notes", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["nearby_place_id"],
            ["nearby_place.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_place_report_nearby_place_id"), "place_report", ["nearby_place_id"], unique=False
    )
    op.create_index(op.f("ix_place_report_reporter_id"), "place_report", ["reporter_id"], unique=False)
    op.create_index(op.f("ix_place_report_status"), "place_report", ["status"], unique=False)
    op.add_column(
        "house_search_request", sa.Column("area", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=True)
    )
    op.add_column("property", sa.Column("area", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=True))
    op.create_index(op.f("ix_property_area"), "property", ["area"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_property_area"), table_name="property")
    op.drop_column("property", "area")
    op.drop_column("house_search_request", "area")
    op.drop_index(op.f("ix_place_report_status"), table_name="place_report")
    op.drop_index(op.f("ix_place_report_reporter_id"), table_name="place_report")
    op.drop_index(op.f("ix_place_report_nearby_place_id"), table_name="place_report")
    op.drop_table("place_report")
    op.drop_index(op.f("ix_nearby_place_state"), table_name="nearby_place")
    op.drop_index("ix_nearby_place_lat_lng", table_name="nearby_place")
    op.drop_index(op.f("ix_nearby_place_is_active"), table_name="nearby_place")
    op.drop_index(op.f("ix_nearby_place_city"), table_name="nearby_place")
    op.drop_index(op.f("ix_nearby_place_category"), table_name="nearby_place")
    op.drop_table("nearby_place")
