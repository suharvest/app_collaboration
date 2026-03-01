"""
SSH + deb deployment deployer
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ..models.device import DeviceConfig
from ..services.remote_pre_check import remote_pre_check
from .base import BaseDeployer
from .ssh_mixin import SSHMixin

logger = logging.getLogger(__name__)


class SSHDeployer(SSHMixin, BaseDeployer):
    """SSH-based deb package deployment"""

    device_type = "ssh_deb"
    ui_traits = {
        "connection": "ssh",
        "auto_deploy": True,
        "renderer": None,
        "has_targets": False,
        "show_model_selection": False,
        "show_service_warning": False,
        "connection_scope": "device",
    }

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        if not config.ssh or not config.package:
            raise ValueError("No SSH or package configuration")

        host = connection.get("host")
        port = connection.get("port", config.ssh.port)
        username = connection.get("username", config.ssh.default_user)
        password = connection.get("password")
        key_file = connection.get("key_file")

        if not host:
            raise ValueError("No host specified for SSH deployment")

        try:
            import paramiko  # noqa: F401
            from scp import SCPClient  # noqa: F401

            # Step 1: Connect (wrapped in thread for async safety)
            await self._report_progress(
                progress_callback, "connect", 0, f"Connecting to {host}..."
            )

            client = await asyncio.to_thread(
                self._create_ssh_connection,
                host,
                port,
                username,
                password,
                key_file,
                config.ssh.connection_timeout,
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
                # Step 1.5: Check remote OS is Linux
                await self._report_progress(
                    progress_callback,
                    "check_os",
                    0,
                    "Checking remote operating system...",
                )

                os_check = await remote_pre_check.check_remote_os(client)
                if not os_check.passed:
                    await self._report_progress(
                        progress_callback, "check_os", 0, os_check.message
                    )
                    return False

                await self._report_progress(
                    progress_callback, "check_os", 100, os_check.message
                )

                # Step 2: Transfer package
                await self._report_progress(
                    progress_callback, "transfer", 0, "Transferring package..."
                )

                package_source = config.package.source
                # path is already resolved to a local file by resolve_remote_assets
                local_path = config.get_asset_path(package_source.path)
                if not local_path or not Path(local_path).exists():
                    await self._report_progress(
                        progress_callback,
                        "transfer",
                        0,
                        f"Package not found: {package_source.path}",
                    )
                    return False

                package_name = Path(local_path).name
                remote_path = f"/tmp/{package_name}"

                # Transfer file with async wrapper
                success = await asyncio.to_thread(
                    self._transfer_file, client, local_path, remote_path
                )

                if not success:
                    await self._report_progress(
                        progress_callback, "transfer", 0, "File transfer failed"
                    )
                    return False

                await self._report_progress(
                    progress_callback, "transfer", 100, "Package transferred"
                )

                # Step 3: Install package
                await self._report_progress(
                    progress_callback, "install", 0, "Installing package..."
                )

                # Run install commands
                install_commands = config.package.install_commands or [
                    f"dpkg -i {remote_path}",
                    "apt-get install -f -y",
                ]

                for i, cmd_template in enumerate(install_commands):
                    cmd = cmd_template.replace("{package}", remote_path).replace(
                        "{package_path}", remote_path
                    )

                    await self._report_progress(
                        progress_callback,
                        "install",
                        int((i / len(install_commands)) * 100),
                        f"Running: {cmd}",
                    )

                    exit_code, _, stderr = await asyncio.to_thread(
                        self._exec_with_timeout, client, cmd, config.ssh.command_timeout
                    )

                    if exit_code != 0:
                        await self._report_progress(
                            progress_callback,
                            "install",
                            0,
                            f"Install failed: {stderr[:200]}",
                        )
                        return False

                await self._report_progress(
                    progress_callback, "install", 100, "Package installed"
                )

                # Step 4: Configure
                await self._report_progress(
                    progress_callback, "configure", 0, "Configuring..."
                )

                # Transfer config files
                for config_file in config.package.config_files:
                    local_config = config.get_asset_path(config_file.source)
                    if local_config and Path(local_config).exists():
                        await asyncio.to_thread(
                            self._transfer_file,
                            client,
                            local_config,
                            config_file.destination,
                        )

                        # Set permissions
                        await asyncio.to_thread(
                            self._exec_with_timeout,
                            client,
                            f"chmod {config_file.mode} {config_file.destination}",
                            30,
                        )

                await self._report_progress(
                    progress_callback, "configure", 100, "Configuration applied"
                )

                # Step 5: Start service
                await self._report_progress(
                    progress_callback, "start_service", 0, "Starting service..."
                )

                if config.package.service:
                    service = config.package.service

                    if service.enable:
                        await asyncio.to_thread(
                            self._exec_with_timeout,
                            client,
                            f"systemctl enable {service.name}",
                            30,
                        )

                    if service.start:
                        exit_code, _, stderr = await asyncio.to_thread(
                            self._exec_with_timeout,
                            client,
                            f"systemctl restart {service.name}",
                            60,
                        )

                        if exit_code != 0:
                            await self._report_progress(
                                progress_callback,
                                "start_service",
                                0,
                                f"Service start failed: {stderr[:200]}",
                            )
                            return False

                        # Verify service is running
                        await asyncio.sleep(2)
                        exit_code, stdout, _ = await asyncio.to_thread(
                            self._exec_with_timeout,
                            client,
                            f"systemctl is-active {service.name}",
                            30,
                        )
                        status = stdout.strip()

                        if status != "active":
                            await self._report_progress(
                                progress_callback,
                                "start_service",
                                0,
                                f"Service not active: {status}",
                            )
                            return False

                await self._report_progress(
                    progress_callback, "start_service", 100, "Service running"
                )

                # Cleanup
                await asyncio.to_thread(
                    self._exec_with_timeout, client, f"rm -f {remote_path}", 30
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
            logger.error(f"SSH deployment failed: {e}")
            await self._report_progress(
                progress_callback, "install", 0, f"Deployment failed: {str(e)}"
            )
            return False

