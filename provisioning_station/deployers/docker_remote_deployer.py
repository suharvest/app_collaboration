"""
Remote Docker Compose deployment via SSH
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional, Dict, Any

from .base import BaseDeployer
from ..models.device import DeviceConfig, SSHConfig
from ..services.remote_pre_check import remote_pre_check

logger = logging.getLogger(__name__)


class RemoteDockerNotInstalled(Exception):
    """Raised when Docker is not installed on remote device"""
    def __init__(self, message: str, can_auto_fix: bool = False, fix_action: str = None):
        super().__init__(message)
        self.can_auto_fix = can_auto_fix
        self.fix_action = fix_action


class DockerRemoteDeployer(BaseDeployer):
    """Deploy Docker Compose applications to remote devices via SSH"""

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        if not config.docker_remote:
            raise ValueError("No docker_remote configuration")

        docker_config = config.docker_remote
        ssh_config = config.ssh or SSHConfig()

        host = connection.get("host")
        port = connection.get("port", ssh_config.port)
        username = connection.get("username", ssh_config.default_user)
        password = connection.get("password")
        key_file = connection.get("key_file")

        if not host:
            raise ValueError("No host specified for remote Docker deployment")

        # Build substitution context from connection + user_inputs defaults
        self._subst_context = {
            "host": host,
            "port": port,
            "username": username,
        }
        # Add defaults from user_inputs config
        if config.user_inputs:
            for user_input in config.user_inputs:
                if user_input.id not in self._subst_context:
                    # Use value from connection if provided, otherwise use default
                    self._subst_context[user_input.id] = connection.get(
                        user_input.id, user_input.default or ""
                    )

        try:
            import paramiko
            from scp import SCPClient

            # Step 1: SSH Connect
            await self._report_progress(
                progress_callback, "connect", 0, f"Connecting to {host}..."
            )

            client = await asyncio.to_thread(
                self._create_ssh_connection,
                host, port, username, password, key_file,
                ssh_config.connection_timeout
            )

            if not client:
                await self._report_progress(
                    progress_callback, "connect", 0, "Connection failed"
                )
                return False

            await self._report_progress(
                progress_callback, "connect", 100, "Connected successfully"
            )

            try:
                # Step 2: Check Docker on remote device
                auto_install_docker = connection.get("auto_install_docker", False)

                await self._report_progress(
                    progress_callback, "check_docker", 0, "Checking Docker on remote device..."
                )

                docker_check = await remote_pre_check.check_docker(client)

                if not docker_check.passed:
                    if docker_check.can_auto_fix and auto_install_docker:
                        # User confirmed auto-install
                        await self._report_progress(
                            progress_callback, "check_docker", 20, "Docker not found. Installing..."
                        )

                        if docker_check.fix_action == "install_docker":
                            success = await remote_pre_check.install_docker(
                                client, progress_callback
                            )
                            if not success:
                                await self._report_progress(
                                    progress_callback, "check_docker", 0, "Docker installation failed"
                                )
                                return False
                        elif docker_check.fix_action == "fix_docker_permission":
                            success = await remote_pre_check.fix_docker_permission(
                                client, username, progress_callback
                            )
                            if not success:
                                return False
                        elif docker_check.fix_action == "start_docker":
                            success = await remote_pre_check.start_docker_service(
                                client, progress_callback
                            )
                            if not success:
                                return False

                        await self._report_progress(
                            progress_callback, "check_docker", 100, "Docker ready"
                        )
                    else:
                        # Docker not installed and no auto-install permission
                        raise RemoteDockerNotInstalled(
                            docker_check.message,
                            can_auto_fix=docker_check.can_auto_fix,
                            fix_action=docker_check.fix_action,
                        )
                else:
                    await self._report_progress(
                        progress_callback, "check_docker", 100, docker_check.message
                    )

                # Step 3: Prepare remote directory
                await self._report_progress(
                    progress_callback, "prepare", 0, "Creating remote directory..."
                )

                # Substitute template variables in remote_path
                remote_path = self._substitute_variables(
                    docker_config.remote_path,
                    self._subst_context
                )
                remote_dir = f"{remote_path}/{config.id}"

                exit_code, _, stderr = await asyncio.to_thread(
                    self._exec_with_timeout,
                    client,
                    f"mkdir -p {remote_dir}",
                    30
                )

                if exit_code != 0:
                    await self._report_progress(
                        progress_callback, "prepare", 0, f"Failed to create directory: {stderr[:200]}"
                    )
                    return False

                await self._report_progress(
                    progress_callback, "prepare", 100, f"Directory ready: {remote_dir}"
                )

                # Step 3: Upload compose files
                await self._report_progress(
                    progress_callback, "upload", 0, "Uploading files..."
                )

                success = await self._upload_compose_files(
                    client, config, docker_config, remote_dir, progress_callback
                )

                if not success:
                    await self._report_progress(
                        progress_callback, "upload", 0, "File upload failed"
                    )
                    return False

                await self._report_progress(
                    progress_callback, "upload", 100, "Files uploaded"
                )

                # Step 4: Docker compose pull
                await self._report_progress(
                    progress_callback, "pull_images", 0, "Pulling images..."
                )

                exit_code, stdout, stderr = await asyncio.to_thread(
                    self._exec_with_timeout,
                    client,
                    f"cd {remote_dir} && docker compose pull",
                    ssh_config.command_timeout
                )

                if exit_code != 0:
                    await self._report_progress(
                        progress_callback, "pull_images", 0, f"Pull failed: {stderr[:200]}"
                    )
                    return False

                await self._report_progress(
                    progress_callback, "pull_images", 100, "Images pulled"
                )

                # Step 5: Docker compose up
                await self._report_progress(
                    progress_callback, "start_services", 0, "Starting services..."
                )

                project_name = docker_config.options.get("project_name", config.id)
                # Substitute template variables in environment values
                # Quote values properly to handle spaces and special characters
                env_items = []
                for k, v in docker_config.environment.items():
                    substituted_value = self._substitute_variables(
                        str(v), self._subst_context
                    )
                    # Escape single quotes in value and wrap in single quotes
                    escaped_value = substituted_value.replace("'", "'\\''")
                    env_items.append(f"{k}='{escaped_value}'")
                env_vars = " ".join(env_items)
                env_prefix = f"env {env_vars} " if env_vars else ""

                compose_cmd = f"cd {remote_dir} && {env_prefix}docker compose -p {project_name} up -d"

                if docker_config.options.get("remove_orphans"):
                    compose_cmd += " --remove-orphans"

                exit_code, stdout, stderr = await asyncio.to_thread(
                    self._exec_with_timeout,
                    client,
                    compose_cmd,
                    ssh_config.command_timeout
                )

                if exit_code != 0:
                    await self._report_progress(
                        progress_callback, "start_services", 0, f"Start failed: {stderr[:200]}"
                    )
                    return False

                await self._report_progress(
                    progress_callback, "start_services", 100, "Services started"
                )

                # Step 6: Health check
                await self._report_progress(
                    progress_callback, "health_check", 0, "Checking services..."
                )

                if docker_config.services:
                    all_healthy = True
                    for service in docker_config.services:
                        if service.health_check_endpoint:
                            healthy = await self._check_remote_service_health(
                                host,
                                service.port,
                                service.health_check_endpoint,
                                timeout=30
                            )
                            if not healthy:
                                if service.required:
                                    await self._report_progress(
                                        progress_callback, "health_check", 0,
                                        f"Service {service.name} is not healthy"
                                    )
                                    all_healthy = False
                                    break
                                else:
                                    logger.warning(f"Optional service {service.name} is not healthy")

                    if not all_healthy:
                        return False

                await self._report_progress(
                    progress_callback, "health_check", 100, "All services healthy"
                )

                return True

            finally:
                client.close()

        except ImportError as e:
            await self._report_progress(
                progress_callback,
                "connect",
                0,
                f"Missing dependency: {str(e)}",
            )
            return False

        except Exception as e:
            logger.error(f"Docker remote deployment failed: {e}")
            await self._report_progress(
                progress_callback, "start_services", 0, f"Deployment failed: {str(e)}"
            )
            return False

    async def _upload_compose_files(
        self,
        client,
        config: DeviceConfig,
        docker_config,
        remote_dir: str,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Upload compose files and related resources to remote"""
        try:
            from scp import SCPClient

            # Get compose file path
            compose_path = config.get_asset_path(docker_config.compose_file)
            if not compose_path or not Path(compose_path).exists():
                logger.error(f"Compose file not found: {docker_config.compose_file}")
                return False

            # If compose_dir is specified, upload entire directory
            if docker_config.compose_dir:
                compose_dir_path = config.get_asset_path(docker_config.compose_dir)
                if compose_dir_path and Path(compose_dir_path).exists():
                    await self._report_progress(
                        progress_callback, "upload", 25,
                        f"Uploading directory: {docker_config.compose_dir}"
                    )

                    # Upload contents of directory (not the directory itself)
                    success = await asyncio.to_thread(
                        self._transfer_directory_contents,
                        client, compose_dir_path, remote_dir
                    )

                    if not success:
                        return False
                else:
                    logger.error(f"Compose directory not found: {docker_config.compose_dir}")
                    return False
            else:
                # Upload just the compose file
                await self._report_progress(
                    progress_callback, "upload", 50,
                    f"Uploading: {docker_config.compose_file}"
                )

                remote_compose_path = f"{remote_dir}/docker-compose.yml"
                success = await asyncio.to_thread(
                    self._transfer_file,
                    client, compose_path, remote_compose_path
                )

                if not success:
                    return False

            return True

        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return False

    def _create_ssh_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str],
        key_file: Optional[str],
        timeout: int,
    ):
        """Create SSH connection (blocking, run in thread)"""
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            if key_file:
                client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    key_filename=key_file,
                    timeout=timeout,
                )
            else:
                client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=timeout,
                )
            return client
        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            return None

    def _transfer_file(self, client, local_path: str, remote_path: str) -> bool:
        """Transfer file via SCP (blocking, run in thread)"""
        try:
            from scp import SCPClient

            with SCPClient(client.get_transport()) as scp:
                scp.put(local_path, remote_path)
            return True
        except Exception as e:
            logger.error(f"File transfer failed: {e}")
            return False

    def _transfer_directory(self, client, local_dir: str, remote_dir: str) -> bool:
        """Transfer entire directory via SCP (blocking, run in thread)"""
        try:
            from scp import SCPClient

            with SCPClient(client.get_transport()) as scp:
                scp.put(local_dir, remote_dir, recursive=True)
            return True
        except Exception as e:
            logger.error(f"Directory transfer failed: {e}")
            return False

    def _transfer_directory_contents(self, client, local_dir: str, remote_dir: str) -> bool:
        """Transfer contents of a directory (files and subdirs) directly into remote_dir"""
        try:
            from scp import SCPClient
            import os

            local_path = Path(local_dir)
            with SCPClient(client.get_transport()) as scp:
                for item in local_path.iterdir():
                    remote_path = f"{remote_dir}/{item.name}"
                    if item.is_file():
                        scp.put(str(item), remote_path)
                    elif item.is_dir():
                        scp.put(str(item), remote_dir, recursive=True)
            return True
        except Exception as e:
            logger.error(f"Directory contents transfer failed: {e}")
            return False

    def _exec_with_timeout(
        self,
        client,
        cmd: str,
        timeout: int = 300,
    ) -> tuple:
        """Execute command with timeout (blocking, run in thread)"""
        try:
            stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)

            # Set channel timeout for read operations
            stdout.channel.settimeout(timeout)
            stderr.channel.settimeout(timeout)

            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode()
            stderr_data = stderr.read().decode()

            return exit_code, stdout_data, stderr_data

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return -1, "", str(e)

    async def _check_remote_service_health(
        self,
        host: str,
        port: int,
        endpoint: str,
        timeout: int = 30
    ) -> bool:
        """Check remote service health via HTTP"""
        try:
            import httpx

            url = f"http://{host}:{port}{endpoint}"
            start_time = asyncio.get_event_loop().time()

            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    async with httpx.AsyncClient() as http_client:
                        response = await http_client.get(url, timeout=5)
                        if response.status_code < 500:
                            return True
                except Exception:
                    pass
                await asyncio.sleep(2)

            return False

        except ImportError:
            logger.warning("httpx not installed, skipping health check")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def _substitute_variables(
        self,
        template: str,
        context: Dict[str, Any],
    ) -> str:
        """Substitute {{variable}} placeholders with values from context"""
        import re

        if not template:
            return template

        def replace_var(match):
            var_name = match.group(1)
            value = context.get(var_name)
            if value is None:
                return ""  # Return empty string if variable not found
            return str(value)

        # Replace {{var}} patterns
        result = re.sub(r'\{\{(\w+)\}\}', replace_var, template)
        return result
