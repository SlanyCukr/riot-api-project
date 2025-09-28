"""
Integration tests for the background tasks system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks.queue import TaskQueue, BackgroundTask, TaskPriority
from app.tasks.scheduler import TaskScheduler, ScheduledTask
from app.tasks.workers import WorkerManager
from app.config.tasks import create_task_system, TaskConfig


class TestTaskSystemIntegration:
    """Integration tests for the complete task system."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_riot_client(self):
        """Create a mock Riot API client."""
        return MagicMock()

    @pytest.fixture
    def mock_detection_service(self):
        """Create a mock detection service."""
        return MagicMock()

    @pytest.fixture
    def task_config(self):
        """Create a task configuration."""
        config = TaskConfig()
        config.max_concurrent_tasks = 2  # Reduce for testing
        config.enable_health_check = False  # Disable for simplicity
        return config

    @pytest.mark.asyncio
    async def test_create_task_system(self, mock_db_session, mock_riot_client,
                                   mock_detection_service, task_config):
        """Test creating the complete task system."""
        # Mock the task modules
        with patch('app.config.tasks.MatchFetchingTasks') as mock_match_fetching, \
             patch('app.config.tasks.PlayerAnalysisTasks') as mock_player_analysis, \
             patch('app.config.tasks.DetectionTasks') as mock_detection_tasks, \
             patch('app.config.tasks.DataCleanupTasks') as mock_data_cleanup:

            # Configure mocks
            mock_match_instance = MagicMock()
            mock_player_instance = MagicMock()
            mock_detection_instance = MagicMock()
            mock_cleanup_instance = MagicMock()

            mock_match_fetching.return_value = mock_match_instance
            mock_player_analysis.return_value = mock_player_instance
            mock_detection_tasks.return_value = mock_detection_instance
            mock_data_cleanup.return_value = mock_cleanup_instance

            # Create task system
            worker_manager, scheduler, task_queue = create_task_system(
                mock_db_session,
                mock_riot_client,
                mock_detection_service,
                task_config
            )

            # Verify components were created
            assert isinstance(worker_manager, WorkerManager)
            assert isinstance(scheduler, TaskScheduler)
            assert isinstance(task_queue, TaskQueue)

            # Verify task handlers were registered
            expected_handlers = [
                'fetch_player_matches',
                'update_active_players',
                'analyze_player_for_smurf',
                'batch_analyze_players',
                'cleanup_old_data',
                'cleanup_failed_detections'
            ]

            for handler_name in expected_handlers:
                assert handler_name in task_queue.task_handlers

            # Verify scheduled tasks were added
            assert len(scheduler.scheduled_tasks) > 0

            # Clean up
            await worker_manager.stop()

    @pytest.mark.asyncio
    async def test_task_execution_flow(self, mock_db_session, mock_riot_client,
                                      mock_detection_service, task_config):
        """Test the complete task execution flow."""
        # Create a simple task system
        task_queue = TaskQueue(max_concurrent_tasks=2)
        scheduler = TaskScheduler(task_queue)
        worker_manager = WorkerManager(task_queue, scheduler,
                                     max_workers=2, enable_health_check=False)

        # Create a simple task handler
        async def test_handler(data):
            await asyncio.sleep(0.1)
            return {'processed': True, 'data': data}

        task_queue.register_handler('test_task', test_handler)

        # Create a scheduled task
        scheduled_task = ScheduledTask(
            name="integration_test",
            task_type="test_task",
            interval_seconds=1,  # Very short for testing
            task_data={'test': 'integration'},
            priority=TaskPriority.NORMAL,
            enabled=True,
            run_immediately=True
        )

        scheduler.add_scheduled_task(scheduled_task)

        # Start the system
        await worker_manager.start()

        try:
            # Wait for task to execute
            await asyncio.sleep(0.5)

            # Verify task was executed
            stats = worker_manager.get_system_stats()
            assert stats['task_queue']['stats'].get('tasks_completed', 0) >= 1
            assert stats['scheduler']['task_details']['integration_test']['total_runs'] >= 1

        finally:
            await worker_manager.stop()

    @pytest.mark.asyncio
    async def test_task_retry_mechanism(self, mock_db_session, mock_riot_client,
                                       mock_detection_service, task_config):
        """Test task retry mechanism."""
        task_queue = TaskQueue(max_concurrent_tasks=1)
        scheduler = TaskScheduler(task_queue)
        worker_manager = WorkerManager(task_queue, scheduler,
                                     max_workers=1, enable_health_check=False)

        # Create a failing handler
        call_count = 0
        async def failing_handler(data):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts
                raise Exception("Test failure")
            return {'success': True, 'attempt': call_count}

        task_queue.register_handler('failing_task', failing_handler)

        # Create a task with retries
        task = BackgroundTask(
            task_type='failing_task',
            priority=TaskPriority.NORMAL,
            data={'test': 'retry'},
            max_retries=3
        )

        # Start the system
        await worker_manager.start()

        try:
            # Add the failing task
            await worker_manager.add_task('failing_task', {'test': 'retry'})

            # Wait for retries to complete
            await asyncio.sleep(2.0)

            # Verify task eventually succeeded
            stats = worker_manager.get_system_stats()
            assert stats['task_queue']['stats'].get('tasks_completed', 0) >= 1
            assert call_count == 3  # Should have been called 3 times

        finally:
            await worker_manager.stop()

    @pytest.mark.asyncio
    async def test_task_priority_processing(self, mock_db_session, mock_riot_client,
                                          mock_detection_service, task_config):
        """Test that tasks are processed according to priority."""
        task_queue = TaskQueue(max_concurrent_tasks=1)  # Single worker to test ordering
        scheduler = TaskScheduler(task_queue)
        worker_manager = WorkerManager(task_queue, scheduler,
                                     max_workers=1, enable_health_check=False)

        execution_order = []

        async def priority_handler(data):
            execution_order.append(data['priority'])
            await asyncio.sleep(0.1)
            return {'priority': data['priority']}

        task_queue.register_handler('priority_test', priority_handler)

        # Start the system
        await worker_manager.start()

        try:
            # Add tasks in reverse priority order
            await worker_manager.add_task('priority_test', {'priority': 'low'}, TaskPriority.LOW)
            await worker_manager.add_task('priority_test', {'priority': 'high'}, TaskPriority.HIGH)
            await worker_manager.add_task('priority_test', {'priority': 'normal'}, TaskPriority.NORMAL)

            # Wait for all tasks to complete
            await asyncio.sleep(1.0)

            # Verify execution order (high, normal, low)
            expected_order = ['high', 'normal', 'low']
            assert execution_order == expected_order

        finally:
            await worker_manager.stop()

    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, mock_db_session, mock_riot_client,
                                           mock_detection_service, task_config):
        """Test system health monitoring."""
        task_config.enable_health_check = True
        task_config.health_check_interval = 0.5  # Very frequent for testing

        task_queue = TaskQueue(max_concurrent_tasks=1)
        scheduler = TaskScheduler(task_queue)
        worker_manager = WorkerManager(task_queue, scheduler,
                                     max_workers=1,
                                     enable_health_check=True,
                                     health_check_interval=0.5)

        async def healthy_handler(data):
            await asyncio.sleep(0.1)
            return {'status': 'healthy'}

        task_queue.register_handler('healthy_task', healthy_handler)

        # Start the system
        await worker_manager.start()

        try:
            # Add a healthy task
            await worker_manager.add_task('healthy_task', {'test': 'health'})

            # Wait for health checks to run
            await asyncio.sleep(1.5)

            # Verify health monitoring is working
            health_status = worker_manager.get_health_status()
            assert health_status['healthy'] == True
            assert health_status['health_check_count'] >= 1

            stats = worker_manager.get_system_stats()
            assert stats['worker_manager']['healthy'] == True

        finally:
            await worker_manager.stop()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_active_tasks(self, mock_db_session,
                                                     mock_riot_client, mock_detection_service, task_config):
        """Test graceful shutdown with active tasks."""
        task_queue = TaskQueue(max_concurrent_tasks=1)
        scheduler = TaskScheduler(task_queue)
        worker_manager = WorkerManager(task_queue, scheduler,
                                     max_workers=1, enable_health_check=False)

        # Create a slow handler
        async def slow_handler(data):
            await asyncio.sleep(1.0)  # Slow task
            return {'completed': True}

        task_queue.register_handler('slow_task', slow_handler)

        # Start the system
        await worker_manager.start()

        try:
            # Add a slow task
            await worker_manager.add_task('slow_task', {'test': 'shutdown'})

            # Let it start
            await asyncio.sleep(0.1)

            # Shutdown while task is running
            start_time = datetime.now()
            await worker_manager.stop()
            shutdown_time = (datetime.now() - start_time).total_seconds()

            # Verify shutdown was graceful (should wait for active task)
            assert shutdown_time >= 0.5  # Should wait for task to complete
            assert not worker_manager.running

        finally:
            # Ensure cleanup
            if worker_manager.running:
                await worker_manager.stop()

    @pytest.mark.asyncio
    async def test_task_status_tracking(self, mock_db_session, mock_riot_client,
                                       mock_detection_service, task_config):
        """Test task status tracking."""
        task_queue = TaskQueue(max_concurrent_tasks=1)
        scheduler = TaskScheduler(task_queue)
        worker_manager = WorkerManager(task_queue, scheduler,
                                     max_workers=1, enable_health_check=False)

        async def status_test_handler(data):
            await asyncio.sleep(0.1)
            return {'status': 'completed'}

        task_queue.register_handler('status_test', status_test_handler)

        # Start the system
        await worker_manager.start()

        try:
            # Add a task and get its ID
            task_id = await worker_manager.add_task('status_test', {'test': 'status'})

            # Check initial status
            status = await worker_manager.get_task_status(task_id)
            assert status is not None
            assert status['task_id'] == task_id

            # Wait for completion
            await asyncio.sleep(0.5)

            # Check final status
            status = await worker_manager.get_task_status(task_id)
            assert status is not None
            assert status['status'] == 'completed'
            assert status['result'] == {'status': 'completed'}

        finally:
            await worker_manager.stop()

    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, mock_db_session, mock_riot_client,
                                            mock_detection_service, task_config):
        """Test error handling and logging."""
        task_queue = TaskQueue(max_concurrent_tasks=1)
        scheduler = TaskScheduler(task_queue)
        worker_manager = WorkerManager(task_queue, scheduler,
                                     max_workers=1, enable_health_check=False)

        # Create a handler that raises an exception
        async def error_handler(data):
            raise ValueError("Test error for logging")

        task_queue.register_handler('error_test', error_handler)

        # Start the system
        await worker_manager.start()

        try:
            # Add a task that will fail
            task_id = await worker_manager.add_task('error_test', {'test': 'error'})

            # Wait for failure
            await asyncio.sleep(0.5)

            # Check that error was handled gracefully
            status = await worker_manager.get_task_status(task_id)
            assert status is not None
            assert status['status'] == 'failed'
            assert 'Test error for logging' in status['error_message']

            # Verify system is still healthy
            health_status = worker_manager.get_health_status()
            assert health_status['healthy'] == True  # System should remain healthy

        finally:
            await worker_manager.stop()

    @pytest.mark.asyncio
    async def test_scheduled_task_execution(self, mock_db_session, mock_riot_client,
                                           mock_detection_service, task_config):
        """Test scheduled task execution."""
        task_queue = TaskQueue(max_concurrent_tasks=1)
        scheduler = TaskScheduler(task_queue)
        worker_manager = WorkerManager(task_queue, scheduler,
                                     max_workers=1, enable_health_check=False)

        async def scheduled_handler(data):
            return {'scheduled': True, 'data': data}

        task_queue.register_handler('scheduled_task', scheduled_handler)

        # Create a scheduled task
        scheduled_task = ScheduledTask(
            name="test_scheduled",
            task_type="scheduled_task",
            interval_seconds=0.5,  # Very short for testing
            task_data={'scheduled': True},
            priority=TaskPriority.NORMAL,
            enabled=True
        )

        scheduler.add_scheduled_task(scheduled_task)

        # Start the system
        await worker_manager.start()

        try:
            # Wait for multiple executions
            await asyncio.sleep(2.0)

            # Verify task was executed multiple times
            stats = worker_manager.get_system_stats()
            task_details = stats['scheduler']['task_details']['test_scheduled']
            assert task_details['total_runs'] >= 2
            assert task_details['enabled'] == True

        finally:
            await worker_manager.stop()