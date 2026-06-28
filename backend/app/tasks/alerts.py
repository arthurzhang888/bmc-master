# backend/app/tasks/alerts.py
from celery import shared_task
import asyncio

from app.core.database import AsyncSessionLocal
from app.services.alert_engine import AlertEngine


@shared_task
def evaluate_alert_rules():
    """定时评估所有告警规则"""
    async def _evaluate():
        async with AsyncSessionLocal() as db:
            engine = AlertEngine(db)
            await engine.evaluate_all_rules()

    asyncio.run(_evaluate())
