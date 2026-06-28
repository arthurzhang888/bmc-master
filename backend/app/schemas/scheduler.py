"""Scheduler schemas."""

from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime


class ScheduledTaskCreate(BaseModel):
    """Schema for creating a scheduled task."""
    name: str
    task_type: str  # power_control, sensor_collect, sel_collect, custom_command
    schedule: str  # Cron expression
    parameters: Dict[str, Any] = {}
    target_servers: List[UUID]


class ScheduledTaskUpdate(BaseModel):
    """Schema for updating a scheduled task."""
    name: Optional[str] = None
    schedule: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    target_servers: Optional[List[UUID]] = None
    is_enabled: Optional[bool] = None


class ScheduledTaskResponse(BaseModel):
    """Schema for scheduled task response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    task_type: str
    schedule: str
    parameters: Dict[str, Any]
    target_servers: List[UUID]
    is_enabled: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    run_count: int
    fail_count: int
    created_at: datetime


class TaskExecutionHistoryResponse(BaseModel):
    """Schema for task execution history response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    status: str  # success, failed
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
