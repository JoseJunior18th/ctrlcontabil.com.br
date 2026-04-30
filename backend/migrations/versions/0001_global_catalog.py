"""create global catalog

Revision ID: 0001_global_catalog
Revises:
Create Date: 2026-04-29
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_global_catalog"
down_revision = None
branch_labels = None
depends_on = None


def should_run(migration_scope: str) -> bool:
    return migration_scope == "global"


def uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        primary_key=True,
    )


def timestamp_column(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


def upgrade(migration_scope: str = "global", tenant_schema: str | None = None) -> None:
    del tenant_schema
    if not should_run(migration_scope):
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "tenants",
        uuid_pk(),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("schema_name", sa.String(length=63), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_tenants_status"),
        sa.UniqueConstraint("schema_name", name="uq_tenants_schema_name"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
        schema="public",
    )
    op.create_index("ix_public_tenants_slug", "tenants", ["slug"], unique=False, schema="public")

    op.create_table(
        "app_users",
        uuid_pk(),
        sa.Column("auth_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("is_global_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_app_users_status"),
        sa.UniqueConstraint("auth_subject", name="uq_app_users_auth_subject"),
        schema="public",
    )
    op.create_index(
        "ix_public_app_users_auth_subject",
        "app_users",
        ["auth_subject"],
        unique=False,
        schema="public",
    )

    op.create_table(
        "tenant_memberships",
        uuid_pk(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False, server_default="member"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "role IN ('admin', 'member', 'viewer')",
            name="ck_tenant_memberships_role",
        ),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_tenant_memberships_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["public.tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["public.app_users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_memberships_tenant_user"),
        schema="public",
    )
    op.create_index(
        "ix_public_tenant_memberships_tenant_id",
        "tenant_memberships",
        ["tenant_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_public_tenant_memberships_user_id",
        "tenant_memberships",
        ["user_id"],
        unique=False,
        schema="public",
    )

    op.create_table(
        "audit_events",
        uuid_pk(),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        timestamp_column("created_at"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["public.app_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["public.tenants.id"], ondelete="SET NULL"),
        schema="public",
    )


def downgrade(migration_scope: str = "global", tenant_schema: str | None = None) -> None:
    del tenant_schema
    if not should_run(migration_scope):
        return

    op.drop_table("audit_events", schema="public")
    op.drop_index(
        "ix_public_tenant_memberships_user_id",
        table_name="tenant_memberships",
        schema="public",
    )
    op.drop_index(
        "ix_public_tenant_memberships_tenant_id",
        table_name="tenant_memberships",
        schema="public",
    )
    op.drop_table("tenant_memberships", schema="public")
    op.drop_index("ix_public_app_users_auth_subject", table_name="app_users", schema="public")
    op.drop_table("app_users", schema="public")
    op.drop_index("ix_public_tenants_slug", table_name="tenants", schema="public")
    op.drop_table("tenants", schema="public")
