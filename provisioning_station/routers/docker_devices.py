"""
Docker device management API routes
"""

from fastapi import APIRouter, HTTPException

from ..models.docker_device import (
    ConnectDeviceRequest,
    ContainersResponse,
    UpgradeRequest,
)
from ..services.docker_device_manager import docker_device_manager

router = APIRouter(prefix="/api/docker-devices", tags=["docker-devices"])


@router.post("/connect")
async def connect_device(request: ConnectDeviceRequest):
    """Test SSH connection and verify Docker is available"""
    try:
        device_info = await docker_device_manager.connect(request)
        return {
            "success": True,
            "device": device_info.model_dump(),
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/containers")
async def list_containers(request: ConnectDeviceRequest):
    """List Docker containers on the connected device"""
    try:
        containers = await docker_device_manager.list_containers(request)
        return {
            "success": True,
            "containers": [c.model_dump() for c in containers],
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upgrade")
async def upgrade_container(request: UpgradeRequest):
    """Pull latest image and recreate container"""
    try:
        result = await docker_device_manager.upgrade(request)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/container-action")
async def container_action(request: ConnectDeviceRequest, container_name: str, action: str):
    """Perform action on a container (start/stop/restart)"""
    try:
        result = await docker_device_manager.container_action(request, container_name, action)
        return result
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
