"""
Integration tests for SolutionManager service
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from provisioning_station.services.solution_manager import SolutionManager


class TestSolutionManagerLoading:
    """Tests for solution loading functionality"""

    @pytest.fixture
    def manager(self, temp_solutions_dir):
        """Create SolutionManager with temporary solutions directory"""
        manager = SolutionManager()
        manager.solutions_dir = temp_solutions_dir
        return manager

    @pytest.mark.asyncio
    async def test_load_solutions_empty_directory(self):
        """Test loading from empty solutions directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            solutions_dir = Path(tmpdir) / "solutions"
            solutions_dir.mkdir()

            manager = SolutionManager()
            manager.solutions_dir = solutions_dir

            solutions = await manager.load_solutions()
            assert solutions == []

    @pytest.mark.asyncio
    async def test_load_solutions_nonexistent_directory(self):
        """Test loading from nonexistent directory"""
        manager = SolutionManager()
        manager.solutions_dir = Path("/nonexistent/path")

        solutions = await manager.load_solutions()
        assert solutions == []

    @pytest.mark.asyncio
    async def test_load_solutions_finds_valid_solution(self, manager):
        """Test that valid solutions are loaded"""
        solutions = await manager.load_solutions()

        assert len(solutions) == 1
        solution = solutions[0]
        assert solution.id == "test_solution"
        assert solution.name == "Test Solution"
        assert solution.name_zh == "测试方案"

    @pytest.mark.asyncio
    async def test_load_solutions_sets_base_path(self, manager, temp_solutions_dir):
        """Test that base_path is set correctly"""
        solutions = await manager.load_solutions()

        solution = solutions[0]
        assert solution.base_path is not None
        assert Path(solution.base_path).exists()
        assert Path(solution.base_path).name == "test_solution"

    @pytest.mark.asyncio
    async def test_get_solution_by_id(self, manager):
        """Test getting solution by ID"""
        await manager.load_solutions()

        solution = manager.get_solution("test_solution")
        assert solution is not None
        assert solution.id == "test_solution"

    @pytest.mark.asyncio
    async def test_get_solution_not_found(self, manager):
        """Test getting nonexistent solution returns None"""
        await manager.load_solutions()

        solution = manager.get_solution("nonexistent")
        assert solution is None

    @pytest.mark.asyncio
    async def test_get_all_solutions(self, manager):
        """Test getting all solutions"""
        await manager.load_solutions()

        solutions = manager.get_all_solutions()
        assert len(solutions) == 1
        assert solutions[0].id == "test_solution"


class TestSolutionManagerMarkdown:
    """Tests for markdown loading functionality"""

    @pytest.fixture
    def manager(self, temp_solutions_dir):
        """Create SolutionManager with temporary solutions directory"""
        manager = SolutionManager()
        manager.solutions_dir = temp_solutions_dir
        return manager

    @pytest.mark.asyncio
    async def test_load_markdown_converts_to_html(self, manager):
        """Test that markdown is converted to HTML by default"""
        await manager.load_solutions()

        html = await manager.load_markdown("test_solution", "intro/description.md")

        assert html is not None
        assert "<h1>" in html or "<p>" in html

    @pytest.mark.asyncio
    async def test_load_markdown_raw(self, manager):
        """Test loading raw markdown without conversion"""
        await manager.load_solutions()

        content = await manager.load_markdown(
            "test_solution",
            "intro/description.md",
            convert_to_html=False
        )

        assert content is not None
        assert "# Test Solution" in content

    @pytest.mark.asyncio
    async def test_load_markdown_chinese(self, manager):
        """Test loading Chinese markdown"""
        await manager.load_solutions()

        content = await manager.load_markdown(
            "test_solution",
            "intro/description_zh.md",
            convert_to_html=False
        )

        assert content is not None
        assert "测试方案" in content

    @pytest.mark.asyncio
    async def test_load_markdown_nonexistent_file(self, manager):
        """Test loading nonexistent markdown file"""
        await manager.load_solutions()

        content = await manager.load_markdown(
            "test_solution",
            "nonexistent.md"
        )

        assert content is None

    @pytest.mark.asyncio
    async def test_load_markdown_invalid_solution(self, manager):
        """Test loading markdown for invalid solution"""
        await manager.load_solutions()

        content = await manager.load_markdown(
            "invalid_solution",
            "intro/description.md"
        )

        assert content is None


class TestSolutionManagerValidation:
    """Tests for solution validation functionality"""

    def test_validate_solution_id_valid(self):
        """Test valid solution IDs"""
        manager = SolutionManager()

        assert manager.validate_solution_id("my_solution") is True
        assert manager.validate_solution_id("test123") is True
        assert manager.validate_solution_id("a") is True
        assert manager.validate_solution_id("solution_v2_beta") is True

    def test_validate_solution_id_invalid(self):
        """Test invalid solution IDs"""
        manager = SolutionManager()

        # Must start with letter
        assert manager.validate_solution_id("123test") is False
        assert manager.validate_solution_id("_test") is False

        # No uppercase
        assert manager.validate_solution_id("MyTest") is False
        assert manager.validate_solution_id("TEST") is False

        # No special characters except underscore
        assert manager.validate_solution_id("test-solution") is False
        assert manager.validate_solution_id("test.solution") is False
        assert manager.validate_solution_id("test solution") is False

    def test_validate_asset_path_valid(self):
        """Test valid asset paths"""
        manager = SolutionManager()

        assert manager.validate_asset_path("intro/cover.png") is True
        assert manager.validate_asset_path("deploy/guide.md") is True
        assert manager.validate_asset_path("devices/config.yaml") is True
        assert manager.validate_asset_path("intro/gallery/image.jpg") is True

    def test_validate_asset_path_invalid_traversal(self):
        """Test path traversal is rejected"""
        manager = SolutionManager()

        assert manager.validate_asset_path("../outside.txt") is False
        assert manager.validate_asset_path("intro/../../../etc/passwd") is False

    def test_validate_asset_path_invalid_absolute(self):
        """Test absolute paths are rejected"""
        manager = SolutionManager()

        assert manager.validate_asset_path("/etc/passwd") is False
        assert manager.validate_asset_path("/root/file.txt") is False

    def test_validate_asset_path_invalid_extension(self):
        """Test invalid file extensions are rejected"""
        manager = SolutionManager()

        assert manager.validate_asset_path("script.py") is False
        assert manager.validate_asset_path("config.json") is False
        assert manager.validate_asset_path("binary.exe") is False


class TestSolutionManagerCRUD:
    """Tests for solution CRUD operations"""

    @pytest.fixture
    def manager(self, temp_solutions_dir):
        """Create SolutionManager with temporary solutions directory"""
        manager = SolutionManager()
        manager.solutions_dir = temp_solutions_dir
        return manager

    @pytest.mark.asyncio
    async def test_create_solution(self, manager, temp_solutions_dir):
        """Test creating a new solution"""
        await manager.load_solutions()

        data = {
            "id": "new_solution",
            "name": "New Solution",
            "name_zh": "新方案",
            "summary": "A new solution",
            "summary_zh": "一个新方案",
            "category": "testing"
        }

        solution = await manager.create_solution(data)

        assert solution.id == "new_solution"
        assert solution.name == "New Solution"
        assert (temp_solutions_dir / "new_solution" / "solution.yaml").exists()

    @pytest.mark.asyncio
    async def test_create_solution_invalid_id(self, manager):
        """Test creating solution with invalid ID"""
        await manager.load_solutions()

        data = {
            "id": "Invalid-ID",  # Invalid: contains hyphen
            "name": "Invalid",
            "summary": "Test"
        }

        with pytest.raises(ValueError) as exc_info:
            await manager.create_solution(data)
        assert "Invalid solution ID format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_solution_duplicate_id(self, manager):
        """Test creating solution with duplicate ID"""
        await manager.load_solutions()

        data = {
            "id": "test_solution",  # Already exists
            "name": "Duplicate",
            "summary": "Test"
        }

        with pytest.raises(ValueError) as exc_info:
            await manager.create_solution(data)
        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_solution(self, manager):
        """Test updating a solution"""
        await manager.load_solutions()

        update_data = {
            "name": "Updated Solution",
            "summary": "Updated summary"
        }

        solution = await manager.update_solution("test_solution", update_data)

        assert solution.name == "Updated Solution"
        assert solution.intro.summary == "Updated summary"

    @pytest.mark.asyncio
    async def test_update_solution_not_found(self, manager):
        """Test updating nonexistent solution"""
        await manager.load_solutions()

        with pytest.raises(ValueError) as exc_info:
            await manager.update_solution("nonexistent", {"name": "Test"})
        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_solution_to_trash(self, manager, temp_solutions_dir):
        """Test deleting solution to trash"""
        await manager.load_solutions()

        result = await manager.delete_solution("test_solution", move_to_trash=True)

        assert result is True
        assert not (temp_solutions_dir / "test_solution").exists()
        assert (temp_solutions_dir / ".trash").exists()
        # Should be one item in trash
        trash_items = list((temp_solutions_dir / ".trash").iterdir())
        assert len(trash_items) == 1

    @pytest.mark.asyncio
    async def test_delete_solution_permanent(self, manager, temp_solutions_dir):
        """Test permanently deleting solution"""
        await manager.load_solutions()

        result = await manager.delete_solution("test_solution", move_to_trash=False)

        assert result is True
        assert not (temp_solutions_dir / "test_solution").exists()
        # Trash should not exist or be empty
        trash_path = temp_solutions_dir / ".trash"
        if trash_path.exists():
            assert len(list(trash_path.iterdir())) == 0

    @pytest.mark.asyncio
    async def test_delete_solution_not_found(self, manager):
        """Test deleting nonexistent solution"""
        await manager.load_solutions()

        with pytest.raises(ValueError) as exc_info:
            await manager.delete_solution("nonexistent")
        assert "not found" in str(exc_info.value)


class TestSolutionManagerReload:
    """Tests for solution reload functionality"""

    @pytest.fixture
    def manager(self, temp_solutions_dir):
        """Create SolutionManager with temporary solutions directory"""
        manager = SolutionManager()
        manager.solutions_dir = temp_solutions_dir
        return manager

    @pytest.mark.asyncio
    async def test_reload_solution(self, manager, temp_solutions_dir):
        """Test reloading a modified solution"""
        await manager.load_solutions()

        # Modify the solution.yaml directly
        yaml_path = temp_solutions_dir / "test_solution" / "solution.yaml"
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        data["name"] = "Modified Name"

        with open(yaml_path, "w") as f:
            yaml.dump(data, f, allow_unicode=True)

        # Reload
        solution = await manager.reload_solution("test_solution")

        assert solution is not None
        assert solution.name == "Modified Name"

    @pytest.mark.asyncio
    async def test_reload_solution_not_found(self, manager):
        """Test reloading nonexistent solution"""
        await manager.load_solutions()

        solution = await manager.reload_solution("nonexistent")
        assert solution is None


class TestSolutionManagerContentFiles:
    """Tests for content file management (guide.md, description.md)"""

    @pytest.fixture
    def manager(self, temp_solutions_dir):
        """Create SolutionManager with temporary solutions directory"""
        manager = SolutionManager()
        manager.solutions_dir = temp_solutions_dir
        return manager

    @pytest.mark.asyncio
    async def test_save_content_file_guide(self, manager, temp_solutions_dir):
        """Test saving guide.md content file"""
        await manager.load_solutions()

        content = """<!-- @lang:en -->
## Step 1: Deploy {#deploy type=manual required=true}

Deploy the service.

<!-- @lang:zh -->
## 步骤 1: 部署 {#deploy type=manual required=true}

部署服务。
"""
        path = await manager.save_content_file("test_solution", "guide.md", content)

        assert path is not None
        assert (temp_solutions_dir / "test_solution" / "guide.md").exists()
        saved_content = (temp_solutions_dir / "test_solution" / "guide.md").read_text()
        assert "Deploy the service" in saved_content

    @pytest.mark.asyncio
    async def test_save_content_file_description(self, manager, temp_solutions_dir):
        """Test saving description.md content file"""
        await manager.load_solutions()

        content = "# My Solution\n\nThis is the description."
        path = await manager.save_content_file("test_solution", "description.md", content)

        assert path is not None
        assert (temp_solutions_dir / "test_solution" / "description.md").exists()

    @pytest.mark.asyncio
    async def test_save_content_file_invalid_filename(self, manager):
        """Test saving invalid filename is rejected"""
        await manager.load_solutions()

        with pytest.raises(ValueError) as exc_info:
            await manager.save_content_file("test_solution", "invalid.txt", "content")
        assert "Must be one of" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_content_file_solution_not_found(self, manager):
        """Test saving to nonexistent solution"""
        await manager.load_solutions()

        with pytest.raises(ValueError) as exc_info:
            await manager.save_content_file("nonexistent", "guide.md", "content")
        assert "not found" in str(exc_info.value)


class TestSolutionManagerPresetSync:
    """Tests for preset syncing from guide.md"""

    @pytest.fixture
    def manager(self, temp_solutions_dir):
        """Create SolutionManager with temporary solutions directory"""
        manager = SolutionManager()
        manager.solutions_dir = temp_solutions_dir
        return manager

    @pytest.mark.asyncio
    async def test_sync_presets_from_guide(self, manager, temp_solutions_dir):
        """Test syncing presets from guide.md to YAML"""
        await manager.load_solutions()

        # Create a guide.md with presets (in deploy/ subdirectory per solution.yaml config)
        guide_content = """## Preset: Cloud Solution {#cloud}

Cloud deployment option.

## Step 1: Deploy Cloud {#cloud_deploy type=docker_deploy required=true}

Deploy to cloud.

## Preset: Edge Computing {#edge}

Edge deployment option.

## Step 1: Deploy Edge {#edge_deploy type=script required=true}

Deploy to edge.
"""
        guide_zh_content = """## 套餐: 云方案 {#cloud}

云部署选项。

## 步骤 1: 部署云服务 {#cloud_deploy type=docker_deploy required=true}

部署到云。

## 套餐: 边缘计算 {#edge}

边缘部署选项。

## 步骤 1: 部署边缘 {#edge_deploy type=script required=true}

部署到边缘。
"""
        # Write to deploy/ folder per solution.yaml config
        guide_path = temp_solutions_dir / "test_solution" / "deploy" / "guide.md"
        guide_path.write_text(guide_content, encoding="utf-8")
        guide_zh_path = temp_solutions_dir / "test_solution" / "deploy" / "guide_zh.md"
        guide_zh_path.write_text(guide_zh_content, encoding="utf-8")

        # Sync presets
        result = await manager.sync_presets_from_guide("test_solution")
        assert result is True

        # Verify YAML was updated
        yaml_path = temp_solutions_dir / "test_solution" / "solution.yaml"
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "intro" in data
        assert "presets" in data["intro"]
        presets = data["intro"]["presets"]
        assert len(presets) == 2
        assert presets[0]["id"] == "cloud"
        assert presets[0]["name"] == "Cloud Solution"
        assert presets[0]["name_zh"] == "云方案"

    @pytest.mark.asyncio
    async def test_sync_presets_no_guide(self, manager):
        """Test syncing when no guide.md exists"""
        await manager.load_solutions()

        # Remove guide files
        guide_path = manager.solutions_dir / "test_solution" / "deploy" / "guide.md"
        if guide_path.exists():
            guide_path.unlink()

        result = await manager.sync_presets_from_guide("test_solution")
        assert result is False


class TestSolutionManagerStructurePreview:
    """Tests for structure preview from guide.md"""

    @pytest.fixture
    def manager(self, temp_solutions_dir):
        """Create SolutionManager with temporary solutions directory"""
        manager = SolutionManager()
        manager.solutions_dir = temp_solutions_dir
        return manager

    @pytest.mark.asyncio
    async def test_get_structure_preview(self, manager, temp_solutions_dir):
        """Test getting structure preview from guide.md"""
        await manager.load_solutions()

        # Create a guide.md with content (in deploy/ subdirectory per solution.yaml config)
        guide_content = """## Preset: Main {#main}

Main preset description.

## Step 1: Deploy {#deploy type=docker_deploy required=true}

Deploy content.

# Deployment Complete

Congratulations!

## Next Steps

1. Open the dashboard
"""
        guide_zh_content = """## 套餐: 主要 {#main}

主要预设描述。

## 步骤 1: 部署 {#deploy type=docker_deploy required=true}

部署内容。

# 部署完成

恭喜！

## 下一步

1. 打开仪表板
"""
        # Write to deploy/ folder per solution.yaml config
        guide_path = temp_solutions_dir / "test_solution" / "deploy" / "guide.md"
        guide_path.write_text(guide_content, encoding="utf-8")
        guide_zh_path = temp_solutions_dir / "test_solution" / "deploy" / "guide_zh.md"
        guide_zh_path.write_text(guide_zh_content, encoding="utf-8")

        preview = await manager.get_structure_preview("test_solution")

        assert preview is not None
        assert "presets" in preview
        assert len(preview["presets"]) == 1
        assert preview["presets"][0]["id"] == "main"
        assert len(preview["presets"][0]["steps"]) == 1
        assert preview["presets"][0]["steps"][0]["id"] == "deploy"
        assert "post_deployment" in preview

    @pytest.mark.asyncio
    async def test_get_structure_preview_not_found(self, manager):
        """Test structure preview for nonexistent solution"""
        await manager.load_solutions()

        preview = await manager.get_structure_preview("nonexistent")
        assert preview is None


class TestSolutionManagerDeviceCatalog:
    """Tests for device catalog functionality"""

    @pytest.fixture
    def manager_with_catalog(self, temp_solutions_dir):
        """Create SolutionManager with mock device catalog"""
        manager = SolutionManager()
        manager.solutions_dir = temp_solutions_dir
        # Mock the global device catalog
        manager._global_device_catalog = {
            "sensecap_watcher": {
                "name": "SenseCAP Watcher",
                "name_zh": "SenseCAP 监视器",
                "category": "sensing",
                "product_url": "https://example.com/watcher"
            },
            "recomputer_j4012": {
                "name": "reComputer J4012",
                "name_zh": "reComputer J4012",
                "category": "computing"
            }
        }
        return manager

    def test_get_device_catalog_list(self, manager_with_catalog):
        """Test getting device catalog as list"""
        catalog_list = manager_with_catalog.get_device_catalog_list()

        assert len(catalog_list) == 2
        assert any(d["id"] == "sensecap_watcher" for d in catalog_list)
        assert any(d["id"] == "recomputer_j4012" for d in catalog_list)

        # Check fields
        watcher = next(d for d in catalog_list if d["id"] == "sensecap_watcher")
        assert watcher["name"] == "SenseCAP Watcher"
        assert watcher["name_zh"] == "SenseCAP 监视器"
        assert watcher["category"] == "sensing"

    def test_get_device_catalog_list_empty(self, temp_solutions_dir):
        """Test getting empty device catalog"""
        manager = SolutionManager()
        manager.solutions_dir = temp_solutions_dir
        manager._global_device_catalog = {}

        catalog_list = manager.get_device_catalog_list()
        assert catalog_list == []


class TestSolutionManagerRequiredDevices:
    """Tests for required devices management"""

    @pytest.fixture
    def manager_with_catalog(self, temp_solutions_dir):
        """Create SolutionManager with mock device catalog"""
        manager = SolutionManager()
        manager.solutions_dir = temp_solutions_dir
        manager._global_device_catalog = {
            "sensecap_watcher": {
                "name": "SenseCAP Watcher",
                "name_zh": "SenseCAP 监视器",
                "product_url": "https://example.com/watcher"
            },
            "recomputer_j4012": {
                "name": "reComputer J4012",
                "name_zh": "reComputer J4012"
            }
        }
        return manager

    @pytest.mark.asyncio
    async def test_update_required_devices(self, manager_with_catalog, temp_solutions_dir):
        """Test updating required devices from catalog IDs"""
        await manager_with_catalog.load_solutions()

        device_ids = ["sensecap_watcher", "recomputer_j4012"]
        updated = await manager_with_catalog.update_required_devices("test_solution", device_ids)

        assert len(updated) == 2
        assert updated[0]["id"] == "sensecap_watcher"
        assert updated[0]["name"] == "SenseCAP Watcher"

        # Verify YAML was updated
        yaml_path = temp_solutions_dir / "test_solution" / "solution.yaml"
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "intro" in data
        assert "required_devices" in data["intro"]
        assert len(data["intro"]["required_devices"]) == 2

    @pytest.mark.asyncio
    async def test_update_required_devices_unknown_id(self, manager_with_catalog):
        """Test updating with unknown device ID"""
        await manager_with_catalog.load_solutions()

        device_ids = ["sensecap_watcher", "unknown_device"]
        updated = await manager_with_catalog.update_required_devices("test_solution", device_ids)

        # Unknown device should still be included with ID as name
        assert len(updated) == 2
        unknown = next(d for d in updated if d["id"] == "unknown_device")
        assert unknown["name"] == "unknown_device"

    @pytest.mark.asyncio
    async def test_update_required_devices_empty(self, manager_with_catalog, temp_solutions_dir):
        """Test clearing required devices"""
        await manager_with_catalog.load_solutions()

        # First add some devices
        await manager_with_catalog.update_required_devices("test_solution", ["sensecap_watcher"])

        # Then clear them
        updated = await manager_with_catalog.update_required_devices("test_solution", [])

        assert updated == []

        # Verify YAML was updated
        yaml_path = temp_solutions_dir / "test_solution" / "solution.yaml"
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["intro"]["required_devices"] == []

    @pytest.mark.asyncio
    async def test_update_required_devices_solution_not_found(self, manager_with_catalog):
        """Test updating devices for nonexistent solution"""
        await manager_with_catalog.load_solutions()

        with pytest.raises(ValueError) as exc_info:
            await manager_with_catalog.update_required_devices("nonexistent", ["sensecap_watcher"])
        assert "not found" in str(exc_info.value)
