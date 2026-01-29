"""
Deployment state models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DeploymentStatus(str, Enum):
    """Deployment status enum"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(BaseModel):
    """Step execution status"""

    id: str
    name: str
    status: str = "pending"  # pending | running | completed | failed | skipped
    progress: int = 0
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LogEntry(BaseModel):
    """Log entry"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = "info"  # debug | info | warning | error
    device_id: Optional[str] = None
    step_id: Optional[str] = None
    message: str


class DeviceDeployment(BaseModel):
    """Device deployment state"""

    device_id: str
    name: str
    type: str
    config_file: Optional[str] = None  # Store config_file path directly
    status: DeploymentStatus = DeploymentStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    connection: Optional[Dict[str, Any]] = None
    steps: List[StepStatus] = []
    error: Optional[str] = None
    logs: List[LogEntry] = []


class Deployment(BaseModel):
    """Complete deployment state"""

    id: str
    solution_id: str
    status: DeploymentStatus = DeploymentStatus.PENDING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    devices: List[DeviceDeployment] = []
    logs: List[LogEntry] = []

    def add_log(
        self,
        message: str,
        level: str = "info",
        device_id: Optional[str] = None,
        step_id: Optional[str] = None,
    ):
        """Add a log entry"""
        entry = LogEntry(
            message=message,
            level=level,
            device_id=device_id,
            step_id=step_id,
        )
        self.logs.append(entry)

        # Also add to device logs if specified
        if device_id:
            for device in self.devices:
                if device.device_id == device_id:
                    device.logs.append(entry)
                    break

    def get_device(self, device_id: str) -> Optional[DeviceDeployment]:
        """Get device deployment by ID"""
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None

    def update_step(
        self,
        device_id: str,
        step_id: str,
        status: str,
        progress: int = 0,
        message: Optional[str] = None,
    ):
        """Update step status"""
        device = self.get_device(device_id)
        if device:
            for step in device.steps:
                if step.id == step_id:
                    step.status = status
                    step.progress = progress
                    if message:
                        step.message = message
                    if status == "running" and not step.started_at:
                        step.started_at = datetime.utcnow()
                    if status in ("completed", "failed", "skipped"):
                        step.completed_at = datetime.utcnow()
                    break
            device.current_step = step_id if status == "running" else None
