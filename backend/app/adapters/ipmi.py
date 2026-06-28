"""IPMI protocol adapter implementation."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from pyghmi.ipmi import command as ipmi_command

from .base import BMCAdapter, SensorReading, SELEntry

logger = logging.getLogger(__name__)


class IPMIAdapter(BMCAdapter):
    """BMC adapter implementation using the IPMI protocol.

    This adapter uses the pyghmi library to communicate with
    legacy BMCs that support the IPMI standard.
    """

    def __init__(self, host: str, username: str, password: str):
        """Initialize the IPMI adapter.

        Args:
            host: The hostname or IP address of the BMC
            username: The username for authentication
            password: The password for authentication
        """
        super().__init__(host, username, password)
        self._client = None

    async def connect(self) -> bool:
        """Establish connection to the BMC via IPMI.

        Returns:
            True if connection was successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            self._client = await loop.run_in_executor(
                None,
                lambda: ipmi_command.Command(
                    bmc=self.host,
                    userid=self.username,
                    password=self.password,
                ),
            )
            return True
        except Exception as e:
            logger.error(f"IPMI connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Close the connection to the BMC."""
        if self._client:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._client.ipmi_session.logout)
            except Exception as e:
                logger.error(f"IPMI disconnect error: {e}")
            finally:
                self._client = None

    async def get_power_status(self) -> str:
        """Get the current power status of the system.

        Returns:
            String representing power status ("On", "Off", or "Unknown")
        """
        if not self._client:
            raise RuntimeError("Not connected to BMC")

        try:
            loop = asyncio.get_event_loop()
            power_status = await loop.run_in_executor(
                None, self._client.get_power
            )
            # pyghmi returns a dict with 'powerstate' key
            if isinstance(power_status, dict):
                state = power_status.get('powerstate', 'Unknown')
            else:
                state = str(power_status)
            return state
        except Exception as e:
            logger.error(f"Failed to get power status: {e}")
            return "Unknown"

    async def set_power(self, action: str) -> bool:
        """Control the power state of the system.

        Args:
            action: The power action to perform ("on", "off", "softoff",
                   "reset", "boot")

        Returns:
            True if the action was successful, False otherwise
        """
        if not self._client:
            raise RuntimeError("Not connected to BMC")

        try:
            loop = asyncio.get_event_loop()
            # Map common action names to pyghmi expected values
            action_map = {
                "On": "on",
                "Off": "off",
                "ForceOff": "off",
                "GracefulShutdown": "softoff",
                "ForceRestart": "reset",
                "GracefulRestart": "reset",
                "boot": "boot",
            }
            ipmi_action = action_map.get(action, action.lower())

            result = await loop.run_in_executor(
                None, self._client.set_power, ipmi_action
            )
            # set_power returns a dict with status info
            if isinstance(result, dict):
                return result.get('powerstate') == ipmi_action or 'error' not in result
            return True
        except Exception as e:
            logger.error(f"Failed to set power state: {e}")
            return False

    async def get_sensors(self) -> List[SensorReading]:
        """Get all sensor readings from the BMC.

        Returns:
            List of SensorReading objects
        """
        if not self._client:
            raise RuntimeError("Not connected to BMC")

        sensors = []
        timestamp = datetime.now()

        try:
            loop = asyncio.get_event_loop()
            readings = await loop.run_in_executor(
                None, self._client.get_sensor_data
            )

            for reading in readings:
                try:
                    # Map IPMI sensor types to our types
                    sensor_type = self._map_sensor_type(reading.type)
                    unit = self._map_unit(reading.units)

                    # Get the value, handling different types
                    value = self._extract_value(reading.value)
                    if value is None:
                        continue

                    sensors.append(
                        SensorReading(
                            name=reading.name,
                            value=value,
                            unit=unit,
                            sensor_type=sensor_type,
                            timestamp=timestamp,
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to process sensor {reading.name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to get sensor data: {e}")

        return sensors

    def _map_sensor_type(self, ipmi_type: str) -> str:
        """Map IPMI sensor type to our sensor type.

        Args:
            ipmi_type: The IPMI sensor type string

        Returns:
            Mapped sensor type
        """
        type_map = {
            "Temperature": "Temperature",
            "Fan": "Fan",
            "Voltage": "Voltage",
            "Current": "Current",
            "Power": "Power",
            "Energy": "Energy",
        }
        return type_map.get(ipmi_type, ipmi_type)

    def _map_unit(self, ipmi_unit: str) -> str:
        """Map IPMI unit to standard unit string.

        Args:
            ipmi_unit: The IPMI unit string

        Returns:
            Mapped unit string
        """
        unit_map = {
            "degrees C": "Celsius",
            "degrees F": "Fahrenheit",
            "RPM": "RPM",
            "Volts": "Volts",
            "Amps": "Amps",
            "Watts": "Watts",
            "Watt-hours": "Watt-hours",
            "Percent": "Percent",
        }
        return unit_map.get(ipmi_unit, ipmi_unit)

    def _extract_value(self, value) -> float:
        """Extract numeric value from sensor reading.

        Args:
            value: The sensor value (could be various types)

        Returns:
            Float value or None if not convertable
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Try to extract number from string like "25.00 C" or "N/A"
            try:
                return float(value.split()[0])
            except (ValueError, IndexError):
                return None
        return None

    async def get_sel_logs(self, since: Optional[datetime] = None) -> List[SELEntry]:
        """Get SEL logs via IPMI.

        Args:
            since: Only return entries newer than this timestamp

        Returns:
            List of SELEntry objects
        """
        if not self._client:
            raise RuntimeError("Not connected to BMC")

        entries = []
        try:
            loop = asyncio.get_event_loop()

            # Get SEL entries using pyghmi
            sel_entries = await loop.run_in_executor(
                None, self._client.get_event_log
            )

            for entry in sel_entries:
                try:
                    # Parse timestamp from entry
                    timestamp = entry.get('timestamp', datetime.utcnow())
                    if isinstance(timestamp, str):
                        try:
                            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        except:
                            timestamp = datetime.utcnow()

                    # Skip if before since
                    if since and timestamp < since:
                        continue

                    # Map severity
                    severity = entry.get('severity', 'ok')
                    if severity in ['critical', 'error']:
                        severity = 'critical'
                    elif severity in ['warning', 'warn']:
                        severity = 'warning'
                    else:
                        severity = 'ok'

                    entries.append(SELEntry(
                        record_id=str(entry.get('record_id', 'unknown')),
                        timestamp=timestamp,
                        sensor_name=entry.get('sensor_name') or entry.get('sensor'),
                        sensor_type=entry.get('sensor_type'),
                        event_direction=entry.get('event_direction', 'Assertion'),
                        event_data=entry.get('description') or entry.get('message', ''),
                        severity=severity
                    ))
                except Exception as e:
                    logger.error(f"Failed to process SEL entry: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to get SEL logs via IPMI: {e}")

        return entries

    @classmethod
    async def probe(cls, host: str, username: str, password: str) -> bool:
        """Probe to check if IPMI is supported on the given host.

        Attempts to establish an IPMI connection to verify
        that the BMC supports the IPMI protocol.

        Args:
            host: The hostname or IP address of the BMC
            username: The username for authentication
            password: The password for authentication

        Returns:
            True if IPMI is supported, False otherwise
        """
        client = None
        try:
            loop = asyncio.get_event_loop()
            client = await loop.run_in_executor(
                None,
                lambda: ipmi_command.Command(
                    bmc=host,
                    userid=username,
                    password=password,
                ),
            )
            # Try to get power status to verify connection
            await loop.run_in_executor(None, client.get_power)
            return True
        except Exception as e:
            logger.error(f"IPMI probe failed for {host}: {e}")
            return False
        finally:
            if client:
                try:
                    await loop.run_in_executor(None, client.ipmi_session.logout)
                except Exception:
                    pass
