"""Bulk operation schemas."""

from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime


class BulkJobCreate(BaseModel):
    name: str
    job_type: str  # power, ipmi_command
    action: Optional[str] = None  # for power jobs
    command: Optional[str] = None  # for ipmi jobs
    target_servers: List[UUID]


class BulkJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    job_type: str
    action: Optional[str]
    status: str
    target_servers: List[UUID]
    total_count: int
    success_count: int
    fail_count: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class BulkJobDetail(BulkJobResponse):
    results: List[Dict[str, Any]]
