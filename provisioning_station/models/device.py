"""
Device configuration models
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DeploymentStep(BaseModel):
    """A deployment step"""
    id: str
    name: str
    name_zh: Optional[str] = None
    description: Optional[str] = None
    description_zh: Optional[str] = None
    optional: bool = False
    default: bool = True


# ESP32 USB Configuration
class PartitionConfig(BaseModel):
    """ESP32 partition configuration"""
    name: str
    offset: str
    file: str


class FlashConfig(BaseModel):
    """ESP32 flash configuration"""
    chip: str = "esp32s3"
    baud_rate: int = 921600
    flash_mode: str = "dio"
    flash_freq: str = "80m"
    flash_size: str = "16MB"
    partitions: List[PartitionConfig] = []


class FirmwareSource(BaseModel):
    """Firmware source configuration"""
    type: str = "local"  # local | url | github_release
    path: Optional[str] = None
    url: Optional[str] = None
    checksum: Optional[Dict[str, str]] = None


class FirmwareConfig(BaseModel):
    """ESP32 firmware configuration"""
    source: FirmwareSource
    flash_config: FlashConfig = Field(default_factory=FlashConfig)


# Docker Configuration
class DockerService(BaseModel):
    """Docker service definition"""
    name: str
    port: int
    health_check_endpoint: Optional[str] = None
    required: bool = True


class DockerConfig(BaseModel):
    """Docker deployment configuration"""
    compose_file: str
    environment: Dict[str, str] = {}
    options: Dict[str, Any] = {}
    services: List[DockerService] = []
    images: List[Dict[str, Any]] = []


# SSH Configuration
class SSHConfig(BaseModel):
    """SSH connection configuration"""
    port: int = 22
    default_user: str = "root"
    auth_methods: List[str] = ["password", "key"]
    connection_timeout: int = 30
    command_timeout: int = 300


class ConfigFileMapping(BaseModel):
    """Configuration file mapping"""
    source: str
    destination: str
    mode: str = "0644"


class ServiceConfig(BaseModel):
    """Service configuration"""
    name: str
    enable: bool = True
    start: bool = True


class PackageSource(BaseModel):
    """Package source configuration"""
    type: str = "local"  # local | url
    path: Optional[str] = None
    url: Optional[str] = None
    checksum: Optional[Dict[str, str]] = None


class PackageConfig(BaseModel):
    """Package installation configuration"""
    source: PackageSource
    install_commands: List[str] = []
    config_files: List[ConfigFileMapping] = []
    service: Optional[ServiceConfig] = None


# Detection Configuration
class DetectionConfig(BaseModel):
    """Device detection configuration"""
    method: str  # usb_serial | local | network_scan
    usb_vendor_id: Optional[str] = None
    usb_product_id: Optional[str] = None
    fallback_ports: List[str] = []
    requirements: List[str] = []
    manual_entry: bool = False


class PreCheck(BaseModel):
    """Pre-deployment check"""
    type: str
    min_version: Optional[str] = None
    min_gb: Optional[float] = None
    min_mb: Optional[float] = None
    ports: List[int] = []
    description: Optional[str] = None


class PostDeploymentConfig(BaseModel):
    """Post-deployment actions"""
    reset_device: bool = False
    wait_for_ready: int = 0
    open_browser: bool = False
    url: Optional[str] = None
    verify_service: bool = False
    service_name: Optional[str] = None


# Main Device Configuration
class DeviceConfig(BaseModel):
    """Complete device configuration"""
    version: str = "1.0"
    id: str
    name: str
    name_zh: Optional[str] = None
    type: str  # esp32_usb | docker_local | ssh_deb

    detection: DetectionConfig

    # Type-specific configurations (only one will be set)
    firmware: Optional[FirmwareConfig] = None  # For esp32_usb
    docker: Optional[DockerConfig] = None  # For docker_local
    ssh: Optional[SSHConfig] = None  # For ssh_deb
    package: Optional[PackageConfig] = None  # For ssh_deb

    pre_checks: List[PreCheck] = []
    steps: List[DeploymentStep] = []
    post_deployment: PostDeploymentConfig = Field(default_factory=PostDeploymentConfig)

    # Runtime fields
    base_path: Optional[str] = None

    def get_asset_path(self, relative_path: str) -> Optional[str]:
        """Get absolute path to a device asset"""
        if self.base_path and relative_path:
            from pathlib import Path
            return str(Path(self.base_path) / relative_path)
        return None

    def get_step_option(self, step_id: str, default: Any = None) -> Any:
        """Get option for a specific step"""
        for step in self.steps:
            if step.id == step_id:
                return step.default
        return default
