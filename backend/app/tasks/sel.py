from datetime import datetime, timedelta
from celery import shared_task
import asyncio

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.server import Server, ServerStatus
from app.models.sel import SystemEventLog, SELSeverity
from app.adapters.factory import BMCAdapterFactory


@shared_task
def collect_server_sel_logs(server_id: str):
    """采集单个服务器的 SEL 日志"""
    async def _collect():
        async with AsyncSessionLocal() as db:
            # 获取服务器信息
            result = await db.execute(
                select(Server).where(Server.id == server_id)
            )
            server = result.scalar_one_or_none()

            if not server or server.status != ServerStatus.ONLINE:
                return {"status": "skipped", "reason": "server not online"}

            try:
                # 获取最新已采集的时间
                result = await db.execute(
                    select(SystemEventLog)
                    .where(SystemEventLog.server_id == server_id)
                    .order_by(SystemEventLog.timestamp.desc())
                    .limit(1)
                )
                last_entry = result.scalar_one_or_none()
                since = last_entry.timestamp if last_entry else datetime.utcnow() - timedelta(days=7)

                # 创建适配器
                adapter, _ = await BMCAdapterFactory.create(
                    server.bmc_ip,
                    server.bmc_username,
                    server.bmc_password
                )

                connected = await adapter.connect()
                if not connected:
                    return {"status": "error", "reason": "connection failed"}

                try:
                    entries = await adapter.get_sel_logs(since=since)

                    # 保存到数据库
                    count = 0
                    for entry in entries:
                        # Map severity string to enum
                        severity_map = {
                            "critical": SELSeverity.CRITICAL,
                            "warning": SELSeverity.WARNING,
                            "ok": SELSeverity.OK
                        }
                        severity = severity_map.get(entry.severity, SELSeverity.OK)

                        sel_log = SystemEventLog(
                            server_id=server_id,
                            record_id=entry.record_id,
                            timestamp=entry.timestamp,
                            sensor_name=entry.sensor_name,
                            sensor_type=entry.sensor_type,
                            event_direction=entry.event_direction,
                            event_data=entry.event_data,
                            severity=severity
                        )
                        db.add(sel_log)
                        count += 1

                    await db.commit()
                    return {"status": "success", "count": count}

                finally:
                    await adapter.disconnect()

            except Exception as e:
                await db.rollback()
                return {"status": "error", "error": str(e)}

    return asyncio.run(_collect())


@shared_task
def collect_all_sel_logs():
    """采集所有服务器的 SEL 日志"""
    async def _collect_all():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Server).where(Server.status == ServerStatus.ONLINE)
            )
            servers = result.scalars().all()

            for server in servers:
                collect_server_sel_logs.delay(str(server.id))

            return {"status": "queued", "count": len(servers)}

    return asyncio.run(_collect_all())
