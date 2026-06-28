# BMC Master Phase 3 - 报表与自动化运维实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** 实现报表分析（趋势、统计、导出）和自动化运维（批量操作、自动发现、定时任务）功能

**Architecture:** 基于 Phase 1/2 架构，新增报表引擎（pandas + openpyxl/reportlab）、批量任务执行器（Celery）、网段扫描器（asyncio）、定时任务调度器（celery-beat）

**Tech Stack:** FastAPI, Celery, Pandas, OpenPyXL, ReportLab, Python-Crontab

---

## 任务概览

共 **10 个任务**：
- Task 1-4: 报表模块（数据库模型、报表 API、导出功能、前端页面）
- Task 5-8: 自动化模块（批量操作、自动发现、定时任务、前端页面）
- Task 9-10: 集成与优化（Celery 配置、测试与文档）

---

## Task 1: 报表数据库模型与迁移

**Files:**
- Create: `backend/app/models/report.py` (ReportTemplate)
- Create: `backend/app/models/bulk_job.py` (BulkJob, BulkJobResult)
- Create: `backend/app/models/discovery.py` (DiscoveryJob, DiscoveredDevice)
- Create: `backend/app/models/scheduler.py` (ScheduledTask, TaskExecutionHistory)
- Modify: `backend/app/models/__init__.py`
- Create: Alembic migration

### Step 1: Create ReportTemplate model

```python
# backend/app/models/report.py
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class ReportType(str, enum.Enum):
    SENSOR_TREND = "sensor_trend"
    ALERT_STATISTICS = "alert_statistics"
    SERVER_UPTIME = "server_uptime"
    ENERGY_CONSUMPTION = "energy_consumption"


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    report_type: Mapped[ReportType] = mapped_column(SQLEnum(ReportType), nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    schedule: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # Cron expression
    last_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
```

### Step 2: Create BulkJob model

```python
# backend/app/models/bulk_job.py
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, DateTime, Text, Enum as SQLEnum, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class BulkJobType(str, enum.Enum):
    POWER = "power"
    IPMI_COMMAND = "ipmi_command"


class BulkJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BulkJob(Base):
    __tablename__ = "bulk_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    job_type: Mapped[BulkJobType] = mapped_column(SQLEnum(BulkJobType), nullable=False)
    action: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # For power jobs
    command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # For IPMI jobs
    status: Mapped[BulkJobStatus] = mapped_column(SQLEnum(BulkJobStatus), default=BulkJobStatus.PENDING)
    target_servers: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    results: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
```

### Step 3: Create DiscoveryJob model

```python
# backend/app/models/discovery.py
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, DateTime, Enum as SQLEnum, JSON, Integer, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class DiscoveryStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoveryJob(Base):
    __tablename__ = "discovery_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    network_range: Mapped[str] = mapped_column(String(64), nullable=False)  # CIDR notation
    ports: Mapped[List[int]] = mapped_column(ARRAY(Integer), default=[623, 443])
    status: Mapped[DiscoveryStatus] = mapped_column(SQLEnum(DiscoveryStatus), default=DiscoveryStatus.PENDING)
    found_devices: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    device_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
```

### Step 4: Create ScheduledTask model

```python
# backend/app/models/scheduler.py
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, DateTime, Enum as SQLEnum, JSON, Integer, ARRAY, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class TaskType(str, enum.Enum):
    POWER_CONTROL = "power_control"
    SENSOR_COLLECT = "sensor_collect"
    SEL_COLLECT = "sel_collect"
    CUSTOM_COMMAND = "custom_command"


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_type: Mapped[TaskType] = mapped_column(SQLEnum(TaskType), nullable=False)
    schedule: Mapped[str] = mapped_column(String(64), nullable=False)  # Cron expression
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    target_servers: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TaskExecutionHistory(Base):
    __tablename__ = "task_execution_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scheduled_tasks.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # success, failed
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Step 5: Update models/__init__.py

```python
# backend/app/models/__init__.py
# Add new imports
from app.models.report import ReportTemplate, ReportType
from app.models.bulk_job import BulkJob, BulkJobType, BulkJobStatus
from app.models.discovery import DiscoveryJob, DiscoveryStatus
from app.models.scheduler import ScheduledTask, TaskType, TaskExecutionHistory

__all__ = [
    # ... existing exports
    "ReportTemplate", "ReportType",
    "BulkJob", "BulkJobType", "BulkJobStatus",
    "DiscoveryJob", "DiscoveryStatus",
    "ScheduledTask", "TaskType", "TaskExecutionHistory",
]
```

### Step 6: Create Alembic migration

```bash
cd backend && alembic revision --autogenerate -m "add phase3 models"
```

### Step 7: Commit

```bash
git add backend/app/models/ backend/alembic/versions/
git commit -m "feat: add Phase 3 models (reports, bulk jobs, discovery, scheduler)"
```

---

## Task 2: 报表服务与 API

**Files:**
- Create: `backend/app/services/report_engine.py`
- Create: `backend/app/api/v1/endpoints/reports.py`
- Create: `backend/app/schemas/report.py`
- Modify: `backend/app/api/v1/api.py`

### Step 1: Create ReportEngine service

```python
# backend/app/services/report_engine.py
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import pandas as pd
import numpy as np

from app.models.sensor import SensorReading
from app.models.alert import AlertHistory
from app.models.server import Server, ServerStatus
from app.models.event import Event


class ReportEngine:
    """报表生成引擎"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_sensor_trend_report(
        self,
        server_id: str,
        sensor_type: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """生成传感器趋势报表"""
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await self.db.execute(
            select(SensorReading)
            .where(
                and_(
                    SensorReading.server_id == server_id,
                    SensorReading.sensor_type == sensor_type,
                    SensorReading.recorded_at >= since
                )
            )
            .order_by(SensorReading.recorded_at)
        )
        readings = result.scalars().all()

        if not readings:
            return {"data_points": [], "statistics": {}}

        # Convert to pandas for analysis
        df = pd.DataFrame([
            {"timestamp": r.recorded_at, "value": float(r.value)}
            for r in readings
        ])

        statistics = {
            "min": float(df["value"].min()),
            "max": float(df["value"].max()),
            "avg": float(df["value"].mean()),
            "std_dev": float(df["value"].std()),
            "count": len(readings)
        }

        # Generate trend prediction (simple linear regression)
        if len(df) > 1:
            df["timestamp_num"] = pd.to_numeric(df["timestamp"])
            slope = np.polyfit(df["timestamp_num"], df["value"], 1)[0]
            statistics["trend_slope"] = float(slope)

        data_points = [
            {"timestamp": r.recorded_at.isoformat(), "value": float(r.value)}
            for r in readings
        ]

        return {
            "server_id": server_id,
            "sensor_type": sensor_type,
            "time_range": f"{hours}h",
            "data_points": data_points,
            "statistics": statistics
        }

    async def generate_alert_statistics(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """生成告警统计报表"""
        since = datetime.utcnow() - timedelta(days=days)

        # Total alerts
        result = await self.db.execute(
            select(func.count()).select_from(AlertHistory)
            .where(AlertHistory.created_at >= since)
        )
        total_alerts = result.scalar()

        # By severity
        result = await self.db.execute(
            select(AlertHistory.severity, func.count())
            .where(AlertHistory.created_at >= since)
            .group_by(AlertHistory.severity)
        )
        by_severity = {str(r[0]): r[1] for r in result.all()}

        # By server
        result = await self.db.execute(
            select(AlertHistory.server_id, func.count())
            .where(AlertHistory.created_at >= since)
            .group_by(AlertHistory.server_id)
        )
        by_server = {str(r[0]): r[1] for r in result.all()}

        # Daily trend
        result = await self.db.execute(
            select(
                func.date_trunc('day', AlertHistory.created_at).label('day'),
                func.count()
            )
            .where(AlertHistory.created_at >= since)
            .group_by('day')
            .order_by('day')
        )
        daily_trend = [
            {"date": r[0].isoformat(), "count": r[1]}
            for r in result.all()
        ]

        return {
            "total_alerts": total_alerts,
            "by_severity": by_severity,
            "by_server": by_server,
            "daily_trend": daily_trend,
            "period_days": days
        }

    async def detect_anomalies(
        self,
        server_id: str,
        sensor_type: str,
        hours: int = 24,
        threshold: float = 3.0
    ) -> List[Dict[str, Any]]:
        """使用 Z-score 检测异常值"""
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await self.db.execute(
            select(SensorReading)
            .where(
                and_(
                    SensorReading.server_id == server_id,
                    SensorReading.sensor_type == sensor_type,
                    SensorReading.recorded_at >= since
                )
            )
            .order_by(SensorReading.recorded_at)
        )
        readings = result.scalars().all()

        if len(readings) < 10:
            return []

        values = [float(r.value) for r in readings]
        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return []

        anomalies = []
        for r in readings:
            z_score = (float(r.value) - mean) / std
            if abs(z_score) > threshold:
                anomalies.append({
                    "timestamp": r.recorded_at.isoformat(),
                    "value": float(r.value),
                    "z_score": float(z_score),
                    "severity": "critical" if abs(z_score) > 4 else "warning"
                })

        return anomalies
```

### Step 2: Create report schemas

```python
# backend/app/schemas/report.py
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime


class SensorTrendReport(BaseModel):
    server_id: UUID
    sensor_type: str
    time_range: str
    data_points: List[Dict[str, Any]]
    statistics: Dict[str, float]


class AlertStatisticsReport(BaseModel):
    total_alerts: int
    by_severity: Dict[str, int]
    by_server: Dict[str, int]
    daily_trend: List[Dict[str, Any]]
    period_days: int


class AnomalyDetectionResult(BaseModel):
    timestamp: str
    value: float
    z_score: float
    severity: str


class ExportRequest(BaseModel):
    report_type: str
    parameters: Dict[str, Any]
    format: str  # pdf, excel, csv
```

### Step 3: Create reports API

```python
# backend/app/api/v1/endpoints/reports.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.services.report_engine import ReportEngine
from app.schemas.report import (
    SensorTrendReport,
    AlertStatisticsReport,
    AnomalyDetectionResult,
    ExportRequest
)

router = APIRouter()


@router.get("/reports/sensor-trend", response_model=SensorTrendReport)
async def get_sensor_trend_report(
    server_id: UUID,
    sensor_type: str = Query(..., description="Sensor type: Temperature, Voltage, Fan, etc."),
    hours: int = Query(24, ge=1, le=168, description="Hours of history"),
    db: AsyncSession = Depends(get_db)
):
    """Get sensor trend report with statistics"""
    engine = ReportEngine(db)
    report = await engine.generate_sensor_trend_report(
        str(server_id), sensor_type, hours
    )
    return report


@router.get("/reports/alert-statistics", response_model=AlertStatisticsReport)
async def get_alert_statistics(
    days: int = Query(7, ge=1, le=90, description="Number of days"),
    db: AsyncSession = Depends(get_db)
):
    """Get alert statistics report"""
    engine = ReportEngine(db)
    report = await engine.generate_alert_statistics(days)
    return report


@router.get("/reports/anomalies", response_model=List[AnomalyDetectionResult])
async def detect_anomalies(
    server_id: UUID,
    sensor_type: str,
    hours: int = Query(24, ge=1, le=168),
    threshold: float = Query(3.0, ge=1.0, le=5.0, description="Z-score threshold"),
    db: AsyncSession = Depends(get_db)
):
    """Detect anomalies in sensor data using Z-score"""
    engine = ReportEngine(db)
    anomalies = await engine.detect_anomalies(
        str(server_id), sensor_type, hours, threshold
    )
    return anomalies


@router.post("/reports/export")
async def export_report(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Export report to PDF, Excel, or CSV"""
    # TODO: Implement export functionality in Task 3
    raise HTTPException(status_code=501, detail="Export not yet implemented")
```

### Step 4: Register reports router

```python
# backend/app/api/v1/api.py
from app.api.v1.endpoints import servers, websocket, events, reports

api_router = APIRouter()
api_router.include_router(servers.router, prefix="/servers", tags=["servers"])
api_router.include_router(websocket.router, prefix="/ws")
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
```

### Step 5: Commit

```bash
git add backend/
git commit -m "feat: add report engine and API endpoints"
```

---

## Task 3: 报表导出功能 (PDF/Excel/CSV)

**Files:**
- Create: `backend/app/services/report_export.py`
- Modify: `backend/app/api/v1/endpoints/reports.py`

### Step 1: Create ReportExportService

```python
# backend/app/services/report_export.py
import io
import csv
from typing import Dict, Any, List
from datetime import datetime

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class ReportExportService:
    """报表导出服务"""

    @staticmethod
    def export_to_csv(data: List[Dict[str, Any]], filename: str = "report.csv") -> bytes:
        """导出为 CSV"""
        if not data:
            return b""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue().encode('utf-8-sig')

    @staticmethod
    def export_to_excel(
        data: List[Dict[str, Any]],
        sheet_name: str = "Report",
        title: str = "Report"
    ) -> bytes:
        """导出为 Excel"""
        if not EXCEL_AVAILABLE:
            raise ImportError("openpyxl not installed")

        if not data:
            return b""

        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name

        # Add title
        ws.merge_cells('A1:F1')
        title_cell = ws['A1']
        title_cell.value = title
        title_cell.font = Font(size=16, bold=True)
        title_cell.alignment = Alignment(horizontal='center')

        # Add timestamp
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Add headers
        headers = list(data[0].keys())
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            cell.font = Font(bold=True, color="FFFFFF")

        # Add data
        for row_idx, row_data in enumerate(data, 5):
            for col_idx, key in enumerate(headers, 1):
                ws.cell(row=row_idx, column=col_idx, value=row_data.get(key))

        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_to_pdf(
        data: List[Dict[str, Any]],
        title: str = "Report",
        subtitle: str = ""
    ) -> bytes:
        """导出为 PDF"""
        if not PDF_AVAILABLE:
            raise ImportError("reportlab not installed")

        if not data:
            return b""

        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []

        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph(title, styles['Heading1']))
        if subtitle:
            elements.append(Paragraph(subtitle, styles['Normal']))
        elements.append(Spacer(1, 20))

        # Timestamp
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 20))

        # Table
        headers = list(data[0].keys())
        table_data = [headers]
        for row in data:
            table_data.append([str(row.get(h, "")) for h in headers])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))

        elements.append(table)
        doc.build(elements)

        output.seek(0)
        return output.getvalue()
```

### Step 2: Update requirements.txt

```
pandas==2.1.0
numpy==1.24.0
openpyxl==3.1.0
reportlab==4.0.0
```

### Step 3: Update reports API with export endpoint

```python
# Add to backend/app/api/v1/endpoints/reports.py

from fastapi.responses import StreamingResponse
from app.services.report_export import ReportExportService

@router.post("/reports/export")
async def export_report(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Export report to PDF, Excel, or CSV"""
    engine = ReportEngine(db)

    # Generate report data based on type
    if request.report_type == "sensor_trend":
        data = await engine.generate_sensor_trend_report(
            request.parameters.get("server_id"),
            request.parameters.get("sensor_type"),
            request.parameters.get("hours", 24)
        )
        export_data = data.get("data_points", [])
        title = f"Sensor Trend Report - {request.parameters.get('sensor_type')}"
    elif request.report_type == "alert_statistics":
        data = await engine.generate_alert_statistics(
            request.parameters.get("days", 7)
        )
        # Flatten for export
        export_data = data.get("daily_trend", [])
        title = "Alert Statistics Report"
    else:
        raise HTTPException(status_code=400, detail="Unknown report type")

    if not export_data:
        raise HTTPException(status_code=404, detail="No data to export")

    export_service = ReportExportService()

    if request.format == "csv":
        content = export_service.export_to_csv(export_data)
        media_type = "text/csv"
        filename = f"{request.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    elif request.format == "excel":
        content = export_service.export_to_excel(export_data, title=title)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{request.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    elif request.format == "pdf":
        content = export_service.export_to_pdf(export_data, title=title)
        media_type = "application/pdf"
        filename = f"{request.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

### Step 4: Commit

```bash
git add backend/
git commit -m "feat: add report export service (PDF, Excel, CSV)"
```

---

## Task 4: 批量操作服务与 API

**Files:**
- Create: `backend/app/services/bulk_executor.py`
- Create: `backend/app/api/v1/endpoints/bulk.py`
- Create: `backend/app/schemas/bulk.py`
- Modify: `backend/app/api/v1/api.py`

### Step 1: Create BulkExecutor service

```python
# backend/app/services/bulk_executor.py
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.bulk_job import BulkJob, BulkJobStatus
from app.models.server import Server, ServerStatus
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

            # Update progress
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
```

### Step 2: Create bulk operation schemas

```python
# backend/app/schemas/bulk.py
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime


class BulkJobCreate(BaseModel):
    name: str
    job_type: str  # power, ipmi_command
    action: Optional[str] = None  # for power jobs
    command: Optional[str] = None  # for ipmi jobs
    target_servers: List[UUID]


class BulkJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    job_type: str
    action: Optional[str]
    status: str
    target_servers: List[UUID]
    total_count: int
    success_count: int
    fail_count: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class BulkJobDetail(BulkJobResponse):
    results: List[Dict[str, Any]]
```

### Step 3: Create bulk API

```python
# backend/app/api/v1/endpoints/bulk.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.bulk_job import BulkJob, BulkJobType, BulkJobStatus
from app.schemas.bulk import BulkJobCreate, BulkJobResponse, BulkJobDetail
from app.services.bulk_executor import BulkExecutor

router = APIRouter()


@router.post("/bulk/power", response_model=BulkJobResponse)
async def create_bulk_power_job(
    job_data: BulkJobCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a bulk power control job"""
    if len(job_data.target_servers) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 servers per batch")

    job = BulkJob(
        name=job_data.name,
        job_type=BulkJobType.POWER,
        action=job_data.action,
        target_servers=[str(s) for s in job_data.target_servers],
        total_count=len(job_data.target_servers),
        status=BulkJobStatus.PENDING
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Queue the job
    from app.tasks.bulk import execute_bulk_job_task
    execute_bulk_job_task.delay(str(job.id))

    return job


@router.get("/bulk/jobs", response_model=List[BulkJobResponse])
async def list_bulk_jobs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List bulk jobs"""
    result = await db.execute(
        select(BulkJob)
        .order_by(BulkJob.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/bulk/jobs/{job_id}", response_model=BulkJobDetail)
async def get_bulk_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get bulk job details with results"""
    result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job
```

### Step 4: Create Celery task for bulk jobs

```python
# backend/app/tasks/bulk.py
from celery import shared_task
import asyncio

from app.core.database import AsyncSessionLocal
from app.models.bulk_job import BulkJob
from app.services.bulk_executor import BulkExecutor


@shared_task
def execute_bulk_job_task(job_id: str):
    """执行批量任务"""
    async def _execute():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
            job = result.scalar_one_or_none()

            if not job:
                return {"status": "error", "message": "Job not found"}

            executor = BulkExecutor(db)

            if job.job_type.value == "power":
                await executor.execute_power_job(job)
            else:
                job.status = "failed"
                await db.commit()
                return {"status": "error", "message": "Unknown job type"}

            return {"status": "completed", "job_id": job_id}

    return asyncio.run(_execute())
```

### Step 5: Commit

```bash
git add backend/
git commit -m "feat: add bulk operation service and API"
```

---

## Task 5-10 概要

由于篇幅限制，以下是剩余任务的概要：

### Task 5: 自动发现服务与 API
- 创建 `DiscoveryService` 用于网段扫描
- 使用 `asyncio` + `asyncio.open_connection` 进行端口扫描
- 实现协议识别（尝试 Redfish probe，失败则尝试 IPMI）
- API: POST /discovery/scan, GET /discovery/jobs/{id}/devices

### Task 6: 定时任务调度器
- 使用 `python-crontab` 解析 Cron 表达式
- 创建 `SchedulerService` 管理定时任务
- 集成 Celery beat 动态添加/删除任务
- API: CRUD for scheduled tasks

### Task 7: 报表前端页面
- `Reports.tsx` - 报表选择器
- `ReportViewer.tsx` - 图表展示（ECharts）
- `ExportButton.tsx` - 导出功能

### Task 8: 自动化前端页面
- `BulkOperations.tsx` - 批量操作界面
- `Discovery.tsx` - 自动发现与导入
- `Scheduler.tsx` - 定时任务管理

### Task 9: Celery 配置更新
- 更新 `celery.py` 添加新的 beat 调度任务
- 配置任务队列和路由

### Task 10: 测试与文档
- 添加单元测试
- 更新 API 文档
- 添加使用说明到 README

---

## 执行方式选择

**计划完成！** 保存于 `docs/phase3-implementation-plan.md`

**执行选项：**

1. **Subagent-Driven (推荐)** - 每个任务分派独立子代理，两阶段审查
2. **Inline Execution** - 在此会话中批量执行任务

请选择执行方式：