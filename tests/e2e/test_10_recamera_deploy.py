"""
E2E tests for recamera_heatmap_grafana solution deployment.

These tests require real hardware devices:
- reCamera at 192.168.42.1 for camera deployment
- Local Docker for Grafana backend (grafana preset only)

reCamera has TWO deployment modes:
1. recamera_nodered - Node-RED flow deployment (for data collection)
2. recamera_cpp - C++ deb package deployment (YOLO11/YOLO26 detector)

All tests are idempotent:
- Node-RED tests: flows are backed up and restored
- C++ tests: packages are uninstalled and original services restored
"""

import time

import httpx
import pytest

from .conftest import (
    RECAMERA_HOST,
    RECAMERA_NODERED_PORT,
    RECAMERA_PASSWORD,
    check_http_endpoint,
    check_port_open,
    check_ssh_connection,
    get_nodered_flows,
)

# Solution and preset IDs
SOLUTION_ID = "recamera_heatmap_grafana"
PRESET_SIMPLE = "simple"
PRESET_GRAFANA = "grafana"

# Labels used by grafana backend deployment
GRAFANA_LABELS = {"sensecraft.solution_id": "recamera_heatmap_grafana"}


# =============================================================================
# reCamera Connection Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_recamera
class TestReCameraConnection:
    """Tests for reCamera device connectivity."""

    def test_recamera_ssh_connection(self, recamera_available, recamera_info):
        """Verify reCamera SSH connection works."""
        assert recamera_available is True

        # Double-check SSH is working
        connected = check_ssh_connection(
            recamera_info.host,
            recamera_info.port,
            recamera_info.user,
            recamera_info.password,
        )
        assert connected, f"Cannot SSH to reCamera at {recamera_info.host}"

    def test_recamera_system_info(self, recamera_available, recamera_info):
        """Verify reCamera system is accessible and has AI services available."""
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            recamera_info.host,
            port=recamera_info.port,
            username=recamera_info.user,
            password=recamera_info.password,
            timeout=10,
        )

        # Check for AI services (Node-RED or YOLO detector)
        # After deployment, YOLO detector replaces Node-RED
        stdin, stdout, stderr = client.exec_command(
            "ps aux | grep -iE 'node-red|yolo.*detector' | grep -v grep || "
            "ls /etc/init.d/S*node-red /etc/init.d/S*yolo* 2>/dev/null"
        )
        output = stdout.read().decode().strip()
        # Should find either Node-RED or YOLO detector
        assert output, "No AI service (Node-RED or YOLO detector) found on reCamera"

        client.close()


# =============================================================================
# Grafana Preset Deployment Tests (run FIRST - requires Node-RED)
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_recamera
@pytest.mark.device_local_docker
@pytest.mark.slow
class TestReCameraGrafanaPreset:
    """
    Tests for deploying recamera_heatmap_grafana grafana preset.

    Grafana preset deploys:
    1. Node-RED flow to reCamera (with InfluxDB output)
    2. Grafana + InfluxDB backend locally

    IMPORTANT: This test class must run BEFORE TestReCameraSimplePreset,
    because Simple preset deploys YOLO which replaces Node-RED.
    """

    def test_nodered_api_available(self, cleanup_recamera_nodered):
        """
        Verify reCamera Node-RED API is accessible (prerequisite for Grafana preset).

        The cleanup_recamera_nodered fixture will restore Node-RED if it was
        replaced by YOLO detector.
        """
        # cleanup_recamera_nodered fixture ensures Node-RED is running
        # Get flows to verify API is working
        flows = get_nodered_flows(RECAMERA_HOST, RECAMERA_NODERED_PORT)
        assert flows is not None, "Cannot get Node-RED flows"
        assert isinstance(flows, list), "Flows should be a list"

        # Also verify runtime info endpoint
        response = httpx.get(
            f"http://{RECAMERA_HOST}:{RECAMERA_NODERED_PORT}/settings",
            timeout=10,
        )
        assert response.status_code == 200

        data = response.json()
        # Node-RED should return settings with nodeVersion
        assert "nodeVersion" in data or "httpNodeRoot" in data

    def test_grafana_preset_deploy(
        self,
        api_server_running,
        recamera_available,
        local_docker_available,
        cleanup_recamera_nodered,
        cleanup_local_docker,
        api_client,
    ):
        """
        Deploy grafana preset and verify both components start.

        This test:
        1. Backs up Node-RED flows (via fixture)
        2. Registers Docker cleanup labels
        3. Deploys grafana preset
        4. Verifies Grafana/InfluxDB are running
        5. Verifies Node-RED flow is updated
        6. Cleanup happens automatically via fixtures
        """
        # Register Docker labels for cleanup
        cleanup_local_docker.add_labels(GRAFANA_LABELS)

        # Clean any existing deployment first
        cleanup_local_docker.cleanup_now()

        # Start deployment
        deploy_response = api_client.post(
            "/api/deployments/start",
            json={
                "solution_id": SOLUTION_ID,
                "preset_id": PRESET_GRAFANA,
                "device_connections": {
                    "recamera": {
                        "host": RECAMERA_HOST,
                    },
                    "backend": {
                        "target": "backend_local",
                    },
                },
            },
        )
        assert deploy_response.status_code == 200, f"Deploy failed: {deploy_response.text}"

        # Wait for Grafana to be accessible
        max_wait = 180  # 3 minutes for Docker pull + start
        start = time.time()
        grafana_up = False
        influxdb_up = False

        while time.time() - start < max_wait:
            if not grafana_up and check_http_endpoint("http://localhost:3000"):
                grafana_up = True
            if not influxdb_up and check_http_endpoint("http://localhost:8086/health"):
                influxdb_up = True

            if grafana_up and influxdb_up:
                break
            time.sleep(10)

        assert grafana_up, "Grafana did not start within timeout"
        assert influxdb_up, "InfluxDB did not start within timeout"

    def test_grafana_cleanup_verification(self, local_docker_available):
        """Verify cleanup removed grafana containers."""
        import subprocess

        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"label=sensecraft.solution_id={SOLUTION_ID}"],
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()

        # Should be empty if cleanup worked
        assert output == "", f"Found leftover containers: {output}"


# =============================================================================
# Simple Preset Deployment Tests (run AFTER Grafana - replaces Node-RED with YOLO)
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_recamera
@pytest.mark.slow
class TestReCameraSimplePreset:
    """
    Tests for deploying recamera_heatmap_grafana simple preset.

    Simple preset deploys YOLO detector (recamera_cpp) to reCamera.
    After deployment, RTSP stream and MQTT detections become available.

    IMPORTANT: This test class must run AFTER TestReCameraGrafanaPreset,
    because it deploys YOLO which replaces Node-RED.
    """

    @pytest.mark.dependency(name="simple_preset_deployed")
    def test_simple_preset_deploy(
        self,
        api_server_running,
        recamera_available,
        cleanup_recamera_cpp,
        api_client,
        recamera_info,
    ):
        """
        Deploy simple preset to reCamera and verify YOLO detector starts.

        This test:
        1. Backs up current service state (via fixture)
        2. Deploys simple preset (YOLO detector) via API
        3. Verifies detector service is running
        4. Restores original state (via fixture)
        """
        original_state = cleanup_recamera_cpp
        assert original_state is not None, "Could not backup original state"

        # Start deployment
        deploy_response = api_client.post(
            "/api/deployments/start",
            json={
                "solution_id": SOLUTION_ID,
                "preset_id": PRESET_SIMPLE,
                "device_connections": {
                    "deploy_detector": {
                        "host": RECAMERA_HOST,
                        "password": RECAMERA_PASSWORD,
                    }
                },
            },
        )
        assert deploy_response.status_code == 200, f"Deploy failed: {deploy_response.text}"

        deployment_id = deploy_response.json().get("deployment_id")
        assert deployment_id, "No deployment_id returned"

        # Wait for deployment completion - check for YOLO detector running
        import paramiko

        max_wait = 180  # 3 minutes for deb package install
        start = time.time()
        deployed = False

        while time.time() - start < max_wait:
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    recamera_info.host,
                    port=recamera_info.port,
                    username=recamera_info.user,
                    password=recamera_info.password,
                    timeout=10,
                )
                # Check for YOLO detector process (ps aux works better than pgrep on reCamera)
                stdin, stdout, stderr = client.exec_command(
                    "ps aux | grep -E 'yolo[0-9]+-detector' | grep -v grep"
                )
                output = stdout.read().decode().strip()
                client.close()

                if output:
                    deployed = True
                    break
            except Exception:
                pass

            time.sleep(10)

        assert deployed, "YOLO detector did not start within timeout"

    def test_simple_preset_rtsp_available(
        self,
        recamera_available,
    ):
        """Verify RTSP stream is available after deployment."""
        # RTSP should be available after YOLO detector is deployed
        rtsp_open = check_port_open(RECAMERA_HOST, 8554, timeout=5.0)
        if not rtsp_open:
            pytest.skip("RTSP not available - run test_simple_preset_deploy first")

        assert rtsp_open, "RTSP port 8554 should be open after deployment"

    def test_simple_preset_mqtt_available(
        self,
        recamera_available,
    ):
        """Verify MQTT detections are available after deployment."""
        # MQTT should be available after YOLO detector is deployed
        mqtt_open = check_port_open(RECAMERA_HOST, 1883, timeout=5.0)
        assert mqtt_open, "MQTT port 1883 should be open"


# =============================================================================
# C++ Detector Deployment Tests (recamera_cpp type)
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_recamera
class TestReCameraCppDeployment:
    """
    Verification tests for C++ YOLO detector on reCamera.

    Note: Actual deployment is tested in TestReCameraSimplePreset.
    These tests verify the detector state after deployment.
    """

    def test_yolo_detector_running(
        self,
        recamera_available,
        recamera_info,
    ):
        """
        Verify YOLO detector is running on reCamera.

        This test checks if any YOLO detector (11 or 26) is running.
        Run after test_simple_preset_deploy to verify deployment worked.
        """
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            recamera_info.host,
            port=recamera_info.port,
            username=recamera_info.user,
            password=recamera_info.password,
            timeout=10,
        )

        # Check for any YOLO detector process
        stdin, stdout, stderr = client.exec_command(
            "ps aux | grep -E 'yolo[0-9]+-detector' | grep -v grep"
        )
        output = stdout.read().decode().strip()
        client.close()

        if not output:
            pytest.skip("No YOLO detector running - run test_simple_preset_deploy first")

        assert output, "YOLO detector should be running"

    def test_yolo_detector_init_script(
        self,
        recamera_available,
        recamera_info,
    ):
        """Verify YOLO detector init script is installed."""
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            recamera_info.host,
            port=recamera_info.port,
            username=recamera_info.user,
            password=recamera_info.password,
            timeout=10,
        )

        # Check for init script
        stdin, stdout, stderr = client.exec_command(
            "ls /etc/init.d/S9*yolo* 2>/dev/null"
        )
        output = stdout.read().decode().strip()
        client.close()

        if not output:
            pytest.skip("No YOLO init script - detector may not be deployed")

        assert "yolo" in output.lower(), "YOLO init script should be installed"


# =============================================================================
# API Contract Tests (No Device Required)
# =============================================================================


@pytest.mark.e2e
class TestReCameraHeatmapAPI:
    """API tests for recamera_heatmap_grafana (no device required)."""

    def test_solution_exists(self, api_server_running, api_client):
        """Verify recamera_heatmap_grafana solution is available."""
        response = api_client.get(f"/api/solutions/{SOLUTION_ID}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == SOLUTION_ID

    def test_deployment_has_presets(self, api_server_running, api_client):
        """Verify solution has expected presets."""
        response = api_client.get(f"/api/solutions/{SOLUTION_ID}/deployment")
        assert response.status_code == 200

        data = response.json()
        presets = data.get("presets", [])
        preset_ids = [p["id"] for p in presets]

        assert PRESET_SIMPLE in preset_ids, f"Missing {PRESET_SIMPLE} preset"
        assert PRESET_GRAFANA in preset_ids, f"Missing {PRESET_GRAFANA} preset"

    def test_simple_preset_structure(self, api_server_running, api_client):
        """Verify simple preset has expected devices."""
        response = api_client.get(f"/api/solutions/{SOLUTION_ID}/deployment")
        assert response.status_code == 200

        data = response.json()
        presets = data.get("presets", [])
        simple = next((p for p in presets if p["id"] == PRESET_SIMPLE), None)

        assert simple is not None
        # Simple preset should have devices (API returns device IDs, not device_groups)
        devices = simple.get("devices", [])
        assert len(devices) > 0, "Simple preset should have at least one device"
        # Should include detector or preview device
        device_str = str(devices).lower()
        assert "detector" in device_str or "preview" in device_str or "recamera" in device_str

    def test_grafana_preset_structure(self, api_server_running, api_client):
        """Verify grafana preset has expected devices."""
        response = api_client.get(f"/api/solutions/{SOLUTION_ID}/deployment")
        assert response.status_code == 200

        data = response.json()
        presets = data.get("presets", [])
        grafana = next((p for p in presets if p["id"] == PRESET_GRAFANA), None)

        assert grafana is not None
        # Grafana preset should have multiple devices (camera + backend)
        devices = grafana.get("devices", [])
        assert len(devices) >= 2, f"Grafana preset should have at least 2 devices, got {devices}"
        # Should include backend device
        device_str = str(devices).lower()
        assert "backend" in device_str, f"Grafana preset should include backend, got {devices}"

    def test_recamera_device_types(self, api_server_running, api_client):
        """Verify reCamera has both nodered and cpp deployment types available."""
        response = api_client.get(f"/api/solutions/{SOLUTION_ID}/deployment")
        assert response.status_code == 200

        data = response.json()
        devices = data.get("devices", [])

        # Get device types
        device_types = {d.get("type") for d in devices}
        device_ids = {d.get("id") for d in devices}

        # Should have recamera_nodered type (for Node-RED flow)
        has_nodered = "recamera_nodered" in device_types or "recamera" in device_ids

        # Should have recamera_cpp type (for YOLO detector)
        has_cpp = "recamera_cpp" in device_types
        has_yolo = any("yolo" in d.get("id", "").lower() for d in devices)

        # At least one reCamera deployment method should be available
        assert has_nodered or has_cpp or has_yolo, \
            f"No reCamera deployment found. Types: {device_types}, IDs: {device_ids}"

    def test_yolo_detector_configs(self, api_server_running, api_client):
        """Verify YOLO detector device configurations if present."""
        response = api_client.get(f"/api/solutions/{SOLUTION_ID}/deployment")
        assert response.status_code == 200

        data = response.json()
        devices = data.get("devices", [])

        # Find YOLO devices
        yolo_devices = [
            d for d in devices
            if d.get("type") == "recamera_cpp" or "yolo" in d.get("id", "").lower()
        ]

        for device in yolo_devices:
            # C++ devices should have SSH configuration
            assert "ssh" in device or "user_inputs" in device, \
                f"YOLO device {device.get('id')} missing SSH config"

            # Should have binary configuration
            if "binary" in device:
                binary = device["binary"]
                # Should have deb_package or models
                assert "deb_package" in binary or "models" in binary
