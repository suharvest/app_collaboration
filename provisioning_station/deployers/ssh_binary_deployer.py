"""
SSH Binary deployment base class

Provides common functionality for deploying binary executables via SSH/SCP.
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


class SSHBinaryDeployer(BaseDeployer):
    """Base class for deploying binary executables via SSH.

    This deployer handles:
    - SSH connection management
    - Binary file transfer via SCP
    - Service script creation
    - Service management (start/stop/restart)

    Subclasses can customize the service management system (systemd, SysVinit, etc.)
    """

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Deploy a binary executable via SSH.

        Expected connection parameters:
        - host: Target hostname or IP address
        - port: SSH port (default: 22)
        - username: SSH username
        - password: SSH password (or key_file)
        - key_file: Path to SSH private key (optional)

        Expected config:
        - ssh: SSH configuration
        - binary: Binary deployment configuration
        """
        if not config.ssh:
            raise ValueError("No SSH configuration")

        if not config.binary:
            raise ValueError("No binary configuration")

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

            # Step 1: Connect
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

                # Step 2: Pre-deploy hook (stop conflicting services)
                await self._report_progress(
                    progress_callback, "prepare", 0, "Preparing deployment..."
                )

                if not await self._pre_deploy_hook(
                    client, config, connection, progress_callback
                ):
                    return False

                await self._report_progress(
                    progress_callback, "prepare", 100, "Preparation complete"
                )

                # Step 3: Transfer binary
                await self._report_progress(
                    progress_callback, "transfer", 0, "Transferring binary..."
                )

                binary_config = config.binary
                source = binary_config.source

                if source.type == "local":
                    local_path = config.get_asset_path(source.path)
                    if not local_path or not Path(local_path).exists():
                        await self._report_progress(
                            progress_callback,
                            "transfer",
                            0,
                            f"Binary not found: {source.path}",
                        )
                        return False

                    binary_name = Path(local_path).name
                    remote_path = (
                        binary_config.install_path or f"/usr/local/bin/{binary_name}"
                    )

                    # Transfer file
                    success = await asyncio.to_thread(
                        self._transfer_file, client, local_path, remote_path
                    )

                    if not success:
                        await self._report_progress(
                            progress_callback, "transfer", 0, "File transfer failed"
                        )
                        return False

                    # Verify checksum if specified
                    if source.checksum:
                        await self._report_progress(
                            progress_callback, "transfer", 75, "Verifying checksum..."
                        )

                        checksum_valid = await asyncio.to_thread(
                            self._verify_remote_checksum,
                            client,
                            remote_path,
                            local_path,
                            source.checksum,
                        )

                        if not checksum_valid:
                            await self._report_progress(
                                progress_callback,
                                "transfer",
                                0,
                                "Checksum verification failed",
                            )
                            return False

                else:
                    # Download from URL on remote device
                    await self._report_progress(
                        progress_callback, "transfer", 0, "Downloading binary..."
                    )
                    url = source.url
                    binary_name = url.split("/")[-1]
                    remote_path = (
                        binary_config.install_path or f"/usr/local/bin/{binary_name}"
                    )

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
                    progress_callback, "transfer", 100, "Binary transferred"
                )

                # Step 4: Set permissions
                await self._report_progress(
                    progress_callback, "configure", 0, "Setting permissions..."
                )

                exit_code, _, stderr = await asyncio.to_thread(
                    self._exec_with_timeout, client, f"chmod +x {remote_path}", 30
                )

                if exit_code != 0:
                    await self._report_progress(
                        progress_callback,
                        "configure",
                        0,
                        f"Failed to set permissions: {stderr}",
                    )
                    return False

                # Step 5: Create service script (subclass-specific)
                await self._report_progress(
                    progress_callback, "configure", 50, "Creating service script..."
                )

                if not await self._create_service_script(
                    client, config, connection, remote_path, progress_callback
                ):
                    return False

                await self._report_progress(
                    progress_callback, "configure", 100, "Configuration complete"
                )

                # Step 6: Start service
                await self._report_progress(
                    progress_callback, "start_service", 0, "Starting service..."
                )

                if not await self._start_service(
                    client, config, connection, progress_callback
                ):
                    await self._report_progress(
                        progress_callback, "start_service", 0, "Failed to start service"
                    )
                    return False

                await self._report_progress(
                    progress_callback, "start_service", 100, "Service started"
                )

                # Step 7: Verify service
                await self._report_progress(
                    progress_callback, "verify", 0, "Verifying service..."
                )

                await asyncio.sleep(2)  # Wait for service to start

                if not await self._verify_service(
                    client, config, connection, progress_callback
                ):
                    await self._report_progress(
                        progress_callback, "verify", 0, "Service verification failed"
                    )
                    return False

                await self._report_progress(
                    progress_callback, "verify", 100, "Service running"
                )

                # Post-deploy hook
                await self._post_deploy_hook(
                    client, config, connection, progress_callback
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
            logger.error(f"SSH binary deployment failed: {e}")
            await self._report_progress(
                progress_callback, "deploy", 0, f"Deployment failed: {str(e)}"
            )
            return False

    async def _pre_deploy_hook(
        self,
        ssh_client,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Hook called before deployment starts.

        Subclasses can override to perform pre-deployment tasks like
        stopping conflicting services.

        Returns:
            True to continue with deployment, False to abort
        """
        return True

    async def _create_service_script(
        self,
        ssh_client,
        config: DeviceConfig,
        connection: Dict[str, Any],
        binary_path: str,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Create the service management script.

        Subclasses should override this to create appropriate service scripts
        for their init system (systemd, SysVinit, etc.).

        Returns:
            True if successful, False otherwise
        """
        # Default implementation does nothing
        return True

    async def _start_service(
        self,
        ssh_client,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Start the deployed service.

        Subclasses should override this to implement their init system's
        service start command.

        Returns:
            True if successful, False otherwise
        """
        return True

    async def _verify_service(
        self,
        ssh_client,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Verify the service is running correctly.

        Subclasses can override for custom verification logic.

        Returns:
            True if service is running, False otherwise
        """
        return True

    async def _post_deploy_hook(
        self,
        ssh_client,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """
        Hook called after successful deployment.

        Subclasses can override to perform post-deployment tasks.
        """
        pass

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
            if "sha256" in expected:
                with open(local_path, "rb") as f:
                    local_hash = hashlib.sha256(f.read()).hexdigest()

                expected_hash = expected["sha256"]

                if local_hash != expected_hash:
                    logger.error(
                        f"Local file checksum mismatch: {local_hash} != {expected_hash}"
                    )
                    return False

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
