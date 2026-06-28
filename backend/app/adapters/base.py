"""Abstract base class for BMC adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class SensorReading:
    """Represents a sensor reading from a BMC."""

    name: str
    value: float
    unit: str
    sensor_type: str
    timestamp: datetime


@dataclass
class SELEntry:
    """Represents a System Event Log entry from a BMC."""

    record_id: str
    timestamp: datetime
    sensor_name: Optional[str]
    sensor_type: Optional[str]
    event_direction: Optional[str]  # Assertion/Deassertion
    event_data: Optional[str]
    severity: str  # ok/warning/critical


class BMCAdapter(ABC):
    """Abstract base class for BMC protocol adapters.

    This class defines the interface that all BMC adapters must implement,
    regardless of the underlying protocol (Redfish, IPMI, etc.).
    """

    def __init__(self, host: str, username: str, password: str):
        """Initialize the BMC adapter.

        Args:
            host: The hostname or IP address of the BMC
            username: The username for authentication
            password: The password for authentication
        """
        self.host = host
        self.username = username
        self.password = password

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the BMC.

        Returns:
            True if connection was successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection to the BMC."""
        pass

    @abstractmethod
    async def get_power_status(self) -> str:
        """Get the current power status of the system.

        Returns:
            String representing power status (e.g., "On", "Off", "Unknown")
        """
        pass

    @abstractmethod
    async def set_power(self, action: str) -> bool:
        """Control the power state of the system.

        Args:
            action: The power action to perform (e.g., "On", "Off", "Reset")

        Returns:
            True if the action was successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_sensors(self) -> List[SensorReading]:
        """Get all sensor readings from the BMC.

        Returns:
            List of SensorReading objects
        """
        pass

    @abstractmethod
    async def get_sel_logs(self, since: Optional[datetime] = None) -> List[SELEntry]:
        """Get SEL (System Event Log) entries from the BMC.

        Args:
            since: Only return entries newer than this timestamp

        Returns:
            List of SELEntry objects
        """
        pass

    @classmethod
    @abstractmethod
    async def probe(cls, host: str, username: str, password: str) -> bool:
        """Probe to check if this adapter can connect to the given host.

        This method is used by the factory to automatically detect which
        protocol a BMC supports.

        Args:
            host: The hostname or IP address of the BMC
            username: The username for authentication
            password: The password for authentication

        Returns:
            True if this protocol is supported, False otherwise
        """
        pass
