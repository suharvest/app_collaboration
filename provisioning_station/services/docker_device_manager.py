"""
Docker device management service - SSH-based container management
"""

import json
import logging
from typing import Dict, Any, List, Optional

from ..models.docker_device import (
    ConnectDeviceRequest,
    ContainerInfo,
    DeviceInfo,
    UpgradeRequest,
)

logger = logging.getLogger(__name__)


class DockerDeviceManager:
    """Manages Docker containers on remote devices via SSH"""

    def _get_ssh_client(self, connection: ConnectDeviceRequest):
        """Create and connect an SSH client"""
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=connection.host,
            port=connection.port,
            username=connection.username,
            password=connection.password,
            timeout=10,
        )
        return client

    def _exec_command(self, client, command: str, timeout: int = 30) -> str:
        """Execute a command and return stdout"""
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8").strip()
        if exit_code != 0:
            error = stderr.read().decode("utf-8").strip()
            raise RuntimeError(f"Command failed (exit {exit_code}): {error or output}")
        return output

    async def connect(self, connection: ConnectDeviceRequest) -> DeviceInfo:
        """Test SSH connection and verify Docker is installed"""
        try:
            client = self._get_ssh_client(connection)
            try:
                # Get Docker version
                docker_version = self._exec_command(client, "docker --version")

                # Get hostname
                hostname = self._exec_command(client, "hostname")

                # Get OS info
                try:
                    os_info = self._exec_command(client, "cat /etc/os-release | head -2")
                except Exception:
                    os_info = ""

                return DeviceInfo(
                    hostname=hostname,
                    docker_version=docker_version.replace("Docker version ", "").split(",")[0],
                    os_info=os_info,
                )
            finally:
                client.close()

        except ImportError:
            raise RuntimeError("SSH library (paramiko) not installed")
        except Exception as e:
            logger.error(f"Connection failed to {connection.host}: {e}")
            raise RuntimeError(f"Connection failed: {str(e)}")

    async def list_containers(self, connection: ConnectDeviceRequest) -> List[ContainerInfo]:
        """List all Docker containers on the device"""
        try:
            client = self._get_ssh_client(connection)
            try:
                # Get container list in JSON format
                output = self._exec_command(
                    client,
                    'docker ps -a --format \'{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.Status}}","ports":"{{.Ports}}"}\''
                )

                containers = []
                if not output:
                    return containers

                for line in output.strip().split("\n"):
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        image = data.get("image", "")
                        # Parse image:tag
                        if ":" in image:
                            image_name, tag = image.rsplit(":", 1)
                        else:
                            image_name = image
                            tag = "latest"

                        # Determine status
                        raw_status = data.get("status", "").lower()
                        if "up" in raw_status:
                            status = "running"
                        elif "exited" in raw_status:
                            status = "exited"
                        else:
                            status = "stopped"

                        # Parse ports
                        ports_str = data.get("ports", "")
                        ports = [p.strip() for p in ports_str.split(",") if p.strip()] if ports_str else []

                        containers.append(ContainerInfo(
                            container_id=data.get("id", ""),
                            name=data.get("name", ""),
                            image=image_name,
                            current_tag=tag,
                            status=status,
                            ports=ports,
                        ))
                    except json.JSONDecodeError:
                        continue

                return containers
            finally:
                client.close()

        except ImportError:
            raise RuntimeError("SSH library (paramiko) not installed")
        except Exception as e:
            logger.error(f"Failed to list containers on {connection.host}: {e}")
            raise RuntimeError(f"Failed to list containers: {str(e)}")

    async def upgrade(self, request: UpgradeRequest) -> Dict[str, Any]:
        """Upgrade a container using docker compose pull + up"""
        connection = ConnectDeviceRequest(
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
        )

        try:
            client = self._get_ssh_client(connection)
            try:
                # Pull new images
                compose_dir = request.compose_path.rsplit("/", 1)[0] if "/" in request.compose_path else "."
                project_flag = f"-p {request.project_name}" if request.project_name else ""

                pull_output = self._exec_command(
                    client,
                    f"cd {compose_dir} && docker compose {project_flag} pull",
                    timeout=120,
                )

                # Recreate containers
                up_output = self._exec_command(
                    client,
                    f"cd {compose_dir} && docker compose {project_flag} up -d",
                    timeout=60,
                )

                return {
                    "success": True,
                    "message": "Container upgraded successfully",
                    "pull_output": pull_output,
                    "up_output": up_output,
                }
            finally:
                client.close()

        except ImportError:
            raise RuntimeError("SSH library (paramiko) not installed")
        except Exception as e:
            logger.error(f"Upgrade failed on {request.host}: {e}")
            raise RuntimeError(f"Upgrade failed: {str(e)}")

    async def container_action(
        self,
        connection: ConnectDeviceRequest,
        container_name: str,
        action: str,
    ) -> Dict[str, Any]:
        """Perform action on a container (start/stop/restart)"""
        if action not in ("start", "stop", "restart"):
            raise ValueError(f"Invalid action: {action}")

        try:
            client = self._get_ssh_client(connection)
            try:
                output = self._exec_command(
                    client,
                    f"docker {action} {container_name}",
                    timeout=30,
                )
                return {
                    "success": True,
                    "message": f"Container {container_name} {action}ed successfully",
                    "output": output,
                }
            finally:
                client.close()

        except Exception as e:
            logger.error(f"Container action {action} failed: {e}")
            raise RuntimeError(f"Action failed: {str(e)}")


# Global instance
docker_device_manager = DockerDeviceManager()
