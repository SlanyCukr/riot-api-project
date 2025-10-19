"""Statistical utility functions for safe calculations."""

import statistics
from typing import List


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: The numerator
        denominator: The denominator
        default: Value to return if denominator is zero

    Returns:
        Result of division or default value
    """
    return numerator / denominator if denominator > 0 else default


def safe_mean(values: List[float], default: float = 0.0) -> float:
    """
    Safely calculate mean of values, returning default if list is empty.

    Args:
        values: List of numeric values
        default: Value to return if list is empty

    Returns:
        Mean of values or default value
    """
    return statistics.mean(values) if values else default


def safe_stdev(values: List[float], default: float = 0.0) -> float:
    """
    Safely calculate standard deviation, returning default if insufficient data.

    Args:
        values: List of numeric values
        default: Value to return if list has < 2 elements

    Returns:
        Standard deviation or default value
    """
    return statistics.stdev(values) if len(values) > 1 else default
