"""
reCamera Node-RED deployment deployer

Deploys Node-RED flows to reCamera devices via Node-RED Admin HTTP API.
Includes service cleanup to stop conflicting C++ applications before deployment.

When switching from C++ to Node-RED:
- Stops and disables C++ services (S* → K*)
- Restores and enables Node-RED services (K* → S*)

Pre-deployment state check:
- Detects current device mode (clean, cpp, nodered, mixed)
- Automatically cleans up conflicting state for idempotent deployment
"""

import asyncio
import logging
import shlex
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..models.device import DeviceConfig
from .nodered_deployer import NodeRedDeployer

logger = logging.getLogger(__name__)


class DeviceMode(str, Enum):
    """Current deployment mode of the reCamera device"""

    CLEAN = "clean"  # No C++ services, no C++ packages, Node-RED at default state
    CPP = "cpp"  # C++ services running or C++ packages installed
    NODERED = "nodered"  # Node-RED running, no C++ services
    MIXED = "mixed"  # Both running (abnormal state)


@dataclass
class DeviceState:
    """Represents the current state of a reCamera device"""

    mode: DeviceMode
    cpp_services: List[str]  # Found C++ init scripts (S* or K*)
    cpp_packages: List[str]  # Installed C++ packages
    cpp_processes_running: bool  # C++ processes detected
    nodered_enabled: bool  # Node-RED S* script exists
    nodered_disabled: bool  # Node-RED K* script exists (was disabled)
    nodered_running: bool  # Node-RED process running

    @property
    def ready_for_nodered(self) -> bool:
        """Check if device is ready for Node-RED deployment without cleanup"""
        # Ready if clean or already in nodered mode
        return self.mode in (DeviceMode.CLEAN, DeviceMode.NODERED)

    @property
    def needs_cpp_cleanup(self) -> bool:
        """Check if C++ services need to be stopped/disabled"""
        return (
            bool(self.cpp_services)
            or bool(self.cpp_packages)
            or self.cpp_processes_running
        )

    @property
    def needs_nodered_restore(self) -> bool:
        """Check if Node-RED service needs to be restored (K* → S*)"""
        return self.nodered_disabled and not self.nodered_enabled


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
        1. Pre-deployment state check
        2. Automatic cleanup of conflicting state
        3. Stopping and disabling C++ services
        4. Restoring Node-RED services that may have been disabled
        """
        recamera_ip = connection.get("recamera_ip")
        ssh_password = connection.get("ssh_password")

        if not recamera_ip:
            logger.info("No SSH credentials provided, skipping service management")
            return True

        if not ssh_password:
            logger.info("No SSH password provided, skipping service management")
            return True

        try:
            import paramiko

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                await asyncio.to_thread(
                    client.connect,
                    hostname=recamera_ip,
                    port=connection.get("ssh_port", 22),
                    username=connection.get("ssh_username", "recamera"),
                    password=ssh_password,
                    timeout=10,
                )

                # Step 1: Pre-deployment state check
                await self._report_progress(
                    progress_callback, "prepare", 10, "Checking device state..."
                )

                state = await self._check_device_state(client, ssh_password)
                logger.info(
                    f"Device state: mode={state.mode.value}, "
                    f"cpp_services={state.cpp_services}, "
                    f"cpp_packages={state.cpp_packages}, "
                    f"nodered_enabled={state.nodered_enabled}, "
                    f"nodered_disabled={state.nodered_disabled}, "
                    f"nodered_running={state.nodered_running}"
                )

                # Report state to user
                state_msg = f"Device mode: {state.mode.value}"
                if state.cpp_packages:
                    state_msg += f", C++ packages: {len(state.cpp_packages)}"
                if state.nodered_disabled:
                    state_msg += ", Node-RED disabled"

                await self._report_progress(progress_callback, "prepare", 20, state_msg)

                # Step 2: Perform cleanup if needed
                if state.needs_cpp_cleanup or state.needs_nodered_restore:
                    await self._report_progress(
                        progress_callback,
                        "prepare",
                        30,
                        "Cleaning up conflicting state...",
                    )
                    await self._ensure_clean_state_for_nodered(
                        client, state, ssh_password, progress_callback
                    )
                else:
                    # Just do the standard service management
                    await self._report_progress(
                        progress_callback, "prepare", 30, "Preparing services..."
                    )
                    await self._stop_and_disable_cpp_services(client, ssh_password)
                    await self._restore_nodered_services(client, ssh_password)
                    await self._kill_cpp_processes(client, ssh_password)

                await self._report_progress(
                    progress_callback, "prepare", 90, "Device ready for Node-RED"
                )

            finally:
                client.close()

        except ImportError:
            logger.warning("paramiko not available, skipping service management")
        except Exception as e:
            logger.warning(f"Service management failed (non-fatal): {e}")

        return True

    async def _check_device_state(
        self,
        client,
        password: str,
    ) -> DeviceState:
        """Check the current deployment state of the device.

        Detects:
        - C++ services (init scripts matching yolo*, detector*, sensecraft*)
        - Installed C++ packages (via opkg)
        - Running C++ processes
        - Node-RED service state (enabled/disabled, running)

        Note: Only S* scripts (enabled) are counted as active services.
        K* scripts (disabled) are tracked separately but don't count as "has service".
        """
        # Check for C++ init scripts (both S* enabled and K* disabled)
        cpp_services = []
        cpp_services_enabled = []  # Only S* scripts
        cpp_patterns = ["yolo", "detector", "sensecraft", "sscma-cpp", "recamera-app"]

        for pattern in cpp_patterns:
            cmd = f"ls /etc/init.d/S*{pattern}* /etc/init.d/K*{pattern}* 2>/dev/null || true"
            result = await self._exec_cmd(client, cmd)
            if result and result.strip():
                for line in result.strip().split("\n"):
                    svc = line.strip()
                    if svc and svc not in cpp_services:
                        cpp_services.append(svc)
                        # Track enabled services separately
                        if "/S" in svc:
                            cpp_services_enabled.append(svc)

        # Check for installed C++ packages
        cpp_packages = []
        cmd = "opkg list-installed 2>/dev/null | grep -E 'yolo|detector|sensecraft|sscma' || true"
        result = await self._exec_cmd(client, cmd)
        if result and result.strip():
            for line in result.strip().split("\n"):
                parts = line.strip().split()
                if parts:
                    cpp_packages.append(parts[0])  # Full package name

        # Check for running C++ processes (use ps instead of pgrep for BusyBox compatibility)
        cmd = "ps aux 2>/dev/null | grep -v grep | grep -E 'yolo.*detector|sensecraft|sscma-cpp' && echo 'running' || true"
        result = await self._exec_cmd(client, cmd)
        cpp_processes_running = result and "running" in result

        # Check Node-RED enabled state (S* script exists)
        cmd = "ls /etc/init.d/S*node-red* 2>/dev/null && echo 'enabled' || true"
        result = await self._exec_cmd(client, cmd)
        nodered_enabled = result and "enabled" in result

        # Check Node-RED disabled state (K* script exists)
        cmd = "ls /etc/init.d/K*node-red* 2>/dev/null && echo 'disabled' || true"
        result = await self._exec_cmd(client, cmd)
        nodered_disabled = result and "disabled" in result

        # Check Node-RED running (use ps instead of pgrep for BusyBox compatibility)
        cmd = "ps aux 2>/dev/null | grep -v grep | grep node-red && echo 'running' || true"
        result = await self._exec_cmd(client, cmd)
        nodered_running = result and "running" in result

        # Determine mode
        # Only count enabled services (S*) as active, not disabled ones (K*)
        has_cpp = (
            bool(cpp_services_enabled) or bool(cpp_packages) or cpp_processes_running
        )
        has_nodered = nodered_running or nodered_enabled

        if has_cpp and has_nodered:
            mode = DeviceMode.MIXED
        elif has_cpp:
            mode = DeviceMode.CPP
        elif has_nodered:
            mode = DeviceMode.NODERED
        else:
            mode = DeviceMode.CLEAN

        return DeviceState(
            mode=mode,
            cpp_services=cpp_services,  # All scripts (for cleanup purposes)
            cpp_packages=cpp_packages,
            cpp_processes_running=cpp_processes_running,
            nodered_enabled=nodered_enabled,
            nodered_disabled=nodered_disabled,
            nodered_running=nodered_running,
        )

    async def _ensure_clean_state_for_nodered(
        self,
        client,
        state: DeviceState,
        password: str,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """Ensure device is ready for Node-RED deployment by cleaning up conflicts.

        Actions:
        - Stop C++ services
        - Disable C++ autostart (S* → K*)
        - Uninstall C++ packages
        - Restore Node-RED service (K* → S*)
        - Start Node-RED if not running
        """
        # Stop C++ services first
        if state.cpp_processes_running or state.cpp_services:
            logger.info("Stopping C++ services...")
            await self._report_progress(
                progress_callback, "prepare", 40, "Stopping C++ services..."
            )
            await self._stop_and_disable_cpp_services(client, password)
            await self._kill_cpp_processes(client, password)

        # Uninstall C++ packages
        if state.cpp_packages:
            logger.info(f"Uninstalling C++ packages: {state.cpp_packages}")
            await self._report_progress(
                progress_callback, "prepare", 50, "Removing C++ packages..."
            )

            for pkg in state.cpp_packages:
                cmd = _build_sudo_cmd(
                    password, f"opkg remove {shlex.quote(pkg)} 2>/dev/null || true"
                )
                await self._exec_cmd(client, cmd)

        # Restore Node-RED service if it was disabled
        if state.needs_nodered_restore:
            logger.info("Restoring Node-RED service...")
            await self._report_progress(
                progress_callback, "prepare", 70, "Restoring Node-RED service..."
            )
            await self._restore_nodered_services(client, password)

        # Start Node-RED if not running
        if not state.nodered_running:
            logger.info("Starting Node-RED service...")
            await self._report_progress(
                progress_callback, "prepare", 80, "Starting Node-RED..."
            )

            # Find and start Node-RED service
            start_script = """for svc in /etc/init.d/S*node-red*; do
    if [ -f "$svc" ]; then
        $svc start && echo "Started: $svc"
    fi
done"""
            cmd = (
                _build_sudo_cmd(password, f"sh -c {shlex.quote(start_script)}")
                + " 2>/dev/null || true"
            )
            result = await self._exec_cmd(client, cmd)
            if result and "Started:" in result:
                logger.info(result.strip())

            # Wait for Node-RED to start
            await asyncio.sleep(3)

        logger.info("Device cleanup completed, ready for Node-RED deployment")

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
            stop_cmd = (
                _build_sudo_cmd(password, f"sh -c {shlex.quote(stop_script)}")
                + " || true"
            )
            await self._exec_cmd(client, stop_cmd)

            # Rename S* to K* to disable auto-start
            disable_script = f"""for svc in /etc/init.d/S*{svc_name}*; do
    if [ -f "$svc" ]; then
        new_name=$(echo "$svc" | sed "s|/S|/K|")
        mv "$svc" "$new_name" 2>/dev/null && echo "Disabled: $svc -> $new_name"
    fi
done"""
            disable_cmd = (
                _build_sudo_cmd(password, f"sh -c {shlex.quote(disable_script)}")
                + " || true"
            )
            result = await self._exec_cmd(client, disable_cmd)
            if result and "Disabled:" in result:
                logger.info(result.strip())

        # Also scan for other custom S9* services and stop them
        scan_script = 'for f in /etc/init.d/S9*; do [ -f "$f" ] && basename "$f"; done'
        scan_cmd = (
            _build_sudo_cmd(password, f"sh -c {shlex.quote(scan_script)}")
            + " 2>/dev/null || true"
        )
        result = await self._exec_cmd(client, scan_cmd)
        if result:
            for svc in result.strip().split("\n"):
                svc = svc.strip()
                if not svc:
                    continue
                # Skip Node-RED related services
                if any(
                    nr in svc.lower()
                    for nr in ["node-red", "sscma-node", "sscma-supervisor"]
                ):
                    continue
                # Stop other S9* services
                cmd = _build_sudo_cmd(
                    password, f"/etc/init.d/{svc} stop 2>/dev/null || true"
                )
                await self._exec_cmd(client, cmd)

    async def _restore_nodered_services(
        self,
        client,
        password: str,
    ) -> None:
        """Restore Node-RED services that may have been disabled (K* → S*)."""
        for svc_name in NODERED_SERVICES:
            # Rename K* back to S* to enable auto-start
            restore_script = f"""for svc in /etc/init.d/K*{svc_name}*; do
    if [ -f "$svc" ]; then
        new_name=$(echo "$svc" | sed "s|/K|/S|")
        mv "$svc" "$new_name" 2>/dev/null && echo "Restored: $svc -> $new_name"
    fi
done"""
            restore_cmd = (
                _build_sudo_cmd(password, f"sh -c {shlex.quote(restore_script)}")
                + " || true"
            )
            result = await self._exec_cmd(client, restore_cmd)
            if result and "Restored:" in result:
                logger.info(result.strip())

    async def _kill_cpp_processes(
        self,
        client,
        password: str,
    ) -> None:
        """Kill any remaining C++ processes (use killall, no pkill on BusyBox)."""
        kill_cmds = [
            _build_sudo_cmd(password, "killall yolo11-detector 2>/dev/null || true"),
            _build_sudo_cmd(password, "killall yolo26-detector 2>/dev/null || true"),
            _build_sudo_cmd(password, "killall sensecraft 2>/dev/null || true"),
            _build_sudo_cmd(password, "killall sscma-cpp 2>/dev/null || true"),
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
