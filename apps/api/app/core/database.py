"""Database configuration and session management using SQLAlchemy 2.0 Async."""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""
    pass


# Normalized URL + driver connect_args (handles managed-Postgres DSNs that
# arrive as postgres:// with ?sslmode=require, etc.)
database_url = settings.sqlalchemy_url
connect_args: dict = dict(settings.db_connect_args)

# Engine arguments based on dialect
engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}

if database_url.startswith("postgresql"):
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })
elif database_url.startswith("sqlite"):
    connect_args.setdefault("check_same_thread", False)

if connect_args:
    engine_kwargs["connect_args"] = connect_args

engine: AsyncEngine = create_async_engine(database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding an async database session with automatic transaction management."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
