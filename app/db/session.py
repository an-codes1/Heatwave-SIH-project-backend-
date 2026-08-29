from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _build_engine():
    """Create the async engine with environment-driven pooling.

    SQLAlchemy's default async pool (AsyncAdaptedQueuePool) is used for
    production; set DB_POOL_SIZE=0 to select NullPool (one connection
    per session, used by the test suite to avoid cross-event-loop
    connection reuse inside FastAPI TestClient).
    """

    engine_kwargs: dict = {
        "echo": False,
        "pool_pre_ping": True,
    }

    if settings.db_pool_size > 0:
        engine_kwargs.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
        )
    else:
        engine_kwargs["poolclass"] = NullPool

    return create_async_engine(
        settings.database_url,
        **engine_kwargs,
    )


engine = _build_engine()


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session for the request life-cycle."""

    async with AsyncSessionLocal() as session:
        yield session