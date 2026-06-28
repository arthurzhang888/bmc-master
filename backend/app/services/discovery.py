"""Discovery service for auto-discovering BMC devices."""

import asyncio
import ipaddress
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.discovery import DiscoveryJob, DiscoveryStatus
from app.adapters.redfish import RedfishAdapter
from app.adapters.ipmi import IPMIAdapter

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service for network discovery of BMC devices."""

    def __init__(self, db: AsyncSession):
        """Initialize discovery service.

        Args:
            db: Database session
        """
        self.db = db
        self._semaphore = asyncio.Semaphore(50)  # Max 50 concurrent connections

    async def start_discovery(self, discovery_job: DiscoveryJob) -> None:
        """Main discovery workflow.

        Args:
            discovery_job: The discovery job to execute
        """
        try:
            # Update job status to running
            discovery_job.status = DiscoveryStatus.RUNNING
            discovery_job.started_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Starting discovery job {discovery_job.id} for range {discovery_job.network_range}")

            # Perform network scan
            found_devices = await self._scan_network(
                discovery_job.network_range,
                discovery_job.ports
            )

            # Update job with results
            discovery_job.found_devices = found_devices
            discovery_job.device_count = len(found_devices)
            discovery_job.status = DiscoveryStatus.COMPLETED
            discovery_job.completed_at = datetime.utcnow()

            logger.info(f"Discovery job {discovery_job.id} completed. Found {len(found_devices)} devices")

        except Exception as e:
            logger.error(f"Discovery job {discovery_job.id} failed: {e}")
            discovery_job.status = DiscoveryStatus.FAILED
            discovery_job.completed_at = datetime.utcnow()
            raise
        finally:
            await self.db.commit()

    async def _scan_network(self, network_range: str, ports: List[int], batch_size: int = 100) -> List[Dict[str, Any]]:
        """Async network scan with batched processing to avoid memory exhaustion.

        Args:
            network_range: CIDR notation network range (e.g., "192.168.1.0/24")
            ports: List of ports to scan
            batch_size: Number of concurrent probes per batch (default 100)

        Returns:
            List of discovered device information
        """
        try:
            network = ipaddress.ip_network(network_range, strict=False)
        except ValueError as e:
            logger.error(f"Invalid network range {network_range}: {e}")
            raise

        found_devices = []
        current_batch = []

        # Process in batches to avoid creating too many tasks at once
        for ip in network.hosts():
            ip_str = str(ip)
            for port in ports:
                task = self._probe_device_with_limit(ip_str, port)
                current_batch.append(task)

                # When batch is full, execute and collect results
                if len(current_batch) >= batch_size:
                    results = await asyncio.gather(*current_batch, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception):
                            logger.debug(f"Probe failed with exception: {result}")
                            continue
                        if result is not None:
                            found_devices.append(result)
                    current_batch = []

        # Process remaining tasks in final batch
        if current_batch:
            results = await asyncio.gather(*current_batch, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.debug(f"Probe failed with exception: {result}")
                    continue
                if result is not None:
                    found_devices.append(result)

        return found_devices

    async def _probe_device_with_limit(self, ip: str, port: int) -> Optional[Dict[str, Any]]:
        """Wrapper to apply semaphore limit to device probing.

        Args:
            ip: IP address to probe
            port: Port to probe

        Returns:
            Device info if found, None otherwise
        """
        async with self._semaphore:
            return await self._probe_device(ip, port)

    async def _probe_device(self, ip: str, port: int) -> Optional[Dict[str, Any]]:
        """Try to probe a device for BMC protocols.

        Tries Redfish first, then IPMI if Redfish fails.

        Args:
            ip: IP address to probe
            port: Port to probe

        Returns:
            Device info dict with protocol type if successful, None otherwise
        """
        # First check if port is open
        if not await self._is_port_open(ip, port):
            return None

        # Try Redfish first (port 443 typically)
        if port == 443:
            try:
                is_redfish = await RedfishAdapter.probe(ip, "", "")
                if is_redfish:
                    return {
                        "ip": ip,
                        "port": port,
                        "protocol": "redfish",
                        "discovered_at": datetime.utcnow().isoformat()
                    }
            except Exception as e:
                logger.debug(f"Redfish probe failed for {ip}:{port}: {e}")

        # Try IPMI (port 623 typically)
        if port == 623:
            try:
                is_ipmi = await IPMIAdapter.probe(ip, "", "")
                if is_ipmi:
                    return {
                        "ip": ip,
                        "port": port,
                        "protocol": "ipmi",
                        "discovered_at": datetime.utcnow().isoformat()
                    }
            except Exception as e:
                logger.debug(f"IPMI probe failed for {ip}:{port}: {e}")

        # For other ports, try Redfish first then IPMI
        if port not in [443, 623]:
            try:
                is_redfish = await RedfishAdapter.probe(ip, "", "")
                if is_redfish:
                    return {
                        "ip": ip,
                        "port": port,
                        "protocol": "redfish",
                        "discovered_at": datetime.utcnow().isoformat()
                    }
            except Exception:
                pass

            try:
                is_ipmi = await IPMIAdapter.probe(ip, "", "")
                if is_ipmi:
                    return {
                        "ip": ip,
                        "port": port,
                        "protocol": "ipmi",
                        "discovered_at": datetime.utcnow().isoformat()
                    }
            except Exception:
                pass

        return None

    async def _is_port_open(self, ip: str, port: int, timeout: float = 2.0) -> bool:
        """Check if a port is open on the given IP.

        Args:
            ip: IP address to check
            port: Port to check
            timeout: Connection timeout in seconds

        Returns:
            True if port is open, False otherwise
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False
