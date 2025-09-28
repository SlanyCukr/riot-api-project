"""
Task scheduler for running periodic background tasks.

Provides a scheduler that can run tasks on defined intervals
with configurable priorities and parameters.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from .queue import BackgroundTask, TaskPriority, TaskQueue
import structlog

logger = structlog.get_logger(__name__)


class ScheduledTask:
    """Represents a scheduled task with timing and configuration."""

    def __init__(
        self,
        name: str,
        task_type: str,
        interval_seconds: int,
        task_data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        enabled: bool = True,
        run_immediately: bool = False
    ):
        """
        Initialize scheduled task.

        Args:
            name: Unique name for the scheduled task
            task_type: Type of task to run
            interval_seconds: How often to run the task
            task_data: Data to pass to the task handler
            priority: Task priority
            enabled: Whether the task is enabled
            run_immediately: Whether to run the task immediately on start
        """
        self.name = name
        self.task_type = task_type
        self.interval_seconds = interval_seconds
        self.task_data = task_data
        self.priority = priority
        self.enabled = enabled
        self.run_immediately = run_immediately
        self.last_run = None
        self.next_run = datetime.now() if run_immediately else datetime.now() + timedelta(seconds=interval_seconds)
        self.total_runs = 0
        self.failed_runs = 0

    def should_run(self) -> bool:
        """Check if the task should run now."""
        return self.enabled and datetime.now() >= self.next_run

    def schedule_next_run(self):
        """Schedule the next run."""
        self.next_run = datetime.now() + timedelta(seconds=self.interval_seconds)

    def update_stats(self, success: bool):
        """Update task run statistics."""
        self.total_runs += 1
        if not success:
            self.failed_runs += 1

    def get_success_rate(self) -> float:
        """Get task success rate."""
        if self.total_runs == 0:
            return 0.0
        return (self.total_runs - self.failed_runs) / self.total_runs


class TaskScheduler:
    """Task scheduler for running periodic background tasks."""

    def __init__(self, task_queue: TaskQueue):
        """
        Initialize task scheduler.

        Args:
            task_queue: Task queue to submit scheduled tasks to
        """
        self.task_queue = task_queue
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._stats = {
            'tasks_scheduled': 0,
            'tasks_executed': 0,
            'tasks_failed': 0,
            'scheduler_uptime': 0
        }
        self._start_time: Optional[datetime] = None

    def add_scheduled_task(self, scheduled_task: ScheduledTask):
        """Add a scheduled task."""
        if scheduled_task.name in self.scheduled_tasks:
            logger.warning("Scheduled task already exists", name=scheduled_task.name)
            return

        self.scheduled_tasks[scheduled_task.name] = scheduled_task
        self._stats['tasks_scheduled'] += 1

        logger.info(
            "Scheduled task added",
            name=scheduled_task.name,
            interval_seconds=scheduled_task.interval_seconds,
            enabled=scheduled_task.enabled,
            next_run=scheduled_task.next_run
        )

    def remove_scheduled_task(self, name: str):
        """Remove a scheduled task."""
        if name in self.scheduled_tasks:
            del self.scheduled_tasks[name]
            logger.info("Scheduled task removed", name=name)

    def enable_task(self, name: str):
        """Enable a scheduled task."""
        if name in self.scheduled_tasks:
            self.scheduled_tasks[name].enabled = True
            logger.info("Scheduled task enabled", name=name)

    def disable_task(self, name: str):
        """Disable a scheduled task."""
        if name in self.scheduled_tasks:
            self.scheduled_tasks[name].enabled = False
            logger.info("Scheduled task disabled", name=name)

    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """Get a scheduled task by name."""
        return self.scheduled_tasks.get(name)

    def get_all_tasks(self) -> List[ScheduledTask]:
        """Get all scheduled tasks."""
        return list(self.scheduled_tasks.values())

    def get_enabled_tasks(self) -> List[ScheduledTask]:
        """Get enabled scheduled tasks."""
        return [task for task in self.scheduled_tasks.values() if task.enabled]

    async def start(self):
        """Start the task scheduler."""
        if self.running:
            logger.warning("Task scheduler is already running")
            return

        self.running = True
        self._start_time = datetime.now()
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        logger.info("Task scheduler started", scheduled_tasks=len(self.scheduled_tasks))

    async def stop(self):
        """Stop the task scheduler."""
        if not self.running:
            return

        self.running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # Update uptime
        if self._start_time:
            self._stats['scheduler_uptime'] = (datetime.now() - self._start_time).total_seconds()

        logger.info("Task scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")

        while self.running:
            try:
                # Check each scheduled task
                for task in self.scheduled_tasks.values():
                    if task.should_run():
                        await self._run_scheduled_task(task)

                # Sleep for a short interval
                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                logger.info("Task scheduler stopping...")
                break
            except Exception as e:
                logger.error("Scheduler error", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error

        logger.info("Scheduler loop stopped")

    async def _run_scheduled_task(self, scheduled_task: ScheduledTask):
        """Run a scheduled task."""
        task_start_time = datetime.now()
        success = False

        try:
            logger.info(
                "Running scheduled task",
                name=scheduled_task.name,
                task_type=scheduled_task.task_type
            )

            # Create and queue the task
            task = BackgroundTask(
                task_type=scheduled_task.task_type,
                priority=scheduled_task.priority,
                data=scheduled_task.task_data.copy()
            )

            await self.task_queue.add_task(task)

            # Update schedule
            scheduled_task.last_run = task_start_time
            scheduled_task.schedule_next_run()
            scheduled_task.update_stats(True)

            self._stats['tasks_executed'] += 1
            success = True

            logger.info(
                "Scheduled task queued",
                name=scheduled_task.name,
                next_run=scheduled_task.next_run,
                total_runs=scheduled_task.total_runs
            )

        except Exception as e:
            scheduled_task.update_stats(False)
            self._stats['tasks_failed'] += 1

            logger.error(
                "Failed to run scheduled task",
                name=scheduled_task.name,
                error=str(e)
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        enabled_count = len(self.get_enabled_tasks())
        total_tasks = len(self.scheduled_tasks)

        task_stats = {}
        for name, task in self.scheduled_tasks.items():
            task_stats[name] = {
                'enabled': task.enabled,
                'total_runs': task.total_runs,
                'failed_runs': task.failed_runs,
                'success_rate': task.get_success_rate(),
                'next_run': task.next_run,
                'last_run': task.last_run
            }

        return {
            'running': self.running,
            'total_scheduled_tasks': total_tasks,
            'enabled_tasks': enabled_tasks,
            'disabled_tasks': total_tasks - enabled_tasks,
            'stats': self._stats.copy(),
            'task_details': task_stats
        }

    def get_overdue_tasks(self) -> List[ScheduledTask]:
        """Get tasks that are overdue to run."""
        now = datetime.now()
        return [
            task for task in self.scheduled_tasks.values()
            if task.enabled and task.next_run < now
        ]

    def reschedule_task(self, name: str, interval_seconds: Optional[int] = None):
        """Reschedule a task with new interval."""
        if name not in self.scheduled_tasks:
            logger.warning("Task not found for rescheduling", name=name)
            return

        task = self.scheduled_tasks[name]
        if interval_seconds:
            task.interval_seconds = interval_seconds

        task.next_run = datetime.now() + timedelta(seconds=task.interval_seconds)
        logger.info(
            "Task rescheduled",
            name=name,
            interval_seconds=task.interval_seconds,
            next_run=task.next_run
        )

    def run_task_now(self, name: str):
        """Run a scheduled task immediately."""
        if name not in self.scheduled_tasks:
            logger.warning("Task not found for immediate run", name=name)
            return

        task = self.scheduled_tasks[name]
        task.next_run = datetime.now()
        logger.info("Task scheduled to run immediately", name=name)