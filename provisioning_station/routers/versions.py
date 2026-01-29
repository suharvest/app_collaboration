"""
Version management API endpoints
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..models.version import (
    DeploymentRecord,
    UpdateCheckResult,
    VersionInfo,
    VersionSummary,
)
from ..services.deployment_history import deployment_history
from ..services.version_manager import version_manager

router = APIRouter(prefix="/api/solutions", tags=["versions"])


@router.get("/{solution_id}/versions", response_model=VersionSummary)
async def get_solution_versions(solution_id: str):
    """
    Get version information for all devices in a solution.

    Returns the current deployed version, available version,
    and whether updates are available for each device.
    """
    result = await version_manager.get_solution_versions(solution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Solution not found")
    return result


@router.get("/{solution_id}/devices/{device_id}/version", response_model=VersionInfo)
async def get_device_version(solution_id: str, device_id: str):
    """
    Get version information for a specific device.
    """
    versions = await version_manager.get_solution_versions(solution_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Solution not found")

    device_version = next(
        (d for d in versions.devices if d.device_id == device_id), None
    )
    if not device_version:
        raise HTTPException(status_code=404, detail="Device not found")

    return device_version


@router.post("/{solution_id}/check-updates", response_model=List[UpdateCheckResult])
async def check_solution_updates(solution_id: str):
    """
    Check for available updates for all devices in a solution.

    Returns a list of update check results indicating which devices
    have updates available and what type of update is required.
    """
    results = await version_manager.check_all_updates(solution_id)
    if not results:
        raise HTTPException(
            status_code=404, detail="Solution not found or no devices configured"
        )
    return results


@router.get(
    "/{solution_id}/devices/{device_id}/check-update",
    response_model=UpdateCheckResult,
)
async def check_device_update(solution_id: str, device_id: str):
    """
    Check if an update is available for a specific device.
    """
    result = await version_manager.check_update_available(solution_id, device_id)
    if not result:
        raise HTTPException(status_code=404, detail="Device not found")
    return result


@router.get("/{solution_id}/deployment-history", response_model=List[DeploymentRecord])
async def get_deployment_history(
    solution_id: str,
    device_id: Optional[str] = None,
    limit: int = 10,
):
    """
    Get deployment history for a solution.

    Optionally filter by device_id and limit the number of results.
    """
    history = await deployment_history.get_history(
        solution_id=solution_id,
        device_id=device_id,
        limit=limit,
    )
    return history


@router.get("/{solution_id}/deployment-stats")
async def get_deployment_stats(solution_id: str):
    """
    Get deployment statistics for a solution.

    Returns total deployments, success/failure counts,
    and the timestamp of the last deployment.
    """
    stats = await deployment_history.get_solution_stats(solution_id)
    return stats
