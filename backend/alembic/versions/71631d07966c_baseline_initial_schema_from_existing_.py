"""Baseline - initial schema from existing database

Revision ID: 71631d07966c
Revises:
Create Date: 2025-10-17 22:39:29.769778

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "71631d07966c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    This is a baseline migration created from an existing database.
    The database schema already matches the SQLAlchemy models,
    so no schema changes are needed.
    """
    # No operations needed - baseline migration
    pass


def downgrade() -> None:
    """Downgrade schema.

    This is a baseline migration, so downgrade is not applicable.
    """
    # No operations needed - baseline migration
    pass
