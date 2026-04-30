from __future__ import annotations

import asyncio
from logging.config import fileConfig

import sqlalchemy as sa
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.database import quote_identifier
from app.db_models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def get_migration_scope() -> str:
    return context.get_x_argument(as_dictionary=True).get("migration_scope", "global")


def get_tenant_schema() -> str | None:
    schema = context.get_x_argument(as_dictionary=True).get("tenant_schema")
    if schema:
        quote_identifier(schema)
    return schema


def run_migrations_offline() -> None:
    tenant_schema = get_tenant_schema()
    configure_args = {
        "url": settings.database_url,
        "target_metadata": target_metadata,
        "literal_binds": True,
        "dialect_opts": {"paramstyle": "named"},
        "include_schemas": True,
    }

    context.configure(
        **configure_args,
    )

    with context.begin_transaction():
        context.run_migrations(
            migration_scope=get_migration_scope(),
            tenant_schema=tenant_schema,
        )


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    tenant_schema = get_tenant_schema()
    if tenant_schema:
        connection.execute(
            sa.text(f"CREATE SCHEMA IF NOT EXISTS {quote_identifier(tenant_schema)}")
        )

    configure_args = {
        "connection": connection,
        "target_metadata": target_metadata,
        "include_schemas": True,
    }
    if tenant_schema:
        configure_args["version_table_schema"] = tenant_schema

    context.configure(**configure_args)

    with context.begin_transaction():
        context.run_migrations(
            migration_scope=get_migration_scope(),
            tenant_schema=tenant_schema,
        )


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
