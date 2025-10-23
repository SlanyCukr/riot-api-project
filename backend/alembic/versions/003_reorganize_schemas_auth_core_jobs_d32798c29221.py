"""003_reorganize_schemas_auth_core_jobs

Revision ID: d32798c29221
Revises: ed197c195294
Create Date: 2025-10-23 00:00:00.000000

Reorganizes tables from 'app' schema into three new schemas:
- auth: User authentication (empty for now, will be populated in next migration)
- core: Player data, matches, ranks, analyses
- jobs: Job configurations, executions, settings
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d32798c29221"
down_revision: Union[str, Sequence[str], None] = "ed197c195294"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Reorganize schemas from 'app' to 'auth', 'core', and 'jobs'."""

    conn = op.get_bind()

    # Create new schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS jobs")

    # Check if app schema has any tables (handles fresh database case)
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'app'"
        )
    )
    table_count = result.scalar()

    if table_count == 0:
        # Fresh database - nothing to move, just create schemas
        print("Fresh database detected - schemas created, no migration needed")
        return

    print(f"Found {table_count} tables in app schema to migrate")

    # Helper function to check if table exists in schema
    def table_exists_in_schema(schema: str, table: str) -> bool:
        result = conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = :schema AND table_name = :table)"
            ),
            {"schema": schema, "table": table},
        )
        return result.scalar()

    # Helper function to check if enum type exists in schema
    def enum_exists_in_schema(schema: str, enum_name: str) -> bool:
        result = conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = :schema AND t.typname = :enum_name)"
            ),
            {"schema": schema, "enum_name": enum_name},
        )
        return result.scalar()

    # Move core tables from app schema to core schema
    # Order matters due to foreign key dependencies

    # 1. Move independent tables first (no foreign keys)
    print("Moving core tables: players, matches...")

    if table_exists_in_schema("app", "players") and not table_exists_in_schema(
        "core", "players"
    ):
        op.execute("ALTER TABLE app.players SET SCHEMA core")
    else:
        print("  - players: already in core schema or doesn't exist in app, skipping")

    if table_exists_in_schema("app", "matches") and not table_exists_in_schema(
        "core", "matches"
    ):
        op.execute("ALTER TABLE app.matches SET SCHEMA core")
    else:
        print("  - matches: already in core schema or doesn't exist in app, skipping")

    # 2. Move tables with foreign keys
    print("Moving dependent core tables...")

    if table_exists_in_schema(
        "app", "match_participants"
    ) and not table_exists_in_schema("core", "match_participants"):
        op.execute("ALTER TABLE app.match_participants SET SCHEMA core")
    else:
        print(
            "  - match_participants: already in core schema or doesn't exist in app, skipping"
        )

    if table_exists_in_schema("app", "player_ranks") and not table_exists_in_schema(
        "core", "player_ranks"
    ):
        op.execute("ALTER TABLE app.player_ranks SET SCHEMA core")
    else:
        print(
            "  - player_ranks: already in core schema or doesn't exist in app, skipping"
        )

    if table_exists_in_schema("app", "smurf_detections") and not table_exists_in_schema(
        "core", "smurf_detections"
    ):
        op.execute("ALTER TABLE app.smurf_detections SET SCHEMA core")
    else:
        print(
            "  - smurf_detections: already in core schema or doesn't exist in app, skipping"
        )

    if table_exists_in_schema(
        "app", "matchmaking_analyses"
    ) and not table_exists_in_schema("core", "matchmaking_analyses"):
        op.execute("ALTER TABLE app.matchmaking_analyses SET SCHEMA core")
    else:
        print(
            "  - matchmaking_analyses: already in core schema or doesn't exist in app, skipping"
        )

    # 3. Move alembic_version to public schema (Alembic metadata table - should be in public)
    print("Checking for alembic_version table...")
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'app' AND table_name = 'alembic_version')"
        )
    )
    if result.scalar():
        print("Moving alembic_version to public schema...")
        op.execute("ALTER TABLE app.alembic_version SET SCHEMA public")

    # 4. Move jobs tables from app schema to jobs schema
    print("Moving jobs tables...")

    if table_exists_in_schema(
        "app", "job_configurations"
    ) and not table_exists_in_schema("jobs", "job_configurations"):
        op.execute("ALTER TABLE app.job_configurations SET SCHEMA jobs")
    else:
        print(
            "  - job_configurations: already in jobs schema or doesn't exist in app, skipping"
        )

    if table_exists_in_schema("app", "job_executions") and not table_exists_in_schema(
        "jobs", "job_executions"
    ):
        op.execute("ALTER TABLE app.job_executions SET SCHEMA jobs")
    else:
        print(
            "  - job_executions: already in jobs schema or doesn't exist in app, skipping"
        )

    if table_exists_in_schema("app", "system_settings") and not table_exists_in_schema(
        "jobs", "system_settings"
    ):
        op.execute("ALTER TABLE app.system_settings SET SCHEMA jobs")
    else:
        print(
            "  - system_settings: already in jobs schema or doesn't exist in app, skipping"
        )

    # 5. Move APScheduler table if it exists
    print("Checking for APScheduler table...")
    if table_exists_in_schema("app", "apscheduler_jobs") and not table_exists_in_schema(
        "jobs", "apscheduler_jobs"
    ):
        print("Moving apscheduler_jobs to jobs schema...")
        op.execute("ALTER TABLE app.apscheduler_jobs SET SCHEMA jobs")
    else:
        print(
            "  - apscheduler_jobs: already in jobs schema or doesn't exist in app, skipping"
        )

    # 6. Move enums to appropriate schemas (if they exist)
    print("Checking for enums to migrate...")

    # Check and move job-related enums to jobs schema
    print("Checking job-related enums...")
    if enum_exists_in_schema("app", "job_type_enum") and not enum_exists_in_schema(
        "jobs", "job_type_enum"
    ):
        print("Moving job_type_enum to jobs schema...")
        op.execute("ALTER TYPE app.job_type_enum SET SCHEMA jobs")
    else:
        print(
            "  - job_type_enum: already in jobs schema or doesn't exist in app, skipping"
        )

    if enum_exists_in_schema("app", "job_status_enum") and not enum_exists_in_schema(
        "jobs", "job_status_enum"
    ):
        print("Moving job_status_enum to jobs schema...")
        op.execute("ALTER TYPE app.job_status_enum SET SCHEMA jobs")
    else:
        print(
            "  - job_status_enum: already in jobs schema or doesn't exist in app, skipping"
        )

    # Check and move core-related enums to core schema
    print("Checking core-related enums...")
    if enum_exists_in_schema("app", "tier_enum") and not enum_exists_in_schema(
        "core", "tier_enum"
    ):
        print("Moving tier_enum to core schema...")
        op.execute("ALTER TYPE app.tier_enum SET SCHEMA core")
    else:
        print("  - tier_enum: already in core schema or doesn't exist in app, skipping")

    if enum_exists_in_schema("app", "rank_enum") and not enum_exists_in_schema(
        "core", "rank_enum"
    ):
        print("Moving rank_enum to core schema...")
        op.execute("ALTER TYPE app.rank_enum SET SCHEMA core")
    else:
        print("  - rank_enum: already in core schema or doesn't exist in app, skipping")

    if enum_exists_in_schema("app", "queue_type_enum") and not enum_exists_in_schema(
        "core", "queue_type_enum"
    ):
        print("Moving queue_type_enum to core schema...")
        op.execute("ALTER TYPE app.queue_type_enum SET SCHEMA core")
    else:
        print(
            "  - queue_type_enum: already in core schema or doesn't exist in app, skipping"
        )

    if enum_exists_in_schema(
        "app", "confidence_level_enum"
    ) and not enum_exists_in_schema("core", "confidence_level_enum"):
        print("Moving confidence_level_enum to core schema...")
        op.execute("ALTER TYPE app.confidence_level_enum SET SCHEMA core")
    else:
        print(
            "  - confidence_level_enum: already in core schema or doesn't exist in app, skipping"
        )

    if enum_exists_in_schema(
        "app", "detection_signal_enum"
    ) and not enum_exists_in_schema("core", "detection_signal_enum"):
        print("Moving detection_signal_enum to core schema...")
        op.execute("ALTER TYPE app.detection_signal_enum SET SCHEMA core")
    else:
        print(
            "  - detection_signal_enum: already in core schema or doesn't exist in app, skipping"
        )

    if enum_exists_in_schema(
        "app", "analysis_status_enum"
    ) and not enum_exists_in_schema("core", "analysis_status_enum"):
        print("Moving analysis_status_enum to core schema...")
        op.execute("ALTER TYPE app.analysis_status_enum SET SCHEMA core")
    else:
        print(
            "  - analysis_status_enum: already in core schema or doesn't exist in app, skipping"
        )

    # 7. Verify app schema is empty before dropping
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'app'"
        )
    )
    remaining_tables = result.scalar()

    if remaining_tables > 0:
        # List remaining tables for debugging
        result = conn.execute(
            sa.text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'app' ORDER BY table_name"
            )
        )
        tables = [row[0] for row in result]
        print(
            f"WARNING: {remaining_tables} tables still remain in app schema: {tables}"
        )
        print("NOT dropping app schema for safety - please verify manually")
    else:
        print("All tables migrated successfully!")


def downgrade() -> None:
    """Revert schema reorganization back to 'app' schema."""

    conn = op.get_bind()

    # Recreate app schema
    op.execute("CREATE SCHEMA IF NOT EXISTS app")

    # Move enums back to app schema (if they exist)
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'jobs' AND t.typname = 'job_type_enum')"
        )
    )
    if result.scalar():
        op.execute("ALTER TYPE jobs.job_type_enum SET SCHEMA app")
        op.execute("ALTER TYPE jobs.job_status_enum SET SCHEMA app")

    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'core' AND t.typname = 'tier_enum')"
        )
    )
    if result.scalar():
        op.execute("ALTER TYPE core.tier_enum SET SCHEMA app")
        op.execute("ALTER TYPE core.rank_enum SET SCHEMA app")
        op.execute("ALTER TYPE core.queue_type_enum SET SCHEMA app")
        op.execute("ALTER TYPE core.confidence_level_enum SET SCHEMA app")
        op.execute("ALTER TYPE core.detection_signal_enum SET SCHEMA app")
        op.execute("ALTER TYPE core.analysis_status_enum SET SCHEMA app")

    # Move APScheduler table back if it exists
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'jobs' AND table_name = 'apscheduler_jobs')"
        )
    )
    if result.scalar():
        op.execute("ALTER TABLE jobs.apscheduler_jobs SET SCHEMA app")

    # Move tables back to app schema
    # Jobs tables
    op.execute("ALTER TABLE jobs.system_settings SET SCHEMA app")
    op.execute("ALTER TABLE jobs.job_executions SET SCHEMA app")
    op.execute("ALTER TABLE jobs.job_configurations SET SCHEMA app")

    # Move alembic_version back to app schema if needed
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'alembic_version')"
        )
    )
    if result.scalar():
        op.execute("ALTER TABLE public.alembic_version SET SCHEMA app")

    # Core tables (reverse order due to foreign keys)
    op.execute("ALTER TABLE core.matchmaking_analyses SET SCHEMA app")
    op.execute("ALTER TABLE core.smurf_detections SET SCHEMA app")
    op.execute("ALTER TABLE core.player_ranks SET SCHEMA app")
    op.execute("ALTER TABLE core.match_participants SET SCHEMA app")
    op.execute("ALTER TABLE core.matches SET SCHEMA app")
    op.execute("ALTER TABLE core.players SET SCHEMA app")

    # Drop new schemas
    op.execute("DROP SCHEMA IF EXISTS jobs CASCADE")
    op.execute("DROP SCHEMA IF EXISTS core CASCADE")
    op.execute("DROP SCHEMA IF EXISTS auth CASCADE")
