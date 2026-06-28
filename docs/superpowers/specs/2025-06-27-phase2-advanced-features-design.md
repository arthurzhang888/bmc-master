# BMC Master Phase 2 - 高级功能设计文档

**日期**: 2025-06-27  
**版本**: v1.0  
**依赖**: Phase 1 核心功能

---

## 1. 概述

### 1.1 目标
在 Phase 1 核心功能基础上，增加告警通知、日志分析和事件管理能力，提升系统的运维价值。

### 1.2 功能范围

| 功能模块 | 描述 | 优先级 |
|---------|------|--------|
| 告警通知系统 | 温度/电压异常、硬件故障告警，支持邮件/钉钉/Webhook | P0 |
| SEL 日志收集 | 系统事件日志自动采集与存储 | P0 |
| 事件中心 | 告警管理、确认、历史查询 | P1 |
| 服务器详情页 | 传感器历史趋势、SEL 日志展示 | P1 |

---

## 2. 告警通知系统

### 2.1 告警规则

```python
class AlertRule(Base):
    """告警规则配置"""
    __tablename__ = "alert_rules"
    
    id: UUID
    name: str                    # 规则名称
    rule_type: Enum              # threshold / trend / presence
    sensor_type: str             # temperature / voltage / fan
    operator: str                # > / < / == / !=
    threshold: float             # 阈值
    duration: int                # 持续时间(秒)
    severity: str                # warning / critical
    enabled: bool
    
    # 通知配置
    notify_email: bool
    notify_webhook: bool
    webhook_url: str
```

### 2.2 告警评估流程

```
传感器数据采集 → 规则匹配 → 持续时间检查 → 生成告警事件 → 发送通知
```

### 2.3 通知渠道

**邮件通知:**
- SMTP 配置
- HTML 邮件模板
- 告警级别颜色区分

**钉钉通知:**
- Webhook 机器人
- Markdown 格式消息
- @指定用户

**通用 Webhook:**
- POST JSON 数据
- 可配置 Headers
- 签名验证

---

## 3. SEL 日志收集

### 3.1 数据模型

```python
class SystemEventLog(Base):
    """IPMI SEL / Redfish LogEntry"""
    __tablename__ = "sel_logs"
    
    id: UUID
    server_id: UUID
    record_id: str               # SEL Record ID
    event_type: str              # System Event / OEM
    timestamp: datetime
    sensor_name: str
    sensor_type: str
    event_direction: str         # Assertion / Deassertion
    event_data: str
    severity: str                # OK / Warning / Critical
    raw_data: JSONB              # 原始数据
```

### 3.2 采集策略

- **频率**: 每 5 分钟轮询一次
- **去重**: 基于 record_id + timestamp
- **保留**: 90 天自动清理

---

## 4. 事件中心

### 4.1 事件类型

```python
class EventType(str, Enum):
    ALERT = "alert"              # 阈值告警
    SEL = "sel"                  # SEL 事件
    SYSTEM = "system"            # 系统事件(上下线)
    AUDIT = "audit"              # 操作审计
```

### 4.2 事件状态

```python
class EventStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    IGNORED = "ignored"
```

### 4.3 API 设计

```
GET  /api/v1/events              # 事件列表(支持过滤)
PUT  /api/v1/events/{id}/ack     # 确认事件
PUT  /api/v1/events/{id}/resolve # 解决事件
```

---

## 5. 服务器详情页增强

### 5.1 传感器历史趋势

- ECharts 折线图
- 时间范围选择(1h/24h/7d)
- 多传感器对比

### 5.2 SEL 日志展示

- 表格形式展示
- 严重程度颜色标识
- 原始数据展开查看

---

## 6. 技术实现

### 6.1 新增依赖

```python
# backend/requirements.txt 新增
aiosmtplib==3.0.0      # 异步邮件发送
jinja2==3.1.0          # 邮件模板
```

### 6.2 定时任务

```python
# 新增 Celery 任务
@celery_app.task
def evaluate_alert_rules():
    """评估所有告警规则"""
    pass

@celery_app.task  
def collect_sel_logs():
    """收集 SEL 日志"""
    pass
```

### 6.3 前端组件

```typescript
// 新增页面
- EventCenter.tsx      # 事件中心
- ServerDetail.tsx     # 服务器详情(增强)
- AlertRules.tsx       # 告警规则配置

// 新增组件
- SensorChart.tsx      # 传感器趋势图
- SELLogTable.tsx      # SEL 日志表格
- NotificationSettings.tsx  # 通知设置
```

---

## 7. 数据库迁移

```sql
-- 告警规则表
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL,
    rule_type VARCHAR(32) NOT NULL,
    sensor_type VARCHAR(32),
    operator VARCHAR(8),
    threshold DECIMAL(10,2),
    duration INTEGER DEFAULT 0,
    severity VARCHAR(16) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    notify_email BOOLEAN DEFAULT false,
    notify_webhook BOOLEAN DEFAULT false,
    webhook_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- SEL 日志表
CREATE TABLE sel_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_id UUID REFERENCES servers(id) ON DELETE CASCADE,
    record_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(32),
    timestamp TIMESTAMP NOT NULL,
    sensor_name VARCHAR(128),
    sensor_type VARCHAR(32),
    event_direction VARCHAR(32),
    event_data TEXT,
    severity VARCHAR(16),
    raw_data JSONB,
    UNIQUE(server_id, record_id, timestamp)
);

-- 事件表
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_id UUID REFERENCES servers(id) ON DELETE CASCADE,
    event_type VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    title VARCHAR(256) NOT NULL,
    message TEXT,
    status VARCHAR(32) DEFAULT 'new',
    acknowledged_by UUID,
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

**文档结束**
