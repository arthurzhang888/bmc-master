from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import pandas as pd
import numpy as np

from app.models.sensor import SensorReading
from app.models.alert import AlertHistory
from app.models.server import Server, ServerStatus


class ReportEngine:
    """报表生成引擎 - Report generation engine with analytics capabilities."""

    def __init__(self, db: AsyncSession):
        """Initialize the report engine.

        Args:
            db: Async SQLAlchemy session for database operations.
        """
        self.db = db

    async def generate_sensor_trend_report(
        self,
        server_id: str,
        sensor_type: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Generate sensor trend report with pandas statistics.

        Retrieves sensor readings for the specified server and sensor type
        within the time window, then calculates statistical metrics using pandas.

        Args:
            server_id: UUID of the server to analyze.
            sensor_type: Type of sensor (temperature, voltage, fan, etc.).
            hours: Number of hours of history to include (default: 24).

        Returns:
            Dictionary containing data points and statistical analysis.
        """
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
            return {
                "server_id": server_id,
                "sensor_type": sensor_type,
                "time_range": f"{hours}h",
                "data_points": [],
                "statistics": {}
            }

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
        """Generate alert statistics report.

        Aggregates alert data by severity, server, and daily trend.

        Args:
            days: Number of days to include in the report (default: 7).

        Returns:
            Dictionary containing total alerts, breakdowns by severity
            and server, and daily trend data.
        """
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
        """Detect anomalies in sensor data using Z-score.

        Uses statistical Z-score analysis to identify outliers in sensor
        readings that deviate significantly from the mean.

        Args:
            server_id: UUID of the server to analyze.
            sensor_type: Type of sensor to check.
            hours: Number of hours of history to analyze (default: 24).
            threshold: Z-score threshold for anomaly detection (default: 3.0).
                      Higher values detect more extreme outliers.

        Returns:
            List of detected anomalies with timestamp, value, z-score, and severity.
        """
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
