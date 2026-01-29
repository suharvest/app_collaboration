"""
Solution loading and management service
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import markdown
import yaml

from ..config import settings
from ..models.device import DeviceConfig
from ..models.solution import Solution

logger = logging.getLogger(__name__)

# Valid file extensions for uploads
ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif'}
ALLOWED_DOC_EXTENSIONS = {'.md'}
ALLOWED_CONFIG_EXTENSIONS = {'.yaml', '.yml'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOC_EXTENSIONS | ALLOWED_CONFIG_EXTENSIONS

# Solution ID validation pattern: lowercase letters, numbers, underscore, must start with letter
SOLUTION_ID_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')


class SolutionManager:
    """Solution loading and management service"""

    def __init__(self):
        self.solutions_dir = settings.solutions_dir
        self.solutions: Dict[str, Solution] = {}
        self._device_configs: Dict[str, Dict[str, DeviceConfig]] = {}  # solution_id -> device_id -> config
        self._global_device_catalog: Dict[str, dict] = {}  # Global device catalog

    async def load_global_device_catalog(self) -> None:
        """Load the global device catalog from devices/catalog.yaml"""
        catalog_path = self.solutions_dir.parent / "devices" / "catalog.yaml"
        if not catalog_path.exists():
            logger.warning(f"Global device catalog not found: {catalog_path}")
            return

        try:
            async with aiofiles.open(catalog_path, "r", encoding="utf-8") as f:
                content = await f.read()
                self._global_device_catalog = yaml.safe_load(content) or {}
            logger.info(f"Loaded {len(self._global_device_catalog)} devices from global catalog")
        except Exception as e:
            logger.error(f"Failed to load global device catalog: {e}")

    def get_global_device(self, device_id: str) -> Optional[dict]:
        """Get device info from global catalog"""
        return self._global_device_catalog.get(device_id)

    def get_global_device_catalog(self) -> Dict[str, dict]:
        """Get the entire global device catalog"""
        return self._global_device_catalog

    async def load_solutions(self) -> List[Solution]:
        """Scan and load all solutions from solutions directory"""
        self.solutions.clear()
        self._device_configs.clear()

        # Load global device catalog first
        await self.load_global_device_catalog()

        if not self.solutions_dir.exists():
            logger.warning(f"Solutions directory does not exist: {self.solutions_dir}")
            return []

        for solution_path in self.solutions_dir.iterdir():
            if solution_path.is_dir():
                solution_file = solution_path / "solution.yaml"
                if solution_file.exists():
                    solution = await self._load_solution(solution_path)
                    if solution:
                        self.solutions[solution.id] = solution
                        logger.info(f"Loaded solution: {solution.id}")

        return list(self.solutions.values())

    async def _load_solution(self, solution_path: Path) -> Optional[Solution]:
        """Load and validate a solution configuration"""
        try:
            solution_file = solution_path / "solution.yaml"
            async with aiofiles.open(solution_file, "r", encoding="utf-8") as f:
                content = await f.read()
                data = yaml.safe_load(content)

            # Set base path for asset resolution
            data["base_path"] = str(solution_path)

            solution = Solution(**data)
            return solution

        except Exception as e:
            logger.error(f"Failed to load solution from {solution_path}: {e}")
            return None

    def get_solution(self, solution_id: str) -> Optional[Solution]:
        """Get a specific solution by ID"""
        return self.solutions.get(solution_id)

    def get_all_solutions(self) -> List[Solution]:
        """Get all loaded solutions"""
        return list(self.solutions.values())

    def find_device_in_solution(
        self, solution: Solution, device_id: str, preset_id: str = None
    ):
        """Find a device by ID from presets.

        Args:
            solution: The solution object
            device_id: The device ID to find
            preset_id: Optional preset ID to search within

        Returns:
            The device reference if found, None otherwise
        """
        if solution.intro and solution.intro.presets:
            for preset in solution.intro.presets:
                if preset_id and preset.id != preset_id:
                    continue
                if preset.devices:
                    for device in preset.devices:
                        if device.id == device_id:
                            return device
        return None

    def get_all_devices_from_solution(self, solution: Solution, preset_id: str = None):
        """Get all devices from a solution's presets.

        Args:
            solution: The solution object
            preset_id: Optional preset ID to filter by

        Returns:
            List of device references from presets
        """
        devices = []
        if solution.intro and solution.intro.presets:
            for preset in solution.intro.presets:
                if preset_id and preset.id != preset_id:
                    continue
                if preset.devices:
                    devices.extend(preset.devices)
        return devices

    def count_devices_in_solution(self, solution: Solution) -> int:
        """Count unique devices in a solution (from presets).

        Args:
            solution: The solution object

        Returns:
            Number of unique device IDs
        """
        device_ids = set()
        if solution.intro and solution.intro.presets:
            for preset in solution.intro.presets:
                if preset.devices:
                    for device in preset.devices:
                        device_ids.add(device.id)
        return len(device_ids)

    async def load_markdown(self, solution_id: str, relative_path: str, convert_to_html: bool = True) -> Optional[str]:
        """Load markdown content from a solution's file and optionally convert to HTML"""
        solution = self.get_solution(solution_id)
        if not solution or not solution.base_path:
            return None

        file_path = Path(solution.base_path) / relative_path
        if not file_path.exists():
            logger.warning(f"Markdown file not found: {file_path}")
            return None

        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            if convert_to_html:
                # Convert markdown to HTML
                md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc'])
                return md.convert(content)
            return content
        except Exception as e:
            logger.error(f"Failed to load markdown {file_path}: {e}")
            return None

    async def load_device_config(
        self, solution_id: str, config_file: str
    ) -> Optional[DeviceConfig]:
        """Load device configuration"""
        # Check cache first
        if solution_id in self._device_configs:
            # Extract device_id from config_file path
            device_id = Path(config_file).stem
            if device_id in self._device_configs[solution_id]:
                return self._device_configs[solution_id][device_id]

        solution = self.get_solution(solution_id)
        if not solution or not solution.base_path:
            return None

        config_path = Path(solution.base_path) / config_file
        if not config_path.exists():
            logger.warning(f"Device config not found: {config_path}")
            return None

        try:
            async with aiofiles.open(config_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = yaml.safe_load(content)

            # Set base path
            data["base_path"] = str(Path(solution.base_path))

            # For script type devices, map 'deployment' key to 'script' config
            if data.get("type") == "script" and "deployment" in data:
                data["script"] = data.pop("deployment")

            config = DeviceConfig(**data)

            # Cache it
            if solution_id not in self._device_configs:
                self._device_configs[solution_id] = {}
            self._device_configs[solution_id][config.id] = config

            return config

        except Exception as e:
            logger.error(f"Failed to load device config {config_path}: {e}")
            return None

    async def reload_solution(self, solution_id: str) -> Optional[Solution]:
        """Reload a specific solution"""
        if solution_id in self.solutions:
            solution = self.solutions[solution_id]
            if solution.base_path:
                new_solution = await self._load_solution(Path(solution.base_path))
                if new_solution:
                    self.solutions[solution_id] = new_solution
                    # Clear device config cache
                    if solution_id in self._device_configs:
                        del self._device_configs[solution_id]
                    return new_solution
        return None

    # ============================================
    # Solution Management Methods
    # ============================================

    def validate_solution_id(self, solution_id: str) -> bool:
        """Validate solution ID format"""
        return bool(SOLUTION_ID_PATTERN.match(solution_id))

    def solution_exists(self, solution_id: str) -> bool:
        """Check if a solution already exists"""
        solution_path = self.solutions_dir / solution_id
        return solution_path.exists()

    async def create_solution(self, data: Dict[str, Any]) -> Solution:
        """Create a new solution with basic structure"""
        solution_id = data["id"]

        # Validate ID format
        if not self.validate_solution_id(solution_id):
            raise ValueError(f"Invalid solution ID format: {solution_id}. Must match pattern: {SOLUTION_ID_PATTERN.pattern}")

        # Check if already exists
        if self.solution_exists(solution_id):
            raise ValueError(f"Solution with ID '{solution_id}' already exists")

        solution_path = self.solutions_dir / solution_id

        try:
            # Create directory structure
            (solution_path / "intro" / "gallery").mkdir(parents=True, exist_ok=True)
            (solution_path / "deploy" / "sections").mkdir(parents=True, exist_ok=True)
            (solution_path / "devices").mkdir(parents=True, exist_ok=True)

            # Create initial solution.yaml
            solution_yaml = {
                "version": "1.0",
                "id": solution_id,
                "name": data["name"],
                "name_zh": data.get("name_zh") or data["name"],
                "intro": {
                    "summary": data["summary"],
                    "summary_zh": data.get("summary_zh") or data["summary"],
                    "description_file": "intro/description.md",
                    "description_file_zh": "intro/description_zh.md",
                    "category": data.get("category", "general"),
                    "tags": [],
                    "stats": {
                        "difficulty": data.get("difficulty", "beginner"),
                        "estimated_time": data.get("estimated_time", "30min"),
                        "deployed_count": 0,
                        "likes_count": 0,
                    },
                },
                "deployment": {
                    "guide_file": "deploy/guide.md",
                    "guide_file_zh": "deploy/guide_zh.md",
                    "devices": [],
                    "order": [],
                },
            }

            # Write solution.yaml
            yaml_path = solution_path / "solution.yaml"
            async with aiofiles.open(yaml_path, "w", encoding="utf-8") as f:
                await f.write(yaml.dump(solution_yaml, allow_unicode=True, sort_keys=False))

            # Create placeholder markdown files
            description_en = f"# {data['name']}\n\n{data['summary']}\n"
            description_zh = f"# {data.get('name_zh') or data['name']}\n\n{data.get('summary_zh') or data['summary']}\n"

            async with aiofiles.open(solution_path / "intro" / "description.md", "w", encoding="utf-8") as f:
                await f.write(description_en)
            async with aiofiles.open(solution_path / "intro" / "description_zh.md", "w", encoding="utf-8") as f:
                await f.write(description_zh)
            async with aiofiles.open(solution_path / "deploy" / "guide.md", "w", encoding="utf-8") as f:
                await f.write(f"## Deployment Guide\n\nFollow the steps below to deploy {data['name']}.\n")
            async with aiofiles.open(solution_path / "deploy" / "guide_zh.md", "w", encoding="utf-8") as f:
                await f.write(f"## 部署指南\n\n按照以下步骤部署 {data.get('name_zh') or data['name']}。\n")

            # Load and register the new solution
            solution = await self._load_solution(solution_path)
            if solution:
                self.solutions[solution_id] = solution
                logger.info(f"Created new solution: {solution_id}")
                return solution
            else:
                raise Exception("Failed to load created solution")

        except Exception as e:
            # Cleanup on failure
            if solution_path.exists():
                shutil.rmtree(solution_path)
            raise e

    async def update_solution(self, solution_id: str, data: Dict[str, Any]) -> Solution:
        """Update an existing solution's basic info"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        yaml_path = Path(solution.base_path) / "solution.yaml"

        # Read current yaml
        async with aiofiles.open(yaml_path, "r", encoding="utf-8") as f:
            content = await f.read()
            current_yaml = yaml.safe_load(content)

        # Update fields
        if data.get("name"):
            current_yaml["name"] = data["name"]
        if data.get("name_zh"):
            current_yaml["name_zh"] = data["name_zh"]
        if data.get("summary"):
            current_yaml["intro"]["summary"] = data["summary"]
        if data.get("summary_zh"):
            current_yaml["intro"]["summary_zh"] = data["summary_zh"]
        if data.get("category"):
            current_yaml["intro"]["category"] = data["category"]
        if data.get("difficulty"):
            current_yaml["intro"]["stats"]["difficulty"] = data["difficulty"]
        if data.get("estimated_time"):
            current_yaml["intro"]["stats"]["estimated_time"] = data["estimated_time"]

        # Write back
        async with aiofiles.open(yaml_path, "w", encoding="utf-8") as f:
            await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False))

        # Reload the solution
        updated_solution = await self.reload_solution(solution_id)
        if updated_solution:
            logger.info(f"Updated solution: {solution_id}")
            return updated_solution
        else:
            raise Exception("Failed to reload updated solution")

    async def delete_solution(self, solution_id: str, move_to_trash: bool = True) -> bool:
        """Delete a solution (optionally move to trash instead of permanent delete)"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        solution_path = Path(solution.base_path)

        if move_to_trash:
            # Move to .trash directory
            trash_dir = self.solutions_dir / ".trash"
            trash_dir.mkdir(exist_ok=True)

            # Use timestamp to avoid conflicts
            import time
            trash_name = f"{solution_id}_{int(time.time())}"
            trash_path = trash_dir / trash_name

            shutil.move(str(solution_path), str(trash_path))
            logger.info(f"Moved solution to trash: {solution_id} -> {trash_path}")
        else:
            # Permanent delete
            shutil.rmtree(solution_path)
            logger.info(f"Permanently deleted solution: {solution_id}")

        # Remove from cache
        if solution_id in self.solutions:
            del self.solutions[solution_id]
        if solution_id in self._device_configs:
            del self._device_configs[solution_id]

        return True

    def validate_asset_path(self, relative_path: str) -> bool:
        """Validate that asset path is safe (no path traversal)"""
        # Normalize and check for path traversal
        normalized = Path(relative_path).as_posix()
        if ".." in normalized or normalized.startswith("/"):
            return False

        # Check file extension
        ext = Path(relative_path).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False

        return True

    async def save_asset(
        self,
        solution_id: str,
        file_content: bytes,
        relative_path: str,
        update_yaml_field: Optional[str] = None
    ) -> str:
        """Save an uploaded file to the solution directory"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        # Validate path
        if not self.validate_asset_path(relative_path):
            raise ValueError(f"Invalid asset path: {relative_path}")

        # Build full path
        solution_path = Path(solution.base_path)
        asset_path = solution_path / relative_path

        # Ensure parent directory exists
        asset_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        async with aiofiles.open(asset_path, "wb") as f:
            await f.write(file_content)

        logger.info(f"Saved asset: {solution_id}/{relative_path}")

        # Optionally update solution.yaml field (e.g., cover_image)
        if update_yaml_field:
            yaml_path = solution_path / "solution.yaml"
            async with aiofiles.open(yaml_path, "r", encoding="utf-8") as f:
                content = await f.read()
                current_yaml = yaml.safe_load(content)

            # Handle nested fields like "intro.cover_image"
            fields = update_yaml_field.split(".")
            target = current_yaml
            for field in fields[:-1]:
                target = target.setdefault(field, {})
            target[fields[-1]] = relative_path

            async with aiofiles.open(yaml_path, "w", encoding="utf-8") as f:
                await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False))

            # Reload solution
            await self.reload_solution(solution_id)

        return relative_path

    async def list_files(self, solution_id: str) -> Dict[str, Any]:
        """List all files in the solution directory as a tree structure"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        solution_path = Path(solution.base_path)

        def build_tree(path: Path, relative_to: Path) -> List[Dict]:
            """Recursively build file tree"""
            items = []
            for item in sorted(path.iterdir()):
                relative_path = item.relative_to(relative_to)
                if item.name.startswith('.'):
                    continue  # Skip hidden files

                entry = {
                    "name": item.name,
                    "path": str(relative_path),
                    "type": "directory" if item.is_dir() else "file",
                }
                if item.is_dir():
                    entry["children"] = build_tree(item, relative_to)
                else:
                    entry["size"] = item.stat().st_size
                    entry["extension"] = item.suffix.lower()
                items.append(entry)
            return items

        return {
            "solution_id": solution_id,
            "files": build_tree(solution_path, solution_path)
        }

    async def delete_file(self, solution_id: str, relative_path: str) -> bool:
        """Delete a file from the solution directory"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        # Validate path (prevent path traversal)
        if ".." in relative_path or relative_path.startswith("/"):
            raise ValueError(f"Invalid path: {relative_path}")

        # Don't allow deleting solution.yaml
        if relative_path == "solution.yaml":
            raise ValueError("Cannot delete solution.yaml")

        file_path = Path(solution.base_path) / relative_path
        if not file_path.exists():
            raise ValueError(f"File not found: {relative_path}")

        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()

        logger.info(f"Deleted file: {solution_id}/{relative_path}")
        return True

    async def save_text_file(
        self,
        solution_id: str,
        relative_path: str,
        content: str
    ) -> str:
        """Create or update a text file (md, yaml, etc.)"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        # Validate path
        if ".." in relative_path or relative_path.startswith("/"):
            raise ValueError(f"Invalid path: {relative_path}")

        # Check extension
        ext = Path(relative_path).suffix.lower()
        if ext not in ALLOWED_DOC_EXTENSIONS | ALLOWED_CONFIG_EXTENSIONS:
            raise ValueError(f"Invalid file type: {ext}")

        file_path = Path(solution.base_path) / relative_path

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.info(f"Saved text file: {solution_id}/{relative_path}")
        return relative_path

    async def get_solution_structure(self, solution_id: str) -> Dict[str, Any]:
        """Get the complete solution structure for management UI"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        solution_path = Path(solution.base_path)

        def file_exists(path: Optional[str]) -> bool:
            if not path:
                return False
            return (solution_path / path).exists()

        # Build preset structure with file status
        presets = []
        for preset in solution.intro.presets:
            preset_data = {
                "id": preset.id,
                "name": preset.name,
                "name_zh": preset.name_zh,
                "description": preset.description,
                "description_zh": preset.description_zh,
                "badge": preset.badge,
                "badge_zh": preset.badge_zh,
                "section": None,
                "devices": [],
            }

            # Preset section files
            if preset.section:
                preset_data["section"] = {
                    "title": preset.section.title,
                    "title_zh": preset.section.title_zh,
                    "description_file": preset.section.description_file,
                    "description_file_zh": preset.section.description_file_zh,
                    "description_file_exists": file_exists(preset.section.description_file),
                    "description_file_zh_exists": file_exists(preset.section.description_file_zh),
                }

            # Preset devices
            for device in preset.devices:
                device_data = {
                    "id": device.id,
                    "name": device.name,
                    "name_zh": device.name_zh,
                    "type": device.type,
                    "required": device.required,
                    "config_file": device.config_file,
                    "section": None,
                    "targets": {},
                }

                # Device section files
                if device.section:
                    device_data["section"] = {
                        "title": device.section.title,
                        "title_zh": device.section.title_zh,
                        "description_file": device.section.description_file,
                        "description_file_zh": device.section.description_file_zh,
                        "description_file_exists": file_exists(device.section.description_file),
                        "description_file_zh_exists": file_exists(device.section.description_file_zh),
                        "troubleshoot_file": device.section.troubleshoot_file,
                        "troubleshoot_file_exists": file_exists(device.section.troubleshoot_file),
                    }

                # Device targets
                if device.targets:
                    for target_id, target in device.targets.items():
                        target_data = {
                            "name": target.name,
                            "name_zh": target.name_zh,
                            "description": target.description,
                            "description_zh": target.description_zh,
                            "default": target.default,
                            "config_file": target.config_file,
                            "section": None,
                        }
                        if target.section:
                            target_data["section"] = {
                                "description_file": target.section.description_file,
                                "description_file_zh": target.section.description_file_zh,
                                "description_file_exists": file_exists(target.section.description_file),
                                "description_file_zh_exists": file_exists(target.section.description_file_zh),
                            }
                        device_data["targets"][target_id] = target_data

                preset_data["devices"].append(device_data)

            presets.append(preset_data)

        return {
            "id": solution.id,
            "name": solution.name,
            "name_zh": solution.name_zh,
            "intro": {
                "summary": solution.intro.summary,
                "summary_zh": solution.intro.summary_zh,
                "category": solution.intro.category,
                "tags": solution.intro.tags,
                "cover_image": solution.intro.cover_image,
                "cover_image_exists": file_exists(solution.intro.cover_image),
                "description_file": solution.intro.description_file,
                "description_file_zh": solution.intro.description_file_zh,
                "description_file_exists": file_exists(solution.intro.description_file),
                "description_file_zh_exists": file_exists(solution.intro.description_file_zh),
                "links": solution.intro.links.model_dump() if solution.intro.links else {},
            },
            "deployment": {
                "guide_file": solution.deployment.guide_file,
                "guide_file_zh": solution.deployment.guide_file_zh,
                "guide_file_exists": file_exists(solution.deployment.guide_file),
                "guide_file_zh_exists": file_exists(solution.deployment.guide_file_zh),
            },
            "stats": solution.intro.stats.model_dump(),
            "presets": presets,
        }

    async def add_preset(self, solution_id: str, preset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new preset to the solution"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        yaml_path = Path(solution.base_path) / "solution.yaml"

        # Read current yaml
        async with aiofiles.open(yaml_path, "r") as f:
            content = await f.read()
            current_yaml = yaml.safe_load(content)

        # Ensure presets array exists
        if "intro" not in current_yaml:
            current_yaml["intro"] = {}
        if "presets" not in current_yaml["intro"]:
            current_yaml["intro"]["presets"] = []

        # Check for duplicate ID
        for preset in current_yaml["intro"]["presets"]:
            if preset.get("id") == preset_data.get("id"):
                raise ValueError(f"Preset with ID '{preset_data.get('id')}' already exists")

        # Add new preset
        new_preset = {
            "id": preset_data["id"],
            "name": preset_data["name"],
            "name_zh": preset_data.get("name_zh", preset_data["name"]),
            "description": preset_data.get("description", ""),
            "description_zh": preset_data.get("description_zh", ""),
            "badge": preset_data.get("badge"),
            "badge_zh": preset_data.get("badge_zh"),
            "device_groups": [],
            "devices": [],
        }
        current_yaml["intro"]["presets"].append(new_preset)

        # Write back
        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False, default_flow_style=False))

        # Reload solution
        await self.reload_solution(solution_id)
        logger.info(f"Added preset '{preset_data['id']}' to solution '{solution_id}'")

        return new_preset

    async def update_preset(self, solution_id: str, preset_id: str, preset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing preset"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        yaml_path = Path(solution.base_path) / "solution.yaml"

        async with aiofiles.open(yaml_path, "r") as f:
            content = await f.read()
            current_yaml = yaml.safe_load(content)

        # Find and update preset
        preset_found = False
        for preset in current_yaml.get("intro", {}).get("presets", []):
            if preset.get("id") == preset_id:
                # Update fields
                for key in ["name", "name_zh", "description", "description_zh", "badge", "badge_zh"]:
                    if key in preset_data:
                        preset[key] = preset_data[key]
                preset_found = True
                break

        if not preset_found:
            raise ValueError(f"Preset not found: {preset_id}")

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False, default_flow_style=False))

        await self.reload_solution(solution_id)
        logger.info(f"Updated preset '{preset_id}' in solution '{solution_id}'")

        return preset_data

    async def delete_preset(self, solution_id: str, preset_id: str) -> bool:
        """Delete a preset from the solution"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        yaml_path = Path(solution.base_path) / "solution.yaml"

        async with aiofiles.open(yaml_path, "r") as f:
            content = await f.read()
            current_yaml = yaml.safe_load(content)

        presets = current_yaml.get("intro", {}).get("presets", [])
        original_len = len(presets)
        current_yaml["intro"]["presets"] = [p for p in presets if p.get("id") != preset_id]

        if len(current_yaml["intro"]["presets"]) == original_len:
            raise ValueError(f"Preset not found: {preset_id}")

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False, default_flow_style=False))

        await self.reload_solution(solution_id)
        logger.info(f"Deleted preset '{preset_id}' from solution '{solution_id}'")

        return True

    async def add_preset_device(
        self,
        solution_id: str,
        preset_id: str,
        device_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a new device (deployment step) to a preset"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        yaml_path = Path(solution.base_path) / "solution.yaml"

        async with aiofiles.open(yaml_path, "r") as f:
            content = await f.read()
            current_yaml = yaml.safe_load(content)

        # Find preset
        preset_found = False
        for preset in current_yaml.get("intro", {}).get("presets", []):
            if preset.get("id") == preset_id:
                if "devices" not in preset:
                    preset["devices"] = []

                # Check for duplicate device ID
                for device in preset["devices"]:
                    if device.get("id") == device_data.get("id"):
                        raise ValueError(f"Device with ID '{device_data.get('id')}' already exists in preset")

                # Build device entry
                new_device = {
                    "id": device_data["id"],
                    "name": device_data["name"],
                    "name_zh": device_data.get("name_zh", device_data["name"]),
                    "type": device_data.get("type", "manual"),
                    "required": device_data.get("required", True),
                }

                # Add section if description files are provided
                if device_data.get("description_file") or device_data.get("description_file_zh"):
                    new_device["section"] = {
                        "title": device_data.get("section_title", device_data["name"]),
                        "title_zh": device_data.get("section_title_zh", device_data.get("name_zh", device_data["name"])),
                        "description_file": device_data.get("description_file"),
                        "description_file_zh": device_data.get("description_file_zh"),
                    }

                preset["devices"].append(new_device)
                preset_found = True
                break

        if not preset_found:
            raise ValueError(f"Preset not found: {preset_id}")

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False, default_flow_style=False))

        await self.reload_solution(solution_id)
        logger.info(f"Added device '{device_data['id']}' to preset '{preset_id}' in solution '{solution_id}'")

        return device_data

    async def update_preset_device(
        self,
        solution_id: str,
        preset_id: str,
        device_id: str,
        device_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a device in a preset"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        yaml_path = Path(solution.base_path) / "solution.yaml"

        async with aiofiles.open(yaml_path, "r") as f:
            content = await f.read()
            current_yaml = yaml.safe_load(content)

        device_found = False
        for preset in current_yaml.get("intro", {}).get("presets", []):
            if preset.get("id") == preset_id:
                for device in preset.get("devices", []):
                    if device.get("id") == device_id:
                        # Update fields
                        for key in ["name", "name_zh", "type", "required", "config_file"]:
                            if key in device_data:
                                device[key] = device_data[key]

                        # Update section
                        if any(k in device_data for k in ["description_file", "description_file_zh", "section_title", "section_title_zh"]):
                            if "section" not in device:
                                device["section"] = {}
                            if "description_file" in device_data:
                                device["section"]["description_file"] = device_data["description_file"]
                            if "description_file_zh" in device_data:
                                device["section"]["description_file_zh"] = device_data["description_file_zh"]
                            if "section_title" in device_data:
                                device["section"]["title"] = device_data["section_title"]
                            if "section_title_zh" in device_data:
                                device["section"]["title_zh"] = device_data["section_title_zh"]

                        device_found = True
                        break
                break

        if not device_found:
            raise ValueError(f"Device '{device_id}' not found in preset '{preset_id}'")

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False, default_flow_style=False))

        await self.reload_solution(solution_id)
        logger.info(f"Updated device '{device_id}' in preset '{preset_id}' in solution '{solution_id}'")

        return device_data

    async def delete_preset_device(
        self,
        solution_id: str,
        preset_id: str,
        device_id: str
    ) -> bool:
        """Delete a device from a preset"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        yaml_path = Path(solution.base_path) / "solution.yaml"

        async with aiofiles.open(yaml_path, "r") as f:
            content = await f.read()
            current_yaml = yaml.safe_load(content)

        device_found = False
        for preset in current_yaml.get("intro", {}).get("presets", []):
            if preset.get("id") == preset_id:
                original_len = len(preset.get("devices", []))
                preset["devices"] = [d for d in preset.get("devices", []) if d.get("id") != device_id]
                if len(preset["devices"]) < original_len:
                    device_found = True
                break

        if not device_found:
            raise ValueError(f"Device '{device_id}' not found in preset '{preset_id}'")

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False, default_flow_style=False))

        await self.reload_solution(solution_id)
        logger.info(f"Deleted device '{device_id}' from preset '{preset_id}' in solution '{solution_id}'")

        return True

    async def update_solution_links(self, solution_id: str, links: Dict[str, str]) -> Dict[str, str]:
        """Update solution external links (wiki, github)"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        yaml_path = Path(solution.base_path) / "solution.yaml"

        async with aiofiles.open(yaml_path, "r") as f:
            content = await f.read()
            current_yaml = yaml.safe_load(content)

        if "intro" not in current_yaml:
            current_yaml["intro"] = {}
        if "links" not in current_yaml["intro"]:
            current_yaml["intro"]["links"] = {}

        for key, value in links.items():
            if key in ["wiki", "github"]:
                current_yaml["intro"]["links"][key] = value

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False, default_flow_style=False))

        await self.reload_solution(solution_id)
        return links

    async def update_solution_tags(self, solution_id: str, tags: List[str]) -> List[str]:
        """Update solution tags"""
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        yaml_path = Path(solution.base_path) / "solution.yaml"

        async with aiofiles.open(yaml_path, "r") as f:
            content = await f.read()
            current_yaml = yaml.safe_load(content)

        if "intro" not in current_yaml:
            current_yaml["intro"] = {}
        current_yaml["intro"]["tags"] = tags

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False, default_flow_style=False))

        await self.reload_solution(solution_id)
        return tags


# Global instance
solution_manager = SolutionManager()
