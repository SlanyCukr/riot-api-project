"""
Background tasks system for async data fetching and analysis.

This package provides a comprehensive background task system for:
- Async match data fetching from Riot API
- Player analysis and smurf detection
- Data cleanup and maintenance
- Scheduled task execution
"""

from .queue import TaskQueue, BackgroundTask, TaskPriority, TaskStatus
from .scheduler import TaskScheduler, ScheduledTask
from .workers import WorkerManager
from .match_fetching import MatchFetchingTasks
from .player_analysis import PlayerAnalysisTasks
from .detection_tasks import DetectionTasks
from .data_cleanup import DataCleanupTasks

__all__ = [
    "TaskQueue",
    "BackgroundTask",
    "TaskPriority",
    "TaskStatus",
    "TaskScheduler",
    "ScheduledTask",
    "WorkerManager",
    "MatchFetchingTasks",
    "PlayerAnalysisTasks",
    "DetectionTasks",
    "DataCleanupTasks",
]