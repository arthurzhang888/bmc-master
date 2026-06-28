# backend/app/services/notification.py
import json
import logging
from typing import Optional
import aiohttp
from aiosmtplib import send
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.models.alert import AlertRule, AlertHistory
from app.models.server import Server

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务"""

    async def send_alert_notification(
        self,
        rule: AlertRule,
        server: Server,
        alert: AlertHistory
    ):
        """发送告警通知"""
        if rule.notify_email:
            await self._send_email(rule, server, alert)

        if rule.notify_webhook and rule.webhook_url:
            await self._send_webhook(rule, server, alert)

    async def _send_email(
        self,
        rule: AlertRule,
        server: Server,
        alert: AlertHistory
    ):
        """发送邮件通知"""
        subject = f"[{alert.severity.value.upper()}] BMC Master Alert: {rule.name}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: {'#f59e0b' if alert.severity.value == 'warning' else '#ef4444'};">
                Alert: {rule.name}
            </h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Server:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{server.hostname or server.bmc_ip}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Sensor:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.sensor_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Value:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.triggered_value}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Threshold:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{rule.operator} {rule.threshold}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Time:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.created_at}</td>
                </tr>
            </table>
        </body>
        </html>
        """

        # Check if SMTP is configured
        if not getattr(settings, 'SMTP_HOST', None):
            logger.warning("Email notification skipped: SMTP_HOST not configured")
            raise NotImplementedError(
                "Email notifications require SMTP configuration. "
                "Set SMTP_HOST, SMTP_PORT, SMTP_FROM, and ALERT_EMAIL in environment."
            )

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = getattr(settings, 'SMTP_FROM', 'alerts@bmc-master.local')
            message["To"] = getattr(settings, 'ALERT_EMAIL', 'admin@example.com')
            message.attach(MIMEText(html_content, "html"))

            await send(
                message,
                hostname=settings.SMTP_HOST,
                port=getattr(settings, 'SMTP_PORT', 587),
                username=getattr(settings, 'SMTP_USER', None),
                password=getattr(settings, 'SMTP_PASSWORD', None),
                start_tls=True
            )
            logger.info(f"Alert email sent: {subject}")
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
            raise

    async def _send_webhook(
        self,
        rule: AlertRule,
        server: Server,
        alert: AlertHistory
    ):
        """发送 Webhook 通知"""
        if not rule.webhook_url:
            return

        payload = {
            "alert_name": rule.name,
            "severity": alert.severity.value,
            "server": {
                "id": str(server.id),
                "hostname": server.hostname,
                "ip": server.bmc_ip
            },
            "sensor": alert.sensor_name,
            "value": float(alert.triggered_value),
            "threshold": float(rule.threshold) if rule.threshold else None,
            "timestamp": alert.created_at.isoformat() if alert.created_at else None
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    rule.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status >= 400:
                        logger.error(f"Webhook failed: {response.status} - {await response.text()}")
            except Exception as e:
                logger.error(f"Webhook error: {e}")
