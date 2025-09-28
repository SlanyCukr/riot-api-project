"""
Tests for the task scheduler system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.tasks.scheduler import TaskScheduler, ScheduledTask
from app.tasks.queue import TaskQueue, BackgroundTask, TaskPriority


class TestTaskScheduler:
    """Test cases for TaskScheduler class."""

    @pytest.fixture
    def task_queue(self):
        """Create a mock task queue."""
        queue = MagicMock(spec=TaskQueue)
        queue.add_task = AsyncMock()
        return queue

    @pytest.fixture
    def scheduler(self, task_queue):
        """Create a task scheduler for testing."""
        return TaskScheduler(task_queue)

    @pytest.fixture
    def scheduled_task(self):
        """Create a scheduled task for testing."""
        return ScheduledTask(
            name="test_task",
            task_type="test_type",
            interval_seconds=60,
            task_data={"test": "data"},
            priority=TaskPriority.NORMAL,
            enabled=True
        )

    def test_scheduler_initialization(self, scheduler, task_queue):
        """Test scheduler initialization."""
        assert scheduler.task_queue == task_queue
        assert len(scheduler.scheduled_tasks) == 0
        assert not scheduler.running

    def test_add_scheduled_task(self, scheduler, scheduled_task):
        """Test adding a scheduled task."""
        scheduler.add_scheduled_task(scheduled_task)

        assert "test_task" in scheduler.scheduled_tasks
        assert scheduler.scheduled_tasks["test_task"] == scheduled_task
        assert scheduler._stats['tasks_scheduled'] == 1

    def test_add_duplicate_task(self, scheduler, scheduled_task):
        """Test adding a duplicate scheduled task."""
        scheduler.add_scheduled_task(scheduled_task)
        scheduler.add_scheduled_task(scheduled_task)  # Add again

        # Should still only have one task
        assert len(scheduler.scheduled_tasks) == 1
        assert scheduler._stats['tasks_scheduled'] == 1  # Not incremented for duplicate

    def test_remove_scheduled_task(self, scheduler, scheduled_task):
        """Test removing a scheduled task."""
        scheduler.add_scheduled_task(scheduled_task)
        assert "test_task" in scheduler.scheduled_tasks

        scheduler.remove_scheduled_task("test_task")
        assert "test_task" not in scheduler.scheduled_tasks

    def test_enable_disable_task(self, scheduler, scheduled_task):
        """Test enabling and disabling scheduled tasks."""
        scheduler.add_scheduled_task(scheduled_task)

        # Disable task
        scheduler.disable_task("test_task")
        assert not scheduled_task.enabled

        # Enable task
        scheduler.enable_task("test_task")
        assert scheduled_task.enabled

    def test_get_task(self, scheduler, scheduled_task):
        """Test getting a scheduled task."""
        scheduler.add_scheduled_task(scheduled_task)

        task = scheduler.get_task("test_task")
        assert task == scheduled_task

        non_existent = scheduler.get_task("non_existent")
        assert non_existent is None

    def test_get_all_tasks(self, scheduler, scheduled_task):
        """Test getting all scheduled tasks."""
        scheduler.add_scheduled_task(scheduled_task)

        all_tasks = scheduler.get_all_tasks()
        assert len(all_tasks) == 1
        assert scheduled_task in all_tasks

    def test_get_enabled_tasks(self, scheduler, scheduled_task):
        """Test getting enabled scheduled tasks."""
        # Add enabled task
        scheduler.add_scheduled_task(scheduled_task)

        # Add disabled task
        disabled_task = ScheduledTask(
            name="disabled_task",
            task_type="test_type",
            interval_seconds=60,
            task_data={"test": "data"},
            priority=TaskPriority.NORMAL,
            enabled=False
        )
        scheduler.add_scheduled_task(disabled_task)

        enabled_tasks = scheduler.get_enabled_tasks()
        assert len(enabled_tasks) == 1
        assert scheduled_task in enabled_tasks
        assert disabled_task not in enabled_tasks

    def test_should_run(self, scheduled_task):
        """Test task run condition."""
        # Task should run immediately if run_immediately is True
        immediate_task = ScheduledTask(
            name="immediate_task",
            task_type="test_type",
            interval_seconds=60,
            task_data={},
            run_immediately=True
        )
        assert immediate_task.should_run()

        # Task should not run if disabled
        scheduled_task.enabled = False
        assert not scheduled_task.should_run()

        # Task should not run if next_run is in the future
        scheduled_task.enabled = True
        scheduled_task.next_run = datetime.now() + timedelta(seconds=30)
        assert not scheduled_task.should_run()

        # Task should run if next_run is in the past
        scheduled_task.next_run = datetime.now() - timedelta(seconds=1)
        assert scheduled_task.should_run()

    def test_schedule_next_run(self, scheduled_task):
        """Test scheduling next run."""
        original_next_run = scheduled_task.next_run
        scheduled_task.schedule_next_run()

        expected_next_run = original_next_run + timedelta(seconds=60)
        assert scheduled_task.next_run >= expected_next_run - timedelta(seconds=1)
        assert scheduled_task.next_run <= expected_next_run + timedelta(seconds=1)

    def test_update_stats(self, scheduled_task):
        """Test updating task statistics."""
        assert scheduled_task.total_runs == 0
        assert scheduled_task.failed_runs == 0
        assert scheduled_task.get_success_rate() == 0.0

        # Update successful run
        scheduled_task.update_stats(True)
        assert scheduled_task.total_runs == 1
        assert scheduled_task.failed_runs == 0
        assert scheduled_task.get_success_rate() == 1.0

        # Update failed run
        scheduled_task.update_stats(False)
        assert scheduled_task.total_runs == 2
        assert scheduled_task.failed_runs == 1
        assert scheduled_task.get_success_rate() == 0.5

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test starting and stopping the scheduler."""
        assert not scheduler.running

        # Start scheduler
        start_task = asyncio.create_task(scheduler.start())
        await asyncio.sleep(0.1)  # Let it start

        assert scheduler.running
        assert scheduler._scheduler_task is not None

        # Stop scheduler
        await scheduler.stop()
        await start_task

        assert not scheduler.running

    @pytest.mark.asyncio
    async def test_run_scheduled_task(self, scheduler, scheduled_task):
        """Test running a scheduled task."""
        scheduler.add_scheduled_task(scheduled_task)

        # Run the task
        await scheduler._run_scheduled_task(scheduled_task)

        # Verify task was added to queue
        scheduler.task_queue.add_task.assert_called_once()
        call_args = scheduler.task_queue.add_task.call_args[0][0]
        assert isinstance(call_args, BackgroundTask)
        assert call_args.task_type == scheduled_task.task_type
        assert call_args.priority == scheduled_task.priority
        assert call_args.data == scheduled_task.task_data

        # Verify task statistics were updated
        assert scheduled_task.total_runs == 1
        assert scheduled_task.failed_runs == 0
        assert scheduled_task.last_run is not None

    @pytest.mark.asyncio
    async def test_run_scheduled_task_failure(self, scheduler, scheduled_task):
        """Test handling of scheduled task failure."""
        scheduler.add_scheduled_task(scheduled_task)

        # Make the queue raise an exception
        scheduler.task_queue.add_task.side_effect = Exception("Queue error")

        # Run the task (should not raise exception)
        await scheduler._run_scheduled_task(scheduled_task)

        # Verify statistics were updated to reflect failure
        assert scheduled_task.total_runs == 1
        assert scheduled_task.failed_runs == 1

    @pytest.mark.asyncio
    async def test_scheduler_loop_execution(self, scheduler, scheduled_task):
        """Test the main scheduler loop."""
        scheduler.add_scheduled_task(scheduled_task)

        # Set task to run immediately
        scheduled_task.next_run = datetime.now() - timedelta(seconds=1)

        # Start scheduler for a short time
        start_task = asyncio.create_task(scheduler.start())
        await asyncio.sleep(0.2)  # Let it run once

        # Stop scheduler
        await scheduler.stop()
        await start_task

        # Verify task was run
        scheduler.task_queue.add_task.assert_called()

    def test_get_stats(self, scheduler, scheduled_task):
        """Test getting scheduler statistics."""
        scheduler.add_scheduled_task(scheduled_task)

        # Add another disabled task
        disabled_task = ScheduledTask(
            name="disabled_task",
            task_type="test_type",
            interval_seconds=60,
            task_data={},
            enabled=False
        )
        scheduler.add_scheduled_task(disabled_task)

        stats = scheduler.get_stats()

        assert stats['total_scheduled_tasks'] == 2
        assert stats['enabled_tasks'] == 1
        assert stats['disabled_tasks'] == 1
        assert 'task_details' in stats
        assert 'test_task' in stats['task_details']
        assert 'disabled_task' in stats['task_details']

    def test_get_overdue_tasks(self, scheduler):
        """Test getting overdue tasks."""
        # Add overdue task
        overdue_task = ScheduledTask(
            name="overdue_task",
            task_type="test_type",
            interval_seconds=60,
            task_data={},
            enabled=True
        )
        overdue_task.next_run = datetime.now() - timedelta(seconds=1)
        scheduler.add_scheduled_task(overdue_task)

        # Add future task
        future_task = ScheduledTask(
            name="future_task",
            task_type="test_type",
            interval_seconds=60,
            task_data={},
            enabled=True
        )
        future_task.next_run = datetime.now() + timedelta(seconds=60)
        scheduler.add_scheduled_task(future_task)

        # Add disabled task
        disabled_task = ScheduledTask(
            name="disabled_task",
            task_type="test_type",
            interval_seconds=60,
            task_data={},
            enabled=False
        )
        disabled_task.next_run = datetime.now() - timedelta(seconds=1)
        scheduler.add_scheduled_task(disabled_task)

        overdue_tasks = scheduler.get_overdue_tasks()
        assert len(overdue_tasks) == 1
        assert overdue_task in overdue_tasks
        assert future_task not in overdue_tasks
        assert disabled_task not in overdue_tasks

    def test_reschedule_task(self, scheduler, scheduled_task):
        """Test rescheduling a task."""
        scheduler.add_scheduled_task(scheduled_task)

        original_next_run = scheduled_task.next_run
        scheduler.reschedule_task("test_task", 120)

        assert scheduled_task.interval_seconds == 120
        assert scheduled_task.next_run > original_next_run

    def test_reschedule_nonexistent_task(self, scheduler):
        """Test rescheduling a non-existent task."""
        # Should not raise exception
        scheduler.reschedule_task("nonexistent", 120)

    def test_run_task_now(self, scheduler, scheduled_task):
        """Test running a task immediately."""
        scheduler.add_scheduled_task(scheduled_task)

        # Set next run to future
        future_time = datetime.now() + timedelta(seconds=60)
        scheduled_task.next_run = future_time

        # Run task now
        scheduler.run_task_now("test_task")

        # Verify next run is now
        assert scheduled_task.next_run <= datetime.now() + timedelta(seconds=1)

    def test_run_task_now_nonexistent(self, scheduler):
        """Test running a non-existent task immediately."""
        # Should not raise exception
        scheduler.run_task_now("nonexistent")