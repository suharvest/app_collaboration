"""
Docker deployment deployer
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional, Dict, Any

from .base import BaseDeployer
from ..models.device import DeviceConfig

logger = logging.getLogger(__name__)


class DockerDeployer(BaseDeployer):
    """Docker compose deployment"""

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        if not config.docker:
            raise ValueError("No Docker configuration")

        docker_config = config.docker

        try:
            # Get compose file path
            compose_file = config.get_asset_path(docker_config.compose_file)
            if not compose_file or not Path(compose_file).exists():
                await self._report_progress(
                    progress_callback,
                    "pull_images",
                    0,
                    f"Compose file not found: {docker_config.compose_file}",
                )
                return False

            compose_dir = Path(compose_file).parent
            project_name = docker_config.options.get("project_name", "provisioning")

            # Step 1: Pull images
            await self._report_progress(
                progress_callback, "pull_images", 0, "Pulling Docker images..."
            )

            pull_result = await self._run_docker_compose(
                compose_file,
                ["pull"],
                project_name,
                progress_callback=lambda msg: asyncio.create_task(
                    self._report_progress(progress_callback, "pull_images", 50, msg)
                )
                if progress_callback
                else None,
            )

            if not pull_result["success"]:
                await self._report_progress(
                    progress_callback,
                    "pull_images",
                    0,
                    f"Pull failed: {pull_result.get('error', 'Unknown error')}",
                )
                return False

            await self._report_progress(
                progress_callback, "pull_images", 100, "Images pulled successfully"
            )

            # Step 2: Create volumes
            await self._report_progress(
                progress_callback, "create_volumes", 0, "Setting up volumes..."
            )

            # Volumes are typically created automatically by docker-compose
            await self._report_progress(
                progress_callback, "create_volumes", 100, "Volumes ready"
            )

            # Step 3: Start services
            await self._report_progress(
                progress_callback, "start_services", 0, "Starting services..."
            )

            # Build environment
            env = docker_config.environment.copy()

            up_args = ["up", "-d"]
            if docker_config.options.get("remove_orphans", False):
                up_args.append("--remove-orphans")
            if docker_config.options.get("build", False):
                up_args.append("--build")

            up_result = await self._run_docker_compose(
                compose_file,
                up_args,
                project_name,
                env=env,
                progress_callback=lambda msg: asyncio.create_task(
                    self._report_progress(progress_callback, "start_services", 50, msg)
                )
                if progress_callback
                else None,
            )

            if not up_result["success"]:
                await self._report_progress(
                    progress_callback,
                    "start_services",
                    0,
                    f"Start failed: {up_result.get('error', 'Unknown error')}",
                )
                return False

            await self._report_progress(
                progress_callback, "start_services", 100, "Services started"
            )

            # Step 4: Health check
            await self._report_progress(
                progress_callback, "health_check", 0, "Checking service health..."
            )

            all_healthy = True
            for service in docker_config.services:
                if service.health_check_endpoint:
                    healthy = await self._check_service_health(
                        service.port,
                        service.health_check_endpoint,
                        timeout=30,
                    )
                    if not healthy and service.required:
                        all_healthy = False
                        await self._report_progress(
                            progress_callback,
                            "health_check",
                            0,
                            f"Service {service.name} is not healthy",
                        )
                        break
                    elif healthy:
                        await self._report_progress(
                            progress_callback,
                            "health_check",
                            50,
                            f"Service {service.name} is healthy",
                        )

            if not all_healthy:
                return False

            await self._report_progress(
                progress_callback, "health_check", 100, "All services healthy"
            )

            # Open browser if configured
            if config.post_deployment.open_browser and config.post_deployment.url:
                try:
                    import webbrowser
                    webbrowser.open(config.post_deployment.url)
                except Exception as e:
                    logger.warning(f"Failed to open browser: {e}")

            return True

        except Exception as e:
            logger.error(f"Docker deployment failed: {e}")
            await self._report_progress(
                progress_callback, "start_services", 0, f"Deployment failed: {str(e)}"
            )
            return False

    async def _run_docker_compose(
        self,
        compose_file: str,
        args: list,
        project_name: str = None,
        env: Dict[str, str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """Run docker compose command"""
        try:
            cmd = ["docker", "compose", "-f", compose_file]
            if project_name:
                cmd.extend(["-p", project_name])
            cmd.extend(args)

            # Build environment
            import os
            full_env = os.environ.copy()
            if env:
                full_env.update(env)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=full_env,
                cwd=str(Path(compose_file).parent),
            )

            output_lines = []
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode().strip()
                output_lines.append(line_str)

                if progress_callback and line_str:
                    progress_callback(line_str)

                logger.debug(f"docker-compose: {line_str}")

            await process.wait()

            return {
                "success": process.returncode == 0,
                "output": "\n".join(output_lines),
                "error": "\n".join(output_lines) if process.returncode != 0 else None,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _check_service_health(
        self, port: int, endpoint: str, timeout: int = 30
    ) -> bool:
        """Check if a service is healthy"""
        import httpx

        url = f"http://localhost:{port}{endpoint}"
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=5)
                    if response.status_code < 500:
                        return True
            except Exception:
                pass

            await asyncio.sleep(2)

        return False
