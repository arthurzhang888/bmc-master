"""Bulk operation executor service."""

from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.bulk_job import BulkJob, BulkJobStatus
from app.models.server import Server
from app.adapters.factory import BMCAdapterFactory


class BulkExecutor:
    """批量任务执行器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_power_job(self, job: BulkJob) -> None:
        """执行批量电源任务"""
        job.status = BulkJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        await self.db.commit()

        results = []
        success_count = 0
        fail_count = 0

        # Process in batches of 10
        batch_size = 10
        for i in range(0, len(job.target_servers), batch_size):
            batch = job.target_servers[i:i + batch_size]

            for server_id in batch:
                result = await self._execute_power_action(server_id, job.action)
                results.append(result)

                if result["status"] == "success":
                    success_count += 1
                else:
                    fail_count += 1

            # Update progress after each batch
            job.results = results
            job.success_count = success_count
            job.fail_count = fail_count
            await self.db.commit()

        job.status = BulkJobStatus.COMPLETED if fail_count == 0 else BulkJobStatus.FAILED
        job.completed_at = datetime.utcnow()
        await self.db.commit()

    async def _execute_power_action(self, server_id: str, action: str) -> Dict[str, Any]:
        """执行单台服务器电源操作"""
        result = await self.db.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()

        if not server:
            return {
                "server_id": server_id,
                "status": "failed",
                "message": "Server not found",
                "executed_at": datetime.utcnow().isoformat()
            }

        try:
            adapter, _ = await BMCAdapterFactory.create(
                server.bmc_ip,
                server.bmc_username,
                server.bmc_password
            )

            connected = await adapter.connect()
            if not connected:
                return {
                    "server_id": server_id,
                    "status": "failed",
                    "message": "Failed to connect to BMC",
                    "executed_at": datetime.utcnow().isoformat()
                }

            try:
                # Map action names
                action_map = {
                    "on": "On",
                    "off": "ForceOff",
                    "restart": "ForceRestart",
                    "soft_off": "GracefulShutdown",
                    "soft_restart": "GracefulRestart"
                }
                adapter_action = action_map.get(action, action)

                success = await adapter.set_power(adapter_action)

                return {
                    "server_id": server_id,
                    "status": "success" if success else "failed",
                    "message": f"Power {action} {'succeeded' if success else 'failed'}",
                    "executed_at": datetime.utcnow().isoformat()
                }
            finally:
                await adapter.disconnect()

        except Exception as e:
            return {
                "server_id": server_id,
                "status": "failed",
                "message": str(e),
                "executed_at": datetime.utcnow().isoformat()
            }
