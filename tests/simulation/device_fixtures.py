"""
Device detection mock fixtures for simulating various device states.

Provides pre-built detection responses and pytest fixtures for mocking
the DeviceDetector without requiring real hardware.

Usage in tests:
    def test_something(mock_device_detector):
        # DeviceDetector.detect_device is now mocked
        # Returns "detected" for esp32/docker, "not_detected" for ssh types
        ...

    def test_custom(mock_device_detector_factory):
        # Create a custom detector mock
        mock = mock_device_detector_factory({
            "esp32_usb": DEVICE_RESPONSES["esp32_usb_detected"],
            "docker_local": DEVICE_RESPONSES["docker_not_running"],
        })
        ...
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Pre-built device detection responses
# ---------------------------------------------------------------------------

DEVICE_RESPONSES: Dict[str, Dict[str, Any]] = {
    # ESP32 USB - detected
    "esp32_usb_detected": {
        "status": "detected",
        "connection_info": {"port": "/dev/ttyACM1"},
        "details": {
            "vid": "0x1a86",
            "pid": "0x55d3",
            "serial_number": "TEST001",
            "description": "USB Single Serial (simulated)",
        },
    },
    # ESP32 USB - not detected
    "esp32_usb_not_detected": {
        "status": "not_detected",
        "details": {"error": "No matching USB serial device found"},
    },
    # ESP32 USB - port busy
    "esp32_usb_port_busy": {
        "status": "error",
        "details": {"error": "Serial port /dev/ttyACM1 is busy (used by another process)"},
    },
    # Himax USB - detected
    "himax_usb_detected": {
        "status": "detected",
        "connection_info": {"port": "/dev/ttyACM0"},
        "details": {
            "vid": "0x1a86",
            "pid": "0x55d3",
            "serial_number": "TEST001",
            "description": "USB Single Serial (simulated)",
        },
    },
    # Docker local - available
    "docker_local_detected": {
        "status": "detected",
        "connection_info": {"docker_host": "unix:///var/run/docker.sock"},
        "details": {
            "docker_version": "24.0.7",
            "compose_version": "2.23.0",
        },
    },
    # Docker local - daemon not running
    "docker_not_running": {
        "status": "not_detected",
        "details": {"error": "Docker daemon is not running"},
    },
    # Docker local - not installed
    "docker_not_installed": {
        "status": "not_detected",
        "details": {"error": "Docker is not installed"},
    },
    # Docker remote - manual required
    "docker_remote_manual": {
        "status": "manual_required",
        "details": {
            "fields": ["host", "username", "password"],
            "description": "Enter SSH credentials for remote Docker host",
        },
    },
    # SSH device - manual required
    "ssh_manual": {
        "status": "manual_required",
        "details": {
            "fields": ["host", "username", "password"],
            "description": "Enter SSH credentials",
        },
    },
    # SSH device - connection failed
    "ssh_connection_failed": {
        "status": "error",
        "details": {"error": "SSH connection refused: Connection timed out after 30s"},
    },
    # SSH device - auth failed
    "ssh_auth_failed": {
        "status": "error",
        "details": {"error": "SSH authentication failed: Invalid credentials"},
    },
    # reCamera - detected via mDNS
    "recamera_detected": {
        "status": "detected",
        "connection_info": {
            "host": "192.168.42.1",
            "username": "root",
            "port": 22,
        },
        "details": {
            "hostname": "recamera-abc123",
            "discovered_via": "mdns",
        },
    },
    # reCamera - not found
    "recamera_not_found": {
        "status": "not_detected",
        "details": {"error": "No reCamera device found on network"},
    },
    # Script - environment ready
    "script_env_ready": {
        "status": "detected",
        "connection_info": {},
        "details": {
            "python": True,
            "node": True,
            "npm": True,
        },
    },
    # Script - missing dependencies
    "script_missing_deps": {
        "status": "error",
        "details": {
            "error": "Required command not found: node",
            "missing": ["node", "npm"],
        },
    },
    # Manual - always ready
    "manual_ready": {
        "status": "manual",
        "details": {"description": "Follow manual instructions"},
    },
    # HA Integration - detected
    "ha_detected": {
        "status": "manual_required",
        "details": {
            "fields": ["host", "username", "password", "ha_url", "ha_token"],
            "description": "Enter Home Assistant connection details",
        },
    },
}

# ---------------------------------------------------------------------------
# Connection info templates for deployment tests
# ---------------------------------------------------------------------------

CONNECTION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "esp32_usb": {"port": "/dev/ttyACM1"},
    "himax_usb": {"port": "/dev/ttyACM0"},
    "docker_local": {"docker_host": "unix:///var/run/docker.sock"},
    "docker_remote": {
        "host": "192.168.1.100",
        "username": "user",
        "password": "pass",
        "port": 22,
    },
    "ssh_deb": {
        "host": "192.168.1.200",
        "username": "root",
        "password": "root",
        "port": 22,
    },
    "recamera_cpp": {
        "host": "192.168.42.1",
        "username": "root",
        "password": "recamera",
        "port": 22,
    },
    "recamera_nodered": {
        "host": "192.168.42.1",
        "username": "root",
        "password": "recamera",
        "port": 22,
        "nodered_host": "192.168.42.1",
    },
    "script": {},
    "manual": {},
    "preview": {},
    "serial_camera": {"port": "/dev/ttyACM0"},
    "ha_integration": {
        "host": "192.168.1.50",
        "username": "root",
        "password": "pass",
        "ha_url": "http://192.168.1.50:8123",
        "ha_token": "test-token-xxx",
    },
}


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


def _build_detector_mock(response_map: Dict[str, Dict[str, Any]]) -> AsyncMock:
    """Build a mock DeviceDetector.detect_device that returns responses by config.type."""

    async def _mock_detect(config):
        device_type = config.type
        if device_type in response_map:
            return response_map[device_type]
        # Default: return manual_required for unknown types
        return {
            "status": "manual_required",
            "details": {"description": f"Simulated manual for {device_type}"},
        }

    mock = AsyncMock(side_effect=_mock_detect)
    return mock


@pytest.fixture
def mock_device_detector():
    """Mock DeviceDetector with sensible defaults: USB/Docker detected, SSH manual.

    All detection calls are intercepted - no real hardware access.
    """
    default_responses = {
        "esp32_usb": DEVICE_RESPONSES["esp32_usb_detected"],
        "himax_usb": DEVICE_RESPONSES["himax_usb_detected"],
        "docker_local": DEVICE_RESPONSES["docker_local_detected"],
        "docker_remote": DEVICE_RESPONSES["docker_remote_manual"],
        "ssh_deb": DEVICE_RESPONSES["ssh_manual"],
        "recamera_cpp": DEVICE_RESPONSES["recamera_detected"],
        "recamera_nodered": DEVICE_RESPONSES["recamera_detected"],
        "script": DEVICE_RESPONSES["script_env_ready"],
        "manual": DEVICE_RESPONSES["manual_ready"],
        "ha_integration": DEVICE_RESPONSES["ha_detected"],
    }
    mock = _build_detector_mock(default_responses)
    with patch(
        "provisioning_station.services.device_detector.DeviceDetector.detect_device",
        mock,
    ):
        yield mock


@pytest.fixture
def mock_device_detector_factory():
    """Factory fixture for custom device detection responses.

    Usage:
        def test_docker_offline(mock_device_detector_factory):
            mock = mock_device_detector_factory({
                "docker_local": DEVICE_RESPONSES["docker_not_running"],
            })
            # ... test with Docker unavailable
    """

    def _factory(response_map: Dict[str, Dict[str, Any]]):
        mock = _build_detector_mock(response_map)
        patcher = patch(
            "provisioning_station.services.device_detector.DeviceDetector.detect_device",
            mock,
        )
        patcher.start()
        return mock, patcher

    yield _factory
