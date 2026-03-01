"""
Deployment flow tests using simulated devices.

These tests exercise the full deployment pipeline (DeploymentEngine → Deployer
→ progress callbacks → state management) WITHOUT real hardware. They run in CI
alongside other unit tests.

Coverage:
- Single-device deployment: success, failure at each step, final_failure
- Multi-device deployment: partial failure, cancellation
- WebSocket message sequencing
- Deployer registry patching and restoration
- Connection validation failures
- All pre-built failure scenarios
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from provisioning_station.deployers import DEPLOYER_REGISTRY
from provisioning_station.models.deployment import DeploymentStatus
from provisioning_station.models.device import (
    DeploymentStep,
    DetectionConfig,
    DeviceConfig,
    DockerConfig,
)
from provisioning_station.services.deployment_engine import DeploymentEngine

from tests.simulation.deployer import SimulationDeployer, patch_registry
from tests.simulation.scenarios import (
    DOCKER_HEALTH_CHECK_FAIL,
    DOCKER_PULL_TIMEOUT,
    FAST_SUCCESS,
    FLASH_WRITE_ERROR,
    SCENARIOS,
    SSH_AUTH_FAILURE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_device_config(
    device_id: str = "test_device",
    device_type: str = "docker_local",
    steps: list = None,
) -> DeviceConfig:
    """Create a minimal DeviceConfig for testing."""
    if steps is None:
        # Use the real deployer's steps if available
        deployer = DEPLOYER_REGISTRY.get(device_type)
        if deployer and deployer.steps:
            steps = [
                DeploymentStep(id=s["id"], name=s["name"])
                for s in deployer.steps
            ]
        else:
            steps = [DeploymentStep(id="step1", name="Step 1")]

    return DeviceConfig(
        id=device_id,
        name=f"Test {device_type}",
        type=device_type,
        detection=DetectionConfig(method="local"),
        steps=steps,
    )


def _make_solution_mock(
    solution_id: str = "test_solution",
    devices: list = None,
    presets: list = None,
):
    """Create a mock Solution object with deployment info."""
    solution = MagicMock()
    solution.id = solution_id
    solution.name = "Test Solution"
    solution.base_path = "/tmp/test_solution"
    solution.intro = MagicMock()
    solution.intro.stats = MagicMock()
    solution.intro.stats.deployed_count = 0

    if devices is None:
        devices = [
            {
                "id": "device1",
                "name": "Test Docker Device",
                "type": "docker_local",
                "config_file": "devices/docker.yaml",
                "required": True,
            }
        ]

    deployment_info = {
        "devices": devices,
        "presets": presets or [],
        "overview": "",
        "post_deployment": None,
    }

    return solution, deployment_info


async def _run_simulated_deployment(
    engine: DeploymentEngine,
    solution_id: str = "test_solution",
    device_type: str = "docker_local",
    device_id: str = "device1",
    scenario: dict = None,
    connection: dict = None,
) -> str:
    """Helper to set up and run a simulated deployment end-to-end."""
    scenario = scenario or FAST_SUCCESS

    # Set up simulation deployer
    sim = SimulationDeployer(device_type, scenario=scenario)
    originals = patch_registry({device_type: sim})

    try:
        solution, deployment_info = _make_solution_mock(
            solution_id=solution_id,
            devices=[
                {
                    "id": device_id,
                    "name": f"Test {device_type}",
                    "type": device_type,
                    "config_file": f"devices/{device_type}.yaml",
                    "required": True,
                }
            ],
        )

        config = _make_device_config(device_id, device_type)

        # Mock solution_manager methods
        with patch(
            "provisioning_station.services.deployment_engine.solution_manager"
        ) as mock_sm:
            mock_sm.get_deployment_from_guide = AsyncMock(return_value=deployment_info)
            mock_sm.load_device_config = AsyncMock(return_value=config)
            mock_sm.get_solution.return_value = solution

            deployment_id = await engine.start_deployment(
                solution=solution,
                device_connections={device_id: connection or {}},
                selected_devices=[device_id],
            )

            # Wait for background task to complete
            if deployment_id in engine._running_tasks:
                try:
                    await asyncio.wait_for(
                        engine._running_tasks[deployment_id], timeout=10.0
                    )
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass

        return deployment_id
    finally:
        DEPLOYER_REGISTRY.update(originals)


# ---------------------------------------------------------------------------
# Tests: SimulationDeployer unit tests
# ---------------------------------------------------------------------------


class TestSimulationDeployer:
    """Test the SimulationDeployer itself."""

    def test_mirrors_real_deployer_steps(self):
        """SimulationDeployer copies steps from the real deployer."""
        for dtype in ["esp32_usb", "docker_local", "recamera_cpp", "script"]:
            sim = SimulationDeployer(dtype)
            real = DEPLOYER_REGISTRY[dtype]
            assert len(sim.steps) == len(real.steps), f"{dtype}: step count mismatch"
            for sim_step, real_step in zip(sim.steps, real.steps):
                assert sim_step["id"] == real_step["id"], f"{dtype}: step id mismatch"

    def test_mirrors_real_deployer_ui_traits(self):
        """SimulationDeployer copies ui_traits from the real deployer."""
        for dtype in ["esp32_usb", "docker_local", "recamera_cpp"]:
            sim = SimulationDeployer(dtype)
            real = DEPLOYER_REGISTRY[dtype]
            assert sim.ui_traits == real.ui_traits, f"{dtype}: ui_traits mismatch"

    def test_invalid_type_raises(self):
        """SimulationDeployer raises ValueError for unknown types."""
        with pytest.raises(ValueError, match="Unknown deployer type"):
            SimulationDeployer("nonexistent_type")

    @pytest.mark.asyncio
    async def test_successful_deploy(self):
        """Simulated deploy completes successfully with all steps."""
        sim = SimulationDeployer("docker_local", scenario=FAST_SUCCESS)
        config = _make_device_config("test", "docker_local")

        progress_calls = []

        async def track_progress(step_id, progress, message):
            progress_calls.append((step_id, progress, message))

        result = await sim.deploy(config, {}, progress_callback=track_progress)

        assert result is True
        assert sim.deploy_count == 1
        assert len(progress_calls) > 0
        # Each step should have progress calls
        step_ids_seen = {c[0] for c in progress_calls}
        expected_ids = {s["id"] for s in sim.steps}
        assert step_ids_seen == expected_ids

    @pytest.mark.asyncio
    async def test_failure_at_step(self):
        """Simulated deploy raises exception at the specified step."""
        sim = SimulationDeployer("docker_local", scenario=DOCKER_PULL_TIMEOUT)
        config = _make_device_config("test", "docker_local")

        with pytest.raises(Exception, match="Timeout pulling image"):
            await sim.deploy(config, {})

        # Should have recorded the failure
        failures = [c for c in sim.call_history if c["event"] == "step_failed"]
        assert len(failures) == 1
        assert failures[0]["step_id"] == "pull_images"

    @pytest.mark.asyncio
    async def test_final_failure(self):
        """deploy() returns False when final_failure is set."""
        sim = SimulationDeployer(
            "docker_local", scenario={"final_failure": True, "step_delay": 0}
        )
        config = _make_device_config("test", "docker_local")

        result = await sim.deploy(config, {})
        assert result is False

    @pytest.mark.asyncio
    async def test_connection_validator_rejects(self):
        """Connection validation failure raises ConnectionError."""
        sim = SimulationDeployer(
            "recamera_cpp",
            scenario={"connection_validator": lambda c: c.get("host") is not None},
        )
        config = _make_device_config("test", "recamera_cpp")

        # No host in connection → validator returns False
        with pytest.raises(ConnectionError, match="connection validation failed"):
            await sim.deploy(config, {})

    @pytest.mark.asyncio
    async def test_connection_validator_accepts(self):
        """Connection validation passes when validator returns True."""
        sim = SimulationDeployer(
            "recamera_cpp",
            scenario={
                "connection_validator": lambda c: c.get("host") is not None,
                "step_delay": 0,
            },
        )
        config = _make_device_config("test", "recamera_cpp")

        result = await sim.deploy(config, {"host": "192.168.42.1"})
        assert result is True

    @pytest.mark.asyncio
    async def test_on_step_callback(self):
        """on_step callback is called for each step."""
        steps_visited = []

        async def on_step(step_id, step_name):
            steps_visited.append(step_id)

        sim = SimulationDeployer(
            "esp32_usb", scenario={"on_step": on_step, "step_delay": 0}
        )
        config = _make_device_config("test", "esp32_usb")

        await sim.deploy(config, {})

        expected = [s["id"] for s in sim.steps]
        assert steps_visited == expected

    @pytest.mark.asyncio
    async def test_reset_clears_history(self):
        """reset() clears all recorded state."""
        sim = SimulationDeployer("docker_local", scenario=FAST_SUCCESS)
        config = _make_device_config("test", "docker_local")

        await sim.deploy(config, {})
        assert sim.deploy_count == 1
        assert len(sim.call_history) > 0

        sim.reset()
        assert sim.deploy_count == 0
        assert len(sim.call_history) == 0
        assert sim.last_config is None

    def test_get_step_calls_filters(self):
        """get_step_calls returns only entries for the specified step."""
        sim = SimulationDeployer("docker_local")
        sim.call_history = [
            {"event": "progress", "step_id": "pull_images", "progress": 50},
            {"event": "progress", "step_id": "start_services", "progress": 100},
            {"event": "progress", "step_id": "pull_images", "progress": 100},
        ]

        calls = sim.get_step_calls("pull_images")
        assert len(calls) == 2
        assert all(c["step_id"] == "pull_images" for c in calls)


# ---------------------------------------------------------------------------
# Tests: patch_registry
# ---------------------------------------------------------------------------


class TestPatchRegistry:
    """Test registry patching utility."""

    def test_patch_and_restore(self):
        """patch_registry replaces and returns originals for restore."""
        original_docker = DEPLOYER_REGISTRY["docker_local"]
        sim = SimulationDeployer("docker_local")

        originals = patch_registry({"docker_local": sim})

        assert DEPLOYER_REGISTRY["docker_local"] is sim
        assert originals["docker_local"] is original_docker

        # Restore
        DEPLOYER_REGISTRY.update(originals)
        assert DEPLOYER_REGISTRY["docker_local"] is original_docker


# ---------------------------------------------------------------------------
# Tests: Deployment engine with simulation
# ---------------------------------------------------------------------------


class TestDeploymentEngineSimulated:
    """Test DeploymentEngine using SimulationDeployer."""

    @pytest.mark.asyncio
    async def test_successful_single_device_deployment(self):
        """Full deployment flow completes successfully with simulated device."""
        engine = DeploymentEngine()
        deployment_id = await _run_simulated_deployment(
            engine, device_type="docker_local", scenario=FAST_SUCCESS
        )

        deployment = engine.get_deployment(deployment_id)
        assert deployment is not None
        assert deployment.status == DeploymentStatus.COMPLETED
        assert len(deployment.devices) == 1
        assert deployment.devices[0].status == DeploymentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_failed_deployment_step(self):
        """Deployment fails when a step raises an exception."""
        engine = DeploymentEngine()
        deployment_id = await _run_simulated_deployment(
            engine,
            device_type="docker_local",
            scenario=DOCKER_PULL_TIMEOUT,
        )

        deployment = engine.get_deployment(deployment_id)
        assert deployment is not None
        assert deployment.status == DeploymentStatus.FAILED
        assert deployment.devices[0].status == DeploymentStatus.FAILED
        assert "Timeout pulling image" in deployment.devices[0].error

    @pytest.mark.asyncio
    async def test_deploy_returns_false(self):
        """Deployment fails when deployer.deploy() returns False."""
        engine = DeploymentEngine()
        deployment_id = await _run_simulated_deployment(
            engine,
            device_type="docker_local",
            scenario={"final_failure": True, "step_delay": 0},
        )

        deployment = engine.get_deployment(deployment_id)
        assert deployment is not None
        assert deployment.status == DeploymentStatus.FAILED

    @pytest.mark.asyncio
    async def test_deployment_records_to_completed_list(self):
        """Completed deployments are added to the completed list."""
        engine = DeploymentEngine()
        deployment_id = await _run_simulated_deployment(
            engine, device_type="docker_local", scenario=FAST_SUCCESS
        )

        # NOTE: The engine currently keeps the deployment in active_deployments
        # even after completion (it only removes _running_tasks). This is a
        # known behavior — get_deployment() checks both dicts.
        assert any(d.id == deployment_id for d in engine.completed_deployments)

    @pytest.mark.asyncio
    async def test_websocket_broadcast_on_success(self):
        """WebSocket messages are broadcast during successful deployment."""
        engine = DeploymentEngine()
        ws_messages = []
        ws_manager = MagicMock()
        ws_manager.broadcast = AsyncMock(
            side_effect=lambda did, msg: ws_messages.append(msg)
        )
        engine.set_websocket_manager(ws_manager)

        deployment_id = await _run_simulated_deployment(
            engine, device_type="docker_local", scenario=FAST_SUCCESS
        )

        # Should have received various message types
        message_types = {m.get("type") for m in ws_messages}
        assert "log" in message_types
        assert "progress" in message_types
        assert "device_started" in message_types
        assert "device_completed" in message_types
        assert "deployment_completed" in message_types

    @pytest.mark.asyncio
    async def test_websocket_broadcast_on_failure(self):
        """WebSocket messages include error info on failure."""
        engine = DeploymentEngine()
        ws_messages = []
        ws_manager = MagicMock()
        ws_manager.broadcast = AsyncMock(
            side_effect=lambda did, msg: ws_messages.append(msg)
        )
        engine.set_websocket_manager(ws_manager)

        deployment_id = await _run_simulated_deployment(
            engine,
            device_type="docker_local",
            scenario=DOCKER_HEALTH_CHECK_FAIL,
        )

        # Should have error logs
        error_logs = [
            m for m in ws_messages if m.get("type") == "log" and m.get("level") == "error"
        ]
        assert len(error_logs) > 0

        # deployment_completed should have failed status
        completion_msgs = [
            m for m in ws_messages if m.get("type") == "deployment_completed"
        ]
        assert len(completion_msgs) == 1
        assert completion_msgs[0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_step_progress_updates_in_order(self):
        """Progress updates arrive in the correct step order."""
        engine = DeploymentEngine()
        ws_messages = []
        ws_manager = MagicMock()
        ws_manager.broadcast = AsyncMock(
            side_effect=lambda did, msg: ws_messages.append(msg)
        )
        engine.set_websocket_manager(ws_manager)

        deployment_id = await _run_simulated_deployment(
            engine, device_type="esp32_usb", scenario=FAST_SUCCESS
        )

        # Extract step progress messages in order
        progress_steps = [
            m["step_id"]
            for m in ws_messages
            if m.get("type") == "progress"
        ]

        # Steps should appear in deployer's step order
        esp32_step_ids = [s["id"] for s in DEPLOYER_REGISTRY["esp32_usb"].steps]
        seen_order = []
        for step_id in progress_steps:
            if step_id not in seen_order:
                seen_order.append(step_id)

        # Verify order matches
        assert seen_order == esp32_step_ids

    @pytest.mark.asyncio
    async def test_multi_device_deployment_success(self):
        """Multi-device deployment completes when all devices succeed."""
        engine = DeploymentEngine()

        # Set up two simulated deployers
        sim_docker = SimulationDeployer("docker_local", scenario=FAST_SUCCESS)
        sim_esp32 = SimulationDeployer("esp32_usb", scenario=FAST_SUCCESS)
        originals = patch_registry({"docker_local": sim_docker, "esp32_usb": sim_esp32})

        try:
            solution, deployment_info = _make_solution_mock(
                devices=[
                    {
                        "id": "docker_device",
                        "name": "Docker Service",
                        "type": "docker_local",
                        "config_file": "devices/docker.yaml",
                        "required": True,
                    },
                    {
                        "id": "esp32_device",
                        "name": "ESP32 Firmware",
                        "type": "esp32_usb",
                        "config_file": "devices/esp32.yaml",
                        "required": True,
                    },
                ],
            )

            docker_config = _make_device_config("docker_device", "docker_local")
            esp32_config = _make_device_config("esp32_device", "esp32_usb")

            with patch(
                "provisioning_station.services.deployment_engine.solution_manager"
            ) as mock_sm:
                mock_sm.get_deployment_from_guide = AsyncMock(
                    return_value=deployment_info
                )

                async def _load_config(sol_id, config_file):
                    if "docker" in config_file:
                        return docker_config
                    elif "esp32" in config_file:
                        return esp32_config
                    return None

                mock_sm.load_device_config = AsyncMock(side_effect=_load_config)
                mock_sm.get_solution.return_value = solution

                deployment_id = await engine.start_deployment(
                    solution=solution,
                    device_connections={
                        "docker_device": {},
                        "esp32_device": {"port": "/dev/ttyACM1"},
                    },
                )

                if deployment_id in engine._running_tasks:
                    await asyncio.wait_for(
                        engine._running_tasks[deployment_id], timeout=10.0
                    )

            deployment = engine.get_deployment(deployment_id)
            assert deployment.status == DeploymentStatus.COMPLETED
            assert len(deployment.devices) == 2
            assert all(
                d.status == DeploymentStatus.COMPLETED for d in deployment.devices
            )
            assert sim_docker.deploy_count == 1
            assert sim_esp32.deploy_count == 1
        finally:
            DEPLOYER_REGISTRY.update(originals)

    @pytest.mark.asyncio
    async def test_multi_device_partial_failure(self):
        """Multi-device deployment stops after first device failure."""
        engine = DeploymentEngine()

        # First device fails, second should not run
        sim_docker = SimulationDeployer("docker_local", scenario=DOCKER_PULL_TIMEOUT)
        sim_esp32 = SimulationDeployer("esp32_usb", scenario=FAST_SUCCESS)
        originals = patch_registry({"docker_local": sim_docker, "esp32_usb": sim_esp32})

        try:
            solution, deployment_info = _make_solution_mock(
                devices=[
                    {
                        "id": "docker_device",
                        "name": "Docker Service",
                        "type": "docker_local",
                        "config_file": "devices/docker.yaml",
                        "required": True,
                    },
                    {
                        "id": "esp32_device",
                        "name": "ESP32 Firmware",
                        "type": "esp32_usb",
                        "config_file": "devices/esp32.yaml",
                        "required": True,
                    },
                ],
            )

            docker_config = _make_device_config("docker_device", "docker_local")
            esp32_config = _make_device_config("esp32_device", "esp32_usb")

            with patch(
                "provisioning_station.services.deployment_engine.solution_manager"
            ) as mock_sm:
                mock_sm.get_deployment_from_guide = AsyncMock(
                    return_value=deployment_info
                )

                async def _load_config(sol_id, config_file):
                    if "docker" in config_file:
                        return docker_config
                    elif "esp32" in config_file:
                        return esp32_config
                    return None

                mock_sm.load_device_config = AsyncMock(side_effect=_load_config)
                mock_sm.get_solution.return_value = solution

                deployment_id = await engine.start_deployment(
                    solution=solution,
                    device_connections={
                        "docker_device": {},
                        "esp32_device": {"port": "/dev/ttyACM1"},
                    },
                )

                if deployment_id in engine._running_tasks:
                    await asyncio.wait_for(
                        engine._running_tasks[deployment_id], timeout=10.0
                    )

            deployment = engine.get_deployment(deployment_id)
            assert deployment.status == DeploymentStatus.FAILED
            assert deployment.devices[0].status == DeploymentStatus.FAILED
            # Second device should NOT have been deployed (engine breaks on failure)
            assert sim_esp32.deploy_count == 0
        finally:
            DEPLOYER_REGISTRY.update(originals)

    @pytest.mark.asyncio
    async def test_deployment_cancellation(self):
        """Deployment can be cancelled while running."""
        engine = DeploymentEngine()

        # Use slow scenario so we can cancel during execution
        sim = SimulationDeployer("docker_local", scenario={"step_delay": 0.5})
        originals = patch_registry({"docker_local": sim})

        try:
            solution, deployment_info = _make_solution_mock()
            config = _make_device_config("device1", "docker_local")

            with patch(
                "provisioning_station.services.deployment_engine.solution_manager"
            ) as mock_sm:
                mock_sm.get_deployment_from_guide = AsyncMock(
                    return_value=deployment_info
                )
                mock_sm.load_device_config = AsyncMock(return_value=config)
                mock_sm.get_solution.return_value = solution

                deployment_id = await engine.start_deployment(
                    solution=solution,
                    device_connections={"device1": {}},
                )

                # Give it a moment to start
                await asyncio.sleep(0.1)

                # Cancel
                await engine.cancel_deployment(deployment_id)

                # Wait for task to finish
                if deployment_id in engine._running_tasks:
                    try:
                        await asyncio.wait_for(
                            engine._running_tasks[deployment_id], timeout=5.0
                        )
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        pass

            deployment = engine.get_deployment(deployment_id)
            assert deployment is not None
            assert deployment.status in (
                DeploymentStatus.CANCELLED,
                DeploymentStatus.FAILED,
            )
        finally:
            DEPLOYER_REGISTRY.update(originals)


# ---------------------------------------------------------------------------
# Tests: All failure scenarios coverage
# ---------------------------------------------------------------------------


class TestAllFailureScenarios:
    """Verify that every pre-built scenario works with its target deployer type."""

    # Map each scenario to a deployer type it makes sense for
    SCENARIO_TYPE_MAP = {
        "fast_success": "docker_local",
        "realistic_success": "docker_local",
        "connection_timeout": "recamera_cpp",
        "ssh_auth_failure": "recamera_cpp",
        "ssh_host_unreachable": "recamera_cpp",
        "serial_port_busy": "esp32_usb",
        "flash_write_error": "esp32_usb",
        "flash_verify_fail": "esp32_usb",
        "erase_timeout": "esp32_usb",
        "docker_pull_timeout": "docker_local",
        "docker_pull_auth_error": "docker_local",
        "docker_health_check_fail": "docker_local",
        "docker_volume_error": "docker_local",
        "docker_start_fail": "docker_local",
        "ssh_transfer_fail": "recamera_cpp",
        "ssh_install_fail": "recamera_cpp",
        "recamera_precheck_fail": "recamera_cpp",
        "recamera_model_deploy_fail": "recamera_cpp",
        "recamera_service_start_fail": "recamera_cpp",
        "nodered_flow_load_fail": "recamera_nodered",
        "script_setup_fail": "script",
        "script_health_check_timeout": "script",
        "ha_auth_fail": "ha_integration",
        "ha_restart_timeout": "ha_integration",
        "deploy_returns_false": "docker_local",
    }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scenario_name",
        list(SCENARIOS.keys()),
    )
    async def test_scenario_runs(self, scenario_name):
        """Each pre-built scenario can be instantiated and run."""
        scenario = SCENARIOS[scenario_name]
        device_type = self.SCENARIO_TYPE_MAP[scenario_name]

        sim = SimulationDeployer(device_type, scenario=scenario)
        config = _make_device_config("test", device_type)

        is_success = scenario_name in ("fast_success", "realistic_success")
        is_final_fail = scenario_name == "deploy_returns_false"
        is_connection_fail = scenario_name == "connection_timeout"

        if is_success:
            result = await sim.deploy(config, {"host": "1.2.3.4"})
            assert result is True
        elif is_final_fail:
            result = await sim.deploy(config, {})
            assert result is False
        elif is_connection_fail:
            with pytest.raises(ConnectionError):
                await sim.deploy(config, {})
        else:
            with pytest.raises(Exception):
                await sim.deploy(config, {"host": "1.2.3.4"})

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scenario_name",
        [k for k, v in SCENARIOS.items() if k not in (
            "fast_success", "realistic_success", "deploy_returns_false",
            "connection_timeout",
        )],
    )
    async def test_failure_scenario_in_engine(self, scenario_name):
        """Each failure scenario produces a FAILED deployment in the engine."""
        scenario = SCENARIOS[scenario_name]
        device_type = self.SCENARIO_TYPE_MAP[scenario_name]

        engine = DeploymentEngine()
        deployment_id = await _run_simulated_deployment(
            engine,
            device_type=device_type,
            scenario=scenario,
        )

        deployment = engine.get_deployment(deployment_id)
        assert deployment is not None, f"Deployment not found for scenario {scenario_name}"
        assert deployment.status == DeploymentStatus.FAILED, (
            f"Scenario '{scenario_name}' should produce FAILED status, "
            f"got {deployment.status}"
        )


# ---------------------------------------------------------------------------
# Tests: All deployer types can be simulated
# ---------------------------------------------------------------------------


class TestAllDeployerTypesSimulatable:
    """Verify every registered deployer can be simulated."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "device_type",
        [dt for dt in DEPLOYER_REGISTRY.keys() if DEPLOYER_REGISTRY[dt].steps],
    )
    async def test_can_simulate_deployer(self, device_type):
        """SimulationDeployer successfully mimics each real deployer type."""
        sim = SimulationDeployer(device_type, scenario=FAST_SUCCESS)
        config = _make_device_config("test", device_type)

        result = await sim.deploy(config, {"host": "1.2.3.4", "port": "/dev/ttyACM0"})
        assert result is True
        assert sim.deploy_count == 1

        # Every step should have been visited
        step_ids = {s["id"] for s in sim.steps}
        visited_ids = {
            c["step_id"] for c in sim.call_history if c.get("step_id")
        }
        assert visited_ids == step_ids, (
            f"{device_type}: not all steps visited. "
            f"Missing: {step_ids - visited_ids}"
        )
