"""
reCamera Node-RED deployment deployer

Deploys Node-RED flows to reCamera devices via Node-RED Admin HTTP API.
Includes service cleanup to stop conflicting C++ applications before deployment.

When switching from C++ to Node-RED:
- Stops and disables C++ services (S* → K*)
- Restores and enables Node-RED services (K* → S*)
"""

import asyncio
import logging
import shlex
from typing import Callable, Optional, Dict, Any, List

from .nodered_deployer import NodeRedDeployer
from ..models.device import DeviceConfig

logger = logging.getLogger(__name__)


def _build_sudo_cmd(password: str, cmd: str) -> str:
    """
    Build a sudo command with proper password escaping.

    Uses printf instead of echo to avoid issues with special characters
    (single quotes, backslashes, etc.) in passwords.
    """
    escaped_password = shlex.quote(password)
    return f"printf '%s\\n' {escaped_password} | sudo -S {cmd}"

# C++ services that conflict with Node-RED (need to stop and disable)
CPP_CONFLICT_SERVICES = [
    "yolo26-detector",
    "sensecraft",
    "sscma",
    "recamera",
]

# Node-RED related services that need to be enabled
NODERED_SERVICES = [
    "node-red",
    "sscma-node",
    "sscma-supervisor",
]


class ReCameraNodeRedDeployer(NodeRedDeployer):
    """Deploy Node-RED flows to reCamera via Admin HTTP API.

    This deployer extends the base NodeRedDeployer with reCamera-specific
    functionality:
    - Stops and disables conflicting C++ services before deployment
    - Restores and enables Node-RED related services
    - Updates InfluxDB configuration in the flow
    - Sets InfluxDB credentials via Node-RED API
    """

    async def _pre_deploy_hook(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Prepare reCamera for Node-RED deployment.

        This includes:
        1. Stopping and disabling C++ services
        2. Restoring Node-RED services that may have been disabled
        """
        recamera_ip = connection.get("recamera_ip")
        ssh_password = connection.get("ssh_password")

        if not recamera_ip:
            logger.info("No SSH credentials provided, skipping service management")
            return True

        if not ssh_password:
            logger.info("No SSH password provided, skipping service management")
            return True

        await self._report_progress(
            progress_callback, "prepare", 30, "Stopping C++ services..."
        )

        try:
            await self._manage_services(
                recamera_ip,
                connection.get("ssh_username", "recamera"),
                ssh_password,
                connection.get("ssh_port", 22),
                progress_callback,
            )
        except Exception as e:
            logger.warning(f"Service management failed (non-fatal): {e}")

        return True

    async def _manage_services(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """Manage services for Node-RED deployment.

        1. Stop and disable C++ services (S* → K*)
        2. Restore Node-RED services (K* → S*)
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

                # Step 1: Stop and disable C++ services
                await self._report_progress(
                    progress_callback, "prepare", 40, "Disabling C++ services..."
                )
                await self._stop_and_disable_cpp_services(client, password)

                # Step 2: Restore Node-RED services
                await self._report_progress(
                    progress_callback, "prepare", 70, "Restoring Node-RED services..."
                )
                await self._restore_nodered_services(client, password)

                # Step 3: Kill any remaining C++ processes
                await self._kill_cpp_processes(client, password)

                await asyncio.sleep(2)
                logger.info("Service management completed successfully")

            finally:
                client.close()

        except ImportError:
            logger.warning("paramiko not available, skipping service management")

        except Exception as e:
            logger.warning(f"Service management failed: {e}")

    async def _stop_and_disable_cpp_services(
        self,
        client,
        password: str,
    ) -> None:
        """Stop C++ services and disable them (S* → K*)."""
        # Find all C++ related services
        for svc_name in CPP_CONFLICT_SERVICES:
            # Stop and disable S* version
            stop_script = f'for f in /etc/init.d/S*{svc_name}*; do [ -f "$f" ] && $f stop 2>/dev/null; done'
            stop_cmd = _build_sudo_cmd(password, f"sh -c {shlex.quote(stop_script)}") + " || true"
            await self._exec_cmd(client, stop_cmd)

            # Rename S* to K* to disable auto-start
            disable_script = f'''for svc in /etc/init.d/S*{svc_name}*; do
    if [ -f "$svc" ]; then
        new_name=$(echo "$svc" | sed "s|/S|/K|")
        mv "$svc" "$new_name" 2>/dev/null && echo "Disabled: $svc -> $new_name"
    fi
done'''
            disable_cmd = _build_sudo_cmd(password, f"sh -c {shlex.quote(disable_script)}") + " || true"
            result = await self._exec_cmd(client, disable_cmd)
            if result and "Disabled:" in result:
                logger.info(result.strip())

        # Also scan for other custom S9* services and stop them
        scan_script = 'for f in /etc/init.d/S9*; do [ -f "$f" ] && basename "$f"; done'
        scan_cmd = _build_sudo_cmd(password, f"sh -c {shlex.quote(scan_script)}") + " 2>/dev/null || true"
        result = await self._exec_cmd(client, scan_cmd)
        if result:
            for svc in result.strip().split('\n'):
                svc = svc.strip()
                if not svc:
                    continue
                # Skip Node-RED related services
                if any(nr in svc.lower() for nr in ['node-red', 'sscma-node', 'sscma-supervisor']):
                    continue
                # Stop other S9* services
                cmd = _build_sudo_cmd(password, f"/etc/init.d/{svc} stop 2>/dev/null || true")
                await self._exec_cmd(client, cmd)

    async def _restore_nodered_services(
        self,
        client,
        password: str,
    ) -> None:
        """Restore Node-RED services that may have been disabled (K* → S*)."""
        for svc_name in NODERED_SERVICES:
            # Rename K* back to S* to enable auto-start
            restore_script = f'''for svc in /etc/init.d/K*{svc_name}*; do
    if [ -f "$svc" ]; then
        new_name=$(echo "$svc" | sed "s|/K|/S|")
        mv "$svc" "$new_name" 2>/dev/null && echo "Restored: $svc -> $new_name"
    fi
done'''
            restore_cmd = _build_sudo_cmd(password, f"sh -c {shlex.quote(restore_script)}") + " || true"
            result = await self._exec_cmd(client, restore_cmd)
            if result and "Restored:" in result:
                logger.info(result.strip())

    async def _kill_cpp_processes(
        self,
        client,
        password: str,
    ) -> None:
        """Kill any remaining C++ processes."""
        kill_cmds = [
            _build_sudo_cmd(password, "pkill -f 'yolo26-detector' 2>/dev/null || true"),
            _build_sudo_cmd(password, "pkill -f 'sensecraft' 2>/dev/null || true"),
            _build_sudo_cmd(password, "pkill -f 'sscma-cpp' 2>/dev/null || true"),
        ]
        for cmd in kill_cmds:
            await self._exec_cmd(client, cmd)

    async def _exec_cmd(
        self,
        client,
        cmd: str,
        timeout: int = 30,
    ) -> Optional[str]:
        """Execute SSH command and return stdout."""
        try:
            stdin, stdout, stderr = await asyncio.to_thread(
                client.exec_command, cmd, timeout=timeout
            )
            stdout.channel.recv_exit_status()
            return stdout.read().decode()
        except Exception as e:
            logger.debug(f"Command failed: {e}")
            return None

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
