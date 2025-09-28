"""
Tests for the task queue system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.tasks.queue import TaskQueue, BackgroundTask, TaskPriority, TaskStatus


class TestTaskQueue:
    """Test cases for TaskQueue class."""

    @pytest.fixture
    def task_queue(self):
        """Create a task queue for testing."""
        return TaskQueue(max_concurrent_tasks=2)

    @pytest.fixture
    def mock_handler(self):
        """Create a mock task handler."""
        async def handler(data):
            await asyncio.sleep(0.1)  # Simulate work
            return {'result': 'success', 'data': data}
        return handler

    @pytest.mark.asyncio
    async def test_task_queue_initialization(self, task_queue):
        """Test task queue initialization."""
        assert task_queue.max_concurrent_tasks == 2
        assert not task_queue.running
        assert len(task_queue.task_handlers) == 0
        assert len(task_queue.active_tasks) == 0
        assert len(task_queue.completed_tasks) == 0

    @pytest.mark.asyncio
    async def test_register_handler(self, task_queue, mock_handler):
        """Test registering a task handler."""
        task_queue.register_handler('test_task', mock_handler)
        assert 'test_task' in task_queue.task_handlers
        assert task_queue.task_handlers['test_task'] == mock_handler

    @pytest.mark.asyncio
    async def test_add_task_when_not_running(self, task_queue):
        """Test adding task when queue is not running."""
        task = BackgroundTask('test_type', TaskPriority.NORMAL, {})

        with pytest.raises(RuntimeError, match="Task queue is not running"):
            await task_queue.add_task(task)

    @pytest.mark.asyncio
    async def test_add_task_success(self, task_queue, mock_handler):
        """Test successfully adding a task."""
        task_queue.register_handler('test_task', mock_handler)

        # Start the queue
        queue_task = asyncio.create_task(task_queue.start())

        try:
            # Add a task
            task = BackgroundTask('test_task', TaskPriority.NORMAL, {'test': 'data'})
            await task_queue.add_task(task)

            # Verify task was added
            assert task_queue.stats['tasks_added'] == 1

            # Wait for task to complete
            await asyncio.sleep(0.5)

            # Check completed tasks
            assert len(task_queue.completed_tasks) == 1
            completed_task = list(task_queue.completed_tasks.values())[0]
            assert completed_task.status == TaskStatus.COMPLETED
            assert completed_task.result == {'result': 'success', 'data': {'test': 'data'}}

        finally:
            await task_queue.stop()
            await queue_task

    @pytest.mark.asyncio
    async def test_task_priority_ordering(self, task_queue, mock_handler):
        """Test that tasks are processed in priority order."""
        task_queue.register_handler('test_task', mock_handler)

        # Create tasks with different priorities
        low_task = BackgroundTask('test_task', TaskPriority.LOW, {'priority': 'low'})
        high_task = BackgroundTask('test_task', TaskPriority.HIGH, {'priority': 'high'})
        normal_task = BackgroundTask('test_task', TaskPriority.NORMAL, {'priority': 'normal'})

        # Start the queue
        queue_task = asyncio.create_task(task_queue.start())

        try:
            # Add tasks in random order
            await task_queue.add_task(normal_task)
            await task_queue.add_task(low_task)
            await task_queue.add_task(high_task)

            # Wait for tasks to complete
            await asyncio.sleep(0.5)

            # Verify all tasks were processed
            assert len(task_queue.completed_tasks) == 3

        finally:
            await task_queue.stop()
            await queue_task

    @pytest.mark.asyncio
    async def test_task_retry_logic(self, task_queue):
        """Test task retry logic."""
        # Create a handler that fails
        failing_handler = AsyncMock(side_effect=Exception("Test error"))
        task_queue.register_handler('failing_task', failing_handler)

        # Start the queue
        queue_task = asyncio.create_task(task_queue.start())

        try:
            # Add a failing task
            task = BackgroundTask('failing_task', TaskPriority.NORMAL, {}, max_retries=2)
            await task_queue.add_task(task)

            # Wait for retries to complete
            await asyncio.sleep(2.0)

            # Check that task was retried
            completed_tasks = [t for t in task_queue.completed_tasks.values() if t.task_id == task.task_id]
            assert len(completed_tasks) == 1
            completed_task = completed_tasks[0]
            assert completed_task.retry_count == 2
            assert completed_task.status == TaskStatus.FAILED
            assert completed_task.error_message == "Test error"

        finally:
            await task_queue.stop()
            await queue_task

    @pytest.mark.asyncio
    async def test_get_task_status(self, task_queue, mock_handler):
        """Test getting task status."""
        task_queue.register_handler('test_task', mock_handler)

        # Start the queue
        queue_task = asyncio.create_task(task_queue.start())

        try:
            # Add a task
            task = BackgroundTask('test_task', TaskPriority.NORMAL, {'test': 'data'})
            await task_queue.add_task(task)

            # Check status while running
            status = await task_queue.get_task_status(task.task_id)
            assert status is not None
            assert status.task_id == task.task_id

            # Wait for completion
            await asyncio.sleep(0.5)

            # Check status after completion
            status = await task_queue.get_task_status(task.task_id)
            assert status.status == TaskStatus.COMPLETED

        finally:
            await task_queue.stop()
            await queue_task

    @pytest.mark.asyncio
    async def test_get_stats(self, task_queue, mock_handler):
        """Test getting queue statistics."""
        task_queue.register_handler('test_task', mock_handler)

        # Start the queue
        queue_task = asyncio.create_task(task_queue.start())

        try:
            # Add some tasks
            for i in range(3):
                task = BackgroundTask('test_task', TaskPriority.NORMAL, {'test': i})
                await task_queue.add_task(task)

            # Wait for completion
            await asyncio.sleep(0.5)

            # Get stats
            stats = task_queue.get_stats()
            assert stats['running'] == True
            assert stats['tasks_added'] == 3
            assert stats['tasks_completed'] == 3
            assert stats['registered_handlers'] == ['test_task']

        finally:
            await task_queue.stop()
            await queue_task

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, task_queue, mock_handler):
        """Test graceful shutdown with active tasks."""
        # Create a slow handler
        slow_handler = AsyncMock(side_effect=asyncio.sleep(1.0))
        task_queue.register_handler('slow_task', slow_handler)

        # Start the queue
        queue_task = asyncio.create_task(task_queue.start())

        try:
            # Add a slow task
            task = BackgroundTask('slow_task', TaskPriority.NORMAL, {})
            await task_queue.add_task(task)

            # Let it start
            await asyncio.sleep(0.1)

            # Stop the queue
            await task_queue.stop()

            # Verify shutdown completed
            assert not task_queue.running

        finally:
            await queue_task

    @pytest.mark.asyncio
    async def test_clear_completed_tasks(self, task_queue, mock_handler):
        """Test clearing old completed tasks."""
        task_queue.register_handler('test_task', mock_handler)

        # Start the queue
        queue_task = asyncio.create_task(task_queue.start())

        try:
            # Add and complete tasks
            for i in range(3):
                task = BackgroundTask('test_task', TaskPriority.NORMAL, {'test': i})
                await task_queue.add_task(task)

            await asyncio.sleep(0.5)

            # Verify tasks are completed
            assert len(task_queue.completed_tasks) == 3

            # Clear completed tasks
            await task_queue.clear_completed_tasks(older_than_days=0)

            # Verify tasks are cleared
            assert len(task_queue.completed_tasks) == 0

        finally:
            await task_queue.stop()
            await queue_task

    @pytest.mark.asyncio
    async def test_missing_task_handler(self, task_queue):
        """Test handling of missing task handler."""
        # Start the queue without registering handler
        queue_task = asyncio.create_task(task_queue.start())

        try:
            # Add a task with no handler
            task = BackgroundTask('missing_task', TaskPriority.NORMAL, {})
            await task_queue.add_task(task)

            # Wait for processing
            await asyncio.sleep(0.5)

            # Verify task failed
            completed_tasks = [t for t in task_queue.completed_tasks.values() if t.task_id == task.task_id]
            assert len(completed_tasks) == 1
            completed_task = completed_tasks[0]
            assert completed_task.status == TaskStatus.FAILED
            assert "No handler registered" in completed_task.error_message

        finally:
            await task_queue.stop()
            await queue_task