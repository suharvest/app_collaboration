"""
Docker device management models
"""

from typing import Dict, List, Optional

from pydantic import BaseModel


class ConnectDeviceRequest(BaseModel):
    """Request to connect to a remote Docker device"""

    host: str
    port: int = 22
    username: str = "recomputer"
    password: str


class ContainerInfo(BaseModel):
    """Information about a Docker container on the device"""

    container_id: str
    name: str
    image: str
    current_tag: str  # Running version/tag
    config_tag: Optional[str] = None  # Expected version from solution config
    update_available: bool = False
    status: str  # running | exited | stopped
    ports: List[str] = []
    labels: Dict[str, str] = {}  # Container labels


class ManagedAppContainer(BaseModel):
    """Single container within a managed application"""

    container_id: str
    container_name: str
    image: str
    tag: str
    status: str  # running | exited | stopped
    ports: List[str] = []


class ManagedApp(BaseModel):
    """SenseCraft-managed application detected on device (grouped by solution)"""

    # SenseCraft metadata from labels
    solution_id: str
    solution_name: Optional[str] = None
    device_id: Optional[str] = None
    deployed_at: Optional[str] = None
    # Aggregated status: running if any container running, otherwise exited/stopped
    status: str  # running | exited | stopped
    # All containers in this application
    containers: List[ManagedAppContainer] = []
    # Aggregated ports from all containers
    ports: List[str] = []
    # Reconfigurable fields (populated from manifest if available)
    config_fields: Optional[List[Dict]] = None


class DeviceInfo(BaseModel):
    """Basic device information after connection"""

    hostname: str
    docker_version: str
    os_info: str = ""


class ContainersResponse(BaseModel):
    """Response for container listing"""

    device: DeviceInfo
    containers: List[ContainerInfo]


class UpgradeRequest(BaseModel):
    """Request to upgrade a container"""

    host: str
    port: int = 22
    username: str = "recomputer"
    password: str
    container_name: str
    compose_path: str
    project_name: Optional[str] = None
