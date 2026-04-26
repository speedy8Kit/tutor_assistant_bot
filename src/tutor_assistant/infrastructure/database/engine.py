"""Async SQLAlchemy engine and session factory.

The engine and session factory are created lazily on first use so that
importing this module does not require DATABASE_URL to be set (useful in tests).
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tutor_assistant.infrastructure.database.models import Base
from tutor_assistant.infrastructure.logging.logger import get_logger

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None

_logger = get_logger()

def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. Use postgresql+asyncpg://user:pass@host/db"
            )
        _engine = create_async_engine(url, echo=False)
    return _engine


def async_session_factory() -> AsyncSession:
    """Return a new AsyncSession. Engine is created on first call."""
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _session_maker()


async def init_db() -> None:
    """Create all tables (CREATE TABLE IF NOT EXISTS)."""
    _logger.info("init database")
    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
