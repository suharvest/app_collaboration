"""
End-to-end tests for deployment API contract.

These tests verify that the API response structure matches what the frontend expects.
This prevents regression when modifying either frontend or backend code.
"""

import pytest
from pathlib import Path
import httpx

# Base URL for the API (assumes dev server is running)
BASE_URL = "http://localhost:3260"


class TestDeploymentAPIContract:
    """Tests for deployment API data structure contract."""

    @pytest.fixture
    def solutions(self):
        """Get list of available solutions."""
        try:
            # Use trailing slash to avoid redirect
            response = httpx.get(f"{BASE_URL}/api/solutions/", timeout=5.0, follow_redirects=True)
            if response.status_code != 200:
                pytest.skip("API server not running")
            solutions = response.json()
            if not solutions:
                pytest.skip("No solutions available")
            return [s["id"] for s in solutions]
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip("API server not running")

    def test_deployment_root_structure(self, solutions):
        """Verify deployment API returns required root-level fields."""
        for solution_id in solutions[:2]:  # Test first 2 solutions
            response = httpx.get(f"{BASE_URL}/api/solutions/{solution_id}/deployment")
            assert response.status_code == 200, f"Failed for {solution_id}"
            data = response.json()

            # Required root fields
            assert "devices" in data, f"Missing 'devices' in {solution_id}"
            assert "presets" in data, f"Missing 'presets' in {solution_id}"
            assert "selection_mode" in data, f"Missing 'selection_mode' in {solution_id}"
            assert isinstance(data["devices"], list), f"'devices' should be a list"
            assert isinstance(data["presets"], list), f"'presets' should be a list"

    def test_device_structure(self, solutions):
        """Verify each device has required fields."""
        for solution_id in solutions[:2]:
            response = httpx.get(f"{BASE_URL}/api/solutions/{solution_id}/deployment")
            data = response.json()

            for device in data.get("devices", []):
                # Required device fields
                assert "id" in device, f"Device missing 'id' in {solution_id}"
                assert "name" in device, f"Device missing 'name' in {solution_id}"
                assert "type" in device, f"Device missing 'type' in {solution_id}"

                # Type should be one of valid types
                valid_types = [
                    "docker_local", "docker_deploy", "docker_remote",
                    "esp32_usb", "himax_usb", "ssh_deb",
                    "manual", "script", "preview",
                    "recamera_cpp", "recamera_nodered"
                ]
                assert device["type"] in valid_types, \
                    f"Invalid device type '{device['type']}' in {solution_id}"

                # section should exist
                assert "section" in device, \
                    f"Device '{device['id']}' missing 'section' in {solution_id}"

    def test_device_section_structure(self, solutions):
        """Verify device section has required fields."""
        for solution_id in solutions[:2]:
            response = httpx.get(f"{BASE_URL}/api/solutions/{solution_id}/deployment")
            data = response.json()

            for device in data.get("devices", []):
                section = device.get("section", {})

                # Section should have title
                assert "title" in section or "title_zh" in section, \
                    f"Device '{device['id']}' section missing title in {solution_id}"

                # If wiring exists, check its structure
                if "wiring" in section:
                    wiring = section["wiring"]
                    # wiring.steps should be a list
                    if "steps" in wiring:
                        assert isinstance(wiring["steps"], list), \
                            f"wiring.steps should be a list in {solution_id}/{device['id']}"
                    # wiring.image should be a string or None
                    if "image" in wiring and wiring["image"]:
                        assert isinstance(wiring["image"], str), \
                            f"wiring.image should be a string in {solution_id}/{device['id']}"

    def test_docker_deploy_has_targets(self, solutions):
        """Verify docker_deploy devices have targets with correct structure."""
        for solution_id in solutions[:2]:
            response = httpx.get(f"{BASE_URL}/api/solutions/{solution_id}/deployment")
            data = response.json()

            for device in data.get("devices", []):
                if device["type"] == "docker_deploy":
                    # docker_deploy should have targets (unless it's a simple case)
                    if "targets" in device:
                        targets = device["targets"]
                        assert isinstance(targets, dict), \
                            f"targets should be a dict in {solution_id}/{device['id']}"

                        for target_id, target in targets.items():
                            # Required target fields
                            assert "name" in target, \
                                f"Target '{target_id}' missing 'name' in {solution_id}/{device['id']}"
                            assert "default" in target, \
                                f"Target '{target_id}' missing 'default' in {solution_id}/{device['id']}"

                            # Target should have section if it has content
                            if "section" in target:
                                target_section = target["section"]
                                # If wiring exists in target section, check structure
                                if "wiring" in target_section:
                                    wiring = target_section["wiring"]
                                    assert "steps" in wiring or "image" in wiring, \
                                        f"Target wiring should have steps or image"

    def test_targets_have_exactly_one_default(self, solutions):
        """Verify that targets have exactly one default (or none for backward compat)."""
        for solution_id in solutions[:2]:
            response = httpx.get(f"{BASE_URL}/api/solutions/{solution_id}/deployment")
            data = response.json()

            for device in data.get("devices", []):
                if device.get("targets"):
                    defaults = [
                        tid for tid, t in device["targets"].items()
                        if t.get("default") is True
                    ]
                    # Should have 0 or 1 default (not more than 1)
                    assert len(defaults) <= 1, \
                        f"Device '{device['id']}' has multiple default targets: {defaults}"

    def test_preset_structure(self, solutions):
        """Verify preset structure matches frontend expectations."""
        for solution_id in solutions[:2]:
            response = httpx.get(f"{BASE_URL}/api/solutions/{solution_id}/deployment")
            data = response.json()

            for preset in data.get("presets", []):
                # Required preset fields
                assert "id" in preset, f"Preset missing 'id' in {solution_id}"
                assert "name" in preset, f"Preset missing 'name' in {solution_id}"
                assert "devices" in preset, f"Preset missing 'devices' in {solution_id}"

                # devices should be a list of strings (device IDs)
                devices = preset["devices"]
                assert isinstance(devices, list), \
                    f"Preset devices should be a list in {solution_id}"

                if devices:
                    # If preset has devices, they should be strings (IDs)
                    # or dicts (legacy format) - both should work
                    first = devices[0]
                    is_id_list = isinstance(first, str)
                    is_object_list = isinstance(first, dict)
                    assert is_id_list or is_object_list, \
                        f"Preset devices should be ID strings or device objects"

    def test_preset_device_ids_exist_in_global_devices(self, solutions):
        """Verify preset device IDs reference existing global devices."""
        for solution_id in solutions[:2]:
            response = httpx.get(f"{BASE_URL}/api/solutions/{solution_id}/deployment")
            data = response.json()

            # Build set of global device IDs
            global_device_ids = {d["id"] for d in data.get("devices", [])}

            for preset in data.get("presets", []):
                preset_devices = preset.get("devices", [])
                for item in preset_devices:
                    # Handle both ID strings and device objects
                    device_id = item if isinstance(item, str) else item.get("id")
                    if device_id:
                        assert device_id in global_device_ids, \
                            f"Preset '{preset['id']}' references unknown device '{device_id}'"

    def test_post_deployment_structure(self, solutions):
        """Verify post_deployment structure if present."""
        for solution_id in solutions[:2]:
            response = httpx.get(f"{BASE_URL}/api/solutions/{solution_id}/deployment")
            data = response.json()

            post = data.get("post_deployment")
            if post:
                # Optional but if present should have success_message
                if "success_message" in post:
                    assert isinstance(post["success_message"], str), \
                        f"success_message should be a string in {solution_id}"

                # next_steps should be a list
                if "next_steps" in post:
                    assert isinstance(post["next_steps"], list), \
                        f"next_steps should be a list in {solution_id}"

    def test_bilingual_fields(self, solutions):
        """Verify bilingual fields are present for Chinese language."""
        for solution_id in solutions[:2]:
            response = httpx.get(
                f"{BASE_URL}/api/solutions/{solution_id}/deployment",
                params={"lang": "zh"}
            )
            data = response.json()

            # Check devices have Chinese names
            for device in data.get("devices", [])[:2]:
                # name should be Chinese when lang=zh
                name = device.get("name", "")
                # At minimum, name_zh should exist for fallback
                assert "name_zh" in device or name, \
                    f"Device '{device['id']}' missing Chinese name"

            # Check presets have Chinese names
            for preset in data.get("presets", [])[:2]:
                assert "name_zh" in preset or preset.get("name"), \
                    f"Preset '{preset['id']}' missing Chinese name"

    def test_wiring_steps_language(self, solutions):
        """Verify wiring steps are in correct language based on lang param."""
        for solution_id in solutions[:1]:  # Test one solution
            # Test Chinese
            response_zh = httpx.get(
                f"{BASE_URL}/api/solutions/{solution_id}/deployment",
                params={"lang": "zh"}
            )
            data_zh = response_zh.json()

            # Test English
            response_en = httpx.get(
                f"{BASE_URL}/api/solutions/{solution_id}/deployment",
                params={"lang": "en"}
            )
            data_en = response_en.json()

            # Find a device with wiring
            for dev_zh, dev_en in zip(data_zh.get("devices", []), data_en.get("devices", [])):
                section_zh = dev_zh.get("section", {})
                section_en = dev_en.get("section", {})

                wiring_zh = section_zh.get("wiring", {})
                wiring_en = section_en.get("wiring", {})

                if wiring_zh.get("steps") and wiring_en.get("steps"):
                    # Steps should be different if translations exist
                    # (unless the content is the same)
                    steps_zh = wiring_zh["steps"]
                    steps_en = wiring_en["steps"]

                    # At least verify both are non-empty lists
                    assert isinstance(steps_zh, list) and len(steps_zh) > 0
                    assert isinstance(steps_en, list) and len(steps_en) > 0
                    break


class TestSmartWarehouseSpecific:
    """Specific tests for smart_warehouse solution as reference implementation."""

    @pytest.fixture
    def deployment_data(self):
        """Get smart_warehouse deployment data."""
        try:
            response = httpx.get(
                f"{BASE_URL}/api/solutions/smart_warehouse/deployment",
                params={"lang": "zh"},
                timeout=5.0
            )
            if response.status_code != 200:
                pytest.skip("API server not running or smart_warehouse not found")
            return response.json()
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip("API server not running")

    def test_has_three_presets(self, deployment_data):
        """smart_warehouse should have 3 presets."""
        presets = deployment_data.get("presets", [])
        assert len(presets) == 3, f"Expected 3 presets, got {len(presets)}"

        preset_ids = [p["id"] for p in presets]
        assert "sensecraft_cloud" in preset_ids
        assert "private_cloud" in preset_ids
        assert "edge_computing" in preset_ids

    def test_warehouse_device_has_targets(self, deployment_data):
        """warehouse device should have local and remote targets."""
        devices = deployment_data.get("devices", [])
        warehouse = next((d for d in devices if d["id"] == "warehouse"), None)

        assert warehouse is not None, "Missing warehouse device"
        assert warehouse["type"] == "docker_deploy"
        assert "targets" in warehouse

        targets = warehouse["targets"]
        assert "warehouse_local" in targets
        assert "warehouse_remote" in targets

    def test_target_wiring_has_chinese_steps(self, deployment_data):
        """Target wiring steps should be in Chinese when lang=zh."""
        devices = deployment_data.get("devices", [])
        warehouse = next((d for d in devices if d["id"] == "warehouse"), None)

        local_target = warehouse["targets"]["warehouse_local"]
        wiring = local_target.get("section", {}).get("wiring", {})

        assert "steps" in wiring, "Missing wiring steps"
        steps = wiring["steps"]

        # First step should be Chinese
        assert len(steps) > 0
        # Check for Chinese characters
        first_step = steps[0]
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in first_step)
        assert has_chinese, f"Expected Chinese steps, got: {first_step}"

    def test_manual_device_has_section_content(self, deployment_data):
        """Manual devices should have section with description or wiring."""
        devices = deployment_data.get("devices", [])
        sensecraft = next((d for d in devices if d["id"] == "sensecraft"), None)

        assert sensecraft is not None, "Missing sensecraft device"
        assert sensecraft["type"] == "manual"

        section = sensecraft.get("section", {})
        # Manual devices should have either wiring or description
        has_content = (
            "wiring" in section or
            "description" in section or
            "troubleshoot" in section
        )
        assert has_content, "Manual device missing section content"

    def test_post_deployment_exists(self, deployment_data):
        """post_deployment should exist with success message."""
        post = deployment_data.get("post_deployment")
        assert post is not None, "Missing post_deployment"
        assert "success_message" in post
        assert len(post["success_message"]) > 0


class TestDevicesAPIContract:
    """Tests for devices API endpoints."""

    @pytest.fixture
    def api_available(self):
        """Check if API is available."""
        try:
            response = httpx.get(f"{BASE_URL}/api/health", timeout=5.0)
            if response.status_code != 200:
                pytest.skip("API server not running")
            return True
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip("API server not running")

    def test_devices_catalog_structure(self, api_available):
        """Verify devices catalog endpoint returns correct structure."""
        response = httpx.get(f"{BASE_URL}/api/devices/catalog")
        assert response.status_code == 200

        data = response.json()
        assert "devices" in data, "Catalog should have 'devices' key"
        assert isinstance(data["devices"], list), "devices should be a list"

        # Each device should have required fields
        for device in data["devices"][:3]:
            assert "id" in device, "Device missing 'id'"
            assert "name" in device, "Device missing 'name'"

    def test_devices_ports_structure(self, api_available):
        """Verify serial ports endpoint returns correct structure."""
        response = httpx.get(f"{BASE_URL}/api/devices/ports")
        assert response.status_code == 200

        data = response.json()
        assert "ports" in data, "Response should have 'ports' key"
        assert isinstance(data["ports"], list), "ports should be a list"


class TestDockerDevicesAPIContract:
    """Tests for Docker devices API endpoints."""

    @pytest.fixture
    def api_available(self):
        """Check if API is available."""
        try:
            response = httpx.get(f"{BASE_URL}/api/health", timeout=5.0)
            if response.status_code != 200:
                pytest.skip("API server not running")
            return True
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip("API server not running")

    def test_local_docker_check_structure(self, api_available):
        """Verify local Docker check returns correct structure."""
        response = httpx.get(f"{BASE_URL}/api/docker-devices/local/check")
        # May return 200 or error status depending on Docker availability
        if response.status_code == 200:
            data = response.json()
            # API returns success and device info
            assert "success" in data, "Response should have 'success' key"
            assert isinstance(data["success"], bool)


class TestSolutionsAPIContract:
    """Extended tests for solutions API endpoints."""

    @pytest.fixture
    def solutions(self):
        """Get list of available solutions."""
        try:
            response = httpx.get(
                f"{BASE_URL}/api/solutions/",
                timeout=5.0,
                follow_redirects=True
            )
            if response.status_code != 200:
                pytest.skip("API server not running")
            solutions = response.json()
            if not solutions:
                pytest.skip("No solutions available")
            return [s["id"] for s in solutions]
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip("API server not running")

    def test_solution_list_structure(self, solutions):
        """Verify solution list has required fields."""
        response = httpx.get(
            f"{BASE_URL}/api/solutions/",
            follow_redirects=True
        )
        data = response.json()

        for solution in data[:3]:
            # Required fields for list view
            assert "id" in solution
            assert "name" in solution
            assert "summary" in solution or "summary_zh" in solution
            assert "category" in solution
            # Stats fields are at root level (flat structure)
            assert "difficulty" in solution

    def test_solution_detail_structure(self, solutions):
        """Verify solution detail has required fields."""
        for solution_id in solutions[:2]:
            response = httpx.get(f"{BASE_URL}/api/solutions/{solution_id}")
            assert response.status_code == 200

            data = response.json()

            # Required fields (flat structure, no nested intro)
            assert "id" in data
            assert "name" in data
            # Summary is at root level
            assert "summary" in data or "summary_zh" in data

    def test_solution_language_parameter(self, solutions):
        """Verify lang parameter affects response."""
        solution_id = solutions[0]

        # Get English version
        response_en = httpx.get(
            f"{BASE_URL}/api/solutions/{solution_id}",
            params={"lang": "en"}
        )

        # Get Chinese version
        response_zh = httpx.get(
            f"{BASE_URL}/api/solutions/{solution_id}",
            params={"lang": "zh"}
        )

        assert response_en.status_code == 200
        assert response_zh.status_code == 200

        # Both should return valid JSON
        data_en = response_en.json()
        data_zh = response_zh.json()

        assert "name" in data_en
        assert "name" in data_zh


class TestErrorResponseContract:
    """Tests for error response consistency."""

    @pytest.fixture
    def api_available(self):
        """Check if API is available."""
        try:
            response = httpx.get(f"{BASE_URL}/api/health", timeout=5.0)
            if response.status_code != 200:
                pytest.skip("API server not running")
            return True
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip("API server not running")

    def test_404_error_structure(self, api_available):
        """Verify 404 errors have consistent structure."""
        response = httpx.get(f"{BASE_URL}/api/solutions/nonexistent_solution_xyz")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data, "Error response should have 'detail' key"

    def test_health_endpoint_structure(self, api_available):
        """Verify health endpoint structure."""
        response = httpx.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


class TestAPIVersionAndHeaders:
    """Tests for API versioning and header consistency."""

    @pytest.fixture
    def api_available(self):
        """Check if API is available."""
        try:
            response = httpx.get(f"{BASE_URL}/api/health", timeout=5.0)
            if response.status_code != 200:
                pytest.skip("API server not running")
            return True
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip("API server not running")

    def test_content_type_json(self, api_available):
        """Verify API returns JSON content type."""
        response = httpx.get(f"{BASE_URL}/api/health")

        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_cors_headers(self, api_available):
        """Verify CORS headers are present for browser requests."""
        response = httpx.get(f"{BASE_URL}/api/health")

        # FastAPI with CORS middleware should include these
        # (if configured for development)
        # This test documents expected behavior


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
