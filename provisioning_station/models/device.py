"""
Device configuration models
"""

from typing import Any, Dict, List, Optional

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


class HimaxModelConfig(BaseModel):
    """Himax AI model configuration for multi-model flashing"""

    id: str  # Unique identifier, e.g., "face_detection"
    name: str  # Display name
    name_zh: Optional[str] = None  # Chinese display name
    path: str  # Local path (relative to assets)
    url: Optional[str] = None  # Remote download URL (optional)
    flash_address: str  # Flash address, e.g., "0xB7B000"
    offset: str = "0x0"  # Offset, usually "0x0"
    required: bool = False  # Whether required
    default: bool = True  # Whether selected by default
    description: Optional[str] = None
    description_zh: Optional[str] = None
    size_hint: Optional[str] = None  # File size hint, e.g., "512KB"
    checksum: Optional[Dict[str, str]] = None  # Checksum for verification


class FlashConfig(BaseModel):
    """Flash configuration for ESP32 and Himax devices"""

    chip: str = "esp32s3"
    baud_rate: int = 921600
    baudrate: int = 921600  # Alias for Himax config
    flash_mode: str = "dio"
    flash_freq: str = "80m"
    flash_size: str = "16MB"
    partitions: List[PartitionConfig] = []
    # Himax-specific options
    requires_reset: bool = False
    timeout: int = 60
    requires_esp32_reset_hold: bool = (
        False  # SenseCAP Watcher: hold ESP32 in reset during Himax flash
    )
    protocol: str = "xmodem"  # "xmodem" (128B) or "xmodem1k" (1024B)
    models: List[HimaxModelConfig] = []  # AI models to flash after base firmware


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


class DockerRemoteConfig(BaseModel):
    """Remote Docker deployment configuration via SSH"""

    compose_file: str  # compose file relative path
    compose_dir: Optional[str] = None  # compose directory (upload entire dir)
    remote_path: str = "/opt/provisioning"  # remote base path
    environment: Dict[str, str] = {}  # environment variables
    options: Dict[str, Any] = {}  # compose options
    services: List[DockerService] = []  # service health check config


# SSH Configuration
class SSHConfig(BaseModel):
    """SSH connection configuration"""

    port: int = 22
    default_user: str = "root"
    default_host: Optional[str] = None
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


# Script Configuration
class ScriptCommand(BaseModel):
    """A command to run during script deployment"""

    command: str
    description: Optional[str] = None


class ScriptConfigTemplate(BaseModel):
    """Configuration file template"""

    file: str
    content: str


class ScriptStartCommand(BaseModel):
    """Platform-specific start commands"""

    linux_macos: Optional[str] = None
    windows: Optional[str] = None
    env: Dict[str, str] = {}


class ScriptHealthCheck(BaseModel):
    """Health check configuration for script deployment"""

    type: str = "log_pattern"  # log_pattern | http | process
    pattern: Optional[str] = None
    url: Optional[str] = None
    timeout_seconds: int = 30


class ScriptDeploymentConfig(BaseModel):
    """Script deployment configuration"""

    working_dir: Optional[str] = None
    setup_commands: List[ScriptCommand] = []
    config_template: Optional[ScriptConfigTemplate] = None
    start_command: Optional[ScriptStartCommand] = None
    health_check: Optional[ScriptHealthCheck] = None


# Node-RED Configuration
class NodeRedConfig(BaseModel):
    """Node-RED deployment configuration for reCamera"""

    flow_file: str  # Path to flow.json template
    port: int = 1880  # Node-RED Admin API port
    influxdb_node_id: Optional[str] = None  # ID of InfluxDB config node to update


# Binary/Package Deployment Configuration for reCamera
class DebPackageConfig(BaseModel):
    """Debian package configuration"""

    path: str  # Path to .deb file (relative to solution assets)
    name: Optional[str] = None  # Package name (for opkg remove)
    includes_init_script: bool = True  # Whether deb package includes init script


class ModelFileConfig(BaseModel):
    """Model file configuration"""

    path: str  # Path to model file (relative to solution assets)
    target_path: str = "/userdata/local/models"  # Target directory on device
    filename: Optional[str] = None  # Target filename (default: same as source)


class InitScriptConfig(BaseModel):
    """Init script configuration for SysVinit"""

    path: Optional[str] = (
        None  # Path to custom init script (relative to solution assets)
    )
    priority: int = 92  # SysVinit priority (S??xxx)
    name: str  # Service name (e.g., "yolo26-detector")
    binary_path: str = "/usr/local/bin"  # Where the binary is installed
    daemon_args: Optional[str] = None  # Arguments passed to daemon
    log_file: Optional[str] = None  # Log file path (default: /var/log/{name}.log)
    ld_library_path: str = (
        "/mnt/system/lib:/mnt/system/usr/lib:/mnt/system/usr/lib/3rd:/mnt/system/lib/3rd:/lib:/usr/lib"
    )
    config_file: Optional[str] = None  # Optional config file path (e.g., /etc/xxx.conf)


class MqttExternalConfig(BaseModel):
    """MQTT external access configuration"""

    enable: bool = False  # Whether to configure external MQTT access
    port: int = 1883
    allow_anonymous: bool = True


class ConflictServiceConfig(BaseModel):
    """Conflicting services to stop/disable"""

    stop: List[str] = []  # Services to stop (e.g., ["S03node-red", "S91sscma-node"])
    disable: List[str] = []  # Services to disable (rename S* to K*)


class BinaryConfig(BaseModel):
    """Binary/Package deployment configuration for reCamera C++ applications

    Supports:
    - .deb package installation via opkg
    - Model file deployment to /userdata/local/models
    - SysVinit init script deployment
    - MQTT external access configuration
    - Conflicting service management
    """

    # Package installation
    deb_package: Optional[DebPackageConfig] = None

    # Model files
    models: List[ModelFileConfig] = []

    # Init script configuration
    init_script: Optional[InitScriptConfig] = None

    # MQTT configuration
    mqtt_config: Optional[MqttExternalConfig] = None

    # Conflict service handling
    conflict_services: Optional[ConflictServiceConfig] = None

    # Legacy fields for backwards compatibility
    service_name: Optional[str] = None
    service_priority: int = 92
    description: Optional[str] = None
    daemon_args: Optional[str] = None
    auto_start: bool = True


class UserInputConfig(BaseModel):
    """User input configuration for deployment"""

    id: str
    name: str
    name_zh: Optional[str] = None
    type: str = "text"  # text | password | select | checkbox
    placeholder: Optional[str] = None
    default: Optional[str] = None
    description: Optional[str] = None
    description_zh: Optional[str] = None
    required: bool = False
    validation: Optional[Dict[str, str]] = None
    options: List[Dict[str, str]] = []  # For select type
    row: Optional[int] = None  # Group inputs with same row number on same line


# Preview Configuration
class PreviewVideoConfig(BaseModel):
    """Video stream configuration for preview"""

    type: str = "rtsp_proxy"  # rtsp_proxy | hls | mjpeg
    rtsp_url_template: Optional[str] = None
    hls_url_template: Optional[str] = None


class PreviewMqttConfig(BaseModel):
    """MQTT configuration for preview"""

    broker_template: Optional[str] = None
    port: int = 1883
    port_template: Optional[str] = None
    topic_template: Optional[str] = None
    topic: Optional[str] = None
    username: Optional[str] = None
    username_template: Optional[str] = None
    password: Optional[str] = None
    password_template: Optional[str] = None


class PreviewOverlayConfig(BaseModel):
    """Overlay configuration for preview"""

    renderer: str = "auto"  # auto | bbox | custom
    script_file: Optional[str] = None
    dependencies: List[str] = []


class PreviewDisplayConfig(BaseModel):
    """Display configuration for preview"""

    aspect_ratio: str = "16:9"
    auto_start: bool = False
    show_stats: bool = True


# Main Device Configuration
class DeviceConfig(BaseModel):
    """Complete device configuration"""

    version: str = "1.0"
    id: str
    name: str
    name_zh: Optional[str] = None
    type: str  # esp32_usb | docker_local | docker_remote | ssh_deb | script | manual | recamera_nodered | recamera_cpp

    detection: Optional[DetectionConfig] = None  # Optional for preview type

    # Type-specific configurations (only one will be set)
    firmware: Optional[FirmwareConfig] = None  # For esp32_usb
    docker: Optional[DockerConfig] = None  # For docker_local
    docker_remote: Optional[DockerRemoteConfig] = None  # For docker_remote
    ssh: Optional[SSHConfig] = None  # For ssh_deb, docker_remote, and recamera_cpp
    package: Optional[PackageConfig] = None  # For ssh_deb
    script: Optional[ScriptDeploymentConfig] = (
        None  # For script type (via deployment key)
    )
    nodered: Optional[NodeRedConfig] = None  # For recamera_nodered
    binary: Optional[BinaryConfig] = (
        None  # For recamera_cpp and other SSH binary deployments
    )

    # Preview type configurations
    video: Optional[PreviewVideoConfig] = None  # For preview type
    mqtt: Optional[PreviewMqttConfig] = None  # For preview type
    overlay: Optional[PreviewOverlayConfig] = None  # For preview type
    display: Optional[PreviewDisplayConfig] = None  # For preview type

    # User inputs for interactive deployments
    user_inputs: List[UserInputConfig] = []

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
