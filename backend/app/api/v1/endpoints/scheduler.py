"""Scheduler API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.scheduler import ScheduledTask, TaskType
from app.schemas.scheduler import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    ScheduledTaskResponse,
    TaskExecutionHistoryResponse
)
from app.services.scheduler import SchedulerService

router = APIRouter()


@router.post("/scheduler/tasks", response_model=ScheduledTaskResponse)
async def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new scheduled task.

    Args:
        task_data: Task creation data
        db: Database session

    Returns:
        Created task
    """
    if len(task_data.target_servers) == 0:
        raise HTTPException(status_code=400, detail="At least one target server is required")

    if len(task_data.target_servers) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 target servers per task")

    # Validate task type
    try:
        TaskType(task_data.task_type)
    except ValueError:
        valid_types = [t.value for t in TaskType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task_type. Valid types: {valid_types}"
        )

    service = SchedulerService(db)
    task = await service.create_task(task_data.model_dump())
    return task


@router.get("/scheduler/tasks", response_model=List[ScheduledTaskResponse])
async def list_scheduled_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    enabled_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """List scheduled tasks.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        enabled_only: Only return enabled tasks
        db: Database session

    Returns:
        List of scheduled tasks
    """
    service = SchedulerService(db)
    tasks = await service.list_tasks(skip=skip, limit=limit, enabled_only=enabled_only)
    return tasks


@router.get("/scheduler/tasks/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a scheduled task by ID.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Scheduled task
    """
    service = SchedulerService(db)
    task = await service.get_task(str(task_id))

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.put("/scheduler/tasks/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: UUID,
    task_data: ScheduledTaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a scheduled task.

    Args:
        task_id: Task ID
        task_data: Updated task data
        db: Database session

    Returns:
        Updated task
    """
    service = SchedulerService(db)

    # Check if task exists
    existing = await service.get_task(str(task_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update task
    update_data = task_data.model_dump(exclude_unset=True)

    if "target_servers" in update_data and update_data["target_servers"] is not None:
        if len(update_data["target_servers"]) == 0:
            raise HTTPException(status_code=400, detail="At least one target server is required")
        if len(update_data["target_servers"]) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 target servers per task")

    task = await service.update_task(str(task_id), update_data)
    return task


@router.delete("/scheduler/tasks/{task_id}")
async def delete_scheduled_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a scheduled task.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Success message
    """
    service = SchedulerService(db)
    deleted = await service.delete_task(str(task_id))

    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task deleted successfully"}


@router.get("/scheduler/tasks/{task_id}/history", response_model=List[TaskExecutionHistoryResponse])
async def get_task_execution_history(
    task_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get execution history for a scheduled task.

    Args:
        task_id: Task ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of execution history entries
    """
    service = SchedulerService(db)

    # Check if task exists
    task = await service.get_task(str(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    history = await service.get_task_history(str(task_id), skip=skip, limit=limit)
    return history


@router.post("/scheduler/tasks/{task_id}/execute")
async def execute_scheduled_task_now(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Execute a scheduled task immediately.

    This endpoint triggers immediate execution of a scheduled task
    outside of its normal schedule.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Execution result
    """
    service = SchedulerService(db)

    # Check if task exists
    task = await service.get_task(str(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.is_enabled:
        raise HTTPException(status_code=400, detail="Cannot execute disabled task")

    # Execute task
    result = await service.execute_task(task)

    return {
        "task_id": str(task_id),
        "execution_result": result
    }
