# backend/app/models/event.py
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum

class EventType(str, enum.Enum):
    ALERT = "alert"
    SEL = "sel"
    SYSTEM = "system"
    AUDIT = "audit"

class EventSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class EventStatus(str, enum.Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    IGNORED = "ignored"

class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"), nullable=True)
    event_type: Mapped[EventType] = mapped_column(SQLEnum(EventType), nullable=False)
    severity: Mapped[EventSeverity] = mapped_column(SQLEnum(EventSeverity), default=EventSeverity.INFO)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[EventStatus] = mapped_column(SQLEnum(EventStatus), default=EventStatus.NEW)
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
