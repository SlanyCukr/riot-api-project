import pytest
from unittest.mock import AsyncMock, MagicMock
from ..service import MatchmakingAnalysisService
from ..repository import (
    SQLAlchemyMatchmakingAnalysisRepository,
)
from ..gateway import MatchmakingGateway
from ..transformers import (
    MatchmakingAnalysisTransformer,
)
from ..schemas import MatchmakingAnalysisCreate
from app.core.enums import JobStatus


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_repository(mock_db):
    return AsyncMock(spec=SQLAlchemyMatchmakingAnalysisRepository)


@pytest.fixture
def mock_gateway():
    return AsyncMock(spec=MatchmakingGateway)


@pytest.fixture
def mock_transformer():
    return AsyncMock(spec=MatchmakingAnalysisTransformer)


@pytest.fixture
def service(mock_repository, mock_gateway, mock_transformer, mock_db):
    return MatchmakingAnalysisService(
        repository=mock_repository,
        gateway=mock_gateway,
        transformer=mock_transformer,
        db=mock_db,
    )


async def test_service_initialization(
    service, mock_repository, mock_gateway, mock_transformer
):
    """Test service initialization with enterprise components"""
    assert service.repository == mock_repository
    assert service.gateway == mock_gateway
    assert service.transformer == mock_transformer


async def test_start_analysis_orchestration(
    service, mock_repository, mock_gateway, mock_transformer
):
    """Test service orchestration for starting analysis"""
    # Setup
    create_request = MatchmakingAnalysisCreate(
        user_id="user-123", parameters={"region": "na"}
    )

    mock_orm_job = MagicMock()
    mock_repository.create_analysis.return_value = mock_orm_job
    mock_transformer.orm_to_response.return_value = {"id": "job-123"}

    # Execute
    await service.start_analysis(create_request)

    # Verify orchestration
    mock_repository.create_analysis.assert_called_once_with(create_request)
    mock_transformer.orm_to_response.assert_called_once_with(mock_orm_job)


async def test_process_match_data_success(service, mock_db):
    """Test MatchDataProcessor.process_match_data method with realistic match data"""
    # Use the match data processor from the service
    processor = service.match_processor

    # Setup realistic match data similar to Riot API response
    match_data = {
        "info": {
            "participants": [
                # Target player
                {
                    "puuid": "target-player-uuid",
                    "teamId": 100,
                    "win": True,
                },
                # Teammate
                {
                    "puuid": "teammate-uuid",
                    "teamId": 100,
                    "win": True,
                },
                # Enemy 1
                {
                    "puuid": "enemy-uuid-1",
                    "teamId": 200,
                    "win": False,
                },
                # Enemy 2
                {
                    "puuid": "enemy-uuid-2",
                    "teamId": 200,
                    "win": False,
                },
            ]
        }
    }

    target_player_puuid = "target-player-uuid"

    # Mock database to return None for all participants (no rank data available)
    # This simulates players not in the database yet
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Execute
    result = await processor.process_match_data(match_data, target_player_puuid, mock_db)

    # Verify result is not None
    assert result is not None

    # Verify player win status is correctly extracted
    assert result["player_win"] is True

    # Verify team winrates list exists (will be empty since no DB data)
    assert "team_winrates" in result
    assert isinstance(result["team_winrates"], list)

    # Verify enemy winrates list exists (will be empty since no DB data)
    assert "enemy_winrates" in result
    assert isinstance(result["enemy_winrates"], list)

    # Verify rank difference is computed
    assert "rank_difference" in result
    assert isinstance(result["rank_difference"], (int, float))

    # Verify basic data structure integrity
    assert isinstance(result["player_win"], bool)


async def test_calculate_fairness_score_scenarios(service):
    """Test the FairnessCalculator.calculate_fairness_score method with different scenarios"""
    calculator = service.fairness_calculator

    # Test 1: Perfectly balanced match (should return 1.0)
    perfect_score = calculator.calculate_fairness_score(
        team_avg_winrate=0.5,  # Same winrates
        enemy_avg_winrate=0.5,  # Same winrates
        avg_rank_difference=0.0  # No rank difference
    )
    assert perfect_score == 1.0, "Perfectly balanced match should return exactly 1.0"

    # Test 2: Slightly unbalanced match (should return reasonable fairness score)
    slightly_unbalanced_score = calculator.calculate_fairness_score(
        team_avg_winrate=0.55,  # Close winrates
        enemy_avg_winrate=0.45,  # Close winrates
        avg_rank_difference=200.0  # Small rank difference
    )
    # Expected: winrate_fairness=0.9, rank_fairness=0.6, combined=0.84
    expected_slightly_unbalanced = 0.84
    assert abs(slightly_unbalanced_score - expected_slightly_unbalanced) < 0.01, \
        f"Slightly unbalanced match should return ~{expected_slightly_unbalanced}, got {slightly_unbalanced_score}"

    # Test 3: Highly unbalanced match (should return low score, < 0.5)
    highly_unbalanced_score = calculator.calculate_fairness_score(
        team_avg_winrate=0.7,   # Very different winrates
        enemy_avg_winrate=0.3,  # Very different winrates
        avg_rank_difference=800.0  # Large rank difference
    )
    # Expected: winrate_fairness=0.6, rank_fairness=0.0, combined=0.36
    expected_highly_unbalanced = 0.36
    assert abs(highly_unbalanced_score - expected_highly_unbalanced) < 0.01, \
        f"Highly unbalanced match should return ~{expected_highly_unbalanced}, got {highly_unbalanced_score}"
    assert highly_unbalanced_score < 0.5, \
        f"Highly unbalanced match should return low score < 0.5, got {highly_unbalanced_score}"

    # Test 4: Edge case - extremely high rank difference
    extreme_rank_score = calculator.calculate_fairness_score(
        team_avg_winrate=0.5,
        enemy_avg_winrate=0.5,
        avg_rank_difference=2000.0  # Very high rank difference
    )
    assert 0.0 <= extreme_rank_score <= 1.0, \
        f"Extreme rank difference should still produce valid score [0.0, 1.0], got {extreme_rank_score}"

    # Test 5: Edge case - zero winrates
    zero_winrate_score = calculator.calculate_fairness_score(
        team_avg_winrate=0.0,
        enemy_avg_winrate=0.0,
        avg_rank_difference=100.0
    )
    assert 0.0 <= zero_winrate_score <= 1.0, \
        f"Zero winrates should produce valid score [0.0, 1.0], got {zero_winrate_score}"

    # Test 6: Edge case - maximum winrate difference
    max_winrate_diff_score = calculator.calculate_fairness_score(
        team_avg_winrate=1.0,
        enemy_avg_winrate=0.0,
        avg_rank_difference=0.0
    )
    assert 0.0 <= max_winrate_diff_score <= 1.0, \
        f"Maximum winrate difference should produce valid score [0.0, 1.0], got {max_winrate_diff_score}"

    # Test 7: All scores should be within valid range [0.0, 1.0]
    test_cases = [
        (0.6, 0.4, 300.0),   # Moderate imbalance
        (0.8, 0.2, 500.0),   # High imbalance
        (0.9, 0.1, 100.0),   # Extreme winrate imbalance, small rank diff
        (0.51, 0.49, 1000.0), # Small winrate diff, large rank diff
    ]

    for team_winrate, enemy_winrate, rank_diff in test_cases:
        score = calculator.calculate_fairness_score(team_winrate, enemy_winrate, rank_diff)
        assert 0.0 <= score <= 1.0, \
            f"Score should be within [0.0, 1.0] for inputs ({team_winrate}, {enemy_winrate}, {rank_diff}), got {score}"


async def test_extract_participant_winrate(service, mock_db):
    """Test the MatchDataProcessor._extract_participant_winrate method queries database correctly"""
    processor = service.match_processor

    # Test 1: Normal case - player found in database with 25 wins, 15 losses -> should return 0.625
    mock_rank_data = MagicMock()
    mock_rank_data.wins = 25
    mock_rank_data.losses = 15

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_rank_data
    mock_db.execute = AsyncMock(return_value=mock_result)

    winrate = await processor._extract_participant_winrate("test-uuid-1", mock_db)
    expected_winrate = 25 / (25 + 15)  # 0.625
    assert winrate == expected_winrate, f"Normal case should return {expected_winrate}, got {winrate}"
    assert 0.0 <= winrate <= 1.0, f"Winrate should be between 0.0 and 1.0, got {winrate}"

    # Test 2: Player not found in database -> should return None
    mock_result_not_found = MagicMock()
    mock_result_not_found.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result_not_found)

    winrate = await processor._extract_participant_winrate("test-uuid-not-found", mock_db)
    assert winrate is None, f"Player not in database should return None, got {winrate}"

    # Test 3: Player with 0 total games -> should return None
    mock_rank_data_no_games = MagicMock()
    mock_rank_data_no_games.wins = 0
    mock_rank_data_no_games.losses = 0

    mock_result_no_games = MagicMock()
    mock_result_no_games.scalar_one_or_none.return_value = mock_rank_data_no_games
    mock_db.execute = AsyncMock(return_value=mock_result_no_games)

    winrate = await processor._extract_participant_winrate("test-uuid-no-games", mock_db)
    assert winrate is None, f"Zero games should return None, got {winrate}"


async def test_process_match_data_missing_player(service, mock_db):
    """Test MatchDataProcessor.process_match_data method with missing player scenarios for graceful handling"""
    processor = service.match_processor

    # Test 1: Empty participants list - should return None gracefully
    empty_match_data = {
        "info": {
            "participants": []
        }
    }
    target_player_puuid = "target-player-uuid"

    result = await processor.process_match_data(empty_match_data, target_player_puuid, mock_db)
    assert result is None, "Empty participants list should return None"

    # Test 2: Player not in participants list - should return None gracefully
    match_with_other_players = {
        "info": {
            "participants": [
                {
                    "puuid": "other-player-1",
                    "teamId": 100,
                    "win": True,
                    "tier": "GOLD",
                    "rank": "II",
                    "wins": 45,
                    "losses": 30,
                },
                {
                    "puuid": "other-player-2",
                    "teamId": 200,
                    "win": False,
                    "tier": "SILVER",
                    "rank": "I",
                    "wins": 20,
                    "losses": 25,
                }
            ]
        }
    }

    result = await processor.process_match_data(match_with_other_players, target_player_puuid, mock_db)
    assert result is None, "Target player not found should return None"

    # Test 3: Malformed match data - missing participants structure - should return None gracefully
    malformed_match_data = {
        "info": {
            # Missing participants key entirely
            "gameDuration": 1800,
            "gameMode": "CLASSIC"
        }
    }

    result = await processor.process_match_data(malformed_match_data, target_player_puuid, mock_db)
    assert result is None, "Missing participants structure should return None"

    # Test 4: Malformed match data - missing info structure - should return None gracefully
    missing_info_match = {
        "metadata": {
            "matchId": "test-match-id"
        }
        # Missing info key entirely
    }

    result = await processor.process_match_data(missing_info_match, target_player_puuid, mock_db)
    assert result is None, "Missing info structure should return None"

    # Test 5: None match data - should return None gracefully without crashing
    result = await processor.process_match_data(None, target_player_puuid, mock_db)
    assert result is None, "None match data should return None"

    # Test 6: Empty dict match data - should return None gracefully
    empty_match = {}

    result = await processor.process_match_data(empty_match, target_player_puuid, mock_db)
    assert result is None, "Empty match data should return None"

    # Test 7: Participants list with None values - should return None gracefully
    participants_with_none = {
        "info": {
            "participants": [
                None,  # None participant
                {
                    "puuid": "other-player-2",
                    "teamId": 100,
                    "win": True,
                    "tier": "GOLD",
                    "rank": "I"
                }
            ]
        }
    }

    result = await processor.process_match_data(participants_with_none, target_player_puuid, mock_db)
    assert result is None, "Participants with None values should return None"

    # Test 8: Participant without puuid field - should return None gracefully
    participant_without_puuid = {
        "info": {
            "participants": [
                {
                    # Missing puuid field
                    "teamId": 100,
                    "win": True,
                    "tier": "GOLD",
                    "rank": "II",
                    "wins": 45,
                    "losses": 30,
                }
            ]
        }
    }

    result = await processor.process_match_data(participant_without_puuid, target_player_puuid, mock_db)
    assert result is None, "Participant without puuid should return None"

    # Test 9: Target player found but missing teamId - should return None gracefully
    player_missing_team_id = {
        "info": {
            "participants": [
                {
                    "puuid": target_player_puuid,
                    # Missing teamId field
                    "win": True,
                    "tier": "GOLD",
                    "rank": "II",
                    "wins": 45,
                    "losses": 30,
                }
            ]
        }
    }

    result = await processor.process_match_data(player_missing_team_id, target_player_puuid, mock_db)
    assert result is None, "Target player missing teamId should return None"

    # Test 10: Verify method doesn't raise exceptions for any malformed input
    malformed_inputs = [
        None,
        {},
        {"info": None},
        {"info": {}},
        {"info": {"participants": None}},
        {"info": {"participants": "not-a-list"}},
        {"wrong": "structure"},
        {"info": {"participants": [{}]}},
    ]

    for malformed_input in malformed_inputs:
        try:
            result = await processor.process_match_data(malformed_input, target_player_puuid, mock_db)
            assert result is None, f"Malformed input {malformed_input} should return None"
        except Exception as e:
            pytest.fail(f"_process_match_data should not raise exceptions for malformed input: {e}")

    # Test 11: Edge case - target player found but no win field
    player_missing_win = {
        "info": {
            "participants": [
                {
                    "puuid": target_player_puuid,
                    "teamId": 100,
                    # Missing win field - should default to False
                    "tier": "GOLD",
                    "rank": "II",
                    "wins": 45,
                    "losses": 30,
                }
            ]
        }
    }

    result = await processor.process_match_data(player_missing_win, target_player_puuid, mock_db)
    # This should actually work because missing win field defaults to False
    if result is not None:
        assert result["player_win"] is False, "Missing win field should default to False"

    # Test 12: Test with empty string PUUID
    empty_puuid_match = {
        "info": {
            "participants": [
                {
                    "puuid": "",
                    "teamId": 100,
                    "win": True,
                    "tier": "GOLD",
                    "rank": "II",
                }
            ]
        }
    }

    result = await processor.process_match_data(empty_puuid_match, "", mock_db)
    # Empty string PUUID should match empty string participant
    if result is not None:
        assert result["player_win"] is True
        assert result["team_winrates"] == []
        assert result["enemy_winrates"] == []


async def test_execute_background_analysis_no_matches(service, mock_repository, mock_gateway):
    """Test execute_background_analysis method when no matches are found"""
    from app.core.exceptions import MatchmakingAnalysisError

    # Setup mock job with valid parameters
    mock_job = MagicMock()
    mock_job.id = "test-job-123"
    mock_job.user_id = "test-user-456"
    mock_job.parameters = {
        "puuid": "test-player-uuid",
        "region": "na"
    }
    mock_job.status = "PENDING"

    # Mock job methods
    mock_job.start_analysis = MagicMock()
    mock_job.calculate_progress = MagicMock(return_value=0.0)
    mock_job.handle_failure = MagicMock()

    # Setup repository mock
    mock_repository.get_analysis_by_id.return_value = mock_job
    mock_repository.update_analysis_status = AsyncMock()

    # Setup gateway mock to return empty list (no matches found)
    mock_gateway.get_player_recent_matches.return_value = []

    # Execute the background analysis - should raise MatchmakingAnalysisError
    with pytest.raises(MatchmakingAnalysisError, match="No valid matches found"):
        await service.execute_background_analysis("test-job-123")

    # Verify job was retrieved
    mock_repository.get_analysis_by_id.assert_called_once_with("test-job-123")

    # Verify gateway was called with correct parameters
    mock_gateway.get_player_recent_matches.assert_called_once_with("test-player-uuid", 50)
