"""
Version management models
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class VersionInfo(BaseModel):
    """Version information for a deployed device"""
    device_id: str
    device_type: str
    config_version: str  # Version from configuration file
    deployed_version: Optional[str] = None  # Runtime version (for Docker)
    available_version: Optional[str] = None  # Latest available version
    last_deployed: Optional[datetime] = None
    update_available: bool = False


class UpdateCheckResult(BaseModel):
    """Result of checking for available updates"""
    device_id: str
    current_version: Optional[str]
    target_version: str
    update_available: bool
    update_type: str  # "pull_image" | "reflash" | "reinstall" | "rerun"


class DeploymentRecord(BaseModel):
    """Record of a deployment"""
    deployment_id: str
    solution_id: str
    device_id: str
    device_type: str
    deployed_version: str  # Version from config at deployment time
    config_version: str  # Configuration file version
    status: str  # "completed" | "failed"
    deployed_at: datetime
    deployed_by: Optional[str] = None  # Optional user identifier
    metadata: Dict[str, Any] = {}  # Extra info (firmware path, image tag, etc.)


class SolutionVersioning(BaseModel):
    """Solution versioning configuration"""
    solution_version: str = "1.0.0"
    last_updated: Optional[str] = None


class VersionSummary(BaseModel):
    """Summary of version information for a solution"""
    solution_id: str
    solution_version: str
    devices: List[VersionInfo]
    last_deployment: Optional[datetime] = None
