"""
Database connection and session management for PostgreSQL using SQLAlchemy with async support.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from .config import settings


class DatabaseManager:
    """Database connection and session manager."""

    def __init__(self):
        # Convert synchronous database URL to asynchronous
        self.database_url = settings.database_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        )

        # Create async engine with connection pooling
        self.engine = create_async_engine(
            self.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            echo=settings.debug,  # Enable SQL logging in debug mode
            future=True,
        )

        # Create async session factory
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with proper cleanup."""
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_tables(self) -> None:
        """Create all database tables."""
        from .models import Base

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all database tables."""
        from .models import Base

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting a database session."""
    async with db_manager.get_session() as session:
        yield session


# Convenience function for getting a session in non-FastAPI contexts
async def get_session():
    """Get a database session."""
    async with db_manager.get_session() as session:
        return session