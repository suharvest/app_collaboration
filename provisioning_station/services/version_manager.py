"""
Version management service
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any

from ..models.version import VersionInfo, UpdateCheckResult, VersionSummary
from .solution_manager import solution_manager
from .deployment_history import deployment_history

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages version information for deployed solutions"""

    async def get_solution_versions(self, solution_id: str) -> Optional[VersionSummary]:
        """Get version information for all devices in a solution"""
        solution = solution_manager.get_solution(solution_id)
        if not solution:
            return None

        devices: List[VersionInfo] = []

        for device_ref in solution.deployment.devices:
            try:
                config = await solution_manager.load_device_config(
                    solution_id, device_ref.config_file
                )
                if not config:
                    continue

                version_info = await self._get_device_version(
                    solution_id, device_ref.id, config.type, config
                )
                devices.append(version_info)

            except Exception as e:
                logger.error(f"Error getting version for {device_ref.id}: {e}")
                continue

        stats = await deployment_history.get_solution_stats(solution_id)

        # Get solution version from solution object
        solution_version = "1.0.0"  # Default
        if hasattr(solution, "version"):
            solution_version = solution.version

        return VersionSummary(
            solution_id=solution_id,
            solution_version=solution_version,
            devices=devices,
            last_deployment=stats.get("last_deployment"),
        )

    async def _get_device_version(
        self,
        solution_id: str,
        device_id: str,
        device_type: str,
        config,
    ) -> VersionInfo:
        """Get version information for a specific device"""
        # Get config version from the configuration
        config_version = config.version if hasattr(config, "version") else "1.0"

        # Get last deployed version from history
        last_deployed_version = await deployment_history.get_last_deployed_version(
            solution_id, device_id
        )

        # Get history to find last deployment time
        history = await deployment_history.get_history(
            solution_id=solution_id,
            device_id=device_id,
            limit=1,
        )
        last_deployed = history[0].deployed_at if history else None

        # Get deployed version for Docker type
        deployed_version = None
        if device_type == "docker_local" and config.docker:
            deployed_version = await self.detect_docker_version(
                config.docker, solution_id
            )

        # Determine if update is available
        update_available = False
        if deployed_version and last_deployed_version:
            update_available = deployed_version != last_deployed_version

        return VersionInfo(
            device_id=device_id,
            device_type=device_type,
            config_version=config_version,
            deployed_version=deployed_version,
            available_version=config_version,
            last_deployed=last_deployed,
            update_available=update_available,
        )

    async def detect_docker_version(
        self,
        docker_config,
        solution_id: str,
    ) -> Optional[str]:
        """Detect version of running Docker containers"""
        try:
            import docker as docker_lib

            client = docker_lib.from_env()

            # Get project name from options or use solution_id
            project_name = docker_config.options.get("project_name", solution_id)

            # List containers with the project label
            containers = client.containers.list(
                filters={"label": f"com.docker.compose.project={project_name}"}
            )

            if not containers:
                return None

            # Try to get version from labels
            for container in containers:
                labels = container.labels
                if "com.seeedstudio.version" in labels:
                    return labels["com.seeedstudio.version"]

            # Try to get version from image tag
            for container in containers:
                image_tags = container.image.tags
                if image_tags:
                    for tag in image_tags:
                        # Extract version from tag like "image:v1.0.0"
                        if ":" in tag:
                            version = tag.split(":")[-1]
                            if version != "latest":
                                return version

            return "latest"

        except ImportError:
            logger.warning("docker package not installed")
            return None
        except Exception as e:
            logger.error(f"Error detecting Docker version: {e}")
            return None

    async def check_update_available(
        self,
        solution_id: str,
        device_id: str,
    ) -> Optional[UpdateCheckResult]:
        """Check if an update is available for a device"""
        solution = solution_manager.get_solution(solution_id)
        if not solution:
            return None

        device_ref = next(
            (d for d in solution.deployment.devices if d.id == device_id),
            None,
        )
        if not device_ref:
            return None

        config = await solution_manager.load_device_config(
            solution_id, device_ref.config_file
        )
        if not config:
            return None

        # Get current deployed version
        current_version = await deployment_history.get_last_deployed_version(
            solution_id, device_id
        )

        # Get target version from config
        target_version = config.version if hasattr(config, "version") else "1.0"

        # Determine update type based on device type
        update_type_map = {
            "docker_local": "pull_image",
            "esp32_usb": "reflash",
            "ssh_deb": "reinstall",
            "script": "rerun",
            "manual": "manual",
        }
        update_type = update_type_map.get(config.type, "unknown")

        # Check if update is available
        update_available = current_version != target_version if current_version else True

        return UpdateCheckResult(
            device_id=device_id,
            current_version=current_version,
            target_version=target_version,
            update_available=update_available,
            update_type=update_type,
        )

    async def check_all_updates(
        self,
        solution_id: str,
    ) -> List[UpdateCheckResult]:
        """Check for updates on all devices in a solution"""
        solution = solution_manager.get_solution(solution_id)
        if not solution:
            return []

        results = []
        for device_ref in solution.deployment.devices:
            result = await self.check_update_available(solution_id, device_ref.id)
            if result:
                results.append(result)

        return results

    async def get_running_versions(self, project_name: str) -> Dict[str, str]:
        """Get versions of all running containers in a project"""
        try:
            import docker as docker_lib

            client = docker_lib.from_env()
            containers = client.containers.list(
                filters={"label": f"com.docker.compose.project={project_name}"}
            )

            versions = {}
            for container in containers:
                service_name = container.labels.get("com.docker.compose.service", "unknown")

                # Try to get version from labels
                version = container.labels.get("com.seeedstudio.version")

                if not version:
                    # Try to get from image tag
                    image_tags = container.image.tags
                    if image_tags:
                        for tag in image_tags:
                            if ":" in tag:
                                version = tag.split(":")[-1]
                                if version != "latest":
                                    break

                versions[service_name] = version or "unknown"

            return versions

        except Exception as e:
            logger.error(f"Error getting running versions: {e}")
            return {}


# Global instance
version_manager = VersionManager()
