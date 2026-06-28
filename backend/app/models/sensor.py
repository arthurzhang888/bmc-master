import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class SensorType(str, enum.Enum):
    TEMPERATURE = "temperature"
    VOLTAGE = "voltage"
    FAN = "fan"
    POWER = "power"
    CURRENT = "current"
    OTHER = "other"


class SensorStatus(str, enum.Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True)
    sensor_name: Mapped[str] = mapped_column(String(128), nullable=False)
    sensor_type: Mapped[SensorType] = mapped_column(SQLEnum(SensorType), default=SensorType.OTHER)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[SensorStatus] = mapped_column(SQLEnum(SensorStatus), default=SensorStatus.OK)
    lower_threshold_critical: Mapped[float] = mapped_column(Float, nullable=True)
    upper_threshold_critical: Mapped[float] = mapped_column(Float, nullable=True)
    lower_threshold_warning: Mapped[float] = mapped_column(Float, nullable=True)
    upper_threshold_warning: Mapped[float] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    server = relationship("Server", back_populates="sensor_readings")
