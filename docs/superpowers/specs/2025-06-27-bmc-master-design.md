# BMC Master - 服务器带外管理系统设计文档

**日期**: 2025-06-27  
**版本**: v1.0  
**状态**: 设计完成，待实现

---

## 1. 项目概述

### 1.1 项目背景
企业数据中心需要一套统一的服务器 BMC (Baseboard Management Controller) 管理系统，用于集中管理 Dell、HPE、Supermicro 等主流品牌服务器的带外管理功能。

### 1.2 目标用户
- 企业内部运维团队
- 用户规模 < 50 人
- 内网部署，无需公网访问

### 1.3 核心功能范围

| 功能模块 | 描述 | Phase |
|---------|------|-------|
| 资产发现 | 自动扫描网段发现 BMC 服务器，识别厂商型号 | 1 |
| 带外管理 | 远程开关机、硬重启、查看电源状态 | 1 |
| 硬件监控 | CPU/内存/硬盘/风扇温度、电压实时采集 | 1 |
| 远程控制台 | 浏览器内嵌 KVM-over-IP (Sol) | 2 |
| 固件管理 | 批量 BMC/BIOS 固件更新 | 3 |
| 告警通知 | 温度异常、硬件故障事件通知 | 2 |
| 日志分析 | SEL 系统事件日志收集与分析 | 2 |
| 权限管理 | 简单 RBAC (管理员/操作员/只读) | 3 |

---

## 2. 技术架构

### 2.1 技术栈选型

**方案**: Python FastAPI + React (推荐)

| 层级 | 技术 | 理由 |
|-----|------|------|
| 前端 | React 18 + ECharts + WebSocket | 工业控制台风格，实时图表 |
| 后端 | FastAPI (Python) | 原生异步支持，自动生成 API 文档 |
| 数据库 | PostgreSQL 16 | 关系型数据，JSONB 支持 |
| 缓存/队列 | Redis 7 | 实时数据缓存、Celery 任务队列 |
| 任务调度 | Celery + Celery Beat | 定时任务、异步执行 |
| 部署 | Docker Compose | 单机一键部署 |

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (React)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │  Dashboard  │ │ Server List │ │ Real-time Charts    │   │
│  │  仪表盘      │ │ 服务器列表   │ │ 实时图表            │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↕ HTTP / WebSocket
┌─────────────────────────────────────────────────────────────┐
│                     API 层 (FastAPI)                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │ REST API    │ │ WebSocket   │ │ JWT Auth            │   │
│  │ 资源接口     │ │ 实时推送     │ │ 认证授权            │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                   业务服务层 (Services)                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐ │
│  │ Discovery   │ │ Monitoring  │ │ Control     │ │ Alert  │ │
│  │ 资产发现     │ │ 监控采集     │ │ 电源控制     │ │ 告警   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↕ 协议抽象
┌─────────────────────────────────────────────────────────────┐
│                   协议适配层 (Adapters)                       │
│  ┌─────────────────┐         ┌─────────────────────────┐   │
│  │ RedfishAdapter  │         │ IPMIAdapter             │   │
│  │ (优先尝试)       │◄───────►│ (自动回退)               │   │
│  │ python-redfish  │         │ pyghmi                  │   │
│  └─────────────────┘         └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↕ IPMI 2.0 / Redfish API
┌─────────────────────────────────────────────────────────────┐
│                    被管理服务器 BMC                          │
│        Dell iDRAC / HPE iLO / Supermicro / 华为 iBMC        │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 协议适配器设计

```python
# 抽象基类
class BMCAdapter(ABC):
    @abstractmethod
    async def get_power_status(self) -> PowerStatus: ...
    @abstractmethod
    async def set_power(self, action: PowerAction) -> bool: ...
    @abstractmethod
    async def get_sensors(self) -> List[SensorReading]: ...
    @abstractmethod
    async def get_sel_logs(self) -> List[SELEntry]: ...

# 工厂自动探测
class BMCAdapterFactory:
    @staticmethod
    async def create(host, username, password) -> BMCAdapter:
        if await RedfishAdapter.probe(host):
            return RedfishAdapter(host, username, password)
        return IPMIAdapter(host, username, password)
```

---

## 3. 数据模型

### 3.1 核心实体

**servers (服务器主表)**
```sql
CREATE TABLE servers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname VARCHAR(128),
    bmc_ip INET NOT NULL UNIQUE,
    bmc_username VARCHAR(64) NOT NULL,
    bmc_password TEXT NOT NULL,  -- 加密存储
    protocol VARCHAR(16),  -- redfish / ipmi
    vendor VARCHAR(32),
    model VARCHAR(64),
    status VARCHAR(16) DEFAULT 'offline',  -- online/offline/error
    power_state VARCHAR(16),  -- on/off/unknown
    last_seen_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**sensor_readings (传感器时序数据)**
```sql
CREATE TABLE sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    server_id UUID REFERENCES servers(id),
    sensor_name VARCHAR(64) NOT NULL,
    sensor_type VARCHAR(16),  -- temp/voltage/fan/power
    value DECIMAL(10,2) NOT NULL,
    unit VARCHAR(8),
    threshold_lower DECIMAL(10,2),
    threshold_upper DECIMAL(10,2),
    recorded_at TIMESTAMP NOT NULL,
    -- 按时间分区，90 天自动清理
) PARTITION BY RANGE (recorded_at);
```

**events (系统事件/告警)**
```sql
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    server_id UUID REFERENCES servers(id),
    event_type VARCHAR(16),  -- sel/alert/audit
    severity VARCHAR(16),  -- info/warning/critical
    message TEXT NOT NULL,
    raw_data JSONB,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**users (用户管理)**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(32) UNIQUE NOT NULL,
    email VARCHAR(128),
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(16) DEFAULT 'viewer',  -- admin/operator/viewer
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**audit_logs (操作审计)**
```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(32) NOT NULL,
    resource_type VARCHAR(32),
    resource_id UUID,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. API 设计

### 4.1 REST API 概览

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/v1/servers | 服务器列表 (分页、过滤) |
| POST | /api/v1/servers | 添加服务器 |
| GET | /api/v1/servers/{id} | 服务器详情 |
| PUT | /api/v1/servers/{id} | 更新服务器 |
| DELETE | /api/v1/servers/{id} | 删除服务器 |
| POST | /api/v1/servers/{id}/discover | 重新发现协议 |
| GET | /api/v1/servers/{id}/power | 获取电源状态 |
| POST | /api/v1/servers/{id}/power | 电源操作 (on/off/restart) |
| GET | /api/v1/servers/{id}/sensors | 当前传感器读数 |
| GET | /api/v1/servers/{id}/sensors/history | 历史数据 |
| GET | /api/v1/events | 事件列表 |
| PUT | /api/v1/events/{id}/ack | 确认事件 |
| POST | /api/v1/discovery/scan | 网段扫描发现 |
| POST | /api/v1/auth/login | 用户登录 |
| POST | /api/v1/auth/refresh | 刷新 Token |

### 4.2 WebSocket 实时协议

**连接**: `wss://api.bmc-master.local/ws/v1/realtime`

**客户端订阅消息**:
```json
{
  "action": "subscribe",
  "topics": ["sensors", "events", "power"],
  "server_ids": ["srv-001", "srv-002"]
}
```

**服务端推送消息类型**:

| type | 描述 | 示例 |
|------|------|------|
| sensor_update | 传感器数据更新 | `{server_id, data: {cpu_temp, fan_speed}}` |
| event_alert | 告警事件 | `{server_id, severity, message}` |
| power_change | 电源状态变化 | `{server_id, old_state, new_state}` |
| server_status | 服务器上下线 | `{server_id, status: online/offline}` |
| task_progress | 任务进度 | `{task_id, progress, status}` |

---

## 5. 界面设计

### 5.1 视觉风格

**工业控制台 / NOC 大屏风格**

- **主色调**: 深海军蓝 `#0a0e17` + 科技青 `#00d4aa`
- **状态色**: 正常 `#00d4aa` / 警告 `#f59e0b` / 故障 `#ef4444`
- **布局**: 三栏式 (左: 服务器列表, 中: 主内容, 右: 仪表盘)
- **字体**: 系统字体栈，数据使用等宽字体

### 5.2 核心页面

1. **Login** - 深色登录页，Logo + 表单
2. **Dashboard** - 全局概览：统计卡片、温度趋势图、告警列表
3. **Server List** - 服务器表格，状态筛选，批量操作
4. **Server Detail** - 单服务器详情：传感器仪表盘、电源控制、SEL 日志
5. **Discovery** - 网段扫描配置、发现结果列表
6. **Events** - 事件中心，告警确认，历史查询
7. **Settings** - 系统设置、用户管理、通知配置

---

## 6. 部署方案

### 6.1 Docker Compose 架构

```yaml
# 6 个容器
- nginx: 反向代理，静态资源服务
- backend: FastAPI 应用
- frontend: React 构建产物 (Nginx)
- celery-worker: 异步任务执行
- celery-beat: 定时任务调度
- postgres: PostgreSQL 数据库
- redis: Redis 缓存和队列
```

### 6.2 目录结构

```
bmc-master/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/          # REST 路由
│   │   ├── core/         # 配置、数据库
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── services/     # 业务逻辑
│   │   ├── adapters/     # Redfish/IPMI 适配器
│   │   └── tasks/        # Celery 任务
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # React 前端
│   ├── src/
│   │   ├── components/   # UI 组件
│   │   ├── pages/        # 页面
│   │   └── services/     # API 客户端
│   └── Dockerfile
├── nginx/
│   └── default.conf
├── docker-compose.yml
├── .env.example
└── README.md
```

### 6.3 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/your-org/bmc-master.git
cd bmc-master

# 2. 配置环境
cp .env.example .env
# 编辑 .env 设置数据库密码等

# 3. 一键启动
docker-compose up -d

# 4. 初始化数据库
docker-compose exec backend alembic upgrade head

# 5. 创建管理员
docker-compose exec backend python -m app.init_admin

# 6. 访问
open http://localhost
```

---

## 7. 实施计划

### Phase 1: 核心功能 (预计 2-3 周)

**Week 1: 基础架构**
- [ ] 项目脚手架搭建 (Docker Compose)
- [ ] 数据库模型实现
- [ ] 基础 API (servers CRUD)
- [ ] 前端框架 + 登录页

**Week 2: 协议适配**
- [ ] Redfish 适配器实现
- [ ] IPMI 适配器实现
- [ ] 协议自动探测逻辑
- [ ] 服务器发现功能

**Week 3: 监控与控制**
- [ ] 传感器数据采集任务
- [ ] 电源控制 API
- [ ] Dashboard 仪表盘
- [ ] WebSocket 实时推送

### Phase 2: 进阶功能 (预计 2 周)

- [ ] 告警通知系统 (邮件/Webhook)
- [ ] SEL 日志收集与展示
- [ ] 服务器详情页完善
- [ ] 事件中心

### Phase 3: 高级功能 (预计 1-2 周)

- [ ] 用户权限管理 (RBAC)
- [ ] 操作审计日志
- [ ] 固件更新 (调研阶段)
- [ ] 报表与导出

---

## 8. 风险与限制

### 8.1 技术风险

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| IPMI/Redfish 厂商差异 | 中 | 优先支持主流厂商，异常反馈 |
| 大量传感器数据 | 中 | 时序分区，自动清理，Redis 缓存 |
| BMC 网络不稳定 | 低 | 连接池，重试机制，超时降级 |

### 8.2 安全考虑

- BMC 密码加密存储 (AES-256)
- JWT Token 过期机制
- 操作审计日志记录
- 内网部署，不暴露公网
- HTTPS 证书配置

---

## 9. 附录

### 9.1 参考资料

- [Redfish API 规范](https://www.dmtf.org/standards/redfish)
- [IPMI 2.0 规范](https://www.intel.com/content/www/us/en/products/docs/servers/ipmi/ipmi-second-gen-interface-spec-v2-rev1-1.html)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

### 9.2 相关库

- `python-redfish`: Redfish 客户端
- `pyghmi`: Python IPMI 库
- `fastapi`: Web 框架
- `sqlalchemy`: ORM
- `celery`: 任务队列
- `echarts`: 前端图表

---

**文档结束**

设计确认后，进入实现阶段。
