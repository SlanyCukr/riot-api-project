"""
Base class for detection factor analyzers.

This module provides the abstract base class that all factor analyzers
should inherit from to ensure consistent interface and behavior.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Any, List
import structlog

from ..schemas.detection import DetectionFactor
from ..detection_config import DETECTION_WEIGHTS, DETECTION_THRESHOLDS

if TYPE_CHECKING:
    from ..models.players import Player

logger = structlog.get_logger(__name__)


class BaseFactorAnalyzer(ABC):
    """
    Abstract base class for detection factor analyzers.

    All factor analyzers should inherit from this class and implement
    the analyze method to ensure consistent interface.
    """

    def __init__(self, factor_name: str):
        self.factor_name = factor_name
        self.weight = DETECTION_WEIGHTS.get(factor_name, 0.1)
        self.logger = structlog.get_logger(f"{__name__}.{factor_name}")

    @abstractmethod
    async def analyze(
        self,
        puuid: str,
        recent_matches: List[Dict[str, Any]],
        player: "Player",
        db: Any,
    ) -> DetectionFactor:
        """
        Analyze a specific detection factor.

        :param puuid: Player UUID
        :type puuid: str
        :param recent_matches: List of recent match data
        :type recent_matches: List[Dict[str, Any]]
        :param player: Player model instance
        :type player: Player
        :param db: Database session
        :type db: Any
        :returns: DetectionFactor with analysis results
        :rtype: DetectionFactor
        :raises AnalysisError: If analysis fails
        """
        pass

    def _create_factor(
        self,
        value: float,
        meets_threshold: bool,
        description: str,
        score: float,
        context: Dict[str, Any] = None,
    ) -> DetectionFactor:
        """
        Create a DetectionFactor with standard configuration.

        :param value: Raw analyzed value
        :type value: float
        :param meets_threshold: Whether the factor meets detection threshold
        :type meets_threshold: bool
        :param description: Human-readable description
        :type description: str
        :param score: Normalized score (0.0 to 1.0)
        :type score: float
        :param context: Additional context information
        :type context: Dict[str, Any]
        :returns: Configured DetectionFactor
        :rtype: DetectionFactor
        """
        return DetectionFactor(
            name=self.factor_name,
            value=value,
            meets_threshold=meets_threshold,
            weight=self.weight,
            description=description,
            score=score,
            context=context or {},
        )

    def _get_threshold(self, threshold_name: str) -> float:
        """
        Get a threshold value from configuration.

        :param threshold_name: Name of the threshold
        :type threshold_name: str
        :returns: Threshold value
        :rtype: float
        :raises KeyError: If threshold is not found
        """
        if threshold_name not in DETECTION_THRESHOLDS:
            raise KeyError(f"Threshold '{threshold_name}' not found in configuration")
        return DETECTION_THRESHOLDS[threshold_name]

    def _log_analysis_start(self, puuid: str, context: Dict[str, Any] = None):
        """Log the start of factor analysis.

        :param puuid: Player UUID
        :type puuid: str
        :param context: Additional context for logging
        :type context: Dict[str, Any]
        """
        self.logger.debug(
            "Starting factor analysis",
            factor=self.factor_name,
            puuid=puuid,
            **(context or {}),
        )

    def _log_analysis_result(
        self,
        puuid: str,
        value: float,
        meets_threshold: bool,
        score: float,
        context: Dict[str, Any] = None,
    ):
        """Log the result of factor analysis.

        :param puuid: Player UUID
        :type puuid: str
        :param value: Analyzed value
        :type value: float
        :param meets_threshold: Whether factor meets threshold
        :type meets_threshold: bool
        :param score: Normalized score
        :type score: float
        :param context: Additional context
        :type context: Dict[str, Any]
        """
        self.logger.info(
            "Factor analysis completed",
            factor=self.factor_name,
            puuid=puuid,
            value=value,
            meets_threshold=meets_threshold,
            score=score,
            **(context or {}),
        )

    def _create_error_factor(self, error: Exception, puuid: str) -> DetectionFactor:
        """
        Create a DetectionFactor for analysis errors.

        :param error: Exception that occurred during analysis
        :type error: Exception
        :param puuid: Player UUID
        :type puuid: str
        :returns: DetectionFactor representing the error
        :rtype: DetectionFactor
        """
        self.logger.error(
            "Factor analysis failed",
            factor=self.factor_name,
            puuid=puuid,
            error=str(error),
            error_type=type(error).__name__,
        )

        return DetectionFactor(
            name=self.factor_name,
            value=0.0,
            meets_threshold=False,
            weight=self.weight,
            description=f"{self.factor_name} analysis failed: {str(error)}",
            score=0.0,
            context={"error": str(error), "error_type": type(error).__name__},
        )
