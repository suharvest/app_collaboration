"""
Solution loading and management service
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml
import aiofiles
import markdown

from ..models.solution import Solution
from ..models.device import DeviceConfig
from ..config import settings

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
            async with aiofiles.open(catalog_path, "r") as f:
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
            async with aiofiles.open(solution_file, "r") as f:
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
            async with aiofiles.open(file_path, "r") as f:
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
            async with aiofiles.open(config_path, "r") as f:
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
            async with aiofiles.open(yaml_path, "w") as f:
                await f.write(yaml.dump(solution_yaml, allow_unicode=True, sort_keys=False))

            # Create placeholder markdown files
            description_en = f"# {data['name']}\n\n{data['summary']}\n"
            description_zh = f"# {data.get('name_zh') or data['name']}\n\n{data.get('summary_zh') or data['summary']}\n"

            async with aiofiles.open(solution_path / "intro" / "description.md", "w") as f:
                await f.write(description_en)
            async with aiofiles.open(solution_path / "intro" / "description_zh.md", "w") as f:
                await f.write(description_zh)
            async with aiofiles.open(solution_path / "deploy" / "guide.md", "w") as f:
                await f.write(f"## Deployment Guide\n\nFollow the steps below to deploy {data['name']}.\n")
            async with aiofiles.open(solution_path / "deploy" / "guide_zh.md", "w") as f:
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
        async with aiofiles.open(yaml_path, "r") as f:
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
        async with aiofiles.open(yaml_path, "w") as f:
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
            async with aiofiles.open(yaml_path, "r") as f:
                content = await f.read()
                current_yaml = yaml.safe_load(content)

            # Handle nested fields like "intro.cover_image"
            fields = update_yaml_field.split(".")
            target = current_yaml
            for field in fields[:-1]:
                target = target.setdefault(field, {})
            target[fields[-1]] = relative_path

            async with aiofiles.open(yaml_path, "w") as f:
                await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False))

            # Reload solution
            await self.reload_solution(solution_id)

        return relative_path


# Global instance
solution_manager = SolutionManager()
