"""initial

Revision ID: 0001
Revises:
Create Date: 2026-10-06 06:16:55.874114
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Needed for the inspection-slot EXCLUDE constraint (integer equality inside a GiST index).
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=254), nullable=False),
        sa.Column("phone", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column("password_hash", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "RENTER", "AGENT", "LANDLORD", "REVIEWER", "ADMIN", name="role", native_enum=False, length=40
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)
    op.create_index(op.f("ix_user_role"), "user", ["role"], unique=False)
    op.create_table(
        "agent_profile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("agency_name", sqlmodel.sql.sqltypes.AutoString(length=160), nullable=True),
        sa.Column("bio", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False),
        sa.Column("profile_photo_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("phone_number", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("whatsapp_number", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=254), nullable=True),
        sa.Column(
            "states_covered", postgresql.ARRAY(sa.String(length=80)), server_default="{}", nullable=False
        ),
        sa.Column(
            "cities_covered", postgresql.ARRAY(sa.String(length=80)), server_default="{}", nullable=False
        ),
        sa.Column(
            "lgas_covered", postgresql.ARRAY(sa.String(length=80)), server_default="{}", nullable=False
        ),
        sa.Column(
            "property_types", postgresql.ARRAY(sa.String(length=80)), server_default="{}", nullable=False
        ),
        sa.Column(
            "service_types", postgresql.ARRAY(sa.String(length=80)), server_default="{}", nullable=False
        ),
        sa.Column("budget_min", sa.Integer(), nullable=True),
        sa.Column("budget_max", sa.Integer(), nullable=True),
        sa.Column("years_experience", sa.Integer(), nullable=False),
        sa.Column(
            "verification_status",
            sa.Enum(
                "DRAFT",
                "SUBMITTED",
                "IN_REVIEW",
                "VERIFIED",
                "REJECTED",
                "SUSPENDED",
                "EXPIRED",
                name="agentverificationstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("verification_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("display_phone_publicly", sa.Boolean(), nullable=False),
        sa.Column("display_email_publicly", sa.Boolean(), nullable=False),
        sa.Column("average_rating", sa.Float(), nullable=True),
        sa.Column("total_reviews", sa.Integer(), nullable=False),
        sa.Column("completed_connections", sa.Integer(), nullable=False),
        sa.Column("response_time_hours", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_profile_cities_covered_gin",
        "agent_profile",
        ["cities_covered"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_agent_profile_lgas_covered_gin",
        "agent_profile",
        ["lgas_covered"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_agent_profile_property_types_gin",
        "agent_profile",
        ["property_types"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_agent_profile_service_types_gin",
        "agent_profile",
        ["service_types"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_agent_profile_states_covered_gin",
        "agent_profile",
        ["states_covered"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(op.f("ix_agent_profile_user_id"), "agent_profile", ["user_id"], unique=True)
    op.create_index(
        op.f("ix_agent_profile_verification_status"), "agent_profile", ["verification_status"], unique=False
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("entity_type", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(length=60), nullable=False),
        sa.Column("from_status", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=True),
        sa.Column("to_status", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=True),
        sa.Column("reason", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column(
            "metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_entity", "audit_log", ["entity_type", "entity_id"], unique=False)
    op.create_index(op.f("ix_audit_log_actor_user_id"), "audit_log", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_audit_log_created_at"), "audit_log", ["created_at"], unique=False)
    op.create_table(
        "agent_verification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_profile_id", sa.Integer(), nullable=False),
        sa.Column("submitted_by", sa.Integer(), nullable=False),
        sa.Column("assigned_reviewer_id", sa.Integer(), nullable=True),
        sa.Column("identity_document_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("business_document_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("evidence_notes", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "SUBMITTED",
                "IN_REVIEW",
                "VERIFIED",
                "REJECTED",
                "SUSPENDED",
                "EXPIRED",
                name="agentverificationstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("rejection_reason", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("reviewer_notes", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_profile_id"],
            ["agent_profile.id"],
        ),
        sa.ForeignKeyConstraint(
            ["assigned_reviewer_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_verification_agent_profile_id"),
        "agent_verification",
        ["agent_profile_id"],
        unique=False,
    )
    op.create_index(op.f("ix_agent_verification_status"), "agent_verification", ["status"], unique=False)
    op.create_table(
        "house_search_request",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("renter_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column("phone", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("whatsapp_number", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=254), nullable=True),
        sa.Column("state", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
        sa.Column("city", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("local_government_area", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=True),
        sa.Column(
            "property_type",
            sa.Enum(
                "SELF_CONTAINED",
                "MINI_FLAT",
                "FLAT",
                "DUPLEX",
                "TERRACE",
                "BUNGALOW",
                "ROOM",
                "SHOP",
                "OFFICE",
                "LAND",
                name="propertytype",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column("budget_min", sa.Integer(), nullable=False),
        sa.Column("budget_max", sa.Integer(), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum("RENT", "PURCHASE", name="purpose", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column("preferred_move_in_date", sa.Date(), nullable=True),
        sa.Column(
            "furnished_preference",
            sa.Enum(
                "FURNISHED", "UNFURNISHED", "EITHER", name="furnishedpreference", native_enum=False, length=40
            ),
            nullable=False,
        ),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column("consent_to_share", sa.Boolean(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "SUBMITTED",
                "MATCHING",
                "ASSIGNED",
                "CONTACTED",
                "COMPLETED",
                "CANCELLED",
                name="housesearchstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("assigned_agent_id", sa.Integer(), nullable=True),
        sa.Column("cancellation_reason", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_agent_id"],
            ["agent_profile.id"],
        ),
        sa.ForeignKeyConstraint(
            ["renter_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_house_search_request_assigned_agent_id"),
        "house_search_request",
        ["assigned_agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_house_search_request_renter_id"), "house_search_request", ["renter_id"], unique=False
    )
    op.create_index(op.f("ix_house_search_request_state"), "house_search_request", ["state"], unique=False)
    op.create_index(op.f("ix_house_search_request_status"), "house_search_request", ["status"], unique=False)
    op.create_table(
        "property",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("listing_agent_id", sa.Integer(), nullable=True),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=160), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=5000), nullable=False),
        sa.Column("address", sqlmodel.sql.sqltypes.AutoString(length=300), nullable=False),
        sa.Column("landmark", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
        sa.Column("city", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("local_government_area", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=True),
        sa.Column("state", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "property_type",
            sa.Enum(
                "SELF_CONTAINED",
                "MINI_FLAT",
                "FLAT",
                "DUPLEX",
                "TERRACE",
                "BUNGALOW",
                "ROOM",
                "SHOP",
                "OFFICE",
                "LAND",
                name="propertytype",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column("bathrooms", sa.Integer(), nullable=False),
        sa.Column("furnished", sa.Boolean(), nullable=False),
        sa.Column("rent_amount", sa.BigInteger(), nullable=False),
        sa.Column("agency_fee", sa.BigInteger(), nullable=False),
        sa.Column("legal_fee", sa.BigInteger(), nullable=False),
        sa.Column("caution_fee", sa.BigInteger(), nullable=False),
        sa.Column("other_fees", sa.BigInteger(), nullable=False),
        sa.Column("other_fees_description", sqlmodel.sql.sqltypes.AutoString(length=300), nullable=True),
        sa.Column("total_move_in_cost", sa.BigInteger(), nullable=False),
        sa.Column(
            "availability_status",
            sa.Enum(
                "AVAILABLE",
                "RESERVED",
                "LET",
                "UNAVAILABLE",
                name="availabilitystatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("is_listed", sa.Boolean(), nullable=False),
        sa.Column("public_slug", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column(
            "verification_status",
            sa.Enum(
                "NOT_SUBMITTED",
                "DRAFT",
                "SUBMITTED",
                "IN_REVIEW",
                "INSPECTION_BOOKED",
                "VERIFIED",
                "REJECTED",
                "EXPIRED",
                name="propertyverificationstate",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["listing_agent_id"],
            ["agent_profile.id"],
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_property_city"), "property", ["city"], unique=False)
    op.create_index(op.f("ix_property_listing_agent_id"), "property", ["listing_agent_id"], unique=False)
    op.create_index(op.f("ix_property_owner_user_id"), "property", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_property_property_type"), "property", ["property_type"], unique=False)
    op.create_index(op.f("ix_property_public_slug"), "property", ["public_slug"], unique=True)
    op.create_index(op.f("ix_property_state"), "property", ["state"], unique=False)
    op.create_index(
        op.f("ix_property_verification_status"), "property", ["verification_status"], unique=False
    )
    op.create_table(
        "agent_enquiry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("house_search_request_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("message", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RESPONDED", "CLOSED", name="enquirystatus", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent_profile.id"],
        ),
        sa.ForeignKeyConstraint(
            ["house_search_request_id"],
            ["house_search_request.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_enquiry_agent_id"), "agent_enquiry", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_agent_enquiry_house_search_request_id"),
        "agent_enquiry",
        ["house_search_request_id"],
        unique=False,
    )
    op.create_table(
        "agent_report",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("property_id", sa.Integer(), nullable=True),
        sa.Column(
            "reason",
            sa.Enum(
                "FAKE_IDENTITY",
                "FALSE_PROPERTY_INFORMATION",
                "MISLEADING_PHOTOS",
                "UNEXPECTED_FEES",
                "PROPERTY_UNAVAILABLE_AFTER_PAYMENT",
                "HARASSMENT",
                "PAYMENT_PRESSURE",
                "FRAUD_SUSPICION",
                "UNAUTHORIZED_AGENT_ACTIVITY",
                name="reportreason",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=4000), nullable=False),
        sa.Column("evidence_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN", "IN_REVIEW", "RESOLVED", "REJECTED", name="reportstatus", native_enum=False, length=40
            ),
            nullable=False,
        ),
        sa.Column("reviewer_notes", sqlmodel.sql.sqltypes.AutoString(length=4000), nullable=True),
        sa.Column("resolution_reason", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("agent_id IS NOT NULL OR property_id IS NOT NULL", name="ck_report_has_target"),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent_profile.id"],
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["property.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_report_agent_id"), "agent_report", ["agent_id"], unique=False)
    op.create_index(op.f("ix_agent_report_property_id"), "agent_report", ["property_id"], unique=False)
    op.create_index(op.f("ix_agent_report_reporter_id"), "agent_report", ["reporter_id"], unique=False)
    op.create_index(op.f("ix_agent_report_status"), "agent_report", ["status"], unique=False)
    op.create_table(
        "inspection_slot",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("landlord_user_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("OPEN", "BOOKED", "CANCELLED", name="slotstatus", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        postgresql.ExcludeConstraint(
            (sa.column("property_id"), "="),
            (sa.text("tstzrange(start_time, end_time, '[)')"), "&&"),
            where=sa.text("status <> 'CANCELLED'"),
            using="gist",
            name="ex_slot_no_overlap",
        ),
        sa.CheckConstraint("end_time > start_time", name="ck_slot_time_order"),
        sa.ForeignKeyConstraint(
            ["landlord_user_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["property.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inspection_slot_property_id"), "inspection_slot", ["property_id"], unique=False)
    op.create_table(
        "property_document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "AUTHORITY_LETTER",
                "OWNER_ID",
                "AGENT_ID",
                "TITLE_DOCUMENT_COPY",
                "UTILITY_BILL",
                "TENANCY_AGREEMENT_TEMPLATE",
                "FEE_SCHEDULE",
                "OTHER",
                name="documenttype",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("original_filename", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column(
            "review_status",
            sa.Enum(
                "UPLOADED",
                "REVIEWED",
                "ACCEPTED",
                "REJECTED",
                name="documentreviewstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("reviewer_notes", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["property.id"],
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_property_document_property_id"), "property_document", ["property_id"], unique=False
    )
    op.create_table(
        "property_media",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column(
            "media_type",
            sa.Enum("PHOTO", "VIDEO_LINK", name="mediatype", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("caption", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["property.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_property_media_property_id"), "property_media", ["property_id"], unique=False)
    op.create_table(
        "reservation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("renter_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("payment_reference", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=True),
        sa.Column("payment_provider", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING_PAYMENT",
                "PENDING_RELEASE",
                "RELEASED",
                "REFUNDED",
                "CANCELLED",
                name="reservationstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("terms_version", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_request_reason", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("cancellation_reason", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["property.id"],
        ),
        sa.ForeignKeyConstraint(
            ["renter_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_reference"),
    )
    op.create_index(op.f("ix_reservation_property_id"), "reservation", ["property_id"], unique=False)
    op.create_index(op.f("ix_reservation_renter_id"), "reservation", ["renter_id"], unique=False)
    op.create_index(op.f("ix_reservation_status"), "reservation", ["status"], unique=False)
    op.create_table(
        "verification_case",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("submitted_by", sa.Integer(), nullable=False),
        sa.Column("assigned_reviewer_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "SUBMITTED",
                "IN_REVIEW",
                "INSPECTION_BOOKED",
                "VERIFIED",
                "REJECTED",
                "EXPIRED",
                name="verificationstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("verification_reference", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inspection_booked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inspection_scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("reviewer_notes", sqlmodel.sql.sqltypes.AutoString(length=4000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_reviewer_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["property.id"],
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("verification_reference"),
    )
    op.create_index(
        op.f("ix_verification_case_assigned_reviewer_id"),
        "verification_case",
        ["assigned_reviewer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_verification_case_property_id"), "verification_case", ["property_id"], unique=False
    )
    op.create_index(op.f("ix_verification_case_status"), "verification_case", ["status"], unique=False)
    op.create_table(
        "inspection_booking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("renter_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "REQUESTED",
                "CONFIRMED",
                "DECLINED",
                "COMPLETED",
                "CANCELLED",
                name="bookingstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("renter_note", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("landlord_note", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["property.id"],
        ),
        sa.ForeignKeyConstraint(
            ["renter_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"],
            ["inspection_slot.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inspection_booking_property_id"), "inspection_booking", ["property_id"], unique=False
    )
    op.create_index(
        op.f("ix_inspection_booking_renter_id"), "inspection_booking", ["renter_id"], unique=False
    )
    op.create_index(op.f("ix_inspection_booking_slot_id"), "inspection_booking", ["slot_id"], unique=False)
    op.create_index(
        "uq_booking_active_slot",
        "inspection_booking",
        ["slot_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('REQUESTED', 'CONFIRMED')"),
    )
    op.create_table(
        "verification_check",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("verification_case_id", sa.Integer(), nullable=False),
        sa.Column(
            "check_type",
            sa.Enum(
                "AGENT_IDENTITY_SEEN",
                "AUTHORITY_TO_MARKET_SEEN",
                "PROPERTY_LOCATION_INSPECTED",
                "PHOTOS_MATCH_INSPECTION",
                "FEE_BREAKDOWN_CONFIRMED",
                "OWNER_CONTACT_CONFIRMED",
                "LISTING_AVAILABILITY_CONFIRMED",
                "SUPPORTING_DOCUMENTS_REVIEWED",
                name="checktype",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "result",
            sa.Enum(
                "NOT_STARTED",
                "PASSED",
                "FAILED",
                "NOT_APPLICABLE",
                name="checkresult",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("evidence_note", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.Column("document_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("completed_by", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["completed_by"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["verification_case_id"],
            ["verification_case.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("verification_case_id", "check_type", name="uq_case_check_type"),
    )
    op.create_index(
        op.f("ix_verification_check_verification_case_id"),
        "verification_check",
        ["verification_case_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_verification_check_verification_case_id"), table_name="verification_check")
    op.drop_table("verification_check")
    op.drop_index(
        "uq_booking_active_slot",
        table_name="inspection_booking",
        postgresql_where=sa.text("status IN ('REQUESTED', 'CONFIRMED')"),
    )
    op.drop_index(op.f("ix_inspection_booking_slot_id"), table_name="inspection_booking")
    op.drop_index(op.f("ix_inspection_booking_renter_id"), table_name="inspection_booking")
    op.drop_index(op.f("ix_inspection_booking_property_id"), table_name="inspection_booking")
    op.drop_table("inspection_booking")
    op.drop_index(op.f("ix_verification_case_status"), table_name="verification_case")
    op.drop_index(op.f("ix_verification_case_property_id"), table_name="verification_case")
    op.drop_index(op.f("ix_verification_case_assigned_reviewer_id"), table_name="verification_case")
    op.drop_table("verification_case")
    op.drop_index(op.f("ix_reservation_status"), table_name="reservation")
    op.drop_index(op.f("ix_reservation_renter_id"), table_name="reservation")
    op.drop_index(op.f("ix_reservation_property_id"), table_name="reservation")
    op.drop_table("reservation")
    op.drop_index(op.f("ix_property_media_property_id"), table_name="property_media")
    op.drop_table("property_media")
    op.drop_index(op.f("ix_property_document_property_id"), table_name="property_document")
    op.drop_table("property_document")
    op.drop_index(op.f("ix_inspection_slot_property_id"), table_name="inspection_slot")
    op.drop_table("inspection_slot")
    op.drop_index(op.f("ix_agent_report_status"), table_name="agent_report")
    op.drop_index(op.f("ix_agent_report_reporter_id"), table_name="agent_report")
    op.drop_index(op.f("ix_agent_report_property_id"), table_name="agent_report")
    op.drop_index(op.f("ix_agent_report_agent_id"), table_name="agent_report")
    op.drop_table("agent_report")
    op.drop_index(op.f("ix_agent_enquiry_house_search_request_id"), table_name="agent_enquiry")
    op.drop_index(op.f("ix_agent_enquiry_agent_id"), table_name="agent_enquiry")
    op.drop_table("agent_enquiry")
    op.drop_index(op.f("ix_property_verification_status"), table_name="property")
    op.drop_index(op.f("ix_property_state"), table_name="property")
    op.drop_index(op.f("ix_property_public_slug"), table_name="property")
    op.drop_index(op.f("ix_property_property_type"), table_name="property")
    op.drop_index(op.f("ix_property_owner_user_id"), table_name="property")
    op.drop_index(op.f("ix_property_listing_agent_id"), table_name="property")
    op.drop_index(op.f("ix_property_city"), table_name="property")
    op.drop_table("property")
    op.drop_index(op.f("ix_house_search_request_status"), table_name="house_search_request")
    op.drop_index(op.f("ix_house_search_request_state"), table_name="house_search_request")
    op.drop_index(op.f("ix_house_search_request_renter_id"), table_name="house_search_request")
    op.drop_index(op.f("ix_house_search_request_assigned_agent_id"), table_name="house_search_request")
    op.drop_table("house_search_request")
    op.drop_index(op.f("ix_agent_verification_status"), table_name="agent_verification")
    op.drop_index(op.f("ix_agent_verification_agent_profile_id"), table_name="agent_verification")
    op.drop_table("agent_verification")
    op.drop_index(op.f("ix_audit_log_created_at"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_user_id"), table_name="audit_log")
    op.drop_index("ix_audit_entity", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index(op.f("ix_agent_profile_verification_status"), table_name="agent_profile")
    op.drop_index(op.f("ix_agent_profile_user_id"), table_name="agent_profile")
    op.drop_index("ix_agent_profile_states_covered_gin", table_name="agent_profile", postgresql_using="gin")
    op.drop_index("ix_agent_profile_service_types_gin", table_name="agent_profile", postgresql_using="gin")
    op.drop_index("ix_agent_profile_property_types_gin", table_name="agent_profile", postgresql_using="gin")
    op.drop_index("ix_agent_profile_lgas_covered_gin", table_name="agent_profile", postgresql_using="gin")
    op.drop_index("ix_agent_profile_cities_covered_gin", table_name="agent_profile", postgresql_using="gin")
    op.drop_table("agent_profile")
    op.drop_index(op.f("ix_user_role"), table_name="user")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
