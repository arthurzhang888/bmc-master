"""BMC Protocol Adapters

This package provides adapters for communicating with BMCs using
either Redfish (modern REST API) or IPMI (legacy protocol).
"""

from .base import BMCAdapter, SensorReading
from .factory import BMCAdapterFactory

__all__ = ["BMCAdapter", "SensorReading", "BMCAdapterFactory"]
