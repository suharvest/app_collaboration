"""
SSH + deb deployment deployer
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional, Dict, Any

from .base import BaseDeployer
from ..models.device import DeviceConfig

logger = logging.getLogger(__name__)


class SSHDeployer(BaseDeployer):
    """SSH-based deb package deployment"""

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
            import paramiko
            from scp import SCPClient

            # Step 1: Connect
            await self._report_progress(
                progress_callback, "connect", 0, f"Connecting to {host}..."
            )

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                if key_file:
                    client.connect(
                        hostname=host,
                        port=port,
                        username=username,
                        key_filename=key_file,
                        timeout=config.ssh.connection_timeout,
                    )
                else:
                    client.connect(
                        hostname=host,
                        port=port,
                        username=username,
                        password=password,
                        timeout=config.ssh.connection_timeout,
                    )

                await self._report_progress(
                    progress_callback, "connect", 100, "Connected successfully"
                )

            except paramiko.AuthenticationException:
                await self._report_progress(
                    progress_callback, "connect", 0, "Authentication failed"
                )
                return False
            except Exception as e:
                await self._report_progress(
                    progress_callback, "connect", 0, f"Connection failed: {str(e)}"
                )
                return False

            # Step 2: Transfer package
            await self._report_progress(
                progress_callback, "transfer", 0, "Transferring package..."
            )

            package_source = config.package.source
            if package_source.type == "local":
                local_path = config.get_asset_path(package_source.path)
                if not local_path or not Path(local_path).exists():
                    await self._report_progress(
                        progress_callback,
                        "transfer",
                        0,
                        f"Package not found: {package_source.path}",
                    )
                    client.close()
                    return False

                package_name = Path(local_path).name
                remote_path = f"/tmp/{package_name}"

                # Transfer file
                with SCPClient(client.get_transport()) as scp:
                    scp.put(local_path, remote_path)

                await self._report_progress(
                    progress_callback, "transfer", 100, "Package transferred"
                )

            else:
                # Download from URL on remote device
                await self._report_progress(
                    progress_callback, "transfer", 0, "Downloading package..."
                )
                url = package_source.url
                package_name = url.split("/")[-1]
                remote_path = f"/tmp/{package_name}"

                stdin, stdout, stderr = client.exec_command(
                    f"wget -O {remote_path} {url}",
                    timeout=config.ssh.command_timeout,
                )
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    await self._report_progress(
                        progress_callback, "transfer", 0, "Download failed"
                    )
                    client.close()
                    return False

                await self._report_progress(
                    progress_callback, "transfer", 100, "Package downloaded"
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

                stdin, stdout, stderr = client.exec_command(
                    cmd, timeout=config.ssh.command_timeout
                )
                exit_code = stdout.channel.recv_exit_status()

                if exit_code != 0:
                    error = stderr.read().decode()
                    await self._report_progress(
                        progress_callback,
                        "install",
                        0,
                        f"Install failed: {error[:200]}",
                    )
                    client.close()
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
                    with SCPClient(client.get_transport()) as scp:
                        scp.put(local_config, config_file.destination)

                    # Set permissions
                    client.exec_command(f"chmod {config_file.mode} {config_file.destination}")

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
                    client.exec_command(f"systemctl enable {service.name}")

                if service.start:
                    stdin, stdout, stderr = client.exec_command(
                        f"systemctl restart {service.name}"
                    )
                    exit_code = stdout.channel.recv_exit_status()

                    if exit_code != 0:
                        error = stderr.read().decode()
                        await self._report_progress(
                            progress_callback,
                            "start_service",
                            0,
                            f"Service start failed: {error[:200]}",
                        )
                        client.close()
                        return False

                    # Verify service is running
                    await asyncio.sleep(2)
                    stdin, stdout, stderr = client.exec_command(
                        f"systemctl is-active {service.name}"
                    )
                    status = stdout.read().decode().strip()

                    if status != "active":
                        await self._report_progress(
                            progress_callback,
                            "start_service",
                            0,
                            f"Service not active: {status}",
                        )
                        client.close()
                        return False

            await self._report_progress(
                progress_callback, "start_service", 100, "Service running"
            )

            # Cleanup
            client.exec_command(f"rm -f {remote_path}")
            client.close()

            return True

        except ImportError:
            await self._report_progress(
                progress_callback,
                "connect",
                0,
                "paramiko or scp not installed",
            )
            return False

        except Exception as e:
            logger.error(f"SSH deployment failed: {e}")
            await self._report_progress(
                progress_callback, "install", 0, f"Deployment failed: {str(e)}"
            )
            return False
