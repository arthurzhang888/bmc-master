import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, DateTime, Enum as SQLEnum, JSON, Integer, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class DiscoveryStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoveryJob(Base):
    __tablename__ = "discovery_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    network_range: Mapped[str] = mapped_column(String(64), nullable=False)
    ports: Mapped[List[int]] = mapped_column(ARRAY(Integer), default=[623, 443])
    status: Mapped[DiscoveryStatus] = mapped_column(SQLEnum(DiscoveryStatus), default=DiscoveryStatus.PENDING)
    found_devices: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    device_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
