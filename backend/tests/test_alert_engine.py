"""Tests for alert engine (Phase 2)."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.alert_engine import AlertEngine
from app.services.notification import NotificationService
from app.models.alert import AlertRule, AlertHistory, AlertSeverity, RuleType
from app.models.sensor import SensorReading, SensorType
from app.models.server import Server, ServerStatus


class TestAlertEngine:
    """Tests for alert engine."""

    @pytest.mark.asyncio
    async def test_check_threshold_greater_than(self):
        """Test threshold check with > operator."""
        mock_db = AsyncMock()
        engine = AlertEngine(mock_db)

        rule = MagicMock()
        rule.operator = ">"
        rule.threshold = 80.0

        assert engine._check_threshold(85.0, rule) is True
        assert engine._check_threshold(80.0, rule) is False
        assert engine._check_threshold(75.0, rule) is False

    @pytest.mark.asyncio
    async def test_check_threshold_less_than(self):
        """Test threshold check with < operator."""
        mock_db = AsyncMock()
        engine = AlertEngine(mock_db)

        rule = MagicMock()
        rule.operator = "<"
        rule.threshold = 20.0

        assert engine._check_threshold(15.0, rule) is True
        assert engine._check_threshold(20.0, rule) is False
        assert engine._check_threshold(25.0, rule) is False

    @pytest.mark.asyncio
    async def test_check_threshold_equals(self):
        """Test threshold check with == operator."""
        mock_db = AsyncMock()
        engine = AlertEngine(mock_db)

        rule = MagicMock()
        rule.operator = "=="
        rule.threshold = 50.0

        assert engine._check_threshold(50.0, rule) is True
        assert engine._check_threshold(51.0, rule) is False

    @pytest.mark.asyncio
    async def test_check_threshold_invalid_operator(self):
        """Test threshold check with invalid operator."""
        mock_db = AsyncMock()
        engine = AlertEngine(mock_db)

        rule = MagicMock()
        rule.operator = "invalid"
        rule.threshold = 50.0

        assert engine._check_threshold(50.0, rule) is False

    @pytest.mark.asyncio
    async def test_check_threshold_none_threshold(self):
        """Test threshold check with None threshold."""
        mock_db = AsyncMock()
        engine = AlertEngine(mock_db)

        rule = MagicMock()
        rule.operator = ">"
        rule.threshold = None

        assert engine._check_threshold(100.0, rule) is False


class TestNotificationService:
    """Tests for notification service."""

    @pytest.mark.asyncio
    async def test_send_webhook(self):
        """Test webhook notification."""
        mock_rule = MagicMock()
        mock_rule.webhook_url = "https://example.com/webhook"
        mock_rule.name = "Test Rule"
        mock_rule.threshold = 80.0
        mock_rule.operator = ">"

        mock_server = MagicMock()
        mock_server.id = uuid4()
        mock_server.hostname = "test-server"
        mock_server.bmc_ip = "192.168.1.1"

        mock_alert = MagicMock()
        mock_alert.severity = AlertSeverity.WARNING
        mock_alert.sensor_name = "CPU Temp"
        mock_alert.triggered_value = 85.0
        mock_alert.created_at = datetime.utcnow()

        service = NotificationService()

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            await service._send_webhook(mock_rule, mock_server, mock_alert)

            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_webhook_no_url(self):
        """Test webhook notification with no URL."""
        mock_rule = MagicMock()
        mock_rule.webhook_url = None

        mock_server = MagicMock()
        mock_alert = MagicMock()

        service = NotificationService()

        # Should not raise error when no webhook URL is configured
        await service._send_webhook(mock_rule, mock_server, mock_alert)

    def test_send_email_not_configured(self):
        """Test email notification when SMTP not configured."""
        mock_rule = MagicMock()
        mock_rule.notify_email = True
        mock_rule.name = "Test Rule"

        mock_server = MagicMock()
        mock_alert = MagicMock()

        service = NotificationService()

        with patch('app.services.notification.settings') as mock_settings:
            mock_settings.SMTP_HOST = None

            with pytest.raises(NotImplementedError):
                import asyncio
                asyncio.run(service._send_email(mock_rule, mock_server, mock_alert))