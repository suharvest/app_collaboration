"""
SSH + deb deployment deployer
"""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ..models.device import DeviceConfig
from ..services.remote_pre_check import remote_pre_check
from .base import BaseDeployer

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
                if package_source.type == "local":
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

                    # Verify checksum if specified
                    if package_source.checksum:
                        await self._report_progress(
                            progress_callback, "transfer", 75, "Verifying checksum..."
                        )

                        checksum_valid = await asyncio.to_thread(
                            self._verify_remote_checksum,
                            client,
                            remote_path,
                            local_path,
                            package_source.checksum,
                        )

                        if not checksum_valid:
                            await self._report_progress(
                                progress_callback,
                                "transfer",
                                0,
                                "Checksum verification failed",
                            )
                            return False

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

                    exit_code, _, stderr = await asyncio.to_thread(
                        self._exec_with_timeout,
                        client,
                        f"wget -O {remote_path} {url}",
                        config.ssh.command_timeout,
                    )

                    if exit_code != 0:
                        await self._report_progress(
                            progress_callback,
                            "transfer",
                            0,
                            f"Download failed: {stderr[:200]}",
                        )
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
        except paramiko.AuthenticationException:
            logger.error("SSH authentication failed")
            return None
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

    def _verify_remote_checksum(
        self,
        client,
        remote_path: str,
        local_path: str,
        expected: Dict[str, str],
    ) -> bool:
        """Verify checksum of remote file matches local file"""
        try:
            # Calculate local file checksum
            if "sha256" in expected:
                with open(local_path, "rb") as f:
                    local_hash = hashlib.sha256(f.read()).hexdigest()

                expected_hash = expected["sha256"]

                # Verify local matches expected
                if local_hash != expected_hash:
                    logger.error(
                        f"Local file checksum mismatch: {local_hash} != {expected_hash}"
                    )
                    return False

                # Get remote file checksum
                exit_code, stdout, _ = self._exec_with_timeout(
                    client, f"sha256sum {remote_path} | cut -d' ' -f1", 30
                )

                if exit_code != 0:
                    logger.error("Failed to calculate remote checksum")
                    return False

                remote_hash = stdout.strip()

                if remote_hash != expected_hash:
                    logger.error(
                        f"Remote checksum mismatch: {remote_hash} != {expected_hash}"
                    )
                    return False

                return True

            elif "md5" in expected:
                with open(local_path, "rb") as f:
                    local_hash = hashlib.md5(f.read()).hexdigest()

                expected_hash = expected["md5"]

                if local_hash != expected_hash:
                    logger.error("Local file MD5 mismatch")
                    return False

                exit_code, stdout, _ = self._exec_with_timeout(
                    client, f"md5sum {remote_path} | cut -d' ' -f1", 30
                )

                if exit_code != 0:
                    return False

                remote_hash = stdout.strip()
                return remote_hash == expected_hash

            # No checksum specified
            return True

        except Exception as e:
            logger.error(f"Checksum verification error: {e}")
            return False
