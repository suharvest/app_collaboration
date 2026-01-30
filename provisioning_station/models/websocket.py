"""
WebSocket Message Models

Pydantic models for WebSocket message types used in deployment communication.
These models ensure type safety and validation for all WebSocket messages.

Frontend reference: frontend/src/modules/api.js LogsWebSocket class
"""

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class WSBaseMessage(BaseModel):
    """Base class for all WebSocket messages."""

    type: str


class WSLogMessage(WSBaseMessage):
    """Log message sent during deployment."""

    type: Literal["log"] = "log"
    level: Literal["info", "warning", "error", "debug", "success"] = "info"
    message: str
    timestamp: str | None = None
    device_id: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "log",
                "level": "info",
                "message": "Starting Docker deployment...",
                "timestamp": "2024-01-15T10:30:00Z",
                "device_id": "warehouse"
            }
        }
    )


class WSStatusMessage(WSBaseMessage):
    """Status update message."""

    type: Literal["status"] = "status"
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    device_id: str | None = None
    message: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "status",
                "status": "running",
                "device_id": "warehouse"
            }
        }
    )


class WSProgressMessage(WSBaseMessage):
    """Progress update message."""

    type: Literal["progress"] = "progress"
    progress: Annotated[float, Field(ge=0, le=100)]
    device_id: str | None = None
    step: str | None = None
    total_steps: int | None = None
    current_step: int | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "progress",
                "progress": 45.5,
                "device_id": "warehouse",
                "step": "Pulling Docker images",
                "current_step": 2,
                "total_steps": 5
            }
        }
    )


class WSDeviceStartedMessage(WSBaseMessage):
    """Device deployment started message."""

    type: Literal["device_started"] = "device_started"
    device_id: str
    device_name: str | None = None


class WSPreCheckStartedMessage(WSBaseMessage):
    """Pre-check started message."""

    type: Literal["pre_check_started"] = "pre_check_started"
    device_id: str


class WSPreCheckPassedMessage(WSBaseMessage):
    """Pre-check passed message."""

    type: Literal["pre_check_passed"] = "pre_check_passed"
    device_id: str


class WSPreCheckFailedMessage(WSBaseMessage):
    """Pre-check failed message."""

    type: Literal["pre_check_failed"] = "pre_check_failed"
    device_id: str
    reason: str | None = None


class WSDeviceCompletedMessage(WSBaseMessage):
    """Device deployment completed message."""

    type: Literal["device_completed"] = "device_completed"
    device_id: str
    status: Literal["completed", "failed", "skipped"]
    message: str | None = None


class WSDeploymentCompletedMessage(WSBaseMessage):
    """Entire deployment completed message."""

    type: Literal["deployment_completed"] = "deployment_completed"
    status: Literal["completed", "failed", "cancelled"]
    message: str | None = None
    completed_devices: list[str] | None = None
    failed_devices: list[str] | None = None


class WSDockerNotInstalledMessage(WSBaseMessage):
    """Docker not installed on remote device message."""

    type: Literal["docker_not_installed"] = "docker_not_installed"
    device_id: str
    host: str
    issue: Literal["not_installed", "not_running", "permission_denied"] = "not_installed"
    message: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "docker_not_installed",
                "device_id": "warehouse",
                "host": "192.168.1.100",
                "issue": "not_installed",
                "message": "Docker is not installed on the remote device"
            }
        }
    )


class WSPingMessage(WSBaseMessage):
    """Heartbeat ping message."""

    type: Literal["ping"] = "ping"


class WSPongMessage(WSBaseMessage):
    """Heartbeat pong response."""

    type: Literal["pong"] = "pong"


# Union type for all WebSocket messages (for validation)
WSMessage = Annotated[
    Union[
        WSLogMessage,
        WSStatusMessage,
        WSProgressMessage,
        WSDeviceStartedMessage,
        WSPreCheckStartedMessage,
        WSPreCheckPassedMessage,
        WSPreCheckFailedMessage,
        WSDeviceCompletedMessage,
        WSDeploymentCompletedMessage,
        WSDockerNotInstalledMessage,
        WSPingMessage,
        WSPongMessage,
    ],
    Field(discriminator="type"),
]


def create_log_message(
    message: str,
    level: str = "info",
    device_id: str | None = None,
    timestamp: datetime | None = None,
) -> WSLogMessage:
    """Create a log message with optional timestamp."""
    return WSLogMessage(
        message=message,
        level=level,
        device_id=device_id,
        timestamp=timestamp.isoformat() if timestamp else datetime.now().isoformat(),
    )


def create_status_message(
    status: str,
    device_id: str | None = None,
    message: str | None = None,
) -> WSStatusMessage:
    """Create a status update message."""
    return WSStatusMessage(
        status=status,
        device_id=device_id,
        message=message,
    )


def create_progress_message(
    progress: float,
    device_id: str | None = None,
    step: str | None = None,
    current_step: int | None = None,
    total_steps: int | None = None,
) -> WSProgressMessage:
    """Create a progress update message."""
    return WSProgressMessage(
        progress=progress,
        device_id=device_id,
        step=step,
        current_step=current_step,
        total_steps=total_steps,
    )


def parse_ws_message(data: dict) -> WSMessage:
    """
    Parse a WebSocket message dict into the appropriate Pydantic model.

    Raises:
        ValueError: If the message type is unknown or data is invalid
    """
    msg_type = data.get("type")

    type_map = {
        "log": WSLogMessage,
        "status": WSStatusMessage,
        "progress": WSProgressMessage,
        "device_started": WSDeviceStartedMessage,
        "pre_check_started": WSPreCheckStartedMessage,
        "pre_check_passed": WSPreCheckPassedMessage,
        "pre_check_failed": WSPreCheckFailedMessage,
        "device_completed": WSDeviceCompletedMessage,
        "deployment_completed": WSDeploymentCompletedMessage,
        "docker_not_installed": WSDockerNotInstalledMessage,
        "ping": WSPingMessage,
        "pong": WSPongMessage,
    }

    if msg_type not in type_map:
        raise ValueError(f"Unknown WebSocket message type: {msg_type}")

    return type_map[msg_type](**data)


# Export message types list for validation
WS_MESSAGE_TYPES = [
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
