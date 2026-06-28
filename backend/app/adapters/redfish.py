"""Redfish protocol adapter implementation."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import redfish

from .base import BMCAdapter, SensorReading, SELEntry

logger = logging.getLogger(__name__)


class RedfishAdapter(BMCAdapter):
    """BMC adapter implementation using the Redfish REST API.

    This adapter uses the python-redfish library to communicate with
    modern BMCs that support the Redfish standard.
    """

    def __init__(self, host: str, username: str, password: str):
        """Initialize the Redfish adapter.

        Args:
            host: The hostname or IP address of the BMC
            username: The username for authentication
            password: The password for authentication
        """
        super().__init__(host, username, password)
        self._client: Optional[redfish.redfish_client] = None
        self._systems_id: Optional[str] = None

    async def connect(self) -> bool:
        """Establish connection to the BMC via Redfish.

        Returns:
            True if connection was successful, False otherwise
        """
        try:
            # Run the blocking redfish client creation in a thread
            loop = asyncio.get_event_loop()
            self._client = await loop.run_in_executor(
                None,
                lambda: redfish.redfish_client(
                    base_url=f"https://{self.host}",
                    username=self.username,
                    password=self.password,
                    default_prefix="/redfish/v1",
                ),
            )

            # Login to the Redfish service
            await loop.run_in_executor(None, self._client.login)

            # Get the default system ID
            systems = await loop.run_in_executor(
                None, self._client.get, "/redfish/v1/Systems"
            )
            systems_data = systems.dict
            if "Members" in systems_data and systems_data["Members"]:
                self._systems_id = systems_data["Members"][0]["@odata.id"].split("/")[-1]
            else:
                self._systems_id = "1"  # Default system ID

            return True
        except Exception as e:
            logger.error(f"Redfish connection failed for {self.host}: {e}")
            return False

    async def disconnect(self) -> None:
        """Close the connection to the BMC."""
        if self._client:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._client.logout)
            except Exception as e:
                logger.error(f"Redfish disconnect error: {e}")
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
            system = await loop.run_in_executor(
                None,
                self._client.get,
                f"/redfish/v1/Systems/{self._systems_id}",
            )
            system_data = system.dict
            power_state = system_data.get("PowerState", "Unknown")
            return power_state
        except Exception as e:
            logger.error(f"Failed to get power status: {e}")
            return "Unknown"

    async def set_power(self, action: str) -> bool:
        """Control the power state of the system.

        Args:
            action: The power action to perform ("On", "Off", "ForceOff",
                   "GracefulShutdown", "ForceRestart", "Nmi", "GracefulRestart")

        Returns:
            True if the action was successful, False otherwise
        """
        if not self._client:
            raise RuntimeError("Not connected to BMC")

        try:
            loop = asyncio.get_event_loop()
            body = {"ResetType": action}
            response = await loop.run_in_executor(
                None,
                self._client.post,
                f"/redfish/v1/Systems/{self._systems_id}/Actions/ComputerSystem.Reset",
                body=body,
            )
            return response.status in (200, 201, 202, 204)
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

            # Get chassis information for thermal and power data
            chassis_list = await loop.run_in_executor(
                None, self._client.get, "/redfish/v1/Chassis"
            )
            chassis_data = chassis_list.dict

            for chassis_member in chassis_data.get("Members", []):
                chassis_url = chassis_member.get("@odata.id")
                if not chassis_url:
                    continue

                chassis_id = chassis_url.split("/")[-1]

                # Get thermal information (temperatures, fans)
                try:
                    thermal = await loop.run_in_executor(
                        None,
                        self._client.get,
                        f"/redfish/v1/Chassis/{chassis_id}/Thermal",
                    )
                    thermal_data = thermal.dict

                    # Process temperature readings
                    for temp in thermal_data.get("Temperatures", []):
                        if temp.get("ReadingCelsius") is not None:
                            sensors.append(
                                SensorReading(
                                    name=temp.get("Name", "Unknown"),
                                    value=float(temp["ReadingCelsius"]),
                                    unit="Celsius",
                                    sensor_type="Temperature",
                                    timestamp=timestamp,
                                )
                            )

                    # Process fan readings
                    for fan in thermal_data.get("Fans", []):
                        if fan.get("Reading") is not None:
                            unit = fan.get("ReadingUnits", "RPM")
                            sensors.append(
                                SensorReading(
                                    name=fan.get("Name", "Unknown"),
                                    value=float(fan["Reading"]),
                                    unit=unit,
                                    sensor_type="Fan",
                                    timestamp=timestamp,
                                )
                            )
                except Exception as e:
                    logger.error(f"Failed to get thermal data: {e}")

                # Get power information
                try:
                    power = await loop.run_in_executor(
                        None,
                        self._client.get,
                        f"/redfish/v1/Chassis/{chassis_id}/Power",
                    )
                    power_data = power.dict

                    # Process power control readings
                    for control in power_data.get("PowerControl", []):
                        if control.get("PowerConsumedWatts") is not None:
                            sensors.append(
                                SensorReading(
                                    name=f"{control.get('Name', 'Power')} Consumed",
                                    value=float(control["PowerConsumedWatts"]),
                                    unit="Watts",
                                    sensor_type="Power",
                                    timestamp=timestamp,
                                )
                            )
                        if control.get("PowerCapacityWatts") is not None:
                            sensors.append(
                                SensorReading(
                                    name=f"{control.get('Name', 'Power')} Capacity",
                                    value=float(control["PowerCapacityWatts"]),
                                    unit="Watts",
                                    sensor_type="Power",
                                    timestamp=timestamp,
                                )
                            )

                    # Process voltage readings
                    for voltage in power_data.get("Voltages", []):
                        if voltage.get("ReadingVolts") is not None:
                            sensors.append(
                                SensorReading(
                                    name=voltage.get("Name", "Unknown"),
                                    value=float(voltage["ReadingVolts"]),
                                    unit="Volts",
                                    sensor_type="Voltage",
                                    timestamp=timestamp,
                                )
                            )
                except Exception as e:
                    logger.error(f"Failed to get power data: {e}")

        except Exception as e:
            logger.error(f"Failed to get chassis list: {e}")

        return sensors

    async def get_sel_logs(self, since: Optional[datetime] = None) -> List[SELEntry]:
        """Get SEL logs from the BMC."""
        if not self._client:
            raise RuntimeError("Not connected to BMC")

        entries = []
        try:
            loop = asyncio.get_event_loop()

            # Get log service from the system
            response = await loop.run_in_executor(
                None,
                self._client.get,
                f"/redfish/v1/Systems/{self._systems_id}/LogServices"
            )
            log_services = response.dict

            for member in log_services.get("Members", []):
                log_service_url = member.get("@odata.id", "")
                if "SEL" in log_service_url.upper() or "Event" in log_service_url:
                    # Get log entries
                    entries_url = f"{log_service_url}/Entries"
                    entries_response = await loop.run_in_executor(
                        None,
                        self._client.get,
                        entries_url
                    )
                    entries_data = entries_response.dict

                    for entry in entries_data.get("Members", []):
                        # Parse timestamp
                        created = entry.get("Created", "")
                        try:
                            timestamp = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        except:
                            timestamp = datetime.utcnow()

                        # Skip if before since
                        if since and timestamp < since:
                            continue

                        # Map severity
                        severity = entry.get("Severity", "OK")
                        if severity in ["Critical", "CriticalError"]:
                            severity = "critical"
                        elif severity in ["Warning", "Degraded"]:
                            severity = "warning"
                        else:
                            severity = "ok"

                        entries.append(SELEntry(
                            record_id=str(entry.get("Id", entry.get("EntryCode", "unknown"))),
                            timestamp=timestamp,
                            sensor_name=entry.get("SensorName") or entry.get("MessageArgs", [None])[0],
                            sensor_type=entry.get("SensorType"),
                            event_direction=entry.get("EntryType"),
                            event_data=entry.get("Message", entry.get("MessageId", "")),
                            severity=severity
                        ))
        except Exception as e:
            logger.error(f"Failed to get SEL logs: {e}")

        return entries

    @classmethod
    async def probe(cls, host: str, username: str, password: str) -> bool:
        """Probe to check if Redfish is supported on the given host.

        Attempts to connect to the Redfish /redfish/v1 endpoint to verify
        that the BMC supports the Redfish protocol.

        Args:
            host: The hostname or IP address of the BMC
            username: The username for authentication
            password: The password for authentication

        Returns:
            True if Redfish is supported, False otherwise
        """
        client = None
        try:
            loop = asyncio.get_event_loop()
            client = await loop.run_in_executor(
                None,
                lambda: redfish.redfish_client(
                    base_url=f"https://{host}",
                    username=username,
                    password=password,
                    default_prefix="/redfish/v1",
                ),
            )
            await loop.run_in_executor(None, client.login)

            # Try to get the root service to verify it's a valid Redfish endpoint
            root = await loop.run_in_executor(None, client.get, "/redfish/v1")
            return root.status == 200
        except Exception as e:
            logger.error(f"Redfish probe failed for {host}: {e}")
            return False
        finally:
            if client:
                try:
                    await loop.run_in_executor(None, client.logout)
                except Exception:
                    pass
