"""
Smurf detection service for multi-factor smurf detection analysis.

This service provides comprehensive smurf detection by analyzing multiple
factors including win rate, account level, rank progression, and performance
consistency.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import structlog

from ..riot_api.data_manager import RiotDataManager
from ..models.players import Player
from ..models.smurf_detection import SmurfDetection
from ..models.ranks import PlayerRank
from ..schemas.detection import (
    DetectionResponse,
    DetectionRequest,
    DetectionStatsResponse,
    DetectionConfigResponse,
    DetectionFactor,
    BulkDetectionResponse,
)
from ..algorithms.win_rate import WinRateAnalyzer
from ..algorithms.rank_progression import RankProgressionAnalyzer
from ..algorithms.performance import PerformanceAnalyzer

logger = structlog.get_logger(__name__)


class SmurfDetectionService:
    """Service for comprehensive smurf detection analysis."""

    def __init__(self, db: AsyncSession, data_manager: RiotDataManager):
        self.db = db
        self.data_manager = data_manager

        # Initialize analyzers
        self.win_rate_analyzer = WinRateAnalyzer()
        self.rank_analyzer = RankProgressionAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()

        # Detection thresholds
        self.thresholds = {
            "high_win_rate": 0.65,  # 65% win rate
            "min_games": 30,  # Minimum games to consider
            "low_account_level": 50,  # Low account level threshold
            "high_kda": 3.5,  # High KDA threshold
            "rank_tier_jump": 2,  # Minimum tier progression to flag
            "performance_variance": 0.3,  # Performance consistency threshold
            "detection_score_high": 0.8,  # High confidence threshold
            "detection_score_medium": 0.6,  # Medium confidence threshold
            "detection_score_low": 0.4,  # Low confidence threshold
        }

        # Factor weights
        self.weights = {
            "win_rate": 0.35,
            "account_level": 0.15,
            "rank_progression": 0.25,
            "performance_consistency": 0.20,
            "kda": 0.05,
        }

    async def analyze_player(
        self,
        puuid: str,
        min_games: int = 30,
        queue_filter: Optional[int] = None,
        time_period_days: Optional[int] = None,
        force_reanalyze: bool = False,
    ) -> DetectionResponse:
        """
        Comprehensive smurf detection analysis for a player.

        Args:
            puuid: Player PUUID to analyze
            min_games: Minimum games required for analysis
            queue_filter: Optional queue filter
            time_period_days: Optional time period filter
            force_reanalyze: Force re-analysis even if recent analysis exists

        Returns:
            DetectionResponse with analysis results
        """
        start_time = datetime.now()

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
        recent_matches = await self._get_recent_matches(
            puuid, queue_filter, min_games, time_period_days
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
        )

        # Calculate analysis time
        analysis_time = (datetime.now() - start_time).total_seconds()

        logger.info(
            "Smurf detection analysis completed",
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
        """Analyze all detection factors."""
        factors = []

        # Win rate analysis
        try:
            win_rate_result = await self.win_rate_analyzer.analyze(recent_matches)
            win_rate_score = self.win_rate_analyzer.calculate_win_rate_score(
                win_rate_result.win_rate, win_rate_result.total_games
            )
            factors.append(
                DetectionFactor(
                    name="win_rate",
                    value=win_rate_result.win_rate,
                    meets_threshold=win_rate_result.meets_threshold,
                    weight=self.weights["win_rate"],
                    description=win_rate_result.description,
                    score=win_rate_score,
                )
            )
        except Exception as e:
            logger.error("Win rate analysis failed", puuid=puuid, error=str(e))
            factors.append(
                DetectionFactor(
                    name="win_rate",
                    value=0.0,
                    meets_threshold=False,
                    weight=self.weights["win_rate"],
                    description="Win rate analysis failed",
                    score=0.0,
                )
            )

        # Account level analysis
        account_level_factor = DetectionFactor(
            name="account_level",
            value=float(player.account_level or 0),
            meets_threshold=(player.account_level or 0)
            <= self.thresholds["low_account_level"],
            weight=self.weights["account_level"],
            description=f"Account level: {player.account_level or 'Unknown'}",
            score=0.15
            if (player.account_level or 0) <= self.thresholds["low_account_level"]
            else 0.0,
        )
        factors.append(account_level_factor)

        # Rank progression analysis
        try:
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
        except Exception as e:
            logger.error("Rank progression analysis failed", puuid=puuid, error=str(e))
            factors.append(
                DetectionFactor(
                    name="rank_progression",
                    value=0.0,
                    meets_threshold=False,
                    weight=self.weights["rank_progression"],
                    description="Rank progression analysis failed",
                    score=0.0,
                )
            )

        # Performance consistency analysis
        try:
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
        except Exception as e:
            logger.error("Performance analysis failed", puuid=puuid, error=str(e))
            factors.append(
                DetectionFactor(
                    name="performance_consistency",
                    value=0.0,
                    meets_threshold=False,
                    weight=self.weights["performance_consistency"],
                    description="Performance analysis failed",
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

        reasons = []
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
        result = await self.db.execute(select(Player).where(Player.puuid == puuid))
        return result.scalar_one_or_none()

    async def _get_recent_matches(
        self,
        puuid: str,
        queue_filter: Optional[int],
        min_games: int,
        time_period_days: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Get recent matches for analysis from database."""
        from ..models.matches import Match
        from ..models.participants import MatchParticipant

        # Build query for recent matches
        query = (
            select(Match, MatchParticipant)
            .join(MatchParticipant, Match.match_id == MatchParticipant.match_id)
            .where(MatchParticipant.puuid == puuid)
            .order_by(desc(Match.game_creation))
            .limit(min_games * 2)
        )  # Get more to filter

        if queue_filter:
            query = query.where(Match.queue_id == queue_filter)

        if time_period_days:
            cutoff_time = int(
                (datetime.now() - timedelta(days=time_period_days)).timestamp() * 1000
            )
            query = query.where(Match.game_creation >= cutoff_time)

        result = await self.db.execute(query)
        matches_data = []

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

        return matches_data[:min_games]

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
    ) -> SmurfDetection:
        """Store detection result in database."""
        # Get factor values for storage
        win_rate_value = next((f.value for f in factors if f.name == "win_rate"), 0.0)
        kda_value = next((f.value for f in factors if f.name == "kda"), 0.0)
        account_level_value = next(
            (f.value for f in factors if f.name == "account_level"), 0.0
        )
        rank_progression_value = next(
            (f.value for f in factors if f.name == "rank_progression"), 0.0
        )

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
            win_rate_score=win_rate_value,
            kda_score=kda_value,
            account_level_score=account_level_value,
            rank_discrepancy_score=rank_progression_value,
            account_level=int(account_level_value),
            current_tier=current_rank.tier if current_rank else None,
            current_rank=current_rank.rank if current_rank else None,
            analysis_version="1.0",
        )

        self.db.add(detection)
        await self.db.commit()
        await self.db.refresh(detection)

        return detection

    async def _get_current_rank(self, puuid: str) -> Optional[PlayerRank]:
        """Get player's current rank."""
        result = await self.db.execute(
            select(PlayerRank).where(
                and_(PlayerRank.puuid == puuid, PlayerRank.is_current)
            )
        )
        return result.scalar_one_or_none()

    async def _get_recent_detection(
        self, puuid: str, hours: int = 24
    ) -> Optional[SmurfDetection]:
        """Get recent detection analysis if it exists."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        result = await self.db.execute(
            select(SmurfDetection)
            .where(
                and_(
                    SmurfDetection.puuid == puuid,
                    SmurfDetection.last_analysis >= cutoff_time,
                )
            )
            .order_by(desc(SmurfDetection.last_analysis))
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
        )

    def _convert_to_response(self, detection: SmurfDetection) -> DetectionResponse:
        """Convert database detection to response."""
        # Create factors from stored data
        factors = [
            DetectionFactor(
                name="win_rate",
                value=float(detection.win_rate_score or 0.0),
                meets_threshold=(detection.win_rate_score or 0.0)
                >= self.thresholds["high_win_rate"],
                weight=self.weights["win_rate"],
                description=f"Win rate: {detection.win_rate_score or 0.0:.1%}",
                score=min(
                    1.0,
                    float(detection.win_rate_score or 0.0)
                    / self.thresholds["high_win_rate"],
                ),
            ),
            DetectionFactor(
                name="kda",
                value=float(detection.kda_score or 0.0),
                meets_threshold=(detection.kda_score or 0.0)
                >= self.thresholds["high_kda"],
                weight=self.weights["kda"],
                description=f"KDA: {detection.kda_score or 0.0:.2f}",
                score=min(
                    1.0, float(detection.kda_score or 0.0) / self.thresholds["high_kda"]
                ),
            ),
            DetectionFactor(
                name="account_level",
                value=float(detection.account_level or 0),
                meets_threshold=(detection.account_level or 0)
                <= self.thresholds["low_account_level"],
                weight=self.weights["account_level"],
                description=f"Account level: {detection.account_level}",
                score=0.15
                if (detection.account_level or 0)
                <= self.thresholds["low_account_level"]
                else 0.0,
            ),
        ]

        return DetectionResponse(
            puuid=str(detection.puuid),
            is_smurf=detection.is_smurf,
            detection_score=float(detection.smurf_score),
            confidence_level=detection.confidence or "none",
            factors=factors,
            reason=f"Stored analysis result (score: {float(detection.smurf_score):.2f})",
            sample_size=detection.games_analyzed,
            created_at=detection.created_at,
        )

    async def get_detection_history(
        self, puuid: str, limit: int = 10, include_factors: bool = True
    ) -> List[DetectionResponse]:
        """Get historical smurf detection results for a player."""
        result = await self.db.execute(
            select(SmurfDetection)
            .where(SmurfDetection.puuid == puuid)
            .order_by(desc(SmurfDetection.last_analysis))
            .limit(limit)
        )

        detections = result.scalars().all()
        return [self._convert_to_response(detection) for detection in detections]

    async def get_detection_stats(self) -> DetectionStatsResponse:
        """Get overall smurf detection statistics."""
        # Get total analyses
        total_result = await self.db.execute(select(func.count(SmurfDetection.id)))
        total_analyses = total_result.scalar() or 0

        # Get smurf count
        smurf_result = await self.db.execute(
            select(func.count(SmurfDetection.id)).where(SmurfDetection.is_smurf)
        )
        smurf_count = smurf_result.scalar() or 0

        # Get average score
        avg_result = await self.db.execute(select(func.avg(SmurfDetection.smurf_score)))
        average_score = float(avg_result.scalar() or 0.0)

        # Get confidence distribution
        confidence_result = await self.db.execute(
            select(SmurfDetection.confidence, func.count(SmurfDetection.id)).group_by(
                SmurfDetection.confidence
            )
        )
        confidence_distribution = {
            str(row[0] or "none"): row[1] for row in confidence_result
        }

        # Get last analysis time
        last_result = await self.db.execute(
            select(func.max(SmurfDetection.last_analysis))
        )
        last_analysis = last_result.scalar()

        # Calculate factor trigger rates (simplified)
        factor_trigger_rates = {
            "win_rate": 0.15,
            "kda": 0.10,
            "account_level": 0.25,
            "rank_progression": 0.20,
            "performance_consistency": 0.15,
        }

        # Get queue type distribution
        queue_result = await self.db.execute(
            select(SmurfDetection.queue_type, func.count(SmurfDetection.id)).group_by(
                SmurfDetection.queue_type
            )
        )
        queue_type_distribution = {
            str(row[0] or "unknown"): row[1] for row in queue_result
        }

        return DetectionStatsResponse(
            total_analyses=total_analyses,
            smurf_count=smurf_count,
            smurf_detection_rate=smurf_count / total_analyses
            if total_analyses > 0
            else 0.0,
            average_score=average_score,
            confidence_distribution=confidence_distribution,
            factor_trigger_rates=factor_trigger_rates,
            queue_type_distribution=queue_type_distribution,
            last_analysis=last_analysis,
        )

    async def get_config(self) -> DetectionConfigResponse:
        """Get current detection configuration."""
        return DetectionConfigResponse(
            thresholds=self.thresholds,
            weights=self.weights,
            min_games_required=self.thresholds["min_games"],
            analysis_version="1.0",
            last_updated=datetime.now(),
        )

    async def analyze_bulk_players(
        self, puuids: List[str], analysis_config: DetectionRequest
    ) -> BulkDetectionResponse:
        """Perform bulk smurf detection analysis."""
        start_time = datetime.now()
        results = []
        successful = 0
        failed = 0

        for puuid in puuids:
            try:
                result = await self.analyze_player(
                    puuid=puuid,
                    min_games=analysis_config.min_games,
                    queue_filter=analysis_config.queue_filter,
                    time_period_days=analysis_config.time_period_days,
                    force_reanalyze=analysis_config.force_reanalyze,
                )
                results.append(result)
                successful += 1
            except Exception as e:
                logger.error(
                    "Bulk analysis failed for player", puuid=puuid, error=str(e)
                )
                failed += 1
                # Create failure response
                results.append(
                    DetectionResponse(
                        puuid=puuid,
                        is_smurf=False,
                        detection_score=0.0,
                        confidence_level="error",
                        factors=[],
                        reason=f"Analysis failed: {str(e)}",
                        sample_size=0,
                        analysis_time_seconds=0.0,
                    )
                )

        processing_time = (datetime.now() - start_time).total_seconds()

        # Create summary
        smurf_count = sum(1 for r in results if r.is_smurf)
        avg_score = (
            sum(r.detection_score for r in results) / len(results) if results else 0.0
        )

        summary = {
            "total_players": len(puuids),
            "successful_analyses": successful,
            "failed_analyses": failed,
            "smurfs_detected": smurf_count,
            "smurf_detection_rate": smurf_count / len(results) if results else 0.0,
            "average_detection_score": avg_score,
        }

        return BulkDetectionResponse(
            results=results,
            summary=summary,
            processing_time_seconds=processing_time,
            successful_analyses=successful,
            failed_analyses=failed,
        )
