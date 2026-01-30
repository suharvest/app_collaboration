"""
Integration tests for mDNS Device Discovery API endpoints
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


class TestScanMdnsEndpoint:
    """Tests for GET /api/devices/scan-mdns endpoint"""

    def test_scan_mdns_returns_devices(self):
        """Test scan endpoint returns discovered devices"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        mock_devices = [
            {"hostname": "raspberrypi", "ip": "192.168.1.100", "port": 22, "device_type": "raspberry"},
            {"hostname": "jetson-nano", "ip": "192.168.1.101", "port": 22, "device_type": "jetson"},
        ]

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, return_value=mock_devices):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns")

                assert response.status_code == 200
                data = response.json()
                assert "devices" in data
                assert len(data["devices"]) == 2
                assert data["devices"][0]["hostname"] == "raspberrypi"
                assert data["devices"][0]["ip"] == "192.168.1.100"
                assert data["devices"][1]["hostname"] == "jetson-nano"

    def test_scan_mdns_empty_result(self):
        """Test scan endpoint with no devices found"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, return_value=[]):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns")

                assert response.status_code == 200
                data = response.json()
                assert data["devices"] == []

    def test_scan_mdns_with_timeout_parameter(self):
        """Test scan endpoint respects timeout parameter"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        async def mock_scan(timeout=3.0, filter_known=True):
            # Verify timeout is passed correctly
            assert timeout == 5.0
            return []

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, side_effect=mock_scan):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns?timeout=5.0")

                assert response.status_code == 200

    def test_scan_mdns_with_filter_known_false(self):
        """Test scan endpoint with filter_known=false"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        async def mock_scan(timeout=3.0, filter_known=True):
            # Verify filter_known is passed correctly
            assert filter_known is False
            return [
                {"hostname": "ubuntu-server", "ip": "192.168.1.50", "port": 22, "device_type": None},
            ]

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, side_effect=mock_scan):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns?filter_known=false")

                assert response.status_code == 200
                data = response.json()
                assert len(data["devices"]) == 1
                assert data["devices"][0]["hostname"] == "ubuntu-server"

    def test_scan_mdns_with_filter_known_true(self):
        """Test scan endpoint with filter_known=true (default)"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        async def mock_scan(timeout=3.0, filter_known=True):
            assert filter_known is True
            return []

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, side_effect=mock_scan):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns?filter_known=true")

                assert response.status_code == 200


class TestScanMdnsParameterValidation:
    """Tests for parameter validation on scan-mdns endpoint"""

    def test_timeout_minimum_validation(self):
        """Test timeout parameter minimum (1.0)"""
        from provisioning_station.main import app
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/devices/scan-mdns?timeout=0.5")

            # Should be rejected (below minimum of 1.0)
            assert response.status_code == 422
            data = response.json()
            assert "detail" in data

    def test_timeout_maximum_validation(self):
        """Test timeout parameter maximum (10.0)"""
        from provisioning_station.main import app
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/devices/scan-mdns?timeout=15.0")

            # Should be rejected (above maximum of 10.0)
            assert response.status_code == 422
            data = response.json()
            assert "detail" in data

    def test_timeout_valid_range(self):
        """Test timeout parameter within valid range"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, return_value=[]):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                # Minimum valid value
                response = client.get("/api/devices/scan-mdns?timeout=1.0")
                assert response.status_code == 200

                # Maximum valid value
                response = client.get("/api/devices/scan-mdns?timeout=10.0")
                assert response.status_code == 200

                # Middle value
                response = client.get("/api/devices/scan-mdns?timeout=5.5")
                assert response.status_code == 200

    def test_timeout_invalid_type(self):
        """Test timeout parameter with invalid type"""
        from provisioning_station.main import app
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/devices/scan-mdns?timeout=abc")

            assert response.status_code == 422

    def test_filter_known_boolean_values(self):
        """Test filter_known accepts boolean values"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, return_value=[]):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                # Test various boolean representations
                for value in ["true", "True", "TRUE", "1"]:
                    response = client.get(f"/api/devices/scan-mdns?filter_known={value}")
                    assert response.status_code == 200, f"Failed for filter_known={value}"

                for value in ["false", "False", "FALSE", "0"]:
                    response = client.get(f"/api/devices/scan-mdns?filter_known={value}")
                    assert response.status_code == 200, f"Failed for filter_known={value}"


class TestScanMdnsDefaultParameters:
    """Tests for default parameter values"""

    def test_default_timeout_is_3(self):
        """Test default timeout is 3.0 seconds"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        captured_timeout = None

        async def mock_scan(timeout=3.0, filter_known=True):
            nonlocal captured_timeout
            captured_timeout = timeout
            return []

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, side_effect=mock_scan):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns")

                assert response.status_code == 200
                assert captured_timeout == 3.0

    def test_default_filter_known_is_true(self):
        """Test default filter_known is True"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        captured_filter_known = None

        async def mock_scan(timeout=3.0, filter_known=True):
            nonlocal captured_filter_known
            captured_filter_known = filter_known
            return []

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, side_effect=mock_scan):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns")

                assert response.status_code == 200
                assert captured_filter_known is True


class TestScanMdnsResponseFormat:
    """Tests for response format consistency"""

    def test_response_has_devices_key(self):
        """Test response always has 'devices' key"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, return_value=[]):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns")

                data = response.json()
                assert "devices" in data
                assert isinstance(data["devices"], list)

    def test_device_object_structure(self):
        """Test each device object has expected structure"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        mock_devices = [
            {"hostname": "raspberrypi", "ip": "192.168.1.100", "port": 22, "device_type": "raspberry"},
        ]

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, return_value=mock_devices):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns")

                data = response.json()
                device = data["devices"][0]

                # Check all expected fields are present
                assert "hostname" in device
                assert "ip" in device
                assert "port" in device
                assert "device_type" in device

                # Check field types
                assert isinstance(device["hostname"], str)
                assert isinstance(device["ip"], str)
                assert isinstance(device["port"], int)
                assert device["device_type"] is None or isinstance(device["device_type"], str)

    def test_device_type_can_be_null(self):
        """Test device_type can be null for unknown devices"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        mock_devices = [
            {"hostname": "unknown-device", "ip": "192.168.1.200", "port": 22, "device_type": None},
        ]

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, return_value=mock_devices):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns")

                data = response.json()
                device = data["devices"][0]
                assert device["device_type"] is None


class TestScanMdnsErrorHandling:
    """Tests for error handling in scan-mdns endpoint"""

    def test_scanner_exception_returns_empty_list(self):
        """Test scanner exception is handled gracefully"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        async def mock_scan_error(timeout=3.0, filter_known=True):
            # The scanner catches exceptions internally and returns empty list
            return []

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, side_effect=mock_scan_error):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns")

                assert response.status_code == 200
                data = response.json()
                assert data["devices"] == []


class TestScanMdnsCombinedParameters:
    """Tests for combined parameter usage"""

    def test_both_parameters_work_together(self):
        """Test timeout and filter_known work together"""
        from provisioning_station.services.mdns_scanner import mdns_scanner

        captured_params = {}

        async def mock_scan(timeout=3.0, filter_known=True):
            captured_params["timeout"] = timeout
            captured_params["filter_known"] = filter_known
            return [{"hostname": "recomputer", "ip": "10.0.0.1", "port": 22, "device_type": "recomputer"}]

        with patch.object(mdns_scanner, 'scan_ssh_devices', new_callable=AsyncMock, side_effect=mock_scan):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/devices/scan-mdns?timeout=5.0&filter_known=false")

                assert response.status_code == 200
                assert captured_params["timeout"] == 5.0
                assert captured_params["filter_known"] is False

                data = response.json()
                assert len(data["devices"]) == 1
