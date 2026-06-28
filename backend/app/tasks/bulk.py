"""Celery tasks for bulk operations."""

import asyncio
from celery import shared_task
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.bulk_job import BulkJob
from app.services.bulk_executor import BulkExecutor


@shared_task
def execute_bulk_job_task(job_id: str):
    """执行批量任务"""
    async def _execute():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "message": "Job not found"}

            executor = BulkExecutor(db)

            if job.job_type.value == "power":
                await executor.execute_power_job(job)
            else:
                job.status = "failed"
                await db.commit()
                return {"status": "error", "message": "Unknown job type"}

            return {"status": "completed", "job_id": job_id}

    return asyncio.run(_execute())
