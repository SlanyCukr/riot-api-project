"""Transformers for converting between layers in player_analysis feature.

This module provides transformation functions for:
- ORM models → Pydantic schemas (API responses)
- Detection data → Factor breakdown (Anti-Corruption Layer)

Following the Data Mapper pattern to keep layers decoupled.
"""

from typing import List, Optional, Callable, Any, TYPE_CHECKING

from .orm_models import PlayerAnalysisORM
from .schemas import (
    DetectionResponse,
    DetectionFactor,
    DetectionRequest,
)

if TYPE_CHECKING:
    from .schemas import DetectionExistsResponse, PlayerAnalysisDomain
    from app.features.matches.orm_models import MatchORM
    from app.features.matches.participants_orm import MatchParticipantORM


class PlayerAnalysisTransformer:
    """Transformer for converting player analysis data between layers."""

    @staticmethod
    def to_detection_response(
        detection: PlayerAnalysisORM,
        factor_weights: dict[str, float],
        factor_thresholds: dict[str, Any],
        analysis_time_seconds: Optional[float] = None,
    ) -> DetectionResponse:
        """Transform PlayerAnalysis ORM to DetectionResponse API schema.

        Applies business logic to convert denormalized factor scores back to
        DetectionFactor objects and converts to API response format.

        This demonstrates the Data Mapper pattern where transformers bridge
        the persistence layer (with stored scores) and the API layer (with DTOs).

        :param detection: PlayerAnalysis ORM model from database
        :param factor_weights: Dictionary of factor weights (e.g., {"win_rate": 0.18, ...})
        :param factor_thresholds: Dictionary of factor thresholds for validation
        :param analysis_time_seconds: Optional analysis time for response
        :returns: Detection response schema for API
        """
        # Use Pydantic's from_attributes to map basic fields automatically
        response = DetectionResponse.model_validate(detection)

        # Override computed fields from stored data
        response.detection_score = float(detection.smurf_score)
        response.confidence_level = detection.confidence or "none"
        response.sample_size = detection.games_analyzed
        response.created_at = detection.created_at

        # Create factor breakdown from stored scores
        factors = PlayerAnalysisTransformer._create_factors_from_detection(
            detection, factor_weights, factor_thresholds
        )
        response.factors = factors

        # Add reason and analysis time
        response.reason = (
            f"Stored analysis result (score: {float(detection.smurf_score):.2f})"
        )
        response.analysis_time_seconds = analysis_time_seconds or 0.0

        return response

    @staticmethod
    def to_detection_exists_response(
        detection: PlayerAnalysisORM,
    ) -> "DetectionExistsResponse":
        """Transform PlayerAnalysis ORM to DetectionExistsResponse schema.

        :param detection: PlayerAnalysis ORM model from database
        :returns: Detection exists response schema
        """
        from .schemas import DetectionExistsResponse

        response = DetectionExistsResponse(
            exists=True,
            last_analysis=detection.last_analysis,
            is_smurf=detection.is_smurf,
            detection_score=float(detection.smurf_score),
            confidence_level=detection.confidence or "none",
        )

        return response

    @staticmethod
    def to_domain_model(
        detection: PlayerAnalysisORM,
    ) -> "PlayerAnalysisDomain":
        """Transform PlayerAnalysis ORM to PlayerAnalysis domain model.

        This creates a clean domain model separate from persistence concerns.

        :param detection: PlayerAnalysis ORM model from database
        :returns: PlayerAnalysis domain model
        """
        # Note: If a separate domain model is created in the future,
        # this method would transform the ORM model to it.
        # For now, we return the ORM model itself as it's already well-designed.
        return detection

    @staticmethod
    def from_detection_request(
        request: DetectionRequest,
    ) -> dict[str, Any]:
        """Convert DetectionRequest to internal format for service layer.

        :param request: Detection request schema from API
        :returns: Dictionary of parameters for service layer
        """
        return {
            "puuid": request.puuid,
            "min_games": request.min_games,
            "queue_filter": request.queue_filter,
            "time_period_days": request.time_period_days,
            "force_reanalyze": request.force_reanalyze,
        }

    @staticmethod
    def _create_factors_from_detection(
        detection: PlayerAnalysisORM,
        factor_weights: dict[str, float],
        factor_thresholds: dict[str, Any],
    ) -> List[DetectionFactor]:
        """Create DetectionFactor objects from stored detection data.

        :param detection: PlayerAnalysis ORM model
        :param factor_weights: Dictionary of factor weights
        :param factor_thresholds: Dictionary of factor thresholds
        :returns: List of DetectionFactor objects
        """
        factors = []

        # Define factor configurations
        # Each config contains: (name, score_attr, threshold_check, description_format, value_attr, score_transform)
        factor_configs = [
            (
                "win_rate",
                "win_rate_score",
                lambda s: float(s)
                >= float(factor_thresholds.get("high_win_rate", 0.70)),
                "Win rate: {value:.1%}",
                None,
                None,
            ),
            (
                "win_rate_trend",
                "win_rate_trend_score",
                lambda s: float(s) > 0.5,
                "Win rate trend (score: {value:.2f})",
                None,
                None,
            ),
            (
                "account_level",
                "account_level_score",
                lambda s: float(s) >= 0.5,  # Low account level gives high score
                "Account level: {value}",
                "account_level",
                None,
            ),
            (
                "rank_progression",
                "rank_progression_score",
                lambda s: float(s) > 0.5,
                "Rank progression (score: {value:.2f})",
                None,
                None,
            ),
            (
                "rank_discrepancy",
                "rank_discrepancy_score",
                lambda s: float(s) > 0.6,
                "Rank vs performance (score: {value:.2f})",
                None,
                None,
            ),
            (
                "performance_consistency",
                "performance_consistency_score",
                lambda s: float(s) > 0.5,
                "Performance consistency (score: {value:.2f})",
                None,
                None,
            ),
            (
                "performance_trends",
                "performance_trends_score",
                lambda s: float(s) > 0.6,
                "Performance trends (score: {value:.2f})",
                None,
                None,
            ),
            (
                "role_performance",
                "role_performance_score",
                lambda s: float(s) > 0.5,
                "Role versatility (score: {value:.2f})",
                None,
                None,
            ),
            (
                "kda",
                "kda_score",
                lambda s: float(s) >= float(factor_thresholds.get("high_kda", 3.5)),
                "KDA: {value:.2f}",
                None,
                lambda s: min(
                    1.0, float(s) / float(factor_thresholds.get("high_kda", 3.5))
                ),
            ),
        ]

        # Create factors using configuration
        for config in factor_configs:
            factor = PlayerAnalysisTransformer._create_factor_from_detection(
                detection, factor_weights, *config
            )
            if factor:
                factors.append(factor)

        return factors

    @staticmethod
    def _create_factor_from_detection(
        detection: PlayerAnalysisORM,
        factor_weights: dict[str, float],
        factor_name: str,
        score_attr: str,
        threshold_check: Callable[[Any], bool],
        description_format: str,
        value_attr: Optional[str] = None,
        score_transform: Optional[Callable[[Any], float]] = None,
    ) -> Optional[DetectionFactor]:
        """Create a DetectionFactor from detection data using configuration.

        :param detection: PlayerAnalysis instance
        :param factor_weights: Dictionary of factor weights
        :param factor_name: Name of the factor
        :param score_attr: Attribute name for the score value
        :param threshold_check: Function that takes score and returns bool
        :param description_format: Format string for description (use {value})
        :param value_attr: Optional different attribute for value field
        :param score_transform: Optional function to transform score
        :returns: DetectionFactor or None if score is None
        """
        # Get score value from detection object
        score_value = getattr(detection, score_attr, None)
        if score_value is None:
            return None

        # Handle Decimal conversion
        score_float = float(score_value)

        # Get value (either same as score or from separate attribute)
        value = (
            getattr(detection, value_attr, score_float) if value_attr else score_float
        )

        # Transform score if needed
        final_score = score_transform(score_float) if score_transform else score_float

        # Check if factor meets threshold
        meets_threshold = threshold_check(score_value)

        # Get weight from factor_weights (default to 0.0 if not found)
        weight = factor_weights.get(factor_name, 0.0)

        # Create description
        description = description_format.format(value=score_value)

        return DetectionFactor(
            name=factor_name,
            value=float(value),
            meets_threshold=meets_threshold,
            weight=weight,
            description=description,
            score=final_score,
        )

    @staticmethod
    def match_data_to_dict(
        match: "MatchORM", participant: "MatchParticipantORM"
    ) -> dict[str, Any]:
        """Transform MatchORM + MatchParticipantORM to dict format for analysis.

        :param match: MatchORM instance
        :param participant: MatchParticipantORM instance
        :returns: Dictionary with match data for analysis
        """

        return {
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
