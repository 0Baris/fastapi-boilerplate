from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


def _build_engine() -> AsyncEngine:
    """Create the async engine in one of two modes.

    1. **Cloud SQL Python Connector** — when ``INSTANCE_CONNECTION_NAME`` is set;
       drives asyncpg through ``google.cloud.sql.connector`` (in-band mTLS) with
       ``NullPool``.
    2. **Plain DATABASE_URL DSN** — local dev / CI / non-GCP (default).
    """
    common_kwargs: dict[str, Any] = {
        "echo": False,
        "future": True,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

    if settings.INSTANCE_CONNECTION_NAME:
        import asyncio

        from google.cloud.sql.connector import Connector, IPTypes
        from sqlalchemy.pool import NullPool

        # The Connector binds to the loop it is created in. The module-level
        # engine is shared across distinct loops (asyncio.run in wait_for_db /
        # alembic vs the long-lived server loop). NullPool never persists a
        # connection across loops; a per-loop Connector keeps each connect
        # aligned with the calling loop — together they avoid ConnectorLoopError.
        connectors: dict[asyncio.AbstractEventLoop, Connector] = {}

        async def _get_conn() -> Any:
            loop = asyncio.get_running_loop()
            connector = connectors.get(loop)
            if connector is None:
                connector = Connector(loop=loop)
                connectors[loop] = connector
            return await connector.connect_async(
                settings.INSTANCE_CONNECTION_NAME,
                "asyncpg",
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                db=settings.DB_NAME,
                ip_type=IPTypes.PRIVATE,
            )

        logger.info(
            "DB engine: Cloud SQL Connector (instance=%s, db=%s, NullPool)",
            settings.INSTANCE_CONNECTION_NAME,
            settings.DB_NAME,
        )
        return create_async_engine(
            "postgresql+asyncpg://",
            async_creator=_get_conn,
            poolclass=NullPool,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )

    logger.info("DB engine: DATABASE_URL DSN")
    return create_async_engine(url=settings.DATABASE_URL, **common_kwargs)


engine: AsyncEngine = _build_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    pass


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
