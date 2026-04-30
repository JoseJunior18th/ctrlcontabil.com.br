from __future__ import annotations

import re
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def quote_identifier(identifier: str) -> str:
    if not IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError("Invalid database identifier.")
    return f'"{identifier}"'


settings = get_settings()
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def set_tenant_search_path(session: AsyncSession, schema_name: str) -> None:
    await session.execute(
        text(f"SET LOCAL search_path TO {quote_identifier(schema_name)}, public")
    )


async def close_db_engine() -> None:
    await engine.dispose()
