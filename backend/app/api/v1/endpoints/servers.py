from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.server import Server
from app.models.sensor import SensorReading
from app.models.sel import SystemEventLog
from app.schemas.server import ServerCreate, ServerUpdate, ServerResponse
from app.schemas.sel import SELLogResponse


class PowerAction(str, Enum):
    """Valid power control actions."""
    ON = "on"
    OFF = "off"
    SOFT_OFF = "softoff"
    RESET = "reset"
    RESTART = "restart"

router = APIRouter()


@router.get("/servers", response_model=List[ServerResponse])
async def list_servers(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all servers with optional filtering."""
    query = select(Server)
    if status:
        query = query.where(Server.status == status)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/servers", response_model=ServerResponse)
async def create_server(
    server: ServerCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new server."""
    # TODO: Probe protocol and discover server info
    db_server = Server(
        hostname=server.hostname,
        bmc_ip=server.bmc_ip,
        bmc_username=server.bmc_username,
        bmc_password=server.bmc_password,
        vendor=server.vendor,
        model=server.model,
    )
    db.add(db_server)
    await db.commit()
    await db.refresh(db_server)
    return db_server


@router.get("/servers/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific server by ID."""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.put("/servers/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: UUID,
    server_update: ServerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a server."""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    for field, value in server_update.model_dump(exclude_unset=True).items():
        setattr(server, field, value)

    await db.commit()
    await db.refresh(server)
    return server


@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a server."""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    await db.delete(server)
    await db.commit()
    return {"message": "Server deleted"}


@router.post("/servers/{server_id}/power")
async def power_control(
    server_id: UUID,
    action: PowerAction,
    db: AsyncSession = Depends(get_db)
):
    """Control server power."""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    # TODO: Use adapter to control power
    # This is a placeholder implementation
    return {"message": f"Power action {action.value} sent to {server.hostname or server.bmc_ip}"}


@router.get("/servers/{server_id}/sensors")
async def get_sensors(
    server_id: UUID,
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of readings"),
    db: AsyncSession = Depends(get_db)
):
    """Get server sensor readings with time range and pagination."""
    from datetime import datetime, timedelta

    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(SensorReading)
        .where(
            SensorReading.server_id == server_id,
            SensorReading.recorded_at >= since
        )
        .order_by(SensorReading.recorded_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/servers/{server_id}/sel", response_model=List[SELLogResponse])
async def get_server_sel_logs(
    server_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get SEL logs for a specific server."""
    result = await db.execute(
        select(SystemEventLog)
        .where(SystemEventLog.server_id == server_id)
        .order_by(SystemEventLog.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()
