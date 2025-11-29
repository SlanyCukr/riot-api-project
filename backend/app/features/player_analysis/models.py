"""Backward compatibility re-export for player analysis models.

This module re-exports the ORM model from orm_models.py for backward compatibility.
New code should import directly from orm_models.py.
"""

from app.features.player_analysis.orm_models import PlayerAnalysisORM as PlayerAnalysis

__all__ = ["PlayerAnalysis"]
