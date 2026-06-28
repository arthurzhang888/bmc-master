"""Discovery API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.discovery import DiscoveryJob, DiscoveryStatus
from app.schemas.discovery import DiscoveryJobCreate, DiscoveryJobResponse, DiscoveryJobDetail
from app.tasks.discovery import run_discovery_task

router = APIRouter()


@router.post("/scan", response_model=DiscoveryJobResponse)
async def create_discovery_job(
    job_data: DiscoveryJobCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create and start a discovery job.

    Args:
        job_data: Discovery job creation data
        db: Database session

    Returns:
        Created discovery job
    """
    # Validate network range
    import ipaddress
    try:
        ipaddress.ip_network(job_data.network_range, strict=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid network range: {e}")

    # Validate ports
    if not job_data.ports:
        raise HTTPException(status_code=400, detail="At least one port must be specified")

    for port in job_data.ports:
        if port < 1 or port > 65535:
            raise HTTPException(status_code=400, detail=f"Invalid port: {port}")

    # Create discovery job
    job = DiscoveryJob(
        name=job_data.name,
        network_range=job_data.network_range,
        ports=job_data.ports,
        status=DiscoveryStatus.PENDING,
        found_devices=[],
        device_count=0
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Queue the discovery task
    run_discovery_task.delay(str(job.id))

    return job


@router.get("/jobs", response_model=List[DiscoveryJobResponse])
async def list_discovery_jobs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List discovery jobs.

    Args:
        skip: Number of jobs to skip
        limit: Maximum number of jobs to return
        db: Database session

    Returns:
        List of discovery jobs
    """
    result = await db.execute(
        select(DiscoveryJob)
        .order_by(DiscoveryJob.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/jobs/{job_id}", response_model=DiscoveryJobDetail)
async def get_discovery_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get discovery job details with found devices.

    Args:
        job_id: Discovery job ID
        db: Database session

    Returns:
        Discovery job with found devices
    """
    result = await db.execute(
        select(DiscoveryJob).where(DiscoveryJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Discovery job not found")

    return job
