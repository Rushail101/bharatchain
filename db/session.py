"""
db/session.py — Database Connection & Session Management
=========================================================
Handles async PostgreSQL connection using SQLAlchemy.
Called by main.py on startup via init_db().

All modules use get_db() as a FastAPI dependency to get a DB session.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings
import logging

logger = logging.getLogger("bharatchain.db")

# Convert standard postgres:// URL to async postgresql+asyncpg://
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,   # logs all SQL in debug mode
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class all database models inherit from."""
    pass


async def init_db():
    """Create all tables on startup if they don't exist."""
    from db.models import (  # noqa — import triggers table registration
        CitizenIdentity, HealthRecord, FinancialRecord,
        PropertyRecord, AssetRecord, ConsentRecord, AuditLog
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")


async def get_db():
    """
    FastAPI dependency — yields a DB session per request.

    Usage in any route:
        from db.session import get_db
        from sqlalchemy.ext.asyncio import AsyncSession

        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
