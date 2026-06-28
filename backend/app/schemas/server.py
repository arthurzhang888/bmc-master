from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class ServerBase(BaseModel):
    hostname: Optional[str] = None
    bmc_ip: str
    bmc_username: str
    vendor: Optional[str] = None
    model: Optional[str] = None


class ServerCreate(ServerBase):
    bmc_password: str


class ServerUpdate(BaseModel):
    hostname: Optional[str] = None
    bmc_username: Optional[str] = None
    bmc_password: Optional[str] = None


class ServerInDB(ServerBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    protocol: str
    status: str
    power_state: str
    last_seen_at: Optional[datetime]
    created_at: datetime


class ServerResponse(ServerInDB):
    pass
