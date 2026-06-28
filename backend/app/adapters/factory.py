"""Factory for creating BMC adapters."""

from typing import Tuple

from .base import BMCAdapter


class BMCAdapterFactory:
    """Factory class for creating BMC adapters.

    This factory automatically detects which protocol (Redfish or IPMI)
    a BMC supports and returns the appropriate adapter instance.
    """

    @staticmethod
    async def create(host: str, username: str, password: str) -> Tuple[BMCAdapter, str]:
        """Create a BMC adapter for the given host.

        Probes the host to determine which protocol is supported,
        then returns an instance of the appropriate adapter.

        Args:
            host: The hostname or IP address of the BMC
            username: The username for authentication
            password: The password for authentication

        Returns:
            Tuple of (adapter instance, protocol name)
            Protocol name is "redfish" or "ipmi"

        Raises:
            ConnectionError: If neither protocol is supported
        """
        from .redfish import RedfishAdapter
        from .ipmi import IPMIAdapter

        # Try Redfish first (modern protocol)
        if await RedfishAdapter.probe(host, username, password):
            return RedfishAdapter(host, username, password), "redfish"

        # Fall back to IPMI (legacy protocol)
        if await IPMIAdapter.probe(host, username, password):
            return IPMIAdapter(host, username, password), "ipmi"

        raise ConnectionError(
            f"Unable to connect to {host} using either Redfish or IPMI protocol. "
            "Please check the host address and credentials."
        )
