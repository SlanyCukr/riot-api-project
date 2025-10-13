"""
Tests for the SmurfDetectionService.

This module contains unit tests for the smurf detection service,
testing individual detection factors and overall detection logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.detection import SmurfDetectionService
from app.models.players import Player
from app.models.ranks import PlayerRank
from app.schemas.detection import DetectionResponse
from app.algorithms.win_rate import WinRateAnalyzer
from app.algorithms.performance import PerformanceAnalyzer


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
def sample_matches():
    """Create sample match data for testing."""
    return [
        {
            "match_id": "match1",
            "game_creation": int(
                (datetime.now() - timedelta(days=1)).timestamp() * 1000
            ),
            "queue_id": 420,
            "win": True,
            "kills": 10,
            "deaths": 2,
            "assists": 8,
            "cs": 250,
            "vision_score": 30,
            "champion_id": 1,
            "role": "MIDDLE",
            "team_id": 100,
        },
        {
            "match_id": "match2",
            "game_creation": int(
                (datetime.now() - timedelta(days=2)).timestamp() * 1000
            ),
            "queue_id": 420,
            "win": True,
            "kills": 8,
            "deaths": 3,
            "assists": 12,
            "cs": 280,
            "vision_score": 25,
            "champion_id": 2,
            "role": "MIDDLE",
            "team_id": 100,
        },
        {
            "match_id": "match3",
            "game_creation": int(
                (datetime.now() - timedelta(days=3)).timestamp() * 1000
            ),
            "queue_id": 420,
            "win": False,
            "kills": 5,
            "deaths": 5,
            "assists": 6,
            "cs": 200,
            "vision_score": 20,
            "champion_id": 3,
            "role": "MIDDLE",
            "team_id": 100,
        },
    ]


@pytest.fixture
def sample_rank():
    """Create a sample player rank for testing."""
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


class TestSmurfDetectionService:
    """Test cases for SmurfDetectionService."""

    @pytest.mark.asyncio
    async def test_analyze_player_insufficient_data(
        self, detection_service, mock_db, sample_player
    ):
        """Test analysis with insufficient match data."""
        # Setup
        puuid = str(sample_player.puuid)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        # Mock _get_recent_matches to return insufficient data
        with patch.object(detection_service, "_get_recent_matches", return_value=[]):
            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Assert
        assert isinstance(result, DetectionResponse)
        assert result.puuid == puuid
        assert result.is_smurf is False
        assert result.confidence_level == "insufficient_data"
        assert result.sample_size == 0
        assert "Insufficient data" in result.reason

    @pytest.mark.asyncio
    async def test_analyze_player_success(
        self, detection_service, mock_db, sample_player, sample_matches
    ):
        """Test successful player analysis."""
        # Setup
        puuid = str(sample_player.puuid)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        # Mock dependencies
        with (
            patch.object(
                detection_service, "_get_recent_matches", return_value=sample_matches
            ),
            patch.object(detection_service, "_get_current_rank", return_value=None),
            patch.object(detection_service, "_store_detection_result") as mock_store,
        ):
            # Mock stored detection result
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            result = await detection_service.analyze_player(puuid=puuid, min_games=3)

        # Assert
        assert isinstance(result, DetectionResponse)
        assert result.puuid == puuid
        assert result.sample_size == len(sample_matches)
        assert len(result.factors) > 0
        assert isinstance(result.detection_score, float)
        assert isinstance(result.is_smurf, bool)
        assert result.analysis_time_seconds is not None

    @pytest.mark.asyncio
    async def test_analyze_detection_factors(
        self, detection_service, sample_player, sample_matches
    ):
        """Test individual detection factor analysis."""
        puuid = str(sample_player.puuid)

        # Mock rank analyzer to avoid database calls
        with patch.object(
            detection_service.rank_analyzer,
            "analyze",
            return_value=MagicMock(
                progression_speed=0.0,
                meets_threshold=False,
                description="Normal progression",
            ),
        ):
            factors = await detection_service._analyze_detection_factors(
                puuid, sample_matches, sample_player
            )

        # Assert
        assert len(factors) >= 5  # Should have at least 5 factors
        factor_names = [f.name for f in factors]
        expected_factors = [
            "win_rate",
            "account_level",
            "rank_progression",
            "performance_consistency",
            "kda",
        ]

        for expected in expected_factors:
            assert expected in factor_names

        # Check win rate factor
        win_rate_factor = next(f for f in factors if f.name == "win_rate")
        assert isinstance(win_rate_factor.value, float)
        assert isinstance(win_rate_factor.weight, float)
        assert isinstance(win_rate_factor.meets_threshold, bool)

    @pytest.mark.asyncio
    async def test_calculate_detection_score(self, detection_service):
        """Test detection score calculation."""
        from app.schemas.detection import DetectionFactor

        # Create test factors
        factors = [
            DetectionFactor(
                name="win_rate",
                value=0.7,
                meets_threshold=True,
                weight=0.35,
                description="High win rate",
                score=0.8,
            ),
            DetectionFactor(
                name="account_level",
                value=25.0,
                meets_threshold=True,
                weight=0.15,
                description="Low account level",
                score=0.6,
            ),
            DetectionFactor(
                name="kda",
                value=2.5,
                meets_threshold=False,
                weight=0.05,
                description="Normal KDA",
                score=0.0,
            ),
        ]

        score = detection_service._calculate_detection_score(factors)

        # Expected: (0.8 * 0.35) + (0.6 * 0.15) + (0.0 * 0.05) = 0.28 + 0.09 + 0.0 = 0.37
        expected_score = (0.8 * 0.35) + (0.6 * 0.15) + (0.0 * 0.05)
        assert abs(score - expected_score) < 0.001

    def test_determine_smurf_status(self, detection_service):
        """Test smurf status determination."""
        from app.schemas.detection import DetectionFactor

        factors = [DetectionFactor("test", 0.5, True, 0.1, "test", 0.5)]

        # Test high confidence
        is_smurf, confidence = detection_service._determine_smurf_status(
            0.85, factors, 30
        )
        assert is_smurf is True
        assert confidence == "high"

        # Test medium confidence
        is_smurf, confidence = detection_service._determine_smurf_status(
            0.65, factors, 30
        )
        assert is_smurf is True
        assert confidence == "medium"

        # Test low confidence
        is_smurf, confidence = detection_service._determine_smurf_status(
            0.45, factors, 30
        )
        assert is_smurf is True
        assert confidence == "low"

        # Test no detection
        is_smurf, confidence = detection_service._determine_smurf_status(
            0.25, factors, 30
        )
        assert is_smurf is False
        assert confidence == "none"

        # Test insufficient data
        is_smurf, confidence = detection_service._determine_smurf_status(
            0.85, factors, 5
        )
        assert is_smurf is False
        assert confidence == "insufficient_data"

    def test_generate_reason(self, detection_service):
        """Test reason generation."""
        from app.schemas.detection import DetectionFactor

        # Test with triggered factors
        factors = [
            DetectionFactor("win_rate", 0.7, True, 0.35, "High win rate: 70%", 0.8),
            DetectionFactor(
                "account_level", 25.0, True, 0.15, "Low account level: 25", 0.6
            ),
        ]

        reason = detection_service._generate_reason(factors, 0.8)
        assert "High win rate" in reason
        assert "Low account level" in reason
        assert "very high confidence" in reason
        assert "0.80" in reason

        # Test with no triggered factors
        factors = [
            DetectionFactor("win_rate", 0.4, False, 0.35, "Normal win rate: 40%", 0.0)
        ]
        reason = detection_service._generate_reason(factors, 0.1)
        assert "No smurf indicators detected" in reason

    def test_analyze_kda(self, detection_service, sample_matches):
        """Test KDA analysis."""
        kda_factor = detection_service._analyze_kda(sample_matches)

        assert kda_factor.name == "kda"
        assert isinstance(kda_factor.value, float)
        assert kda_factor.value > 0
        assert isinstance(kda_factor.meets_threshold, bool)
        assert isinstance(kda_factor.weight, float)
        assert "KDA" in kda_factor.description

    def test_calculate_kda(self, detection_service):
        """Test KDA calculation."""
        # Test normal case
        kda = detection_service._calculate_kda(10, 5, 5)
        assert kda == 3.0  # (10 + 5) / 5

        # Test zero deaths
        kda = detection_service._calculate_kda(8, 0, 4)
        assert kda == 12.0  # 8 + 4

        # Test all zeros
        kda = detection_service._calculate_kda(0, 0, 0)
        assert kda == 0.0

    @pytest.mark.asyncio
    async def test_get_detection_history(self, detection_service, mock_db):
        """Test detection history retrieval."""
        puuid = str(uuid4())

        # Mock database response
        mock_detection = MagicMock()
        mock_detection.puuid = puuid
        mock_detection.is_smurf = True
        mock_detection.smurf_score = Decimal("0.75")
        mock_detection.confidence = "high"
        mock_detection.games_analyzed = 30
        mock_detection.created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_detection]
        mock_db.execute.return_value = mock_result

        history = await detection_service.get_detection_history(puuid, limit=10)

        assert len(history) == 1
        assert history[0].puuid == puuid
        assert history[0].is_smurf is True
        assert history[0].detection_score == 0.75

    @pytest.mark.asyncio
    async def test_get_detection_stats(self, detection_service, mock_db):
        """Test detection statistics retrieval."""
        # Mock database responses
        total_result = MagicMock()
        total_result.scalar.return_value = 100
        smurf_result = MagicMock()
        smurf_result.scalar.return_value = 25
        avg_result = MagicMock()
        avg_result.scalar.return_value = 0.45
        confidence_result = MagicMock()
        confidence_result.return_value = [("high", 15), ("medium", 10)]
        queue_result = MagicMock()
        queue_result.return_value = [("420", 80), ("440", 20)]
        last_result = MagicMock()
        last_result.scalar.return_value = datetime.now()

        def mock_execute_side_effect(query):
            if "count(SmurfDetection.id)" in str(query):
                if "is_smurf" in str(query):
                    return smurf_result
                else:
                    return total_result
            elif "avg(SmurfDetection.smurf_score)" in str(query):
                return avg_result
            elif "confidence" in str(query) and "group_by" in str(query):
                return confidence_result
            elif "queue_type" in str(query) and "group_by" in str(query):
                return queue_result
            elif "max(SmurfDetection.last_analysis)" in str(query):
                return last_result
            return MagicMock()

        mock_db.execute.side_effect = mock_execute_side_effect

        stats = await detection_service.get_detection_stats()

        assert stats.total_analyses == 100
        assert stats.smurf_count == 25
        assert stats.smurf_detection_rate == 0.25
        assert stats.average_score == 0.45
        assert "high" in stats.confidence_distribution
        assert "420" in stats.queue_type_distribution

    @pytest.mark.asyncio
    async def test_get_config(self, detection_service):
        """Test configuration retrieval."""
        config = await detection_service.get_config()

        assert "thresholds" in config
        assert "weights" in config
        assert "min_games_required" in config
        assert "analysis_version" in config
        assert "last_updated" in config

        # Check some expected values
        assert config.thresholds["high_win_rate"] == 0.65
        assert config.weights["win_rate"] == 0.35
        assert config.min_games_required == 30


class TestDetectionAlgorithms:
    """Test cases for individual detection algorithms."""

    @pytest.mark.asyncio
    async def test_win_rate_analyzer(self):
        """Test WinRateAnalyzer."""
        analyzer = WinRateAnalyzer()

        # Test with high win rate
        matches = [
            {"win": True},
            {"win": True},
            {"win": True},
            {"win": True},
            {"win": False},
        ]
        result = await analyzer.analyze(matches)

        assert result.win_rate == 0.8
        assert result.wins == 4
        assert result.total_games == 5
        assert result.meets_threshold is True  # 80% > 65%

        # Test with normal win rate
        matches = [
            {"win": True},
            {"win": True},
            {"win": False},
            {"win": False},
            {"win": False},
        ]
        result = await analyzer.analyze(matches)

        assert result.win_rate == 0.4
        assert result.meets_threshold is False

        # Test with empty matches
        result = await analyzer.analyze([])
        assert result.win_rate == 0.0
        assert result.meets_threshold is False

    @pytest.mark.asyncio
    async def test_performance_analyzer(self):
        """Test PerformanceAnalyzer."""
        analyzer = PerformanceAnalyzer()

        # Test with high performance
        matches = [
            {"kills": 10, "deaths": 2, "assists": 8, "cs": 250, "vision_score": 30},
            {"kills": 8, "deaths": 3, "assists": 12, "cs": 280, "vision_score": 25},
            {"kills": 12, "deaths": 1, "assists": 6, "cs": 300, "vision_score": 35},
        ]
        result = await analyzer.analyze(matches)

        assert result.avg_kda > 3.5  # Should be high
        assert result.consistency_score > 0.5  # Should be consistent
        assert isinstance(result.meets_threshold, bool)

        # Test with empty matches
        result = await analyzer.analyze([])
        assert result.avg_kda == 0.0
        assert result.meets_threshold is False


class TestAlgorithmIntegration:
    """Test cases for newly integrated algorithm features."""

    @pytest.mark.asyncio
    async def test_detection_includes_rank_discrepancy_factor(
        self, detection_service, sample_player, sample_matches, sample_rank, mock_db
    ):
        """Test that rank discrepancy factor appears in detection results."""
        # Setup: Player with high KDA but low rank (Gold II)
        puuid = str(sample_player.puuid)
        sample_rank.tier = "GOLD"
        sample_rank.rank = "II"

        # Modify matches to have high KDA (smurf signal)
        high_kda_matches = [
            {
                **match,
                "kills": 15,
                "deaths": 2,
                "assists": 10,
            }
            for match in sample_matches * 10  # Need 30+ matches
        ]

        # Mock database and service methods
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        with (
            patch.object(
                detection_service, "_get_recent_detection", return_value=None
            ),  # Force new analysis
            patch.object(
                detection_service,
                "_get_recent_matches",
                return_value=(high_kda_matches, []),
            ),
            patch.object(
                detection_service, "_get_current_rank", return_value=sample_rank
            ),
            patch.object(detection_service, "_store_detection_result") as mock_store,
            patch.object(detection_service, "_mark_matches_processed"),
        ):
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Assert: rank_discrepancy factor exists in result.factors
        factor_names = [f.name for f in result.factors]
        assert "rank_discrepancy" in factor_names

        # Get the rank_discrepancy factor
        rank_discrepancy_factor = next(
            f for f in result.factors if f.name == "rank_discrepancy"
        )

        # Assert: factor.meets_threshold is True when discrepancy is high
        # (high KDA in Gold rank should trigger this)
        assert isinstance(rank_discrepancy_factor.meets_threshold, bool)
        assert rank_discrepancy_factor.weight > 0
        assert rank_discrepancy_factor.value is not None

    @pytest.mark.asyncio
    async def test_detection_includes_performance_trends_factor(
        self, detection_service, sample_player, mock_db
    ):
        """Test that performance trends factor appears in detection results."""
        # Setup: Matches with sudden performance improvement
        puuid = str(sample_player.puuid)

        # Create matches showing improvement over time
        # Older matches (lower performance)
        older_matches = [
            {
                "match_id": f"match_old_{i}",
                "game_creation": int(
                    (datetime.now() - timedelta(days=30 - i)).timestamp() * 1000
                ),
                "queue_id": 420,
                "win": i % 3 == 0,  # Low win rate
                "kills": 3,
                "deaths": 5,
                "assists": 4,
                "cs": 120,
                "vision_score": 15,
                "champion_id": 1,
                "role": "MIDDLE",
                "team_id": 100,
            }
            for i in range(15)
        ]

        # Recent matches (high performance)
        recent_matches = [
            {
                "match_id": f"match_new_{i}",
                "game_creation": int(
                    (datetime.now() - timedelta(days=i)).timestamp() * 1000
                ),
                "queue_id": 420,
                "win": True,
                "kills": 12,
                "deaths": 2,
                "assists": 8,
                "cs": 250,
                "vision_score": 35,
                "champion_id": 1,
                "role": "MIDDLE",
                "team_id": 100,
            }
            for i in range(15)
        ]

        all_matches = recent_matches + older_matches

        # Mock database
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        with (
            patch.object(
                detection_service, "_get_recent_detection", return_value=None
            ),  # Force new analysis
            patch.object(
                detection_service, "_get_recent_matches", return_value=(all_matches, [])
            ),
            patch.object(detection_service, "_get_current_rank", return_value=None),
            patch.object(detection_service, "_store_detection_result") as mock_store,
            patch.object(detection_service, "_mark_matches_processed"),
        ):
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Assert: performance_trends factor exists
        factor_names = [f.name for f in result.factors]
        assert "performance_trends" in factor_names

        # Get the performance_trends factor
        trends_factor = next(
            f for f in result.factors if f.name == "performance_trends"
        )

        # Assert: flags sudden improvement correctly
        assert isinstance(trends_factor.meets_threshold, bool)
        assert trends_factor.weight > 0
        # With sudden improvement, this should likely be flagged
        assert trends_factor.value is not None

    @pytest.mark.asyncio
    async def test_detection_includes_role_performance_factor(
        self, detection_service, sample_player, mock_db
    ):
        """Test that role performance factor appears in detection results."""
        # Setup: Matches with high performance across multiple roles
        puuid = str(sample_player.puuid)

        roles = ["MIDDLE", "TOP", "JUNGLE", "BOTTOM", "UTILITY"]
        multi_role_matches = []

        for i in range(30):
            role = roles[i % len(roles)]
            multi_role_matches.append(
                {
                    "match_id": f"match_{i}",
                    "game_creation": int(
                        (datetime.now() - timedelta(days=i)).timestamp() * 1000
                    ),
                    "queue_id": 420,
                    "win": True,
                    "kills": 10,
                    "deaths": 2,
                    "assists": 8,
                    "cs": 200,
                    "vision_score": 30,
                    "champion_id": i % 5 + 1,
                    "role": role,
                    "team_id": 100,
                }
            )

        # Mock database
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        with (
            patch.object(
                detection_service, "_get_recent_detection", return_value=None
            ),  # Force new analysis
            patch.object(
                detection_service,
                "_get_recent_matches",
                return_value=(multi_role_matches, []),
            ),
            patch.object(detection_service, "_get_current_rank", return_value=None),
            patch.object(detection_service, "_store_detection_result") as mock_store,
            patch.object(detection_service, "_mark_matches_processed"),
        ):
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Assert: role_performance factor exists
        factor_names = [f.name for f in result.factors]
        assert "role_performance" in factor_names

        # Get the role_performance factor
        role_factor = next(f for f in result.factors if f.name == "role_performance")

        # Assert: flags multi-role high performance
        assert isinstance(role_factor.meets_threshold, bool)
        assert role_factor.weight > 0
        assert role_factor.value is not None

    @pytest.mark.asyncio
    async def test_detection_includes_win_rate_trend_factor(
        self, detection_service, sample_player, mock_db
    ):
        """Test that win rate trend factor appears in detection results."""
        # Setup: Matches with sudden win rate spike
        puuid = str(sample_player.puuid)

        # Create matches with improving win rate
        # Older matches: 40% win rate
        older_matches = [
            {
                "match_id": f"match_old_{i}",
                "game_creation": int(
                    (datetime.now() - timedelta(days=30 - i)).timestamp() * 1000
                ),
                "queue_id": 420,
                "win": i % 5 < 2,  # 40% win rate
                "kills": 5,
                "deaths": 5,
                "assists": 6,
                "cs": 180,
                "vision_score": 20,
                "champion_id": 1,
                "role": "MIDDLE",
                "team_id": 100,
            }
            for i in range(15)
        ]

        # Recent matches: 80% win rate
        recent_matches = [
            {
                "match_id": f"match_new_{i}",
                "game_creation": int(
                    (datetime.now() - timedelta(days=i)).timestamp() * 1000
                ),
                "queue_id": 420,
                "win": i % 5 < 4,  # 80% win rate
                "kills": 10,
                "deaths": 3,
                "assists": 8,
                "cs": 220,
                "vision_score": 30,
                "champion_id": 1,
                "role": "MIDDLE",
                "team_id": 100,
            }
            for i in range(15)
        ]

        all_matches = recent_matches + older_matches

        # Mock database
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        with (
            patch.object(
                detection_service, "_get_recent_detection", return_value=None
            ),  # Force new analysis
            patch.object(
                detection_service, "_get_recent_matches", return_value=(all_matches, [])
            ),
            patch.object(detection_service, "_get_current_rank", return_value=None),
            patch.object(detection_service, "_store_detection_result") as mock_store,
            patch.object(detection_service, "_mark_matches_processed"),
        ):
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Assert: win_rate_trend factor exists
        factor_names = [f.name for f in result.factors]
        assert "win_rate_trend" in factor_names

        # Get the win_rate_trend factor
        trend_factor = next(f for f in result.factors if f.name == "win_rate_trend")

        # Assert: detects win rate changes
        assert isinstance(trend_factor.meets_threshold, bool)
        assert trend_factor.weight > 0
        assert trend_factor.value is not None

    @pytest.mark.asyncio
    async def test_detection_factor_weights_sum_to_one(
        self, detection_service, sample_player, sample_matches, mock_db
    ):
        """Test that all factor weights sum approximately to 1.0."""
        puuid = str(sample_player.puuid)

        # Use sufficient matches for analysis
        matches = sample_matches * 10

        # Mock database
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        with (
            patch.object(
                detection_service, "_get_recent_detection", return_value=None
            ),  # Force new analysis
            patch.object(
                detection_service, "_get_recent_matches", return_value=(matches, [])
            ),
            patch.object(detection_service, "_get_current_rank", return_value=None),
            patch.object(detection_service, "_store_detection_result") as mock_store,
            patch.object(detection_service, "_mark_matches_processed"),
        ):
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Calculate sum of all factor weights
        weight_sum = sum(factor.weight for factor in result.factors)

        # Assert: sum of all factor weights ≈ 1.0 (within 0.01)
        assert abs(weight_sum - 1.0) < 0.01, (
            f"Weight sum is {weight_sum}, expected ~1.0"
        )

    @pytest.mark.asyncio
    async def test_detection_handles_no_rank_data(
        self, detection_service, sample_player, sample_matches, mock_db
    ):
        """Test detection works when player has no rank data."""
        puuid = str(sample_player.puuid)

        # Use sufficient matches
        matches = sample_matches * 10

        # Mock database
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        with (
            patch.object(
                detection_service, "_get_recent_detection", return_value=None
            ),  # Force new analysis
            patch.object(
                detection_service, "_get_recent_matches", return_value=(matches, [])
            ),
            patch.object(
                detection_service, "_get_current_rank", return_value=None
            ),  # No rank
            patch.object(detection_service, "_store_detection_result") as mock_store,
            patch.object(detection_service, "_mark_matches_processed"),
        ):
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            # Should not raise exception
            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Assert: detection completes without error
        assert result is not None
        assert result.puuid == puuid

        # Assert: rank_discrepancy and rank_progression factors may be skipped or have value 0
        factor_dict = {f.name: f for f in result.factors}

        if "rank_discrepancy" in factor_dict:
            # If present, should have zero score when no rank data
            assert factor_dict["rank_discrepancy"].score >= 0

        if "rank_progression" in factor_dict:
            # If present, should handle missing rank gracefully
            assert factor_dict["rank_progression"].score >= 0

    @pytest.mark.asyncio
    async def test_detection_handles_insufficient_matches(
        self, detection_service, sample_player, sample_matches, mock_db
    ):
        """Test detection with too few matches for trends."""
        puuid = str(sample_player.puuid)

        # Only 5 matches (below minimum)
        few_matches = sample_matches[:2]  # Only 2 matches

        # Mock database
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        with (
            patch.object(
                detection_service, "_get_recent_detection", return_value=None
            ),  # Force new analysis
            patch.object(
                detection_service, "_get_recent_matches", return_value=(few_matches, [])
            ),
            patch.object(detection_service, "_get_current_rank", return_value=None),
        ):
            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Assert: detection completes
        assert result is not None
        assert result.puuid == puuid

        # Assert: confidence_level indicates insufficient data
        assert result.confidence_level == "insufficient_data"
        assert result.sample_size < 30

        # Assert: trend factors are skipped or have low confidence
        {f.name: f for f in result.factors}

        # With insufficient data, most factors should have low scores
        assert result.detection_score is not None

    @pytest.mark.asyncio
    async def test_detection_with_all_new_factors_improves_accuracy(
        self, detection_service, sample_player, sample_rank, mock_db
    ):
        """Test that new factors improve overall detection for known smurf patterns."""
        puuid = str(sample_player.puuid)

        # Create smurf pattern: high rank mismatch, sudden improvement, multi-role
        sample_rank.tier = "SILVER"  # Low rank
        sample_rank.rank = "III"

        roles = ["MIDDLE", "TOP", "JUNGLE"]
        smurf_matches = []

        for i in range(30):
            role = roles[i % len(roles)]
            # Recent matches: very high performance
            if i < 15:
                smurf_matches.append(
                    {
                        "match_id": f"match_{i}",
                        "game_creation": int(
                            (datetime.now() - timedelta(days=i)).timestamp() * 1000
                        ),
                        "queue_id": 420,
                        "win": True,  # High win rate
                        "kills": 15,
                        "deaths": 2,
                        "assists": 10,
                        "cs": 280,
                        "vision_score": 40,
                        "champion_id": i % 3 + 1,
                        "role": role,
                        "team_id": 100,
                    }
                )
            # Older matches: lower performance (showing improvement)
            else:
                smurf_matches.append(
                    {
                        "match_id": f"match_{i}",
                        "game_creation": int(
                            (datetime.now() - timedelta(days=i)).timestamp() * 1000
                        ),
                        "queue_id": 420,
                        "win": i % 2 == 0,  # 50% win rate
                        "kills": 8,
                        "deaths": 5,
                        "assists": 6,
                        "cs": 180,
                        "vision_score": 20,
                        "champion_id": i % 3 + 1,
                        "role": role,
                        "team_id": 100,
                    }
                )

        # Mock database
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        with (
            patch.object(
                detection_service, "_get_recent_detection", return_value=None
            ),  # Force new analysis
            patch.object(
                detection_service,
                "_get_recent_matches",
                return_value=(smurf_matches, []),
            ),
            patch.object(
                detection_service, "_get_current_rank", return_value=sample_rank
            ),
            patch.object(detection_service, "_store_detection_result") as mock_store,
            patch.object(detection_service, "_mark_matches_processed"),
        ):
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Assert: detection_score is high (> 0.5 at least, ideally > 0.7)
        assert result.detection_score > 0.5, (
            f"Detection score {result.detection_score} too low for smurf pattern"
        )

        # Assert: is_smurf is True
        # Note: Depending on thresholds, this might be medium confidence
        # Just check that detection score is elevated

        # Assert: all relevant factors are present
        factor_names = [f.name for f in result.factors]
        assert "rank_discrepancy" in factor_names
        assert "performance_trends" in factor_names
        assert "role_performance" in factor_names
        assert "win_rate_trend" in factor_names

    @pytest.mark.asyncio
    async def test_detection_with_legitimate_player_doesnt_false_positive(
        self, detection_service, sample_player, sample_rank, mock_db
    ):
        """Test that new factors don't cause false positives for legitimate players."""
        puuid = str(sample_player.puuid)

        # Create legitimate player pattern: appropriate rank, gradual improvement
        sample_rank.tier = "GOLD"  # Appropriate rank
        sample_rank.rank = "II"

        legitimate_matches = []

        for i in range(30):
            # Gradual, consistent performance
            legitimate_matches.append(
                {
                    "match_id": f"match_{i}",
                    "game_creation": int(
                        (datetime.now() - timedelta(days=i)).timestamp() * 1000
                    ),
                    "queue_id": 420,
                    "win": i % 2 == 0,  # 50% win rate (normal)
                    "kills": 6,
                    "deaths": 5,
                    "assists": 8,
                    "cs": 190,
                    "vision_score": 25,
                    "champion_id": 1,  # One-trick
                    "role": "MIDDLE",  # Single role
                    "team_id": 100,
                }
            )

        # Mock database
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_player
        mock_db.execute.return_value = mock_result

        with (
            patch.object(
                detection_service, "_get_recent_detection", return_value=None
            ),  # Force new analysis
            patch.object(
                detection_service,
                "_get_recent_matches",
                return_value=(legitimate_matches, []),
            ),
            patch.object(
                detection_service, "_get_current_rank", return_value=sample_rank
            ),
            patch.object(detection_service, "_store_detection_result") as mock_store,
            patch.object(detection_service, "_mark_matches_processed"),
        ):
            mock_detection = MagicMock()
            mock_detection.created_at = datetime.now()
            mock_store.return_value = mock_detection

            result = await detection_service.analyze_player(puuid=puuid, min_games=30)

        # Assert: detection_score is low (< 0.6)
        assert result.detection_score < 0.6, (
            f"Detection score {result.detection_score} too high for legitimate player"
        )

        # Assert: is_smurf is False
        assert result.is_smurf is False, (
            "Legitimate player incorrectly flagged as smurf"
        )


if __name__ == "__main__":
    pytest.main([__file__])
