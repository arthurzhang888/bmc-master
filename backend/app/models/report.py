import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class ReportType(str, enum.Enum):
    SENSOR_TREND = "sensor_trend"
    ALERT_STATISTICS = "alert_statistics"
    SERVER_UPTIME = "server_uptime"
    ENERGY_CONSUMPTION = "energy_consumption"


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    report_type: Mapped[ReportType] = mapped_column(SQLEnum(ReportType), nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    schedule: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
