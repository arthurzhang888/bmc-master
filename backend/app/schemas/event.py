from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class EventBase(BaseModel):
    event_type: str
    severity: str
    title: str
    message: Optional[str] = None


class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    server_id: Optional[UUID]
    status: str
    acknowledged_by: Optional[UUID]
    acknowledged_at: Optional[datetime]
    created_at: datetime


class EventAcknowledge(BaseModel):
    status: str  # acknowledged / resolved / ignored
