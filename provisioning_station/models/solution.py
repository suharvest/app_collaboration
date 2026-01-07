"""
Solution configuration models
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MediaItem(BaseModel):
    """Media item (image or video) in gallery"""
    type: str = Field(..., pattern="^(image|video)$")
    src: str
    thumbnail: Optional[str] = None
    caption: Optional[str] = None
    caption_zh: Optional[str] = None


class RequiredDevice(BaseModel):
    """Device shown in intro page"""
    name: str
    name_zh: Optional[str] = None
    image: Optional[str] = None
    purchase_url: Optional[str] = None
    description: Optional[str] = None
    description_zh: Optional[str] = None


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
    tags: List[str] = []
    required_devices: List[RequiredDevice] = []
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
    title: str
    title_zh: Optional[str] = None
    description_file: Optional[str] = None
    description_file_zh: Optional[str] = None
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


class DeviceRef(BaseModel):
    """Device reference in solution"""
    id: str
    name: str
    name_zh: Optional[str] = None
    type: str  # esp32_usb | docker_local | ssh_deb | script | manual
    required: bool = True
    config_file: Optional[str] = None  # Optional for manual/script types
    user_inputs: List[UserInput] = []  # User inputs for script types
    section: Optional[DeviceSection] = None


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
    devices: List[DeviceRef] = []
    order: List[str] = []
    post_deployment: PostDeployment = Field(default_factory=PostDeployment)


class Solution(BaseModel):
    """Complete solution configuration"""
    version: str = "1.0"
    id: str
    name: str
    name_zh: Optional[str] = None
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
