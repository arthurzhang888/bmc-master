"""Discovery job schemas."""

from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime


class DiscoveryJobCreate(BaseModel):
    """Schema for creating a discovery job."""
    name: str
    network_range: str  # CIDR format, e.g., "192.168.1.0/24"
    ports: List[int] = [623, 443]  # Default IPMI and Redfish ports


class DiscoveryJobResponse(BaseModel):
    """Schema for discovery job list response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    network_range: str
    ports: List[int]
    status: str
    device_count: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class DiscoveryJobDetail(DiscoveryJobResponse):
    """Schema for detailed discovery job response with found devices."""
    found_devices: List[Dict[str, Any]]
