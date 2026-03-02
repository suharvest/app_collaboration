"""
Solution configuration models
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MediaItem(BaseModel):
    """Media item (image or video) in gallery"""

    type: str = Field(..., pattern="^(image|video)$")
    src: str
    thumbnail: Optional[str] = None
    caption: Optional[str] = None
    caption_zh: Optional[str] = None


class RequiredDevice(BaseModel):
    """Device shown in intro page (legacy, kept for backward compatibility)"""

    id: Optional[str] = None  # Device ID from catalog
    name: str
    name_zh: Optional[str] = None
    image: Optional[str] = None
    purchase_url: Optional[str] = None
    description: Optional[str] = None
    description_zh: Optional[str] = None


# ============ Device Configuration System ============


class DeviceCatalogItem(BaseModel):
    """Device definition in catalog (local overrides for global catalog)"""

    name: Optional[str] = None  # Optional when using global catalog
    name_zh: Optional[str] = None
    image: Optional[str] = None
    product_url: Optional[str] = None  # Renamed from purchase_url for consistency
    wiki_url: Optional[str] = None
    description: Optional[str] = None
    description_zh: Optional[str] = None
    category: Optional[str] = None


class DeviceGroupOption(BaseModel):
    """Option within a device group"""

    device_ref: str
    label: Optional[str] = None
    label_zh: Optional[str] = None


class DeviceGroupSection(BaseModel):
    """Section with template variables for device group deployment instructions"""

    title: Optional[str] = None
    title_zh: Optional[str] = None
    description_file: Optional[str] = None
    description_file_zh: Optional[str] = None
    # Template variable mappings: {variable_name: {device_ref: content_file_path}}
    variables: Dict[str, Dict[str, str]] = {}


class DeviceGroup(BaseModel):
    """Device selection group"""

    id: str
    name: str
    name_zh: Optional[str] = None
    type: str = "single"  # single | multiple | quantity
    required: bool = True
    description: Optional[str] = None
    description_zh: Optional[str] = None
    # Deployment section with template variables
    section: Optional[DeviceGroupSection] = None
    # For single/multiple type
    options: List[DeviceGroupOption] = []
    default: Optional[str] = None
    default_selections: List[str] = []
    # For multiple type
    min_count: int = 0
    max_count: int = 10
    # For quantity type
    device_ref: Optional[str] = None
    default_count: int = 1


class PresetLinks(BaseModel):
    """Links specific to a preset"""

    wiki: Optional[str] = None
    github: Optional[str] = None


class Preset(BaseModel):
    """Pre-defined device configuration"""

    id: str
    name: str
    name_zh: Optional[str] = None
    description: Optional[str] = None
    description_zh: Optional[str] = None
    badge: Optional[str] = None
    badge_zh: Optional[str] = None
    disabled: bool = False  # If true, show warning that preset is incomplete
    device_groups: List[DeviceGroup] = []  # Device groups for this preset
    architecture_image: Optional[str] = None  # Architecture diagram for this preset
    links: Optional[PresetLinks] = None  # Per-preset wiki/github links
    section: Optional[DeviceGroupSection] = None  # Level 1: preset deployment guide
    devices: List["DeviceRef"] = []  # Preset-specific deployment devices


class SolutionStats(BaseModel):
    """Solution statistics"""

    deployed_count: int = 0
    likes_count: int = 0
    difficulty: str = "beginner"  # beginner | intermediate | advanced
    estimated_time: str = "30min"


class SolutionLinks(BaseModel):
    """External links for solution"""

    wiki: Optional[str] = None
    github: Optional[str] = None
    docs: Optional[str] = None


class Partner(BaseModel):
    """Deployment partner who can provide on-site service"""

    name: str
    name_zh: Optional[str] = None
    logo: Optional[str] = None
    regions: List[str] = []  # Service regions (Chinese)
    regions_en: List[str] = []  # Service regions (English)
    contact: Optional[str] = None  # Email or phone
    website: Optional[str] = None


class SolutionIntro(BaseModel):
    """Intro page content"""

    summary: str
    summary_zh: Optional[str] = None
    description_file: Optional[str] = None
    description_file_zh: Optional[str] = None
    cover_image: Optional[str] = None
    gallery: List[MediaItem] = []
    category: str = "general"
    solution_type: str = "solution"  # "solution" | "technical"
    tags: List[str] = []
    required_devices: List[RequiredDevice] = []  # Legacy field
    # New device configuration system
    device_catalog: Dict[str, DeviceCatalogItem] = {}
    presets: List[Preset] = []  # Presets now contain device_groups directly
    partners: List[Partner] = []  # Deployment partners
    stats: SolutionStats = Field(default_factory=SolutionStats)
    links: SolutionLinks = Field(default_factory=SolutionLinks)


class WiringInfo(BaseModel):
    """Wiring instructions for device"""

    image: Optional[str] = None
    steps: List[str] = []
    steps_zh: List[str] = []


class DeviceSection(BaseModel):
    """Device section in deployment page"""

    title: Optional[str] = None
    title_zh: Optional[str] = None
    description_file: Optional[str] = None
    description_file_zh: Optional[str] = None
    # Troubleshoot content shown below deploy button
    troubleshoot_file: Optional[str] = None
    troubleshoot_file_zh: Optional[str] = None
    wiring: Optional[WiringInfo] = None


class UserInput(BaseModel):
    """User input field for deployment"""

    id: str
    name: str
    name_zh: Optional[str] = None
    type: str = "text"  # text | password | select
    placeholder: Optional[str] = None
    description: Optional[str] = None
    description_zh: Optional[str] = None
    required: bool = True
    default: Optional[str] = None
    default_template: Optional[str] = None  # Template with {{var}} placeholders


# Preview configuration models
class PreviewVideoConfig(BaseModel):
    """Video source configuration for preview"""

    type: str = "rtsp_proxy"  # rtsp_proxy | mjpeg | hls
    rtsp_url_template: Optional[str] = None
    mjpeg_url_template: Optional[str] = None
    hls_url_template: Optional[str] = None


class PreviewMqttConfig(BaseModel):
    """MQTT configuration for preview"""

    broker_template: Optional[str] = None
    port: int = 1883
    topic_template: str = "inference/results"
    username: Optional[str] = None
    password: Optional[str] = None


class PreviewOverlayConfig(BaseModel):
    """Overlay rendering configuration"""

    renderer: str = "custom"  # builtin_bbox | custom
    script_file: Optional[str] = None


class PreviewDisplayConfig(BaseModel):
    """Display settings for preview"""

    aspect_ratio: str = "16:9"
    auto_start: bool = False
    show_stats: bool = True


class PreviewConfig(BaseModel):
    """Complete preview configuration for a deployment step"""

    video: PreviewVideoConfig = Field(default_factory=PreviewVideoConfig)
    mqtt: PreviewMqttConfig = Field(default_factory=PreviewMqttConfig)
    overlay: PreviewOverlayConfig = Field(default_factory=PreviewOverlayConfig)
    display: PreviewDisplayConfig = Field(default_factory=PreviewDisplayConfig)
    user_inputs: List[UserInput] = []


class DeviceTarget(BaseModel):
    """A deployment target variant (e.g., local/remote, or model A/B)"""

    name: str
    name_zh: Optional[str] = None
    description: Optional[str] = None
    description_zh: Optional[str] = None
    default: bool = False
    config_file: Optional[str] = None
    section: Optional[DeviceSection] = None


class DeviceShowWhen(BaseModel):
    """Conditional display rules for devices"""

    preset: Optional[str] = None  # Show device only when this preset is selected


class DeviceRef(BaseModel):
    """Device reference in solution"""

    id: str
    name: str
    name_zh: Optional[str] = None
    type: str  # esp32_usb | docker_local | ssh_deb | script | manual | preview
    required: bool = True
    show_when: Optional[DeviceShowWhen] = None  # Conditional display rules
    config_file: Optional[str] = None  # Optional for manual/script types
    targets: Optional[Dict[str, DeviceTarget]] = None  # Alternative deployment targets
    user_inputs: List[UserInput] = []  # User inputs for script types
    section: Optional[DeviceSection] = None
    preview: Optional[PreviewConfig] = None  # Preview configuration for type: preview


class PostDeploymentStep(BaseModel):
    """Post-deployment step"""

    title: str
    title_zh: Optional[str] = None
    action: str = "guide"  # open_url | guide
    url: Optional[str] = None
    content_file: Optional[str] = None


class PostDeployment(BaseModel):
    """Post-deployment configuration"""

    success_message_file: Optional[str] = None
    success_message_file_zh: Optional[str] = None
    next_steps: List[PostDeploymentStep] = []


class SolutionDeployment(BaseModel):
    """Deployment page content"""

    guide_file: Optional[str] = None
    guide_file_zh: Optional[str] = None
    selection_mode: str = "sequential"  # sequential | single_choice
    devices: List[DeviceRef] = []
    order: List[str] = []
    post_deployment: PostDeployment = Field(default_factory=PostDeployment)


class Solution(BaseModel):
    """Complete solution configuration"""

    version: str = "1.0"
    id: str
    name: str
    name_zh: Optional[str] = None
    enabled: bool = True  # Whether the solution is visible in the solutions list
    intro: SolutionIntro
    deployment: SolutionDeployment

    # Runtime fields
    base_path: Optional[str] = None  # Path to solution directory

    def get_asset_path(self, relative_path: str) -> Optional[str]:
        """Get absolute path to a solution asset"""
        if self.base_path and relative_path:
            from pathlib import Path

            return str(Path(self.base_path) / relative_path)
        return None

    def get_localized(self, field: str, lang: str = "en") -> str:
        """Get localized field value"""
        if lang == "zh":
            zh_field = f"{field}_zh"
            if hasattr(self, zh_field) and getattr(self, zh_field):
                return getattr(self, zh_field)
        return getattr(self, field, "")
