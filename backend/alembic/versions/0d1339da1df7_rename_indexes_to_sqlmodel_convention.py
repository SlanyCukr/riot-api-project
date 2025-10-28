"""rename_indexes_to_sqlmodel_convention

Revision ID: 0d1339da1df7
Revises: 2438ef1ce370
Create Date: 2025-10-27 18:59:09.201181

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0d1339da1df7"
down_revision: Union[str, Sequence[str], None] = "2438ef1ce370"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename indexes from old app.* convention to SQLModel convention.

    This migration synchronizes the database schema with SQLModel's index naming:
    - ix_app_* -> ix_core_* (for core schema)
    - ix_app_* -> ix_jobs_* (for jobs schema)
    - ix_users_* -> ix_auth_users_* (for auth schema)
    """

    # Core schema - players table
    op.execute(
        "ALTER INDEX core.ix_app_players_is_active RENAME TO ix_core_players_is_active"
    )
    op.execute(
        "ALTER INDEX core.ix_app_players_is_analyzed RENAME TO ix_core_players_is_analyzed"
    )
    op.execute(
        "ALTER INDEX core.ix_app_players_is_tracked RENAME TO ix_core_players_is_tracked"
    )
    op.execute(
        "ALTER INDEX core.ix_app_players_last_ban_check RENAME TO ix_core_players_last_ban_check"
    )
    op.execute(
        "ALTER INDEX core.ix_app_players_last_seen RENAME TO ix_core_players_last_seen"
    )
    op.execute(
        "ALTER INDEX core.ix_app_players_matches_exhausted RENAME TO ix_core_players_matches_exhausted"
    )
    op.execute(
        "ALTER INDEX core.ix_app_players_platform RENAME TO ix_core_players_platform"
    )
    op.execute("ALTER INDEX core.ix_app_players_puuid RENAME TO ix_core_players_puuid")
    op.execute(
        "ALTER INDEX core.ix_app_players_riot_id RENAME TO ix_core_players_riot_id"
    )
    op.execute(
        "ALTER INDEX core.ix_app_players_summoner_id RENAME TO ix_core_players_summoner_id"
    )
    op.execute(
        "ALTER INDEX core.ix_app_players_summoner_name RENAME TO ix_core_players_summoner_name"
    )

    # Core schema - matches table
    op.execute(
        "ALTER INDEX core.ix_app_matches_game_creation RENAME TO ix_core_matches_game_creation"
    )
    op.execute(
        "ALTER INDEX core.ix_app_matches_game_mode RENAME TO ix_core_matches_game_mode"
    )
    op.execute(
        "ALTER INDEX core.ix_app_matches_game_type RENAME TO ix_core_matches_game_type"
    )
    op.execute(
        "ALTER INDEX core.ix_app_matches_game_version RENAME TO ix_core_matches_game_version"
    )
    op.execute(
        "ALTER INDEX core.ix_app_matches_is_processed RENAME TO ix_core_matches_is_processed"
    )
    op.execute(
        "ALTER INDEX core.ix_app_matches_match_id RENAME TO ix_core_matches_match_id"
    )
    op.execute(
        "ALTER INDEX core.ix_app_matches_platform_id RENAME TO ix_core_matches_platform_id"
    )
    op.execute(
        "ALTER INDEX core.ix_app_matches_queue_id RENAME TO ix_core_matches_queue_id"
    )
    op.execute(
        "ALTER INDEX core.ix_app_matches_tournament_id RENAME TO ix_core_matches_tournament_id"
    )

    # Core schema - match_participants table
    op.execute(
        "ALTER INDEX core.ix_app_match_participants_champion_id RENAME TO ix_core_match_participants_champion_id"
    )
    op.execute(
        "ALTER INDEX core.ix_app_match_participants_champion_name RENAME TO ix_core_match_participants_champion_name"
    )
    op.execute(
        "ALTER INDEX core.ix_app_match_participants_individual_position RENAME TO ix_core_match_participants_individual_position"
    )
    op.execute(
        "ALTER INDEX core.ix_app_match_participants_match_id RENAME TO ix_core_match_participants_match_id"
    )
    op.execute(
        "ALTER INDEX core.ix_app_match_participants_puuid RENAME TO ix_core_match_participants_puuid"
    )
    op.execute(
        "ALTER INDEX core.ix_app_match_participants_role RENAME TO ix_core_match_participants_role"
    )
    op.execute(
        "ALTER INDEX core.ix_app_match_participants_team_id RENAME TO ix_core_match_participants_team_id"
    )
    op.execute(
        "ALTER INDEX core.ix_app_match_participants_team_position RENAME TO ix_core_match_participants_team_position"
    )

    # Core schema - player_ranks table
    op.execute(
        "ALTER INDEX core.ix_app_player_ranks_is_current RENAME TO ix_core_player_ranks_is_current"
    )
    op.execute(
        "ALTER INDEX core.ix_app_player_ranks_league_id RENAME TO ix_core_player_ranks_league_id"
    )
    op.execute(
        "ALTER INDEX core.ix_app_player_ranks_puuid RENAME TO ix_core_player_ranks_puuid"
    )
    op.execute(
        "ALTER INDEX core.ix_app_player_ranks_queue_type RENAME TO ix_core_player_ranks_queue_type"
    )
    op.execute(
        "ALTER INDEX core.ix_app_player_ranks_rank RENAME TO ix_core_player_ranks_rank"
    )
    op.execute(
        "ALTER INDEX core.ix_app_player_ranks_season_id RENAME TO ix_core_player_ranks_season_id"
    )
    op.execute(
        "ALTER INDEX core.ix_app_player_ranks_tier RENAME TO ix_core_player_ranks_tier"
    )

    # Core schema - matchmaking_analyses table
    op.execute(
        "ALTER INDEX core.ix_app_matchmaking_analyses_puuid RENAME TO ix_core_matchmaking_analyses_puuid"
    )
    op.execute(
        "ALTER INDEX core.ix_app_matchmaking_analyses_status RENAME TO ix_core_matchmaking_analyses_status"
    )

    # Jobs schema - job_configurations table
    op.execute(
        "ALTER INDEX jobs.ix_app_job_configurations_is_active RENAME TO ix_jobs_job_configurations_is_active"
    )
    op.execute(
        "ALTER INDEX jobs.ix_app_job_configurations_job_type RENAME TO ix_jobs_job_configurations_job_type"
    )
    op.execute(
        "ALTER INDEX jobs.ix_app_job_configurations_name RENAME TO ix_jobs_job_configurations_name"
    )

    # Jobs schema - job_executions table
    op.execute(
        "ALTER INDEX jobs.ix_app_job_executions_completed_at RENAME TO ix_jobs_job_executions_completed_at"
    )
    op.execute(
        "ALTER INDEX jobs.ix_app_job_executions_job_config_id RENAME TO ix_jobs_job_executions_job_config_id"
    )
    op.execute(
        "ALTER INDEX jobs.ix_app_job_executions_started_at RENAME TO ix_jobs_job_executions_started_at"
    )
    op.execute(
        "ALTER INDEX jobs.ix_app_job_executions_status RENAME TO ix_jobs_job_executions_status"
    )

    # Jobs schema - system_settings table
    op.execute(
        "ALTER INDEX jobs.ix_app_system_settings_key RENAME TO ix_jobs_system_settings_key"
    )

    # Auth schema - users table (add schema prefix)
    op.execute("ALTER INDEX auth.ix_users_created_at RENAME TO idx_users_created_at")
    op.execute("ALTER INDEX auth.ix_users_email RENAME TO ix_auth_users_email")
    op.execute("ALTER INDEX auth.ix_users_is_active RENAME TO ix_auth_users_is_active")
    op.execute("ALTER INDEX auth.ix_users_is_admin RENAME TO ix_auth_users_is_admin")
    op.execute("ALTER INDEX auth.ix_users_last_login RENAME TO idx_users_last_login")


def downgrade() -> None:
    """Revert index names to old convention.

    This reverses the naming convention changes.
    """

    # Core schema - players table
    op.execute(
        "ALTER INDEX core.ix_core_players_is_active RENAME TO ix_app_players_is_active"
    )
    op.execute(
        "ALTER INDEX core.ix_core_players_is_analyzed RENAME TO ix_app_players_is_analyzed"
    )
    op.execute(
        "ALTER INDEX core.ix_core_players_is_tracked RENAME TO ix_app_players_is_tracked"
    )
    op.execute(
        "ALTER INDEX core.ix_core_players_last_ban_check RENAME TO ix_app_players_last_ban_check"
    )
    op.execute(
        "ALTER INDEX core.ix_core_players_last_seen RENAME TO ix_app_players_last_seen"
    )
    op.execute(
        "ALTER INDEX core.ix_core_players_matches_exhausted RENAME TO ix_app_players_matches_exhausted"
    )
    op.execute(
        "ALTER INDEX core.ix_core_players_platform RENAME TO ix_app_players_platform"
    )
    op.execute("ALTER INDEX core.ix_core_players_puuid RENAME TO ix_app_players_puuid")
    op.execute(
        "ALTER INDEX core.ix_core_players_riot_id RENAME TO ix_app_players_riot_id"
    )
    op.execute(
        "ALTER INDEX core.ix_core_players_summoner_id RENAME TO ix_app_players_summoner_id"
    )
    op.execute(
        "ALTER INDEX core.ix_core_players_summoner_name RENAME TO ix_app_players_summoner_name"
    )

    # Core schema - matches table
    op.execute(
        "ALTER INDEX core.ix_core_matches_game_creation RENAME TO ix_app_matches_game_creation"
    )
    op.execute(
        "ALTER INDEX core.ix_core_matches_game_mode RENAME TO ix_app_matches_game_mode"
    )
    op.execute(
        "ALTER INDEX core.ix_core_matches_game_type RENAME TO ix_app_matches_game_type"
    )
    op.execute(
        "ALTER INDEX core.ix_core_matches_game_version RENAME TO ix_app_matches_game_version"
    )
    op.execute(
        "ALTER INDEX core.ix_core_matches_is_processed RENAME TO ix_app_matches_is_processed"
    )
    op.execute(
        "ALTER INDEX core.ix_core_matches_match_id RENAME TO ix_app_matches_match_id"
    )
    op.execute(
        "ALTER INDEX core.ix_core_matches_platform_id RENAME TO ix_app_matches_platform_id"
    )
    op.execute(
        "ALTER INDEX core.ix_core_matches_queue_id RENAME TO ix_app_matches_queue_id"
    )
    op.execute(
        "ALTER INDEX core.ix_core_matches_tournament_id RENAME TO ix_app_matches_tournament_id"
    )

    # Core schema - match_participants table
    op.execute(
        "ALTER INDEX core.ix_core_match_participants_champion_id RENAME TO ix_app_match_participants_champion_id"
    )
    op.execute(
        "ALTER INDEX core.ix_core_match_participants_champion_name RENAME TO ix_app_match_participants_champion_name"
    )
    op.execute(
        "ALTER INDEX core.ix_core_match_participants_individual_position RENAME TO ix_app_match_participants_individual_position"
    )
    op.execute(
        "ALTER INDEX core.ix_core_match_participants_match_id RENAME TO ix_app_match_participants_match_id"
    )
    op.execute(
        "ALTER INDEX core.ix_core_match_participants_puuid RENAME TO ix_app_match_participants_puuid"
    )
    op.execute(
        "ALTER INDEX core.ix_core_match_participants_role RENAME TO ix_app_match_participants_role"
    )
    op.execute(
        "ALTER INDEX core.ix_core_match_participants_team_id RENAME TO ix_app_match_participants_team_id"
    )
    op.execute(
        "ALTER INDEX core.ix_core_match_participants_team_position RENAME TO ix_app_match_participants_team_position"
    )

    # Core schema - player_ranks table
    op.execute(
        "ALTER INDEX core.ix_core_player_ranks_is_current RENAME TO ix_app_player_ranks_is_current"
    )
    op.execute(
        "ALTER INDEX core.ix_core_player_ranks_league_id RENAME TO ix_app_player_ranks_league_id"
    )
    op.execute(
        "ALTER INDEX core.ix_core_player_ranks_puuid RENAME TO ix_app_player_ranks_puuid"
    )
    op.execute(
        "ALTER INDEX core.ix_core_player_ranks_queue_type RENAME TO ix_app_player_ranks_queue_type"
    )
    op.execute(
        "ALTER INDEX core.ix_core_player_ranks_rank RENAME TO ix_app_player_ranks_rank"
    )
    op.execute(
        "ALTER INDEX core.ix_core_player_ranks_season_id RENAME TO ix_app_player_ranks_season_id"
    )
    op.execute(
        "ALTER INDEX core.ix_core_player_ranks_tier RENAME TO ix_app_player_ranks_tier"
    )

    # Core schema - matchmaking_analyses table
    op.execute(
        "ALTER INDEX core.ix_core_matchmaking_analyses_puuid RENAME TO ix_app_matchmaking_analyses_puuid"
    )
    op.execute(
        "ALTER INDEX core.ix_core_matchmaking_analyses_status RENAME TO ix_app_matchmaking_analyses_status"
    )

    # Jobs schema - job_configurations table
    op.execute(
        "ALTER INDEX jobs.ix_jobs_job_configurations_is_active RENAME TO ix_app_job_configurations_is_active"
    )
    op.execute(
        "ALTER INDEX jobs.ix_jobs_job_configurations_job_type RENAME TO ix_app_job_configurations_job_type"
    )
    op.execute(
        "ALTER INDEX jobs.ix_jobs_job_configurations_name RENAME TO ix_app_job_configurations_name"
    )

    # Jobs schema - job_executions table
    op.execute(
        "ALTER INDEX jobs.ix_jobs_job_executions_completed_at RENAME TO ix_app_job_executions_completed_at"
    )
    op.execute(
        "ALTER INDEX jobs.ix_jobs_job_executions_job_config_id RENAME TO ix_app_job_executions_job_config_id"
    )
    op.execute(
        "ALTER INDEX jobs.ix_jobs_job_executions_started_at RENAME TO ix_app_job_executions_started_at"
    )
    op.execute(
        "ALTER INDEX jobs.ix_jobs_job_executions_status RENAME TO ix_app_job_executions_status"
    )

    # Jobs schema - system_settings table
    op.execute(
        "ALTER INDEX jobs.ix_jobs_system_settings_key RENAME TO ix_app_system_settings_key"
    )

    # Auth schema - users table (remove schema prefix)
    op.execute("ALTER INDEX auth.idx_users_created_at RENAME TO ix_users_created_at")
    op.execute("ALTER INDEX auth.ix_auth_users_email RENAME TO ix_users_email")
    op.execute("ALTER INDEX auth.ix_auth_users_is_active RENAME TO ix_users_is_active")
    op.execute("ALTER INDEX auth.ix_auth_users_is_admin RENAME TO ix_users_is_admin")
    op.execute("ALTER INDEX auth.idx_users_last_login RENAME TO ix_users_last_login")
