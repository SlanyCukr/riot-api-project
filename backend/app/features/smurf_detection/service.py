"""
Player analysis service for multi-factor player analysis.

This service provides comprehensive player analysis by analyzing multiple
factors including win rate, account level, rank progression, and performance
consistency using modular factor analyzers.
"""

from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
import structlog

from app.core.riot_api.data_manager import RiotDataManager
from app.features.players.models import Player
from .models import SmurfDetection
from app.features.players.ranks import PlayerRank
from .schemas import (
    DetectionResponse,
    DetectionFactor,
)
from app.core.decorators import service_error_handler, input_validation
from .config import get_detection_config
from .analyzers import (
    WinRateFactorAnalyzer,
    WinRateTrendFactorAnalyzer,
    AccountLevelFactorAnalyzer,
    PerformanceFactorAnalyzer,
    RankProgressionFactorAnalyzer,
)

logger = structlog.get_logger(__name__)


class SmurfDetectionService:
    """Service for comprehensive player analysis using modular factor analyzers."""

    def __init__(self, db: AsyncSession, data_manager: RiotDataManager):
        """
        Initialize player analysis service.

        :param db: Database session
        :type db: AsyncSession
        :param data_manager: Riot API data manager
        :type data_manager: RiotDataManager
        """
        self.db = db
        self.data_manager = data_manager

        # Load configuration
        config = get_detection_config()
        self.thresholds = config["thresholds"]
        self.weights = config["weights"]
        self.analysis_config = config["analysis"]

        # Initialize modular factor analyzers
        self.factor_analyzers = {
            "win_rate": WinRateFactorAnalyzer(),
            "win_rate_trend": WinRateTrendFactorAnalyzer(),
            "account_level": AccountLevelFactorAnalyzer(),
            "performance_consistency": PerformanceFactorAnalyzer(),
            "rank_progression": RankProgressionFactorAnalyzer(),
        }

        logger.info(
            "SmurfDetectionService initialized",
            num_analyzers=len(self.factor_analyzers),
            config_version="1.0",
        )

    @service_error_handler("DetectionService")
    @input_validation(
        validate_non_empty=["puuid"],
        validate_positive=["min_games"],
    )
    async def analyze_player(
        self,
        puuid: str,
        min_games: int = 30,
        queue_filter: Optional[int] = None,
        time_period_days: Optional[int] = None,
        force_reanalyze: bool = False,
    ) -> DetectionResponse:
        """
        Comprehensive player analysis for a player.

        :param puuid: Player PUUID to analyze
        :type puuid: str
        :param min_games: Minimum games required for analysis
        :type min_games: int
        :param queue_filter: Optional queue filter
        :type queue_filter: Optional[int]
        :param time_period_days: Optional time period filter
        :type time_period_days: Optional[int]
        :param force_reanalyze: Force re-analysis even if recent analysis exists
        :type force_reanalyze: bool
        :returns: DetectionResponse with analysis results
        :rtype: DetectionResponse
        """
        start_time = datetime.now(timezone.utc)

        # Check if recent analysis exists (unless forced)
        if not force_reanalyze:
            recent_analysis = await self._get_recent_detection(puuid, hours=24)
            if recent_analysis:
                logger.info(
                    "Using recent detection analysis", puuid=puuid, age_hours=24
                )
                return self._convert_to_response(recent_analysis)

        # Get player data
        player = await self._get_player(puuid)
        if not player:
            raise ValueError(f"Player not found: {puuid}")

        # Get recent performance data
        recent_matches, match_ids = await self._get_recent_matches(
            puuid, queue_filter, min_games, time_period_days
        )

        # Apply analysis configuration limits
        max_matches = self.analysis_config.get("recent_matches_limit", 50)
        if len(recent_matches) > max_matches:
            recent_matches = recent_matches[:max_matches]
            match_ids = match_ids[:max_matches]
            logger.debug(
                "Limited matches by analysis_config",
                puuid=puuid,
                original_count=len(recent_matches),
                limited_to=max_matches,
            )

        if len(recent_matches) < min_games:
            logger.info(
                "Insufficient match data",
                puuid=puuid,
                matches=len(recent_matches),
                required=min_games,
            )
            return self._create_insufficient_data_response(
                puuid, len(recent_matches), min_games
            )

        # Analyze each factor
        factors = await self._analyze_detection_factors(puuid, recent_matches, player)

        # Calculate detection score
        detection_score = self._calculate_detection_score(factors)

        # Determine if smurf and confidence level
        is_smurf, confidence_level = self._determine_smurf_status(
            detection_score, factors, len(recent_matches)
        )

        # Store detection result
        detection = await self._store_detection_result(
            puuid=puuid,
            is_smurf=is_smurf,
            detection_score=detection_score,
            confidence_level=confidence_level,
            factors=factors,
            sample_size=len(recent_matches),
            queue_type=queue_filter,
            time_period_days=time_period_days,
            player=player,
        )

        # Mark matches as processed
        await self._mark_matches_processed(match_ids)

        # Calculate analysis time
        analysis_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.info(
            "Player analysis completed",
            puuid=puuid,
            is_smurf=is_smurf,
            detection_score=detection_score,
            confidence_level=confidence_level,
            analysis_time_seconds=analysis_time,
        )

        return DetectionResponse(
            puuid=puuid,
            is_smurf=is_smurf,
            detection_score=detection_score,
            confidence_level=confidence_level,
            factors=factors,
            reason=self._generate_reason(factors, detection_score),
            sample_size=len(recent_matches),
            analysis_time_seconds=analysis_time,
            created_at=detection.created_at,
        )

    async def _analyze_detection_factors(
        self, puuid: str, recent_matches: List[Dict[str, Any]], player: Player
    ) -> List[DetectionFactor]:
        """
        Analyze all detection factors using modular analyzers.

        This method coordinates the analysis of multiple detection factors
        using the modular analyzer system for better maintainability.

        :param puuid: Player UUID
        :type puuid: str
        :param recent_matches: List of recent match data
        :type recent_matches: List[Dict[str, Any]]
        :param player: Player model instance
        :type player: Player
        :returns: List of DetectionFactor objects
        :rtype: List[DetectionFactor]
        """
        factors: List[DetectionFactor] = []

        logger.info(
            "Starting factor analysis using modular analyzers",
            puuid=puuid,
            num_analyzers=len(self.factor_analyzers),
            match_count=len(recent_matches),
        )

        # Run each factor analyzer
        for factor_name, analyzer in self.factor_analyzers.items():
            factor = await analyzer.analyze(puuid, recent_matches, player, self.db)
            factors.append(factor)
            logger.debug(
                "Factor analysis completed",
                puuid=puuid,
                factor=factor_name,
                meets_threshold=factor.meets_threshold,
                score=factor.score,
            )

        logger.info(
            "Factor analysis completed",
            puuid=puuid,
            total_factors=len(factors),
            successful_analyzers=sum(1 for f in factors if f.score > 0),
        )

        # Add legacy KDA factor (to be migrated to factor analyzer)
        factors.append(self._analyze_kda(recent_matches))

        return factors

    def _calculate_detection_score(self, factors: List[DetectionFactor]) -> float:
        """Calculate weighted detection score."""
        total_score = 0.0
        total_weight = 0.0

        for factor in factors:
            total_score += factor.score * factor.weight
            total_weight += factor.weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _determine_smurf_status(
        self, detection_score: float, factors: List[DetectionFactor], sample_size: int
    ) -> tuple[bool, str]:
        """Determine if player is a smurf and confidence level."""
        if sample_size < self.thresholds["min_games"]:
            return False, "insufficient_data"

        if detection_score >= self.thresholds["detection_score_high"]:
            return True, "high"
        elif detection_score >= self.thresholds["detection_score_medium"]:
            return True, "medium"
        elif detection_score >= self.thresholds["detection_score_low"]:
            return True, "low"
        else:
            return False, "none"

    @staticmethod
    def _get_confidence_level(score: float) -> str:
        """Determine confidence level based on score."""
        if score >= 0.8:
            return "very high confidence"
        elif score >= 0.6:
            return "high confidence"
        elif score >= 0.4:
            return "moderate confidence"
        else:
            return "low confidence"

    def _generate_reason(self, factors: List[DetectionFactor], score: float) -> str:
        """Generate human-readable reason for detection."""
        triggered_factors = [f for f in factors if f.meets_threshold]

        if not triggered_factors:
            return "No smurf indicators detected"

        reasons: List[str] = []
        for factor in triggered_factors[:3]:  # Top 3 factors
            reasons.append(factor.description.split(":")[0])

        confidence = self._get_confidence_level(score)
        return f"Smurf indicators detected: {', '.join(reasons)} ({confidence}, score: {score:.2f})"

    async def _get_player(self, puuid: str) -> Optional[Player]:
        """Get player from database."""
        result = await self.db.execute(
            select(Player).where(Player.puuid == puuid).limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_recent_matches(
        self,
        puuid: str,
        queue_filter: Optional[int],
        min_games: int,
        time_period_days: Optional[int],
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """Get recent matches for analysis from database.

        :returns: Tuple of (match_data_list, match_ids_list)
        :rtype: tuple[List[Dict[str, Any]], List[str]]
        """
        from app.features.matches.models import Match
        from app.features.matches.participants import MatchParticipant

        # Build query for recent matches
        # Use analysis config for minimum matches calculation
        min_matches_for_analysis = self.analysis_config.get(
            "min_matches_for_analysis", 10
        )
        effective_min_games = max(min_games, min_matches_for_analysis)

        query = (
            select(Match, MatchParticipant)
            .join(MatchParticipant, Match.match_id == MatchParticipant.match_id)
            .where(MatchParticipant.puuid == puuid)
            .order_by(desc(Match.game_creation))
            .limit(effective_min_games * 2)
        )  # Get more to filter

        if queue_filter:
            query = query.where(Match.queue_id == queue_filter)

        if time_period_days:
            cutoff_time = int(
                (
                    datetime.now(timezone.utc) - timedelta(days=time_period_days)
                ).timestamp()
                * 1000
            )
            query = query.where(Match.game_creation >= cutoff_time)

        result = await self.db.execute(query)
        matches_data: List[Dict[str, Any]] = []
        match_ids: List[str] = []

        for match, participant in result:
            match_dict = {
                "match_id": match.match_id,
                "game_creation": match.game_creation,
                "queue_id": match.queue_id,
                "win": participant.win,
                "kills": participant.kills,
                "deaths": participant.deaths,
                "assists": participant.assists,
                "cs": participant.cs,
                "vision_score": participant.vision_score,
                "champion_id": participant.champion_id,
                "role": participant.role,
                "team_id": participant.team_id,
            }
            matches_data.append(match_dict)
            match_ids.append(match.match_id)

        # Return only the requested number of matches
        limit = min(len(matches_data), effective_min_games)
        return matches_data[:limit], match_ids[:limit]

    def _analyze_kda(self, recent_matches: List[Dict[str, Any]]) -> DetectionFactor:
        """Analyze KDA factor."""
        if not recent_matches:
            return DetectionFactor(
                name="kda",
                value=0.0,
                meets_threshold=False,
                weight=self.weights["kda"],
                description="No match data available",
                score=0.0,
            )

        total_kills = sum(m.get("kills", 0) for m in recent_matches)
        total_deaths = sum(m.get("deaths", 0) for m in recent_matches)
        total_assists = sum(m.get("assists", 0) for m in recent_matches)

        avg_kda = self._calculate_kda(total_kills, total_deaths, total_assists)
        meets_threshold = avg_kda >= self.thresholds["high_kda"]
        kda_score = (
            min(1.0, avg_kda / self.thresholds["high_kda"]) if meets_threshold else 0.0
        )

        return DetectionFactor(
            name="kda",
            value=avg_kda,
            meets_threshold=meets_threshold,
            weight=self.weights["kda"],
            description=f"Average KDA: {avg_kda:.2f}",
            score=kda_score,
        )

    def _calculate_kda(self, kills: int, deaths: int, assists: int) -> float:
        """Calculate KDA ratio."""
        if deaths == 0:
            return kills + assists
        return (kills + assists) / deaths

    async def _store_detection_result(
        self,
        puuid: str,
        is_smurf: bool,
        detection_score: float,
        confidence_level: str,
        factors: List[DetectionFactor],
        sample_size: int,
        queue_type: Optional[int] = None,
        time_period_days: Optional[int] = None,
        player: Optional[Player] = None,
    ) -> SmurfDetection:
        """Store detection result in database."""
        # Get factor SCORES for storage (normalized 0-1 values)
        scores = {f.name: f.score for f in factors}

        # Get actual account level from player data (not the score!)
        actual_account_level = player.account_level if player else 0

        # Get current rank information
        current_rank = await self._get_current_rank(puuid)

        detection = SmurfDetection(
            puuid=puuid,
            is_smurf=is_smurf,
            confidence=confidence_level,
            smurf_score=detection_score,
            games_analyzed=sample_size,
            queue_type=str(queue_type) if queue_type else None,
            time_period_days=time_period_days,
            win_rate_threshold=self.thresholds["high_win_rate"],
            kda_threshold=self.thresholds["high_kda"],
            win_rate_score=scores.get("win_rate", 0.0),
            kda_score=scores.get("kda", 0.0),
            account_level_score=scores.get("account_level", 0.0),
            rank_discrepancy_score=scores.get("rank_discrepancy", 0.0),
            rank_progression_score=scores.get("rank_progression", 0.0),
            win_rate_trend_score=scores.get("win_rate_trend", 0.0),
            performance_consistency_score=scores.get("performance_consistency", 0.0),
            performance_trends_score=scores.get("performance_trends", 0.0),
            role_performance_score=scores.get("role_performance", 0.0),
            account_level=actual_account_level,
            current_tier=current_rank.tier if current_rank else None,
            current_rank=current_rank.rank if current_rank else None,
            analysis_version="1.0",
        )

        self.db.add(detection)
        await self.db.commit()
        await self.db.refresh(detection)

        return detection

    async def _mark_matches_processed(self, match_ids: List[str]) -> None:
        """Mark matches as processed after analysis.

        :param match_ids: List of match IDs to mark as processed.
        :type match_ids: List[str]
        """
        if not match_ids:
            return

        from sqlalchemy import update
        from app.features.matches.models import Match

        try:
            # Update all matches in one query
            stmt = (
                update(Match)
                .where(Match.match_id.in_(match_ids))
                .values(is_processed=True)
            )
            await self.db.execute(stmt)
            await self.db.commit()

            logger.debug(
                "Marked matches as processed",
                match_count=len(match_ids),
                match_ids=match_ids[:5],  # Log first 5 for debugging
            )
        except Exception as e:
            logger.error(
                "Failed to mark matches as processed",
                error=str(e),
                match_ids=match_ids,
            )
            # Don't raise - this is not critical for the analysis result
            await self.db.rollback()

    async def _get_current_rank(self, puuid: str) -> Optional[PlayerRank]:
        """Get player's current rank."""
        result = await self.db.execute(
            select(PlayerRank)
            .where(and_(PlayerRank.puuid == puuid, PlayerRank.is_current))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_recent_detection(
        self, puuid: str, hours: int = 24
    ) -> Optional[SmurfDetection]:
        """Get recent detection analysis if it exists."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = await self.db.execute(
            select(SmurfDetection)
            .where(
                and_(
                    SmurfDetection.puuid == puuid,
                    SmurfDetection.last_analysis >= cutoff_time,
                )
            )
            .order_by(desc(SmurfDetection.last_analysis))
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _create_insufficient_data_response(
        self, puuid: str, available: int, required: int
    ) -> DetectionResponse:
        """Create response when insufficient data is available."""
        return DetectionResponse(
            puuid=puuid,
            is_smurf=False,
            detection_score=0.0,
            confidence_level="insufficient_data",
            factors=[],
            reason=f"Insufficient data: only {available} matches found (need {required})",
            sample_size=available,
            analysis_time_seconds=0.0,
            created_at=None,
        )

    def _create_factor_from_detection(
        self,
        detection: SmurfDetection,
        factor_name: str,
        score_attr: str,
        threshold_check: Callable[..., Any],
        description_format: str,
        value_attr: str | None = None,
        score_transform: Callable[..., Any] | None = None,
    ) -> DetectionFactor | None:
        """
        Create a DetectionFactor from detection data using configuration.

        Args:
            detection: SmurfDetection instance
            factor_name: Name of the factor
            score_attr: Attribute name for the score value
            threshold_check: Function that takes score and returns bool
            description_format: Format string for description (use {value})
            value_attr: Optional different attribute for value field
            score_transform: Optional function to transform score

        Returns:
            DetectionFactor or None if score is None
        """
        score_value = getattr(detection, score_attr, None)
        if score_value is None:
            return None

        value = (
            getattr(detection, value_attr, score_value) if value_attr else score_value
        )
        final_score = (
            score_transform(score_value) if score_transform else float(score_value)
        )

        return DetectionFactor(
            name=factor_name,
            value=float(value),
            meets_threshold=threshold_check(score_value),
            weight=self.weights[factor_name],
            description=description_format.format(value=score_value),
            score=final_score,
        )

    def _convert_to_response(self, detection: SmurfDetection) -> DetectionResponse:
        """Convert database detection to response."""
        # Create factors from stored data using configuration-driven approach
        factor_configs = [
            # (factor_name, score_attr, threshold_check, description_format, value_attr, score_transform)
            (
                "win_rate",
                "win_rate_score",
                lambda s: s >= self.thresholds["high_win_rate"],
                "Win rate: {value:.1%}",
                None,
                None,
            ),
            (
                "win_rate_trend",
                "win_rate_trend_score",
                lambda s: s > 0.5,
                "Win rate trend (score: {value:.2f})",
                None,
                None,
            ),
            (
                "account_level",
                "account_level_score",
                lambda s: getattr(detection, "account_level", 0)
                <= self.thresholds["low_account_level"],
                "Account level: {value}",
                "account_level",
                None,
            ),
            (
                "rank_progression",
                "rank_progression_score",
                lambda s: s > 0.5,
                "Rank progression (score: {value:.2f})",
                None,
                None,
            ),
            (
                "rank_discrepancy",
                "rank_discrepancy_score",
                lambda s: s > 0.6,
                "Rank vs performance (score: {value:.2f})",
                None,
                None,
            ),
            (
                "performance_consistency",
                "performance_consistency_score",
                lambda s: s > 0.5,
                "Performance consistency (score: {value:.2f})",
                None,
                None,
            ),
            (
                "performance_trends",
                "performance_trends_score",
                lambda s: s > 0.6,
                "Performance trends (score: {value:.2f})",
                None,
                None,
            ),
            (
                "role_performance",
                "role_performance_score",
                lambda s: s > 0.5,
                "Role versatility (score: {value:.2f})",
                None,
                None,
            ),
            (
                "kda",
                "kda_score",
                lambda s: s >= self.thresholds["high_kda"],
                "KDA: {value:.2f}",
                None,
                lambda s: min(1.0, float(s) / self.thresholds["high_kda"]),
            ),
        ]

        factors = []
        for config in factor_configs:
            factor = self._create_factor_from_detection(detection, *config)
            if factor:
                factors.append(factor)

        return DetectionResponse(
            puuid=str(detection.puuid),
            is_smurf=detection.is_smurf,
            detection_score=float(detection.smurf_score),
            confidence_level=detection.confidence or "none",
            factors=factors,
            reason=f"Stored analysis result (score: {float(detection.smurf_score):.2f})",
            sample_size=detection.games_analyzed,
            created_at=detection.created_at,
            analysis_time_seconds=0.0,
        )
