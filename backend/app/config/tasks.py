"""
Task system configuration and setup.

Provides configuration and initialization for the background task system,
including scheduled tasks and worker management.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from ..tasks.queue import TaskQueue, TaskPriority, BackgroundTask
from ..tasks.scheduler import TaskScheduler, ScheduledTask
from ..tasks.workers import WorkerManager
from ..tasks.match_fetching import MatchFetchingTasks
from ..tasks.player_analysis import PlayerAnalysisTasks
from ..tasks.detection_tasks import DetectionTasks
from ..tasks.data_cleanup import DataCleanupTasks
from ..services.detection import SmurfDetectionService
from ..riot_api.client import RiotAPIClient
from ..database import get_db

logger = structlog.get_logger(__name__)


class TaskConfig:
    """Configuration for the background task system."""

    def __init__(self):
        """Initialize task configuration."""
        # Task queue settings
        self.max_concurrent_tasks = 5
        self.max_task_retries = 3

        # Scheduler settings
        self.scheduler_check_interval = 10  # seconds

        # Worker manager settings
        self.enable_health_check = True
        self.health_check_interval = 60  # seconds

        # Rate limiting settings
        self.default_delay_between_players = 2  # seconds
        self.default_batch_size = 10

        # Retention policies
        self.data_retention_days = 90
        self.detection_retention_days = 365
        self.failed_detection_retention_days = 7

        # Analysis settings
        self.default_min_games = 30
        self.default_queue_filter = 420  # Ranked solo

        # Cleanup settings
        self.cleanup_batch_size = 1000
        self.enable_dry_run_cleanup = False

        # Scheduled task intervals (in seconds)
        self.scheduled_intervals = {
            'update_active_players': 3600,  # 1 hour
            'daily_smurf_analysis': 86400,  # 24 hours
            'weekly_data_cleanup': 604800,  # 7 days
            'cleanup_failed_detections': 86400,  # 24 hours
            'analyze_suspicious_players': 43200,  # 12 hours
            'analyze_new_players': 21600,  # 6 hours
            'reanalyze_old_detections': 172800,  # 48 hours
            'optimize_detection_thresholds': 604800,  # 7 days
            'generate_detection_report': 86400,  # 24 hours
            'calibrate_detection_model': 1209600,  # 14 days
        }

    def get_interval(self, task_name: str) -> int:
        """Get the interval for a scheduled task."""
        return self.scheduled_intervals.get(task_name, 86400)  # Default to 24 hours


def create_task_system(
    db_session,
    riot_client: RiotAPIClient,
    detection_service: SmurfDetectionService,
    config: Optional[TaskConfig] = None
) -> tuple[WorkerManager, TaskScheduler, TaskQueue]:
    """
    Create and configure the complete task system.

    Args:
        db_session: Database session
        riot_client: Riot API client
        detection_service: Smurf detection service
        config: Optional task configuration

    Returns:
        Tuple of (worker_manager, scheduler, task_queue)
    """
    if config is None:
        config = TaskConfig()

    logger.info("Creating task system", config={
        'max_concurrent_tasks': config.max_concurrent_tasks,
        'enable_health_check': config.enable_health_check,
        'health_check_interval': config.health_check_interval
    })

    # Create task queue
    task_queue = TaskQueue(max_concurrent_tasks=config.max_concurrent_tasks)

    # Create task handlers
    match_fetching = MatchFetchingTasks(db_session, riot_client)
    player_analysis = PlayerAnalysisTasks(detection_service)
    detection_tasks = DetectionTasks(detection_service)
    data_cleanup = DataCleanupTasks(db_session)

    # Register task handlers
    task_queue.register_handler('fetch_player_matches', match_fetching.fetch_player_matches)
    task_queue.register_handler('update_active_players', match_fetching.update_active_players)
    task_queue.register_handler('fetch_missing_matches', match_fetching.fetch_missing_matches)
    task_queue.register_handler('refresh_stale_player_data', match_fetching.refresh_stale_player_data)
    task_queue.register_handler('batch_fetch_matches', match_fetching.batch_fetch_matches)

    task_queue.register_handler('analyze_player_for_smurf', player_analysis.analyze_player_for_smurf)
    task_queue.register_handler('batch_analyze_players', player_analysis.batch_analyze_players)
    task_queue.register_handler('analyze_suspicious_players', player_analysis.analyze_suspicious_players)
    task_queue.register_handler('analyze_new_players', player_analysis.analyze_new_players)
    task_queue.register_handler('reanalyze_old_detections', player_analysis.reanalyze_old_detections)
    task_queue.register_handler('analyze_rank_jumps', player_analysis.analyze_rank_jumps)

    task_queue.register_handler('optimize_detection_thresholds', detection_tasks.optimize_detection_thresholds)
    task_queue.register_handler('validate_detection_accuracy', detection_tasks.validate_detection_accuracy)
    task_queue.register_handler('detect_detection_patterns', detection_tasks.detect_detection_patterns)
    task_queue.register_handler('generate_detection_report', detection_tasks.generate_detection_report)
    task_queue.register_handler('calibrate_detection_model', detection_tasks.calibrate_detection_model)

    task_queue.register_handler('cleanup_old_data', data_cleanup.cleanup_old_data)
    task_queue.register_handler('cleanup_failed_detections', data_cleanup.cleanup_failed_detections)
    task_queue.register_handler('cleanup_orphaned_records', data_cleanup.cleanup_orphaned_records)
    task_queue.register_handler('optimize_database', data_cleanup.optimize_database)
    task_queue.register_handler('cleanup_duplicate_records', data_cleanup.cleanup_duplicate_records)

    # Create scheduler
    scheduler = TaskScheduler(task_queue)

    # Add scheduled tasks
    scheduled_tasks = _create_scheduled_tasks(config)
    for task in scheduled_tasks:
        scheduler.add_scheduled_task(task)

    # Create worker manager
    worker_manager = WorkerManager(
        task_queue=task_queue,
        scheduler=scheduler,
        max_workers=config.max_concurrent_tasks,
        enable_health_check=config.enable_health_check,
        health_check_interval=config.health_check_interval
    )

    logger.info("Task system created successfully", scheduled_tasks=len(scheduled_tasks))

    return worker_manager, scheduler, task_queue


def _create_scheduled_tasks(config: TaskConfig) -> List[ScheduledTask]:
    """Create all scheduled tasks based on configuration."""
    scheduled_tasks = []

    # Data fetching tasks
    scheduled_tasks.append(ScheduledTask(
        name="update_active_players_hourly",
        task_type="update_active_players",
        interval_seconds=config.get_interval('update_active_players'),
        task_data={
            'limit': 20,
            'days_threshold': 7,
            'matches_per_player': 20
        },
        priority=TaskPriority.NORMAL,
        enabled=True
    ))

    scheduled_tasks.append(ScheduledTask(
        name="fetch_missing_matches_daily",
        task_type="fetch_missing_matches",
        interval_seconds=config.get_interval('update_active_players') * 2,  # Every 2 hours
        task_data={
            'min_games': 50,
            'days_back': 30
        },
        priority=TaskPriority.NORMAL,
        enabled=True
    ))

    # Player analysis tasks
    scheduled_tasks.append(ScheduledTask(
        name="daily_smurf_analysis",
        task_type="batch_analyze_players",
        interval_seconds=config.get_interval('daily_smurf_analysis'),
        task_data={
            'puuids': [],  # Will be populated dynamically
            'batch_size': config.default_batch_size,
            'delay_seconds': config.default_delay_between_players,
            'analysis_config': {
                'min_games': config.default_min_games,
                'queue_filter': config.default_queue_filter,
                'force_reanalyze': False
            }
        },
        priority=TaskPriority.HIGH,
        enabled=True
    ))

    scheduled_tasks.append(ScheduledTask(
        name="analyze_suspicious_players",
        task_type="analyze_suspicious_players",
        interval_seconds=config.get_interval('analyze_suspicious_players'),
        task_data={
            'limit': 50,
            'min_win_rate': 0.6,
            'min_games': config.default_min_games
        },
        priority=TaskPriority.HIGH,
        enabled=True
    ))

    scheduled_tasks.append(ScheduledTask(
        name="analyze_new_players",
        task_type="analyze_new_players",
        interval_seconds=config.get_interval('analyze_new_players'),
        task_data={
            'days_threshold': 30,
            'limit': 100,
            'min_account_level': 1
        },
        priority=TaskPriority.NORMAL,
        enabled=True
    ))

    scheduled_tasks.append(ScheduledTask(
        name="reanalyze_old_detections",
        task_type="reanalyze_old_detections",
        interval_seconds=config.get_interval('reanalyze_old_detections'),
        task_data={
            'days_threshold': 30,
            'limit': 100,
            'only_smurfs': True
        },
        priority=TaskPriority.NORMAL,
        enabled=True
    ))

    # Detection optimization tasks
    scheduled_tasks.append(ScheduledTask(
        name="optimize_detection_thresholds",
        task_type="optimize_detection_thresholds",
        interval_seconds=config.get_interval('optimize_detection_thresholds'),
        task_data={
            'sample_size': 1000,
            'min_confidence': 0.8
        },
        priority=TaskPriority.LOW,
        enabled=True
    ))

    scheduled_tasks.append(ScheduledTask(
        name="calibrate_detection_model",
        task_type="calibrate_detection_model",
        interval_seconds=config.get_interval('calibrate_detection_model'),
        task_data={
            'sample_size': 500,
            'calibration_method': 'statistical'
        },
        priority=TaskPriority.LOW,
        enabled=True
    ))

    scheduled_tasks.append(ScheduledTask(
        name="generate_detection_report",
        task_type="generate_detection_report",
        interval_seconds=config.get_interval('generate_detection_report'),
        task_data={
            'days_back': 7,
            'include_details': True
        },
        priority=TaskPriority.NORMAL,
        enabled=True
    ))

    # Data cleanup tasks
    scheduled_tasks.append(ScheduledTask(
        name="weekly_data_cleanup",
        task_type="cleanup_old_data",
        interval_seconds=config.get_interval('weekly_data_cleanup'),
        task_data={
            'days_threshold': config.data_retention_days,
            'dry_run': config.enable_dry_run_cleanup,
            'batch_size': config.cleanup_batch_size
        },
        priority=TaskPriority.LOW,
        enabled=True
    ))

    scheduled_tasks.append(ScheduledTask(
        name="cleanup_failed_detections_daily",
        task_type="cleanup_failed_detections",
        interval_seconds=config.get_interval('cleanup_failed_detections'),
        task_data={
            'days_threshold': config.failed_detection_retention_days,
            'max_retries': config.max_task_retries,
            'dry_run': config.enable_dry_run_cleanup
        },
        priority=TaskPriority.LOW,
        enabled=True
    ))

    scheduled_tasks.append(ScheduledTask(
        name="monthly_orphan_cleanup",
        task_type="cleanup_orphaned_records",
        interval_seconds=2592000,  # 30 days
        task_data={
            'dry_run': config.enable_dry_run_cleanup,
            'batch_size': config.cleanup_batch_size
        },
        priority=TaskPriority.LOW,
        enabled=True
    ))

    scheduled_tasks.append(ScheduledTask(
        name="monthly_database_optimization",
        task_type="optimize_database",
        interval_seconds=2592000,  # 30 days
        task_data={
            'vacuum_tables': True,
            'analyze_tables': True,
            'update_statistics': True
        },
        priority=TaskPriority.LOW,
        enabled=True
    ))

    return scheduled_tasks


def create_dynamic_batch_analysis_task(
    player_puuids: List[str],
    priority: TaskPriority = TaskPriority.NORMAL,
    batch_size: Optional[int] = None,
    delay_seconds: Optional[int] = None
) -> BackgroundTask:
    """
    Create a dynamic batch analysis task.

    Args:
        player_puuids: List of player PUUIDs to analyze
        priority: Task priority
        batch_size: Batch size for processing
        delay_seconds: Delay between players

    Returns:
        BackgroundTask instance
    """
    config = TaskConfig()

    return BackgroundTask(
        task_type="batch_analyze_players",
        priority=priority,
        data={
            'puuids': player_puuids,
            'batch_size': batch_size or config.default_batch_size,
            'delay_seconds': delay_seconds or config.default_delay_between_players,
            'analysis_config': {
                'min_games': config.default_min_games,
                'queue_filter': config.default_queue_filter,
                'force_reanalyze': False
            }
        }
    )


def create_immediate_analysis_task(
    puuid: str,
    priority: TaskPriority = TaskPriority.HIGH,
    force_reanalyze: bool = True
) -> BackgroundTask:
    """
    Create an immediate analysis task for a single player.

    Args:
        puuid: Player PUUID to analyze
        priority: Task priority
        force_reanalyze: Whether to force reanalysis

    Returns:
        BackgroundTask instance
    """
    config = TaskConfig()

    return BackgroundTask(
        task_type="analyze_player_for_smurf",
        priority=priority,
        data={
            'puuid': puuid,
            'min_games': config.default_min_games,
            'queue_filter': config.default_queue_filter,
            'force_reanalyze': force_reanalyze
        }
    )


def create_match_fetching_task(
    puuid: str,
    limit: int = 50,
    queue_filter: Optional[int] = None,
    priority: TaskPriority = TaskPriority.NORMAL
) -> BackgroundTask:
    """
    Create a match fetching task for a player.

    Args:
        puuid: Player PUUID
        limit: Number of matches to fetch
        queue_filter: Queue type filter
        priority: Task priority

    Returns:
        BackgroundTask instance
    """
    return BackgroundTask(
        task_type="fetch_player_matches",
        priority=priority,
        data={
            'puuid': puuid,
            'limit': limit,
            'queue_filter': queue_filter
        }
    )


async def get_task_system_stats(worker_manager: WorkerManager) -> Dict[str, Any]:
    """
    Get comprehensive statistics for the task system.

    Args:
        worker_manager: Worker manager instance

    Returns:
        Dictionary with system statistics
    """
    return worker_manager.get_system_stats()


async def validate_task_configuration(worker_manager: WorkerManager) -> Dict[str, Any]:
    """
    Validate the task system configuration.

    Args:
        worker_manager: Worker manager instance

    Returns:
        Dictionary with validation results
    """
    stats = await get_task_system_stats(worker_manager)

    validation_results = {
        'valid': True,
        'issues': [],
        'warnings': [],
        'suggestions': []
    }

    # Check task queue health
    queue_stats = stats['task_queue']
    if not queue_stats['running']:
        validation_results['valid'] = False
        validation_results['issues'].append("Task queue is not running")

    if queue_stats['queue_size'] > 100:
        validation_results['warnings'].append(f"Large queue size: {queue_stats['queue_size']}")

    if len(queue_stats['registered_handlers']) == 0:
        validation_results['valid'] = False
        validation_results['issues'].append("No task handlers registered")

    # Check scheduler health
    scheduler_stats = stats['scheduler']
    if not scheduler_stats['running']:
        validation_results['valid'] = False
        validation_results['issues'].append("Task scheduler is not running")

    if scheduler_stats['enabled_tasks'] == 0:
        validation_results['warnings'].append("No scheduled tasks are enabled")

    # Check worker manager health
    worker_stats = stats['worker_manager']
    if not worker_stats['running']:
        validation_results['valid'] = False
        validation_results['issues'].append("Worker manager is not running")

    if not worker_stats['healthy']:
        validation_results['valid'] = False
        validation_results['issues'].extend(worker_stats['health_issues'])

    # Performance suggestions
    if queue_stats['stats'].get('tasks_failed', 0) > 10:
        failure_rate = queue_stats['stats']['tasks_failed'] / max(queue_stats['stats'].get('tasks_added', 1), 1)
        if failure_rate > 0.1:
            validation_results['suggestions'].append(
                f"High task failure rate ({failure_rate:.1%}). Consider investigating error patterns."
            )

    if worker_stats['metrics'].get('tasks_per_minute', 0) < 1:
        validation_results['suggestions'].append(
            "Low task throughput. Consider adjusting worker count or task priorities."
        )

    return validation_results