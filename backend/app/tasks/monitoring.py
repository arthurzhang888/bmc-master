import asyncio
from datetime import datetime
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.server import Server
from app.models.sensor import SensorReading
from app.adapters.factory import BMCAdapterFactory


@shared_task(bind=True, max_retries=3)
def collect_server_sensors(self, server_id: str):
    """采集单个服务器的传感器数据"""
    async def _collect():
        async with AsyncSessionLocal() as db:
            # 查询服务器
            from sqlalchemy import select
            result = await db.execute(
                select(Server).where(Server.id == server_id)
            )
            server = result.scalar_one_or_none()

            if not server or server.status.value != "online":
                return {"status": "skipped", "reason": "server not online"}

            try:
                # 创建适配器
                adapter, protocol = await BMCAdapterFactory.create(
                    server.bmc_ip,
                    server.bmc_username,
                    server.bmc_password
                )

                # 连接并获取传感器
                connected = await adapter.connect()
                if not connected:
                    return {"status": "error", "reason": "connection failed"}

                try:
                    readings = await adapter.get_sensors()

                    # 保存到数据库
                    for reading in readings:
                        db_reading = SensorReading(
                            server_id=server_id,
                            sensor_name=reading.name,
                            sensor_type=reading.sensor_type,
                            value=reading.value,
                            unit=reading.unit,
                            recorded_at=reading.timestamp or datetime.utcnow()
                        )
                        db.add(db_reading)

                    await db.commit()
                    return {"status": "success", "count": len(readings)}

                finally:
                    await adapter.disconnect()

            except Exception as e:
                await db.rollback()
                raise self.retry(exc=e, countdown=60)

    return asyncio.run(_collect())


@shared_task
def collect_all_servers_sensors():
    """采集所有在线服务器的传感器数据"""
    async def _collect_all():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Server).where(Server.status.value == "online")
            )
            servers = result.scalars().all()

            for server in servers:
                collect_server_sensors.delay(str(server.id))

            return {"status": "queued", "count": len(servers)}

    return asyncio.run(_collect_all())
