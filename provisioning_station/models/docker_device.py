"""
Docker device management models
"""

from typing import List, Optional
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
