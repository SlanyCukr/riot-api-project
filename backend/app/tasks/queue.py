"""
Background task queue implementation for async data processing.

Provides a priority-based task queue with retry logic, error handling,
and graceful shutdown capabilities.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from collections import defaultdict
import structlog

logger = structlog.get_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class BackgroundTask:
    """Background task data structure."""
    task_type: str
    priority: TaskPriority
    data: Dict[str, Any]
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    max_retries: int = 3
    retry_count: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class TaskQueue:
    """Priority-based background task queue with retry logic."""

    def __init__(self, max_concurrent_tasks: int = 10):
        """
        Initialize task queue.

        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.queue = asyncio.PriorityQueue()
        self.active_tasks: Dict[str, BackgroundTask] = {}
        self.completed_tasks: Dict[str, BackgroundTask] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.running = False
        self.stats = defaultdict(int)
        self._shutdown_event = asyncio.Event()
        self._worker_tasks: List[asyncio.Task] = []

    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler function for a task type."""
        if task_type in self.task_handlers:
            logger.warning("Task handler already registered", task_type=task_type)

        self.task_handlers[task_type] = handler
        logger.info("Task handler registered", task_type=task_type)

    async def start(self):
        """Start the task queue processor."""
        if self.running:
            logger.warning("Task queue is already running")
            return

        self.running = True
        logger.info("Task queue started", max_concurrent_tasks=self.max_concurrent_tasks)

        # Create workers
        self._worker_tasks = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self.max_concurrent_tasks)
        ]

        try:
            await asyncio.gather(*self._worker_tasks)
        except asyncio.CancelledError:
            logger.info("Task queue shutting down...")
        finally:
            await self._shutdown()

    async def stop(self):
        """Stop the task queue processor."""
        if not self.running:
            return

        self.running = False
        self._shutdown_event.set()

        # Cancel all worker tasks
        for worker_task in self._worker_tasks:
            worker_task.cancel()

        logger.info("Task queue stop requested")

    async def add_task(self, task: BackgroundTask):
        """Add a task to the queue."""
        if not self.running:
            raise RuntimeError("Task queue is not running")

        # Priority queue expects (priority, timestamp, task)
        # Lower priority number = higher priority
        priority_value = -task.priority.value
        await self.queue.put((priority_value, task.created_at.timestamp(), task))

        logger.info("Task added to queue", task_id=task.task_id, task_type=task.task_type)
        self.stats['tasks_added'] += 1

    async def get_task_status(self, task_id: str) -> Optional[BackgroundTask]:
        """Get the status of a specific task."""
        # Check active tasks first
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]

        # Check completed tasks
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]

        return None

    async def _worker(self, worker_name: str):
        """Worker process for handling tasks."""
        logger.info("Worker started", worker=worker_name)

        while self.running and not self._shutdown_event.is_set():
            try:
                # Get task from queue with timeout
                try:
                    _, _, task = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Process the task
                await self._process_task(task, worker_name)

            except asyncio.CancelledError:
                logger.info("Worker cancelled", worker=worker_name)
                break
            except Exception as e:
                logger.error("Worker error", worker=worker_name, error=str(e))

        logger.info("Worker stopped", worker=worker_name)

    async def _process_task(self, task: BackgroundTask, worker_name: str):
        """Process a specific task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.active_tasks[task.task_id] = task

        try:
            logger.info(
                "Processing task",
                task_id=task.task_id,
                task_type=task.task_type,
                worker=worker_name
            )

            # Get handler for task type
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler registered for task type: {task.task_type}")

            # Execute the task
            result = await handler(task.data)

            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result

            self.stats['tasks_completed'] += 1
            logger.info(
                "Task completed",
                task_id=task.task_id,
                task_type=task.task_type,
                worker=worker_name
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error_message = str(e)

            self.stats['tasks_failed'] += 1
            logger.error(
                "Task failed",
                task_id=task.task_id,
                task_type=task.task_type,
                worker=worker_name,
                error=str(e)
            )

            # Retry logic
            if task.retry_count < task.max_retries:
                await self._retry_task(task)

        finally:
            # Move task from active to completed
            self.active_tasks.pop(task.task_id, None)
            self.completed_tasks[task.task_id] = task
            self.queue.task_done()

    async def _retry_task(self, task: BackgroundTask):
        """Retry a failed task."""
        task.retry_count += 1
        task.status = TaskStatus.RETRYING
        task.error_message = None
        task.started_at = None
        task.completed_at = None

        # Exponential backoff
        base_delay = 2 ** task.retry_count
        jitter = base_delay * 0.1 * (2 * (hash(task.task_id) % 100) / 100 - 1)  # -10% to +10%
        delay = min(base_delay + jitter, 60)  # Max 60 seconds

        logger.info(
            "Retrying task",
            task_id=task.task_id,
            task_type=task.task_type,
            retry_count=task.retry_count,
            delay_seconds=delay
        )

        await asyncio.sleep(delay)
        await self.add_task(task)

    async def _shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down task queue")

        # Wait for active tasks to complete
        timeout = 30  # 30 seconds grace period
        start_time = datetime.now()

        while self.active_tasks and (datetime.now() - start_time).total_seconds() < timeout:
            await asyncio.sleep(1)
            logger.info(
                "Waiting for active tasks to complete",
                remaining_tasks=len(self.active_tasks)
            )

        if self.active_tasks:
            logger.warning(
                "Shutdown timeout reached",
                remaining_tasks=len(self.active_tasks)
            )

        logger.info("Task queue shutdown complete")

    def get_stats(self) -> Dict[str, Any]:
        """Get task queue statistics."""
        return {
            'running': self.running,
            'active_tasks': len(self.active_tasks),
            'queue_size': self.queue.qsize(),
            'stats': dict(self.stats),
            'completed_tasks': len(self.completed_tasks),
            'registered_handlers': list(self.task_handlers.keys())
        }

    async def clear_completed_tasks(self, older_than_days: int = 7):
        """Clear completed tasks older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        tasks_to_remove = [
            task_id for task_id, task in self.completed_tasks.items()
            if task.completed_at and task.completed_at < cutoff_date
        ]

        for task_id in tasks_to_remove:
            del self.completed_tasks[task_id]

        logger.info("Cleared old completed tasks", count=len(tasks_to_remove))

    def get_active_task_types(self) -> Dict[str, int]:
        """Get count of active tasks by type."""
        task_types = defaultdict(int)
        for task in self.active_tasks.values():
            task_types[task.task_type] += 1
        return dict(task_types)

    def get_failed_tasks(self) -> List[BackgroundTask]:
        """Get list of failed tasks."""
        return [task for task in self.completed_tasks.values() if task.status == TaskStatus.FAILED]