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
    SolutionVersioning,
    VersionSummary,
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
    "SolutionVersioning",
    "VersionSummary",
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
