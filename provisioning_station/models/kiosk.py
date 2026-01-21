"""
Kiosk mode management models
"""

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel


class KioskStatus(BaseModel):
    """Current Kiosk mode status for a deployment"""
    deployment_id: str
    enabled: bool = False
    kiosk_user: Optional[str] = None
    app_url: Optional[str] = None
    configured_at: Optional[datetime] = None


class KioskConfigRequest(BaseModel):
    """Request to configure Kiosk mode"""
    enabled: bool
    kiosk_user: str
    app_url: Optional[str] = None  # Will use deployment URL if not specified
    password: Optional[str] = None  # SSH password for remote deployments


class KioskConfigResponse(BaseModel):
    """Response from Kiosk configuration"""
    success: bool
    message: str
    status: Optional[KioskStatus] = None


class UpdateRequest(BaseModel):
    """Request to update a deployed application"""
    password: Optional[str] = None  # SSH password for remote deployments


class UpdateResponse(BaseModel):
    """Response from application update"""
    success: bool
    message: str
    new_version: Optional[str] = None


class ActiveDeployment(BaseModel):
    """Information about an active deployment"""
    deployment_id: str
    solution_id: str
    solution_name: str
    solution_name_zh: Optional[str] = None
    device_id: str
    device_type: str
    status: str  # "running" | "stopped" | "unknown"
    deployed_at: datetime
    app_url: str
    host: Optional[str] = None  # For remote deployments
    kiosk_enabled: bool = False
    kiosk_user: Optional[str] = None
    connection_info: Optional[Dict[str, Any]] = None  # Saved connection details


class DeploymentAction(BaseModel):
    """Action to perform on a deployment"""
    action: str  # "start" | "stop" | "restart" | "update"
    password: Optional[str] = None


class DeploymentActionResponse(BaseModel):
    """Response from deployment action"""
    success: bool
    message: str
    status: Optional[str] = None
