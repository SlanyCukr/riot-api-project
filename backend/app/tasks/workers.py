"""
Worker manager for coordinating background task workers.

Provides a high-level interface for managing task workers
with monitoring and lifecycle management.
"""

import asyncio
import signal
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from .queue import TaskQueue, TaskPriority, TaskStatus
from .scheduler import TaskScheduler, ScheduledTask

logger = structlog.get_logger(__name__)


class WorkerManager:
    """High-level manager for background task workers."""

    def __init__(
        self,
        task_queue: TaskQueue,
        scheduler: TaskScheduler,
        max_workers: int = 5,
        enable_health_check: bool = True,
        health_check_interval: int = 60
    ):
        """
        Initialize worker manager.

        Args:
            task_queue: Task queue instance
            scheduler: Task scheduler instance
            max_workers: Maximum number of worker threads
            enable_health_check: Enable periodic health checks
            health_check_interval: Health check interval in seconds
        """
        self.task_queue = task_queue
        self.scheduler = scheduler
        self.max_workers = max_workers
        self.enable_health_check = enable_health_check
        self.health_check_interval = health_check_interval

        self.running = False
        self.start_time: Optional[datetime] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Metrics
        self.metrics = {
            'uptime_seconds': 0,
            'total_tasks_processed': 0,
            'tasks_per_minute': 0.0,
            'last_health_check': None,
            'health_check_count': 0,
            'error_count': 0,
            'last_error': None
        }

        # Health status
        self.healthy = True
        self.health_issues: List[str] = []

    async def start(self):
        """Start the worker manager and all components."""
        if self.running:
            logger.warning("Worker manager is already running")
            return

        self.running = True
        self.start_time = datetime.now()

        # Start task queue
        await self.task_queue.start()

        # Start scheduler
        await self.scheduler.start()

        # Start health check if enabled
        if self.enable_health_check:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()

        logger.info("Worker manager started", max_workers=self.max_workers)

    async def stop(self):
        """Stop the worker manager and all components."""
        if not self.running:
            return

        logger.info("Worker manager stopping...")

        self.running = False
        self._shutdown_event.set()

        # Stop health check
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Stop scheduler
        await self.scheduler.stop()

        # Stop task queue
        await self.task_queue.stop()

        # Update uptime
        if self.start_time:
            self.metrics['uptime_seconds'] = (datetime.now() - self.start_time).total_seconds()

        logger.info("Worker manager stopped")

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        try:
            # For Unix systems
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (AttributeError, ValueError):
            # Signal handling not available (e.g., Windows)
            pass

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal", signal=signum)
        asyncio.create_task(self.stop())

    async def _health_check_loop(self):
        """Periodic health check loop."""
        logger.info("Health check loop started")

        while self.running:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check error", error=str(e))
                self.metrics['error_count'] += 1
                self.metrics['last_error'] = str(e)

        logger.info("Health check loop stopped")

    async def _perform_health_check(self):
        """Perform a comprehensive health check."""
        self.metrics['last_health_check'] = datetime.now()
        self.metrics['health_check_count'] += 1

        health_issues = []

        # Check task queue health
        queue_stats = self.task_queue.get_stats()
        if not queue_stats['running']:
            health_issues.append("Task queue is not running")

        # Check scheduler health
        scheduler_stats = self.scheduler.get_stats()
        if not scheduler_stats['running']:
            health_issues.append("Task scheduler is not running")

        # Check for overdue tasks
        overdue_tasks = self.scheduler.get_overdue_tasks()
        if overdue_tasks:
            health_issues.append(f"{len(overdue_tasks)} tasks are overdue")

        # Check for high failure rate
        if queue_stats['stats'].get('tasks_failed', 0) > 10:
            failure_rate = queue_stats['stats']['tasks_failed'] / max(queue_stats['stats'].get('tasks_added', 1), 1)
            if failure_rate > 0.1:  # More than 10% failure rate
                health_issues.append(f"High task failure rate: {failure_rate:.1%}")

        # Check queue size
        if queue_stats['queue_size'] > 100:
            health_issues.append(f"Large queue size: {queue_stats['queue_size']} tasks")

        # Update health status
        self.healthy = len(health_issues) == 0
        self.health_issues = health_issues

        # Update metrics
        if queue_stats['stats'].get('tasks_completed', 0) > 0:
            uptime_minutes = max(self.metrics['uptime_seconds'] / 60, 1)
            self.metrics['tasks_per_minute'] = queue_stats['stats']['tasks_completed'] / uptime_minutes

        self.metrics['total_tasks_processed'] = queue_stats['stats'].get('tasks_completed', 0)

        # Log health status
        if self.healthy:
            logger.debug("Health check passed")
        else:
            logger.warning("Health check failed", issues=health_issues)

    async def add_task(
        self,
        task_type: str,
        data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3
    ) -> str:
        """
        Add a task to the queue.

        Args:
            task_type: Type of task to add
            data: Task data
            priority: Task priority
            max_retries: Maximum retry attempts

        Returns:
            Task ID
        """
        from .queue import BackgroundTask

        task = BackgroundTask(
            task_type=task_type,
            priority=priority,
            data=data,
            max_retries=max_retries
        )

        await self.task_queue.add_task(task)
        return task.task_id

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.

        Args:
            task_id: Task ID to check

        Returns:
            Task status dictionary or None if not found
        """
        task = await self.task_queue.get_task_status(task_id)
        if not task:
            return None

        return {
            'task_id': task.task_id,
            'task_type': task.task_type,
            'status': task.status.value,
            'priority': task.priority.value,
            'retry_count': task.retry_count,
            'max_retries': task.max_retries,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'error_message': task.error_message,
            'result': task.result
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        queue_stats = self.task_queue.get_stats()
        scheduler_stats = self.scheduler.get_stats()

        uptime = 0
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            'worker_manager': {
                'running': self.running,
                'uptime_seconds': uptime,
                'healthy': self.healthy,
                'health_issues': self.health_issues,
                'max_workers': self.max_workers,
                'metrics': self.metrics.copy()
            },
            'task_queue': queue_stats,
            'scheduler': scheduler_stats
        }

    async def run_immediate_task(
        self,
        task_type: str,
        data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.HIGH
    ) -> str:
        """
        Run a task immediately with high priority.

        Args:
            task_type: Type of task to run
            data: Task data
            priority: Task priority (default HIGH)

        Returns:
            Task ID
        """
        return await self.add_task(task_type, data, priority)

    async def wait_for_task_completion(
        self,
        task_id: str,
        timeout: float = 300.0,
        check_interval: float = 1.0
    ) -> bool:
        """
        Wait for a task to complete.

        Args:
            task_id: Task ID to wait for
            timeout: Maximum time to wait in seconds
            check_interval: How often to check task status

        Returns:
            True if task completed, False if timeout
        """
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            task = await self.task_queue.get_task_status(task_id)
            if task and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                return True

            await asyncio.sleep(check_interval)

        return False

    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status."""
        return {
            'healthy': self.healthy,
            'health_issues': self.health_issues.copy(),
            'last_health_check': self.metrics['last_health_check'],
            'health_check_count': self.metrics['health_check_count'],
            'uptime_seconds': self.metrics['uptime_seconds'],
            'error_count': self.metrics['error_count'],
            'last_error': self.metrics['last_error']
        }

    async def force_health_check(self):
        """Force an immediate health check."""
        await self._perform_health_check()
        return self.get_health_status()

    async def cleanup_old_tasks(self, older_than_days: int = 7):
        """Clean up old completed tasks."""
        await self.task_queue.clear_completed_tasks(older_than_days)
        logger.info("Cleaned up old tasks", older_than_days=older_than_days)