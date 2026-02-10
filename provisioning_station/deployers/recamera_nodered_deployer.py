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
import shutil
import subprocess
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..models.device import DeviceConfig, NodeRedModuleConfig
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


DEFAULT_SSCMA_CLIENT_ID = "d4edfe2d22b78af8"


class ReCameraNodeRedDeployer(NodeRedDeployer):
    """Deploy Node-RED flows to reCamera via Admin HTTP API.

    This deployer extends the base NodeRedDeployer with reCamera-specific
    functionality:
    - Stops and disables conflicting C++ services before deployment
    - Restores and enables Node-RED related services
    - Updates InfluxDB configuration in the flow
    - Sets InfluxDB credentials via Node-RED API
    - Template variable replacement ({{influxdb_host}}, {{sscma_client_id}})
    """

    _sscma_client_id: str = DEFAULT_SSCMA_CLIENT_ID

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

                # Step 3: Sync device clock if needed
                # reCamera via USB has no internet → NTP fails → clock stuck at 1970
                # InfluxDB rejects writes outside its retention window
                await self._sync_device_clock(client, ssh_password, progress_callback)

                await self._report_progress(
                    progress_callback, "prepare", 90, "Device ready for Node-RED"
                )

            finally:
                client.close()

        except ImportError:
            logger.warning("paramiko not available, skipping service management")
        except Exception as e:
            logger.warning(f"Service management failed (non-fatal): {e}")

        # Discover SSCMA client ID from current flows
        await self._discover_sscma_client_id(config, connection)

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

    async def _sync_device_clock(
        self,
        client,
        password: str,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """Sync device clock from host machine if device time is stale.

        reCamera connected via USB has no internet, so NTP cannot sync.
        The clock may be stuck at 1970-01-01 (epoch). InfluxDB rejects
        writes with timestamps outside its retention window (e.g. 7 days),
        so we must fix the clock before deploying flows that write data.

        Uses the host machine's UTC time as the reference.
        """
        import datetime

        # Read device's current year
        result = await self._exec_cmd(client, "date +%Y")
        if not result:
            return

        try:
            device_year = int(result.strip())
        except ValueError:
            return

        current_year = datetime.datetime.now(datetime.timezone.utc).year

        if device_year >= current_year - 1:
            # Clock is reasonably current (within 1 year), skip sync
            logger.info(f"Device clock OK (year={device_year})")
            return

        # Device clock is stale — sync from host
        await self._report_progress(
            progress_callback,
            "prepare",
            85,
            f"Syncing device clock (stuck at {device_year})...",
        )

        utc_now = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cmd = _build_sudo_cmd(password, f"date -s {shlex.quote(utc_now)}")
        result = await self._exec_cmd(client, cmd)
        if result:
            logger.info(f"Device clock synced to: {utc_now} UTC")
        else:
            logger.warning("Failed to sync device clock")

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

    async def _discover_sscma_client_id(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
    ) -> None:
        """Discover the SSCMA config node ID from the current Node-RED flows.

        The SSCMA config node (type "sscma") is created by the reCamera system
        and has a unique ID. Our flow template references it via {{sscma_client_id}}.
        """
        recamera_ip = connection.get("recamera_ip")
        if not recamera_ip:
            return

        nodered_port = config.nodered.port if config.nodered else 1880
        flows = await self.get_current_flows(recamera_ip, nodered_port)
        if not flows:
            logger.info(
                f"Could not fetch current flows, using default SSCMA client ID: "
                f"{self._sscma_client_id}"
            )
            return

        for node in flows:
            if node.get("type") == "sscma":
                self._sscma_client_id = node["id"]
                logger.info(f"Discovered SSCMA client ID: {self._sscma_client_id}")
                return

        logger.info(
            f"No SSCMA config node found in current flows, "
            f"using default: {self._sscma_client_id}"
        )

    async def _update_flow_config(
        self,
        flow_data: List[Dict],
        config: DeviceConfig,
        connection: Dict[str, Any],
    ) -> tuple[List[Dict], Dict[str, Dict]]:
        """Update flow configuration with template variables and InfluxDB settings.

        Template variables replaced in JSON text:
        - {{influxdb_host}}: InfluxDB server IP
        - {{sscma_client_id}}: SSCMA config node ID (discovered or default)

        Expected connection parameters:
        - influxdb_url: InfluxDB URL (e.g., "http://192.168.1.100:8086")
        - influxdb_token: InfluxDB API Token
        - influxdb_org: InfluxDB Organization
        - influxdb_bucket: InfluxDB Bucket name
        """
        import json

        nodered_config = config.nodered
        credentials = {}

        # Get InfluxDB parameters from config (YAML fixed values) + connection (user input)
        influxdb_cfg = config.influxdb or {}
        influxdb_host = connection.get("influxdb_host", "")
        influxdb_port = influxdb_cfg.get("port", 8086)
        influxdb_token = influxdb_cfg.get("token") or connection.get("influxdb_token")
        influxdb_org = influxdb_cfg.get("org") or connection.get(
            "influxdb_org", "seeed"
        )
        influxdb_bucket = influxdb_cfg.get("bucket") or connection.get(
            "influxdb_bucket", "recamera"
        )
        influxdb_url = connection.get("influxdb_url")
        if not influxdb_url and influxdb_host:
            influxdb_url = f"http://{influxdb_host}:{influxdb_port}"

        # Step 1: Template variable replacement on serialized JSON
        flow_text = json.dumps(flow_data)
        if influxdb_host:
            flow_text = flow_text.replace("{{influxdb_host}}", influxdb_host)
        flow_text = flow_text.replace("{{sscma_client_id}}", self._sscma_client_id)
        flow_data = json.loads(flow_text)

        # Step 2: Structured InfluxDB config node updates
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

    # --- Module proxy install / offline fallback hooks ---

    @asynccontextmanager
    async def _ssh_connect(self, connection: Dict[str, Any]):
        """Create a temporary SSH connection from connection parameters."""
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        recamera_ip = connection.get("recamera_ip")
        await asyncio.to_thread(
            client.connect,
            hostname=recamera_ip,
            port=connection.get("ssh_port", 22),
            username=connection.get("ssh_username", "recamera"),
            password=connection.get("ssh_password"),
            timeout=10,
        )
        try:
            yield client
        finally:
            client.close()

    async def _proxy_install_module(
        self,
        module: NodeRedModuleConfig,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback=None,
    ) -> bool:
        """Download module on local machine, then SCP to reCamera.

        Steps:
        1. npm install in a temp dir on the local machine
        2. Check for native dependencies (binding.gyp) — abort if found
        3. tar + SCP to device ~/.node-red/
        4. Extract and update package.json on device
        """
        recamera_ip = connection.get("recamera_ip")
        ssh_password = connection.get("ssh_password")
        if not recamera_ip or not ssh_password:
            logger.warning("Proxy install: missing SSH credentials")
            return False

        # Check npm is available locally
        if not shutil.which("npm"):
            logger.warning("Proxy install: npm not found on local machine")
            return False

        tmpdir = None
        try:
            tmpdir = tempfile.mkdtemp(prefix="nodered-proxy-")
            pkg_spec = (
                f"{module.name}@{module.version}" if module.version else module.name
            )

            # Step 1: npm install locally
            logger.info(f"Proxy: downloading {pkg_spec} on local machine...")
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "npm",
                    "install",
                    pkg_spec,
                    "--production",
                    "--ignore-scripts",
                    "--no-optional",
                ],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.warning(
                    f"Proxy: npm install failed for {pkg_spec}: {result.stderr[:300]}"
                )
                return False

            node_modules = Path(tmpdir) / "node_modules"
            if not node_modules.exists():
                logger.warning("Proxy: node_modules not created after npm install")
                return False

            # Step 2: Check for native dependencies (binding.gyp)
            binding_files = list(node_modules.rglob("binding.gyp"))
            if binding_files:
                logger.warning(
                    f"Module {module.name} has native dependencies "
                    f"({len(binding_files)} binding.gyp found), "
                    f"cannot proxy install for different architecture"
                )
                return False

            # Step 3: Create tarball
            tarball = Path(tmpdir) / "module.tar.gz"
            tar_result = await asyncio.to_thread(
                subprocess.run,
                ["tar", "czf", str(tarball), "-C", str(tmpdir), "node_modules"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if tar_result.returncode != 0:
                logger.warning(f"Proxy: tar failed: {tar_result.stderr[:200]}")
                return False

            # Step 4: SCP to device + extract into userDir
            return await self._push_tarball_to_device(
                tarball, module, connection, progress_callback
            )

        except subprocess.TimeoutExpired:
            logger.warning(f"Proxy: npm install timed out for {module.name}")
            return False
        except Exception as e:
            logger.warning(f"Proxy install failed for {module.name}: {e}")
            return False
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)

    async def _install_from_offline_package(
        self,
        module: NodeRedModuleConfig,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback=None,
    ) -> bool:
        """Install module from a pre-packaged offline tarball."""
        if not connection.get("ssh_password"):
            return False

        tarball_path = config.get_asset_path(module.offline_package)
        if not tarball_path or not Path(tarball_path).exists():
            logger.warning(f"Offline package not found: {module.offline_package}")
            return False

        return await self._push_tarball_to_device(
            Path(tarball_path), module, connection, progress_callback
        )

    async def _push_tarball_to_device(
        self,
        tarball: Path,
        module: NodeRedModuleConfig,
        connection: Dict[str, Any],
        progress_callback=None,
    ) -> bool:
        """SCP a tarball to device and extract into Node-RED userDir (~/.node-red/).

        Also updates ~/.node-red/package.json to register the module so
        Node-RED loads it on restart.
        """
        remote_tmp = "/tmp/_nodered_module.tar.gz"
        # Node-RED userDir — owned by recamera user, no sudo needed
        nodered_user_dir = "$HOME/.node-red"

        try:
            async with self._ssh_connect(connection) as client:
                # SCP upload
                sftp = await asyncio.to_thread(client.open_sftp)
                try:
                    await asyncio.to_thread(sftp.put, str(tarball), remote_tmp)
                finally:
                    sftp.close()

                logger.info(
                    f"Tarball uploaded to device ({tarball.stat().st_size} bytes)"
                )

                # Extract into userDir (no sudo needed, owned by recamera)
                extract_cmd = f"tar xzf {remote_tmp} -C {nodered_user_dir}"
                result = await self._exec_cmd(client, extract_cmd, timeout=60)

                # Update package.json to register the module
                version_spec = f"~{module.version}" if module.version else "*"
                update_pkg_script = (
                    f"cd {nodered_user_dir} && "
                    f'python3 -c "'
                    f"import json; "
                    f"p = json.load(open('package.json')); "
                    f"p.setdefault('dependencies', dict())"
                    f"['{module.name}'] = '{version_spec}'; "
                    f"json.dump(p, open('package.json', 'w'), indent=2)"
                    f'" 2>/dev/null || '
                    # Fallback: use sed if python3 not available
                    f'sed -i \'"dependencies":/a\\    "{module.name}": "{version_spec}",\' '
                    f"{nodered_user_dir}/package.json"
                )
                await self._exec_cmd(client, update_pkg_script, timeout=10)

                # Verify extraction
                check_cmd = (
                    f"ls {nodered_user_dir}/node_modules/{module.name}/package.json "
                    f"2>/dev/null && echo 'EXTRACTED_OK'"
                )
                check_result = await self._exec_cmd(client, check_cmd)
                if check_result and "EXTRACTED_OK" in check_result:
                    logger.info(f"Module {module.name} extracted to device userDir")
                else:
                    logger.warning(
                        f"Module {module.name} extraction could not be verified"
                    )

                # Clean up remote tarball
                await self._exec_cmd(client, f"rm -f {remote_tmp}")
                return True

        except Exception as e:
            logger.warning(f"Push tarball to device failed: {e}")
            return False

    async def _restart_nodered_service(
        self,
        config=None,
        connection=None,
        progress_callback=None,
    ) -> bool:
        """Restart Node-RED on reCamera by killing the process.

        The init script (S03node-red) will auto-restart it.
        Node-RED runs as the 'recamera' user, so no sudo needed.
        """
        if not connection:
            return False

        try:
            async with self._ssh_connect(connection) as client:
                # Kill node-red process — init script auto-restarts it
                kill_cmd = "kill $(pidof node-red) 2>/dev/null && echo 'KILLED'"
                result = await self._exec_cmd(client, kill_cmd, timeout=10)
                if result and "KILLED" in result:
                    logger.info("Node-RED process killed, waiting for auto-restart...")
                    # Wait for init script to respawn and Node-RED to begin startup.
                    # On memory-constrained devices (180MB), startup can be slow.
                    await asyncio.sleep(10)
                    return True
                else:
                    logger.warning("Could not find node-red process to kill")
                    return False
        except Exception as e:
            logger.warning(f"Node-RED restart failed: {e}")
            return False

    async def get_current_flows(
        self,
        recamera_ip: str,
        port: int = 1880,
    ) -> Optional[List[Dict]]:
        """Get current flows from reCamera Node-RED (for backup/reference)"""
        return await super().get_current_flows(recamera_ip, port)
