"""add fiscal profile fields to tenant companies

Revision ID: 0003_company_fiscal_profile
Revises: 0002_tenant_companies
Create Date: 2026-04-30
"""
# ruff: noqa: S608
from __future__ import annotations

from alembic import op

from app.database import quote_identifier

revision = "0003_company_fiscal_profile"
down_revision = "0002_tenant_companies"
branch_labels = None
depends_on = None

FISCAL_COLUMNS = (
    ("tax_regime", "varchar(40)"),
    ("state_registration", "varchar(40)"),
    ("municipal_registration", "varchar(40)"),
    ("email", "varchar(255)"),
    ("phone", "varchar(40)"),
    ("postal_code", "varchar(20)"),
    ("street", "varchar(160)"),
    ("number", "varchar(30)"),
    ("complement", "varchar(120)"),
    ("district", "varchar(120)"),
    ("city", "varchar(120)"),
    ("state", "varchar(2)"),
    ("country", "varchar(2) NOT NULL DEFAULT 'BR'"),
)


def validate_tenant_schema(schema: str | None) -> str | None:
    if schema:
        quote_identifier(schema)
    return schema


def upgrade(migration_scope: str = "global", tenant_schema: str | None = None) -> None:
    schema = validate_tenant_schema(tenant_schema)
    if migration_scope != "tenant" or not schema:
        return

    quoted_schema = quote_identifier(schema)
    for column_name, column_type in FISCAL_COLUMNS:
        op.execute(
            f"ALTER TABLE {quoted_schema}.companies "
            f"ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
        )

    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'ck_companies_tax_regime'
                  AND connamespace = '{schema}'::regnamespace
            ) THEN
                ALTER TABLE {quoted_schema}.companies
                ADD CONSTRAINT ck_companies_tax_regime CHECK (
                    tax_regime IS NULL OR tax_regime IN (
                        'simples_nacional',
                        'lucro_presumido',
                        'lucro_real',
                        'mei',
                        'isento',
                        'outro'
                    )
                );
            END IF;
        END $$;
        """
    )


def downgrade(migration_scope: str = "global", tenant_schema: str | None = None) -> None:
    schema = validate_tenant_schema(tenant_schema)
    if migration_scope != "tenant" or not schema:
        return

    op.drop_constraint("ck_companies_tax_regime", "companies", schema=schema, type_="check")
    for column_name, _column_type in reversed(FISCAL_COLUMNS):
        op.drop_column("companies", column_name, schema=schema)
