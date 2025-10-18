"""remove_unused_indexes

Revision ID: 69dcb5a3c7f9
Revises: 833296d94323
Create Date: 2025-10-18 16:55:57.582467

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "69dcb5a3c7f9"
down_revision: Union[str, Sequence[str], None] = "833296d94323"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove unused indexes to reduce bloat and improve write performance."""

    # Match Participants - unused analytics indexes (no queries use these filters)
    op.drop_index(
        "ix_match_participants_champion_name",
        table_name="match_participants",
        schema="app",
    )
    op.drop_index(
        "ix_match_participants_role", table_name="match_participants", schema="app"
    )
    op.drop_index(
        "ix_match_participants_team_position",
        table_name="match_participants",
        schema="app",
    )
    op.drop_index(
        "idx_participants_kills_deaths", table_name="match_participants", schema="app"
    )
    op.drop_index(
        "idx_participants_position_champion",
        table_name="match_participants",
        schema="app",
    )
    op.drop_index(
        "idx_participants_champion_win", table_name="match_participants", schema="app"
    )
    op.drop_index(
        "idx_participants_team_win", table_name="match_participants", schema="app"
    )

    # Players - legacy/unused identity fields
    op.drop_index("ix_players_summoner_id", table_name="players", schema="app")
    op.drop_index("ix_players_summoner_name", table_name="players", schema="app")
    op.drop_index(
        "ix_players_riot_id", table_name="players", schema="app"
    )  # Redundant with idx_players_riot_tag
    op.drop_index("ix_players_last_ban_check", table_name="players", schema="app")
    op.drop_index("ix_players_is_analyzed", table_name="players", schema="app")

    # Matches - unused filter fields
    op.drop_index("ix_matches_tournament_id", table_name="matches", schema="app")
    op.drop_index("ix_matches_game_mode", table_name="matches", schema="app")
    op.drop_index("ix_matches_game_type", table_name="matches", schema="app")
    op.drop_index("idx_matches_processed_error", table_name="matches", schema="app")

    # Job Configurations - unused
    op.drop_index(
        "idx_job_config_type_active", table_name="job_configurations", schema="app"
    )
    op.drop_index(
        "ix_job_configurations_job_type", table_name="job_configurations", schema="app"
    )
    op.drop_index(
        "ix_job_configurations_is_active", table_name="job_configurations", schema="app"
    )

    # Job Executions - unused
    op.drop_index(
        "ix_job_executions_completed_at", table_name="job_executions", schema="app"
    )

    # Smurf Detections - unused single-field indexes (composites are better)
    op.drop_index(
        "idx_smurf_detection_false_positive",
        table_name="smurf_detections",
        schema="app",
    )
    op.drop_index(
        "ix_smurf_detections_confidence", table_name="smurf_detections", schema="app"
    )
    op.drop_index(
        "ix_smurf_detections_queue_type", table_name="smurf_detections", schema="app"
    )
    op.drop_index(
        "ix_smurf_detections_false_positive_reported",
        table_name="smurf_detections",
        schema="app",
    )
    op.drop_index(
        "ix_smurf_detections_manually_verified",
        table_name="smurf_detections",
        schema="app",
    )
    op.drop_index(
        "ix_smurf_detections_smurf_score", table_name="smurf_detections", schema="app"
    )


def downgrade() -> None:
    """Recreate removed indexes if needed."""

    # Match Participants
    op.create_index(
        "ix_match_participants_champion_name",
        "match_participants",
        ["champion_name"],
        schema="app",
    )
    op.create_index(
        "ix_match_participants_role", "match_participants", ["role"], schema="app"
    )
    op.create_index(
        "ix_match_participants_team_position",
        "match_participants",
        ["team_position"],
        schema="app",
    )
    op.create_index(
        "idx_participants_kills_deaths",
        "match_participants",
        ["kills", "deaths"],
        schema="app",
    )
    op.create_index(
        "idx_participants_position_champion",
        "match_participants",
        ["individual_position", "champion_id"],
        schema="app",
    )
    op.create_index(
        "idx_participants_champion_win",
        "match_participants",
        ["champion_id", "win"],
        schema="app",
    )
    op.create_index(
        "idx_participants_team_win",
        "match_participants",
        ["team_id", "win"],
        schema="app",
    )

    # Players
    op.create_index("ix_players_summoner_id", "players", ["summoner_id"], schema="app")
    op.create_index(
        "ix_players_summoner_name", "players", ["summoner_name"], schema="app"
    )
    op.create_index("ix_players_riot_id", "players", ["riot_id"], schema="app")
    op.create_index(
        "ix_players_last_ban_check", "players", ["last_ban_check"], schema="app"
    )
    op.create_index("ix_players_is_analyzed", "players", ["is_analyzed"], schema="app")

    # Matches
    op.create_index(
        "ix_matches_tournament_id", "matches", ["tournament_id"], schema="app"
    )
    op.create_index("ix_matches_game_mode", "matches", ["game_mode"], schema="app")
    op.create_index("ix_matches_game_type", "matches", ["game_type"], schema="app")
    op.create_index(
        "idx_matches_processed_error",
        "matches",
        ["is_processed", "processing_error"],
        schema="app",
    )

    # Job Configurations
    op.create_index(
        "idx_job_config_type_active",
        "job_configurations",
        ["job_type", "is_active"],
        schema="app",
    )
    op.create_index(
        "ix_job_configurations_job_type",
        "job_configurations",
        ["job_type"],
        schema="app",
    )
    op.create_index(
        "ix_job_configurations_is_active",
        "job_configurations",
        ["is_active"],
        schema="app",
    )

    # Job Executions
    op.create_index(
        "ix_job_executions_completed_at",
        "job_executions",
        ["completed_at"],
        schema="app",
    )

    # Smurf Detections
    op.create_index(
        "idx_smurf_detection_false_positive",
        "smurf_detections",
        ["false_positive_reported", "is_smurf"],
        schema="app",
    )
    op.create_index(
        "ix_smurf_detections_confidence",
        "smurf_detections",
        ["confidence"],
        schema="app",
    )
    op.create_index(
        "ix_smurf_detections_queue_type",
        "smurf_detections",
        ["queue_type"],
        schema="app",
    )
    op.create_index(
        "ix_smurf_detections_false_positive_reported",
        "smurf_detections",
        ["false_positive_reported"],
        schema="app",
    )
    op.create_index(
        "ix_smurf_detections_manually_verified",
        "smurf_detections",
        ["manually_verified"],
        schema="app",
    )
    op.create_index(
        "ix_smurf_detections_smurf_score",
        "smurf_detections",
        ["smurf_score"],
        schema="app",
    )
