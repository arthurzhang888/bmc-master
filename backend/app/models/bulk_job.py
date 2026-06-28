import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, DateTime, Enum as SQLEnum, JSON, Integer, ARRAY, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class BulkJobType(str, enum.Enum):
    POWER = "power"
    IPMI_COMMAND = "ipmi_command"


class BulkJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BulkJob(Base):
    __tablename__ = "bulk_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    job_type: Mapped[BulkJobType] = mapped_column(SQLEnum(BulkJobType), nullable=False)
    action: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[BulkJobStatus] = mapped_column(SQLEnum(BulkJobStatus), default=BulkJobStatus.PENDING)
    target_servers: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    results: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
