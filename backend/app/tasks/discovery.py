import asyncio
import ipaddress
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.server import Server, ServerStatus, PowerState
from app.models.discovery import DiscoveryJob
from app.adapters.factory import BMCAdapterFactory
from app.services.discovery import DiscoveryService


@shared_task(bind=True, max_retries=2)
def discover_single_ip(self, ip: str, username: str, password: str):
    """探测单个 IP 是否为 BMC 服务器"""
    async def _discover():
        async with AsyncSessionLocal() as db:
            # 检查是否已存在
            from sqlalchemy import select
            result = await db.execute(
                select(Server).where(Server.bmc_ip == ip)
            )
            if result.scalar_one_or_none():
                return {"status": "exists", "ip": ip}

            try:
                # 尝试协议探测
                adapter, protocol = await BMCAdapterFactory.create(
                    ip, username, password
                )

                connected = await adapter.connect()
                if not connected:
                    return {"status": "unreachable", "ip": ip}

                try:
                    # 获取服务器信息
                    sensors = await adapter.get_sensors()
                    power = await adapter.get_power_status()

                    # 创建服务器记录
                    server = Server(
                        bmc_ip=ip,
                        bmc_username=username,
                        bmc_password=password,
                        protocol=protocol,
                        status=ServerStatus.ONLINE,
                        power_state=PowerState(power.lower()) if power else PowerState.UNKNOWN
                    )
                    db.add(server)
                    await db.commit()

                    return {"status": "discovered", "ip": ip, "protocol": protocol}

                finally:
                    await adapter.disconnect()

            except Exception as e:
                return {"status": "error", "ip": ip, "error": str(e)}

    return asyncio.run(_discover())


@shared_task
def scan_network_range(network_range: str, username: str, password: str):
    """扫描网段发现 BMC 服务器"""
    try:
        network = ipaddress.ip_network(network_range, strict=False)
        for ip in network.hosts():
            discover_single_ip.delay(str(ip), username, password)

        return {"status": "scanning", "range": network_range, "hosts": network.num_addresses - 2}
    except ValueError as e:
        return {"status": "error", "error": str(e)}


@shared_task
def run_discovery_task(job_id: str):
    """Async task to run discovery job.

    Args:
        job_id: The discovery job ID to run
    """
    async def _execute():
        async with AsyncSessionLocal() as db:
            # Get the discovery job
            result = await db.execute(
                select(DiscoveryJob).where(DiscoveryJob.id == job_id)
            )
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "message": "Discovery job not found"}

            # Run discovery
            service = DiscoveryService(db)
            await service.start_discovery(job)

            return {
                "status": "completed",
                "job_id": job_id,
                "devices_found": job.device_count
            }

    return asyncio.run(_execute())
