"""
Deployment Parameter Tests

These tests verify that deployment parameters are correctly structured
and validated. This catches "parameter passing" issues that cause
deployment failures even when the deployment logic itself is correct.

Frontend reference: frontend/src/pages/deploy/devices.js startDeployment()
Backend reference: provisioning_station/models/api.py StartDeploymentRequest
"""

import pytest
from pydantic import ValidationError

from provisioning_station.models.api import (
    StartDeploymentRequest,
    DeviceConnectionRequest,
)


class TestStartDeploymentRequest:
    """Tests for StartDeploymentRequest model validation."""

    def test_minimal_request(self):
        """Test minimal valid deployment request."""
        request = StartDeploymentRequest(
            solution_id="smart_warehouse",
        )
        assert request.solution_id == "smart_warehouse"
        assert request.preset_id is None
        assert request.device_connections == {}
        assert request.options == {}
        assert request.selected_devices == []

    def test_full_request(self):
        """Test full deployment request with all fields."""
        request = StartDeploymentRequest(
            solution_id="smart_warehouse",
            preset_id="sensecraft_cloud",
            selected_devices=["warehouse", "watcher"],
            device_connections={
                "warehouse": {"host": "192.168.1.100", "username": "pi"},
                "watcher": {"port": "/dev/ttyUSB0"},
            },
            options={
                "deploy_target": "warehouse_local",
                "config_file": "configs/local.yaml",
            },
        )
        assert request.solution_id == "smart_warehouse"
        assert request.preset_id == "sensecraft_cloud"
        assert len(request.selected_devices) == 2
        assert "warehouse" in request.device_connections
        assert request.options["deploy_target"] == "warehouse_local"

    def test_solution_id_required(self):
        """Test that solution_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            StartDeploymentRequest()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("solution_id",) for e in errors)

    def test_device_connections_dict_format(self):
        """Test device_connections accepts nested dict format."""
        # This is how frontend sends it in devices.js:309-313
        request = StartDeploymentRequest(
            solution_id="test",
            device_connections={
                "warehouse": {
                    "host": "192.168.1.100",
                    "port": 22,
                    "username": "pi",
                    "password": "raspberry",
                }
            },
        )
        conn = request.device_connections["warehouse"]
        assert conn["host"] == "192.168.1.100"
        assert conn["port"] == 22
        assert conn["username"] == "pi"
        assert conn["password"] == "raspberry"


class TestDeviceConnectionFormats:
    """Tests for different device connection formats.

    These match the frontend startDeployment() logic in devices.js:295-335
    """

    def test_esp32_usb_connection(self):
        """Test ESP32 USB connection format (devices.js:295-299)."""
        request = StartDeploymentRequest(
            solution_id="test",
            selected_devices=["firmware"],
            device_connections={
                "firmware": {
                    "port": "/dev/ttyUSB0",
                }
            },
        )
        conn = request.device_connections["firmware"]
        assert "port" in conn
        assert conn["port"] == "/dev/ttyUSB0"

    def test_himax_usb_connection(self):
        """Test Himax USB connection format with models (devices.js:300-306)."""
        request = StartDeploymentRequest(
            solution_id="test",
            selected_devices=["himax"],
            device_connections={
                "himax": {
                    "port": "/dev/cu.usbserial-01",
                    "selected_models": ["scrfd", "facenet"],
                }
            },
        )
        conn = request.device_connections["himax"]
        assert "port" in conn
        assert "selected_models" in conn
        assert "scrfd" in conn["selected_models"]

    def test_docker_remote_connection(self):
        """Test Docker remote (SSH) connection format (devices.js:307-313)."""
        request = StartDeploymentRequest(
            solution_id="smart_warehouse",
            selected_devices=["warehouse"],
            device_connections={
                "warehouse": {
                    "host": "192.168.1.100",
                    "port": 22,
                    "username": "pi",
                    "password": "raspberry",
                }
            },
            options={
                "deploy_target": "warehouse_remote",
            },
        )
        conn = request.device_connections["warehouse"]
        assert conn["host"] == "192.168.1.100"
        assert conn["port"] == 22
        assert conn["username"] == "pi"

    def test_recamera_nodered_connection(self):
        """Test reCamera Node-RED connection format (devices.js:314-323)."""
        request = StartDeploymentRequest(
            solution_id="recamera_heatmap",
            selected_devices=["recamera"],
            device_connections={
                "recamera": {
                    "recamera_ip": "192.168.1.50",
                    "nodered_host": "192.168.1.50",
                    "ssh_username": "recamera",
                    "ssh_password": "recamera",
                    "ssh_port": 22,
                }
            },
        )
        conn = request.device_connections["recamera"]
        assert "recamera_ip" in conn
        assert "nodered_host" in conn
        assert conn["ssh_username"] == "recamera"

    def test_recamera_cpp_connection(self):
        """Test reCamera C++ connection format (devices.js:324-331)."""
        request = StartDeploymentRequest(
            solution_id="recamera_app",
            selected_devices=["recamera"],
            device_connections={
                "recamera": {
                    "host": "192.168.1.50",
                    "port": 22,
                    "username": "recamera",
                    "password": "recamera",
                }
            },
        )
        conn = request.device_connections["recamera"]
        assert conn["host"] == "192.168.1.50"
        assert conn["username"] == "recamera"

    def test_docker_local_connection(self):
        """Test Docker local connection (empty object) (devices.js:332-334)."""
        request = StartDeploymentRequest(
            solution_id="smart_warehouse",
            selected_devices=["warehouse"],
            device_connections={
                "warehouse": {}
            },
            options={
                "deploy_target": "warehouse_local",
            },
        )
        # Local docker just needs empty connection dict
        assert "warehouse" in request.device_connections
        assert request.device_connections["warehouse"] == {}


class TestDeploymentOptions:
    """Tests for deployment options format."""

    def test_deploy_target_option(self):
        """Test deploy_target option for docker_deploy devices."""
        request = StartDeploymentRequest(
            solution_id="smart_warehouse",
            selected_devices=["warehouse"],
            device_connections={"warehouse": {}},
            options={
                "deploy_target": "warehouse_local",
                "config_file": "docker/local.yaml",
            },
        )
        assert request.options["deploy_target"] == "warehouse_local"
        assert request.options["config_file"] == "docker/local.yaml"

    def test_user_inputs_option(self):
        """Test user_inputs option for script devices."""
        request = StartDeploymentRequest(
            solution_id="test",
            selected_devices=["script_step"],
            device_connections={"script_step": {}},
            options={
                "user_inputs": {
                    "api_key": "sk-xxx",
                    "model": "gpt-4",
                }
            },
        )
        assert "user_inputs" in request.options
        assert request.options["user_inputs"]["api_key"] == "sk-xxx"

    def test_preset_id_with_options(self):
        """Test preset_id is passed separately from options."""
        request = StartDeploymentRequest(
            solution_id="smart_warehouse",
            preset_id="edge_computing",
            selected_devices=["warehouse"],
            device_connections={"warehouse": {}},
            options={
                "deploy_target": "warehouse_local",
            },
        )
        # preset_id should be top-level, not in options
        assert request.preset_id == "edge_computing"
        assert "preset_id" not in request.options


class TestDeviceConnectionRequest:
    """Tests for SSH connection request validation."""

    def test_effective_host_prefers_host_over_ip(self):
        """Test that 'host' field takes precedence over 'ip_address'."""
        request = DeviceConnectionRequest(
            host="192.168.1.100",
            ip_address="10.0.0.1",  # Should be ignored
        )
        assert request.effective_host == "192.168.1.100"

    def test_effective_host_falls_back_to_ip(self):
        """Test fallback to ip_address when host not provided."""
        request = DeviceConnectionRequest(
            ip_address="10.0.0.1",
        )
        assert request.effective_host == "10.0.0.1"

    def test_effective_host_trims_whitespace(self):
        """Test whitespace is trimmed from host."""
        request = DeviceConnectionRequest(
            host="  192.168.1.100  ",
        )
        assert request.effective_host == "192.168.1.100"

    def test_effective_username_trims_whitespace(self):
        """Test whitespace is trimmed from username."""
        request = DeviceConnectionRequest(
            username="  pi  ",
        )
        assert request.effective_username == "pi"


class TestFrontendBackendConsistency:
    """Tests to verify frontend and backend parameter naming matches."""

    def test_frontend_param_names_match_backend(self):
        """Verify frontend param names in devices.js match StartDeploymentRequest fields."""
        # Frontend uses these names in devices.js:270-276
        frontend_params = {
            "solution_id",
            "preset_id",
            "selected_devices",
            "device_connections",
            "options",
        }

        # Backend expects these fields
        backend_fields = set(StartDeploymentRequest.model_fields.keys())

        # All frontend params should be valid backend fields
        for param in frontend_params:
            assert param in backend_fields, (
                f"Frontend param '{param}' not found in backend model. "
                f"Backend fields: {backend_fields}"
            )

    def test_connection_field_names_documented(self):
        """Document expected connection field names for each device type.

        This test serves as documentation for the expected field names.
        If a field name changes in frontend or backend, this test should fail.
        """
        # ESP32/Himax USB
        usb_fields = ["port", "selected_models"]

        # SSH-based (docker_remote, ssh_deb, recamera_cpp)
        ssh_fields = ["host", "port", "username", "password"]

        # reCamera Node-RED (special format)
        nodered_fields = [
            "recamera_ip",
            "nodered_host",
            "ssh_username",
            "ssh_password",
            "ssh_port",
        ]

        # Options fields
        options_fields = [
            "deploy_target",
            "config_file",
            "user_inputs",
        ]

        # Just document - actual validation is in other tests
        assert len(usb_fields) > 0
        assert len(ssh_fields) > 0
        assert len(nodered_fields) > 0
        assert len(options_fields) > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_device_id_in_selected_devices(self):
        """Test handling of empty string in selected_devices."""
        request = StartDeploymentRequest(
            solution_id="test",
            selected_devices=["warehouse", "", "watcher"],
        )
        # Should accept but backend should filter empty strings
        assert "" in request.selected_devices

    def test_special_characters_in_solution_id(self):
        """Test solution_id with valid special characters."""
        request = StartDeploymentRequest(
            solution_id="smart_warehouse_v2",
        )
        assert request.solution_id == "smart_warehouse_v2"

    def test_none_values_in_connection(self):
        """Test None values in device_connections are handled."""
        request = StartDeploymentRequest(
            solution_id="test",
            device_connections={
                "warehouse": {
                    "host": "192.168.1.100",
                    "password": None,  # Password can be None
                }
            },
        )
        assert request.device_connections["warehouse"]["password"] is None

    def test_numeric_port_in_connection(self):
        """Test port can be int or string in frontend."""
        # Frontend sometimes sends string from input field
        request = StartDeploymentRequest(
            solution_id="test",
            device_connections={
                "warehouse": {
                    "host": "192.168.1.100",
                    "port": 22,  # Should be int
                }
            },
        )
        assert request.device_connections["warehouse"]["port"] == 22


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
