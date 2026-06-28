"""Bulk operation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.bulk_job import BulkJob, BulkJobType, BulkJobStatus
from app.schemas.bulk import BulkJobCreate, BulkJobResponse, BulkJobDetail
from app.services.bulk_executor import BulkExecutor

router = APIRouter()


@router.post("/bulk/power", response_model=BulkJobResponse)
async def create_bulk_power_job(
    job_data: BulkJobCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a bulk power control job"""
    if len(job_data.target_servers) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 servers per batch")

    job = BulkJob(
        name=job_data.name,
        job_type=BulkJobType.POWER,
        action=job_data.action,
        target_servers=[str(s) for s in job_data.target_servers],
        total_count=len(job_data.target_servers),
        status=BulkJobStatus.PENDING
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Queue the job
    from app.tasks.bulk import execute_bulk_job_task
    execute_bulk_job_task.delay(str(job.id))

    return job


@router.get("/bulk/jobs", response_model=List[BulkJobResponse])
async def list_bulk_jobs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List bulk jobs"""
    result = await db.execute(
        select(BulkJob)
        .order_by(BulkJob.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/bulk/jobs/{job_id}", response_model=BulkJobDetail)
async def get_bulk_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get bulk job details with results"""
    result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job
