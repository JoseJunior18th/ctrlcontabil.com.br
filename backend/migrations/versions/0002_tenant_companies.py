"""create tenant companies table

Revision ID: 0002_tenant_companies
Revises: 0001_global_catalog
Create Date: 2026-04-29
"""
from __future__ import annotations

from alembic import op

from app.database import quote_identifier

revision = "0002_tenant_companies"
down_revision = "0001_global_catalog"
branch_labels = None
depends_on = None


def validate_tenant_schema(schema: str | None) -> str | None:
    if schema:
        quote_identifier(schema)
    return schema


def upgrade(migration_scope: str = "global", tenant_schema: str | None = None) -> None:
    schema = validate_tenant_schema(tenant_schema)
    if migration_scope != "tenant" or not schema:
        return

    quoted_schema = quote_identifier(schema)
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}")
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {quoted_schema}.companies (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            legal_name varchar(180) NOT NULL,
            trade_name varchar(180),
            tax_id varchar(32) NOT NULL,
            status varchar(20) NOT NULL DEFAULT 'active',
            created_by_user_id uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_companies_tax_id UNIQUE (tax_id),
            CONSTRAINT ck_companies_status CHECK (status IN ('active', 'inactive'))
        )
        """
    )


def downgrade(migration_scope: str = "global", tenant_schema: str | None = None) -> None:
    schema = validate_tenant_schema(tenant_schema)
    if migration_scope != "tenant" or not schema:
        return

    op.execute(f"DROP TABLE IF EXISTS {quote_identifier(schema)}.companies")
