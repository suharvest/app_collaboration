"""
Pydantic models for Provisioning Station
"""

from .api import (
    DeploymentStatusResponse,
    DetectedDevice,
    SolutionDetail,
    SolutionSummary,
    StartDeploymentRequest,
)
from .deployment import (
    Deployment,
    DeploymentStatus,
    DeviceDeployment,
    LogEntry,
    StepStatus,
)
from .device import (
    DeploymentStep,
    DetectionConfig,
    DeviceConfig,
    DockerConfig,
    DockerRemoteConfig,
    FirmwareConfig,
    PackageConfig,
    SSHConfig,
)
from .docker_device import (
    ConnectDeviceRequest,
    ContainerInfo,
    ContainersResponse,
    DeviceInfo,
    UpgradeRequest,
)
from .kiosk import (
    ActiveDeployment,
    DeploymentAction,
    DeploymentActionResponse,
    KioskConfigRequest,
    KioskConfigResponse,
    KioskStatus,
    UpdateRequest,
    UpdateResponse,
)
from .solution import (
    DeviceRef,
    DeviceSection,
    MediaItem,
    RequiredDevice,
    Solution,
    SolutionDeployment,
    SolutionIntro,
    SolutionLinks,
    SolutionStats,
)
from .version import (
    DeploymentRecord,
    SolutionVersioning,
    StepRecord,
    UpdateCheckResult,
    VersionInfo,
    VersionSummary,
)
from .websocket import (
    WS_MESSAGE_TYPES,
    WSDeploymentCompletedMessage,
    WSDeviceCompletedMessage,
    WSDeviceStartedMessage,
    WSDockerNotInstalledMessage,
    WSLogMessage,
    WSMessage,
    WSPingMessage,
    WSPongMessage,
    WSPreCheckFailedMessage,
    WSPreCheckPassedMessage,
    WSPreCheckStartedMessage,
    WSProgressMessage,
    WSStatusMessage,
    create_log_message,
    create_progress_message,
    create_status_message,
    parse_ws_message,
)

__all__ = [
    # Solution models
    "Solution",
    "SolutionIntro",
    "SolutionDeployment",
    "DeviceRef",
    "DeviceSection",
    "MediaItem",
    "RequiredDevice",
    "SolutionStats",
    "SolutionLinks",
    # Device models
    "DeviceConfig",
    "DetectionConfig",
    "FirmwareConfig",
    "DockerConfig",
    "DockerRemoteConfig",
    "SSHConfig",
    "PackageConfig",
    "DeploymentStep",
    # Deployment models
    "Deployment",
    "DeviceDeployment",
    "DeploymentStatus",
    "StepStatus",
    "LogEntry",
    # API models
    "SolutionSummary",
    "SolutionDetail",
    "DetectedDevice",
    "StartDeploymentRequest",
    "DeploymentStatusResponse",
    # Version models
    "VersionInfo",
    "UpdateCheckResult",
    "DeploymentRecord",
    "StepRecord",
    "SolutionVersioning",
    "VersionSummary",
    # Docker device models
    "ConnectDeviceRequest",
    "ContainerInfo",
    "DeviceInfo",
    "ContainersResponse",
    "UpgradeRequest",
    # Kiosk models
    "KioskStatus",
    "KioskConfigRequest",
    "KioskConfigResponse",
    "UpdateRequest",
    "UpdateResponse",
    "ActiveDeployment",
    "DeploymentAction",
    "DeploymentActionResponse",
    # WebSocket models
    "WSLogMessage",
    "WSStatusMessage",
    "WSProgressMessage",
    "WSDeviceStartedMessage",
    "WSPreCheckStartedMessage",
    "WSPreCheckPassedMessage",
    "WSPreCheckFailedMessage",
    "WSDeviceCompletedMessage",
    "WSDeploymentCompletedMessage",
    "WSDockerNotInstalledMessage",
    "WSPingMessage",
    "WSPongMessage",
    "WSMessage",
    "WS_MESSAGE_TYPES",
    "create_log_message",
    "create_status_message",
    "create_progress_message",
    "parse_ws_message",
]
