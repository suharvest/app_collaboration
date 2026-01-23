"""
API request/response models
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from .deployment import DeploymentStatus, StepStatus


class SolutionSummary(BaseModel):
    """Solution summary for listing"""
    id: str
    name: str
    name_zh: Optional[str] = None
    summary: str
    summary_zh: Optional[str] = None
    category: str
    tags: List[str] = []
    cover_image: Optional[str] = None
    difficulty: str = "beginner"
    estimated_time: str = "30min"
    deployed_count: int = 0
    likes_count: int = 0
    device_count: int = 0


class DeviceSummary(BaseModel):
    """Device summary"""
    id: str
    name: str
    name_zh: Optional[str] = None
    type: str
    required: bool = True


class PartnerInfo(BaseModel):
    """Deployment partner information"""
    name: str
    name_zh: Optional[str] = None
    logo: Optional[str] = None
    regions: List[str] = []  # Service regions
    contact: Optional[str] = None
    website: Optional[str] = None


class SolutionDetail(BaseModel):
    """Detailed solution information"""
    id: str
    name: str
    name_zh: Optional[str] = None
    summary: str
    summary_zh: Optional[str] = None
    description: Optional[str] = None  # Loaded from markdown file
    description_zh: Optional[str] = None
    category: str
    tags: List[str] = []
    cover_image: Optional[str] = None
    gallery: List[Dict[str, Any]] = []
    devices: List[DeviceSummary] = []
    required_devices: List[Dict[str, Any]] = []  # Legacy field
    # New device configuration system
    device_catalog: Dict[str, Dict[str, Any]] = {}
    device_groups: List[Dict[str, Any]] = []
    presets: List[Dict[str, Any]] = []
    partners: List[PartnerInfo] = []  # Deployment partners
    stats: Dict[str, Any] = {}
    links: Dict[str, str] = {}
    deployment_order: List[str] = []
    wiki_url: Optional[str] = None


class DetectedDevice(BaseModel):
    """Detected device information"""
    config_id: str
    name: str
    name_zh: Optional[str] = None
    type: str
    status: str  # detected | not_detected | manual_required | error
    connection_info: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None
    section: Optional[Dict[str, Any]] = None  # Deployment section info


class DeviceConnectionRequest(BaseModel):
    """Request to configure device connection"""
    ip_address: Optional[str] = None
    host: Optional[str] = None  # Alias for ip_address
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    serial_port: Optional[str] = None

    @property
    def effective_host(self) -> Optional[str]:
        """Get the host, preferring 'host' over 'ip_address'"""
        return self.host or self.ip_address


class StartDeploymentRequest(BaseModel):
    """Request to start a deployment"""
    solution_id: str
    device_connections: Dict[str, Dict[str, Any]] = {}
    options: Dict[str, Any] = {}
    selected_devices: List[str] = []  # If empty, deploy all required


class DeviceDeploymentStatus(BaseModel):
    """Device deployment status"""
    device_id: str
    name: str
    type: str
    status: DeploymentStatus
    current_step: Optional[str] = None
    steps: List[StepStatus] = []
    progress: int = 0
    error: Optional[str] = None


class DeploymentStatusResponse(BaseModel):
    """Deployment status response"""
    id: str
    solution_id: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    devices: List[DeviceDeploymentStatus] = []
    overall_progress: int = 0


class LogEntryResponse(BaseModel):
    """Log entry for WebSocket"""
    timestamp: str
    level: str
    device_id: Optional[str] = None
    step_id: Optional[str] = None
    message: str


class DeploymentListItem(BaseModel):
    """Deployment list item"""
    id: str
    solution_id: str
    solution_name: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    device_count: int = 0
