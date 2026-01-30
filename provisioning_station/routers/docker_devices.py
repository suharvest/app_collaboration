"""
Docker device management API routes
"""

from fastapi import APIRouter, HTTPException, Query

from ..models.docker_device import (
    ConnectDeviceRequest,
    UpgradeRequest,
)
from ..services.docker_device_manager import docker_device_manager

router = APIRouter(prefix="/api/docker-devices", tags=["docker-devices"])


# ============================================
# Local Docker Endpoints
# ============================================


@router.get("/local/check")
async def check_local_docker():
    """Check if Docker is available on local machine"""
    try:
        device_info = await docker_device_manager.check_local_docker()
        return {
            "success": True,
            "device": device_info.model_dump(),
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/local/containers")
async def list_local_containers():
    """List Docker containers on local machine"""
    try:
        containers = await docker_device_manager.list_local_containers()
        return {
            "success": True,
            "containers": [c.model_dump() for c in containers],
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/local/managed-apps")
async def list_local_managed_apps():
    """List SenseCraft-managed applications on local machine"""
    try:
        apps = await docker_device_manager.list_local_managed_apps()
        return {
            "success": True,
            "apps": [app.model_dump() for app in apps],
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/local/container-action")
async def local_container_action(container_name: str, action: str):
    """Perform action on a local container (start/stop/restart)"""
    try:
        result = await docker_device_manager.local_container_action(
            container_name, action
        )
        return result
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# Remote Docker Endpoints (SSH)
# ============================================


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
async def container_action(
    request: ConnectDeviceRequest, container_name: str, action: str
):
    """Perform action on a container (start/stop/restart)"""
    try:
        result = await docker_device_manager.container_action(
            request, container_name, action
        )
        return result
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/managed-apps")
async def list_managed_apps(request: ConnectDeviceRequest):
    """List SenseCraft-managed applications on the device.

    Returns only containers that were deployed through SenseCraft Provisioning,
    identified by the sensecraft.managed label.
    """
    try:
        apps = await docker_device_manager.list_managed_apps(request)
        return {
            "success": True,
            "apps": [app.model_dump() for app in apps],
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# App Removal & Image Pruning Endpoints
# ============================================


@router.post("/local/remove-app")
async def local_remove_app(
    solution_id: str,
    container_names: str = Query(..., description="Comma-separated container names"),
    remove_images: bool = False,
    remove_volumes: bool = False,
):
    """Remove all containers for an app on local machine, optionally removing images and volumes"""
    try:
        names_list = [n.strip() for n in container_names.split(",") if n.strip()]
        if not names_list:
            raise ValueError("No container names provided")

        result = await docker_device_manager.local_remove_app(
            solution_id=solution_id,
            container_names=names_list,
            remove_images=remove_images,
            remove_volumes=remove_volumes,
        )
        return result
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/local/prune-images")
async def local_prune_images():
    """Remove all unused Docker images on local machine"""
    try:
        result = await docker_device_manager.local_prune_images()
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/remove-app")
async def remove_app(
    request: ConnectDeviceRequest,
    solution_id: str = Query(...),
    container_names: str = Query(..., description="Comma-separated container names"),
    remove_images: bool = False,
    remove_volumes: bool = False,
):
    """Remove all containers for an app on remote device, optionally removing images and volumes"""
    try:
        names_list = [n.strip() for n in container_names.split(",") if n.strip()]
        if not names_list:
            raise ValueError("No container names provided")

        result = await docker_device_manager.remove_app(
            connection=request,
            solution_id=solution_id,
            container_names=names_list,
            remove_images=remove_images,
            remove_volumes=remove_volumes,
        )
        return result
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/prune-images")
async def prune_images(request: ConnectDeviceRequest):
    """Remove all unused Docker images on remote device"""
    try:
        result = await docker_device_manager.prune_images(request)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
