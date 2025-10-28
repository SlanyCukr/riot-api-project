import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context

# Import all models for autogenerate support
from app.core import get_global_settings

# Import all SQLModel feature models so Alembic can detect them
# These imports register the models with SQLModel.metadata
from app.features.players.models import Player, PlayerRank  # noqa: F401
from app.features.matches.models import Match  # noqa: F401
from app.features.matches.participants import MatchParticipant  # noqa: F401
from app.features.player_analysis.models import PlayerAnalysis  # noqa: F401
from app.features.matchmaking_analysis.models import MatchmakingAnalysis  # noqa: F401
from app.features.jobs.models import JobConfiguration, JobExecution  # noqa: F401
from app.features.settings.models import SystemSetting  # noqa: F401
from app.features.auth.models import User  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from application settings
settings = get_global_settings()
database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

# Override the sqlalchemy.url from the .ini file with our async URL
config.set_main_option("sqlalchemy.url", database_url)

# Use SQLModel metadata for all application tables
# All models now use SQLModel (auth, players, matches, player_analysis, jobs, settings, matchmaking_analysis)
# APScheduler manages its own schema independently (apscheduler_jobs table)
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    """
    Exclude tables managed by external libraries.

    This prevents Alembic from managing tables owned by external libraries
    like APScheduler, which handle their own schema lifecycle.

    Args:
        object: The schema object (Table, Index, etc.)
        name: Name of the object
        type_: Type of object ('table', 'column', 'index', etc.)
        reflected: Whether object was reflected from the database
        compare_to: The metadata object being compared to (if any)

    Returns:
        False to exclude the object from autogenerate, True to include it.
    """
    # Exclude tables owned by external libraries (APScheduler manages its own schema)
    # This catches the apscheduler_jobs table that APScheduler creates/manages
    if type_ == "table" and name.startswith("apscheduler_"):
        return False

    return True


def include_name(name, type_, parent_names):
    """
    Filter schema names during autogenerate.

    This function controls which schemas Alembic scans when include_schemas=True.
    Only our application schemas (core, auth, jobs) are included, preventing
    Alembic from trying to manage tables in other schemas.

    Args:
        name: Name of the object (schema, table, column, etc.)
        type_: Type of object ('schema', 'table', 'column', 'index', etc.)
        parent_names: Dict containing parent object names

    Returns:
        True to include the object, False to exclude it.
    """
    # Only scan our application schemas
    if type_ == "schema":
        # Include our custom schemas + public (where alembic_version lives)
        return name in ("core", "auth", "jobs", "public", None)

    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        include_schemas=True,  # Scan all application schemas (core, auth, jobs)
        include_name=include_name,  # Filter which schemas to scan
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Enable autogenerate features
        compare_type=True,
        compare_server_default=True,
        # Use naming conventions for consistent constraint names
        render_as_batch=False,
        # Exclude objects marked with skip_autogenerate
        include_object=include_object,
        # Multi-schema support (PostgreSQL)
        include_schemas=True,  # Scan all application schemas (core, auth, jobs)
        include_name=include_name,  # Filter which schemas to scan
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
