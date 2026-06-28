from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.event import Event, EventStatus
from app.schemas.event import EventResponse, EventAcknowledge

router = APIRouter()


@router.get("/events", response_model=List[EventResponse])
async def list_events(
    skip: int = 0,
    limit: int = 100,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    server_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """List events with filtering"""
    query = select(Event).order_by(desc(Event.created_at))

    if event_type:
        query = query.where(Event.event_type == event_type)
    if severity:
        query = query.where(Event.severity == severity)
    if status:
        query = query.where(Event.status == status)
    if server_id:
        query = query.where(Event.server_id == server_id)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/events/{event_id}/ack")
async def acknowledge_event(
    event_id: UUID,
    data: EventAcknowledge,
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge or resolve an event"""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Update status
    try:
        event.status = EventStatus(data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data.status}")

    if event.status == EventStatus.ACKNOWLEDGED:
        event.acknowledged_at = datetime.utcnow()
        # TODO: Set acknowledged_by from current user when auth is implemented

    await db.commit()
    await db.refresh(event)
    return EventResponse.model_validate(event)
