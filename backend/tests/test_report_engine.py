"""Tests for report engine."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import pandas as pd
import numpy as np

from app.services.report_engine import ReportEngine


@pytest.mark.asyncio
async def test_generate_sensor_trend_report_empty():
    """Test sensor trend report with no data."""
    mock_db = AsyncMock()

    # Setup mock chain: execute() -> scalars() -> all()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    engine = ReportEngine(mock_db)
    result = await engine.generate_sensor_trend_report("server-1", "temperature", 24)

    assert result["data_points"] == []
    assert result["statistics"] == {}
    assert result["server_id"] == "server-1"
    assert result["sensor_type"] == "temperature"


@pytest.mark.asyncio
async def test_generate_alert_statistics():
    """Test alert statistics report."""
    mock_db = AsyncMock()

    # Mock total count
    mock_result = MagicMock()
    mock_result.scalar.return_value = 100
    mock_db.execute.return_value = mock_result

    engine = ReportEngine(mock_db)
    # Note: This is a simplified test - in reality you'd need to mock
    # multiple execute calls with different return values

    result = await engine.generate_alert_statistics(7)

    assert "total_alerts" in result
    assert "period_days" in result
    assert result["period_days"] == 7


@pytest.mark.asyncio
async def test_detect_anomalies_insufficient_data():
    """Test anomaly detection with insufficient data."""
    mock_db = AsyncMock()

    # Setup mock chain: execute() -> scalars() -> all()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    engine = ReportEngine(mock_db)
    result = await engine.detect_anomalies("server-1", "temperature", 24, 3.0)

    assert result == []


def test_statistics_calculation():
    """Test statistics calculation with pandas."""
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    df = pd.DataFrame({"value": values})

    assert df["value"].min() == 10.0
    assert df["value"].max() == 50.0
    assert df["value"].mean() == 30.0
    assert df["value"].std() > 0