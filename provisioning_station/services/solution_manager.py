"""
Solution loading and management service
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml
import aiofiles
import markdown

from ..models.solution import Solution
from ..models.device import DeviceConfig
from ..config import settings

logger = logging.getLogger(__name__)


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


# Global instance
solution_manager = SolutionManager()
