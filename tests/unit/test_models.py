"""
Unit tests for Pydantic models in provisioning_station.models.solution
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from provisioning_station.models.solution import (
    DeviceGroup,
    DeviceGroupOption,
    DeviceRef,
    MediaItem,
    Partner,
    Preset,
    RequiredDevice,
    Solution,
    SolutionDeployment,
    SolutionIntro,
    SolutionLinks,
    SolutionStats,
    UserInput,
)


class TestMediaItem:
    """Tests for MediaItem model"""

    def test_valid_image_type(self):
        """Test creating MediaItem with image type"""
        item = MediaItem(type="image", src="path/to/image.png")
        assert item.type == "image"
        assert item.src == "path/to/image.png"
        assert item.caption is None

    def test_valid_video_type(self):
        """Test creating MediaItem with video type"""
        item = MediaItem(type="video", src="path/to/video.mp4", caption="Demo video")
        assert item.type == "video"
        assert item.caption == "Demo video"

    def test_invalid_type(self):
        """Test that invalid type raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            MediaItem(type="audio", src="path/to/file.mp3")
        assert "String should match pattern" in str(exc_info.value)

    def test_with_caption_zh(self):
        """Test MediaItem with Chinese caption"""
        item = MediaItem(
            type="image",
            src="cover.png",
            caption="Cover Image",
            caption_zh="封面图片"
        )
        assert item.caption_zh == "封面图片"


class TestRequiredDevice:
    """Tests for RequiredDevice model"""

    def test_minimal_device(self):
        """Test creating device with only required field"""
        device = RequiredDevice(name="Test Device")
        assert device.name == "Test Device"
        assert device.name_zh is None
        assert device.image is None

    def test_full_device(self):
        """Test creating device with all fields"""
        device = RequiredDevice(
            name="SenseCAP Watcher",
            name_zh="SenseCAP Watcher",
            image="watcher.png",
            purchase_url="https://example.com/buy",
            description="AI-powered watcher",
            description_zh="AI 智能监控设备"
        )
        assert device.purchase_url == "https://example.com/buy"


class TestDeviceGroup:
    """Tests for DeviceGroup model"""

    def test_single_type_group(self):
        """Test single selection device group"""
        group = DeviceGroup(
            id="server_type",
            name="Server Type",
            type="single",
            options=[
                DeviceGroupOption(device_ref="server_a", label="Server A"),
                DeviceGroupOption(device_ref="server_b", label="Server B"),
            ],
            default="server_a"
        )
        assert group.type == "single"
        assert len(group.options) == 2
        assert group.default == "server_a"

    def test_multiple_type_group(self):
        """Test multiple selection device group"""
        group = DeviceGroup(
            id="accessories",
            name="Accessories",
            type="multiple",
            options=[
                DeviceGroupOption(device_ref="sensor_a"),
                DeviceGroupOption(device_ref="sensor_b"),
            ],
            default_selections=["sensor_a", "sensor_b"],
            min_count=1,
            max_count=5
        )
        assert group.type == "multiple"
        assert group.min_count == 1
        assert group.max_count == 5

    def test_quantity_type_group(self):
        """Test quantity-based device group"""
        group = DeviceGroup(
            id="cameras",
            name="Camera Count",
            type="quantity",
            device_ref="camera_x",
            default_count=3
        )
        assert group.type == "quantity"
        assert group.device_ref == "camera_x"
        assert group.default_count == 3


class TestPreset:
    """Tests for Preset model"""

    def test_minimal_preset(self):
        """Test creating preset with minimal fields"""
        preset = Preset(id="basic", name="Basic Setup")
        assert preset.id == "basic"
        assert preset.name == "Basic Setup"
        assert preset.device_groups == []
        assert preset.devices == []

    def test_preset_with_badge(self):
        """Test preset with badge"""
        preset = Preset(
            id="recommended",
            name="Recommended",
            badge="Best Value",
            badge_zh="最佳性价比"
        )
        assert preset.badge == "Best Value"
        assert preset.badge_zh == "最佳性价比"


class TestSolutionStats:
    """Tests for SolutionStats model"""

    def test_default_values(self):
        """Test default stat values"""
        stats = SolutionStats()
        assert stats.deployed_count == 0
        assert stats.likes_count == 0
        assert stats.difficulty == "beginner"
        assert stats.estimated_time == "30min"

    def test_custom_values(self):
        """Test custom stat values"""
        stats = SolutionStats(
            deployed_count=100,
            likes_count=50,
            difficulty="advanced",
            estimated_time="2h"
        )
        assert stats.deployed_count == 100
        assert stats.difficulty == "advanced"


class TestSolutionLinks:
    """Tests for SolutionLinks model"""

    def test_empty_links(self):
        """Test links with no URLs"""
        links = SolutionLinks()
        assert links.wiki is None
        assert links.github is None
        assert links.docs is None

    def test_with_urls(self):
        """Test links with URLs"""
        links = SolutionLinks(
            wiki="https://wiki.example.com",
            github="https://github.com/example/repo"
        )
        assert links.wiki == "https://wiki.example.com"


class TestPartner:
    """Tests for Partner model"""

    def test_minimal_partner(self):
        """Test partner with only required fields"""
        partner = Partner(name="Partner Inc")
        assert partner.name == "Partner Inc"
        assert partner.regions == []

    def test_full_partner(self):
        """Test partner with all fields"""
        partner = Partner(
            name="Deployment Co",
            name_zh="部署公司",
            regions=["广东省", "浙江省"],
            regions_en=["Guangdong", "Zhejiang"],
            contact="contact@example.com"
        )
        assert len(partner.regions) == 2


class TestUserInput:
    """Tests for UserInput model"""

    def test_text_input(self):
        """Test text input field"""
        input_field = UserInput(
            id="api_key",
            name="API Key",
            type="text",
            required=True
        )
        assert input_field.type == "text"
        assert input_field.required is True

    def test_password_input(self):
        """Test password input field"""
        input_field = UserInput(
            id="password",
            name="Password",
            type="password",
            placeholder="Enter password"
        )
        assert input_field.type == "password"

    def test_input_with_default_template(self):
        """Test input with default template"""
        input_field = UserInput(
            id="mqtt_topic",
            name="MQTT Topic",
            default_template="devices/{{device_id}}/data"
        )
        assert "{{device_id}}" in input_field.default_template


class TestDeviceRef:
    """Tests for DeviceRef model"""

    def test_minimal_device_ref(self):
        """Test device ref with minimal fields"""
        device = DeviceRef(
            id="step1",
            name="Step 1",
            type="manual"
        )
        assert device.id == "step1"
        assert device.type == "manual"
        assert device.required is True

    def test_docker_device(self):
        """Test docker device"""
        device = DeviceRef(
            id="docker_app",
            name="Docker Application",
            type="docker_local",
            config_file="devices/docker_app.yaml"
        )
        assert device.type == "docker_local"
        assert device.config_file == "devices/docker_app.yaml"

    def test_esp32_device(self):
        """Test ESP32 device"""
        device = DeviceRef(
            id="esp32_sensor",
            name="ESP32 Sensor",
            type="esp32_usb",
            required=True
        )
        assert device.type == "esp32_usb"


class TestSolution:
    """Tests for Solution model"""

    def test_minimal_solution(self, test_solution_yaml):
        """Test creating solution from minimal valid data"""
        solution = Solution(**test_solution_yaml)
        assert solution.id == "test_solution"
        assert solution.name == "Test Solution"
        assert solution.intro.category == "testing"

    def test_solution_get_localized_en(self, test_solution_yaml):
        """Test getting English localized field"""
        solution = Solution(**test_solution_yaml)
        assert solution.get_localized("name", "en") == "Test Solution"

    def test_solution_get_localized_zh(self, test_solution_yaml):
        """Test getting Chinese localized field"""
        solution = Solution(**test_solution_yaml)
        assert solution.get_localized("name", "zh") == "测试方案"

    def test_solution_get_localized_fallback(self, test_solution_yaml):
        """Test localized field fallback to English"""
        # Remove Chinese name
        test_solution_yaml["name_zh"] = None
        solution = Solution(**test_solution_yaml)
        # Should fallback to English name
        assert solution.get_localized("name", "zh") == "Test Solution"

    def test_solution_get_asset_path(self, test_solution_yaml):
        """Test getting asset path"""
        test_solution_yaml["base_path"] = "/path/to/solution"
        solution = Solution(**test_solution_yaml)
        path = solution.get_asset_path("intro/cover.png")
        assert path == str(Path("/path/to/solution") / "intro/cover.png")

    def test_solution_get_asset_path_no_base(self, test_solution_yaml):
        """Test getting asset path without base_path"""
        solution = Solution(**test_solution_yaml)
        path = solution.get_asset_path("intro/cover.png")
        assert path is None

    def test_solution_missing_required_fields(self):
        """Test that missing required fields raise error"""
        with pytest.raises(ValidationError):
            Solution(
                id="test",
                name="Test"
                # Missing intro and deployment
            )


class TestSolutionIntro:
    """Tests for SolutionIntro model"""

    def test_minimal_intro(self):
        """Test minimal intro"""
        intro = SolutionIntro(summary="Test summary")
        assert intro.summary == "Test summary"
        assert intro.category == "general"
        assert intro.tags == []

    def test_intro_with_presets(self):
        """Test intro with presets"""
        intro = SolutionIntro(
            summary="Test",
            presets=[
                Preset(id="basic", name="Basic"),
                Preset(id="advanced", name="Advanced")
            ]
        )
        assert len(intro.presets) == 2


class TestSolutionDeployment:
    """Tests for SolutionDeployment model"""

    def test_minimal_deployment(self):
        """Test minimal deployment config"""
        deployment = SolutionDeployment()
        assert deployment.selection_mode == "sequential"
        assert deployment.devices == []
        assert deployment.order == []

    def test_single_choice_mode(self):
        """Test single choice selection mode"""
        deployment = SolutionDeployment(
            selection_mode="single_choice",
            devices=[
                DeviceRef(id="option1", name="Option 1", type="manual"),
                DeviceRef(id="option2", name="Option 2", type="manual"),
            ]
        )
        assert deployment.selection_mode == "single_choice"
        assert len(deployment.devices) == 2
