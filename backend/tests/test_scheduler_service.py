"""Tests for scheduler service."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.scheduler import SchedulerService
from app.models.scheduler import ScheduledTask, TaskType, TaskExecutionHistory


@pytest.mark.asyncio
async def test_calculate_next_run():
    """Test cron next run calculation."""
    mock_db = AsyncMock()
    service = SchedulerService(mock_db)

    # Mock CronTab to avoid system crontab dependency
    with patch('app.services.scheduler.CronTab') as mock_cron:
        mock_entry = MagicMock()
        mock_entry.next.return_value = 3600  # 1 hour in seconds
        mock_cron.return_value = mock_entry

        # Test hourly schedule
        last_run = datetime(2024, 1, 1, 12, 0, 0)
        next_run = service._calculate_next_run("0 * * * *", last_run)

        assert next_run > last_run
        assert next_run == last_run + timedelta(seconds=3600)


@pytest.mark.asyncio
async def test_create_task():
    """Test creating a scheduled task."""
    mock_db = AsyncMock()
    service = SchedulerService(mock_db)

    task_data = {
        "name": "Test Task",
        "task_type": "power_control",
        "schedule": "0 2 * * *",
        "parameters": {"action": "on"},
        "target_servers": [str(uuid4())]
    }

    with patch.object(service, '_calculate_next_run', return_value=datetime.utcnow() + timedelta(hours=1)):
        task = await service.create_task(task_data)

    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_execute_task_power_control():
    """Test executing a power control task."""
    mock_db = AsyncMock()
    service = SchedulerService(mock_db)

    mock_task = MagicMock()
    mock_task.id = uuid4()
    mock_task.name = "Power On Task"
    mock_task.task_type = TaskType.POWER_CONTROL
    mock_task.parameters = {"action": "on"}
    mock_task.target_servers = [str(uuid4())]
    mock_task.schedule = "0 2 * * *"
    mock_task.run_count = 0
    mock_task.fail_count = 0

    # Mock server lookup
    mock_server = MagicMock()
    mock_server.bmc_ip = "192.168.1.1"
    mock_server.bmc_username = "admin"
    mock_server.bmc_password = "password"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_server
    mock_db.execute.return_value = mock_result

    with patch('app.services.scheduler.BMCAdapterFactory') as mock_factory:
        mock_adapter = AsyncMock()
        mock_adapter.connect.return_value = True
        mock_adapter.set_power.return_value = True
        mock_factory.create.return_value = (mock_adapter, None)

        result = await service.execute_task(mock_task)

    assert result["status"] == "success"
    assert mock_task.run_count == 1