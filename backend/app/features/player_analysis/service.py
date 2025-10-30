"""
Player analysis service with enterprise patterns.

This service orchestrates multi-factor player analysis by coordinating:
- Repository layer for data access
- Analyzer modules for factor evaluation
- Transformer layer for response creation

Follows clean architecture with pure orchestration logic in service.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import structlog

from app.core.riot_api.data_manager import RiotDataManager
from app.features.players.orm_models import PlayerORM
from .orm_models import PlayerAnalysisORM as PlayerAnalysis
from .repository import PlayerAnalysisRepositoryInterface
from .schemas import (
    DetectionResponse,
    DetectionFactor,
)
from .transformers import PlayerAnalysisTransformer
from app.core.decorators import service_error_handler, input_validation
from .config import get_detection_config
from .analyzers import (
    WinRateFactorAnalyzer,
    WinRateTrendFactorAnalyzer,
    AccountLevelFactorAnalyzer,
    PerformanceFactorAnalyzer,
    RankProgressionFactorAnalyzer,
    RankDiscrepancyFactorAnalyzer,
    PerformanceTrendsFactorAnalyzer,
    RolePerformanceFactorAnalyzer,
    KDAFactorAnalyzer,
)

logger = structlog.get_logger(__name__)


# Custom exceptions for player analysis
class PlayerAnalysisError(Exception):
    """Base exception for player analysis operations."""

    pass


class PlayerNotFoundError(PlayerAnalysisError):
    """Raised when player is not found."""

    pass


class InsufficientDataError(PlayerAnalysisError):
    """Raised when insufficient match data is available for analysis."""

    pass


class PlayerAnalysisService:
    """Service for comprehensive player analysis using modular factor analyzers.

    Orchestrates the player analysis workflow by:
    1. Checking cache via repository
    2. Fetching data via repository
    3. Running analyzers
    4. Calculating scores
    5. Storing results via repository
    6. Transforming response
    """

    def __init__(
        self,
        repository: PlayerAnalysisRepositoryInterface,
        data_manager: Optional[RiotDataManager] = None,
    ):
        """
        Initialize player analysis service.

        :param repository: Player analysis repository instance
        :type repository: PlayerAnalysisRepositoryInterface
        :param data_manager: Riot API data manager (optional, for legacy compatibility)
        :type data_manager: Optional[RiotDataManager]
        """
        self.repository = repository
        self.data_manager = data_manager

        # Load configuration
        config = get_detection_config()
        self.config = config

        # Initialize transformer
        self.transformer = PlayerAnalysisTransformer()

        # Initialize modular factor analyzers
        self.factor_analyzers = {
            "win_rate": WinRateFactorAnalyzer(),
            "win_rate_trend": WinRateTrendFactorAnalyzer(),
            "account_level": AccountLevelFactorAnalyzer(),
            "performance_consistency": PerformanceFactorAnalyzer(),
            "rank_progression": RankProgressionFactorAnalyzer(),
            "rank_discrepancy": RankDiscrepancyFactorAnalyzer(),
            "performance_trends": PerformanceTrendsFactorAnalyzer(),
            "role_performance": RolePerformanceFactorAnalyzer(),
            "kda": KDAFactorAnalyzer(),
        }

        logger.info(
            "PlayerAnalysisService initialized",
            num_analyzers=len(self.factor_analyzers),
            config_version="1.0",
        )

    @service_error_handler("PlayerAnalysisService")
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
        Perform player analysis - pure orchestration.

        Orchestrates the analysis workflow:
        1. Check cache (if not force_reanalyze)
        2. Fetch data via repository
        3. Validate sufficient data
        4. Run analyzers
        5. Calculate score
        6. Determine status
        7. Persist result
        8. Mark matches processed
        9. Transform response

        :param puuid: Player PUUID to analyze
        :param min_games: Minimum games required
        :param queue_filter: Optional queue type filter
        :param time_period_days: Optional time period filter
        :param force_reanalyze: Force re-analysis even if recent analysis exists
        :returns: DetectionResponse with analysis results
        """
        start_time = datetime.now(timezone.utc)

        # 1. Check cache (return early if recent analysis exists)
        if not force_reanalyze:
            cached = await self.repository.get_recent_analysis(puuid, hours=24)
            if cached:
                logger.info("Using cached analysis", puuid=puuid, analysis_id=cached.id)
                return self.transformer.to_detection_response(
                    cached,
                    self.config["weights"],
                    self.config["thresholds"],
                    analysis_time_seconds=0.0,
                )

        # 2. Fetch data via repository (pure data access)
        player = await self.repository.get_player_with_relations(puuid)
        if not player:
            raise PlayerNotFoundError(f"Player not found: {puuid}")

        matches_data, match_ids = await self.repository.get_matches_for_analysis(
            puuid=puuid,
            min_games=min_games,
            queue_filter=queue_filter,
            time_period_days=time_period_days,
        )

        # 3. Validate sufficient data
        if len(matches_data) < min_games:
            raise InsufficientDataError(
                f"Need {min_games} matches for analysis, got {len(matches_data)}"
            )

        # 4. Run analyzers (delegation to analyzer objects)
        factors = await self._run_analyzers(
            puuid=puuid,
            player=player,
            matches=matches_data,
            rank_history=player.ranks,
        )

        # 5. Calculate weighted score
        total_score = self._calculate_weighted_score(factors)

        # 6. Determine detection status
        is_smurf, confidence = self._determine_detection_status(
            total_score, len(matches_data)
        )

        # 7. Create analysis record (pure data object construction)
        analysis = PlayerAnalysis(
            puuid=puuid,
            is_smurf=is_smurf,
            confidence=confidence,
            smurf_score=total_score,
            games_analyzed=len(matches_data),
            queue_type=str(queue_filter) if queue_filter else None,
            time_period_days=time_period_days,
            win_rate_threshold=self.config["thresholds"]["high_win_rate"],
            kda_threshold=self.config["thresholds"]["high_kda"],
            win_rate_score=next(
                (f.score for f in factors if f.name == "win_rate"), 0.0
            ),
            kda_score=next((f.score for f in factors if f.name == "kda"), 0.0),
            account_level_score=next(
                (f.score for f in factors if f.name == "account_level"), 0.0
            ),
            rank_discrepancy_score=next(
                (f.score for f in factors if f.name == "rank_discrepancy"), 0.0
            ),
            rank_progression_score=next(
                (f.score for f in factors if f.name == "rank_progression"), 0.0
            ),
            win_rate_trend_score=next(
                (f.score for f in factors if f.name == "win_rate_trend"), 0.0
            ),
            performance_consistency_score=next(
                (f.score for f in factors if f.name == "performance_consistency"), 0.0
            ),
            performance_trends_score=next(
                (f.score for f in factors if f.name == "performance_trends"), 0.0
            ),
            role_performance_score=next(
                (f.score for f in factors if f.name == "role_performance"), 0.0
            ),
            account_level=player.account_level,
            current_tier=None,  # Will be set by repository
            current_rank=None,  # Will be set by repository
            analysis_version="1.0",
        )

        # 8. Persist via repository
        stored = await self.repository.create_analysis(analysis)

        # 9. Mark matches processed
        if match_ids:
            await self.repository.mark_matches_processed(match_ids)

        # Calculate analysis time
        time_taken = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.info(
            "Player analysis completed",
            puuid=puuid,
            is_smurf=is_smurf,
            detection_score=total_score,
            confidence=confidence,
            analysis_time_seconds=time_taken,
        )

        # 10. Transform to response (using transformer)
        return self.transformer.to_detection_response(
            stored,
            self.config["weights"],
            self.config["thresholds"],
            analysis_time_seconds=time_taken,
        )

    async def _run_analyzers(
        self,
        puuid: str,
        player: PlayerORM,
        matches_data: List[Dict[str, Any]],
        rank_history: Optional[List],
    ) -> List[DetectionFactor]:
        """
        Run all factor analyzers - delegation to analyzer objects.

        All analyzers receive pure data (no database access).
        Pre-fetch rank history and pass to analyzers as parameters.

        :param puuid: Player PUUID
        :param player: Player ORM with relations
        :param matches_data: Match data for analysis (list of dicts)
        :param rank_history: Player rank history (pre-fetched)
        :returns: List of DetectionFactor objects
        """
        factors: List[DetectionFactor] = []

        logger.info(
            "Running factor analyzers",
            puuid=puuid,
            num_analyzers=len(self.factor_analyzers),
            match_count=len(matches_data),
            rank_count=len(rank_history) if rank_history else 0,
        )

        # Run each factor analyzer with pure data (no DB access)
        for factor_name, analyzer in self.factor_analyzers.items():
            factor = await analyzer.analyze(
                puuid=puuid,
                matches_data=matches_data,
                player_data=player,
                rank_history=rank_history,
            )
            factors.append(factor)
            logger.debug(
                "Factor analyzed",
                puuid=puuid,
                factor=factor_name,
                meets_threshold=factor.meets_threshold,
                score=factor.score,
            )

        logger.info(
            "Factor analysis complete",
            puuid=puuid,
            total_factors=len(factors),
            successful_factors=sum(1 for f in factors if f.score > 0),
        )

        return factors

    def _calculate_weighted_score(self, factors: List[DetectionFactor]) -> float:
        """
        Calculate weighted detection score from factors.

        :param factors: List of detection factors
        :returns: Weighted score (0.0 to 1.0)
        """
        total_score = 0.0
        total_weight = 0.0

        for factor in factors:
            total_score += factor.score * factor.weight
            total_weight += factor.weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _determine_detection_status(
        self, detection_score: float, sample_size: int
    ) -> tuple[bool, str]:
        """
        Determine if player is a smurf and confidence level.

        :param detection_score: Weighted detection score
        :param sample_size: Number of matches analyzed
        :returns: Tuple of (is_smurf, confidence_level)
        """
        thresholds = self.config["thresholds"]

        if sample_size < thresholds["min_games"]:
            return False, "insufficient_data"

        if detection_score >= thresholds["detection_score_high"]:
            return True, "high"
        elif detection_score >= thresholds["detection_score_medium"]:
            return True, "medium"
        elif detection_score >= thresholds["detection_score_low"]:
            return True, "low"
        else:
            return False, "none"
