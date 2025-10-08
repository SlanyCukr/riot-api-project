"""change_puuid_to_varchar

Revision ID: f3ffda16584b
Revises: ad5ad0661dc8
Create Date: 2025-10-08 08:59:22.127888

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3ffda16584b"
down_revision = "ad5ad0661dc8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change puuid column from UUID to VARCHAR(78) in all tables
    # Note: Riot PUUIDs are base64-encoded strings, not UUIDs

    # Step 1: Drop foreign key constraints
    op.drop_constraint(
        "fk_match_participants_puuid_players", "match_participants", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_player_ranks_puuid_players", "player_ranks", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_smurf_detections_puuid_players", "smurf_detections", type_="foreignkey"
    )

    # Step 2: Alter column types
    # Players table (primary key)
    op.alter_column(
        "players",
        "puuid",
        existing_type=sa.UUID(),
        type_=sa.String(length=78),
        existing_nullable=False,
        postgresql_using="puuid::text",
    )

    # Match participants table
    op.alter_column(
        "match_participants",
        "puuid",
        existing_type=sa.UUID(),
        type_=sa.String(length=78),
        existing_nullable=False,
        postgresql_using="puuid::text",
    )

    # Player ranks table
    op.alter_column(
        "player_ranks",
        "puuid",
        existing_type=sa.UUID(),
        type_=sa.String(length=78),
        existing_nullable=False,
        postgresql_using="puuid::text",
    )

    # Smurf detections table
    op.alter_column(
        "smurf_detections",
        "puuid",
        existing_type=sa.UUID(),
        type_=sa.String(length=78),
        existing_nullable=False,
        postgresql_using="puuid::text",
    )

    # Step 3: Recreate foreign key constraints
    op.create_foreign_key(
        "fk_match_participants_puuid_players",
        "match_participants",
        "players",
        ["puuid"],
        ["puuid"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_player_ranks_puuid_players",
        "player_ranks",
        "players",
        ["puuid"],
        ["puuid"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_smurf_detections_puuid_players",
        "smurf_detections",
        "players",
        ["puuid"],
        ["puuid"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Revert VARCHAR(78) back to UUID

    # Step 1: Drop foreign key constraints
    op.drop_constraint(
        "fk_smurf_detections_puuid_players", "smurf_detections", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_player_ranks_puuid_players", "player_ranks", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_match_participants_puuid_players", "match_participants", type_="foreignkey"
    )

    # Step 2: Revert column types back to UUID
    op.alter_column(
        "smurf_detections",
        "puuid",
        existing_type=sa.String(length=78),
        type_=sa.UUID(),
        existing_nullable=False,
        postgresql_using="puuid::uuid",
    )

    op.alter_column(
        "player_ranks",
        "puuid",
        existing_type=sa.String(length=78),
        type_=sa.UUID(),
        existing_nullable=False,
        postgresql_using="puuid::uuid",
    )

    op.alter_column(
        "match_participants",
        "puuid",
        existing_type=sa.String(length=78),
        type_=sa.UUID(),
        existing_nullable=False,
        postgresql_using="puuid::uuid",
    )

    op.alter_column(
        "players",
        "puuid",
        existing_type=sa.String(length=78),
        type_=sa.UUID(),
        existing_nullable=False,
        postgresql_using="puuid::uuid",
    )

    # Step 3: Recreate foreign key constraints
    op.create_foreign_key(
        "fk_match_participants_puuid_players",
        "match_participants",
        "players",
        ["puuid"],
        ["puuid"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_player_ranks_puuid_players",
        "player_ranks",
        "players",
        ["puuid"],
        ["puuid"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_smurf_detections_puuid_players",
        "smurf_detections",
        "players",
        ["puuid"],
        ["puuid"],
        ondelete="CASCADE",
    )
