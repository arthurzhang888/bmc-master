import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.services.report_engine import ReportEngine
from app.services.report_export import ReportExportService
from app.schemas.report import (
    SensorTrendReport,
    AlertStatisticsReport,
    AnomalyDetectionResult,
    ExportRequest
)

router = APIRouter()


@router.get("/sensor-trend", response_model=SensorTrendReport)
async def get_sensor_trend_report(
    server_id: UUID,
    sensor_type: str = Query(..., description="Sensor type: temperature, voltage, fan, power, current, other"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history"),
    db: AsyncSession = Depends(get_db)
):
    """Get sensor trend report with statistics.

    Returns sensor readings for the specified server and sensor type
    with statistical analysis including min, max, average, and trend slope.
    """
    engine = ReportEngine(db)
    report = await engine.generate_sensor_trend_report(
        str(server_id), sensor_type, hours
    )

    # Convert data_points dict format to match schema
    if report["data_points"]:
        report["server_id"] = server_id

    return report


@router.get("/alert-statistics", response_model=AlertStatisticsReport)
async def get_alert_statistics(
    days: int = Query(7, ge=1, le=90, description="Number of days"),
    db: AsyncSession = Depends(get_db)
):
    """Get alert statistics report.

    Returns aggregated alert data including total count, breakdown by severity,
    breakdown by server, and daily trend over the specified period.
    """
    engine = ReportEngine(db)
    report = await engine.generate_alert_statistics(days)
    return report


@router.get("/anomalies", response_model=List[AnomalyDetectionResult])
async def detect_anomalies(
    server_id: UUID,
    sensor_type: str = Query(..., description="Sensor type to analyze"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history to analyze"),
    threshold: float = Query(3.0, ge=1.0, le=5.0, description="Z-score threshold for anomaly detection"),
    db: AsyncSession = Depends(get_db)
):
    """Detect anomalies in sensor data using Z-score.

    Analyzes sensor readings and returns data points that deviate
    significantly from the mean based on the Z-score threshold.
    """
    engine = ReportEngine(db)
    anomalies = await engine.detect_anomalies(
        str(server_id), sensor_type, hours, threshold
    )
    return anomalies


@router.post("/export")
async def export_report(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Export report to PDF, Excel, or CSV.

    Generates report data based on report_type and converts it to the requested format.
    Supported formats: csv, excel, pdf.

    Args:
        request: Export request containing report_type, parameters, and format.
        db: Database session.

    Returns:
        StreamingResponse with the exported file content and appropriate Content-Disposition header.

    Raises:
        HTTPException: If report type is unknown, format is unsupported, or no data is available.
    """
    engine = ReportEngine(db)

    # Generate report data based on type
    if request.report_type == "sensor_trend":
        data = await engine.generate_sensor_trend_report(
            request.parameters.get("server_id"),
            request.parameters.get("sensor_type"),
            request.parameters.get("hours", 24)
        )
        export_data = data.get("data_points", [])
        title = f"Sensor Trend Report - {request.parameters.get('sensor_type', 'Unknown')}"
    elif request.report_type == "alert_statistics":
        data = await engine.generate_alert_statistics(
            request.parameters.get("days", 7)
        )
        # Flatten daily_trend for export
        export_data = data.get("daily_trend", [])
        title = "Alert Statistics Report"
    elif request.report_type == "anomalies":
        export_data = await engine.detect_anomalies(
            request.parameters.get("server_id"),
            request.parameters.get("sensor_type"),
            request.parameters.get("hours", 24),
            request.parameters.get("threshold", 3.0)
        )
        title = f"Anomaly Detection Report - {request.parameters.get('sensor_type', 'Unknown')}"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown report type: {request.report_type}")

    if not export_data:
        raise HTTPException(status_code=404, detail="No data to export")

    export_service = ReportExportService()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    try:
        if request.format == "csv":
            content = export_service.export_to_csv(export_data)
            media_type = "text/csv"
            filename = f"{request.report_type}_{timestamp}.csv"
        elif request.format == "excel":
            content = export_service.export_to_excel(export_data, title=title)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{request.report_type}_{timestamp}.xlsx"
        elif request.format == "pdf":
            content = export_service.export_to_pdf(export_data, title=title)
            media_type = "application/pdf"
            filename = f"{request.report_type}_{timestamp}.pdf"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}. Use csv, excel, or pdf.")
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
