"""
Pydantic models for Provisioning Station
"""

from .solution import (
    Solution,
    SolutionIntro,
    SolutionDeployment,
    DeviceRef,
    DeviceSection,
    MediaItem,
    RequiredDevice,
    SolutionStats,
    SolutionLinks,
)
from .device import (
    DeviceConfig,
    DetectionConfig,
    FirmwareConfig,
    DockerConfig,
    DockerRemoteConfig,
    SSHConfig,
    PackageConfig,
    DeploymentStep,
)
from .deployment import (
    Deployment,
    DeviceDeployment,
    DeploymentStatus,
    StepStatus,
    LogEntry,
)
from .api import (
    SolutionSummary,
    SolutionDetail,
    DetectedDevice,
    StartDeploymentRequest,
    DeploymentStatusResponse,
)
from .version import (
    VersionInfo,
    UpdateCheckResult,
    DeploymentRecord,
    StepRecord,
    SolutionVersioning,
    VersionSummary,
)
from .docker_device import (
    ConnectDeviceRequest,
    ContainerInfo,
    DeviceInfo,
    ContainersResponse,
    UpgradeRequest,
)
from .kiosk import (
    KioskStatus,
    KioskConfigRequest,
    KioskConfigResponse,
    UpdateRequest,
    UpdateResponse,
    ActiveDeployment,
    DeploymentAction,
    DeploymentActionResponse,
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
]
