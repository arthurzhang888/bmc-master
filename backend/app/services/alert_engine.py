# backend/app/services/alert_engine.py
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.alert import AlertRule, AlertHistory, AlertSeverity
from app.models.sensor import SensorReading
from app.models.server import Server, ServerStatus
from app.models.event import Event, EventType, EventSeverity
from app.services.notification import NotificationService


class AlertEngine:
    """告警规则评估引擎"""

    def __init__(self, db: AsyncSession, notification_service: Optional[NotificationService] = None):
        self.db = db
        self.notification_service = notification_service or NotificationService()

    async def evaluate_all_rules(self):
        """评估所有启用的告警规则"""
        result = await self.db.execute(
            select(AlertRule).where(AlertRule.enabled == True)
        )
        rules = result.scalars().all()

        for rule in rules:
            await self.evaluate_rule(rule)

    async def evaluate_rule(self, rule: AlertRule):
        """评估单个告警规则"""
        # 获取所有在线服务器
        result = await self.db.execute(
            select(Server).where(Server.status == ServerStatus.ONLINE)
        )
        servers = result.scalars().all()

        for server in servers:
            # 检查持续时间要求
            if rule.duration and rule.duration > 0:
                # 查询持续时间窗口内的所有读数
                since = datetime.utcnow() - timedelta(seconds=rule.duration)
                result = await self.db.execute(
                    select(SensorReading)
                    .where(
                        and_(
                            SensorReading.server_id == server.id,
                            SensorReading.sensor_type == rule.sensor_type,
                            SensorReading.recorded_at >= since
                        )
                    )
                    .order_by(SensorReading.recorded_at.desc())
                )
                readings = result.scalars().all()

                # 需要至少2个读数，且全部超过阈值才算持续 breach
                if len(readings) >= 2 and all(
                    self._check_threshold(r.value, rule) for r in readings
                ):
                    # 使用最新的读数触发告警
                    await self._trigger_alert(rule, server, readings[0])
            else:
                # 无持续时间要求，只检查最新读数
                result = await self.db.execute(
                    select(SensorReading)
                    .where(
                        and_(
                            SensorReading.server_id == server.id,
                            SensorReading.sensor_type == rule.sensor_type
                        )
                    )
                    .order_by(SensorReading.recorded_at.desc())
                    .limit(1)
                )
                reading = result.scalar_one_or_none()

                if reading and self._check_threshold(reading.value, rule):
                    await self._trigger_alert(rule, server, reading)

    def _check_threshold(self, value: float, rule: AlertRule) -> bool:
        """检查阈值条件"""
        ops = {
            ">": lambda v, t: v > t,
            ">=": lambda v, t: v >= t,
            "<": lambda v, t: v < t,
            "<=": lambda v, t: v <= t,
            "==": lambda v, t: v == t,
            "!=": lambda v, t: v != t,
        }
        op_func = ops.get(rule.operator)
        if op_func and rule.threshold is not None:
            return op_func(float(value), float(rule.threshold))
        return False

    async def _trigger_alert(self, rule: AlertRule, server: Server, reading: SensorReading):
        """触发告警"""
        # 检查是否已经存在未解决的相同告警
        result = await self.db.execute(
            select(AlertHistory)
            .where(
                and_(
                    AlertHistory.rule_id == rule.id,
                    AlertHistory.server_id == server.id,
                    AlertHistory.sensor_name == reading.sensor_name,
                    AlertHistory.resolved_at.is_(None)
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return  # 已存在未解决的告警

        # 创建告警历史
        alert = AlertHistory(
            rule_id=rule.id,
            server_id=server.id,
            sensor_name=reading.sensor_name,
            triggered_value=float(reading.value),
            severity=rule.severity
        )
        self.db.add(alert)

        # 创建事件
        event = Event(
            server_id=server.id,
            event_type=EventType.ALERT,
            severity=EventSeverity.WARNING if rule.severity == AlertSeverity.WARNING else EventSeverity.CRITICAL,
            title=f"Alert: {rule.name}",
            message=f"Server {server.hostname or server.bmc_ip}: {reading.sensor_name} = {reading.value} {reading.unit} (threshold: {rule.threshold})"
        )
        self.db.add(event)

        # Send notification
        await self.notification_service.send_alert_notification(rule, server, alert)

        await self.db.commit()
