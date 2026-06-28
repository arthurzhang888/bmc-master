import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, DateTime, Enum as SQLEnum, JSON, Integer, ARRAY, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class TaskType(str, enum.Enum):
    POWER_CONTROL = "power_control"
    SENSOR_COLLECT = "sensor_collect"
    SEL_COLLECT = "sel_collect"
    CUSTOM_COMMAND = "custom_command"


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_type: Mapped[TaskType] = mapped_column(SQLEnum(TaskType), nullable=False)
    schedule: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    target_servers: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TaskExecutionHistory(Base):
    __tablename__ = "task_execution_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scheduled_tasks.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
