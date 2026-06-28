"""Celery tasks for scheduled operations."""

import asyncio
import logging
from celery import shared_task
from sqlalchemy import select
from datetime import datetime, timedelta

from app.core.database import AsyncSessionLocal
from app.models.scheduler import ScheduledTask, TaskExecutionHistory
from app.services.scheduler import SchedulerService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_scheduled_task(self, task_id: str):
    """Execute a scheduled task by ID.

    This task is called by Celery Beat or the API to execute
    a scheduled task.

    Args:
        task_id: The scheduled task ID to execute

    Returns:
        Execution result dictionary
    """
    async def _execute():
        async with AsyncSessionLocal() as db:
            # Get the scheduled task
            result = await db.execute(
                select(ScheduledTask).where(ScheduledTask.id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Scheduled task {task_id} not found")
                return {"status": "error", "message": "Task not found"}

            if not task.is_enabled:
                logger.info(f"Scheduled task {task_id} is disabled, skipping execution")
                return {"status": "skipped", "message": "Task is disabled"}

            # Execute the task
            service = SchedulerService(db)
            execution_result = await service.execute_task(task)

            return {
                "status": execution_result.get("status"),
                "task_id": task_id,
                "task_name": task.name,
                "task_type": task.task_type.value,
                "executed_at": datetime.utcnow().isoformat()
            }

    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"Task execution failed for {task_id}: {exc}")
        # Retry the task
        raise self.retry(exc=exc)


@shared_task
def check_and_run_due_tasks():
    """Check for due tasks and execute them.

    This task is designed to be run periodically by Celery Beat
    to check for tasks that are due to run and execute them.

    Returns:
        Summary of executed tasks
    """
    async def _check():
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()

            # Find tasks that are due and enabled
            result = await db.execute(
                select(ScheduledTask)
                .where(
                    ScheduledTask.is_enabled == True,
                    ScheduledTask.next_run_at <= now
                )
            )
            due_tasks = result.scalars().all()

            executed_count = 0
            failed_count = 0

            for task in due_tasks:
                try:
                    # Queue the task for execution
                    execute_scheduled_task.delay(str(task.id))
                    executed_count += 1
                    logger.info(f"Queued scheduled task {task.id}: {task.name}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to queue task {task.id}: {e}")

            return {
                "status": "completed",
                "due_tasks_found": len(due_tasks),
                "tasks_queued": executed_count,
                "tasks_failed": failed_count,
                "checked_at": now.isoformat()
            }

    return asyncio.run(_check())


@shared_task
def cleanup_old_execution_history(days: int = 30):
    """Clean up old execution history records.

    Args:
        days: Delete records older than this many days

    Returns:
        Cleanup result
    """
    async def _cleanup():
        async with AsyncSessionLocal() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            result = await db.execute(
                select(TaskExecutionHistory)
                .where(TaskExecutionHistory.started_at < cutoff_date)
            )
            old_records = result.scalars().all()

            deleted_count = 0
            for record in old_records:
                await db.delete(record)
                deleted_count += 1

            await db.commit()

            logger.info(f"Cleaned up {deleted_count} old execution history records")

            return {
                "status": "completed",
                "records_deleted": deleted_count,
                "older_than_days": days
            }

    return asyncio.run(_cleanup())
