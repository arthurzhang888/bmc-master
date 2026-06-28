"""Tests for BMC adapters (Phase 1)."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.adapters.base import BMCAdapter, SensorReading, SELEntry
from app.adapters.factory import BMCAdapterFactory
from app.adapters.redfish import RedfishAdapter
from app.adapters.ipmi import IPMIAdapter


class TestBMCAdapterFactory:
    """Tests for BMC adapter factory."""

    @pytest.mark.asyncio
    async def test_create_redfish_first(self):
        """Test factory tries Redfish first."""
        with patch.object(RedfishAdapter, 'probe', return_value=True) as mock_redfish_probe:
            with patch.object(IPMIAdapter, 'probe', return_value=False):
                adapter, protocol = await BMCAdapterFactory.create("192.168.1.1", "admin", "password")

                assert mock_redfish_probe.called
                assert protocol == "redfish"
                assert isinstance(adapter, RedfishAdapter)

    @pytest.mark.asyncio
    async def test_create_fallback_to_ipmi(self):
        """Test factory falls back to IPMI when Redfish fails."""
        with patch.object(RedfishAdapter, 'probe', return_value=False):
            with patch.object(IPMIAdapter, 'probe', return_value=True) as mock_ipmi_probe:
                adapter, protocol = await BMCAdapterFactory.create("192.168.1.1", "admin", "password")

                assert mock_ipmi_probe.called
                assert protocol == "ipmi"
                assert isinstance(adapter, IPMIAdapter)

    @pytest.mark.asyncio
    async def test_create_raises_error_when_both_fail(self):
        """Test factory raises error when both protocols fail."""
        with patch.object(RedfishAdapter, 'probe', return_value=False):
            with patch.object(IPMIAdapter, 'probe', return_value=False):
                with pytest.raises(ConnectionError):
                    await BMCAdapterFactory.create("192.168.1.1", "admin", "password")


class TestRedfishAdapter:
    """Tests for Redfish adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = RedfishAdapter("192.168.1.1", "admin", "password")
        assert adapter.host == "192.168.1.1"
        assert adapter.username == "admin"
        assert adapter.password == "password"

    @pytest.mark.asyncio
    async def test_probe_success(self):
        """Test successful Redfish probe."""
        with patch('app.adapters.redfish.redfish.redfish_client') as mock_client:
            mock_redfish = MagicMock()
            mock_redfish.get.return_value = MagicMock(status=200)
            mock_client.return_value = mock_redfish

            result = await RedfishAdapter.probe("192.168.1.1", "admin", "password")
            assert result is True

    @pytest.mark.asyncio
    async def test_probe_failure(self):
        """Test failed Redfish probe."""
        with patch('app.adapters.redfish.redfish.redfish_client', side_effect=Exception("Connection failed")):
            result = await RedfishAdapter.probe("192.168.1.1", "admin", "password")
            assert result is False


class TestIPMIAdapter:
    """Tests for IPMI adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = IPMIAdapter("192.168.1.1", "admin", "password")
        assert adapter.host == "192.168.1.1"
        assert adapter.username == "admin"
        assert adapter.password == "password"

    @pytest.mark.asyncio
    async def test_probe_success(self):
        """Test successful IPMI probe."""
        with patch('app.adapters.ipmi.ipmi_command') as mock_cmd:
            mock_cmd.return_value = MagicMock()

            result = await IPMIAdapter.probe("192.168.1.1", "admin", "password")
            assert result is True

    @pytest.mark.asyncio
    async def test_probe_failure(self):
        """Test failed IPMI probe."""
        with patch('app.adapters.ipmi.ipmi_command.Command', side_effect=Exception("Connection failed")):
            result = await IPMIAdapter.probe("192.168.1.1", "admin", "password")
            assert result is False


class TestSensorReading:
    """Tests for SensorReading dataclass."""

    def test_sensor_reading_creation(self):
        """Test creating a sensor reading."""
        now = datetime.utcnow()
        reading = SensorReading(
            name="CPU1 Temp",
            value=45.5,
            unit="Celsius",
            sensor_type="temperature",
            timestamp=now
        )

        assert reading.name == "CPU1 Temp"
        assert reading.value == 45.5
        assert reading.unit == "Celsius"
        assert reading.sensor_type == "temperature"
        assert reading.timestamp == now


class TestSELEntry:
    """Tests for SELEntry dataclass."""

    def test_sel_entry_creation(self):
        """Test creating a SEL entry."""
        now = datetime.utcnow()
        entry = SELEntry(
            record_id="1",
            timestamp=now,
            sensor_name="Fan 1",
            sensor_type="fan",
            event_direction="Assertion",
            event_data="RPM below threshold",
            severity="warning"
        )

        assert entry.record_id == "1"
        assert entry.timestamp == now
        assert entry.sensor_name == "Fan 1"
        assert entry.severity == "warning"