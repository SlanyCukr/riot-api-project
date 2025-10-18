"""
Player analysis service for multi-factor player analysis.

This service provides comprehensive player analysis by analyzing multiple
factors including win rate, account level, rank progression, and performance
consistency using modular factor analyzers.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
import structlog

from ..riot_api.data_manager import RiotDataManager
from ..models.players import Player
from ..models.smurf_detection import SmurfDetection
from ..models.ranks import PlayerRank
from ..schemas.detection import (
    DetectionResponse,
    DetectionFactor,
)
from .decorators import service_error_handler, input_validation
from .utils import validate_puuid
from .detection_config import get_detection_config
from .analyzers import (
    WinRateFactorAnalyzer,
    AccountLevelFactorAnalyzer,
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
            "account_level": AccountLevelFactorAnalyzer(),
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
        custom_validators={"puuid": validate_puuid},
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

        # Account level analysis
        account_level_factor = DetectionFactor(
            name="account_level",
            value=float(player.account_level or 0),
            meets_threshold=(player.account_level or 0)
            <= self.thresholds["low_account_level"],
            weight=self.weights["account_level"],
            description=f"Account level: {player.account_level or 'Unknown'}",
            score=(
                0.15
                if (player.account_level or 0) <= self.thresholds["low_account_level"]
                else 0.0
            ),
        )
        factors.append(account_level_factor)

        # Rank progression analysis
        rank_result = await self.rank_analyzer.analyze(puuid, self.db)
        rank_score = (
            min(1.0, rank_result.progression_speed / 100)
            if rank_result.progression_speed > 0
            else 0.0
        )
        factors.append(
            DetectionFactor(
                name="rank_progression",
                value=rank_result.progression_speed,
                meets_threshold=rank_result.meets_threshold,
                weight=self.weights["rank_progression"],
                description=rank_result.description,
                score=rank_score,
            )
        )

        # Performance consistency analysis
        performance_result = await self.performance_analyzer.analyze(recent_matches)
        performance_score = (
            performance_result.consistency_score
            if performance_result.meets_threshold
            else 0.0
        )
        factors.append(
            DetectionFactor(
                name="performance_consistency",
                value=performance_result.consistency_score,
                meets_threshold=performance_result.meets_threshold,
                weight=self.weights["performance_consistency"],
                description=performance_result.description,
                score=performance_score,
            )
        )

        # Win rate trend analysis
        if len(recent_matches) >= 10:
            win_rate_trend_result = self.win_rate_analyzer.analyze_win_rate_trend(
                recent_matches
            )
            trend_score = win_rate_trend_result.get("score", 0.0)
            trend_type = win_rate_trend_result.get("trend", "stable")
            improvement = win_rate_trend_result.get("improvement", 0.0)

            factors.append(
                DetectionFactor(
                    name="win_rate_trend",
                    value=improvement,
                    meets_threshold=trend_score > 0.5,
                    weight=self.weights["win_rate_trend"],
                    description=f"Win rate trend: {trend_type} ({improvement:+.1%} change)",
                    score=trend_score,
                )
            )
        else:
            factors.append(
                DetectionFactor(
                    name="win_rate_trend",
                    value=0.0,
                    meets_threshold=False,
                    weight=self.weights["win_rate_trend"],
                    description="Win rate trend: insufficient data",
                    score=0.0,
                )
            )

        # Performance trends analysis
        if len(recent_matches) >= 10:
            performance_trend_result = (
                self.performance_analyzer.analyze_performance_trends(recent_matches)
            )
            trend_score = performance_trend_result.get("trend_score", 0.0)
            is_stable = performance_trend_result.get("is_suspiciously_stable", False)
            overall_perf = performance_trend_result.get("overall_performance", 0.0)

            # High score if either trending upward OR suspiciously stable high performance
            final_score = max(trend_score, 0.8 if is_stable else 0.0)

            factors.append(
                DetectionFactor(
                    name="performance_trends",
                    value=overall_perf,
                    meets_threshold=final_score > 0.6,
                    weight=self.weights["performance_trends"],
                    description=f"Performance trend: {performance_trend_result.get('trend', 'stable')} (score: {overall_perf:.2f})",
                    score=final_score,
                )
            )
        else:
            factors.append(
                DetectionFactor(
                    name="performance_trends",
                    value=0.0,
                    meets_threshold=False,
                    weight=self.weights["performance_trends"],
                    description="Performance trends: insufficient data",
                    score=0.0,
                )
            )

        # Role performance analysis
        role_perf_result = self.performance_analyzer.analyze_role_performance(
            recent_matches
        )
        versatility_score = role_perf_result.get("role_versatility_score", 0)
        high_perf_roles = role_perf_result.get("consistent_high_performance", 0)

        # Smurfs often excel at multiple roles
        role_score = min(1.0, high_perf_roles / 3.0) if versatility_score >= 3 else 0.0

        factors.append(
            DetectionFactor(
                name="role_performance",
                value=float(high_perf_roles),
                meets_threshold=high_perf_roles >= 2,
                weight=self.weights["role_performance"],
                description=f"Role versatility: {high_perf_roles} roles with high performance",
                score=role_score,
            )
        )

        # Rank discrepancy analysis (rank vs performance mismatch)
        current_rank = await self._get_current_rank(puuid)

        if current_rank:
            # Calculate performance metrics from recent matches
            total_kills = sum(m.get("kills", 0) for m in recent_matches)
            total_deaths = sum(m.get("deaths", 0) for m in recent_matches)
            total_assists = sum(m.get("assists", 0) for m in recent_matches)
            wins = sum(1 for m in recent_matches if m.get("win", False))

            avg_kda = self._calculate_kda(total_kills, total_deaths, total_assists)
            win_rate = wins / len(recent_matches) if recent_matches else 0.0

            performance_metrics = {
                "kda": avg_kda,
                "win_rate": win_rate,
            }

            rank_discrepancy_result = self.rank_analyzer.analyze_rank_discrepancy(
                current_rank, performance_metrics
            )

            discrepancy_score = rank_discrepancy_result.get("discrepancy_score", 0.0)
            is_suspicious = rank_discrepancy_result.get("is_suspicious", False)

            # Handle UNRANKED separately with clearer messaging
            if current_rank.tier == "UNRANKED":
                description = f"Player is unranked (KDA: {avg_kda:.2f}, WR: {win_rate:.1%}) - no tier comparison"
            else:
                description = f"Rank vs performance: {current_rank.tier} {current_rank.rank} (KDA: {avg_kda:.2f}, WR: {win_rate:.1%})"

            factors.append(
                DetectionFactor(
                    name="rank_discrepancy",
                    value=discrepancy_score,
                    meets_threshold=is_suspicious,
                    weight=self.weights["rank_discrepancy"],
                    description=description,
                    score=min(1.0, discrepancy_score * 3),  # Scale to 0-1
                )
            )
        else:
            factors.append(
                DetectionFactor(
                    name="rank_discrepancy",
                    value=0.0,
                    meets_threshold=False,
                    weight=self.weights["rank_discrepancy"],
                    description="Rank discrepancy: no rank data available",
                    score=0.0,
                )
            )

        # KDA analysis
        kda_factor = self._analyze_kda(recent_matches)
        factors.append(kda_factor)

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

    def _generate_reason(self, factors: List[DetectionFactor], score: float) -> str:
        """Generate human-readable reason for detection."""
        triggered_factors = [f for f in factors if f.meets_threshold]

        if not triggered_factors:
            return "No smurf indicators detected"

        reasons: List[str] = []
        for factor in triggered_factors[:3]:  # Top 3 factors
            reasons.append(factor.description.split(":")[0])

        if score >= 0.8:
            confidence = "very high confidence"
        elif score >= 0.6:
            confidence = "high confidence"
        elif score >= 0.4:
            confidence = "moderate confidence"
        else:
            confidence = "low confidence"

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
        from ..models.matches import Match
        from ..models.participants import MatchParticipant

        # Build query for recent matches
        # Use analysis config for minimum matches calculation
        min_matches_for_analysis = self.analysis_config.get("min_matches_for_analysis", 10)
        effective_min_games = max(min_games, min_games_for_analysis)

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
        win_rate_score = next((f.score for f in factors if f.name == "win_rate"), 0.0)
        kda_score = next((f.score for f in factors if f.name == "kda"), 0.0)
        account_level_score = next(
            (f.score for f in factors if f.name == "account_level"), 0.0
        )
        rank_progression_score = next(
            (f.score for f in factors if f.name == "rank_progression"), 0.0
        )
        rank_discrepancy_score = next(
            (f.score for f in factors if f.name == "rank_discrepancy"), 0.0
        )
        win_rate_trend_score = next(
            (f.score for f in factors if f.name == "win_rate_trend"), 0.0
        )
        performance_consistency_score = next(
            (f.score for f in factors if f.name == "performance_consistency"), 0.0
        )
        performance_trends_score = next(
            (f.score for f in factors if f.name == "performance_trends"), 0.0
        )
        role_performance_score = next(
            (f.score for f in factors if f.name == "role_performance"), 0.0
        )

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
            win_rate_score=win_rate_score,
            kda_score=kda_score,
            account_level_score=account_level_score,
            rank_discrepancy_score=rank_discrepancy_score,
            rank_progression_score=rank_progression_score,
            win_rate_trend_score=win_rate_trend_score,
            performance_consistency_score=performance_consistency_score,
            performance_trends_score=performance_trends_score,
            role_performance_score=role_performance_score,
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
        from ..models.matches import Match

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

    def _convert_to_response(self, detection: SmurfDetection) -> DetectionResponse:
        """Convert database detection to response."""
        # Create factors from stored data
        factors = []

        # 1. Win rate
        if detection.win_rate_score is not None:
            factors.append(
                DetectionFactor(
                    name="win_rate",
                    value=float(detection.win_rate_score),
                    meets_threshold=detection.win_rate_score
                    >= self.thresholds["high_win_rate"],
                    weight=self.weights["win_rate"],
                    description=f"Win rate: {detection.win_rate_score:.1%}",
                    score=float(detection.win_rate_score),
                )
            )

        # 2. Win rate trend
        if detection.win_rate_trend_score is not None:
            factors.append(
                DetectionFactor(
                    name="win_rate_trend",
                    value=float(detection.win_rate_trend_score),
                    meets_threshold=detection.win_rate_trend_score > 0.5,
                    weight=self.weights["win_rate_trend"],
                    description=f"Win rate trend (score: {detection.win_rate_trend_score:.2f})",
                    score=float(detection.win_rate_trend_score),
                )
            )

        # 3. Account level
        if detection.account_level is not None:
            factors.append(
                DetectionFactor(
                    name="account_level",
                    value=float(detection.account_level),
                    meets_threshold=detection.account_level
                    <= self.thresholds["low_account_level"],
                    weight=self.weights["account_level"],
                    description=f"Account level: {detection.account_level}",
                    score=float(detection.account_level_score or 0.0),
                )
            )

        # 4. Rank progression
        if detection.rank_progression_score is not None:
            factors.append(
                DetectionFactor(
                    name="rank_progression",
                    value=float(detection.rank_progression_score),
                    meets_threshold=detection.rank_progression_score > 0.5,
                    weight=self.weights["rank_progression"],
                    description=f"Rank progression (score: {detection.rank_progression_score:.2f})",
                    score=float(detection.rank_progression_score),
                )
            )

        # 5. Rank discrepancy
        if detection.rank_discrepancy_score is not None:
            factors.append(
                DetectionFactor(
                    name="rank_discrepancy",
                    value=float(detection.rank_discrepancy_score),
                    meets_threshold=detection.rank_discrepancy_score > 0.6,
                    weight=self.weights["rank_discrepancy"],
                    description=f"Rank vs performance (score: {detection.rank_discrepancy_score:.2f})",
                    score=float(detection.rank_discrepancy_score),
                )
            )

        # 6. Performance consistency
        if detection.performance_consistency_score is not None:
            factors.append(
                DetectionFactor(
                    name="performance_consistency",
                    value=float(detection.performance_consistency_score),
                    meets_threshold=detection.performance_consistency_score > 0.5,
                    weight=self.weights["performance_consistency"],
                    description=f"Performance consistency (score: {detection.performance_consistency_score:.2f})",
                    score=float(detection.performance_consistency_score),
                )
            )

        # 7. Performance trends
        if detection.performance_trends_score is not None:
            factors.append(
                DetectionFactor(
                    name="performance_trends",
                    value=float(detection.performance_trends_score),
                    meets_threshold=detection.performance_trends_score > 0.6,
                    weight=self.weights["performance_trends"],
                    description=f"Performance trends (score: {detection.performance_trends_score:.2f})",
                    score=float(detection.performance_trends_score),
                )
            )

        # 8. Role performance
        if detection.role_performance_score is not None:
            factors.append(
                DetectionFactor(
                    name="role_performance",
                    value=float(detection.role_performance_score),
                    meets_threshold=detection.role_performance_score > 0.5,
                    weight=self.weights["role_performance"],
                    description=f"Role versatility (score: {detection.role_performance_score:.2f})",
                    score=float(detection.role_performance_score),
                )
            )

        # 9. KDA
        if detection.kda_score is not None:
            factors.append(
                DetectionFactor(
                    name="kda",
                    value=float(detection.kda_score),
                    meets_threshold=detection.kda_score >= self.thresholds["high_kda"],
                    weight=self.weights["kda"],
                    description=f"KDA: {detection.kda_score:.2f}",
                    score=min(
                        1.0, float(detection.kda_score) / self.thresholds["high_kda"]
                    ),
                )
            )

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
