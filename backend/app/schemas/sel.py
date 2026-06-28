from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class SELLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    server_id: UUID
    record_id: str
    event_type: Optional[str]
    timestamp: datetime
    sensor_name: Optional[str]
    sensor_type: Optional[str]
    event_direction: Optional[str]
    event_data: Optional[str]
    severity: str
    raw_data: Optional[dict]
