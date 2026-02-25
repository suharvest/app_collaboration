"""
Docker deployment deployer

NOTE: Local Docker deployment is only supported on Linux and macOS.
Windows is not supported as deployment target.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from ..models.device import DeviceConfig
from ..utils.compose_labels import create_labels, inject_labels_to_compose_file
from .action_executor import LocalActionExecutor
from .base import BaseDeployer
from .docker_remote_deployer import RemoteDockerNotInstalled

logger = logging.getLogger(__name__)


class DockerDeployer(BaseDeployer):
    """Docker compose deployment"""

    device_type = "docker_local"
    ui_traits = {
        "connection": "none",
        "auto_deploy": True,
        "renderer": None,
        "has_targets": False,
        "show_model_selection": False,
        "show_service_warning": False,
        "connection_scope": "device",
    }
    steps = [
        {
            "id": "actions_before",
            "name": "Custom Setup",
            "name_zh": "自定义准备",
            "_condition": "actions.before",
        },
        {
            "id": "pull_images",
            "name": "Pull Docker Images",
            "name_zh": "拉取 Docker 镜像",
        },
        {
            "id": "create_volumes",
            "name": "Create Data Volumes",
            "name_zh": "创建数据卷",
        },
        {"id": "start_services", "name": "Start Services", "name_zh": "启动服务"},
        {"id": "health_check", "name": "Health Check", "name_zh": "健康检查"},
        {
            "id": "actions_after",
            "name": "Custom Config",
            "name_zh": "自定义配置",
            "_condition": "actions.after",
        },
    ]

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        # Platform check - local Docker deployment not supported on Windows
        if sys.platform == "win32":
            await self._report_progress(
                progress_callback,
                "check_os",
                0,
                "Local Docker deployment is not supported on Windows. "
                "Please use a Linux or macOS host, or deploy to a remote Linux device.",
            )
            return False

        # Check if Docker is available locally
        auto_install = connection.get("auto_install_docker", False)
        docker_ready = await self._ensure_docker_available(
            auto_install, progress_callback
        )
        if not docker_ready:
            return False

        if not config.docker:
            raise ValueError("No Docker configuration")

        docker_config = config.docker

        # Track temp file for cleanup
        temp_compose_file = None

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

            # Inject SenseCraft labels for container tracking
            solution_id = connection.get("_solution_id")
            solution_name = connection.get("_solution_name")
            device_id = connection.get("_device_id")

            if solution_id and device_id:
                config_file_label = connection.get("_config_file")
                labels = create_labels(
                    solution_id=solution_id,
                    device_id=device_id,
                    solution_name=solution_name,
                    config_file=config_file_label,
                )
                temp_compose_file = inject_labels_to_compose_file(compose_file, labels)
                compose_file = temp_compose_file
                logger.info("Injected SenseCraft labels into compose file")

            # Check for existing containers that would conflict
            auto_replace = connection.get("auto_replace_containers", False)
            await self._check_existing_containers(
                compose_file,
                project_name,
                str(compose_dir),
                auto_replace,
                progress_callback,
            )

            # Before actions
            executor = LocalActionExecutor()
            if not await self._execute_actions(
                "before", config, connection, progress_callback, executor
            ):
                return False

            # Step 1: Pull images
            await self._report_progress(
                progress_callback, "pull_images", 0, "Pulling Docker images..."
            )

            pull_result = await self._run_docker_compose(
                compose_file,
                ["pull"],
                project_name,
                progress_callback=lambda msg: (
                    asyncio.create_task(
                        self._report_progress(progress_callback, "pull_images", 50, msg)
                    )
                    if progress_callback
                    else None
                ),
                working_dir=str(compose_dir),
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

            # Build environment with template substitution
            from ..utils.template import substitute

            env = {}
            for k, v in docker_config.environment.items():
                env[k] = substitute(str(v), connection) or ""

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
                progress_callback=lambda msg: (
                    asyncio.create_task(
                        self._report_progress(
                            progress_callback, "start_services", 50, msg
                        )
                    )
                    if progress_callback
                    else None
                ),
                working_dir=str(compose_dir),
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
                        timeout=service.health_check_timeout,
                        progress_callback=progress_callback,
                        container_name=service.name,
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

            # After actions
            if not await self._execute_actions(
                "after", config, connection, progress_callback, executor
            ):
                return False

            # Open browser if configured
            if config.post_deployment.open_browser and config.post_deployment.url:
                try:
                    import webbrowser

                    webbrowser.open(config.post_deployment.url)
                except Exception as e:
                    logger.warning(f"Failed to open browser: {e}")

            return True

        except RemoteDockerNotInstalled:
            raise  # Let deployment engine handle Docker installation dialog

        except Exception as e:
            logger.error(f"Docker deployment failed: {e}")
            await self._report_progress(
                progress_callback, "start_services", 0, f"Deployment failed: {str(e)}"
            )
            return False

        finally:
            # Clean up temporary compose file
            if temp_compose_file and Path(temp_compose_file).exists():
                try:
                    os.remove(temp_compose_file)
                    logger.debug(f"Cleaned up temp compose file: {temp_compose_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")

    async def _ensure_docker_available(
        self,
        auto_install: bool,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Check if Docker is available locally, optionally install on Linux"""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            if process.returncode == 0:
                logger.info(f"Docker found: {stdout.decode().strip()}")
                return True
        except FileNotFoundError:
            pass

        # Docker not found
        if sys.platform == "linux":
            if auto_install:
                return await self._install_docker_locally(progress_callback)
            else:
                raise RemoteDockerNotInstalled(
                    "Docker is not installed on this machine. "
                    "Would you like to install it automatically?",
                    can_auto_fix=True,
                    fix_action="install_docker",
                )
        else:
            # macOS/Windows - manual install only
            await self._report_progress(
                progress_callback,
                "pull_images",
                0,
                "Docker is not installed. "
                "Please install Docker Desktop from https://www.docker.com/products/docker-desktop/",
            )
            return False

    async def _install_docker_locally(
        self,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Install Docker on local Linux machine"""
        try:
            await self._report_progress(
                progress_callback, "pull_images", 0, "Installing Docker..."
            )

            # Detect if Debian-based
            is_debian = False
            try:
                process = await asyncio.create_subprocess_exec(
                    "cat",
                    "/etc/os-release",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await process.communicate()
                os_info = stdout.decode().lower()
                is_debian = any(
                    d in os_info for d in ("debian", "ubuntu", "raspbian", "linuxmint")
                )
            except Exception:
                pass

            if is_debian:
                script = (
                    "set -e && "
                    "sudo apt-get update && "
                    "sudo apt-get install -y ca-certificates curl gnupg && "
                    "sudo install -m 0755 -d /etc/apt/keyrings && "
                    'curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | sudo gpg --batch --yes --dearmor -o /etc/apt/keyrings/docker.gpg && '
                    "sudo chmod a+r /etc/apt/keyrings/docker.gpg && "
                    'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null && '
                    "sudo apt-get update && "
                    "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && "
                    "sudo usermod -aG docker $USER && "
                    "sudo systemctl enable docker && "
                    "sudo systemctl start docker"
                )
            else:
                script = (
                    "set -e && "
                    "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && "
                    "sudo sh /tmp/get-docker.sh && "
                    "sudo usermod -aG docker $USER && "
                    "rm -f /tmp/get-docker.sh && "
                    "sudo systemctl enable docker 2>/dev/null || true && "
                    "sudo systemctl start docker 2>/dev/null || sudo service docker start || true"
                )

            await self._report_progress(
                progress_callback,
                "pull_images",
                10,
                "Running Docker installation script...",
            )

            process = await asyncio.create_subprocess_exec(
                "bash",
                "-c",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            output_lines = []
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line_str = line.decode().strip()
                output_lines.append(line_str)
                if progress_callback and line_str:
                    await self._report_progress(
                        progress_callback, "pull_images", 50, line_str
                    )

            await process.wait()

            if process.returncode != 0:
                error_msg = "\n".join(output_lines[-5:])
                await self._report_progress(
                    progress_callback,
                    "pull_images",
                    0,
                    f"Docker installation failed: {error_msg}",
                )
                return False

            await self._report_progress(
                progress_callback, "pull_images", 80, "Docker installed successfully"
            )
            return True

        except Exception as e:
            logger.error(f"Docker installation failed: {e}")
            await self._report_progress(
                progress_callback,
                "pull_images",
                0,
                f"Docker installation failed: {str(e)}",
            )
            return False

    async def _run_docker_compose(
        self,
        compose_file: str,
        args: list,
        project_name: str = None,
        env: Dict[str, str] = None,
        progress_callback: Optional[Callable] = None,
        working_dir: str = None,
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

            # Use provided working_dir or fall back to compose file's directory
            cwd = working_dir or str(Path(compose_file).parent)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=full_env,
                cwd=cwd,
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

            await process.wait()

            return {
                "success": process.returncode == 0,
                "output": "\n".join(output_lines),
                "error": "\n".join(output_lines) if process.returncode != 0 else None,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_compose_container_names(self, compose_file: str) -> List[str]:
        """Extract container_name values from compose file"""
        try:
            with open(compose_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not data or "services" not in data:
                return []
            names = []
            for service_config in data.get("services", {}).values():
                if service_config and "container_name" in service_config:
                    names.append(service_config["container_name"])
            return names
        except Exception as e:
            logger.debug(f"Failed to parse compose file for container names: {e}")
            return []

    async def _check_existing_containers(
        self,
        compose_file: str,
        project_name: str,
        working_dir: str,
        auto_replace: bool,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """Check for existing containers that would conflict with deployment.

        If conflicting containers are found and auto_replace is False, raises
        RemoteDockerNotInstalled to trigger a user confirmation dialog.
        If auto_replace is True, stops and removes the existing containers.
        """
        container_names = self._get_compose_container_names(compose_file)
        if not container_names:
            return  # No explicit container_name, compose handles it

        # Check which container names already exist
        existing = []
        for name in container_names:
            try:
                process = await asyncio.create_subprocess_exec(
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name=^/{name}$",
                    "--format",
                    "{{.Names}} ({{.Image}}) - {{.Status}}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await process.communicate()
                output = stdout.decode().strip()
                if output:
                    existing.append(output)
            except Exception:
                pass

        if not existing:
            return  # No conflicts

        if auto_replace:
            await self._report_progress(
                progress_callback,
                "pull_images",
                0,
                "Stopping existing containers...",
            )

            # Run docker compose down for this project
            await self._run_docker_compose(
                compose_file,
                ["down", "--remove-orphans"],
                project_name,
                working_dir=working_dir,
            )

            # Force remove any remaining containers with conflicting names
            # (handles cross-project conflicts)
            for name in container_names:
                try:
                    await asyncio.create_subprocess_exec(
                        "docker",
                        "rm",
                        "-f",
                        name,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                except Exception:
                    pass

            await self._report_progress(
                progress_callback,
                "pull_images",
                0,
                "Existing containers removed",
            )
        else:
            container_list = ", ".join(
                name for name in container_names if any(name in e for e in existing)
            )
            raise RemoteDockerNotInstalled(
                f"Found existing containers: {container_list}. "
                "Would you like to stop and replace them with the new deployment?",
                can_auto_fix=True,
                fix_action="replace_containers",
            )

    async def _check_service_health(
        self,
        port: int,
        endpoint: str,
        timeout: int = 60,
        progress_callback=None,
        container_name: str = None,
    ) -> bool:
        """Check if a service is healthy.

        First tries HTTP health check. If that times out and a container_name
        is provided, falls back to checking Docker's own container health status.
        """
        import httpx

        url = f"http://localhost:{port}{endpoint}"
        start_time = asyncio.get_event_loop().time()
        attempt = 0

        while asyncio.get_event_loop().time() - start_time < timeout:
            attempt += 1
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=5)
                    if response.status_code < 500:
                        return True
            except Exception as e:
                if progress_callback:
                    elapsed = int(asyncio.get_event_loop().time() - start_time)
                    await self._report_progress(
                        progress_callback,
                        "health_check",
                        min(50, elapsed * 100 // timeout),
                        f"Waiting for service (attempt {attempt}, {elapsed}s/{timeout}s)...",
                    )
                logger.debug(f"Health check attempt {attempt} failed: {e}")

            await asyncio.sleep(2)

        # HTTP check timed out — fallback to Docker's own health status
        if container_name:
            docker_healthy = await self._check_docker_container_health(container_name)
            if docker_healthy:
                logger.info(
                    f"HTTP health check timed out but Docker reports {container_name} as healthy"
                )
                return True

        return False

    async def _check_docker_container_health(self, container_name: str) -> bool:
        """Check Docker's own container health status as fallback.

        Returns True if the container is running (and healthy if healthcheck defined).
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "docker",
                "inspect",
                "--format",
                "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
                container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            if process.returncode != 0:
                return False

            output = stdout.decode().strip()
            parts = output.split("|")
            state_status = parts[0] if parts else ""
            health_status = parts[1] if len(parts) > 1 else "none"

            # Container must be running
            if state_status != "running":
                return False

            # If no healthcheck defined, running is good enough
            if health_status == "none":
                return True

            # If healthcheck defined, it must be healthy
            return health_status == "healthy"

        except Exception as e:
            logger.debug(f"Docker health check fallback failed: {e}")
            return False
