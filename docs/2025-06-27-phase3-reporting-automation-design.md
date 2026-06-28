# BMC Master Phase 3 - 报表与自动化运维设计文档

**日期**: 2025-06-27  
**版本**: v1.0  
**依赖**: Phase 1 核心功能, Phase 2 高级功能

---

## 1. 概述

### 1.1 目标
在 Phase 1 和 Phase 2 基础上，增加报表分析能力和自动化运维功能，提升系统的运营价值。

### 1.2 功能范围

| 模块 | 功能 | 优先级 |
|-----|------|--------|
| **报表与数据分析** | 传感器历史趋势、告警统计、服务器在线率 | P0 |
| | 性能预测、能耗分析、异常检测 | P1 |
| | PDF/Excel/CSV 导出 | P0 |
| **自动化运维** | 批量操作（电源/IPMI命令） | P0 |
| | 自动发现（网段扫描、协议识别） | P1 |
| | 定时任务编排 | P2 |

---

## 2. 报表与数据分析模块

### 2.1 核心报表

#### 传感器历史趋势报表
```python
class SensorTrendReport(BaseModel):
    server_id: UUID
    sensor_type: str  # Temperature, Voltage, Fan, etc.
    time_range: str   # 1h, 24h, 7d, 30d
    data_points: List[SensorDataPoint]
    statistics: SensorStatistics  # min, max, avg, std_dev

class SensorDataPoint(BaseModel):
    timestamp: datetime
    value: float
    unit: str
```

**功能**:
- 按时间范围查询传感器历史数据
- 生成折线图数据
- 计算统计指标（最小值、最大值、平均值、标准差）
- 支持多传感器对比

#### 告警统计报表
```python
class AlertStatisticsReport(BaseModel):
    total_alerts: int
    by_server: Dict[UUID, int]
    by_type: Dict[str, int]  # temperature, voltage, etc.
    by_severity: Dict[str, int]  # warning, critical
    by_time_period: List[TimePeriodCount]
    resolution_time_avg: float  # 平均解决时间（分钟）
```

**功能**:
- 告警总数统计
- 按服务器、类型、严重程度分组
- 时间趋势分析
- 解决效率分析

#### 服务器在线率报表
```python
class ServerUptimeReport(BaseModel):
    server_id: UUID
    period: str  # 7d, 30d, 90d
    uptime_percentage: float
    offline_events: List[OfflineEvent]
    mtbf: float  # 平均故障间隔时间
    mttr: float  # 平均修复时间
```

### 2.2 高级分析

#### 性能预测
- 基于时间序列分析预测传感器趋势
- 预测何时可能触发告警阈值
- 提供维护建议

#### 能耗分析
- 电力消耗趋势（基于 Power 传感器）
- 按服务器/机架/数据中心的能耗统计
- 节能优化建议

#### 异常检测
- 使用统计方法检测异常传感器读数
- Z-score 算法识别离群值
- 自动创建事件

### 2.3 导出功能

| 格式 | 用途 | 实现方式 |
|------|------|----------|
| PDF | 汇报、存档 | ReportLab / WeasyPrint |
| Excel | 数据分析 | openpyxl |
| CSV | 数据交换 | 标准库 csv |

**API 设计**:
```
POST /api/v1/reports/sensor-trend/export
  - format: pdf | excel | csv
  - server_id: UUID
  - sensor_type: str
  - time_range: str
```

---

## 3. 自动化运维模块

### 3.1 批量操作

#### 批量电源控制
```python
class BulkPowerJob(BaseModel):
    id: UUID
    name: str
    action: PowerAction  # on, off, restart
    target_servers: List[UUID]
    status: JobStatus  # pending, running, completed, failed
    results: List[ServerJobResult]
    created_at: datetime
    completed_at: Optional[datetime]

class ServerJobResult(BaseModel):
    server_id: UUID
    status: str  # success, failed, skipped
    message: Optional[str]
    executed_at: datetime
```

**执行流程**:
1. 创建批量任务（验证目标服务器）
2. Celery 分批执行（每批最多 10 台）
3. 实时更新执行状态
4. 生成执行报告

#### 批量 IPMI 命令
```python
class BulkIPMIJob(BaseModel):
    id: UUID
    name: str
    command: str  # 原始 IPMI 命令
    target_servers: List[UUID]
    status: JobStatus
    results: List[ServerCommandResult]
```

**安全限制**:
- 只允许白名单中的安全命令
- 禁止修改 BMC 配置的命令
- 记录所有执行的命令用于审计

### 3.2 自动发现

#### 网段扫描
```python
class DiscoveryJob(BaseModel):
    id: UUID
    network_range: str  # 192.168.1.0/24
    ports: List[int]    # 623 (IPMI), 443 (Redfish)
    status: JobStatus
    found_devices: List[DiscoveredDevice]
    started_at: datetime
    completed_at: Optional[datetime]

class DiscoveredDevice(BaseModel):
    ip_address: str
    port: int
    protocol: Protocol  # redfish, ipmi, unknown
    vendor: Optional[str]
    model: Optional[str]
    is_already_managed: bool
```

**扫描流程**:
1. 异步扫描网段中的活跃主机
2. 探测端口 623 (IPMI) 和 443 (Redfish)
3. 尝试获取设备信息（不验证凭据）
4. 显示发现结果，用户选择添加到系统

#### 协议识别
- 自动检测 Redfish/IPMI 协议
- 尝试获取基本设备信息
- 记录协议版本和能力

### 3.3 定时任务编排

#### 任务定义
```python
class ScheduledTask(BaseModel):
    id: UUID
    name: str
    task_type: TaskType  # power_control, sensor_collect, custom_command
    schedule: str  # Cron 表达式
    parameters: Dict[str, Any]
    target_servers: List[UUID]
    is_enabled: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    run_count: int
    fail_count: int
```

#### 任务类型
| 类型 | 描述 |
|------|------|
| power_control | 定时开关机 |
| sensor_collect | 定时采集传感器（高频率）|
| sel_collect | 定时采集 SEL 日志 |
| custom_command | 自定义 IPMI 命令 |

#### 任务依赖
```python
class TaskDependency(BaseModel):
    task_id: UUID
    depends_on_task_id: UUID
    condition: DependencyCondition  # on_success, on_failure, always
```

**使用场景**:
- 任务 A 成功后才执行任务 B
- 批量关机 → 维护 → 批量开机

---

## 4. 数据库模型

### 4.1 新增表

```sql
-- 批量任务表
CREATE TABLE bulk_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL,
    job_type VARCHAR(32) NOT NULL,  -- power, ipmi_command
    action VARCHAR(32),
    command TEXT,
    status VARCHAR(32) DEFAULT 'pending',
    target_servers UUID[] NOT NULL,
    results JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- 自动发现任务表
CREATE TABLE discovery_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    network_range VARCHAR(64) NOT NULL,
    ports INTEGER[] DEFAULT '{623,443}',
    status VARCHAR(32) DEFAULT 'pending',
    found_devices JSONB DEFAULT '[]',
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 定时任务表
CREATE TABLE scheduled_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL,
    task_type VARCHAR(32) NOT NULL,
    schedule VARCHAR(64) NOT NULL,  -- Cron 表达式
    parameters JSONB DEFAULT '{}',
    target_servers UUID[] NOT NULL,
    is_enabled BOOLEAN DEFAULT true,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    run_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0
);

-- 报表配置表
CREATE TABLE report_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL,
    report_type VARCHAR(32) NOT NULL,  -- sensor_trend, alert_stats, uptime
    parameters JSONB DEFAULT '{}',
    schedule VARCHAR(64),  -- 可选的定时生成
    last_generated_at TIMESTAMP
);
```

---

## 5. API 设计

### 5.1 报表 API

```
GET  /api/v1/reports/sensor-trend           # 传感器趋势报表
GET  /api/v1/reports/alert-statistics       # 告警统计报表
GET  /api/v1/reports/server-uptime          # 服务器在线率报表
POST /api/v1/reports/export                 # 导出报表
GET  /api/v1/reports/anomalies              # 异常检测结果
GET  /api/v1/reports/predictions            # 性能预测
```

### 5.2 自动化 API

```
POST /api/v1/bulk/power                     # 创建批量电源任务
POST /api/v1/bulk/ipmi-command              # 创建批量 IPMI 任务
GET  /api/v1/bulk/jobs                      # 列表批量任务
GET  /api/v1/bulk/jobs/{id}                 # 获取任务详情
GET  /api/v1/bulk/jobs/{id}/results         # 获取执行结果

POST /api/v1/discovery/scan                 # 启动网段扫描
GET  /api/v1/discovery/jobs                 # 扫描任务列表
GET  /api/v1/discovery/jobs/{id}/devices    # 发现的设备
POST /api/v1/discovery/devices/{id}/import  # 导入设备到系统

GET    /api/v1/scheduler/tasks              # 定时任务列表
POST   /api/v1/scheduler/tasks              # 创建定时任务
PUT    /api/v1/scheduler/tasks/{id}         # 更新定时任务
DELETE /api/v1/scheduler/tasks/{id}         # 删除定时任务
POST   /api/v1/scheduler/tasks/{id}/toggle  # 启用/禁用任务
GET    /api/v1/scheduler/tasks/{id}/history # 执行历史
```

---

## 6. 前端设计

### 6.1 新增页面

- **Reports.tsx** - 报表中心，选择报表类型和参数
- **ReportViewer.tsx** - 报表查看器，显示图表和数据
- **BulkOperations.tsx** - 批量操作页面
- **Discovery.tsx** - 自动发现和导入
- **Scheduler.tsx** - 定时任务管理

### 6.2 组件

- **ReportChart.tsx** - 报表图表（基于 ECharts）
- **BulkJobTable.tsx** - 批量任务状态表格
- **DeviceDiscoveryTable.tsx** - 发现的设备列表
- **CronScheduleInput.tsx** - Cron 表达式输入器
- **ExportButton.tsx** - 导出按钮（支持多种格式）

---

## 7. 技术实现

### 7.1 新增依赖

```python
# backend/requirements.txt 新增
pandas==2.1.0          # 数据分析
numpy==1.24.0          # 数值计算
openpyxl==3.1.0        # Excel 导出
reportlab==4.0.0       # PDF 生成
python-crontab==3.0.0  # Cron 解析
scapy==2.5.0           # 网络扫描（可选）
```

### 7.2 Celery 任务

```python
# 新增 Celery 任务
@celery_app.task
def execute_bulk_power_job(job_id: str):
    """执行批量电源任务"""
    pass

@celery_app.task
def execute_discovery_scan(job_id: str):
    """执行网段扫描"""
    pass

@celery_app.task
def generate_scheduled_report(template_id: str):
    """生成定时报表"""
    pass
```

---

## 8. 安全考虑

### 8.1 批量操作安全
- 限制单次批量操作的服务器数量（最多 50 台）
- 敏感操作需要二次确认
- 记录所有批量操作日志

### 8.2 自动发现安全
- 仅扫描配置的网段，避免扫描外部网络
- 不尝试暴力破解 BMC 凭据
- 发现结果仅管理员可见

### 8.3 定时任务安全
- 限制可执行的命令白名单
- 任务执行超时控制
- 失败任务自动告警

---

**文档结束**
