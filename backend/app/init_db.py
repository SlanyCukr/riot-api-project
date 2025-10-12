"""Database initialization script using SQLAlchemy create_all().

This script creates all database tables defined in SQLAlchemy models.
It replaces Alembic migrations for simpler database initialization.
"""

import asyncio
import sys
from typing import NoReturn

import structlog
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import SQLAlchemyError

from app.models import Base
from app.config import get_global_settings

logger = structlog.get_logger(__name__)


async def init_db() -> None:
    """Initialize database by creating all tables defined in models.

    This function:
    1. Connects to PostgreSQL using async SQLAlchemy
    2. Creates all tables defined in Base.metadata
    3. Handles errors gracefully with logging

    Raises:
        SQLAlchemyError: If database connection or table creation fails
    """
    try:
        settings = get_global_settings()

        # Convert synchronous database URL to asynchronous
        database_url = settings.database_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        )

        logger.info(
            "Initializing database",
            database_url=database_url.replace(settings.postgres_password, "***"),
        )

        # Create async engine with echo for visibility
        engine = create_async_engine(
            database_url,
            echo=settings.debug,  # Show SQL queries in debug mode
            future=True,
        )

        # Create all tables
        async with engine.begin() as conn:
            logger.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)

        await engine.dispose()

        logger.info(
            "Database initialization completed successfully",
            tables_created=len(Base.metadata.tables),
            table_names=list(Base.metadata.tables.keys()),
        )

    except SQLAlchemyError as e:
        logger.error(
            "Database initialization failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during database initialization",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def drop_all_tables() -> None:
    """Drop all tables from the database.

    WARNING: This is destructive and will delete all data!
    Only use for testing or development reset.

    Raises:
        SQLAlchemyError: If database connection or table dropping fails
    """
    try:
        settings = get_global_settings()
        database_url = settings.database_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        )

        logger.warning("Dropping all database tables...")

        engine = create_async_engine(database_url, echo=settings.debug, future=True)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        await engine.dispose()

        logger.info("All database tables dropped successfully")

    except SQLAlchemyError as e:
        logger.error(
            "Failed to drop database tables",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def reset_db() -> None:
    """Reset database by dropping and recreating all tables.

    WARNING: This is destructive and will delete all data!
    Only use for testing or development reset.
    """
    logger.warning("Resetting database (drop + create)...")
    await drop_all_tables()
    await init_db()
    logger.info("Database reset completed successfully")


def main() -> NoReturn:
    """Run CLI for database initialization commands.

    Supports commands:
    - init: Create all tables (default)
    - drop: Drop all tables (WARNING: destructive)
    - reset: Drop and recreate all tables (WARNING: destructive)

    Usage:
        python -m app.init_db [init|drop|reset]
    """
    command = sys.argv[1] if len(sys.argv) > 1 else "init"

    if command == "init":
        asyncio.run(init_db())
    elif command == "drop":
        asyncio.run(drop_all_tables())
    elif command == "reset":
        asyncio.run(reset_db())
    else:
        logger.error(f"Unknown command: {command}")
        print("Usage: python -m app.init_db [init|drop|reset]")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
