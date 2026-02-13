"""
Remote pre-deployment check service
Checks remote device requirements via SSH before deployment
"""

import asyncio
import logging
import re
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RemoteCheckResult(BaseModel):
    """Result of a remote pre-deployment check"""

    check_type: str
    passed: bool
    message: str
    can_auto_fix: bool = False
    fix_action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class RemotePreCheckService:
    """Validates remote device requirements via SSH"""

    async def check_docker(
        self,
        ssh_client,
        progress_callback: Optional[Callable] = None,
    ) -> RemoteCheckResult:
        """Check if Docker is installed on remote device"""
        try:
            # Check docker version
            exit_code, stdout, stderr = await asyncio.to_thread(
                self._exec_command, ssh_client, "docker --version", timeout=30
            )

            if exit_code != 0:
                return RemoteCheckResult(
                    check_type="docker_installed",
                    passed=False,
                    message="Docker is not installed on remote device",
                    can_auto_fix=True,
                    fix_action="install_docker",
                )

            # Parse version
            version_match = re.search(r"Docker version (\d+\.\d+\.\d+)", stdout)
            version = version_match.group(1) if version_match else "unknown"

            # Check if docker daemon is running
            exit_code, stdout, stderr = await asyncio.to_thread(
                self._exec_command, ssh_client, "docker info", timeout=30
            )

            if exit_code != 0:
                # Check if it's a permission issue
                if "permission denied" in stderr.lower():
                    return RemoteCheckResult(
                        check_type="docker_installed",
                        passed=False,
                        message=f"Docker {version} installed but user lacks permission. Need to add user to docker group.",
                        can_auto_fix=True,
                        fix_action="fix_docker_permission",
                        details={"version": version},
                    )
                else:
                    return RemoteCheckResult(
                        check_type="docker_installed",
                        passed=False,
                        message=f"Docker {version} installed but daemon is not running",
                        can_auto_fix=True,
                        fix_action="start_docker",
                        details={"version": version},
                    )

            return RemoteCheckResult(
                check_type="docker_installed",
                passed=True,
                message=f"Docker {version} is installed and running",
                details={"version": version},
            )

        except Exception as e:
            logger.error(f"Remote Docker check failed: {e}")
            return RemoteCheckResult(
                check_type="docker_installed",
                passed=False,
                message=f"Failed to check Docker: {str(e)}",
            )

    async def check_docker_compose(
        self,
        ssh_client,
        progress_callback: Optional[Callable] = None,
    ) -> RemoteCheckResult:
        """Check if Docker Compose is available on remote device"""
        try:
            # Check docker compose version (v2 plugin style)
            exit_code, stdout, stderr = await asyncio.to_thread(
                self._exec_command, ssh_client, "docker compose version", timeout=30
            )

            if exit_code == 0:
                version_match = re.search(r"v?(\d+\.\d+\.\d+)", stdout)
                version = version_match.group(1) if version_match else "unknown"
                return RemoteCheckResult(
                    check_type="docker_compose_installed",
                    passed=True,
                    message=f"Docker Compose {version} is available",
                    details={"version": version},
                )

            # Try standalone docker-compose
            exit_code, stdout, stderr = await asyncio.to_thread(
                self._exec_command, ssh_client, "docker-compose --version", timeout=30
            )

            if exit_code == 0:
                version_match = re.search(r"(\d+\.\d+\.\d+)", stdout)
                version = version_match.group(1) if version_match else "unknown"
                return RemoteCheckResult(
                    check_type="docker_compose_installed",
                    passed=True,
                    message=f"Docker Compose (standalone) {version} is available",
                    details={"version": version, "standalone": True},
                )

            return RemoteCheckResult(
                check_type="docker_compose_installed",
                passed=False,
                message="Docker Compose is not installed",
                can_auto_fix=True,
                fix_action="install_docker",  # Docker installation includes compose
            )

        except Exception as e:
            logger.error(f"Remote Docker Compose check failed: {e}")
            return RemoteCheckResult(
                check_type="docker_compose_installed",
                passed=False,
                message=f"Failed to check Docker Compose: {str(e)}",
            )

    async def install_docker(
        self,
        ssh_client,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Install Docker on remote device (supports Debian/Ubuntu and generic Linux)"""
        try:
            if progress_callback:
                await progress_callback("install_docker", 0, "Detecting system...")

            # Detect distro and init system
            distro = await self.detect_distro(ssh_client)
            init_system = await self.detect_init_system(ssh_client)

            distro_id = distro["id"]
            distro_like = distro["like"]

            logger.info(
                f"Installing Docker on {distro['name']} ({distro_id}), init: {init_system}"
            )

            if progress_callback:
                await progress_callback(
                    "install_docker", 10, f"Installing Docker on {distro['name']}..."
                )

            # Check for OpenWrt - Docker is not typically supported
            if distro_id == "openwrt":
                logger.warning(
                    "OpenWrt detected - Docker installation may not be supported"
                )
                if progress_callback:
                    await progress_callback(
                        "install_docker",
                        0,
                        "OpenWrt detected. Docker is not typically supported on OpenWrt due to resource constraints. "
                        "Please use a device with full Linux support.",
                    )
                return False

            # Determine if Debian-based
            is_debian_based = (
                distro_id in ("debian", "ubuntu", "raspbian", "linuxmint")
                or "debian" in distro_like
                or "ubuntu" in distro_like
            )

            if is_debian_based:
                # Install Docker on Debian/Ubuntu using official method
                install_script = """
                    set -e
                    export DEBIAN_FRONTEND=noninteractive

                    # Update package index
                    sudo -E apt-get update

                    # Install prerequisites
                    sudo -E apt-get install -y ca-certificates curl gnupg

                    # Add Docker's official GPG key
                    sudo install -m 0755 -d /etc/apt/keyrings
                    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | sudo gpg --batch --yes --dearmor -o /etc/apt/keyrings/docker.gpg
                    sudo chmod a+r /etc/apt/keyrings/docker.gpg

                    # Set up repository
                    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

                    # Install Docker Engine
                    sudo -E apt-get update
                    sudo -E apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

                    # Add current user to docker group
                    sudo usermod -aG docker $USER

                    echo "Docker installation completed"
                """

                # Start service based on init system
                if init_system == "systemd":
                    install_script += """
                    sudo systemctl enable docker
                    sudo systemctl start docker
                    """
                else:
                    install_script += """
                    sudo update-rc.d docker defaults 2>/dev/null || true
                    sudo /etc/init.d/docker start 2>/dev/null || sudo service docker start || true
                    """
            else:
                # Generic install script using convenience script
                install_script = """
                    set -e
                    curl -fsSL https://get.docker.com -o get-docker.sh
                    sudo sh get-docker.sh
                    sudo usermod -aG docker $USER
                    rm -f get-docker.sh
                    echo "Docker installation completed"
                """

                # Start service based on init system
                if init_system == "systemd":
                    install_script += """
                    sudo systemctl enable docker
                    sudo systemctl start docker
                    """
                else:
                    install_script += """
                    sudo /etc/init.d/docker start 2>/dev/null || sudo service docker start || true
                    """

            if progress_callback:
                await progress_callback(
                    "install_docker", 20, "Running installation script..."
                )

            exit_code, stdout, stderr = await asyncio.to_thread(
                self._exec_command,
                ssh_client,
                install_script,
                timeout=600,  # 10 minutes for installation
            )

            if exit_code != 0:
                logger.error(f"Docker installation failed: {stderr}")
                if progress_callback:
                    await progress_callback(
                        "install_docker", 0, f"Installation failed: {stderr[:200]}"
                    )
                return False

            if progress_callback:
                await progress_callback(
                    "install_docker", 100, "Docker installed successfully"
                )

            return True

        except Exception as e:
            logger.error(f"Docker installation failed: {e}")
            if progress_callback:
                await progress_callback(
                    "install_docker", 0, f"Installation failed: {str(e)}"
                )
            return False

    async def fix_docker_permission(
        self,
        ssh_client,
        username: str,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Fix Docker permission by adding user to docker group"""
        try:
            if progress_callback:
                await progress_callback(
                    "fix_permission", 0, "Fixing Docker permissions..."
                )

            exit_code, stdout, stderr = await asyncio.to_thread(
                self._exec_command,
                ssh_client,
                f"sudo usermod -aG docker {username}",
                timeout=30,
            )

            if exit_code != 0:
                logger.error(f"Failed to fix Docker permission: {stderr}")
                if progress_callback:
                    await progress_callback(
                        "fix_permission", 0, f"Failed: {stderr[:200]}"
                    )
                return False

            if progress_callback:
                await progress_callback(
                    "fix_permission",
                    100,
                    "Permission fixed. Note: User may need to re-login for changes to take effect.",
                )

            return True

        except Exception as e:
            logger.error(f"Failed to fix Docker permission: {e}")
            return False

    async def detect_init_system(
        self,
        ssh_client,
    ) -> str:
        """
        Detect the init system on remote device.

        Returns:
            "systemd" - For Ubuntu/Debian with systemd
            "procd" - For OpenWrt
            "sysvinit" - For traditional init.d systems (reCamera, etc.)
            "unknown" - If detection fails
        """
        try:
            # Check for systemd (Ubuntu, Debian, most modern Linux)
            exit_code, stdout, _ = await asyncio.to_thread(
                self._exec_command,
                ssh_client,
                "systemctl --version 2>/dev/null | head -1",
                timeout=10,
            )
            if exit_code == 0 and "systemd" in stdout.lower():
                return "systemd"

            # Check for procd (OpenWrt)
            exit_code, stdout, _ = await asyncio.to_thread(
                self._exec_command,
                ssh_client,
                "[ -f /sbin/procd ] && echo procd",
                timeout=10,
            )
            if exit_code == 0 and "procd" in stdout:
                return "procd"

            # Check for SysVinit style (init.d scripts)
            exit_code, stdout, _ = await asyncio.to_thread(
                self._exec_command,
                ssh_client,
                "[ -d /etc/init.d ] && echo sysvinit",
                timeout=10,
            )
            if exit_code == 0 and "sysvinit" in stdout:
                return "sysvinit"

            return "unknown"

        except Exception as e:
            logger.warning(f"Init system detection failed: {e}")
            return "unknown"

    async def detect_distro(
        self,
        ssh_client,
    ) -> Dict[str, str]:
        """
        Detect the Linux distribution on remote device.

        Returns dict with keys: id, name, version, like (e.g., debian-based)
        """
        try:
            exit_code, stdout, _ = await asyncio.to_thread(
                self._exec_command,
                ssh_client,
                "cat /etc/os-release 2>/dev/null",
                timeout=10,
            )

            distro = {
                "id": "unknown",
                "name": "Unknown Linux",
                "version": "",
                "like": "",
            }

            if exit_code == 0 and stdout:
                for line in stdout.strip().split("\n"):
                    if "=" in line:
                        key, _, value = line.partition("=")
                        value = value.strip('"').strip("'")
                        if key == "ID":
                            distro["id"] = value.lower()
                        elif key == "NAME":
                            distro["name"] = value
                        elif key == "VERSION_ID":
                            distro["version"] = value
                        elif key == "ID_LIKE":
                            distro["like"] = value.lower()

            # Special detection for OpenWrt (may not have standard os-release)
            if distro["id"] == "unknown":
                exit_code, stdout, _ = await asyncio.to_thread(
                    self._exec_command,
                    ssh_client,
                    "[ -f /etc/openwrt_release ] && echo openwrt",
                    timeout=10,
                )
                if exit_code == 0 and "openwrt" in stdout:
                    distro["id"] = "openwrt"
                    distro["name"] = "OpenWrt"

            return distro

        except Exception as e:
            logger.warning(f"Distro detection failed: {e}")
            return {"id": "unknown", "name": "Unknown Linux", "version": "", "like": ""}

    async def start_docker_service(
        self,
        ssh_client,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Start Docker daemon on remote device (supports systemd and sysvinit)"""
        try:
            if progress_callback:
                await progress_callback("start_docker", 0, "Detecting init system...")

            init_system = await self.detect_init_system(ssh_client)
            logger.info(f"Detected init system: {init_system}")

            if progress_callback:
                await progress_callback(
                    "start_docker", 20, f"Starting Docker ({init_system})..."
                )

            if init_system == "systemd":
                cmd = "sudo systemctl start docker && sudo systemctl enable docker"
            elif init_system in ("sysvinit", "procd"):
                # For OpenWrt/SysVinit systems
                cmd = "sudo /etc/init.d/docker start 2>/dev/null || sudo service docker start 2>/dev/null || true"
            else:
                # Try systemd first, fall back to init.d
                cmd = "(sudo systemctl start docker 2>/dev/null || sudo /etc/init.d/docker start 2>/dev/null || sudo service docker start 2>/dev/null) && echo started"

            exit_code, stdout, stderr = await asyncio.to_thread(
                self._exec_command, ssh_client, cmd, timeout=60
            )

            if exit_code != 0:
                logger.error(f"Failed to start Docker: {stderr}")
                if progress_callback:
                    await progress_callback(
                        "start_docker", 0, f"Failed: {stderr[:200]}"
                    )
                return False

            if progress_callback:
                await progress_callback("start_docker", 100, "Docker service started")

            return True

        except Exception as e:
            logger.error(f"Failed to start Docker: {e}")
            return False

    async def check_remote_os(
        self,
        ssh_client,
    ) -> RemoteCheckResult:
        """
        Check if remote device is running a supported Linux OS.

        This application only supports deploying to Linux systems.
        Windows and macOS targets are not supported.
        """
        try:
            # Check uname to determine OS type
            exit_code, stdout, stderr = await asyncio.to_thread(
                self._exec_command, ssh_client, "uname -s", timeout=30
            )

            if exit_code != 0:
                return RemoteCheckResult(
                    check_type="remote_os",
                    passed=False,
                    message=f"Failed to detect remote OS: {stderr[:200]}",
                    details={"error": stderr},
                )

            os_name = stdout.strip().lower()

            # Check for supported OS (Linux only)
            if os_name == "linux":
                # Get more details about the Linux distribution
                exit_code, distro_info, _ = await asyncio.to_thread(
                    self._exec_command,
                    ssh_client,
                    "cat /etc/os-release 2>/dev/null | head -5 || echo 'Unknown Linux'",
                    timeout=30,
                )

                return RemoteCheckResult(
                    check_type="remote_os",
                    passed=True,
                    message="Remote device is running Linux",
                    details={
                        "os": "Linux",
                        "distro_info": distro_info.strip()[:500],
                    },
                )

            elif os_name == "darwin":
                return RemoteCheckResult(
                    check_type="remote_os",
                    passed=False,
                    message="Remote device is running macOS. Only Linux targets are supported for deployment.",
                    can_auto_fix=False,
                    details={"os": "macOS"},
                )

            elif "mingw" in os_name or "msys" in os_name or "cygwin" in os_name:
                return RemoteCheckResult(
                    check_type="remote_os",
                    passed=False,
                    message="Remote device appears to be running Windows. Only Linux targets are supported for deployment.",
                    can_auto_fix=False,
                    details={"os": "Windows", "uname": os_name},
                )

            else:
                return RemoteCheckResult(
                    check_type="remote_os",
                    passed=False,
                    message=f"Unsupported remote OS: {os_name}. Only Linux targets are supported.",
                    can_auto_fix=False,
                    details={"os": os_name},
                )

        except Exception as e:
            logger.error(f"Remote OS check failed: {e}")
            return RemoteCheckResult(
                check_type="remote_os",
                passed=False,
                message=f"Failed to check remote OS: {str(e)}",
            )

    def _exec_command(
        self,
        client,
        cmd: str,
        timeout: int = 300,
    ) -> tuple:
        """Execute command on remote device (blocking, run in thread)"""
        try:
            stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
            stdout.channel.settimeout(timeout)
            stderr.channel.settimeout(timeout)

            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode()
            stderr_data = stderr.read().decode()

            return exit_code, stdout_data, stderr_data

        except Exception as e:
            logger.error(f"Remote command execution failed: {e}")
            return -1, "", str(e)


# Global instance
remote_pre_check = RemotePreCheckService()
