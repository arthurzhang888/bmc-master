import uuid
import os
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from cryptography.fernet import Fernet
import enum

# Initialize Fernet with environment key or generate one for development
_ENCRYPTION_KEY = os.environ.get('BMC_PASSWORD_KEY', Fernet.generate_key())
_fernet = Fernet(_ENCRYPTION_KEY)


def encrypt_password(plain_password: str) -> str:
    """Encrypt a plain text password."""
    return _fernet.encrypt(plain_password.encode()).decode()


def decrypt_password(encrypted_password: str) -> str:
    """Decrypt an encrypted password."""
    return _fernet.decrypt(encrypted_password.encode()).decode()


class ServerStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class PowerState(str, enum.Enum):
    ON = "on"
    OFF = "off"
    UNKNOWN = "unknown"


class Protocol(str, enum.Enum):
    REDFISH = "redfish"
    IPMI = "ipmi"
    UNKNOWN = "unknown"


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname: Mapped[str] = mapped_column(String(128), nullable=True)
    bmc_ip: Mapped[str] = mapped_column(String(39), unique=True, nullable=False, index=True)
    bmc_username: Mapped[str] = mapped_column(String(64), nullable=False)
    _bmc_password: Mapped[str] = mapped_column("bmc_password", Text, nullable=False)
    protocol: Mapped[Protocol] = mapped_column(SQLEnum(Protocol), default=Protocol.UNKNOWN)
    vendor: Mapped[str] = mapped_column(String(32), nullable=True)
    model: Mapped[str] = mapped_column(String(64), nullable=True)
    status: Mapped[ServerStatus] = mapped_column(SQLEnum(ServerStatus), default=ServerStatus.OFFLINE)
    power_state: Mapped[PowerState] = mapped_column(SQLEnum(PowerState), default=PowerState.UNKNOWN)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    sensor_readings = relationship("SensorReading", back_populates="server")

    @property
    def bmc_password(self) -> str:
        """Get decrypted BMC password."""
        return decrypt_password(self._bmc_password)

    @bmc_password.setter
    def bmc_password(self, value: str):
        """Set encrypted BMC password."""
        self._bmc_password = encrypt_password(value)
