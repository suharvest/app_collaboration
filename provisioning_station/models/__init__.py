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
]
