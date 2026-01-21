"""
Device Management API routes

Provides endpoints for managing deployed applications:
- List active deployments
- Application updates
- Kiosk mode configuration
- Deployment actions (start/stop/restart)
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.kiosk import (
    KioskStatus,
    KioskConfigRequest,
    KioskConfigResponse,
    UpdateRequest,
    UpdateResponse,
    ActiveDeployment,
    DeploymentAction,
    DeploymentActionResponse,
)
from ..services.kiosk_manager import kiosk_manager
from ..services.update_manager import update_manager
from ..services.deployment_history import deployment_history
from ..services.solution_manager import solution_manager

router = APIRouter(prefix="/api/device-management", tags=["device-management"])


@router.get("/active", response_model=List[ActiveDeployment])
async def list_active_deployments(
    solution_id: Optional[str] = Query(None, description="Filter by solution ID"),
):
    """
    List all active/deployed applications

    Returns deployments that have been successfully completed and may still be running.
    """
    try:
        # Get deployment history
        history = await deployment_history.get_history(
            solution_id=solution_id,
            limit=100,
        )

        active_deployments = []
        seen_deployments = set()

        for record in history:
            if record.status != "completed":
                continue

            # Create unique key for deployment
            key = f"{record.solution_id}:{record.device_id}"
            if key in seen_deployments:
                continue
            seen_deployments.add(key)

            # Get solution info
            solution = solution_manager.get_solution(record.solution_id)
            solution_name = solution.name if solution else record.solution_id
            solution_name_zh = solution.name_zh if solution else None

            # Determine app URL
            host = record.metadata.get("host") if record.metadata else None
            port = record.metadata.get("port", 8280) if record.metadata else 8280

            if host:
                app_url = f"http://{host}:{port}"
            else:
                app_url = f"http://localhost:{port}"

            # Get kiosk status
            kiosk_status = await kiosk_manager.get_status(record.deployment_id)

            # Determine deployment status
            status = await _check_deployment_status(record)

            active_deployments.append(ActiveDeployment(
                deployment_id=record.deployment_id,
                solution_id=record.solution_id,
                solution_name=solution_name,
                solution_name_zh=solution_name_zh,
                device_id=record.device_id,
                device_type=record.device_type,
                status=status,
                deployed_at=record.deployed_at,
                app_url=app_url,
                host=host,
                kiosk_enabled=kiosk_status.enabled if kiosk_status else False,
                kiosk_user=kiosk_status.kiosk_user if kiosk_status else None,
                connection_info=record.metadata.get("connection_info") if record.metadata else None,
            ))

        return active_deployments

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deployment_id}/status")
async def get_deployment_status(deployment_id: str):
    """Get the current status of a deployment"""
    try:
        history = await deployment_history.get_history(limit=100)
        record = next((r for r in history if r.deployment_id == deployment_id), None)

        if not record:
            raise HTTPException(status_code=404, detail="Deployment not found")

        status = await _check_deployment_status(record)

        return {
            "deployment_id": deployment_id,
            "status": status,
            "device_type": record.device_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{deployment_id}/action", response_model=DeploymentActionResponse)
async def perform_deployment_action(deployment_id: str, action: DeploymentAction):
    """
    Perform an action on a deployment

    Actions:
    - start: Start the container/service
    - stop: Stop the container/service
    - restart: Restart the container/service
    - update: Pull latest image and restart
    """
    try:
        history = await deployment_history.get_history(limit=100)
        record = next((r for r in history if r.deployment_id == deployment_id), None)

        if not record:
            raise HTTPException(status_code=404, detail="Deployment not found")

        if action.action == "update":
            result = await update_manager.update_deployment(
                deployment_id=deployment_id,
                password=action.password,
            )
            return DeploymentActionResponse(
                success=result.success,
                message=result.message,
                status="running" if result.success else "unknown",
            )

        elif action.action in ("start", "stop", "restart"):
            result = await update_manager.container_action(
                deployment_id=deployment_id,
                action=action.action,
                password=action.password,
            )
            return DeploymentActionResponse(
                success=result.success,
                message=result.message,
                status=result.new_version,  # Repurposed for status
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action.action}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deployment_id}/kiosk", response_model=KioskStatus)
async def get_kiosk_status(deployment_id: str):
    """Get Kiosk mode status for a deployment"""
    try:
        status = await kiosk_manager.get_status(deployment_id)
        if not status:
            return KioskStatus(deployment_id=deployment_id, enabled=False)
        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{deployment_id}/kiosk", response_model=KioskConfigResponse)
async def configure_kiosk(deployment_id: str, config: KioskConfigRequest):
    """
    Configure Kiosk mode for a deployment

    This will:
    - For enabled=True: Configure the device to auto-start the app in fullscreen on boot
    - For enabled=False: Remove the auto-start configuration
    """
    try:
        if config.enabled:
            result = await kiosk_manager.configure(
                deployment_id=deployment_id,
                kiosk_user=config.kiosk_user,
                app_url=config.app_url,
                password=config.password,
            )
        else:
            result = await kiosk_manager.unconfigure(
                deployment_id=deployment_id,
                kiosk_user=config.kiosk_user,
                password=config.password,
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{deployment_id}/kiosk", response_model=KioskConfigResponse)
async def remove_kiosk(deployment_id: str, kiosk_user: str = Query(...), password: Optional[str] = Query(None)):
    """Remove Kiosk mode configuration"""
    try:
        result = await kiosk_manager.unconfigure(
            deployment_id=deployment_id,
            kiosk_user=kiosk_user,
            password=password,
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{deployment_id}/update", response_model=UpdateResponse)
async def update_deployment(deployment_id: str, request: UpdateRequest):
    """
    Update a deployed application

    This will:
    1. Pull the latest Docker image
    2. Restart the container with the new image

    For remote deployments, SSH password may be required if not saved.
    """
    try:
        result = await update_manager.update_deployment(
            deployment_id=deployment_id,
            password=request.password,
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _check_deployment_status(record) -> str:
    """Check if a deployment is currently running"""
    try:
        import asyncio

        device_type = record.device_type
        metadata = record.metadata or {}

        if device_type == "docker_local":
            # Check local Docker container
            container_name = metadata.get("container_name", "")
            if not container_name:
                # Try to infer from solution
                container_name = f"{record.solution_id}_{record.device_id}"

            proc = await asyncio.create_subprocess_exec(
                "docker", "inspect", "-f", "{{.State.Running}}", container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                running = stdout.decode().strip().lower() == "true"
                return "running" if running else "stopped"

            return "unknown"

        elif device_type == "docker_remote":
            # For remote, we can't easily check without SSH connection
            # Return unknown or check via HTTP health endpoint
            host = metadata.get("host")
            port = metadata.get("port", 8280)

            if host:
                import httpx

                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        resp = await client.get(f"http://{host}:{port}/api/v1/health")
                        if resp.status_code < 500:
                            return "running"
                except Exception:
                    pass

            return "unknown"

        else:
            return "unknown"

    except Exception:
        return "unknown"
