"""
SimulationDeployer: mimics any real deployer type without touching hardware.

Usage:
    from tests.simulation.deployer import SimulationDeployer

    # Simulate a successful ESP32 deployment
    sim = SimulationDeployer("esp32_usb")

    # Simulate failure at a specific step
    sim = SimulationDeployer("docker_local", scenario={
        "fail_at": {"pull_images": "Connection timeout pulling image nginx:latest"},
    })

    # Simulate slow deployment
    sim = SimulationDeployer("recamera_cpp", scenario={"step_delay": 1.0})

    # Replace in registry for testing
    engine.deployers["esp32_usb"] = sim
"""

import asyncio
import copy
import logging
from typing import Any, Callable, Dict, Optional

from provisioning_station.deployers import DEPLOYER_REGISTRY
from provisioning_station.deployers.base import BaseDeployer
from provisioning_station.models.device import DeviceConfig

logger = logging.getLogger(__name__)


class SimulationDeployer(BaseDeployer):
    """A deployer that simulates any real deployer type.

    It copies the steps and ui_traits from the real deployer, then simulates
    the deploy flow with configurable timing and failure injection.

    Scenario options:
        step_delay (float): Seconds to wait per step. Default: 0.02
        fail_at (dict): Mapping of step_id -> error message. The deploy will
            raise an exception when reaching that step.
        fail_at_progress (dict): Mapping of step_id -> progress (0-100) at which
            to fail. Default: 50.
        final_failure (bool): If True, deploy() returns False even if all steps
            pass. Simulates a post-step validation failure.
        progress_increments (int): Number of progress updates per step. Default: 3.
        connection_validator (callable): Optional function(connection) -> bool.
            If it returns False, the deploy fails with a connection error.
        on_step (callable): Optional async callback(step_id, step_name) called
            before each step begins. Useful for assertions in tests.
        record_calls (bool): If True, records all progress callbacks for later
            assertion. Default: True.
    """

    def __init__(self, mimic_type: str, scenario: Optional[Dict[str, Any]] = None):
        real_deployer = DEPLOYER_REGISTRY.get(mimic_type)
        if not real_deployer:
            raise ValueError(
                f"Unknown deployer type '{mimic_type}'. "
                f"Available: {list(DEPLOYER_REGISTRY.keys())}"
            )

        self.device_type = mimic_type
        self.steps = copy.deepcopy(real_deployer.steps)
        self.ui_traits = copy.deepcopy(real_deployer.ui_traits)
        self.scenario = scenario or {}
        self.mimic_type = mimic_type

        # Call recording for test assertions
        self.call_history: list = []
        self.deploy_count: int = 0
        self.last_config: Optional[DeviceConfig] = None
        self.last_connection: Optional[Dict] = None

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Simulate a deployment with configurable behavior."""
        self.deploy_count += 1
        self.last_config = config
        self.last_connection = connection

        step_delay = self.scenario.get("step_delay", 0.02)
        fail_at = self.scenario.get("fail_at", {})
        fail_at_progress = self.scenario.get("fail_at_progress", {})
        increments = self.scenario.get("progress_increments", 3)
        connection_validator = self.scenario.get("connection_validator")
        on_step = self.scenario.get("on_step")
        record = self.scenario.get("record_calls", True)

        logger.info(
            f"[Simulation] Starting {self.mimic_type} deploy "
            f"(device={config.id}, steps={len(self.steps)})"
        )

        # Validate connection if checker provided
        if connection_validator and not connection_validator(connection):
            error_msg = f"Simulated connection validation failed for {config.id}"
            if record:
                self.call_history.append(
                    {"event": "connection_failed", "device_id": config.id}
                )
            raise ConnectionError(error_msg)

        for step in self.steps:
            step_id = step["id"]
            step_name = step.get("name", step_id)

            # Optional test hook
            if on_step:
                await on_step(step_id, step_name)

            # Check for failure injection at this step
            if step_id in fail_at:
                fail_progress = fail_at_progress.get(step_id, 50)
                # Report partial progress before failure
                await self._report_progress(
                    progress_callback,
                    step_id,
                    fail_progress,
                    f"Simulating {step_name}...",
                )
                error_msg = fail_at[step_id]
                if record:
                    self.call_history.append(
                        {
                            "event": "step_failed",
                            "step_id": step_id,
                            "error": error_msg,
                        }
                    )
                logger.info(f"[Simulation] Injecting failure at step '{step_id}': {error_msg}")
                raise Exception(error_msg)

            # Simulate progress increments
            for i in range(increments):
                progress = int(((i + 1) / increments) * 100)
                if progress > 100:
                    progress = 100
                message = f"Simulating {step_name}..." if progress < 100 else f"{step_name} completed"
                await self._report_progress(
                    progress_callback, step_id, progress, message
                )
                if record:
                    self.call_history.append(
                        {
                            "event": "progress",
                            "step_id": step_id,
                            "progress": progress,
                            "message": message,
                        }
                    )
                if step_delay > 0:
                    await asyncio.sleep(step_delay)

            logger.info(f"[Simulation] Step '{step_id}' completed")

        # Check for final failure flag
        if self.scenario.get("final_failure", False):
            if record:
                self.call_history.append({"event": "final_failure"})
            logger.info("[Simulation] Returning False (final_failure scenario)")
            return False

        if record:
            self.call_history.append({"event": "deploy_success"})
        logger.info(f"[Simulation] Deployment completed successfully for {config.id}")
        return True

    def get_step_calls(self, step_id: str) -> list:
        """Get all recorded calls for a specific step."""
        return [c for c in self.call_history if c.get("step_id") == step_id]

    def reset(self):
        """Reset call history for reuse across tests."""
        self.call_history.clear()
        self.deploy_count = 0
        self.last_config = None
        self.last_connection = None


def patch_registry(overrides: Dict[str, "SimulationDeployer"]) -> Dict[str, BaseDeployer]:
    """Temporarily replace deployers in the registry with simulators.

    Args:
        overrides: Mapping of device_type -> SimulationDeployer instance.

    Returns:
        The original deployer instances (for restoring later).

    Usage:
        originals = patch_registry({"esp32_usb": SimulationDeployer("esp32_usb")})
        try:
            # run tests
        finally:
            DEPLOYER_REGISTRY.update(originals)
    """
    originals = {}
    for dtype, sim_deployer in overrides.items():
        if dtype in DEPLOYER_REGISTRY:
            originals[dtype] = DEPLOYER_REGISTRY[dtype]
        DEPLOYER_REGISTRY[dtype] = sim_deployer
    return originals
