"""Initial schema

Revision ID: 20260310_0001
Revises:
Create Date: 2026-03-10 11:40:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260310_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "managed_services",
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("container_name", sa.String(length=128), nullable=False),
        sa.Column("config_path", sa.String(length=255), nullable=False),
        sa.Column("supports_reload", sa.Boolean(), nullable=False),
        sa.Column("supports_raw_edit", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("slug"),
        sa.UniqueConstraint("container_name"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("before", sa.JSON(), nullable=False),
        sa.Column("after", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_action"), "audit_events", ["action"], unique=False)
    op.create_index(
        op.f("ix_audit_events_resource_id"),
        "audit_events",
        ["resource_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_resource_type"),
        "audit_events",
        ["resource_type"],
        unique=False,
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("refresh_jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_jti"),
    )
    op.create_index(op.f("ix_auth_sessions_refresh_jti"), "auth_sessions", ["refresh_jti"], unique=True)
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"], unique=False)

    op.create_table(
        "backup_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("restored_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_backup_snapshots_checksum"),
        "backup_snapshots",
        ["checksum"],
        unique=False,
    )

    op.create_table(
        "service_config_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("service_slug", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("raw_config", sa.Text(), nullable=False),
        sa.Column("rendered_config", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=False),
        sa.Column("apply_status", sa.String(length=32), nullable=False),
        sa.Column("apply_message", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["service_slug"], ["managed_services.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_slug", "version", name="uq_service_version"),
    )
    op.create_index(
        op.f("ix_service_config_versions_checksum"),
        "service_config_versions",
        ["checksum"],
        unique=False,
    )
    op.create_index(
        op.f("ix_service_config_versions_service_slug"),
        "service_config_versions",
        ["service_slug"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_service_config_versions_service_slug"), table_name="service_config_versions")
    op.drop_index(op.f("ix_service_config_versions_checksum"), table_name="service_config_versions")
    op.drop_table("service_config_versions")

    op.drop_index(op.f("ix_backup_snapshots_checksum"), table_name="backup_snapshots")
    op.drop_table("backup_snapshots")

    op.drop_index(op.f("ix_auth_sessions_user_id"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_refresh_jti"), table_name="auth_sessions")
    op.drop_table("auth_sessions")

    op.drop_index(op.f("ix_audit_events_resource_type"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_resource_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_action"), table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_table("managed_services")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
