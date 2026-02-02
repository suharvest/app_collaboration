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
from .markdown_parser import (
    parse_bilingual_markdown,
    parse_deployment_guide,
    parse_guide_pair,
    parse_single_language_guide,
    validate_structure_consistency,
    ParseResult,
    StructureValidationResult,
    DeploymentStep,
    PresetGuide,
)

logger = logging.getLogger(__name__)

# Valid file extensions for uploads
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}
ALLOWED_DOC_EXTENSIONS = {".md"}
ALLOWED_CONFIG_EXTENSIONS = {".yaml", ".yml"}
ALLOWED_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOC_EXTENSIONS | ALLOWED_CONFIG_EXTENSIONS
)

# Solution ID validation pattern: lowercase letters, numbers, underscore, must start with letter
SOLUTION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class SolutionManager:
    """Solution loading and management service"""

    def __init__(self):
        self.solutions_dir = settings.solutions_dir
        self.solutions: Dict[str, Solution] = {}
        self._device_configs: Dict[str, Dict[str, DeviceConfig]] = (
            {}
        )  # solution_id -> device_id -> config
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
            logger.info(
                f"Loaded {len(self._global_device_catalog)} devices from global catalog"
            )
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

    async def find_device_async(
        self, solution_id: str, device_id: str, preset_id: str = None
    ):
        """Find a device by ID from guide.md.

        Args:
            solution_id: The solution ID
            device_id: The device ID to find
            preset_id: Optional preset ID to search within (unused, for API compatibility)

        Returns:
            Device dict if found, None otherwise
        """
        deployment_info = await self.get_deployment_from_guide(solution_id, "en")
        if deployment_info and deployment_info.get("devices"):
            for device in deployment_info["devices"]:
                if device.get("id") == device_id:
                    return device
        return None

    async def get_all_devices_async(self, solution_id: str, preset_id: str = None):
        """Get all devices from guide.md.

        Args:
            solution_id: The solution ID
            preset_id: Optional preset ID to filter by

        Returns:
            List of device dicts
        """
        deployment_info = await self.get_deployment_from_guide(solution_id, "en")
        if deployment_info and deployment_info.get("devices"):
            all_devices = deployment_info["devices"]
            if preset_id and deployment_info.get("presets"):
                preset = next(
                    (p for p in deployment_info["presets"] if p["id"] == preset_id), None
                )
                if preset and preset.get("devices"):
                    device_ids = preset["devices"]
                    return [d for d in all_devices if d["id"] in device_ids]
            return all_devices
        return []

    def count_devices_in_solution(self, solution: Solution) -> int:
        """Count unique devices in a solution (legacy - always returns 0).

        Kept for backward compatibility. Use count_steps_from_guide() instead.
        """
        # Devices are now defined in guide.md, not solution.yaml
        return 0

    # Legacy alias for backward compatibility
    def find_device_in_solution(self, solution: Solution, device_id: str, preset_id: str = None):
        """Legacy method - always returns None. Use find_device_async() instead."""
        return None

    def get_all_devices_from_solution(self, solution: Solution, preset_id: str = None):
        """Legacy method - always returns empty list. Use get_all_devices_async() instead."""
        return []

    def _legacy_count_devices(self, solution: Solution) -> int:
        """Internal: Count devices from solution.yaml presets (deprecated)."""
        device_ids = set()
        if solution.intro and solution.intro.presets:
            for preset in solution.intro.presets:
                if preset.devices:
                    for device in preset.devices:
                        device_ids.add(device.id)
        return len(device_ids)

    async def load_markdown(
        self, solution_id: str, relative_path: str, convert_to_html: bool = True
    ) -> Optional[str]:
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
                md = markdown.Markdown(extensions=["extra", "codehilite", "toc"])
                return md.convert(content)
            return content
        except Exception as e:
            logger.error(f"Failed to load markdown {file_path}: {e}")
            return None

    async def load_bilingual_markdown(
        self,
        solution_id: str,
        relative_path: str,
        lang: str = "en",
        convert_to_html: bool = True,
    ) -> Optional[str]:
        """Load bilingual markdown and return content for specified language.

        This method handles the new bilingual format with `<!-- @lang:en -->` markers.

        Args:
            solution_id: The solution ID
            relative_path: Path to the bilingual markdown file
            lang: Target language ('en' or 'zh')
            convert_to_html: Whether to convert to HTML

        Returns:
            The markdown/HTML content for the specified language
        """
        solution = self.get_solution(solution_id)
        if not solution or not solution.base_path:
            return None

        file_path = Path(solution.base_path) / relative_path
        if not file_path.exists():
            logger.warning(f"Bilingual markdown file not found: {file_path}")
            return None

        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            # Parse bilingual content
            lang_content = parse_bilingual_markdown(content, lang)

            if convert_to_html:
                md = markdown.Markdown(extensions=["extra", "codehilite", "toc"])
                return md.convert(lang_content)
            return lang_content
        except Exception as e:
            logger.error(f"Failed to load bilingual markdown {file_path}: {e}")
            return None

    async def parse_deployment_guide(
        self, solution_id: str, guide_path: str
    ) -> Optional[ParseResult]:
        """Parse a deployment guide markdown file.

        Args:
            solution_id: The solution ID
            guide_path: Path to the guide.md file

        Returns:
            ParseResult with parsed steps, presets, and success content
        """
        solution = self.get_solution(solution_id)
        if not solution or not solution.base_path:
            return None

        file_path = Path(solution.base_path) / guide_path
        if not file_path.exists():
            logger.warning(f"Deployment guide not found: {file_path}")
            return None

        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            result = parse_deployment_guide(content)
            if result.has_errors:
                for error in result.errors:
                    logger.warning(f"Parse error in {guide_path}: {error}")
            return result
        except Exception as e:
            logger.error(f"Failed to parse deployment guide {file_path}: {e}")
            return None

    async def validate_guide_pair(
        self, solution_id: str
    ) -> Optional[StructureValidationResult]:
        """Validate structure consistency between guide.md and guide_zh.md.

        Args:
            solution_id: The solution ID

        Returns:
            StructureValidationResult with validation errors/warnings
        """
        solution = self.get_solution(solution_id)
        if not solution or not solution.base_path:
            return None

        base_path = Path(solution.base_path)

        # Get guide file paths from solution config
        guide_en_path = solution.deployment.guide_file or "guide.md"
        guide_zh_path = solution.deployment.guide_file_zh or "guide_zh.md"

        en_file = base_path / guide_en_path
        zh_file = base_path / guide_zh_path

        # Check if both files exist
        en_exists = en_file.exists()
        zh_exists = zh_file.exists()

        if not en_exists and not zh_exists:
            result = StructureValidationResult(valid=True)
            result.warnings.append(
                type("ParseWarning", (), {"message": "No guide files found", "line_number": None})()
            )
            return result

        if not en_exists:
            from .markdown_parser import ParseError, ParseErrorType, ParseWarning
            result = StructureValidationResult(valid=False)
            result.warnings.append(
                ParseWarning(message=f"English guide not found: {guide_en_path}")
            )
            return result

        if not zh_exists:
            from .markdown_parser import ParseWarning
            result = StructureValidationResult(valid=True)
            result.warnings.append(
                ParseWarning(message=f"Chinese guide not found: {guide_zh_path}")
            )
            return result

        try:
            # Load both files
            async with aiofiles.open(en_file, "r", encoding="utf-8") as f:
                en_content = await f.read()
            async with aiofiles.open(zh_file, "r", encoding="utf-8") as f:
                zh_content = await f.read()

            # Parse and validate
            _, validation = parse_guide_pair(en_content, zh_content)
            return validation

        except Exception as e:
            logger.error(f"Failed to validate guide pair: {e}")
            return None

    async def get_guide_structure(
        self, solution_id: str
    ) -> Optional[dict]:
        """Get parsed structure from guide files for management UI.

        Returns structure with presets and steps extracted from guide.md,
        plus validation status.
        """
        solution = self.get_solution(solution_id)
        if not solution or not solution.base_path:
            return None

        base_path = Path(solution.base_path)
        guide_en_path = solution.deployment.guide_file or "guide.md"
        guide_zh_path = solution.deployment.guide_file_zh or "guide_zh.md"

        en_file = base_path / guide_en_path
        zh_file = base_path / guide_zh_path

        result = {
            "guide_en": {
                "path": guide_en_path,
                "exists": en_file.exists(),
                "size": en_file.stat().st_size if en_file.exists() else 0,
            },
            "guide_zh": {
                "path": guide_zh_path,
                "exists": zh_file.exists(),
                "size": zh_file.stat().st_size if zh_file.exists() else 0,
            },
            "validation": None,
            "presets": [],
        }

        # Validate if both files exist
        if en_file.exists() and zh_file.exists():
            validation = await self.validate_guide_pair(solution_id)
            if validation:
                result["validation"] = {
                    "valid": validation.valid,
                    "errors": [
                        {
                            "type": str(e.error_type.value),
                            "message": e.message,
                            "suggestion": e.suggestion,
                        }
                        for e in validation.errors
                    ],
                    "warnings": [
                        {"message": w.message}
                        for w in validation.warnings
                    ],
                }

            # Parse EN file to get structure
            try:
                async with aiofiles.open(en_file, "r", encoding="utf-8") as f:
                    en_content = await f.read()
                en_result = parse_single_language_guide(en_content)

                for preset in en_result.presets:
                    preset_data = {
                        "id": preset.id,
                        "name": preset.name,
                        "description": preset.description,
                        "is_default": preset.is_default,
                        "steps": [
                            {
                                "id": s.id,
                                "name": s.title_en or s.id,  # Use title_en as name
                                "type": s.type,
                                "required": s.required,
                                "config_file": s.config_file,
                                "targets": [
                                    {
                                        "id": t.id,
                                        "name": t.name,
                                        "is_default": t.is_default,
                                    }
                                    for t in (s.targets or [])
                                ],
                            }
                            for s in preset.steps
                        ],
                    }
                    result["presets"].append(preset_data)

            except Exception as e:
                logger.error(f"Failed to parse EN guide for structure: {e}")

        return result

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
    # Guide-based Deployment Methods (Simplified Structure)
    # ============================================

    async def validate_preset_ids(self, solution_id: str) -> List[str]:
        """Validate that preset IDs in YAML match those in guide.md.

        Args:
            solution_id: The solution ID

        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        solution = self.get_solution(solution_id)
        if not solution:
            return [f"Solution not found: {solution_id}"]

        # Get preset IDs from YAML (used for intro page)
        yaml_preset_ids = set()
        if solution.intro and solution.intro.presets:
            yaml_preset_ids = {p.id for p in solution.intro.presets}

        # Parse guide.md to get preset IDs (used for deploy page)
        guide_file = solution.deployment.guide_file or "guide.md"
        guide_path = Path(solution.base_path) / guide_file

        if not guide_path.exists():
            errors.append(f"Guide file not found: {guide_file}")
            return errors

        try:
            async with aiofiles.open(guide_path, "r", encoding="utf-8") as f:
                content = await f.read()

            parse_result = parse_single_language_guide(content)
            guide_preset_ids = {p.id for p in parse_result.presets}

            # Check for mismatches
            missing_in_guide = yaml_preset_ids - guide_preset_ids
            extra_in_guide = guide_preset_ids - yaml_preset_ids

            if missing_in_guide:
                errors.append(
                    f"Presets in YAML but not in guide.md: {sorted(missing_in_guide)}"
                )
            if extra_in_guide:
                errors.append(
                    f"Presets in guide.md but not in YAML: {sorted(extra_in_guide)}"
                )

            if errors:
                logger.warning(
                    f"Solution {solution_id} preset mismatch:\n" + "\n".join(errors)
                )

        except Exception as e:
            logger.error(f"Failed to validate preset IDs for {solution_id}: {e}")
            errors.append(str(e))

        return errors

    async def count_steps_from_guide(self, solution_id: str) -> int:
        """Count unique step IDs from guide.md.

        Args:
            solution_id: The solution ID

        Returns:
            Number of unique step IDs across all presets
        """
        solution = self.get_solution(solution_id)
        if not solution or not solution.base_path:
            return 0

        guide_file = solution.deployment.guide_file or "guide.md"
        guide_path = Path(solution.base_path) / guide_file

        if not guide_path.exists():
            return 0

        try:
            async with aiofiles.open(guide_path, "r", encoding="utf-8") as f:
                content = await f.read()

            parse_result = parse_single_language_guide(content)

            # Count unique step IDs across all presets
            step_ids = set()
            for preset in parse_result.presets:
                for step in preset.steps:
                    step_ids.add(step.id)

            return len(step_ids)

        except Exception as e:
            logger.error(f"Failed to count steps from guide for {solution_id}: {e}")
            return 0

    async def get_deployment_from_guide(
        self, solution_id: str, lang: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """Load deployment page data 100% from guide.md.

        This is the core method for the simplified structure. All deployment
        information is parsed from guide.md and guide_zh.md, eliminating
        redundancy with YAML.

        Args:
            solution_id: The solution ID
            lang: Language code ('en' or 'zh')

        Returns:
            Dict with devices, presets, overview, and post_deployment
        """
        solution = self.get_solution(solution_id)
        if not solution or not solution.base_path:
            return None

        base_path = Path(solution.base_path)

        # Validate preset IDs consistency (logs warnings)
        await self.validate_preset_ids(solution_id)

        # Get guide file paths
        guide_en_path = solution.deployment.guide_file or "guide.md"
        guide_zh_path = solution.deployment.guide_file_zh or "guide_zh.md"

        en_file = base_path / guide_en_path
        zh_file = base_path / guide_zh_path

        # Parse both EN and ZH guide files
        en_result = None
        zh_result = None

        if en_file.exists():
            try:
                async with aiofiles.open(en_file, "r", encoding="utf-8") as f:
                    en_content = await f.read()
                en_result = parse_single_language_guide(en_content)
            except Exception as e:
                logger.error(f"Failed to parse EN guide: {e}")

        if zh_file.exists():
            try:
                async with aiofiles.open(zh_file, "r", encoding="utf-8") as f:
                    zh_content = await f.read()
                zh_result = parse_single_language_guide(zh_content)
            except Exception as e:
                logger.error(f"Failed to parse ZH guide: {e}")

        if not en_result:
            logger.warning(f"No EN guide found for {solution_id}")
            return None

        # Build merged result with translations
        devices = []
        presets = []
        seen_device_ids = set()

        for en_preset in en_result.presets:
            # Find corresponding ZH preset
            zh_preset = None
            if zh_result:
                zh_preset = next(
                    (p for p in zh_result.presets if p.id == en_preset.id), None
                )

            preset_device_ids = []

            for en_step in en_preset.steps:
                # Find corresponding ZH step
                zh_step = None
                if zh_preset:
                    zh_step = next(
                        (s for s in zh_preset.steps if s.id == en_step.id), None
                    )

                # Build device info (compatible with frontend)
                device = await self._build_device_from_step(
                    solution_id, en_step, zh_step, lang
                )

                # Only add unique devices to global list
                if en_step.id not in seen_device_ids:
                    devices.append(device)
                    seen_device_ids.add(en_step.id)

                preset_device_ids.append(en_step.id)

            # Build preset info with section for frontend compatibility
            preset_description = (
                zh_preset.description if lang == "zh" and zh_preset
                else en_preset.description
            )
            presets.append({
                "id": en_preset.id,
                "name": (
                    zh_preset.name if lang == "zh" and zh_preset
                    else en_preset.name
                ),
                "name_zh": zh_preset.name if zh_preset else en_preset.name,
                "description": preset_description,
                "description_zh": zh_preset.description if zh_preset else "",
                "devices": preset_device_ids,
                # Section object for frontend renderPresetSectionContent()
                "section": {
                    "title": "",
                    "description": preset_description,
                } if preset_description else None,
            })

        # Build post_deployment from success content
        post_deployment = None
        if en_result.success:
            success_content = (
                zh_result.success.content_en if lang == "zh" and zh_result and zh_result.success
                else en_result.success.content_en
            )

            # Extract Next Steps links from markdown: [title](url)
            next_steps = []
            if success_content:
                import re
                links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', success_content)
                for title, url in links:
                    next_steps.append({"title": title, "url": url})

            post_deployment = {
                "success_message": success_content,
                "next_steps": next_steps,
            }

        # Build overview
        overview = (
            zh_result.overview_en if lang == "zh" and zh_result
            else en_result.overview_en
        )

        return {
            "solution_id": solution_id,
            "guide": overview,
            "selection_mode": solution.deployment.selection_mode or "sequential",
            "devices": devices,
            "device_groups": [],  # No longer used
            "presets": presets,
            "order": [],  # Determined by guide.md structure
            "post_deployment": post_deployment,
        }

    async def _build_device_from_step(
        self,
        solution_id: str,
        en_step: DeploymentStep,
        zh_step: Optional[DeploymentStep],
        lang: str,
    ) -> Dict[str, Any]:
        """Build a device dict from a parsed step.

        Args:
            solution_id: The solution ID
            en_step: English step from markdown parser
            zh_step: Chinese step (optional)
            lang: Target language

        Returns:
            Device dict compatible with frontend
        """
        solution = self.get_solution(solution_id)

        # Choose titles based on language
        title = zh_step.title_en if lang == "zh" and zh_step else en_step.title_en
        title_zh = zh_step.title_en if zh_step else en_step.title_en

        device = {
            "id": en_step.id,
            "name": title,
            "name_zh": title_zh,
            "type": en_step.type,
            "required": en_step.required,
        }

        # Build section content
        section = {
            "title": title,
            "title_zh": title_zh,
        }

        # Description (already HTML from parser)
        if lang == "zh" and zh_step and zh_step.section.description:
            section["description"] = zh_step.section.description
        elif en_step.section.description:
            section["description"] = en_step.section.description

        # Troubleshoot
        if lang == "zh" and zh_step and zh_step.section.troubleshoot:
            section["troubleshoot"] = zh_step.section.troubleshoot
        elif en_step.section.troubleshoot:
            section["troubleshoot"] = en_step.section.troubleshoot

        # Wiring - use Chinese step's wiring for Chinese language
        wiring_source = (
            zh_step.section.wiring if lang == "zh" and zh_step and zh_step.section.wiring
            else en_step.section.wiring
        )
        if wiring_source:
            section["wiring"] = {
                "image": (
                    f"/api/solutions/{solution_id}/assets/{wiring_source.image}"
                    if wiring_source.image else None
                ),
                "steps": wiring_source.steps,
            }

        device["section"] = section

        # Load device config if specified
        if en_step.config_file:
            device["config_file"] = en_step.config_file
            config = await self.load_device_config(solution_id, en_step.config_file)
            if config:
                if config.ssh:
                    device["ssh"] = config.ssh.model_dump()
                if config.user_inputs:
                    device["user_inputs"] = [
                        inp.model_dump() for inp in config.user_inputs
                    ]
                if en_step.type == "preview":
                    device["preview"] = {
                        "user_inputs": (
                            [inp.model_dump() for inp in config.user_inputs]
                            if config.user_inputs
                            else []
                        ),
                        "video": config.video.model_dump() if config.video else None,
                        "mqtt": config.mqtt.model_dump() if config.mqtt else None,
                        "overlay": config.overlay.model_dump() if config.overlay else None,
                        "display": config.display.model_dump() if config.display else None,
                    }

        # Build targets (for docker_deploy type)
        if en_step.targets:
            # Build a lookup for Chinese targets by ID
            zh_targets_by_id = {}
            if zh_step and zh_step.targets:
                for zt in zh_step.targets:
                    zh_targets_by_id[zt.id] = zt

            targets_data = {}
            for target in en_step.targets:
                # Get corresponding Chinese target for translation
                zh_target = zh_targets_by_id.get(target.id)
                zh_name = zh_target.name if zh_target else target.name
                zh_desc = zh_target.description if zh_target else target.description
                zh_troubleshoot = (
                    zh_target.troubleshoot if zh_target else target.troubleshoot
                )

                target_info = {
                    "name": target.name if lang == "en" else zh_name,
                    "name_zh": zh_name,
                    "description": (
                        target.description if lang == "en" else zh_desc
                    ),
                    "description_zh": zh_desc,
                    "default": target.default,
                    "config_file": target.config_file,
                }

                # Load target's device config for user_inputs and ssh settings
                if target.config_file:
                    target_config = await self.load_device_config(
                        solution_id, target.config_file
                    )
                    if target_config:
                        if target_config.ssh:
                            target_info["ssh"] = target_config.ssh.model_dump()
                        if target_config.user_inputs:
                            target_info["user_inputs"] = [
                                inp.model_dump() for inp in target_config.user_inputs
                            ]

                # Build target section content (description, troubleshoot, wiring)
                target_section = {}

                # Add description
                if lang == "en" and target.description:
                    target_section["description"] = target.description
                elif lang == "zh" and zh_desc:
                    target_section["description"] = zh_desc

                # Add troubleshoot
                if lang == "en" and target.troubleshoot:
                    target_section["troubleshoot"] = target.troubleshoot
                elif lang == "zh" and zh_troubleshoot:
                    target_section["troubleshoot"] = zh_troubleshoot

                # Add wiring (from target.wiring parsed from guide.md)
                # For Chinese: use zh_target's wiring if available
                wiring_source = (
                    zh_target.wiring if lang == "zh" and zh_target and zh_target.wiring
                    else target.wiring
                )
                if wiring_source:
                    wiring_data = {
                        "image": (
                            f"/api/solutions/{solution_id}/assets/{wiring_source.image}"
                            if wiring_source.image else None
                        ),
                        "steps": wiring_source.steps,
                    }
                    target_section["wiring"] = wiring_data

                if target_section:
                    target_info["section"] = target_section

                targets_data[target.id] = target_info
            device["targets"] = targets_data

        return device

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
            raise ValueError(
                f"Invalid solution ID format: {solution_id}. Must match pattern: {SOLUTION_ID_PATTERN.pattern}"
            )

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
                await f.write(
                    yaml.dump(solution_yaml, allow_unicode=True, sort_keys=False)
                )

            # Create placeholder markdown files
            description_en = f"# {data['name']}\n\n{data['summary']}\n"
            description_zh = f"# {data.get('name_zh') or data['name']}\n\n{data.get('summary_zh') or data['summary']}\n"

            async with aiofiles.open(
                solution_path / "intro" / "description.md", "w", encoding="utf-8"
            ) as f:
                await f.write(description_en)
            async with aiofiles.open(
                solution_path / "intro" / "description_zh.md", "w", encoding="utf-8"
            ) as f:
                await f.write(description_zh)
            async with aiofiles.open(
                solution_path / "deploy" / "guide.md", "w", encoding="utf-8"
            ) as f:
                await f.write(
                    f"## Deployment Guide\n\nFollow the steps below to deploy {data['name']}.\n"
                )
            async with aiofiles.open(
                solution_path / "deploy" / "guide_zh.md", "w", encoding="utf-8"
            ) as f:
                await f.write(
                    f"## 部署指南\n\n按照以下步骤部署 {data.get('name_zh') or data['name']}。\n"
                )

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
        if "enabled" in data:
            current_yaml["enabled"] = data["enabled"]
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

    async def delete_solution(
        self, solution_id: str, move_to_trash: bool = True
    ) -> bool:
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
        update_yaml_field: Optional[str] = None,
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
                await f.write(
                    yaml.dump(current_yaml, allow_unicode=True, sort_keys=False)
                )

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
                if item.name.startswith("."):
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
            "files": build_tree(solution_path, solution_path),
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
        self, solution_id: str, relative_path: str, content: str
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
                    "description_file_exists": file_exists(
                        preset.section.description_file
                    ),
                    "description_file_zh_exists": file_exists(
                        preset.section.description_file_zh
                    ),
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
                        "description_file_exists": file_exists(
                            device.section.description_file
                        ),
                        "description_file_zh_exists": file_exists(
                            device.section.description_file_zh
                        ),
                        "troubleshoot_file": device.section.troubleshoot_file,
                        "troubleshoot_file_exists": file_exists(
                            device.section.troubleshoot_file
                        ),
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
                                "description_file_exists": file_exists(
                                    target.section.description_file
                                ),
                                "description_file_zh_exists": file_exists(
                                    target.section.description_file_zh
                                ),
                            }
                        device_data["targets"][target_id] = target_data

                preset_data["devices"].append(device_data)

            presets.append(preset_data)

        # Build required devices with image URLs
        required_devices = []
        if solution.intro.required_devices:
            # Use legacy required_devices if present
            for device in solution.intro.required_devices:
                dev = device.model_dump()
                if device.image:
                    dev["image"] = f"/api/solutions/{solution_id}/assets/{device.image}"
                required_devices.append(dev)
        elif solution.intro.device_catalog:
            # Fall back to device_catalog if required_devices is empty
            for device_id, device in solution.intro.device_catalog.items():
                dev = {
                    "id": device_id,
                    "name": device.name,
                    "name_zh": device.name_zh,
                    "description": device.description,
                    "description_zh": device.description_zh,
                }
                if device.image:
                    dev["image"] = f"/api/solutions/{solution_id}/assets/{device.image}"
                if device.product_url:
                    dev["purchase_url"] = device.product_url
                required_devices.append(dev)

        return {
            "id": solution.id,
            "name": solution.name,
            "name_zh": solution.name_zh,
            "enabled": solution.enabled,
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
                "description_file_zh_exists": file_exists(
                    solution.intro.description_file_zh
                ),
                "links": (
                    solution.intro.links.model_dump() if solution.intro.links else {}
                ),
                "required_devices": required_devices,
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

    async def add_preset(
        self, solution_id: str, preset_data: Dict[str, Any]
    ) -> Dict[str, Any]:
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
                raise ValueError(
                    f"Preset with ID '{preset_data.get('id')}' already exists"
                )

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
            await f.write(
                yaml.dump(
                    current_yaml,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
            )

        # Reload solution
        await self.reload_solution(solution_id)
        logger.info(f"Added preset '{preset_data['id']}' to solution '{solution_id}'")

        return new_preset

    async def update_preset(
        self, solution_id: str, preset_id: str, preset_data: Dict[str, Any]
    ) -> Dict[str, Any]:
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
                for key in [
                    "name",
                    "name_zh",
                    "description",
                    "description_zh",
                    "badge",
                    "badge_zh",
                ]:
                    if key in preset_data:
                        preset[key] = preset_data[key]
                preset_found = True
                break

        if not preset_found:
            raise ValueError(f"Preset not found: {preset_id}")

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(
                yaml.dump(
                    current_yaml,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
            )

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
        current_yaml["intro"]["presets"] = [
            p for p in presets if p.get("id") != preset_id
        ]

        if len(current_yaml["intro"]["presets"]) == original_len:
            raise ValueError(f"Preset not found: {preset_id}")

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(
                yaml.dump(
                    current_yaml,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
            )

        await self.reload_solution(solution_id)
        logger.info(f"Deleted preset '{preset_id}' from solution '{solution_id}'")

        return True

    async def add_preset_device(
        self, solution_id: str, preset_id: str, device_data: Dict[str, Any]
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
                        raise ValueError(
                            f"Device with ID '{device_data.get('id')}' already exists in preset"
                        )

                # Build device entry
                new_device = {
                    "id": device_data["id"],
                    "name": device_data["name"],
                    "name_zh": device_data.get("name_zh", device_data["name"]),
                    "type": device_data.get("type", "manual"),
                    "required": device_data.get("required", True),
                }

                # Add section if provided (supports both nested and flat formats)
                section_data = device_data.get("section", {})
                desc_file = section_data.get(
                    "description_file"
                ) or device_data.get("description_file")
                desc_file_zh = section_data.get(
                    "description_file_zh"
                ) or device_data.get("description_file_zh")

                if desc_file or desc_file_zh or section_data:
                    new_device["section"] = {
                        "title": section_data.get("title")
                        or device_data.get("section_title", device_data["name"]),
                        "title_zh": section_data.get("title_zh")
                        or device_data.get(
                            "section_title_zh",
                            device_data.get("name_zh", device_data["name"]),
                        ),
                        "description_file": desc_file,
                        "description_file_zh": desc_file_zh,
                    }

                preset["devices"].append(new_device)
                preset_found = True
                break

        if not preset_found:
            raise ValueError(f"Preset not found: {preset_id}")

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(
                yaml.dump(
                    current_yaml,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
            )

        await self.reload_solution(solution_id)
        logger.info(
            f"Added device '{device_data['id']}' to preset '{preset_id}' in solution '{solution_id}'"
        )

        return device_data

    async def update_preset_device(
        self,
        solution_id: str,
        preset_id: str,
        device_id: str,
        device_data: Dict[str, Any],
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
                        for key in [
                            "name",
                            "name_zh",
                            "type",
                            "required",
                            "config_file",
                        ]:
                            if key in device_data:
                                device[key] = device_data[key]

                        # Update section (supports both nested and flat formats)
                        section_data = device_data.get("section", {})
                        has_section_update = section_data or any(
                            k in device_data
                            for k in [
                                "description_file",
                                "description_file_zh",
                                "section_title",
                                "section_title_zh",
                            ]
                        )

                        if has_section_update:
                            if "section" not in device:
                                device["section"] = {}

                            # Handle nested section object
                            if section_data.get("description_file"):
                                device["section"]["description_file"] = section_data[
                                    "description_file"
                                ]
                            elif "description_file" in device_data:
                                device["section"]["description_file"] = device_data[
                                    "description_file"
                                ]

                            if section_data.get("description_file_zh"):
                                device["section"]["description_file_zh"] = section_data[
                                    "description_file_zh"
                                ]
                            elif "description_file_zh" in device_data:
                                device["section"]["description_file_zh"] = device_data[
                                    "description_file_zh"
                                ]

                            if section_data.get("title"):
                                device["section"]["title"] = section_data["title"]
                            elif "section_title" in device_data:
                                device["section"]["title"] = device_data["section_title"]

                            if section_data.get("title_zh"):
                                device["section"]["title_zh"] = section_data["title_zh"]
                            elif "section_title_zh" in device_data:
                                device["section"]["title_zh"] = device_data[
                                    "section_title_zh"
                                ]

                        device_found = True
                        break
                break

        if not device_found:
            raise ValueError(f"Device '{device_id}' not found in preset '{preset_id}'")

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(
                yaml.dump(
                    current_yaml,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
            )

        await self.reload_solution(solution_id)
        logger.info(
            f"Updated device '{device_id}' in preset '{preset_id}' in solution '{solution_id}'"
        )

        return device_data

    async def delete_preset_device(
        self, solution_id: str, preset_id: str, device_id: str
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
                preset["devices"] = [
                    d for d in preset.get("devices", []) if d.get("id") != device_id
                ]
                if len(preset["devices"]) < original_len:
                    device_found = True
                break

        if not device_found:
            raise ValueError(f"Device '{device_id}' not found in preset '{preset_id}'")

        async with aiofiles.open(yaml_path, "w") as f:
            await f.write(
                yaml.dump(
                    current_yaml,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
            )

        await self.reload_solution(solution_id)
        logger.info(
            f"Deleted device '{device_id}' from preset '{preset_id}' in solution '{solution_id}'"
        )

        return True

    async def update_solution_links(
        self, solution_id: str, links: Dict[str, str]
    ) -> Dict[str, str]:
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
            await f.write(
                yaml.dump(
                    current_yaml,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
            )

        await self.reload_solution(solution_id)
        return links

    async def update_solution_tags(
        self, solution_id: str, tags: List[str]
    ) -> List[str]:
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
            await f.write(
                yaml.dump(
                    current_yaml,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
            )

        await self.reload_solution(solution_id)
        return tags


    # ============================================
    # Content File Management (New Simplified API)
    # ============================================

    async def save_content_file(
        self, solution_id: str, filename: str, content: str
    ) -> str:
        """Save a core content file (guide.md, description.md, etc.).

        This is used by the simplified management UI to upload the 4 required files.

        Args:
            solution_id: The solution ID
            filename: One of guide.md, guide_zh.md, description.md, description_zh.md
            content: File content

        Returns:
            The saved file path
        """
        valid_files = [
            "guide.md", "guide_zh.md",
            "description.md", "description_zh.md"
        ]
        if filename not in valid_files:
            raise ValueError(f"Invalid filename: {filename}. Must be one of: {valid_files}")

        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        file_path = Path(solution.base_path) / filename

        # Write the file
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.info(f"Saved content file: {solution_id}/{filename}")

        # If it's a guide file, sync presets to YAML
        if filename.startswith("guide"):
            await self.sync_presets_from_guide(solution_id)

        return filename

    async def sync_presets_from_guide(self, solution_id: str) -> bool:
        """Sync preset metadata from guide.md to solution.yaml.

        This extracts preset IDs, names, and descriptions from guide.md
        and updates the intro.presets[] array in solution.yaml for use
        on the introduction page.

        Args:
            solution_id: The solution ID

        Returns:
            True if sync was successful
        """
        solution = self.get_solution(solution_id)
        if not solution or not solution.base_path:
            return False

        base_path = Path(solution.base_path)
        guide_en_path = solution.deployment.guide_file or "guide.md"
        guide_zh_path = solution.deployment.guide_file_zh or "guide_zh.md"

        en_file = base_path / guide_en_path
        zh_file = base_path / guide_zh_path

        if not en_file.exists():
            logger.warning(f"Cannot sync presets: {guide_en_path} not found")
            return False

        try:
            # Parse EN guide
            async with aiofiles.open(en_file, "r", encoding="utf-8") as f:
                en_content = await f.read()
            en_result = parse_single_language_guide(en_content)

            # Parse ZH guide if exists
            zh_result = None
            if zh_file.exists():
                async with aiofiles.open(zh_file, "r", encoding="utf-8") as f:
                    zh_content = await f.read()
                zh_result = parse_single_language_guide(zh_content)

            # Build presets array for YAML
            presets = []
            for en_preset in en_result.presets:
                zh_preset = None
                if zh_result:
                    zh_preset = next(
                        (p for p in zh_result.presets if p.id == en_preset.id), None
                    )

                preset_data = {
                    "id": en_preset.id,
                    "name": en_preset.name,
                    "name_zh": zh_preset.name if zh_preset else en_preset.name,
                    "description": en_preset.description or "",
                    "description_zh": zh_preset.description if zh_preset else "",
                }
                presets.append(preset_data)

            # Update solution.yaml
            yaml_path = base_path / "solution.yaml"
            async with aiofiles.open(yaml_path, "r", encoding="utf-8") as f:
                content = await f.read()
                current_yaml = yaml.safe_load(content)

            if "intro" not in current_yaml:
                current_yaml["intro"] = {}
            current_yaml["intro"]["presets"] = presets

            async with aiofiles.open(yaml_path, "w", encoding="utf-8") as f:
                await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False))

            # Reload solution
            await self.reload_solution(solution_id)
            logger.info(f"Synced {len(presets)} presets from guide.md to YAML for {solution_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to sync presets from guide: {e}")
            return False

    async def get_structure_preview(self, solution_id: str) -> Optional[Dict[str, Any]]:
        """Get a complete structure preview from guide.md for management UI.

        Returns the parsed structure including presets, steps, and post-deployment
        content, plus validation status.

        Args:
            solution_id: The solution ID

        Returns:
            Dict with presets, post_deployment, and validation info
        """
        solution = self.get_solution(solution_id)
        if not solution or not solution.base_path:
            return None

        base_path = Path(solution.base_path)
        guide_en_path = solution.deployment.guide_file or "guide.md"
        guide_zh_path = solution.deployment.guide_file_zh or "guide_zh.md"

        en_file = base_path / guide_en_path
        zh_file = base_path / guide_zh_path

        result = {
            "solution_id": solution_id,
            "presets": [],
            "post_deployment": None,
            "validation": {
                "valid": True,
                "errors": [],
                "warnings": [],
            },
            "content_files": {
                "guide_en": {
                    "path": guide_en_path,
                    "exists": en_file.exists(),
                    "size": en_file.stat().st_size if en_file.exists() else 0,
                },
                "guide_zh": {
                    "path": guide_zh_path,
                    "exists": zh_file.exists(),
                    "size": zh_file.stat().st_size if zh_file.exists() else 0,
                },
                "description_en": {
                    "path": solution.intro.description_file or "description.md",
                    "exists": (base_path / (solution.intro.description_file or "description.md")).exists(),
                },
                "description_zh": {
                    "path": solution.intro.description_file_zh or "description_zh.md",
                    "exists": (base_path / (solution.intro.description_file_zh or "description_zh.md")).exists(),
                },
            },
        }

        if not en_file.exists():
            result["validation"]["warnings"].append({
                "message": f"English guide not found: {guide_en_path}"
            })
            return result

        try:
            # Parse EN guide
            async with aiofiles.open(en_file, "r", encoding="utf-8") as f:
                en_content = await f.read()
            en_result = parse_single_language_guide(en_content)

            # Parse ZH guide if exists
            zh_result = None
            if zh_file.exists():
                async with aiofiles.open(zh_file, "r", encoding="utf-8") as f:
                    zh_content = await f.read()
                zh_result = parse_single_language_guide(zh_content)

            # Validate structure consistency
            if zh_result:
                validation = await self.validate_guide_pair(solution_id)
                if validation:
                    result["validation"]["valid"] = validation.valid
                    result["validation"]["errors"] = [
                        {
                            "type": str(e.error_type.value),
                            "message": e.message,
                            "suggestion": e.suggestion,
                        }
                        for e in validation.errors
                    ]
                    result["validation"]["warnings"] = [
                        {"message": w.message}
                        for w in validation.warnings
                    ]
            else:
                result["validation"]["warnings"].append({
                    "message": f"Chinese guide not found: {guide_zh_path}"
                })

            # Build presets structure
            for en_preset in en_result.presets:
                zh_preset = None
                if zh_result:
                    zh_preset = next(
                        (p for p in zh_result.presets if p.id == en_preset.id), None
                    )

                preset_data = {
                    "id": en_preset.id,
                    "name": en_preset.name,
                    "name_zh": zh_preset.name if zh_preset else en_preset.name,
                    "description": en_preset.description or "",
                    "description_zh": zh_preset.description if zh_preset else "",
                    "steps": [],
                }

                for en_step in en_preset.steps:
                    zh_step = None
                    if zh_preset:
                        zh_step = next(
                            (s for s in zh_preset.steps if s.id == en_step.id), None
                        )

                    step_data = {
                        "id": en_step.id,
                        "title": en_step.title_en,
                        "title_zh": zh_step.title_en if zh_step else en_step.title_en,
                        "type": en_step.type,
                        "required": en_step.required,
                        "config_file": en_step.config_file,
                        "has_targets": bool(en_step.targets),
                        "targets": [],
                    }

                    # Add targets info
                    if en_step.targets:
                        for target in en_step.targets:
                            step_data["targets"].append({
                                "id": target.id,
                                "name": target.name,
                                "default": target.default,
                            })

                    preset_data["steps"].append(step_data)

                result["presets"].append(preset_data)

            # Build post_deployment info
            if en_result.success:
                result["post_deployment"] = {
                    "content_en": en_result.success.content_en,
                    "content_zh": zh_result.success.content_en if zh_result and zh_result.success else None,
                }

        except Exception as e:
            logger.error(f"Failed to get structure preview: {e}")
            result["validation"]["errors"].append({
                "type": "parse_error",
                "message": str(e),
            })

        return result

    def get_device_catalog_list(self) -> List[Dict[str, Any]]:
        """Get device catalog as a list for dropdown selectors.

        Returns:
            List of device info dicts with id, name, name_zh, category, image, product_url
        """
        result = []
        for device_id, device in self._global_device_catalog.items():
            result.append({
                "id": device_id,
                "name": device.get("name", device_id),
                "name_zh": device.get("name_zh", device.get("name", device_id)),
                "category": device.get("category"),
                "image": device.get("image"),
                "product_url": device.get("product_url"),
                "description": device.get("description"),
                "description_zh": device.get("description_zh"),
            })
        return result

    async def update_required_devices(
        self, solution_id: str, device_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Update the required_devices list for a solution from catalog IDs.

        Args:
            solution_id: The solution ID
            device_ids: List of device IDs from the catalog

        Returns:
            List of updated required_devices
        """
        solution = self.get_solution(solution_id)
        if not solution:
            raise ValueError(f"Solution not found: {solution_id}")

        yaml_path = Path(solution.base_path) / "solution.yaml"

        # Read current yaml
        async with aiofiles.open(yaml_path, "r", encoding="utf-8") as f:
            content = await f.read()
            current_yaml = yaml.safe_load(content)

        if "intro" not in current_yaml:
            current_yaml["intro"] = {}

        # Build required_devices from catalog
        required_devices = []
        for device_id in device_ids:
            device_info = self._global_device_catalog.get(device_id)
            if device_info:
                required_devices.append({
                    "id": device_id,
                    "name": device_info.get("name", device_id),
                    "name_zh": device_info.get("name_zh", device_info.get("name", device_id)),
                })
            else:
                # Device not in catalog, just use the ID
                required_devices.append({
                    "id": device_id,
                    "name": device_id,
                    "name_zh": device_id,
                })

        current_yaml["intro"]["required_devices"] = required_devices

        # Write back
        async with aiofiles.open(yaml_path, "w", encoding="utf-8") as f:
            await f.write(yaml.dump(current_yaml, allow_unicode=True, sort_keys=False))

        # Reload solution
        await self.reload_solution(solution_id)
        logger.info(f"Updated required_devices for {solution_id}: {device_ids}")

        return required_devices


# Global instance
solution_manager = SolutionManager()
