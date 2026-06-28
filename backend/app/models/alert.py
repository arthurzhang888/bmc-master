# backend/app/models/alert.py
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, Integer, Boolean, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum

class RuleType(str, enum.Enum):
    THRESHOLD = "threshold"
    TREND = "trend"
    PRESENCE = "presence"

class AlertSeverity(str, enum.Enum):
    WARNING = "warning"
    CRITICAL = "critical"

class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(SQLEnum(RuleType), default=RuleType.THRESHOLD)
    sensor_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    operator: Mapped[str] = mapped_column(String(8), default=">")  # > < == !=
    threshold: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    duration: Mapped[int] = mapped_column(Integer, default=0)  # seconds
    severity: Mapped[AlertSeverity] = mapped_column(SQLEnum(AlertSeverity), default=AlertSeverity.WARNING)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Notification settings
    notify_email: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_webhook: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alert_rules.id"))
    server_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("servers.id"))
    sensor_name: Mapped[str] = mapped_column(String(128))
    triggered_value: Mapped[float] = mapped_column(Numeric(10, 2))
    severity: Mapped[AlertSeverity] = mapped_column(SQLEnum(AlertSeverity))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
