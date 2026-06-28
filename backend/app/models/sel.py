# backend/app/models/sel.py
import uuid
from datetime import datetime
from typing import Optional
import sqlalchemy as sa
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum

class SELSeverity(str, enum.Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"

class SystemEventLog(Base):
    __tablename__ = "sel_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"))
    record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sensor_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sensor_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    event_direction: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # Assertion/Deassertion
    event_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[SELSeverity] = mapped_column(SQLEnum(SELSeverity), default=SELSeverity.OK)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Unique constraint to prevent duplicates
    __table_args__ = (
        sa.UniqueConstraint('server_id', 'record_id', 'timestamp', name='uq_sel_record'),
        sa.Index('idx_sel_server_time', 'server_id', 'timestamp'),
    )
