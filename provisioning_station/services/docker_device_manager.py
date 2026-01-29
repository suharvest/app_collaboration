"""
Docker device management service - Local and SSH-based container management
"""

import asyncio
import json
import logging
import socket
import subprocess
from typing import Dict, Any, List, Optional

from ..models.docker_device import (
    ConnectDeviceRequest,
    ContainerInfo,
    DeviceInfo,
    UpgradeRequest,
    ManagedApp,
    ManagedAppContainer,
)
from ..utils.compose_labels import LABELS, parse_container_labels

logger = logging.getLogger(__name__)


class DockerDeviceManager:
    """Manages Docker containers on local and remote devices"""

    # ============================================
    # Local Docker Management
    # ============================================

    async def check_local_docker(self) -> DeviceInfo:
        """Check if Docker is available locally"""
        try:
            # Get Docker version
            result = await asyncio.to_thread(
                subprocess.run,
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError("Docker not available")

            docker_version = result.stdout.strip().replace("Docker version ", "").split(",")[0]

            # Get hostname
            hostname = socket.gethostname()

            return DeviceInfo(
                hostname=hostname,
                docker_version=docker_version,
                os_info="Local Machine",
            )
        except FileNotFoundError:
            raise RuntimeError("Docker is not installed")
        except Exception as e:
            logger.error(f"Local Docker check failed: {e}")
            raise RuntimeError(f"Docker check failed: {str(e)}")

    async def list_local_containers(self) -> List[ContainerInfo]:
        """List all Docker containers on local machine"""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "docker", "ps", "-a", "--format",
                    '{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.Status}}","ports":"{{.Ports}}","labels":"{{.Labels}}"}'
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Docker command failed: {result.stderr}")

            containers = []
            output = result.stdout.strip()
            if not output:
                return containers

            for line in output.split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    image = data.get("image", "")
                    if ":" in image:
                        image_name, tag = image.rsplit(":", 1)
                    else:
                        image_name = image
                        tag = "latest"

                    raw_status = data.get("status", "").lower()
                    if "up" in raw_status:
                        status = "running"
                    elif "exited" in raw_status:
                        status = "exited"
                    else:
                        status = "stopped"

                    ports_str = data.get("ports", "")
                    ports = [p.strip() for p in ports_str.split(",") if p.strip()] if ports_str else []

                    labels_str = data.get("labels", "")
                    labels = {}
                    if labels_str:
                        for pair in labels_str.split(","):
                            if "=" in pair:
                                k, v = pair.split("=", 1)
                                labels[k] = v

                    containers.append(ContainerInfo(
                        container_id=data.get("id", ""),
                        name=data.get("name", ""),
                        image=image_name,
                        current_tag=tag,
                        status=status,
                        ports=ports,
                        labels=labels,
                    ))
                except json.JSONDecodeError:
                    continue

            return containers

        except FileNotFoundError:
            raise RuntimeError("Docker is not installed")
        except Exception as e:
            logger.error(f"Failed to list local containers: {e}")
            raise RuntimeError(f"Failed to list containers: {str(e)}")

    async def list_local_managed_apps(self) -> List[ManagedApp]:
        """List SenseCraft-managed applications on local machine, grouped by solution"""
        containers = await self.list_local_containers()
        return self._group_containers_by_solution(containers)

    def _group_containers_by_solution(self, containers: List[ContainerInfo]) -> List[ManagedApp]:
        """Group containers by solution_id into ManagedApp objects"""
        # Group containers by solution_id
        solution_groups: Dict[str, Dict[str, Any]] = {}

        for container in containers:
            sensecraft_meta = parse_container_labels(container.labels or {})
            if not sensecraft_meta:
                continue

            solution_id = sensecraft_meta.get("solution_id")
            if not solution_id:
                continue

            if solution_id not in solution_groups:
                solution_groups[solution_id] = {
                    "solution_id": solution_id,
                    "solution_name": sensecraft_meta.get("solution_name"),
                    "device_id": sensecraft_meta.get("device_id"),
                    "deployed_at": sensecraft_meta.get("deployed_at"),
                    "containers": [],
                    "ports": [],
                    "statuses": [],
                }

            group = solution_groups[solution_id]
            group["containers"].append(ManagedAppContainer(
                container_id=container.container_id,
                container_name=container.name,
                image=container.image,
                tag=container.current_tag,
                status=container.status,
                ports=container.ports,
            ))
            group["ports"].extend(container.ports)
            group["statuses"].append(container.status)

        # Convert to ManagedApp list
        managed_apps = []
        for group in solution_groups.values():
            # Determine aggregated status: running if any container running
            statuses = group["statuses"]
            if "running" in statuses:
                status = "running"
            elif "exited" in statuses:
                status = "exited"
            else:
                status = "stopped"

            managed_apps.append(ManagedApp(
                solution_id=group["solution_id"],
                solution_name=group["solution_name"],
                device_id=group["device_id"],
                deployed_at=group["deployed_at"],
                status=status,
                containers=group["containers"],
                ports=list(set(group["ports"])),  # Deduplicate ports
            ))

        return managed_apps

    async def local_container_action(self, container_name: str, action: str) -> Dict[str, Any]:
        """Perform action on a local container (start/stop/restart/remove)"""
        if action not in ("start", "stop", "restart", "remove"):
            raise ValueError(f"Invalid action: {action}")

        try:
            if action == "remove":
                # First stop the container, then remove it
                await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "stop", container_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "rm", container_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            else:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["docker", action, container_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            if result.returncode != 0:
                raise RuntimeError(f"Action failed: {result.stderr}")

            action_past = "removed" if action == "remove" else f"{action}ed"
            return {
                "success": True,
                "message": f"Container {container_name} {action_past} successfully",
                "output": result.stdout,
            }
        except Exception as e:
            logger.error(f"Local container action {action} failed: {e}")
            raise RuntimeError(f"Action failed: {str(e)}")

    async def local_remove_app(
        self,
        solution_id: str,
        container_names: List[str],
        remove_images: bool = False,
    ) -> Dict[str, Any]:
        """Remove all containers for an app, optionally removing images"""
        results = []
        images_to_remove = []

        # Get container info before removing (to get image references)
        if remove_images:
            containers = await self.list_local_containers()
            for c in containers:
                if c.name in container_names:
                    images_to_remove.append(f"{c.image}:{c.current_tag}")

        # Remove containers
        for container_name in container_names:
            try:
                result = await self.local_container_action(container_name, "remove")
                results.append({"container": container_name, "success": True})
            except Exception as e:
                results.append({"container": container_name, "success": False, "error": str(e)})

        # Remove images if requested
        images_removed = []
        images_skipped = []
        if remove_images and images_to_remove:
            for image in set(images_to_remove):  # deduplicate
                try:
                    # Check if image is used by other containers
                    check_result = await asyncio.to_thread(
                        subprocess.run,
                        ["docker", "ps", "-a", "--filter", f"ancestor={image}", "--format", "{{.Names}}"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    remaining_containers = [n for n in check_result.stdout.strip().split("\n") if n]

                    if remaining_containers:
                        images_skipped.append({"image": image, "reason": f"used by: {', '.join(remaining_containers)}"})
                        continue

                    # Remove the image
                    result = await asyncio.to_thread(
                        subprocess.run,
                        ["docker", "rmi", image],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    if result.returncode == 0:
                        images_removed.append(image)
                    else:
                        images_skipped.append({"image": image, "reason": result.stderr.strip()})
                except Exception as e:
                    images_skipped.append({"image": image, "reason": str(e)})

        return {
            "success": all(r["success"] for r in results),
            "containers": results,
            "images_removed": images_removed,
            "images_skipped": images_skipped,
        }

    async def local_prune_images(self) -> Dict[str, Any]:
        """Remove all unused Docker images"""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["docker", "image", "prune", "-af"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Prune failed: {result.stderr}")

            # Parse output to get space reclaimed
            output = result.stdout
            space_reclaimed = "0B"
            for line in output.split("\n"):
                if "Total reclaimed space:" in line:
                    space_reclaimed = line.split(":")[-1].strip()
                    break

            return {
                "success": True,
                "message": f"Pruned unused images, reclaimed {space_reclaimed}",
                "output": output,
                "space_reclaimed": space_reclaimed,
            }
        except Exception as e:
            logger.error(f"Local image prune failed: {e}")
            raise RuntimeError(f"Prune failed: {str(e)}")

    # ============================================
    # Remote Docker Management (SSH)
    # ============================================

    def _get_ssh_client(self, connection: ConnectDeviceRequest):
        """Create and connect an SSH client

        Raises:
            paramiko.AuthenticationException: If authentication fails
            paramiko.SSHException: If SSH connection fails
            OSError: If network connection fails
        """
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=connection.host,
                port=connection.port,
                username=connection.username,
                password=connection.password,
                timeout=10,
            )
            return client
        except paramiko.AuthenticationException:
            raise RuntimeError(
                f"Authentication failed for {connection.username}@{connection.host}. "
                "Please check your username and password."
            )
        except paramiko.SSHException as e:
            raise RuntimeError(f"SSH connection error: {e}")
        except OSError as e:
            raise RuntimeError(
                f"Cannot connect to {connection.host}:{connection.port}. "
                f"Network error: {e}"
            )

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
                # Get container list in JSON format with labels
                output = self._exec_command(
                    client,
                    'docker ps -a --format \'{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.Status}}","ports":"{{.Ports}}","labels":"{{.Labels}}"}\''
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

                        # Parse labels
                        labels_str = data.get("labels", "")
                        labels = {}
                        if labels_str:
                            for pair in labels_str.split(","):
                                if "=" in pair:
                                    k, v = pair.split("=", 1)
                                    labels[k] = v

                        containers.append(ContainerInfo(
                            container_id=data.get("id", ""),
                            name=data.get("name", ""),
                            image=image_name,
                            current_tag=tag,
                            status=status,
                            ports=ports,
                            labels=labels,
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

    async def list_managed_apps(self, connection: ConnectDeviceRequest) -> List[ManagedApp]:
        """List only SenseCraft-managed applications on the device, grouped by solution"""
        containers = await self.list_containers(connection)
        return self._group_containers_by_solution(containers)

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
        """Perform action on a container (start/stop/restart/remove)"""
        if action not in ("start", "stop", "restart", "remove"):
            raise ValueError(f"Invalid action: {action}")

        try:
            client = self._get_ssh_client(connection)
            try:
                if action == "remove":
                    # First stop, then remove
                    try:
                        self._exec_command(client, f"docker stop {container_name}", timeout=30)
                    except Exception:
                        pass  # Container might already be stopped
                    output = self._exec_command(client, f"docker rm {container_name}", timeout=30)
                else:
                    output = self._exec_command(
                        client,
                        f"docker {action} {container_name}",
                        timeout=30,
                    )

                action_past = "removed" if action == "remove" else f"{action}ed"
                return {
                    "success": True,
                    "message": f"Container {container_name} {action_past} successfully",
                    "output": output,
                }
            finally:
                client.close()

        except Exception as e:
            logger.error(f"Container action {action} failed: {e}")
            raise RuntimeError(f"Action failed: {str(e)}")

    async def remove_app(
        self,
        connection: ConnectDeviceRequest,
        solution_id: str,
        container_names: List[str],
        remove_images: bool = False,
    ) -> Dict[str, Any]:
        """Remove all containers for an app on remote device, optionally removing images"""
        results = []
        images_to_remove = []

        try:
            client = self._get_ssh_client(connection)
            try:
                # Get container info before removing (to get image references)
                if remove_images:
                    containers = await self.list_containers(connection)
                    for c in containers:
                        if c.name in container_names:
                            images_to_remove.append(f"{c.image}:{c.current_tag}")

                # Remove containers
                for container_name in container_names:
                    try:
                        try:
                            self._exec_command(client, f"docker stop {container_name}", timeout=30)
                        except Exception:
                            pass
                        self._exec_command(client, f"docker rm {container_name}", timeout=30)
                        results.append({"container": container_name, "success": True})
                    except Exception as e:
                        results.append({"container": container_name, "success": False, "error": str(e)})

                # Remove images if requested
                images_removed = []
                images_skipped = []
                if remove_images and images_to_remove:
                    for image in set(images_to_remove):
                        try:
                            # Check if image is used by other containers
                            check_output = self._exec_command(
                                client,
                                f"docker ps -a --filter ancestor={image} --format '{{{{.Names}}}}'",
                                timeout=10,
                            )
                            remaining = [n for n in check_output.strip().split("\n") if n]
                            if remaining:
                                images_skipped.append({"image": image, "reason": f"used by: {', '.join(remaining)}"})
                                continue

                            self._exec_command(client, f"docker rmi {image}", timeout=60)
                            images_removed.append(image)
                        except Exception as e:
                            images_skipped.append({"image": image, "reason": str(e)})

                return {
                    "success": all(r["success"] for r in results),
                    "containers": results,
                    "images_removed": images_removed,
                    "images_skipped": images_skipped,
                }
            finally:
                client.close()

        except Exception as e:
            logger.error(f"Remove app failed: {e}")
            raise RuntimeError(f"Remove app failed: {str(e)}")

    async def prune_images(self, connection: ConnectDeviceRequest) -> Dict[str, Any]:
        """Remove all unused Docker images on remote device"""
        try:
            client = self._get_ssh_client(connection)
            try:
                output = self._exec_command(client, "docker image prune -af", timeout=120)

                # Parse output to get space reclaimed
                space_reclaimed = "0B"
                for line in output.split("\n"):
                    if "Total reclaimed space:" in line:
                        space_reclaimed = line.split(":")[-1].strip()
                        break

                return {
                    "success": True,
                    "message": f"Pruned unused images, reclaimed {space_reclaimed}",
                    "output": output,
                    "space_reclaimed": space_reclaimed,
                }
            finally:
                client.close()

        except Exception as e:
            logger.error(f"Remote image prune failed: {e}")
            raise RuntimeError(f"Prune failed: {str(e)}")


# Global instance
docker_device_manager = DockerDeviceManager()
