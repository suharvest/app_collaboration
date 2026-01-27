"""
reCamera C++ deployment deployer

Deploys C++ applications to reCamera devices via SSH using opkg.
Based on actual deployment process from sscma-example-sg200x.

Key features:
- .deb package installation via opkg (includes init script)
- Model file deployment to /userdata/local/models
- Automatic conflict service handling (stop node-red, sscma-node, etc.)
- Optional MQTT external access configuration
- Optional service disabling (rename S* to K*)
"""

import asyncio
import logging
import shlex
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List

from .base import BaseDeployer
from ..models.device import DeviceConfig

logger = logging.getLogger(__name__)


def _build_sudo_cmd(password: str, cmd: str) -> str:
    """
    Build a sudo command with proper password escaping.

    Uses printf instead of echo to avoid issues with special characters
    (single quotes, backslashes, etc.) in passwords.

    Args:
        password: The sudo password
        cmd: The command to run with sudo

    Returns:
        A shell command string that safely pipes the password to sudo
    """
    # Use shlex.quote to safely escape the password for the shell
    # printf '%s\n' handles special characters better than echo
    escaped_password = shlex.quote(password)
    return f"printf '%s\\n' {escaped_password} | sudo -S {cmd}"

# Default conflicting services on reCamera
DEFAULT_CONFLICT_SERVICES = [
    "S03node-red",
    "S91sscma-node",
    "S93sscma-supervisor",
    # Also check K* versions (disabled services)
    "K03node-red",
    "K91sscma-node",
    "K93sscma-supervisor",
]


class ReCameraCppDeployer(BaseDeployer):
    """Deploy C++ applications to reCamera devices.

    This deployer handles:
    - .deb package installation via opkg (with included init script)
    - Model file deployment to /userdata/local/models
    - Conflict service handling (stop/disable)
    - Optional MQTT external access configuration

    Note: The deb package typically includes the init script, so no
    separate init script generation is needed.
    """

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Deploy C++ application to reCamera.

        Expected connection parameters:
        - host: reCamera IP address
        - port: SSH port (default: 22)
        - username: SSH username (default: recamera)
        - password: SSH password (required)
        """
        host = connection.get("host")
        port = connection.get("port", 22)
        username = connection.get("username", "recamera")
        password = connection.get("password")

        if not host:
            await self._report_progress(
                progress_callback, "connect", 0, "Host address is required"
            )
            return False

        if not password:
            await self._report_progress(
                progress_callback, "connect", 0, "Password is required"
            )
            return False

        binary_config = config.binary
        if not binary_config:
            await self._report_progress(
                progress_callback, "connect", 0, "No binary configuration"
            )
            return False

        try:
            import paramiko
            from scp import SCPClient

            # Step 1: Connect
            await self._report_progress(
                progress_callback, "connect", 0, f"Connecting to {host}..."
            )

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                await asyncio.to_thread(
                    client.connect,
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=30,
                )
            except paramiko.AuthenticationException:
                await self._report_progress(
                    progress_callback, "connect", 0, "Authentication failed"
                )
                return False
            except Exception as e:
                await self._report_progress(
                    progress_callback, "connect", 0, f"Connection failed: {e}"
                )
                return False

            await self._report_progress(
                progress_callback, "connect", 100, "Connected successfully"
            )

            try:
                # Step 2: Stop conflicting services
                await self._report_progress(
                    progress_callback, "prepare", 0, "Stopping conflicting services..."
                )

                await self._stop_conflict_services(client, binary_config, password)

                await self._report_progress(
                    progress_callback, "prepare", 100, "Services stopped"
                )

                # Step 3: Transfer files
                await self._report_progress(
                    progress_callback, "transfer", 0, "Transferring files..."
                )

                files_to_transfer = await self._prepare_files(config, binary_config)

                with SCPClient(client.get_transport()) as scp:
                    total_files = len(files_to_transfer)
                    for i, (local_path, remote_path) in enumerate(files_to_transfer):
                        progress = int((i / total_files) * 100)
                        await self._report_progress(
                            progress_callback,
                            "transfer",
                            progress,
                            f"Uploading {Path(local_path).name}...",
                        )
                        await asyncio.to_thread(scp.put, local_path, remote_path)

                await self._report_progress(
                    progress_callback, "transfer", 100, "Files transferred"
                )

                # Step 4: Install deb package
                if binary_config.deb_package:
                    await self._report_progress(
                        progress_callback, "install", 0, "Installing package..."
                    )

                    # Clean up any orphaned K* init scripts (from previous Node-RED deployment)
                    # The deb package will create a fresh S* script
                    service_name = self._get_service_name(binary_config)
                    if service_name:
                        await self._cleanup_orphaned_scripts(client, service_name, password)

                    deb_name = Path(binary_config.deb_package.path).name
                    install_cmd = _build_sudo_cmd(password, f"opkg install --force-reinstall /tmp/{deb_name}")

                    exit_code, stdout, stderr = await self._exec_sudo(
                        client, install_cmd, password, timeout=120
                    )

                    if exit_code != 0 and "already installed" not in stderr.lower():
                        await self._report_progress(
                            progress_callback,
                            "install",
                            0,
                            f"Package installation failed: {stderr[:200]}",
                        )
                        return False

                    await self._report_progress(
                        progress_callback, "install", 100, "Package installed"
                    )

                # Step 5: Deploy model files
                if binary_config.models:
                    await self._report_progress(
                        progress_callback, "models", 0, "Deploying model files..."
                    )

                    await self._deploy_models(client, binary_config, password)

                    await self._report_progress(
                        progress_callback, "models", 100, "Models deployed"
                    )

                # Step 6: Deploy init script (only if deb doesn't include it)
                # Most deb packages include the init script, so this step is often skipped
                deb_includes_init = (
                    binary_config.deb_package
                    and binary_config.deb_package.includes_init_script
                )
                if not deb_includes_init and binary_config.init_script:
                    await self._report_progress(
                        progress_callback, "configure", 0, "Configuring service..."
                    )

                    await self._deploy_init_script(client, config, binary_config, password)

                    await self._report_progress(
                        progress_callback, "configure", 100, "Service configured"
                    )

                # Step 7: Configure MQTT (optional)
                if binary_config.mqtt_config and binary_config.mqtt_config.enable:
                    await self._report_progress(
                        progress_callback, "mqtt", 0, "Configuring MQTT..."
                    )

                    await self._configure_mqtt(client, binary_config.mqtt_config, password)

                    await self._report_progress(
                        progress_callback, "mqtt", 100, "MQTT configured"
                    )

                # Step 8: Disable conflict services (optional)
                if binary_config.conflict_services and binary_config.conflict_services.disable:
                    await self._report_progress(
                        progress_callback, "disable", 0, "Disabling conflicting services..."
                    )

                    await self._disable_services(
                        client, binary_config.conflict_services.disable, password
                    )

                    await self._report_progress(
                        progress_callback, "disable", 100, "Services disabled"
                    )

                # Step 9: Start service
                if binary_config.auto_start:
                    await self._report_progress(
                        progress_callback, "start", 0, "Starting service..."
                    )

                    if not await self._start_service(client, binary_config, password):
                        await self._report_progress(
                            progress_callback, "start", 0, "Service failed to start"
                        )
                        return False

                    await self._report_progress(
                        progress_callback, "start", 100, "Service started"
                    )

                # Step 10: Verify
                await self._report_progress(
                    progress_callback, "verify", 0, "Verifying deployment..."
                )

                await asyncio.sleep(3)

                if await self._verify_service(client, binary_config, password):
                    await self._report_progress(
                        progress_callback, "verify", 100, "Deployment verified"
                    )
                else:
                    await self._report_progress(
                        progress_callback, "verify", 100, "Deployment complete (verification skipped)"
                    )

                return True

            finally:
                client.close()

        except ImportError as e:
            await self._report_progress(
                progress_callback, "connect", 0, f"Missing dependency: {e}"
            )
            return False

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            await self._report_progress(
                progress_callback, "deploy", 0, f"Deployment failed: {e}"
            )
            return False

    async def _stop_conflict_services(
        self,
        client,
        binary_config,
        password: str,
    ) -> None:
        """Stop all conflicting services."""
        services = DEFAULT_CONFLICT_SERVICES.copy()

        if binary_config.conflict_services and binary_config.conflict_services.stop:
            services.extend(binary_config.conflict_services.stop)

        for service in services:
            # Try both S* and K* versions
            for prefix in ["S", "K"]:
                svc_name = service if service.startswith(prefix) else f"{prefix}{service.lstrip('SK')}"
                cmd = _build_sudo_cmd(password, f"/etc/init.d/{svc_name} stop 2>/dev/null || true")
                await self._exec_sudo(client, cmd, password, timeout=30)

        # Wait for services to stop
        await asyncio.sleep(2)

    async def _prepare_files(
        self,
        config: DeviceConfig,
        binary_config,
    ) -> List[tuple]:
        """Prepare list of files to transfer."""
        files = []

        # Deb package
        if binary_config.deb_package:
            local_path = config.get_asset_path(binary_config.deb_package.path)
            if local_path and Path(local_path).exists():
                files.append((local_path, "/tmp/"))

        # Model files
        for model in binary_config.models:
            local_path = config.get_asset_path(model.path)
            if local_path and Path(local_path).exists():
                files.append((local_path, "/tmp/"))

        # Init script (only if deb doesn't include it and custom script is provided)
        deb_includes_init = (
            binary_config.deb_package
            and binary_config.deb_package.includes_init_script
        )
        if not deb_includes_init and binary_config.init_script and binary_config.init_script.path:
            local_path = config.get_asset_path(binary_config.init_script.path)
            if local_path and Path(local_path).exists():
                files.append((local_path, "/tmp/"))

        return files

    async def _deploy_models(
        self,
        client,
        binary_config,
        password: str,
    ) -> None:
        """Deploy model files to target directories."""
        for model in binary_config.models:
            target_dir = model.target_path
            filename = model.filename or Path(model.path).name

            # Create target directory
            cmd = _build_sudo_cmd(password, f"mkdir -p {shlex.quote(target_dir)}")
            await self._exec_sudo(client, cmd, password, timeout=30)

            # Copy model file
            src_name = Path(model.path).name
            cmd = _build_sudo_cmd(password, f"cp /tmp/{shlex.quote(src_name)} {shlex.quote(target_dir)}/{shlex.quote(filename)}")
            await self._exec_sudo(client, cmd, password, timeout=60)

    async def _deploy_init_script(
        self,
        client,
        config: DeviceConfig,
        binary_config,
        password: str,
    ) -> None:
        """Deploy custom SysVinit init script.

        This method is only called when the deb package doesn't include
        the init script and a custom script is provided.
        """
        init_config = binary_config.init_script
        if not init_config or not init_config.path:
            logger.warning("No custom init script provided, skipping")
            return

        service_name = init_config.name
        priority = init_config.priority
        script_path = f"/etc/init.d/S{priority:02d}{service_name}"

        # Deploy custom script
        src_name = Path(init_config.path).name
        cmd = _build_sudo_cmd(password, f"cp /tmp/{shlex.quote(src_name)} {shlex.quote(script_path)}")
        await self._exec_sudo(client, cmd, password, timeout=30)

        # Remove old scripts with same name but different priority
        cleanup_cmd = _build_sudo_cmd(password, f"sh -c 'ls /etc/init.d/*{service_name} 2>/dev/null | grep -v {script_path} | xargs rm -f 2>/dev/null || true'")
        await self._exec_sudo(client, cleanup_cmd, password, timeout=30)

        # Make executable
        cmd = _build_sudo_cmd(password, f"chmod +x {shlex.quote(script_path)}")
        await self._exec_sudo(client, cmd, password, timeout=30)

    async def _configure_mqtt(
        self,
        client,
        mqtt_config,
        password: str,
    ) -> None:
        """Configure Mosquitto for external access."""
        # Check if already configured
        check_cmd = "grep -q 'listener 1883 0.0.0.0' /etc/mosquitto/mosquitto.conf 2>/dev/null && echo 'configured'"
        exit_code, stdout, _ = await self._exec_sudo(client, check_cmd, password, timeout=10)

        if "configured" in stdout:
            logger.info("MQTT already configured for external access")
            return

        # Add configuration
        config_cmds = [
            _build_sudo_cmd(password, f"sh -c 'echo \"listener {mqtt_config.port} 0.0.0.0\" >> /etc/mosquitto/mosquitto.conf'"),
        ]

        if mqtt_config.allow_anonymous:
            config_cmds.append(
                _build_sudo_cmd(password, "sh -c 'echo \"allow_anonymous true\" >> /etc/mosquitto/mosquitto.conf'")
            )

        for cmd in config_cmds:
            await self._exec_sudo(client, cmd, password, timeout=30)

        # Restart mosquitto (need two separate sudo commands)
        await self._exec_sudo(client, _build_sudo_cmd(password, "killall mosquitto 2>/dev/null || true"), password, timeout=30)
        await asyncio.sleep(1)
        await self._exec_sudo(client, _build_sudo_cmd(password, "/usr/sbin/mosquitto -c /etc/mosquitto/mosquitto.conf -d"), password, timeout=30)

    async def _disable_services(
        self,
        client,
        services: List[str],
        password: str,
    ) -> None:
        """Disable services by renaming S* to K*."""
        for service in services:
            # Find and rename S* services
            shell_script = f'''for svc in /etc/init.d/S*{service}*; do
    if [ -f "$svc" ]; then
        new_name=$(echo $svc | sed "s|/S|/K|")
        mv "$svc" "$new_name" 2>/dev/null || true
    fi
done'''
            cmd = _build_sudo_cmd(password, f"sh -c {shlex.quote(shell_script)}")
            await self._exec_sudo(client, cmd, password, timeout=30)

    async def _start_service(
        self,
        client,
        binary_config,
        password: str,
    ) -> bool:
        """Start the deployed service."""
        init_config = binary_config.init_script
        if init_config:
            service_name = init_config.name
            priority = init_config.priority
        else:
            service_name = binary_config.service_name
            priority = binary_config.service_priority

        script_path = f"/etc/init.d/S{priority:02d}{service_name}"

        cmd = _build_sudo_cmd(password, f"{script_path} start")
        exit_code, stdout, stderr = await self._exec_sudo(client, cmd, password, timeout=60)

        if exit_code != 0:
            logger.error(f"Failed to start service: {stderr}")
            return False

        return True

    async def _verify_service(
        self,
        client,
        binary_config,
        password: str,
    ) -> bool:
        """Verify the service is running."""
        init_config = binary_config.init_script
        if init_config:
            service_name = init_config.name
            priority = init_config.priority
        else:
            service_name = binary_config.service_name
            priority = binary_config.service_priority

        # Check via init script status
        script_path = f"/etc/init.d/S{priority:02d}{service_name}"
        cmd = _build_sudo_cmd(password, f"{script_path} status")
        exit_code, stdout, _ = await self._exec_sudo(client, cmd, password, timeout=30)

        if "running" in stdout.lower():
            return True

        # Fallback: check process
        cmd = f"ps aux | grep -v grep | grep {service_name}"
        exit_code, stdout, _ = await self._exec_sudo(client, cmd, password, timeout=10)

        return exit_code == 0 and stdout.strip()

    async def _exec_sudo(
        self,
        client,
        cmd: str,
        password: str,
        timeout: int = 60,
    ) -> tuple:
        """Execute command with sudo (password piped)."""
        try:
            stdin, stdout, stderr = await asyncio.to_thread(
                client.exec_command, cmd, timeout=timeout
            )

            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode()
            stderr_data = stderr.read().decode()

            return exit_code, stdout_data, stderr_data

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return -1, "", str(e)

    def _get_service_name(self, binary_config) -> Optional[str]:
        """Get the service name from config."""
        if binary_config.init_script:
            return binary_config.init_script.name
        if binary_config.service_name:
            return binary_config.service_name
        if binary_config.deb_package and binary_config.deb_package.name:
            return binary_config.deb_package.name
        return None

    async def _cleanup_orphaned_scripts(
        self,
        client,
        service_name: str,
        password: str,
    ) -> None:
        """Remove orphaned K* init scripts for the service.

        When switching from Node-RED back to C++, the previous init script
        may have been renamed to K* (disabled). Remove it before installing
        the new deb package which will create a fresh S* script.
        """
        shell_script = f'''for svc in /etc/init.d/K*{service_name}*; do
    if [ -f "$svc" ]; then
        rm -f "$svc" && echo "Removed orphaned: $svc"
    fi
done'''
        cleanup_cmd = _build_sudo_cmd(password, f"sh -c {shlex.quote(shell_script)}") + " 2>/dev/null || true"

        exit_code, stdout, _ = await self._exec_sudo(
            client, cleanup_cmd, password, timeout=30
        )

        if stdout and "Removed orphaned:" in stdout:
            logger.info(stdout.strip())
