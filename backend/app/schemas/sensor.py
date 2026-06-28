from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class SensorReadingBase(BaseModel):
    sensor_name: str
    sensor_type: str
    value: float
    unit: str


class SensorReadingCreate(SensorReadingBase):
    server_id: UUID


class SensorReadingInDB(SensorReadingBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    server_id: UUID
    status: str
    recorded_at: datetime


class SensorReadingResponse(SensorReadingInDB):
    pass
