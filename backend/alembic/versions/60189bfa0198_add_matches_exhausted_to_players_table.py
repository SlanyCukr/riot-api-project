"""add matches_exhausted to players table

Revision ID: 60189bfa0198
Revises: 5e775a6127a0
Create Date: 2025-10-20 17:32:43.775312

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "60189bfa0198"
down_revision: Union[str, Sequence[str], None] = "5e775a6127a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add matches_exhausted column to players table
    op.add_column(
        "players",
        sa.Column(
            "matches_exhausted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True when all available matches have been fetched from Riot API",
        ),
        schema="app",
    )
    # Add index on matches_exhausted
    op.create_index(
        op.f("ix_players_matches_exhausted"),
        "players",
        ["matches_exhausted"],
        schema="app",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove index
    op.drop_index(
        op.f("ix_players_matches_exhausted"), table_name="players", schema="app"
    )
    # Remove column
    op.drop_column("players", "matches_exhausted", schema="app")
