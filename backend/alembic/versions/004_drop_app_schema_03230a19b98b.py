"""drop_app_schema

Revision ID: 03230a19b98b
Revises: d32798c29221
Create Date: 2025-10-23 03:13:33.071399

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "03230a19b98b"
down_revision: Union[str, Sequence[str], None] = "d32798c29221"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the app schema (with CASCADE to handle any remaining tables)."""

    conn = op.get_bind()

    # Check if app schema has any remaining tables (for logging only)
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'app'"
        )
    )
    remaining_tables = result.scalar()

    if remaining_tables > 0:
        # List remaining tables for information
        result = conn.execute(
            sa.text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'app' ORDER BY table_name"
            )
        )
        tables = [row[0] for row in result]
        print(
            f"Note: {remaining_tables} tables still in app schema (will be dropped with CASCADE): {tables}"
        )

    # Drop the app schema (CASCADE will drop any remaining tables/objects)
    print("Dropping app schema...")
    op.execute("DROP SCHEMA IF EXISTS app CASCADE")
    print("App schema dropped successfully!")


def downgrade() -> None:
    """Recreate the app schema (empty)."""

    print("Recreating app schema...")
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    print("App schema recreated!")
