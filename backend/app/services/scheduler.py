"""Scheduler service for managing scheduled tasks."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from crontab import CronTab
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.scheduler import ScheduledTask, TaskType, TaskExecutionHistory
from app.models.server import Server
from app.models.sensor import SensorReading, SensorType, SensorStatus
from app.adapters.factory import BMCAdapterFactory

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing and executing scheduled tasks."""

    def __init__(self, db: AsyncSession):
        """Initialize scheduler service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_task(self, task_data: Dict[str, Any]) -> ScheduledTask:
        """Create a new scheduled task.

        Args:
            task_data: Task data including name, task_type, schedule, parameters, target_servers

        Returns:
            Created ScheduledTask
        """
        # Calculate next run time
        next_run = self._calculate_next_run(task_data["schedule"], datetime.utcnow())

        task = ScheduledTask(
            name=task_data["name"],
            task_type=TaskType(task_data["task_type"]),
            schedule=task_data["schedule"],
            parameters=task_data.get("parameters", {}),
            target_servers=[str(s) for s in task_data["target_servers"]],
            next_run_at=next_run,
            is_enabled=True,
            run_count=0,
            fail_count=0
        )

        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        logger.info(f"Created scheduled task {task.id}: {task.name}")
        return task

    async def update_task(self, task_id: str, task_data: Dict[str, Any]) -> Optional[ScheduledTask]:
        """Update an existing scheduled task.

        Args:
            task_id: Task ID
            task_data: Updated task data

        Returns:
            Updated ScheduledTask or None if not found
        """
        result = await self.db.execute(
            select(ScheduledTask).where(ScheduledTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        # Update fields
        if "name" in task_data and task_data["name"] is not None:
            task.name = task_data["name"]

        if "schedule" in task_data and task_data["schedule"] is not None:
            task.schedule = task_data["schedule"]
            # Recalculate next run time
            task.next_run_at = self._calculate_next_run(task.schedule, datetime.utcnow())

        if "parameters" in task_data and task_data["parameters"] is not None:
            task.parameters = task_data["parameters"]

        if "target_servers" in task_data and task_data["target_servers"] is not None:
            task.target_servers = [str(s) for s in task_data["target_servers"]]

        if "is_enabled" in task_data and task_data["is_enabled"] is not None:
            task.is_enabled = task_data["is_enabled"]

        await self.db.commit()
        await self.db.refresh(task)

        logger.info(f"Updated scheduled task {task.id}: {task.name}")
        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete a scheduled task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            select(ScheduledTask).where(ScheduledTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return False

        await self.db.delete(task)
        await self.db.commit()

        logger.info(f"Deleted scheduled task {task_id}")
        return True

    async def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a scheduled task by ID.

        Args:
            task_id: Task ID

        Returns:
            ScheduledTask or None if not found
        """
        result = await self.db.execute(
            select(ScheduledTask).where(ScheduledTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        skip: int = 0,
        limit: int = 100,
        enabled_only: bool = False
    ) -> List[ScheduledTask]:
        """List scheduled tasks.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            enabled_only: Only return enabled tasks

        Returns:
            List of ScheduledTask
        """
        query = select(ScheduledTask)

        if enabled_only:
            query = query.where(ScheduledTask.is_enabled == True)

        query = query.order_by(ScheduledTask.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def execute_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a scheduled task.

        Args:
            task: ScheduledTask to execute

        Returns:
            Execution result dictionary
        """
        logger.info(f"Executing scheduled task {task.id}: {task.name}")

        # Create execution history record (not committed yet)
        history = TaskExecutionHistory(
            task_id=task.id,
            status="running",
            started_at=datetime.utcnow()
        )
        self.db.add(history)

        try:
            # Execute based on task type
            if task.task_type == TaskType.POWER_CONTROL:
                result = await self._execute_power_control(task)
            elif task.task_type == TaskType.SENSOR_COLLECT:
                result = await self._execute_sensor_collect(task)
            elif task.task_type == TaskType.SEL_COLLECT:
                result = await self._execute_sel_collect(task)
            elif task.task_type == TaskType.CUSTOM_COMMAND:
                result = await self._execute_custom_command(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")

            # Update history with success
            history.status = "success"
            history.result = result
            history.completed_at = datetime.utcnow()

            # Update task stats
            task.last_run_at = datetime.utcnow()
            task.run_count += 1
            task.next_run_at = self._calculate_next_run(task.schedule, datetime.utcnow())

            await self.db.commit()

            logger.info(f"Task {task.id} executed successfully")
            return {"status": "success", "result": result}

        except Exception as e:
            logger.error(f"Task {task.id} execution failed: {e}")

            # Update history with failure
            history.status = "failed"
            history.error_message = str(e)
            history.completed_at = datetime.utcnow()

            # Update task stats
            task.last_run_at = datetime.utcnow()
            task.run_count += 1
            task.fail_count += 1
            task.next_run_at = self._calculate_next_run(task.schedule, datetime.utcnow())

            await self.db.commit()

            return {"status": "failed", "error": str(e)}

    async def get_task_history(
        self,
        task_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[TaskExecutionHistory]:
        """Get execution history for a task.

        Args:
            task_id: Task ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of TaskExecutionHistory
        """
        result = await self.db.execute(
            select(TaskExecutionHistory)
            .where(TaskExecutionHistory.task_id == task_id)
            .order_by(desc(TaskExecutionHistory.started_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    def _calculate_next_run(self, schedule: str, last_run: datetime) -> datetime:
        """Calculate next run time from cron expression.

        Args:
            schedule: Cron expression string
            last_run: Last run datetime

        Returns:
            Next run datetime
        """
        try:
            entry = CronTab(schedule)
            next_run_seconds = entry.next(last_run, default_utc=True)
            return last_run + timedelta(seconds=next_run_seconds)
        except Exception as e:
            logger.error(f"Failed to calculate next run for schedule '{schedule}': {e}")
            # Return a default time (1 hour from now)
            return datetime.utcnow() + timedelta(hours=1)

    async def _execute_power_control(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute power control task.

        Args:
            task: ScheduledTask with power control parameters

        Returns:
            Execution result
        """
        action = task.parameters.get("action", "On")
        results = []

        for server_id in task.target_servers:
            result = await self._execute_server_power_action(server_id, action)
            results.append(result)

        return {
            "task_type": "power_control",
            "action": action,
            "target_count": len(task.target_servers),
            "results": results
        }

    async def _execute_server_power_action(self, server_id: str, action: str) -> Dict[str, Any]:
        """Execute power action on a single server.

        Args:
            server_id: Server ID
            action: Power action

        Returns:
            Execution result for this server
        """
        result = await self.db.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()

        if not server:
            return {
                "server_id": server_id,
                "status": "failed",
                "message": "Server not found"
            }

        try:
            adapter, _ = await BMCAdapterFactory.create(
                server.bmc_ip,
                server.bmc_username,
                server.bmc_password
            )

            connected = await adapter.connect()
            if not connected:
                return {
                    "server_id": server_id,
                    "status": "failed",
                    "message": "Failed to connect to BMC"
                }

            try:
                # Map action names
                action_map = {
                    "on": "On",
                    "off": "ForceOff",
                    "restart": "ForceRestart",
                    "soft_off": "GracefulShutdown",
                    "soft_restart": "GracefulRestart"
                }
                adapter_action = action_map.get(action.lower(), action)

                success = await adapter.set_power(adapter_action)

                return {
                    "server_id": server_id,
                    "status": "success" if success else "failed",
                    "message": f"Power {action} {'succeeded' if success else 'failed'}"
                }
            finally:
                await adapter.disconnect()

        except Exception as e:
            return {
                "server_id": server_id,
                "status": "failed",
                "message": str(e)
            }

    async def _execute_sensor_collect(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute sensor collection task.

        Args:
            task: ScheduledTask with sensor collection parameters

        Returns:
            Execution result
        """
        results = []
        total_sensors = 0

        for server_id in task.target_servers:
            result = await self._collect_server_sensors(server_id)
            results.append(result)
            if result["status"] == "success":
                total_sensors += result.get("sensor_count", 0)

        return {
            "task_type": "sensor_collect",
            "target_count": len(task.target_servers),
            "total_sensors_collected": total_sensors,
            "results": results
        }

    async def _collect_server_sensors(self, server_id: str) -> Dict[str, Any]:
        """Collect sensors from a single server.

        Args:
            server_id: Server ID

        Returns:
            Collection result for this server
        """
        result = await self.db.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()

        if not server:
            return {
                "server_id": server_id,
                "status": "failed",
                "message": "Server not found"
            }

        try:
            adapter, _ = await BMCAdapterFactory.create(
                server.bmc_ip,
                server.bmc_username,
                server.bmc_password
            )

            connected = await adapter.connect()
            if not connected:
                return {
                    "server_id": server_id,
                    "status": "failed",
                    "message": "Failed to connect to BMC"
                }

            try:
                sensors = await adapter.get_sensors()

                # Store sensor readings in database
                stored_count = 0
                for sensor in sensors:
                    # Determine sensor type
                    sensor_type = SensorType.OTHER
                    sensor_type_str = sensor.sensor_type.upper()
                    if "TEMP" in sensor_type_str:
                        sensor_type = SensorType.TEMPERATURE
                    elif "VOLT" in sensor_type_str:
                        sensor_type = SensorType.VOLTAGE
                    elif "FAN" in sensor_type_str:
                        sensor_type = SensorType.FAN
                    elif "POWER" in sensor_type_str:
                        sensor_type = SensorType.POWER
                    elif "CURRENT" in sensor_type_str:
                        sensor_type = SensorType.CURRENT

                    # Determine status based on value (simplified logic)
                    status = SensorStatus.OK

                    reading = SensorReading(
                        server_id=server_id,
                        sensor_name=sensor.name,
                        sensor_type=sensor_type,
                        value=sensor.value,
                        unit=sensor.unit,
                        status=status,
                        recorded_at=sensor.timestamp
                    )
                    self.db.add(reading)
                    stored_count += 1

                await self.db.commit()

                return {
                    "server_id": server_id,
                    "status": "success",
                    "sensor_count": stored_count,
                    "message": f"Collected {stored_count} sensor readings"
                }
            finally:
                await adapter.disconnect()

        except Exception as e:
            return {
                "server_id": server_id,
                "status": "failed",
                "message": str(e)
            }

    async def _execute_sel_collect(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute SEL collection task.

        Args:
            task: ScheduledTask with SEL collection parameters

        Returns:
            Execution result
        """
        hours = task.parameters.get("hours", 24)
        since = datetime.utcnow() - timedelta(hours=hours)

        results = []
        total_entries = 0

        for server_id in task.target_servers:
            result = await self._collect_server_sel(server_id, since)
            results.append(result)
            if result["status"] == "success":
                total_entries += result.get("entry_count", 0)

        return {
            "task_type": "sel_collect",
            "target_count": len(task.target_servers),
            "total_entries_collected": total_entries,
            "since_hours": hours,
            "results": results
        }

    async def _collect_server_sel(self, server_id: str, since: datetime) -> Dict[str, Any]:
        """Collect SEL logs from a single server.

        Args:
            server_id: Server ID
            since: Only collect entries after this time

        Returns:
            Collection result for this server
        """
        result = await self.db.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()

        if not server:
            return {
                "server_id": server_id,
                "status": "failed",
                "message": "Server not found"
            }

        try:
            adapter, _ = await BMCAdapterFactory.create(
                server.bmc_ip,
                server.bmc_username,
                server.bmc_password
            )

            connected = await adapter.connect()
            if not connected:
                return {
                    "server_id": server_id,
                    "status": "failed",
                    "message": "Failed to connect to BMC"
                }

            try:
                entries = await adapter.get_sel_logs(since=since)

                # SEL entries are typically stored as events
                # For now, just return the count and details
                entry_details = []
                for entry in entries:
                    entry_details.append({
                        "record_id": entry.record_id,
                        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                        "sensor_name": entry.sensor_name,
                        "sensor_type": entry.sensor_type,
                        "severity": entry.severity,
                        "event_data": entry.event_data
                    })

                return {
                    "server_id": server_id,
                    "status": "success",
                    "entry_count": len(entries),
                    "entries": entry_details[:100]  # Limit details in result
                }
            finally:
                await adapter.disconnect()

        except Exception as e:
            return {
                "server_id": server_id,
                "status": "failed",
                "message": str(e)
            }

    async def _execute_custom_command(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute custom command task.

        Args:
            task: ScheduledTask with custom command parameters

        Returns:
            Execution result
        """
        command = task.parameters.get("command", "")
        if not command:
            return {
                "task_type": "custom_command",
                "status": "failed",
                "message": "No command specified"
            }

        results = []
        for server_id in task.target_servers:
            # Custom command execution would require IPMI raw commands
            # For now, return a placeholder
            results.append({
                "server_id": server_id,
                "status": "not_implemented",
                "message": "Custom command execution not yet implemented"
            })

        return {
            "task_type": "custom_command",
            "command": command,
            "target_count": len(task.target_servers),
            "results": results
        }
