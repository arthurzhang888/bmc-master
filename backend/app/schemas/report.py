from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime


class DataPoint(BaseModel):
    """Single sensor data point."""
    timestamp: str
    value: float


class SensorTrendReport(BaseModel):
    """Sensor trend report with statistics."""
    server_id: UUID
    sensor_type: str
    time_range: str
    data_points: List[DataPoint]
    statistics: Dict[str, float]


class AlertStatisticsReport(BaseModel):
    """Alert statistics report."""
    total_alerts: int
    by_severity: Dict[str, int]
    by_server: Dict[str, int]
    daily_trend: List[Dict[str, Any]]
    period_days: int


class AnomalyDetectionResult(BaseModel):
    """Anomaly detection result item."""
    timestamp: str
    value: float
    z_score: float
    severity: str


class ExportRequest(BaseModel):
    """Report export request."""
    report_type: str
    parameters: Dict[str, Any]
    format: str  # pdf, excel, csv
