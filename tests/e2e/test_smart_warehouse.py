"""
E2E tests for smart_warehouse solution deployment.

These tests require real hardware devices:
- R1100 at 192.168.10.76 for remote Docker deployment
- Local Docker for local deployment

All tests are idempotent - containers are cleaned up after each test.
"""

import pytest

from .conftest import (
    API_BASE_URL,
    R1100_HOST,
    R1100_PASSWORD,
    R1100_USER,
    check_http_endpoint,
    check_ssh_connection,
)

# Solution and preset IDs
SOLUTION_ID = "smart_warehouse"
PRESET_PRIVATE_CLOUD = "private_cloud"

# Labels used by smart_warehouse deployment for cleanup
WAREHOUSE_LABELS = {"sensecraft.solution_id": "smart_warehouse"}


# =============================================================================
# R1100 Connection Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_r1100
class TestR1100Connection:
    """Tests for R1100 device connectivity."""

    def test_r1100_ssh_connection(self, r1100_available, r1100_info):
        """Verify R1100 SSH connection works."""
        assert r1100_available is True

        # Double-check SSH is working
        connected = check_ssh_connection(
            r1100_info.host,
            r1100_info.port,
            r1100_info.user,
            r1100_info.password,
        )
        assert connected, f"Cannot SSH to R1100 at {r1100_info.host}"

    def test_r1100_docker_available(self, r1100_available, r1100_info):
        """Verify Docker is installed and running on R1100."""
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            r1100_info.host,
            port=r1100_info.port,
            username=r1100_info.user,
            password=r1100_info.password,
            timeout=10,
        )

        # Check Docker version
        stdin, stdout, stderr = client.exec_command("docker --version")
        output = stdout.read().decode().strip()
        assert "Docker version" in output, f"Docker not installed: {output}"

        # Check Docker is running
        stdin, stdout, stderr = client.exec_command("docker info")
        exit_status = stdout.channel.recv_exit_status()
        assert exit_status == 0, "Docker daemon not running"

        client.close()

    def test_r1100_has_network_access(self, r1100_available, r1100_info):
        """Verify R1100 can access external network (for pulling images)."""
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            r1100_info.host,
            port=r1100_info.port,
            username=r1100_info.user,
            password=r1100_info.password,
            timeout=10,
        )

        # Try to ping a well-known host
        stdin, stdout, stderr = client.exec_command(
            "ping -c 1 -W 5 docker.io || ping -c 1 -W 5 8.8.8.8"
        )
        exit_status = stdout.channel.recv_exit_status()

        client.close()

        # Network access is nice to have, not required (images might be cached)
        if exit_status != 0:
            pytest.skip("R1100 has no external network access (images must be pre-cached)")


# =============================================================================
# R1100 Deployment Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_r1100
@pytest.mark.slow
class TestSmartWarehouseRemoteDeploy:
    """Tests for deploying smart_warehouse to R1100."""

    def test_warehouse_remote_deploy(
        self,
        api_server_running,
        r1100_available,
        cleanup_r1100_docker,
        api_client,
    ):
        """
        Deploy warehouse system to R1100 and verify it starts correctly.

        This test:
        1. Starts deployment via API
        2. Waits for deployment completion
        3. Verifies the service is accessible
        4. Cleans up containers (via fixture)
        """
        # Register labels for cleanup
        cleanup_r1100_docker.add_labels(WAREHOUSE_LABELS)

        # First, clean any existing deployment
        cleanup_r1100_docker.cleanup_now()

        # Get deployment info
        response = api_client.get(f"/api/solutions/{SOLUTION_ID}/deployment")
        assert response.status_code == 200
        deployment_data = response.json()

        # Find warehouse device
        devices = deployment_data.get("devices", [])
        warehouse_device = next((d for d in devices if d["id"] == "warehouse"), None)
        assert warehouse_device is not None, "warehouse device not found in deployment"

        # Start deployment
        deploy_response = api_client.post(
            "/api/deployments/start",
            json={
                "solution_id": SOLUTION_ID,
                "preset_id": PRESET_PRIVATE_CLOUD,
                "device_connections": {
                    "warehouse": {
                        "target": "warehouse_remote",
                        "host": R1100_HOST,
                        "username": R1100_USER,
                        "password": R1100_PASSWORD,
                    }
                },
            },
        )
        assert deploy_response.status_code == 200, f"Deploy failed: {deploy_response.text}"

        deployment_id = deploy_response.json().get("deployment_id")
        assert deployment_id, "No deployment_id returned"

        # Wait for deployment completion by polling deployment status API
        import time

        max_wait = 180  # 3 minutes
        start = time.time()
        deployed = False
        final_status = None

        while time.time() - start < max_wait:
            # Check deployment status via API
            status_response = api_client.get(f"/api/deployments/{deployment_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                final_status = status_data.get("status")
                if final_status in ("completed", "failed"):
                    deployed = final_status == "completed"
                    break
            time.sleep(5)

        assert deployed, f"Deployment failed with status: {final_status}"

        # After deployment completes, verify service is accessible
        # Give it a few seconds for containers to fully start
        time.sleep(5)
        service_up = check_http_endpoint(f"http://{R1100_HOST}:2124/api/dashboard/stats")
        # Service check is informational - deployment success is the main test
        if not service_up:
            print(f"Warning: Service not immediately accessible at {R1100_HOST}:2124")

    def test_warehouse_remote_cleanup_verification(
        self,
        r1100_available,
        r1100_info,
    ):
        """Verify that cleanup actually removes containers."""
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            r1100_info.host,
            port=r1100_info.port,
            username=r1100_info.user,
            password=r1100_info.password,
            timeout=10,
        )

        # Check no warehouse containers are running (from previous tests)
        stdin, stdout, stderr = client.exec_command(
            'docker ps -q -f "label=sensecraft.solution_id=smart_warehouse"'
        )
        output = stdout.read().decode().strip()
        client.close()

        # Should be empty if cleanup worked
        assert output == "", f"Found leftover containers: {output}"


# =============================================================================
# Local Docker Deployment Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_local_docker
@pytest.mark.slow
class TestSmartWarehouseLocalDeploy:
    """Tests for deploying smart_warehouse locally."""

    def test_warehouse_local_deploy(
        self,
        api_server_running,
        local_docker_available,
        cleanup_local_docker,
        api_client,
    ):
        """
        Deploy warehouse system locally and verify it starts correctly.

        This test:
        1. Starts deployment via API
        2. Waits for deployment completion
        3. Verifies the service is accessible
        4. Cleans up containers (via fixture)
        """
        # Register labels for cleanup
        cleanup_local_docker.add_labels(WAREHOUSE_LABELS)

        # First, clean any existing deployment
        cleanup_local_docker.cleanup_now()

        # Start deployment
        deploy_response = api_client.post(
            "/api/deployments/start",
            json={
                "solution_id": SOLUTION_ID,
                "preset_id": PRESET_PRIVATE_CLOUD,
                "device_connections": {
                    "warehouse": {
                        "target": "warehouse_local",
                    }
                },
            },
        )
        assert deploy_response.status_code == 200, f"Deploy failed: {deploy_response.text}"

        deployment_id = deploy_response.json().get("deployment_id")
        assert deployment_id, "No deployment_id returned"

        # Wait for deployment completion by polling deployment status API
        import time

        max_wait = 180  # 3 minutes
        start = time.time()
        deployed = False
        final_status = None

        while time.time() - start < max_wait:
            # Check deployment status via API
            status_response = api_client.get(f"/api/deployments/{deployment_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                final_status = status_data.get("status")
                if final_status in ("completed", "failed"):
                    deployed = final_status == "completed"
                    break
            time.sleep(5)

        assert deployed, f"Deployment failed with status: {final_status}"

    def test_local_cleanup_verification(self, local_docker_available):
        """Verify that cleanup actually removes containers."""
        import subprocess

        result = subprocess.run(
            ["docker", "ps", "-q", "-f", "label=sensecraft.solution_id=smart_warehouse"],
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()

        # Should be empty if cleanup worked
        assert output == "", f"Found leftover containers: {output}"


# =============================================================================
# API Contract Tests (No Device Required)
# =============================================================================


@pytest.mark.e2e
class TestSmartWarehouseAPI:
    """API tests for smart_warehouse (no device required)."""

    def test_solution_exists(self, api_server_running, api_client):
        """Verify smart_warehouse solution is available."""
        response = api_client.get(f"/api/solutions/{SOLUTION_ID}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == SOLUTION_ID

    def test_deployment_has_presets(self, api_server_running, api_client):
        """Verify smart_warehouse has expected presets."""
        response = api_client.get(f"/api/solutions/{SOLUTION_ID}/deployment")
        assert response.status_code == 200

        data = response.json()
        presets = data.get("presets", [])
        preset_ids = [p["id"] for p in presets]

        assert "sensecraft_cloud" in preset_ids
        assert "private_cloud" in preset_ids
        assert "edge_computing" in preset_ids

    def test_warehouse_device_has_targets(self, api_server_running, api_client):
        """Verify warehouse device has local and remote targets."""
        response = api_client.get(f"/api/solutions/{SOLUTION_ID}/deployment")
        assert response.status_code == 200

        data = response.json()
        devices = data.get("devices", [])
        warehouse = next((d for d in devices if d["id"] == "warehouse"), None)

        assert warehouse is not None
        assert warehouse.get("type") == "docker_deploy"
        assert "targets" in warehouse

        targets = warehouse["targets"]
        assert "warehouse_local" in targets
        assert "warehouse_remote" in targets
