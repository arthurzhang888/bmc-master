# BMC Master Phase 1 - 核心功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 BMC Master 核心功能：项目脚手架、数据库模型、协议适配器、服务器 CRUD API、传感器监控、Dashboard 仪表盘、WebSocket 实时推送

**Architecture:** 后端使用 FastAPI + SQLAlchemy + Celery，前端使用 React + ECharts，协议层使用 Adapter 模式支持 Redfish/IPMI 自动探测，数据存储使用 PostgreSQL + Redis

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Celery, React 18, TypeScript, PostgreSQL 16, Redis 7, Docker Compose

---

## 文件结构规划

```
bmc-master/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   ├── server.py
│   │   │   └── sensor.py
│   │   ├── schemas/
│   │   ├── api/
│   │   ├── adapters/
│   │   ├── services/
│   │   └── tasks/
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Task 1: 项目基础架构 - Docker Compose 环境

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `backend/Dockerfile`
- Create: `backend/requirements.txt`

- [ ] **Step 1: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USER:-bmc}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-bmc_secret}
      POSTGRES_DB: ${DB_NAME:-bmc_master}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-bmc}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER:-bmc}:${DB_PASSWORD:-bmc_secret}@postgres:5432/${DB_NAME:-bmc_master}
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY:-your-secret-key-change-in-production}
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER:-bmc}:${DB_PASSWORD:-bmc_secret}@postgres:5432/${DB_NAME:-bmc_master}
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./backend:/app
    depends_on:
      - redis
      - postgres
    command: celery -A app.tasks worker --loglevel=info

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER:-bmc}:${DB_PASSWORD:-bmc_secret}@postgres:5432/${DB_NAME:-bmc_master}
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./backend:/app
    depends_on:
      - redis
      - postgres
    command: celery -A app.tasks beat --loglevel=info

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8000
    command: npm run dev

volumes:
  postgres_data:
  redis_data:
```

- [ ] **Step 2: 创建 .env.example**

```bash
# Database
DB_USER=bmc
DB_PASSWORD=bmc_secret
DB_NAME=bmc_master

# Security
SECRET_KEY=change-this-to-a-random-string-in-production

# BMC Default Credentials (for discovery)
DEFAULT_BMC_USERNAME=ADMIN
DEFAULT_BMC_PASSWORD=ADMIN
```

- [ ] **Step 3: 创建 backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc python3-dev ipmitool \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: 创建 backend/requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.0
redis==5.0.0
celery==5.4.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
cryptography==42.0.0
redfish==3.2.4
pyghmi==1.5.62
pydantic-settings==2.3.0
pytest==8.2.0
pytest-asyncio==0.23.0
httpx==0.27.0
```

- [ ] **Step 5: 测试配置**

Run: `docker-compose config`
Expected: 无错误输出

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml .env.example backend/
git commit -m "infra: add Docker Compose setup"
```

---

## Task 2: FastAPI 基础结构与数据库模型

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/server.py`
- Create: `backend/app/models/sensor.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: 创建配置管理**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://bmc:bmc_secret@localhost:5432/bmc_master"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    PROJECT_NAME: str = "BMC Master"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
```

- [ ] **Step 2: 创建数据库配置**

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

- [ ] **Step 3: 创建数据模型**

```python
# backend/app/models/server.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum

class ServerStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"

class PowerState(str, enum.Enum):
    ON = "on"
    OFF = "off"
    UNKNOWN = "unknown"

class Protocol(str, enum.Enum):
    REDFISH = "redfish"
    IPMI = "ipmi"
    UNKNOWN = "unknown"

class Server(Base):
    __tablename__ = "servers"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname: Mapped[str] = mapped_column(String(128), nullable=True)
    bmc_ip: Mapped[str] = mapped_column(String(39), unique=True, nullable=False, index=True)
    bmc_username: Mapped[str] = mapped_column(String(64), nullable=False)
    bmc_password: Mapped[str] = mapped_column(Text, nullable=False)
    protocol: Mapped[Protocol] = mapped_column(SQLEnum(Protocol), default=Protocol.UNKNOWN)
    vendor: Mapped[str] = mapped_column(String(32), nullable=True)
    model: Mapped[str] = mapped_column(String(64), nullable=True)
    status: Mapped[ServerStatus] = mapped_column(SQLEnum(ServerStatus), default=ServerStatus.OFFLINE)
    power_state: Mapped[PowerState] = mapped_column(SQLEnum(PowerState), default=PowerState.UNKNOWN)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    sensor_readings = relationship("SensorReading", back_populates="server")
```

- [ ] **Step 4: 创建 FastAPI 主应用**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}
```

- [ ] **Step 5: 创建 Alembic 迁移**

Run: `cd backend && alembic init alembic`
修改 `alembic/env.py` 导入 models
Run: `alembic revision --autogenerate -m "init"`
Run: `alembic upgrade head`

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add FastAPI core with database models"
```

---

## Task 3: BMC 协议适配器层

**Files:**
- Create: `backend/app/adapters/base.py`
- Create: `backend/app/adapters/redfish.py`
- Create: `backend/app/adapters/ipmi.py`
- Create: `backend/app/adapters/factory.py`

- [ ] **Step 1: 创建抽象基类**

```python
# backend/app/adapters/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class SensorReading:
    name: str
    value: float
    unit: str
    sensor_type: str
    timestamp: datetime

class BMCAdapter(ABC):
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password

    @abstractmethod
    async def get_power_status(self) -> str:
        pass

    @abstractmethod
    async def set_power(self, action: str) -> bool:
        pass

    @abstractmethod
    async def get_sensors(self) -> List[SensorReading]:
        pass

    @classmethod
    @abstractmethod
    async def probe(cls, host: str, username: str, password: str) -> bool:
        pass
```

- [ ] **Step 2: 创建 Redfish 适配器**

实现 `redfish.py` 调用 python-redfish 库
- 实现 connect/disconnect
- 实现 get_power_status/set_power
- 实现 get_sensors 读取温度/风扇/功率

- [ ] **Step 3: 创建 IPMI 适配器**

实现 `ipmi.py` 调用 pyghmi 库
- 使用 ipmitool 命令或 pyghmi
- 实现相同的 BMCAdapter 接口

- [ ] **Step 4: 创建工厂类**

```python
# backend/app/adapters/factory.py
class BMCAdapterFactory:
    @staticmethod
    async def create(host: str, username: str, password: str):
        from .redfish import RedfishAdapter
        from .ipmi import IPMIAdapter
        
        if await RedfishAdapter.probe(host, username, password):
            return RedfishAdapter(host, username, password), "redfish"
        return IPMIAdapter(host, username, password), "ipmi"
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/adapters/
git commit -m "feat: add BMC protocol adapters (Redfish/IPMI)"
```

---

## Task 4: REST API 实现

**Files:**
- Create: `backend/app/schemas/server.py`
- Create: `backend/app/api/v1/endpoints/servers.py`
- Modify: `backend/app/main.py` 注册路由

- [ ] **Step 1: 创建 Pydantic Schemas**

```python
# backend/app/schemas/server.py
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class ServerBase(BaseModel):
    hostname: Optional[str] = None
    bmc_ip: str
    bmc_username: str
    vendor: Optional[str] = None
    model: Optional[str] = None

class ServerCreate(ServerBase):
    bmc_password: str

class ServerResponse(ServerBase):
    id: UUID
    status: str
    power_state: str
    protocol: str
    
    class Config:
        from_attributes = True
```

- [ ] **Step 2: 实现服务器 CRUD API**

```python
# backend/app/api/v1/endpoints/servers.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

router = APIRouter()

@router.get("/servers", response_model=List[ServerResponse])
async def list_servers(db: AsyncSession = Depends(get_db)):
    # 实现查询逻辑
    pass

@router.post("/servers", response_model=ServerResponse)
async def create_server(server: ServerCreate, db: AsyncSession = Depends(get_db)):
    # 实现创建逻辑，包含协议探测
    pass

@router.get("/servers/{server_id}", response_model=ServerResponse)
async def get_server(server_id: UUID, db: AsyncSession = Depends(get_db)):
    pass

@router.post("/servers/{server_id}/power")
async def power_control(server_id: UUID, action: str, db: AsyncSession = Depends(get_db)):
    # 调用 adapter 控制电源
    pass

@router.get("/servers/{server_id}/sensors")
async def get_sensors(server_id: UUID, db: AsyncSession = Depends(get_db)):
    # 获取传感器数据
    pass
```

- [ ] **Step 3: 注册路由**

```python
# backend/app/main.py
from app.api.v1.endpoints import servers

app.include_router(servers.router, prefix="/api/v1")
```

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat: add REST API for server management"
```

---

## Task 5: Celery 定时任务

**Files:**
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/monitoring.py`

- [ ] **Step 1: 配置 Celery**

```python
# backend/app/tasks/__init__.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "bmc_master",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.monitoring"]
)
```

- [ ] **Step 2: 创建监控任务**

```python
# backend/app/tasks/monitoring.py
from app.tasks import celery_app
from app.adapters.factory import BMCAdapterFactory
from app.models.sensor import SensorReading

@celery_app.task
def collect_server_sensors(server_id: str):
    """采集单个服务器的传感器数据"""
    # 查询服务器信息
    # 创建 adapter
    # 获取传感器数据
    # 保存到数据库
    pass

@celery_app.task
def discover_servers(network_range: str):
    """扫描网段发现 BMC 服务器"""
    # 实现 IP 扫描
    # 对每个 IP 尝试协议探测
    # 保存发现的服务器
    pass
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/tasks/
git commit -m "feat: add Celery tasks for monitoring and discovery"
```

---

## Task 6: React 前端基础

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/Dockerfile`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "bmc-master-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "axios": "^1.7.0",
    "echarts": "^5.5.0",
    "echarts-for-react": "^3.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0"
  }
}
```

- [ ] **Step 2: 创建 Dockerfile**

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
```

- [ ] **Step 3: 创建基础 React 应用**

```tsx
// frontend/src/App.tsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ServerList from './pages/ServerList';
import Login from './pages/Login';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Dashboard />} />
        <Route path="/servers" element={<ServerList />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: add React frontend structure"
```

---

## Task 7: Dashboard 仪表盘界面

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/components/ServerStatusCard.tsx`
- Create: `frontend/src/services/api.ts`

- [ ] **Step 1: 创建 API 客户端**

```typescript
// frontend/src/services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

export const serverApi = {
  list: () => api.get('/api/v1/servers'),
  get: (id: string) => api.get(`/api/v1/servers/${id}`),
  create: (data: any) => api.post('/api/v1/servers', data),
  power: (id: string, action: string) => 
    api.post(`/api/v1/servers/${id}/power`, { action }),
  sensors: (id: string) => api.get(`/api/v1/servers/${id}/sensors`),
};

export default api;
```

- [ ] **Step 2: 创建 Dashboard 组件**

```tsx
// frontend/src/pages/Dashboard.tsx
import React, { useEffect, useState } from 'react';
import { serverApi } from '../services/api';
import ReactECharts from 'echarts-for-react';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState({ online: 0, offline: 0, warning: 0 });
  const [servers, setServers] = useState([]);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    const res = await serverApi.list();
    setServers(res.data);
    // 计算统计
  };

  // NOC 风格深色主题
  const chartOption = {
    backgroundColor: 'transparent',
    title: { text: 'Temperature Trends', textStyle: { color: '#00d4aa' } },
    series: [{
      type: 'line',
      data: [],
      smooth: true,
      lineStyle: { color: '#00d4aa' }
    }]
  };

  return (
    <div style={{ background: '#0a0e17', minHeight: '100vh', color: '#e0e6ed' }}>
      {/* Header */}
      <header style={{ padding: '16px 24px', borderBottom: '2px solid #00d4aa' }}>
        <h1 style={{ color: '#00d4aa', margin: 0 }}>🔧 BMC Master</h1>
      </header>
      
      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', padding: '24px' }}>
        <div style={{ background: '#111827', padding: '20px', borderRadius: '8px', borderLeft: '4px solid #00d4aa' }}>
          <div style={{ fontSize: '32px', color: '#00d4aa' }}>{stats.online}</div>
          <div style={{ fontSize: '12px', color: '#64748b' }}>Online Servers</div>
        </div>
        <div style={{ background: '#111827', padding: '20px', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
          <div style={{ fontSize: '32px', color: '#f59e0b' }}>{stats.warning}</div>
          <div style={{ fontSize: '12px', color: '#64748b' }}>Warnings</div>
        </div>
        <div style={{ background: '#111827', padding: '20px', borderRadius: '8px', borderLeft: '4px solid #ef4444' }}>
          <div style={{ fontSize: '32px', color: '#ef4444' }}>{stats.offline}</div>
          <div style={{ fontSize: '12px', color: '#64748b' }}>Offline</div>
        </div>
      </div>
      
      {/* Charts */}
      <div style={{ padding: '0 24px' }}>
        <ReactECharts option={chartOption} style={{ height: '300px' }} />
      </div>
    </div>
  );
};

export default Dashboard;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "feat: add Dashboard with NOC-style UI and charts"
```

---

## Task 8: WebSocket 实时推送

**Files:**
- Create: `backend/app/api/v1/endpoints/websocket.py`
- Modify: `frontend/src/pages/Dashboard.tsx` 添加 WebSocket

- [ ] **Step 1: 创建 WebSocket 端点**

```python
# backend/app/api/v1/endpoints/websocket.py
from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ws/v1/realtime")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # 处理订阅消息
            # 推送传感器更新
    except:
        pass
```

- [ ] **Step 2: 前端 WebSocket 连接**

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useEffect, useRef } from 'react';

export const useWebSocket = (onMessage: (data: any) => void) => {
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws/v1/realtime');
    ws.current.onmessage = (event) => {
      onMessage(JSON.parse(event.data));
    };
    return () => ws.current?.close();
  }, []);

  return ws;
};
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/endpoints/websocket.py frontend/src/hooks/
git commit -m "feat: add WebSocket for real-time sensor updates"
```

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2025-06-27-phase1-core-features.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints for review

**Which approach would you like?**
