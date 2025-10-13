"""
Tests for algorithm integration in SmurfDetectionService.

This module tests the integration of the 4 newly added algorithm methods:
- analyze_rank_discrepancy
- analyze_performance_trends
- analyze_role_performance
- analyze_win_rate_trend
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.detection import SmurfDetectionService
from app.models.players import Player
from app.models.ranks import PlayerRank
from app.schemas.detection import DetectionFactor


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_riot_client():
    """Mock Riot API client."""
    client = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def detection_service(mock_db, mock_riot_client):
    """Create SmurfDetectionService instance with mocked dependencies."""
    return SmurfDetectionService(mock_db, mock_riot_client)


@pytest.fixture
def sample_player():
    """Create a sample player for testing."""
    return Player(
        puuid=uuid4(),
        riot_id="TestPlayer",
        tag_line="NA1",
        summoner_name="TestSummoner",
        platform="NA1",
        account_level=25,
        last_seen=datetime.now(),
    )


@pytest.fixture
def sample_gold_rank():
    """Create a Gold rank for testing."""
    return PlayerRank(
        id=1,
        puuid=uuid4(),
        queue_type="RANKED_SOLO_5x5",
        tier="GOLD",
        rank="II",
        league_points=75,
        wins=25,
        losses=15,
        is_current=True,
        created_at=datetime.now() - timedelta(days=30),
    )


@pytest.fixture
def sample_iron_rank():
    """Create an Iron rank for testing."""
    return PlayerRank(
        id=1,
        puuid=uuid4(),
        queue_type="RANKED_SOLO_5x5",
        tier="IRON",
        rank="III",
        league_points=20,
        wins=5,
        losses=8,
        is_current=True,
        created_at=datetime.now() - timedelta(days=5),
    )


@pytest.fixture
def high_performance_matches():
    """Create high-performance match data for testing."""
    return [
        {
            "match_id": f"match{i}",
            "game_creation": int(
                (datetime.now() - timedelta(days=i)).timestamp() * 1000
            ),
            "queue_id": 420,
            "win": True,
            "kills": 10 + i,
            "deaths": 2,
            "assists": 8,
            "cs": 250 + i * 10,
            "vision_score": 30 + i,
            "champion_id": i + 1,
            "role": "MIDDLE",
            "team_id": 100,
        }
        for i in range(15)
    ]


@pytest.fixture
def multi_role_high_performance_matches():
    """Create multi-role high-performance matches."""
    roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "SUPPORT"]
    matches = []
    for i in range(15):
        matches.append(
            {
                "match_id": f"match{i}",
                "game_creation": int(
                    (datetime.now() - timedelta(days=i)).timestamp() * 1000
                ),
                "queue_id": 420,
                "win": True,
                "kills": 8 + i % 3,
                "deaths": 2,
                "assists": 10,
                "cs": 220 + i * 5,
                "vision_score": 25 + i,
                "champion_id": i + 1,
                "role": roles[i % len(roles)],
                "team_id": 100,
            }
        )
    return matches


@pytest.fixture
def improving_performance_matches():
    """Create matches showing improvement over time."""
    matches = []
    # Early matches: poor performance
    for i in range(5):
        matches.append(
            {
                "match_id": f"old_match{i}",
                "game_creation": int(
                    (datetime.now() - timedelta(days=20 + i)).timestamp() * 1000
                ),
                "queue_id": 420,
                "win": i % 2 == 0,  # 60% win rate
                "kills": 3 + i % 2,
                "deaths": 5,
                "assists": 4,
                "cs": 150 + i * 5,
                "vision_score": 15,
                "champion_id": i + 1,
                "role": "MIDDLE",
                "team_id": 100,
            }
        )

    # Recent matches: excellent performance
    for i in range(5, 15):
        matches.append(
            {
                "match_id": f"new_match{i}",
                "game_creation": int(
                    (datetime.now() - timedelta(days=i - 5)).timestamp() * 1000
                ),
                "queue_id": 420,
                "win": True,  # 100% win rate
                "kills": 12,
                "deaths": 2,
                "assists": 10,
                "cs": 280,
                "vision_score": 35,
                "champion_id": i + 1,
                "role": "MIDDLE",
                "team_id": 100,
            }
        )

    # Return in reverse order (newest first)
    return list(reversed(matches))


class TestRankDiscrepancyIntegration:
    """Test rank discrepancy algorithm integration."""

    @pytest.mark.asyncio
    async def test_high_skill_low_rank_flags_smurf(
        self, detection_service, sample_iron_rank
    ):
        """Test that high skill in low rank flags as smurf."""
        # High performance metrics
        performance_metrics = {
            "kda": 5.0,  # Very high for Iron
            "win_rate": 0.80,  # High win rate
        }

        result = detection_service.rank_analyzer.analyze_rank_discrepancy(
            sample_iron_rank, performance_metrics
        )

        assert result["is_suspicious"] is True
        assert result["tier_mismatch"] is True
        assert result["discrepancy_score"] > 0.15
        assert result["actual_kda"] > result["expected_kda"]

    @pytest.mark.asyncio
    async def test_appropriate_skill_no_flag(self, detection_service, sample_gold_rank):
        """Test that appropriate skill for rank doesn't flag."""
        # Normal performance for Gold
        performance_metrics = {
            "kda": 2.0,  # Expected for Gold
            "win_rate": 0.52,  # Expected for Gold
        }

        result = detection_service.rank_analyzer.analyze_rank_discrepancy(
            sample_gold_rank, performance_metrics
        )

        assert result["is_suspicious"] is False
        assert result["tier_mismatch"] is False
        assert result["discrepancy_score"] <= 0.15

    @pytest.mark.asyncio
    async def test_rank_discrepancy_with_no_rank_data(self, detection_service):
        """Test handling of player with no rank data."""
        # Create unranked player rank
        unranked = PlayerRank(
            id=1,
            puuid=uuid4(),
            queue_type="RANKED_SOLO_5x5",
            tier="UNRANKED",
            rank=None,
            league_points=0,
            wins=0,
            losses=0,
            is_current=True,
            created_at=datetime.now(),
        )

        performance_metrics = {"kda": 3.0, "win_rate": 0.60}

        # Should handle gracefully with tier_level 0
        result = detection_service.rank_analyzer.analyze_rank_discrepancy(
            unranked, performance_metrics
        )

        assert "discrepancy_score" in result
        assert "is_suspicious" in result


class TestPerformanceTrendsIntegration:
    """Test performance trends algorithm integration."""

    @pytest.mark.asyncio
    async def test_sudden_improvement_flags_smurf(
        self, detection_service, improving_performance_matches
    ):
        """Test that sudden improvement pattern flags as smurf."""
        result = detection_service.performance_analyzer.analyze_performance_trends(
            improving_performance_matches
        )

        assert result["trend"] == "improving"
        assert result["trend_score"] > 0.0
        assert result["performance_change"] > 0.2  # Significant improvement
        assert result["recent_performance"] > result["early_performance"]

    @pytest.mark.asyncio
    async def test_stable_high_performance_flags(
        self, detection_service, high_performance_matches
    ):
        """Test that stable high performance flags as suspicious."""
        result = detection_service.performance_analyzer.analyze_performance_trends(
            high_performance_matches
        )

        assert result["is_suspiciously_stable"] is True
        assert result["overall_performance"] > 0.7
        assert result["stability_score"] > 0.8

    @pytest.mark.asyncio
    async def test_insufficient_match_data_handled(self, detection_service):
        """Test handling of insufficient match data (< 10 games)."""
        few_matches = [
            {
                "match_id": f"match{i}",
                "game_creation": int(datetime.now().timestamp() * 1000),
                "kills": 5,
                "deaths": 3,
                "assists": 7,
                "cs": 200,
                "vision_score": 25,
            }
            for i in range(5)
        ]

        result = detection_service.performance_analyzer.analyze_performance_trends(
            few_matches
        )

        assert result["trend"] == "insufficient_data"
        assert result["score"] == 0.0


class TestRolePerformanceIntegration:
    """Test role performance algorithm integration."""

    @pytest.mark.asyncio
    async def test_multi_role_high_performer_booster_indicator(
        self, detection_service, multi_role_high_performance_matches
    ):
        """Test that multi-role high performance indicates booster."""
        result = detection_service.performance_analyzer.analyze_role_performance(
            multi_role_high_performance_matches
        )

        # Should detect high performance across multiple roles
        assert result["consistent_high_performance"] >= 2
        assert len(result["role_stats"]) >= 3
        assert len(result["suspicious_patterns"]) > 0

    @pytest.mark.asyncio
    async def test_single_role_specialist_normal_smurf(
        self, detection_service, high_performance_matches
    ):
        """Test that single-role specialist shows normal smurf pattern."""
        result = detection_service.performance_analyzer.analyze_role_performance(
            high_performance_matches
        )

        # Should show high performance in single role
        assert len(result["role_stats"]) <= 2  # Mostly one role
        role_stats = result["role_stats"]

        # Check that the main role has high performance
        if "MIDDLE" in role_stats:
            assert role_stats["MIDDLE"]["avg_kda"] >= 3.5

    @pytest.mark.asyncio
    async def test_normal_multi_role_player_no_flag(self, detection_service):
        """Test that normal multi-role player doesn't flag."""
        # Create matches with normal performance across roles
        normal_matches = []
        roles = ["TOP", "JUNGLE", "MIDDLE"]
        for i in range(15):
            normal_matches.append(
                {
                    "match_id": f"match{i}",
                    "kills": 4,
                    "deaths": 4,
                    "assists": 6,
                    "cs": 180,
                    "vision_score": 20,
                    "role": roles[i % len(roles)],
                }
            )

        result = detection_service.performance_analyzer.analyze_role_performance(
            normal_matches
        )

        # Should not flag as suspicious
        assert result["consistent_high_performance"] == 0
        assert len(result["suspicious_patterns"]) == 0


class TestWinRateTrendIntegration:
    """Test win rate trend algorithm integration."""

    @pytest.mark.asyncio
    async def test_sudden_win_rate_spike_flags(
        self, detection_service, improving_performance_matches
    ):
        """Test that sudden win rate spike flags as smurf."""
        result = detection_service.win_rate_analyzer.analyze_win_rate_trend(
            improving_performance_matches
        )

        assert result["trend"] == "improving"
        assert result["score"] > 0.0
        assert result["improvement"] > 0.1
        assert result["recent_win_rate"] > result["older_win_rate"]

    @pytest.mark.asyncio
    async def test_gradual_improvement_low_score(self, detection_service):
        """Test that gradual improvement doesn't flag strongly."""
        # Create matches with gradual win rate improvement
        gradual_matches = []
        for i in range(20):
            # Win rate gradually increases from 45% to 55%
            win = (i >= 10 and i % 2 == 0) or (i < 10 and i % 3 == 0)
            gradual_matches.append(
                {
                    "match_id": f"match{i}",
                    "win": win,
                }
            )

        # Reverse to get newest first
        gradual_matches = list(reversed(gradual_matches))

        result = detection_service.win_rate_analyzer.analyze_win_rate_trend(
            gradual_matches
        )

        # Should show improvement but not strong signal
        assert abs(result["improvement"]) <= 0.2  # Modest improvement


class TestOverallDetectionScoreIntegration:
    """Test overall detection score calculation with new factors."""

    @pytest.mark.asyncio
    async def test_factor_weights_sum_to_one(self, detection_service):
        """Test that factor weights sum to 1.0."""
        weights = detection_service.weights
        total_weight = sum(weights.values())

        # Should be approximately 1.0 (allowing for float precision)
        assert abs(total_weight - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_detection_score_calculation_correct(self, detection_service):
        """Test that overall detection score calculation is correct."""
        # Create test factors with known values
        test_factors = [
            DetectionFactor(
                name="win_rate",
                value=0.7,
                meets_threshold=True,
                weight=0.35,
                description="Test",
                score=0.8,
            ),
            DetectionFactor(
                name="account_level",
                value=25.0,
                meets_threshold=True,
                weight=0.15,
                description="Test",
                score=0.15,
            ),
            DetectionFactor(
                name="rank_progression",
                value=50.0,
                meets_threshold=True,
                weight=0.25,
                description="Test",
                score=0.5,
            ),
            DetectionFactor(
                name="performance_consistency",
                value=0.85,
                meets_threshold=True,
                weight=0.20,
                description="Test",
                score=0.85,
            ),
            DetectionFactor(
                name="kda",
                value=4.0,
                meets_threshold=True,
                weight=0.05,
                description="Test",
                score=1.0,
            ),
        ]

        score = detection_service._calculate_detection_score(test_factors)

        # Expected: (0.8*0.35) + (0.15*0.15) + (0.5*0.25) + (0.85*0.20) + (1.0*0.05)
        expected = (
            (0.8 * 0.35) + (0.15 * 0.15) + (0.5 * 0.25) + (0.85 * 0.20) + (1.0 * 0.05)
        )

        assert abs(score - expected) < 0.001

    @pytest.mark.asyncio
    async def test_new_factors_improve_detection_accuracy(
        self,
        detection_service,
        mock_db,
        sample_player,
        high_performance_matches,
        sample_iron_rank,
    ):
        """Test that adding new factors improves detection accuracy."""
        puuid = str(sample_player.puuid)

        # Mock database calls
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        # Mock dependencies
        with (
            patch.object(
                detection_service,
                "_get_recent_matches",
                return_value=(high_performance_matches, ["match1"]),
            ),
            patch.object(
                detection_service, "_get_current_rank", return_value=sample_iron_rank
            ),
            patch.object(detection_service, "_store_detection_result") as mock_store,
            patch.object(detection_service, "_mark_matches_processed"),
        ):
            # Mock stored detection result
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            result = await detection_service.analyze_player(puuid=puuid, min_games=10)

        # Should detect smurf with high confidence
        assert result.is_smurf is True
        assert result.detection_score > 0.6  # Should have high score
        assert len(result.factors) >= 5  # Should have all factors

    @pytest.mark.asyncio
    async def test_existing_detection_still_works(
        self, detection_service, mock_db, sample_player
    ):
        """Regression test: ensure existing detection logic still works."""
        puuid = str(sample_player.puuid)

        # Create normal matches (should not flag as smurf)
        normal_matches = [
            {
                "match_id": f"match{i}",
                "game_creation": int(
                    (datetime.now() - timedelta(days=i)).timestamp() * 1000
                ),
                "queue_id": 420,
                "win": i % 2 == 0,  # 50% win rate
                "kills": 4,
                "deaths": 4,
                "assists": 6,
                "cs": 180,
                "vision_score": 20,
                "champion_id": i + 1,
                "role": "MIDDLE",
                "team_id": 100,
            }
            for i in range(30)
        ]

        # Mock database calls
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        with (
            patch.object(
                detection_service,
                "_get_recent_matches",
                return_value=(normal_matches, ["match1"]),
            ),
            patch.object(detection_service, "_get_current_rank", return_value=None),
            patch.object(detection_service, "_store_detection_result") as mock_store,
            patch.object(detection_service, "_mark_matches_processed"),
        ):
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Normal player should not be flagged
        assert result.is_smurf is False
        assert result.detection_score < 0.4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
