"""
E2E test fixtures for device deployment testing.

These fixtures check device availability and provide helpers for deployment testing.
All tests must be idempotent - devices should be restored to original state after tests.
"""

import asyncio
import json
import socket
import subprocess
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, Callable

import httpx
import pytest
import websockets

# =============================================================================
# Device Configuration
# =============================================================================

# API server
API_BASE_URL = "http://localhost:3260"

# R1100 configuration
R1100_HOST = "192.168.10.76"
R1100_USER = "recomputer"
R1100_PASSWORD = "seeed"
R1100_SSH_PORT = 22

# reCamera configuration
RECAMERA_HOST = "192.168.42.1"
RECAMERA_PASSWORD = "recamera.1"
RECAMERA_SSH_PORT = 22
RECAMERA_NODERED_PORT = 1880

# Deployment timeouts
DEPLOYMENT_TIMEOUT = 300  # 5 minutes max for deployment


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DeviceInfo:
    """Device connection information."""

    host: str
    port: int
    user: str | None = None
    password: str | None = None


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""

    success: bool
    device_id: str
    messages: list[dict]
    error: str | None = None


# =============================================================================
# Helper Functions
# =============================================================================


def check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_ssh_connection(host: str, port: int, user: str, password: str) -> bool:
    """Check if SSH connection is possible using paramiko."""
    try:
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=port, username=user, password=password, timeout=5)
        client.close()
        return True
    except Exception:
        return False


def check_http_endpoint(url: str, timeout: float = 5.0) -> bool:
    """Check if an HTTP endpoint is reachable."""
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code < 500
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def check_docker_available() -> bool:
    """Check if Docker is available locally."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# =============================================================================
# Cleanup Helpers
# =============================================================================


def cleanup_docker_containers(
    labels: dict[str, str], host: str | None = None, ssh_info: DeviceInfo | None = None
) -> None:
    """
    Remove Docker containers matching the given labels.

    Args:
        labels: Dict of label key-value pairs to match
        host: If None, cleanup locally. Otherwise cleanup on remote host.
        ssh_info: SSH connection info for remote cleanup
    """
    label_filters = " ".join([f'-f "label={k}={v}"' for k, v in labels.items()])

    if host is None:
        # Local cleanup (use xargs without -r for macOS compatibility)
        cmd = f"docker ps -aq {label_filters} | xargs docker rm -f 2>/dev/null || true"
        subprocess.run(cmd, shell=True, capture_output=True)
    else:
        # Remote cleanup via SSH
        if ssh_info:
            import paramiko

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    ssh_info.host,
                    port=ssh_info.port,
                    username=ssh_info.user,
                    password=ssh_info.password,
                    timeout=10,
                )
                cmd = f"docker ps -aq {label_filters} | xargs docker rm -f 2>/dev/null || true"
                client.exec_command(cmd)
                client.close()
            except Exception:
                pass


def get_nodered_flows(host: str, port: int = 1880) -> list[dict] | None:
    """Get current Node-RED flows for backup."""
    try:
        response = httpx.get(f"http://{host}:{port}/flows", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def restore_nodered_flows(host: str, flows: list[dict], port: int = 1880) -> bool:
    """Restore Node-RED flows from backup."""
    try:
        response = httpx.post(
            f"http://{host}:{port}/flows",
            json=flows,
            headers={"Content-Type": "application/json", "Node-RED-Deployment-Type": "full"},
            timeout=30,
        )
        return response.status_code == 204
    except Exception:
        return False


def get_recamera_service_state(host: str, user: str, password: str) -> dict | None:
    """
    Get current service state on reCamera for backup.

    Returns dict with running services and installed packages.
    """
    try:
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=22, username=user, password=password, timeout=10)

        state = {
            "running_services": [],
            "installed_packages": [],
        }

        # Get running services (check S* scripts in /etc/init.d)
        stdin, stdout, stderr = client.exec_command(
            "ls /etc/init.d/S* 2>/dev/null | xargs -I {} basename {}"
        )
        services = stdout.read().decode().strip().split("\n")
        state["running_services"] = [s for s in services if s]

        # Check if yolo detector packages are installed
        for pkg in ["yolo11-detector", "yolo26-detector"]:
            stdin, stdout, stderr = client.exec_command(f"opkg list-installed | grep {pkg}")
            if stdout.read().decode().strip():
                state["installed_packages"].append(pkg)

        client.close()
        return state
    except Exception:
        return None


def restore_recamera_service_state(
    host: str, user: str, password: str, original_state: dict
) -> bool:
    """
    Restore reCamera to original service state.

    This removes any yolo detector packages that weren't originally installed
    and restores original services.
    """
    try:
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=22, username=user, password=password, timeout=10)

        original_packages = set(original_state.get("installed_packages", []))

        # Remove packages that weren't originally installed
        for pkg in ["yolo11-detector", "yolo26-detector"]:
            if pkg not in original_packages:
                # Stop service first
                client.exec_command(f"/etc/init.d/S92{pkg.replace('-', '_')} stop 2>/dev/null")
                # Remove package
                client.exec_command(f"opkg remove {pkg} 2>/dev/null")

        # Restore original services (re-enable disabled services)
        original_services = set(original_state.get("running_services", []))
        for service in ["S03node-red", "S91sscma-node", "S93sscma-supervisor"]:
            if service in original_services:
                # Check if it was renamed to K*
                k_service = service.replace("S", "K", 1)
                stdin, stdout, stderr = client.exec_command(
                    f"test -f /etc/init.d/{k_service} && "
                    f"mv /etc/init.d/{k_service} /etc/init.d/{service}"
                )
                # Start the service
                client.exec_command(f"/etc/init.d/{service} start 2>/dev/null")

        client.close()
        return True
    except Exception:
        return False


# =============================================================================
# API Server Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def api_server_running() -> bool:
    """Check if the API server is running. Skip test if not."""
    if not check_http_endpoint(f"{API_BASE_URL}/api/health"):
        pytest.skip("API server not running at localhost:3260")
    return True


@pytest.fixture
def api_client(api_server_running) -> httpx.Client:
    """Create an HTTP client for API calls."""
    with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
        yield client


# =============================================================================
# Device Availability Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def watcher_available() -> bool:
    """Check if SenseCAP Watcher is connected via USB."""
    # Check for Watcher USB device (typically shows as /dev/ttyACM* or /dev/ttyUSB*)
    try:
        result = subprocess.run(
            ["ls", "/dev/ttyACM0"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass

    # Also check via API
    try:
        response = httpx.get(f"{API_BASE_URL}/api/devices/ports", timeout=5)
        if response.status_code == 200:
            ports = response.json().get("ports", [])
            # Look for Watcher-like devices
            for port in ports:
                if "ACM" in port.get("device", "") or "Watcher" in port.get("description", ""):
                    return True
    except Exception:
        pass

    pytest.skip("SenseCAP Watcher not connected via USB")


@pytest.fixture(scope="session")
def recamera_available() -> bool:
    """Check if reCamera is reachable at 192.168.42.1."""
    if not check_port_open(RECAMERA_HOST, RECAMERA_SSH_PORT):
        pytest.skip(f"reCamera not reachable at {RECAMERA_HOST}")

    # Try 'recamera' user first (for recamera_cpp), then 'root' (for recamera_nodered)
    if not check_ssh_connection(
        RECAMERA_HOST, RECAMERA_SSH_PORT, "recamera", RECAMERA_PASSWORD
    ):
        if not check_ssh_connection(
            RECAMERA_HOST, RECAMERA_SSH_PORT, "root", RECAMERA_PASSWORD
        ):
            pytest.skip(f"Cannot SSH to reCamera at {RECAMERA_HOST}")

    return True


@pytest.fixture(scope="session")
def recamera_nodered_available(recamera_available) -> bool:
    """Check if reCamera Node-RED API is available."""
    if not check_http_endpoint(f"http://{RECAMERA_HOST}:{RECAMERA_NODERED_PORT}/flows"):
        pytest.skip(f"reCamera Node-RED not available at {RECAMERA_HOST}:{RECAMERA_NODERED_PORT}")
    return True


@pytest.fixture(scope="session")
def r1100_available() -> bool:
    """Check if R1100 is reachable at 192.168.10.76."""
    if not check_port_open(R1100_HOST, R1100_SSH_PORT):
        pytest.skip(f"R1100 not reachable at {R1100_HOST}")

    if not check_ssh_connection(R1100_HOST, R1100_SSH_PORT, R1100_USER, R1100_PASSWORD):
        pytest.skip(f"Cannot SSH to R1100 at {R1100_HOST}")

    return True


@pytest.fixture(scope="session")
def local_docker_available() -> bool:
    """Check if local Docker is available."""
    if not check_docker_available():
        pytest.skip("Local Docker not available")
    return True


# =============================================================================
# Cleanup Fixtures (ensure idempotency)
# =============================================================================


@pytest.fixture
def cleanup_local_docker():
    """
    Fixture that provides cleanup function and auto-cleans after test.

    Usage:
        def test_something(cleanup_local_docker):
            cleanup_local_docker.add_labels({"sensecraft.solution": "smart_warehouse"})
            # ... run deployment ...
            # Cleanup happens automatically after test
    """

    class DockerCleanup:
        def __init__(self):
            self.label_sets: list[dict[str, str]] = []

        def add_labels(self, labels: dict[str, str]):
            """Register labels to clean up after test."""
            self.label_sets.append(labels)

        def cleanup_now(self):
            """Force cleanup immediately."""
            for labels in self.label_sets:
                cleanup_docker_containers(labels)

    cleanup = DockerCleanup()
    yield cleanup

    # Auto cleanup after test
    cleanup.cleanup_now()


@pytest.fixture
def cleanup_r1100_docker(r1100_available):
    """
    Fixture that provides cleanup function for R1100 Docker containers.
    """
    ssh_info = DeviceInfo(
        host=R1100_HOST,
        port=R1100_SSH_PORT,
        user=R1100_USER,
        password=R1100_PASSWORD,
    )

    class R1100DockerCleanup:
        def __init__(self):
            self.label_sets: list[dict[str, str]] = []

        def add_labels(self, labels: dict[str, str]):
            """Register labels to clean up after test."""
            self.label_sets.append(labels)

        def cleanup_now(self):
            """Force cleanup immediately."""
            for labels in self.label_sets:
                cleanup_docker_containers(labels, host=R1100_HOST, ssh_info=ssh_info)

    cleanup = R1100DockerCleanup()
    yield cleanup

    # Auto cleanup after test
    cleanup.cleanup_now()


def restore_nodered_if_needed(host: str, user: str, password: str) -> bool:
    """
    Restore Node-RED service if it was replaced by YOLO detector.

    Returns True if Node-RED is available after restoration attempt.
    """
    import time

    try:
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=22, username=user, password=password, timeout=10)

        # Check if Node-RED is running
        stdin, stdout, stderr = client.exec_command(
            "ps aux | grep -v grep | grep node-red"
        )
        if stdout.read().decode().strip():
            client.close()
            return True  # Already running

        # Check if YOLO is running (need to stop it first)
        stdin, stdout, stderr = client.exec_command(
            "ps aux | grep -v grep | grep -E 'yolo[0-9]+-detector'"
        )
        yolo_running = bool(stdout.read().decode().strip())

        if yolo_running:
            # Kill YOLO processes
            stdin, stdout, stderr = client.exec_command(
                f"echo '{password}' | sudo -S killall yolo11-detector 2>/dev/null || true"
            )
            stdout.channel.recv_exit_status()
            stdin, stdout, stderr = client.exec_command(
                f"echo '{password}' | sudo -S killall yolo26-detector 2>/dev/null || true"
            )
            stdout.channel.recv_exit_status()

        # Start Node-RED directly
        stdin, stdout, stderr = client.exec_command(
            f"echo '{password}' | sudo -S /etc/init.d/S03node-red start 2>/dev/null || "
            f"echo '{password}' | sudo -S /etc/init.d/S*node-red* start 2>/dev/null || true"
        )
        stdout.channel.recv_exit_status()

        client.close()

        # Wait for Node-RED to fully start (it needs time to initialize)
        max_wait = 30
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if check_http_endpoint(f"http://{host}:{RECAMERA_NODERED_PORT}/flows"):
                return True
            time.sleep(2)

        return False

    except Exception as e:
        print(f"Failed to restore Node-RED: {e}")
        return False


@pytest.fixture
def cleanup_recamera_nodered(recamera_available):
    """
    Fixture that backs up and restores Node-RED flows.

    If Node-RED was replaced by YOLO, this fixture will restore it first.
    Ensures idempotency by restoring original flows after test.
    """
    # First, ensure Node-RED is available (restore if needed)
    nodered_ready = restore_nodered_if_needed(
        RECAMERA_HOST, "recamera", RECAMERA_PASSWORD
    )

    if not nodered_ready:
        pytest.skip("Cannot restore Node-RED on reCamera")

    # Backup current flows before test
    original_flows = get_nodered_flows(RECAMERA_HOST, RECAMERA_NODERED_PORT)

    yield original_flows

    # Restore original flows after test
    if original_flows is not None:
        restore_nodered_flows(RECAMERA_HOST, original_flows, RECAMERA_NODERED_PORT)


@pytest.fixture
def cleanup_recamera_cpp(recamera_available, recamera_info):
    """
    Fixture that backs up and restores reCamera service state for C++ deployments.

    Ensures idempotency by:
    1. Recording original service state before test
    2. Removing any installed yolo detector packages after test
    3. Restoring original services (node-red, sscma-node, etc.)
    """
    # Backup current service state before test
    original_state = get_recamera_service_state(
        recamera_info.host,
        recamera_info.user,
        recamera_info.password,
    )

    yield original_state

    # Restore original state after test
    if original_state is not None:
        restore_recamera_service_state(
            recamera_info.host,
            recamera_info.user,
            recamera_info.password,
            original_state,
        )


# =============================================================================
# WebSocket Helpers
# =============================================================================


@pytest.fixture
def websocket_client_factory():
    """Factory fixture for creating WebSocket connections to deployment endpoint."""

    @asynccontextmanager
    async def create_websocket(deployment_id: str) -> AsyncGenerator[websockets.WebSocketClientProtocol, None]:
        ws_url = f"ws://localhost:3260/ws/deployments/{deployment_id}"
        async with websockets.connect(ws_url) as ws:
            yield ws

    return create_websocket


@pytest.fixture
def deployment_waiter(websocket_client_factory):
    """
    Helper fixture for waiting on deployment completion via WebSocket.

    Returns a function that starts a deployment and waits for completion.
    """

    async def wait_for_deployment(
        api_client: httpx.Client,
        solution_id: str,
        preset_id: str,
        device_configs: dict,
        timeout: float = DEPLOYMENT_TIMEOUT,
    ) -> DeploymentResult:
        """
        Start a deployment and wait for completion via WebSocket.

        Args:
            api_client: HTTP client for API calls
            solution_id: Solution ID to deploy
            preset_id: Preset ID to use
            device_configs: Device configuration dict
            timeout: Max wait time in seconds

        Returns:
            DeploymentResult with success status and messages
        """
        # Start deployment
        response = api_client.post(
            "/api/deployments/start",
            json={
                "solution_id": solution_id,
                "preset_id": preset_id,
                "devices": device_configs,
            },
        )

        if response.status_code != 200:
            return DeploymentResult(
                success=False,
                device_id="",
                messages=[],
                error=f"Failed to start deployment: {response.text}",
            )

        data = response.json()
        deployment_id = data.get("deployment_id")

        if not deployment_id:
            return DeploymentResult(
                success=False,
                device_id="",
                messages=[],
                error="No deployment_id in response",
            )

        # Connect to WebSocket and wait for completion
        messages = []
        success = False
        error = None

        try:
            async with websocket_client_factory(deployment_id) as ws:
                start_time = asyncio.get_event_loop().time()

                while True:
                    # Check timeout
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        error = "Deployment timeout"
                        break

                    try:
                        msg_text = await asyncio.wait_for(ws.recv(), timeout=30)
                        msg = json.loads(msg_text)
                        messages.append(msg)

                        # Check for completion
                        if msg.get("type") == "deployment_completed":
                            success = msg.get("status") == "completed"
                            if not success:
                                error = msg.get("message", "Deployment failed")
                            break

                    except asyncio.TimeoutError:
                        # No message received, continue waiting
                        continue

        except Exception as e:
            error = str(e)

        return DeploymentResult(
            success=success,
            device_id=device_configs.get("device_id", ""),
            messages=messages,
            error=error,
        )

    return wait_for_deployment


# =============================================================================
# Device Info Fixtures
# =============================================================================


@pytest.fixture
def r1100_info() -> DeviceInfo:
    """R1100 connection information."""
    return DeviceInfo(
        host=R1100_HOST,
        port=R1100_SSH_PORT,
        user=R1100_USER,
        password=R1100_PASSWORD,
    )


@pytest.fixture
def recamera_info() -> DeviceInfo:
    """reCamera connection information (uses 'recamera' user for cpp deployments)."""
    return DeviceInfo(
        host=RECAMERA_HOST,
        port=RECAMERA_SSH_PORT,
        user="recamera",  # recamera_cpp uses 'recamera' user, not root
        password=RECAMERA_PASSWORD,
    )
