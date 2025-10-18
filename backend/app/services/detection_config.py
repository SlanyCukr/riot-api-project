"""
Configuration for smurf detection service.

This module contains thresholds, weights, and other configuration
parameters used in the player analysis algorithms.
"""

from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)

# Detection thresholds configuration
DETECTION_THRESHOLDS: Dict[str, float] = {
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

# Factor weights configuration (must sum to 1.0)
DETECTION_WEIGHTS: Dict[str, float] = {
    "win_rate": 0.18,  # Base win rate
    "win_rate_trend": 0.10,  # Win rate over time (NEW)
    "account_level": 0.08,  # Account age indicator
    "rank_progression": 0.09,  # Rank climb speed
    "rank_discrepancy": 0.20,  # Rank vs performance mismatch (NEW) - HIGH
    "kda_ratio": 0.12,  # Kill/Death/Assist ratio
    "damage_per_minute": 0.08,  # Consistent high damage output
    "vision_score": 0.06,  # Vision and map awareness
    "cs_per_minute": 0.09,  # Farming efficiency
}

# Analysis configuration
ANALYSIS_CONFIG: Dict[str, Any] = {
    "recent_matches_limit": 50,  # Maximum matches to analyze
    "min_matches_for_analysis": 10,  # Minimum matches required
    "performance_window_days": 30,  # Days to consider for performance
    "consistency_threshold": 0.15,  # Performance consistency threshold
    "outlier_threshold": 2.0,  # Standard deviations for outlier detection
}


def validate_configuration() -> None:
    """
    Validate detection configuration parameters.

    Raises:
        ValueError: If configuration is invalid
    """
    # Validate weights sum to 1.0
    total_weight = sum(DETECTION_WEIGHTS.values())
    if not (0.99 <= total_weight <= 1.01):  # Allow small floating point errors
        raise ValueError(
            f"Detection weights must sum to 1.0, current sum: {total_weight:.4f}"
        )

    # Validate thresholds are within reasonable bounds
    if not (0.0 <= DETECTION_THRESHOLDS["high_win_rate"] <= 1.0):
        raise ValueError("high_win_rate threshold must be between 0.0 and 1.0")

    if DETECTION_THRESHOLDS["min_games"] < 1:
        raise ValueError("min_games must be positive")

    if DETECTION_THRESHOLDS["low_account_level"] < 1:
        raise ValueError("low_account_level must be positive")

    # Validate weights are positive and sum correctly
    for name, weight in DETECTION_WEIGHTS.items():
        if weight < 0:
            raise ValueError(f"Weight {name} must be non-negative")

    logger.info(
        "Detection configuration validated",
        total_weight=total_weight,
        num_weights=len(DETECTION_WEIGHTS),
        num_thresholds=len(DETECTION_THRESHOLDS),
    )


def get_detection_config() -> Dict[str, Any]:
    """
    Get complete detection configuration.

    Returns:
        Dictionary containing all detection configuration
    """
    return {
        "thresholds": DETECTION_THRESHOLDS.copy(),
        "weights": DETECTION_WEIGHTS.copy(),
        "analysis": ANALYSIS_CONFIG.copy(),
    }


# Validate configuration on import
validate_configuration()
