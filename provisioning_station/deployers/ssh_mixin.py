"""
SSH connection mixin for deployers.

Provides shared SSH utilities used by multiple deployers:
- DockerRemoteDeployer
- SSHDeployer
- SSHBinaryDeployer

Extracted to eliminate code duplication of SSH connection creation,
command execution, file transfer, and checksum verification.
"""

import hashlib
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SSHMixin:
    """Mixin providing common SSH operations for deployers."""

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
            logger.error(f"SSH authentication failed for {username}@{host}")
            return None
        except paramiko.SSHException as e:
            logger.error(f"SSH error connecting to {host}: {e}")
            return None
        except OSError as e:
            logger.error(f"Network error connecting to {host}: {e}")
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
