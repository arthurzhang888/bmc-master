# BMC Master Phase 2 - 高级功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** 实现告警通知系统、SEL 日志收集、事件中心和服务器详情页增强

**Architecture:** 基于 Phase 1 架构，新增告警评估引擎、通知服务、SEL 采集器

**Tech Stack:** FastAPI, Celery, SQLAlchemy, React, ECharts, aiosmtplib

---

## Task 1: 数据库模型与迁移

**Files:**
- Create: `backend/app/models/alert.py` (AlertRule, AlertHistory)
- Create: `backend/app/models/sel.py` (SystemEventLog)
- Create: `backend/app/models/event.py` (Event)
- Modify: `backend/app/models/__init__.py`
- Create: Alembic migration

- [ ] **Step 1: 创建 AlertRule 模型**

```python
# backend/app/models/alert.py
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, Integer, Boolean, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum

class RuleType(str, enum.Enum):
    THRESHOLD = "threshold"
    TREND = "trend"
    PRESENCE = "presence"

class AlertSeverity(str, enum.Enum):
    WARNING = "warning"
    CRITICAL = "critical"

class AlertRule(Base):
    __tablename__ = "alert_rules"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(SQLEnum(RuleType), default=RuleType.THRESHOLD)
    sensor_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    operator: Mapped[str] = mapped_column(String(8), default=">")  # > < == !=
    threshold: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    duration: Mapped[int] = mapped_column(Integer, default=0)  # seconds
    severity: Mapped[AlertSeverity] = mapped_column(SQLEnum(AlertSeverity), default=AlertSeverity.WARNING)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Notification settings
    notify_email: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_webhook: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

class AlertHistory(Base):
    __tablename__ = "alert_history"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alert_rules.id"))
    server_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("servers.id"))
    sensor_name: Mapped[str] = mapped_column(String(128))
    triggered_value: Mapped[float] = mapped_column(Numeric(10, 2))
    severity: Mapped[AlertSeverity] = mapped_column(SQLEnum(AlertSeverity))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

- [ ] **Step 2: 创建 SystemEventLog 模型**

```python
# backend/app/models/sel.py
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum

class SELSeverity(str, enum.Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"

class SystemEventLog(Base):
    __tablename__ = "sel_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"))
    record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sensor_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sensor_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    event_direction: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # Assertion/Deassertion
    event_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[SELSeverity] = mapped_column(SQLEnum(SELSeverity), default=SELSeverity.OK)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Unique constraint to prevent duplicates
    __table_args__ = (
        sa.UniqueConstraint('server_id', 'record_id', 'timestamp', name='uq_sel_record'),
        sa.Index('idx_sel_server_time', 'server_id', 'timestamp'),
    )
```

- [ ] **Step 3: 创建 Event 模型**

```python
# backend/app/models/event.py
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum

class EventType(str, enum.Enum):
    ALERT = "alert"
    SEL = "sel"
    SYSTEM = "system"
    AUDIT = "audit"

class EventSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class EventStatus(str, enum.Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    IGNORED = "ignored"

class Event(Base):
    __tablename__ = "events"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"), nullable=True)
    event_type: Mapped[EventType] = mapped_column(SQLEnum(EventType), nullable=False)
    severity: Mapped[EventSeverity] = mapped_column(SQLEnum(EventSeverity), default=EventSeverity.INFO)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[EventStatus] = mapped_column(SQLEnum(EventStatus), default=EventStatus.NEW)
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

- [ ] **Step 4: 更新 models/__init__.py**

```python
from app.models.alert import AlertRule, AlertHistory
from app.models.sel import SystemEventLog
from app.models.event import Event, EventType, EventSeverity, EventStatus

__all__ = [
    # ... existing exports
    "AlertRule", "AlertHistory",
    "SystemEventLog",
    "Event", "EventType", "EventSeverity", "EventStatus",
]
```

- [ ] **Step 5: 创建 Alembic 迁移**

Run: `cd backend && alembic revision --autogenerate -m "add alert sel event models"`
Run: `alembic upgrade head`

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/ backend/alembic/versions/
git commit -m "feat: add alert, sel, event models"
```

---

## Task 2: 告警评估引擎

**Files:**
- Create: `backend/app/services/alert_engine.py`
- Create: `backend/app/tasks/alerts.py`
- Modify: `backend/app/core/celery.py` to register new tasks

- [ ] **Step 1: 创建告警评估服务**

```python
# backend/app/services/alert_engine.py
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.alert import AlertRule, AlertHistory, AlertSeverity
from app.models.sensor import SensorReading
from app.models.server import Server
from app.models.event import Event, EventType, EventSeverity

class AlertEngine:
    """告警规则评估引擎"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
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
            select(Server).where(Server.status == "online")
        )
        servers = result.scalars().all()
        
        for server in servers:
            # 获取该服务器最新的传感器数据
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
        
        await self.db.commit()
```

- [ ] **Step 2: 创建告警定时任务**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/
git commit -m "feat: add alert evaluation engine"
```

---

## Task 3: 通知服务

**Files:**
- Create: `backend/app/services/notification.py`
- Create: `backend/app/templates/email/alert.html`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 添加依赖**

```
aiosmtplib==3.0.0
jinja2==3.1.0
```

- [ ] **Step 2: 创建通知服务**

```python
# backend/app/services/notification.py
import json
from typing import Optional
import aiohttp
from aiosmtplib import send
from jinja2 import Template

from app.core.config import settings
from app.models.alert import AlertRule, AlertHistory
from app.models.server import Server

class NotificationService:
    """通知服务"""
    
    async def send_alert_notification(
        self,
        rule: AlertRule,
        server: Server,
        alert: AlertHistory
    ):
        """发送告警通知"""
        if rule.notify_email:
            await self._send_email(rule, server, alert)
        
        if rule.notify_webhook and rule.webhook_url:
            await self._send_webhook(rule, server, alert)
    
    async def _send_email(
        self,
        rule: AlertRule,
        server: Server,
        alert: AlertHistory
    ):
        """发送邮件通知"""
        subject = f"[{alert.severity.value.upper()}] BMC Master Alert: {rule.name}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: {'#f59e0b' if alert.severity.value == 'warning' else '#ef4444'};">
                Alert: {rule.name}
            </h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Server:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{server.hostname or server.bmc_ip}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Sensor:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.sensor_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Value:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.triggered_value}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Threshold:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{rule.operator} {rule.threshold}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Time:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.created_at}</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # TODO: Configure SMTP settings from environment
        # await send(
        #     message=html_content,
        #     subject=subject,
        #     sender=settings.SMTP_FROM,
        #     recipients=[settings.ALERT_EMAIL],
        #     hostname=settings.SMTP_HOST,
        #     port=settings.SMTP_PORT,
        # )
    
    async def _send_webhook(
        self,
        rule: AlertRule,
        server: Server,
        alert: AlertHistory
    ):
        """发送 Webhook 通知"""
        if not rule.webhook_url:
            return
        
        payload = {
            "alert_name": rule.name,
            "severity": alert.severity.value,
            "server": {
                "id": str(server.id),
                "hostname": server.hostname,
                "ip": server.bmc_ip
            },
            "sensor": alert.sensor_name,
            "value": float(alert.triggered_value),
            "threshold": float(rule.threshold) if rule.threshold else None,
            "timestamp": alert.created_at.isoformat() if alert.created_at else None
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    rule.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status >= 400:
                        print(f"Webhook failed: {response.status}")
            except Exception as e:
                print(f"Webhook error: {e}")
```

- [ ] **Step 3: Commit**

```bash
git add backend/
git commit -m "feat: add notification service with email and webhook"
```

---

## Task 4: SEL 日志采集

**Files:**
- Create: `backend/app/tasks/sel.py`
- Modify: `backend/app/adapters/base.py` to add get_sel_logs method
- Modify: `backend/app/adapters/redfish.py` and `ipmi.py` to implement SEL collection

- [ ] **Step 1: 更新适配器基类**

```python
# backend/app/adapters/base.py (add to BMCAdapter)
@dataclass
class SELEntry:
    record_id: str
    timestamp: datetime
    sensor_name: Optional[str]
    sensor_type: Optional[str]
    event_direction: Optional[str]  # Assertion/Deassertion
    event_data: Optional[str]
    severity: str  # ok/warning/critical

# Add abstract method to BMCAdapter:
@abstractmethod
async def get_sel_logs(self, since: Optional[datetime] = None) -> List[SELEntry]:
    pass
```

- [ ] **Step 2: 实现 SEL 采集任务**

```python
# backend/app/tasks/sel.py
from datetime import datetime, timedelta
from celery import shared_task
import asyncio

from sqlalchemy import select, and_
from app.core.database import AsyncSessionLocal
from app.models.server import Server
from app.models.sel import SystemEventLog
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
            
            if not server or server.status != "online":
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
                        sel_log = SystemEventLog(
                            server_id=server_id,
                            record_id=entry.record_id,
                            timestamp=entry.timestamp,
                            sensor_name=entry.sensor_name,
                            sensor_type=entry.sensor_type,
                            event_direction=entry.event_direction,
                            event_data=entry.event_data,
                            severity=entry.severity
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
                select(Server).where(Server.status == "online")
            )
            servers = result.scalars().all()
            
            for server in servers:
                collect_server_sel_logs.delay(str(server.id))
            
            return {"status": "queued", "count": len(servers)}
    
    return asyncio.run(_collect_all())
```

- [ ] **Step 3: Commit**

```bash
git add backend/
git commit -m "feat: add SEL log collection tasks"
```

---

## Task 5: 事件 API

**Files:**
- Create: `backend/app/schemas/event.py`
- Create: `backend/app/api/v1/endpoints/events.py`
- Modify: `backend/app/api/v1/api.py` to register router

- [ ] **Step 1: 创建 Event schemas**

```python
# backend/app/schemas/event.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

class EventBase(BaseModel):
    event_type: str
    severity: str
    title: str
    message: Optional[str] = None

class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    server_id: Optional[UUID]
    status: str
    acknowledged_by: Optional[UUID]
    acknowledged_at: Optional[datetime]
    created_at: datetime

class EventAcknowledge(BaseModel):
    status: str  # acknowledged / resolved / ignored
```

- [ ] **Step 2: 创建 Event API**

```python
# backend/app/api/v1/endpoints/events.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.event import Event, EventStatus
from app.schemas.event import EventResponse, EventAcknowledge

router = APIRouter()

@router.get("/events", response_model=List[EventResponse])
async def list_events(
    skip: int = 0,
    limit: int = 100,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    server_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """List events with filtering"""
    query = select(Event).order_by(desc(Event.created_at))
    
    if event_type:
        query = query.where(Event.event_type == event_type)
    if severity:
        query = query.where(Event.severity == severity)
    if status:
        query = query.where(Event.status == status)
    if server_id:
        query = query.where(Event.server_id == server_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/events/{event_id}/ack")
async def acknowledge_event(
    event_id: UUID,
    data: EventAcknowledge,
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge or resolve an event"""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.status = data.status
    if data.status == EventStatus.ACKNOWLEDGED:
        event.acknowledged_at = datetime.utcnow()
        # TODO: Set acknowledged_by from current user
    
    await db.commit()
    await db.refresh(event)
    return event
```

- [ ] **Step 3: Commit**

```bash
git add backend/
git commit -m "feat: add event API endpoints"
```

---

## Task 6: 前端 - 事件中心页面

**Files:**
- Create: `frontend/src/pages/EventCenter.tsx`
- Create: `frontend/src/services/eventApi.ts`
- Modify: `frontend/src/App.tsx` to add route

- [ ] **Step 1: 创建 Event API 客户端**

```typescript
// frontend/src/services/eventApi.ts
import api from './api';

export const eventApi = {
  list: (params?: { event_type?: string; severity?: string; status?: string }) =>
    api.get('/api/v1/events', { params }),
  acknowledge: (id: string, status: string) =>
    api.post(`/api/v1/events/${id}/ack`, { status }),
};
```

- [ ] **Step 2: 创建 EventCenter 页面**

```tsx
// frontend/src/pages/EventCenter.tsx
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { eventApi } from '../services/eventApi';

interface Event {
  id: string;
  event_type: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string | null;
  status: 'new' | 'acknowledged' | 'resolved' | 'ignored';
  created_at: string;
}

const EventCenter: React.FC = () => {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ severity: '', status: '' });

  useEffect(() => {
    loadEvents();
  }, [filter]);

  const loadEvents = async () => {
    try {
      const params: any = {};
      if (filter.severity) params.severity = filter.severity;
      if (filter.status) params.status = filter.status;
      
      const response = await eventApi.list(params);
      setEvents(response.data);
    } catch (err) {
      console.error('Failed to load events:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (id: string, status: string) => {
    try {
      await eventApi.acknowledge(id, status);
      loadEvents();
    } catch (err) {
      console.error('Failed to update event:', err);
    }
  };

  // NOC style (same as Dashboard)
  const containerStyle: React.CSSProperties = {
    backgroundColor: '#0a0e17',
    minHeight: '100vh',
    color: '#e0e6ed',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#ef4444';
      case 'warning': return '#f59e0b';
      default: return '#00d4aa';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new': return '#ef4444';
      case 'acknowledged': return '#f59e0b';
      case 'resolved': return '#00d4aa';
      default: return '#64748b';
    }
  };

  return (
    <div style={containerStyle}>
      <header style={{ padding: '16px 24px', borderBottom: '2px solid #00d4aa', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ color: '#00d4aa', margin: 0 }}>Event Center</h1>
        <Link to="/" style={{ color: '#00d4aa', textDecoration: 'none' }}>← Dashboard</Link>
      </header>

      <div style={{ padding: '24px' }}>
        {/* Filters */}
        <div style={{ marginBottom: '20px', display: 'flex', gap: '16px' }}>
          <select 
            value={filter.severity} 
            onChange={(e) => setFilter({ ...filter, severity: e.target.value })}
            style={{ padding: '8px', backgroundColor: '#111827', color: '#e0e6ed', border: '1px solid #1e3a5f', borderRadius: '4px' }}
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
          
          <select 
            value={filter.status} 
            onChange={(e) => setFilter({ ...filter, status: e.target.value })}
            style={{ padding: '8px', backgroundColor: '#111827', color: '#e0e6ed', border: '1px solid #1e3a5f', borderRadius: '4px' }}
          >
            <option value="">All Status</option>
            <option value="new">New</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>

        {/* Events Table */}
        <div style={{ backgroundColor: '#111827', borderRadius: '8px', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: '#1e3a5f' }}>
                <th style={{ padding: '12px', textAlign: 'left', color: '#00d4aa' }}>Time</th>
                <th style={{ padding: '12px', textAlign: 'left', color: '#00d4aa' }}>Severity</th>
                <th style={{ padding: '12px', textAlign: 'left', color: '#00d4aa' }}>Title</th>
                <th style={{ padding: '12px', textAlign: 'left', color: '#00d4aa' }}>Status</th>
                <th style={{ padding: '12px', textAlign: 'left', color: '#00d4aa' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {events.map(event => (
                <tr key={event.id} style={{ borderBottom: '1px solid #1e3a5f' }}>
                  <td style={{ padding: '12px', color: '#64748b' }}>
                    {new Date(event.created_at).toLocaleString()}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ 
                      color: getSeverityColor(event.severity),
                      textTransform: 'uppercase',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      {event.severity}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    <div style={{ color: '#e0e6ed' }}>{event.title}</div>
                    {event.message && (
                      <div style={{ color: '#64748b', fontSize: '12px', marginTop: '4px' }}>
                        {event.message}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ 
                      color: getStatusColor(event.status),
                      textTransform: 'capitalize'
                    }}>
                      {event.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    {event.status === 'new' && (
                      <button
                        onClick={() => handleAcknowledge(event.id, 'acknowledged')}
                        style={{ 
                          padding: '6px 12px', 
                          backgroundColor: '#f59e0b', 
                          color: '#0a0e17',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          marginRight: '8px'
                        }}
                      >
                        Ack
                      </button>
                    )}
                    {(event.status === 'new' || event.status === 'acknowledged') && (
                      <button
                        onClick={() => handleAcknowledge(event.id, 'resolved')}
                        style={{ 
                          padding: '6px 12px', 
                          backgroundColor: '#00d4aa', 
                          color: '#0a0e17',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        Resolve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default EventCenter;
```

- [ ] **Step 3: 更新 App.tsx**

```tsx
// Add to App.tsx
import EventCenter from './pages/EventCenter';

// Add route:
<Route path="/events" element={<EventCenter />} />
```

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: add EventCenter page"
```

---

## Task 7: 服务器详情页增强

**Files:**
- Create: `frontend/src/pages/ServerDetail.tsx`
- Modify: `frontend/src/pages/ServerList.tsx` to link to detail page
- Modify: `frontend/src/App.tsx` to add route

- [ ] **Step 1: 创建 ServerDetail 页面**

```tsx
// frontend/src/pages/ServerDetail.tsx
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { serverApi } from '../services/api';

const ServerDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [server, setServer] = useState<any>(null);
  const [sensors, setSensors] = useState<any[]>([]);
  const [selLogs, setSelLogs] = useState<any[]>([]);
  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    if (id) {
      loadServerData();
    }
  }, [id, timeRange]);

  const loadServerData = async () => {
    try {
      const [serverRes, sensorsRes] = await Promise.all([
        serverApi.get(id!),
        serverApi.sensors(id!)
      ]);
      setServer(serverRes.data);
      setSensors(sensorsRes.data);
    } catch (err) {
      console.error('Failed to load server data:', err);
    }
  };

  const containerStyle: React.CSSProperties = {
    backgroundColor: '#0a0e17',
    minHeight: '100vh',
    color: '#e0e6ed',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  };

  const chartOption = {
    backgroundColor: 'transparent',
    title: { text: 'Temperature History', textStyle: { color: '#00d4aa' } },
    xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: '#64748b' } } },
    yAxis: { type: 'value', axisLine: { lineStyle: { color: '#64748b' } } },
    series: [{
      data: sensors.filter(s => s.sensor_type === 'temperature').map(s => s.value),
      type: 'line',
      smooth: true,
      lineStyle: { color: '#00d4aa' }
    }]
  };

  if (!server) {
    return <div style={containerStyle}>Loading...</div>;
  }

  return (
    <div style={containerStyle}>
      <header style={{ padding: '16px 24px', borderBottom: '2px solid #00d4aa', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ color: '#00d4aa', margin: 0 }}>{server.hostname || server.bmc_ip}</h1>
          <div style={{ color: '#64748b', fontSize: '14px' }}>{server.bmc_ip} | {server.vendor} {server.model}</div>
        </div>
        <Link to="/servers" style={{ color: '#00d4aa', textDecoration: 'none' }}>← Back to Servers</Link>
      </header>

      <div style={{ padding: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Sensor Charts */}
        <div style={{ backgroundColor: '#111827', padding: '20px', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h3 style={{ color: '#00d4aa', margin: 0 }}>Sensor Trends</h3>
            <select 
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              style={{ padding: '8px', backgroundColor: '#0a0e17', color: '#e0e6ed', border: '1px solid #1e3a5f', borderRadius: '4px' }}
            >
              <option value="1h">Last 1 hour</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
            </select>
          </div>
          <ReactECharts option={chartOption} style={{ height: '300px' }} />
        </div>

        {/* Current Sensors */}
        <div style={{ backgroundColor: '#111827', padding: '20px', borderRadius: '8px' }}>
          <h3 style={{ color: '#00d4aa', marginTop: 0 }}>Current Readings</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
            {sensors.map(sensor => (
              <div key={sensor.id} style={{ backgroundColor: '#0a0e17', padding: '16px', borderRadius: '8px' }}>
                <div style={{ color: '#64748b', fontSize: '12px' }}>{sensor.sensor_name}</div>
                <div style={{ color: '#00d4aa', fontSize: '24px', fontWeight: 'bold' }}>
                  {sensor.value} <span style={{ fontSize: '14px' }}>{sensor.unit}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SEL Logs */}
        <div style={{ backgroundColor: '#111827', padding: '20px', borderRadius: '8px', gridColumn: '1 / -1' }}>
          <h3 style={{ color: '#00d4aa', marginTop: 0 }}>System Event Logs (SEL)</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #1e3a5f' }}>
                <th style={{ textAlign: 'left', padding: '12px', color: '#64748b' }}>Time</th>
                <th style={{ textAlign: 'left', padding: '12px', color: '#64748b' }}>Sensor</th>
                <th style={{ textAlign: 'left', padding: '12px', color: '#64748b' }}>Event</th>
                <th style={{ textAlign: 'left', padding: '12px', color: '#64748b' }}>Severity</th>
              </tr>
            </thead>
            <tbody>
              {selLogs.map(log => (
                <tr key={log.id} style={{ borderBottom: '1px solid #1e3a5f' }}>
                  <td style={{ padding: '12px' }}>{new Date(log.timestamp).toLocaleString()}</td>
                  <td style={{ padding: '12px' }}>{log.sensor_name}</td>
                  <td style={{ padding: '12px' }}>{log.event_data}</td>
                  <td style={{ padding: '12px', color: log.severity === 'critical' ? '#ef4444' : log.severity === 'warning' ? '#f59e0b' : '#00d4aa' }}>
                    {log.severity}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ServerDetail;
```

- [ ] **Step 2: 更新 App.tsx**

```tsx
// Add to App.tsx
import ServerDetail from './pages/ServerDetail';

// Add route:
<Route path="/servers/:id" element={<ServerDetail />} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "feat: add ServerDetail page with sensor charts and SEL logs"
```

---

## Task 8: 集成与测试

**Files:**
- Modify: `backend/app/main.py` - add new routers
- Modify: `docker-compose.yml` - ensure services are configured
- Create: README.md with setup instructions

- [ ] **Step 1: 更新 main.py**

```python
# Add to backend/app/main.py
from app.api.v1.endpoints import events

app.include_router(events.router, prefix=settings.API_V1_STR)
```

- [ ] **Step 2: 更新 docker-compose.yml** (添加 Celery beat schedule)

```yaml
# Add environment variables for celery beat
 celery-beat:
   environment:
     # ... existing env vars
     CELERY_BEAT_SCHEDULE: |
       {
         "collect-sensors": {"task": "app.tasks.monitoring.collect_all_servers_sensors", "schedule": 30.0},
         "collect-sel": {"task": "app.tasks.sel.collect_all_sel_logs", "schedule": 300.0},
         "evaluate-alerts": {"task": "app.tasks.alerts.evaluate_alert_rules", "schedule": 60.0}
       }
```

- [ ] **Step 3: Commit 并总结**

```bash
git add backend/ docker-compose.yml
git commit -m "feat: integrate Phase 2 features"
```

---

**Phase 2 计划完成！**

现在可以开始实施，需要从 Task 1 开始吗？