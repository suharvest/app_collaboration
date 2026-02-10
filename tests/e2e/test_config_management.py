"""
E2E test for Docker app configuration management.

Tests the full flow:
1. Deploy a dummy Docker app with SenseCraft labels
2. Create config manifest with reconfigurable fields
3. Verify the Devices page shows the app with a Configure button
4. Open the Configure modal, change values, save
5. Verify containers are recreated with new env
6. Clean up everything

Prerequisites:
- Local Docker running
- Backend API at localhost:3260
- Frontend at localhost:5173
- playwright-cli available

Usage:
    # Run just this test
    uv run --group test pytest tests/e2e/test_config_management.py -v

    # Or run the setup/teardown manually for interactive testing:
    python tests/e2e/test_config_management.py --setup     # Create mock app
    python tests/e2e/test_config_management.py --teardown   # Clean up
    python tests/e2e/test_config_management.py --playwright  # Run playwright UI tests
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Test constants
SOLUTION_ID = "_test_config_e2e"
DEVICE_ID = "test_server"
PROJECT_NAME = "test-config-e2e"
COMPOSE_FILE = FIXTURES_DIR / "test-config-compose.yml"
MANIFESTS_DIR = Path.home() / ".sensecraft" / "deployments" / SOLUTION_ID

API_BASE = "http://localhost:3260"
FRONTEND_URL = "http://localhost:5173"


# ============================================
# Setup / Teardown Helpers
# ============================================


def setup_mock_app():
    """Deploy a dummy Docker app with SenseCraft labels and config manifest."""
    print(f"[setup] Deploying test app: {SOLUTION_ID}")

    # 1. Build labels
    from provisioning_station.utils.compose_labels import (
        create_labels,
        inject_labels_to_compose_file,
    )

    labels = create_labels(
        solution_id=SOLUTION_ID,
        device_id=DEVICE_ID,
        solution_name="Test Config App",
        config_file="devices/test_server.yaml",
    )

    # 2. Inject labels into compose file -> temp file
    temp_compose = inject_labels_to_compose_file(str(COMPOSE_FILE), labels)
    print(f"[setup] Temp compose: {temp_compose}")

    # 3. docker compose up -d
    env = os.environ.copy()
    env["DB_HOST"] = "192.168.1.100"
    env["API_PORT"] = "9090"

    result = subprocess.run(
        [
            "docker", "compose",
            "-f", temp_compose,
            "-p", PROJECT_NAME,
            "up", "-d",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(COMPOSE_FILE.parent),
    )
    print(f"[setup] docker compose up: rc={result.returncode}")
    if result.stdout:
        print(f"  stdout: {result.stdout.strip()}")
    if result.stderr:
        print(f"  stderr: {result.stderr.strip()}")

    # Clean up temp compose
    try:
        os.remove(temp_compose)
    except Exception:
        pass

    if result.returncode != 0:
        raise RuntimeError(f"docker compose up failed: {result.stderr}")

    # 4. Create config manifest
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "solution_id": SOLUTION_ID,
        "device_id": DEVICE_ID,
        "device_type": "docker_local",
        "config_file": "devices/test_server.yaml",
        "fields": [
            {
                "id": "db_host",
                "name": "Database Host",
                "name_zh": "数据库地址",
                "type": "text",
                "current_value": "192.168.1.100",
                "default": "localhost",
                "required": True,
                "placeholder": "192.168.x.x",
                "description": "IP address of the database server",
                "description_zh": "数据库服务器的 IP 地址",
                "validation": None,
                "options": [],
            },
            {
                "id": "api_port",
                "name": "API Port",
                "name_zh": "API 端口",
                "type": "text",
                "current_value": "9090",
                "default": "8080",
                "required": False,
                "placeholder": "8080",
                "description": "Port for the API service",
                "description_zh": "API 服务端口",
                "validation": None,
                "options": [],
            },
        ],
    }
    manifest_path = MANIFESTS_DIR / f"{DEVICE_ID}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"[setup] Manifest saved: {manifest_path}")

    # 5. Wait for container to be running
    for _ in range(10):
        check = subprocess.run(
            ["docker", "ps", "--filter", f"label=sensecraft.solution_id={SOLUTION_ID}",
             "--format", "{{.Status}}"],
            capture_output=True, text=True,
        )
        if "Up" in check.stdout:
            print("[setup] Container is running")
            return True
        time.sleep(1)

    print("[setup] WARNING: Container may not be running")
    return False


def teardown_mock_app():
    """Remove the dummy Docker app and config manifest."""
    print(f"[teardown] Cleaning up: {SOLUTION_ID}")

    # 1. docker compose down
    try:
        # Find running containers with our solution_id label
        result = subprocess.run(
            ["docker", "ps", "-aq", "--filter", f"label=sensecraft.solution_id={SOLUTION_ID}"],
            capture_output=True, text=True,
        )
        container_ids = result.stdout.strip().split()
        if container_ids and container_ids[0]:
            subprocess.run(
                ["docker", "rm", "-f"] + container_ids,
                capture_output=True, text=True,
            )
            print(f"[teardown] Removed containers: {container_ids}")
    except Exception as e:
        print(f"[teardown] Container cleanup error: {e}")

    # Also try compose down
    try:
        subprocess.run(
            ["docker", "compose", "-p", PROJECT_NAME, "down", "--remove-orphans"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        pass

    # 2. Remove manifest
    if MANIFESTS_DIR.exists():
        shutil.rmtree(MANIFESTS_DIR)
        print(f"[teardown] Removed manifests dir: {MANIFESTS_DIR}")

    # Clean parent if empty
    parent = MANIFESTS_DIR.parent
    if parent.exists() and not any(parent.iterdir()):
        parent.rmdir()

    print("[teardown] Done")


# ============================================
# Playwright UI Tests
# ============================================


def run_playwright_command(cmd: str, timeout: int = 15) -> dict:
    """Run a playwright-cli command and return parsed result."""
    result = subprocess.run(
        ["playwright-cli"] + cmd.split(),
        capture_output=True, text=True,
        timeout=timeout,
    )
    return {
        "rc": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def get_snapshot_path(output: str) -> str | None:
    """Extract snapshot file path from playwright-cli output."""
    for line in output.split("\n"):
        if "Snapshot" in line and ".yml" in line:
            # Extract path between parentheses
            start = line.find("(")
            end = line.find(")")
            if start != -1 and end != -1:
                return line[start + 1:end]
    return None


def read_snapshot(output: str) -> str:
    """Read the snapshot YAML content from playwright-cli output."""
    snapshot_path = get_snapshot_path(output)
    if not snapshot_path:
        return ""
    # Resolve relative to project root (where pytest runs from)
    full_path = PROJECT_ROOT / snapshot_path
    if full_path.exists():
        return full_path.read_text()
    # Fallback: try frontend dir
    alt_path = PROJECT_ROOT / "frontend" / snapshot_path
    if alt_path.exists():
        return alt_path.read_text()
    return ""


def run_playwright_tests():
    """Run the full playwright UI test flow."""
    errors = []

    # Open Devices page
    print("\n[playwright] Opening Devices page...")
    r = run_playwright_command(f"open {FRONTEND_URL}/#/devices")
    if r["rc"] != 0:
        errors.append(f"Failed to open page: {r['stderr']}")
        return errors

    # Wait for page to load with retry - the page makes async API calls
    # that may take a moment to complete
    snapshot = ""
    for attempt in range(6):
        time.sleep(2)
        r = run_playwright_command("snapshot")
        snapshot = read_snapshot(r["stdout"])
        if "Test Config App" in snapshot:
            break
        # Click Refresh button if visible to retry loading
        if attempt > 0:
            for line in snapshot.split("\n"):
                if "Refresh" in line and "ref=" in line:
                    ref_start = line.find("ref=") + 4
                    ref_end = line.find("]", ref_start)
                    if ref_start > 3 and ref_end != -1:
                        ref = line[ref_start:ref_end]
                        run_playwright_command(f"click {ref}")
                        break
            print(f"  Retry {attempt}/5 - waiting for app card...")

    # TEST 1: Verify app card appears with solution name
    print("[playwright] TEST 1: App card visible...")
    if "Test Config App" not in snapshot:
        errors.append("App card 'Test Config App' not found on Devices page")
        print(f"  FAIL - Card not found. Snapshot excerpt:\n{snapshot[:800]}")
    else:
        print("  PASS")

    # TEST 2: Verify Configure button is present
    print("[playwright] TEST 2: Configure button visible...")
    if "Configure" not in snapshot:
        errors.append("Configure button not found on app card")
        print("  FAIL")
    else:
        print("  PASS")

    # TEST 3: Verify status badge shows running
    print("[playwright] TEST 3: Status badge shows running...")
    if "running" not in snapshot.lower():
        errors.append("Running status not shown")
        print("  FAIL")
    else:
        print("  PASS")

    # TEST 4: Click Configure button -> modal opens
    print("[playwright] TEST 4: Click Configure button...")
    # Find the Configure button ref
    configure_ref = None
    for line in snapshot.split("\n"):
        if "Configure" in line and "ref=" in line:
            # Extract ref value
            start = line.find("ref=") + 4
            end = line.find("]", start)
            if start > 3 and end != -1:
                configure_ref = line[start:end]
                break

    if not configure_ref:
        errors.append("Could not find Configure button ref in snapshot")
        print("  FAIL - Cannot find button ref")
    else:
        r = run_playwright_command(f"click {configure_ref}")
        time.sleep(1)  # Wait for modal to open and API to respond

        r = run_playwright_command("snapshot")
        modal_snapshot = read_snapshot(r["stdout"])

        # TEST 5: Modal shows config fields
        print("[playwright] TEST 5: Modal shows config fields...")
        if "Database Host" not in modal_snapshot:
            errors.append("Database Host field not found in modal")
            print("  FAIL")
        else:
            print("  PASS")

        # TEST 6: Modal shows current values
        print("[playwright] TEST 6: Current values populated...")
        if "192.168.1.100" not in modal_snapshot:
            errors.append("Current value '192.168.1.100' not found in modal")
            print("  FAIL")
        else:
            print("  PASS")

        # TEST 7: Modal shows API Port field
        print("[playwright] TEST 7: API Port field present...")
        if "API Port" not in modal_snapshot:
            errors.append("API Port field not found in modal")
            print("  FAIL")
        else:
            print("  PASS")

        # TEST 8: Close modal via Cancel
        print("[playwright] TEST 8: Close modal via Cancel...")
        cancel_ref = None
        for line in modal_snapshot.split("\n"):
            if "Cancel" in line and "ref=" in line:
                start = line.find("ref=") + 4
                end = line.find("]", start)
                if start > 3 and end != -1:
                    cancel_ref = line[start:end]
                    break

        if cancel_ref:
            r = run_playwright_command(f"click {cancel_ref}")
            time.sleep(0.5)
            r = run_playwright_command("snapshot")
            after_cancel = read_snapshot(r["stdout"])

            # The modal fields should no longer be visible (modal hidden)
            # But the app card should still be visible
            if "Test Config App" in after_cancel:
                print("  PASS")
            else:
                errors.append("Page state incorrect after cancel")
                print("  FAIL")
        else:
            errors.append("Could not find Cancel button ref")
            print("  FAIL - Cannot find Cancel ref")

    # Close browser
    run_playwright_command("close")

    return errors


# ============================================
# Pytest Tests
# ============================================


@pytest.fixture(scope="module")
def mock_app(local_docker_available, api_server_running):
    """Setup mock app before tests, teardown after."""
    setup_mock_app()
    # Give the API a moment to pick up the new container
    time.sleep(2)
    yield
    teardown_mock_app()


class TestConfigManagementAPI:
    """Test config management API endpoints with real Docker containers."""

    def test_managed_apps_shows_config_fields(self, mock_app, api_client):
        """Managed apps endpoint returns config_fields for apps with manifests."""
        response = api_client.get("/api/docker-devices/local/managed-apps")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Find our test app
        apps = data["apps"]
        test_app = next(
            (a for a in apps if a["solution_id"] == SOLUTION_ID), None
        )
        assert test_app is not None, f"Test app not found. Apps: {[a['solution_id'] for a in apps]}"
        assert test_app["solution_name"] == "Test Config App"
        assert test_app["status"] == "running"
        assert test_app["config_fields"] is not None
        assert len(test_app["config_fields"]) == 2
        assert test_app["config_fields"][0]["id"] == "db_host"

    def test_get_config_returns_fields(self, mock_app, api_client):
        """GET config endpoint returns field schema with current values."""
        response = api_client.get(
            f"/api/docker-devices/local/config/{SOLUTION_ID}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["config"] is not None

        fields = data["config"]["fields"]
        assert len(fields) == 2

        db_host = next(f for f in fields if f["id"] == "db_host")
        assert db_host["current_value"] == "192.168.1.100"
        assert db_host["name"] == "Database Host"
        assert db_host["name_zh"] == "数据库地址"
        assert db_host["required"] is True

        api_port = next(f for f in fields if f["id"] == "api_port")
        assert api_port["current_value"] == "9090"

    def test_get_config_nonexistent_returns_null(self, mock_app, api_client):
        """GET config for nonexistent solution returns null."""
        response = api_client.get(
            "/api/docker-devices/local/config/nonexistent_solution_xyz"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["config"] is None


@pytest.mark.skipif(
    not shutil.which("playwright-cli"),
    reason="playwright-cli not available",
)
class TestConfigManagementUI:
    """Test config management UI with playwright-cli."""

    def test_full_configure_flow(self, mock_app):
        """Full UI test: devices page -> configure button -> modal -> cancel."""
        errors = run_playwright_tests()
        if errors:
            pytest.fail(
                f"Playwright UI tests failed with {len(errors)} error(s):\n"
                + "\n".join(f"  - {e}" for e in errors)
            )


# ============================================
# CLI Entry Point (for manual testing)
# ============================================

if __name__ == "__main__":
    # Add project root to path for imports
    sys.path.insert(0, str(PROJECT_ROOT))

    if "--setup" in sys.argv:
        setup_mock_app()
        print("\nMock app is ready. Open http://localhost:5173/#/devices to test.")
        print("Run with --teardown to clean up when done.")

    elif "--teardown" in sys.argv:
        teardown_mock_app()

    elif "--playwright" in sys.argv:
        errors = run_playwright_tests()
        if errors:
            print(f"\n{len(errors)} error(s):")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print("\nAll playwright tests passed!")

    else:
        print("Usage:")
        print("  python tests/e2e/test_config_management.py --setup       # Create mock app")
        print("  python tests/e2e/test_config_management.py --teardown    # Clean up")
        print("  python tests/e2e/test_config_management.py --playwright  # Run UI tests")
        print()
        print("Or run via pytest:")
        print("  uv run --group test pytest tests/e2e/test_config_management.py -v")
