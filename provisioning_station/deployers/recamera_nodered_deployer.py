"""
reCamera Node-RED deployment deployer

Deploys Node-RED flows to reCamera devices via Node-RED Admin HTTP API.
Includes service cleanup to stop conflicting C++ applications before deployment.
"""

import asyncio
import logging
from typing import Callable, Optional, Dict, Any, List

from .nodered_deployer import NodeRedDeployer
from ..models.device import DeviceConfig

logger = logging.getLogger(__name__)

# Known C++ services that may conflict with Node-RED flows on reCamera
RECAMERA_CPP_SERVICES = [
    "S99sensecraft",  # SenseCraft C++ app
    "S99sscma",       # SSCMA C++ app
    "S99recamera",    # Custom reCamera apps
]


class ReCameraNodeRedDeployer(NodeRedDeployer):
    """Deploy Node-RED flows to reCamera via Admin HTTP API.

    This deployer extends the base NodeRedDeployer with reCamera-specific
    functionality:
    - Stops conflicting C++ services before deployment
    - Updates InfluxDB configuration in the flow
    - Sets InfluxDB credentials via Node-RED API
    """

    async def _pre_deploy_hook(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Stop conflicting C++ services before deploying Node-RED flow."""

        recamera_ip = connection.get("recamera_ip")
        ssh_password = connection.get("ssh_password")

        if not recamera_ip:
            # Can't clean up without SSH access - just proceed with deployment
            logger.info("No SSH credentials provided, skipping C++ service cleanup")
            return True

        # Only attempt cleanup if SSH password is provided
        if not ssh_password:
            logger.info("No SSH password provided, skipping C++ service cleanup")
            return True

        await self._report_progress(
            progress_callback, "prepare", 50, "Stopping conflicting services..."
        )

        try:
            await self._stop_cpp_services(
                recamera_ip,
                connection.get("ssh_username", "recamera"),
                ssh_password,
                connection.get("ssh_port", 22),
            )
        except Exception as e:
            logger.warning(f"Failed to stop C++ services (non-fatal): {e}")
            # Don't fail deployment if cleanup fails - Node-RED might still work

        return True

    async def _stop_cpp_services(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
    ) -> None:
        """Stop known C++ services on reCamera via SSH.

        reCamera uses SysVinit, so we use /etc/init.d/S??xxx stop commands.
        """
        try:
            import paramiko

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                await asyncio.to_thread(
                    client.connect,
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=10,
                )

                # List all init.d scripts matching known patterns
                for service in RECAMERA_CPP_SERVICES:
                    # Try to find and stop the service
                    cmd = f"ls /etc/init.d/{service}* 2>/dev/null && /etc/init.d/{service}* stop || true"
                    stdin, stdout, stderr = await asyncio.to_thread(
                        client.exec_command, cmd, timeout=30
                    )
                    exit_code = stdout.channel.recv_exit_status()

                    if exit_code == 0:
                        output = stdout.read().decode().strip()
                        if output:
                            logger.info(f"Stopped service: {output}")

                # Also kill any running C++ processes by common names
                kill_cmds = [
                    "pkill -f 'sensecraft' || true",
                    "pkill -f 'sscma-cpp' || true",
                ]
                for cmd in kill_cmds:
                    await asyncio.to_thread(client.exec_command, cmd, timeout=10)

                logger.info("C++ services stopped successfully")

            finally:
                client.close()

        except ImportError:
            logger.warning("paramiko not available, skipping C++ service cleanup")

        except Exception as e:
            logger.warning(f"Failed to stop C++ services: {e}")

    async def _update_flow_config(
        self,
        flow_data: List[Dict],
        config: DeviceConfig,
        connection: Dict[str, Any],
    ) -> tuple[List[Dict], Dict[str, Dict]]:
        """Update InfluxDB configuration in the flow.

        Expected connection parameters:
        - influxdb_url: InfluxDB URL (e.g., "http://192.168.1.100:8086")
        - influxdb_token: InfluxDB API Token
        - influxdb_org: InfluxDB Organization
        - influxdb_bucket: InfluxDB Bucket name
        """
        nodered_config = config.nodered
        credentials = {}

        # Get InfluxDB connection parameters
        influxdb_url = connection.get("influxdb_url")
        influxdb_token = connection.get("influxdb_token")
        influxdb_org = connection.get("influxdb_org", "seeed")
        influxdb_bucket = connection.get("influxdb_bucket", "recamera")

        influxdb_node_id = nodered_config.influxdb_node_id if nodered_config else None
        updated = False

        for node in flow_data:
            # Find InfluxDB config node
            if node.get("type") == "influxdb":
                if influxdb_node_id and node.get("id") != influxdb_node_id:
                    continue

                # Update URL if provided
                if influxdb_url:
                    node["url"] = influxdb_url
                    logger.info(f"Updated InfluxDB URL to: {influxdb_url}")

                # Update organization if provided
                if influxdb_org:
                    node["org"] = influxdb_org

                # Update bucket if this node has bucket field
                if influxdb_bucket and "bucket" in node:
                    node["bucket"] = influxdb_bucket

                # Prepare credentials for this node
                if influxdb_token:
                    credentials[node.get("id")] = {"token": influxdb_token}

                updated = True
                break

            # Also check for influxdb out nodes to update bucket
            if node.get("type") == "influxdb out" and influxdb_bucket:
                node["bucket"] = influxdb_bucket

        if not updated and influxdb_url:
            logger.warning("No InfluxDB config node found in flow")

        return flow_data, credentials

    async def get_current_flows(
        self,
        recamera_ip: str,
        port: int = 1880,
    ) -> Optional[List[Dict]]:
        """Get current flows from reCamera Node-RED (for backup/reference)"""
        return await super().get_current_flows(recamera_ip, port)
