"""Tests for discovery service."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import ipaddress

from app.services.discovery import DiscoveryService
from app.models.discovery import DiscoveryJob, DiscoveryStatus


@pytest.mark.asyncio
async def test_ip_network_parsing():
    """Test CIDR parsing."""
    # Valid CIDR
    network = ipaddress.ip_network("192.168.1.0/24", strict=False)
    assert str(network) == "192.168.1.0/24"

    # Invalid CIDR should raise ValueError
    with pytest.raises(ValueError):
        ipaddress.ip_network("invalid-cidr", strict=False)


@pytest.mark.asyncio
async def test_is_port_open():
    """Test port checking."""
    mock_db = AsyncMock()
    service = DiscoveryService(mock_db)

    with patch('asyncio.open_connection') as mock_open:
        # Port open
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)

        result = await service._is_port_open("192.168.1.1", 443)
        assert result is True
        assert mock_writer.close.called

        # Port closed (timeout)
        mock_open.side_effect = asyncio.TimeoutError()
        result = await service._is_port_open("192.168.1.1", 443)
        assert result is False


@pytest.mark.asyncio
async def test_start_discovery():
    """Test discovery workflow."""
    mock_db = AsyncMock()
    service = DiscoveryService(mock_db)

    mock_job = MagicMock()
    mock_job.id = "job-1"
    mock_job.network_range = "192.168.1.0/30"
    mock_job.ports = [443]
    mock_job.status = DiscoveryStatus.PENDING

    with patch.object(service, '_scan_network', return_value=[{"ip": "192.168.1.1", "port": 443}]):
        await service.start_discovery(mock_job)

    assert mock_job.status == DiscoveryStatus.COMPLETED
    assert mock_job.device_count == 1
    assert mock_db.commit.called