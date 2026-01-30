"""
WebSocket Contract Tests

These tests verify that WebSocket message structures are consistent
between the backend models and frontend expectations.

Frontend reference: frontend/src/modules/api.js LogsWebSocket class
Backend reference: provisioning_station/models/websocket.py
"""

import pytest
from pydantic import ValidationError

from provisioning_station.models.websocket import (
    WSDeploymentCompletedMessage,
    WSDeviceCompletedMessage,
    WSDeviceStartedMessage,
    WSDockerNotInstalledMessage,
    WSLogMessage,
    WSPingMessage,
    WSPongMessage,
    WSPreCheckFailedMessage,
    WSPreCheckPassedMessage,
    WSPreCheckStartedMessage,
    WSProgressMessage,
    WSStatusMessage,
    WS_MESSAGE_TYPES,
    create_log_message,
    create_progress_message,
    create_status_message,
    parse_ws_message,
)


class TestWSMessageTypes:
    """Tests for WebSocket message type definitions."""

    def test_all_message_types_defined(self):
        """Verify all expected message types are in WS_MESSAGE_TYPES."""
        expected_types = [
            "log",
            "status",
            "progress",
            "device_started",
            "pre_check_started",
            "pre_check_passed",
            "pre_check_failed",
            "device_completed",
            "deployment_completed",
            "docker_not_installed",
            "ping",
            "pong",
        ]

        for msg_type in expected_types:
            assert msg_type in WS_MESSAGE_TYPES, f"Missing message type: {msg_type}"

    def test_no_unexpected_message_types(self):
        """Verify no unexpected message types are defined."""
        expected_count = 12  # log, status, progress, device_started, etc.
        assert len(WS_MESSAGE_TYPES) == expected_count, (
            f"Expected {expected_count} message types, got {len(WS_MESSAGE_TYPES)}"
        )


class TestWSLogMessage:
    """Tests for log message model."""

    def test_valid_log_message(self):
        """Test creating a valid log message."""
        msg = WSLogMessage(
            message="Starting deployment",
            level="info",
            device_id="warehouse",
        )

        assert msg.type == "log"
        assert msg.message == "Starting deployment"
        assert msg.level == "info"
        assert msg.device_id == "warehouse"

    def test_log_message_defaults(self):
        """Test log message default values."""
        msg = WSLogMessage(message="Test")

        assert msg.type == "log"
        assert msg.level == "info"
        assert msg.device_id is None
        assert msg.timestamp is None

    def test_log_message_levels(self):
        """Test all valid log levels."""
        valid_levels = ["info", "warning", "error", "debug", "success"]

        for level in valid_levels:
            msg = WSLogMessage(message="Test", level=level)
            assert msg.level == level

    def test_invalid_log_level(self):
        """Test that invalid log level raises error."""
        with pytest.raises(ValidationError):
            WSLogMessage(message="Test", level="invalid")

    def test_log_message_serialization(self):
        """Test log message JSON serialization."""
        msg = WSLogMessage(
            message="Test",
            level="info",
            device_id="warehouse",
            timestamp="2024-01-15T10:30:00Z",
        )

        data = msg.model_dump()
        assert data["type"] == "log"
        assert data["message"] == "Test"
        assert data["level"] == "info"
        assert data["device_id"] == "warehouse"


class TestWSStatusMessage:
    """Tests for status message model."""

    def test_valid_status_message(self):
        """Test creating a valid status message."""
        msg = WSStatusMessage(status="running", device_id="warehouse")

        assert msg.type == "status"
        assert msg.status == "running"
        assert msg.device_id == "warehouse"

    def test_all_valid_statuses(self):
        """Test all valid status values."""
        valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]

        for status in valid_statuses:
            msg = WSStatusMessage(status=status)
            assert msg.status == status

    def test_invalid_status(self):
        """Test that invalid status raises error."""
        with pytest.raises(ValidationError):
            WSStatusMessage(status="invalid")


class TestWSProgressMessage:
    """Tests for progress message model."""

    def test_valid_progress_message(self):
        """Test creating a valid progress message."""
        msg = WSProgressMessage(
            progress=45.5,
            device_id="warehouse",
            step="Pulling images",
            current_step=2,
            total_steps=5,
        )

        assert msg.type == "progress"
        assert msg.progress == 45.5
        assert msg.device_id == "warehouse"
        assert msg.step == "Pulling images"
        assert msg.current_step == 2
        assert msg.total_steps == 5

    def test_progress_bounds(self):
        """Test progress value bounds."""
        # Valid bounds
        WSProgressMessage(progress=0)
        WSProgressMessage(progress=100)
        WSProgressMessage(progress=50.5)

        # Invalid bounds
        with pytest.raises(ValidationError):
            WSProgressMessage(progress=-1)

        with pytest.raises(ValidationError):
            WSProgressMessage(progress=101)


class TestWSDeviceMessages:
    """Tests for device-related messages."""

    def test_device_started_message(self):
        """Test device started message."""
        msg = WSDeviceStartedMessage(
            device_id="warehouse",
            device_name="WMS Backend",
        )

        assert msg.type == "device_started"
        assert msg.device_id == "warehouse"
        assert msg.device_name == "WMS Backend"

    def test_device_completed_message(self):
        """Test device completed message."""
        msg = WSDeviceCompletedMessage(
            device_id="warehouse",
            status="completed",
            message="Deployment successful",
        )

        assert msg.type == "device_completed"
        assert msg.device_id == "warehouse"
        assert msg.status == "completed"

    def test_device_completed_statuses(self):
        """Test valid device completed statuses."""
        valid_statuses = ["completed", "failed", "skipped"]

        for status in valid_statuses:
            msg = WSDeviceCompletedMessage(device_id="test", status=status)
            assert msg.status == status


class TestWSPreCheckMessages:
    """Tests for pre-check messages."""

    def test_pre_check_started(self):
        """Test pre-check started message."""
        msg = WSPreCheckStartedMessage(device_id="warehouse")
        assert msg.type == "pre_check_started"
        assert msg.device_id == "warehouse"

    def test_pre_check_passed(self):
        """Test pre-check passed message."""
        msg = WSPreCheckPassedMessage(device_id="warehouse")
        assert msg.type == "pre_check_passed"
        assert msg.device_id == "warehouse"

    def test_pre_check_failed(self):
        """Test pre-check failed message."""
        msg = WSPreCheckFailedMessage(
            device_id="warehouse",
            reason="Docker not running",
        )
        assert msg.type == "pre_check_failed"
        assert msg.device_id == "warehouse"
        assert msg.reason == "Docker not running"


class TestWSDeploymentCompletedMessage:
    """Tests for deployment completed message."""

    def test_deployment_completed(self):
        """Test deployment completed message."""
        msg = WSDeploymentCompletedMessage(
            status="completed",
            completed_devices=["warehouse", "watcher"],
            failed_devices=[],
        )

        assert msg.type == "deployment_completed"
        assert msg.status == "completed"
        assert msg.completed_devices == ["warehouse", "watcher"]
        assert msg.failed_devices == []

    def test_deployment_failed(self):
        """Test deployment failed message."""
        msg = WSDeploymentCompletedMessage(
            status="failed",
            message="Deployment failed due to network error",
            completed_devices=["warehouse"],
            failed_devices=["watcher"],
        )

        assert msg.status == "failed"
        assert "network error" in msg.message.lower()


class TestWSDockerNotInstalledMessage:
    """Tests for Docker not installed message."""

    def test_docker_not_installed(self):
        """Test Docker not installed message."""
        msg = WSDockerNotInstalledMessage(
            device_id="warehouse",
            host="192.168.1.100",
            issue="not_installed",
            message="Docker is not installed on the remote device",
        )

        assert msg.type == "docker_not_installed"
        assert msg.device_id == "warehouse"
        assert msg.host == "192.168.1.100"
        assert msg.issue == "not_installed"

    def test_docker_issues(self):
        """Test all Docker issue types."""
        valid_issues = ["not_installed", "not_running", "permission_denied"]

        for issue in valid_issues:
            msg = WSDockerNotInstalledMessage(
                device_id="test",
                host="localhost",
                issue=issue,
            )
            assert msg.issue == issue


class TestWSHeartbeatMessages:
    """Tests for heartbeat (ping/pong) messages."""

    def test_ping_message(self):
        """Test ping message."""
        msg = WSPingMessage()
        assert msg.type == "ping"

    def test_pong_message(self):
        """Test pong message."""
        msg = WSPongMessage()
        assert msg.type == "pong"


class TestMessageFactoryFunctions:
    """Tests for message factory functions."""

    def test_create_log_message(self):
        """Test create_log_message helper."""
        msg = create_log_message(
            message="Test message",
            level="warning",
            device_id="warehouse",
        )

        assert isinstance(msg, WSLogMessage)
        assert msg.message == "Test message"
        assert msg.level == "warning"
        assert msg.device_id == "warehouse"
        assert msg.timestamp is not None

    def test_create_status_message(self):
        """Test create_status_message helper."""
        msg = create_status_message(
            status="running",
            device_id="warehouse",
            message="Deploying...",
        )

        assert isinstance(msg, WSStatusMessage)
        assert msg.status == "running"
        assert msg.device_id == "warehouse"
        assert msg.message == "Deploying..."

    def test_create_progress_message(self):
        """Test create_progress_message helper."""
        msg = create_progress_message(
            progress=50.0,
            device_id="warehouse",
            step="Pulling images",
            current_step=2,
            total_steps=4,
        )

        assert isinstance(msg, WSProgressMessage)
        assert msg.progress == 50.0
        assert msg.device_id == "warehouse"
        assert msg.step == "Pulling images"
        assert msg.current_step == 2
        assert msg.total_steps == 4


class TestParseWSMessage:
    """Tests for message parsing function."""

    def test_parse_log_message(self):
        """Test parsing log message."""
        data = {
            "type": "log",
            "message": "Test",
            "level": "info",
        }

        msg = parse_ws_message(data)
        assert isinstance(msg, WSLogMessage)
        assert msg.message == "Test"

    def test_parse_status_message(self):
        """Test parsing status message."""
        data = {
            "type": "status",
            "status": "running",
        }

        msg = parse_ws_message(data)
        assert isinstance(msg, WSStatusMessage)
        assert msg.status == "running"

    def test_parse_progress_message(self):
        """Test parsing progress message."""
        data = {
            "type": "progress",
            "progress": 75.0,
        }

        msg = parse_ws_message(data)
        assert isinstance(msg, WSProgressMessage)
        assert msg.progress == 75.0

    def test_parse_unknown_type(self):
        """Test parsing unknown message type raises error."""
        data = {"type": "unknown_type"}

        with pytest.raises(ValueError) as exc_info:
            parse_ws_message(data)

        assert "Unknown WebSocket message type" in str(exc_info.value)

    def test_parse_all_message_types(self):
        """Test parsing all message types."""
        test_cases = [
            ({"type": "log", "message": "test"}, WSLogMessage),
            ({"type": "status", "status": "running"}, WSStatusMessage),
            ({"type": "progress", "progress": 50}, WSProgressMessage),
            ({"type": "device_started", "device_id": "test"}, WSDeviceStartedMessage),
            ({"type": "pre_check_started", "device_id": "test"}, WSPreCheckStartedMessage),
            ({"type": "pre_check_passed", "device_id": "test"}, WSPreCheckPassedMessage),
            ({"type": "pre_check_failed", "device_id": "test"}, WSPreCheckFailedMessage),
            (
                {"type": "device_completed", "device_id": "test", "status": "completed"},
                WSDeviceCompletedMessage,
            ),
            (
                {"type": "deployment_completed", "status": "completed"},
                WSDeploymentCompletedMessage,
            ),
            (
                {"type": "docker_not_installed", "device_id": "test", "host": "localhost"},
                WSDockerNotInstalledMessage,
            ),
            ({"type": "ping"}, WSPingMessage),
            ({"type": "pong"}, WSPongMessage),
        ]

        for data, expected_class in test_cases:
            msg = parse_ws_message(data)
            assert isinstance(msg, expected_class), f"Failed for type: {data['type']}"


class TestFrontendCompatibility:
    """Tests to ensure backend models match frontend expectations."""

    def test_log_message_matches_frontend_handler(self):
        """Verify log message structure matches frontend handler expectations."""
        # Frontend expects: { type: 'log', level, message, timestamp?, device_id? }
        msg = WSLogMessage(
            message="Test",
            level="info",
            timestamp="2024-01-15T10:30:00Z",
            device_id="warehouse",
        )

        data = msg.model_dump()

        # These fields are accessed in frontend LogsWebSocket
        assert "type" in data and data["type"] == "log"
        assert "message" in data
        assert "level" in data

    def test_status_message_matches_frontend_handler(self):
        """Verify status message matches frontend handler."""
        # Frontend emits status to listeners with { status }
        msg = WSStatusMessage(status="running")

        data = msg.model_dump()

        assert "type" in data and data["type"] == "status"
        assert "status" in data

    def test_progress_message_matches_frontend_handler(self):
        """Verify progress message matches frontend handler."""
        # Frontend emits progress to 'progress' listeners
        msg = WSProgressMessage(progress=50.0)

        data = msg.model_dump()

        assert "type" in data and data["type"] == "progress"
        assert "progress" in data

    def test_docker_not_installed_matches_frontend_handler(self):
        """Verify docker_not_installed message matches frontend handler."""
        # Frontend emits to 'docker_not_installed' listeners
        msg = WSDockerNotInstalledMessage(
            device_id="warehouse",
            host="192.168.1.100",
        )

        data = msg.model_dump()

        assert "type" in data and data["type"] == "docker_not_installed"
        # Frontend needs these for Docker install dialog
        assert "device_id" in data
        assert "host" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
