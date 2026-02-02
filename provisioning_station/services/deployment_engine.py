"""
Deployment orchestration engine
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..deployers.base import BaseDeployer
from ..deployers.docker_deployer import DockerDeployer
from ..deployers.docker_remote_deployer import (
    DockerRemoteDeployer,
    RemoteDockerNotInstalled,
)
from ..deployers.esp32_deployer import ESP32Deployer
from ..deployers.himax_deployer import HimaxDeployer
from ..deployers.manual_deployer import ManualDeployer
from ..deployers.recamera_cpp_deployer import ReCameraCppDeployer
from ..deployers.recamera_nodered_deployer import ReCameraNodeRedDeployer
from ..deployers.script_deployer import ScriptDeployer
from ..deployers.ssh_deployer import SSHDeployer
from ..models.deployment import (
    Deployment,
    DeploymentStatus,
    DeviceDeployment,
    StepStatus,
)
from ..models.solution import Solution
from ..models.version import DeploymentRecord, StepRecord
from .deployment_history import deployment_history
from .pre_check_validator import pre_check_validator
from .solution_manager import solution_manager

logger = logging.getLogger(__name__)


class DeploymentEngine:
    """Orchestrates deployment execution across multiple devices"""

    def __init__(self):
        self.active_deployments: Dict[str, Deployment] = {}
        self.completed_deployments: List[Deployment] = []
        self._websocket_manager = None
        self._running_tasks: Dict[str, asyncio.Task] = {}

        # Initialize deployers
        self.deployers: Dict[str, BaseDeployer] = {
            "esp32_usb": ESP32Deployer(),
            "himax_usb": HimaxDeployer(),
            "docker_local": DockerDeployer(),
            "docker_remote": DockerRemoteDeployer(),
            "ssh_deb": SSHDeployer(),
            "script": ScriptDeployer(),
            "manual": ManualDeployer(),
            "recamera_nodered": ReCameraNodeRedDeployer(),
            "recamera_cpp": ReCameraCppDeployer(),
        }

    def set_websocket_manager(self, manager):
        """Set WebSocket manager for broadcasting updates"""
        self._websocket_manager = manager

    async def start_deployment(
        self,
        solution: Solution,
        device_connections: Dict[str, Dict[str, Any]],
        selected_devices: List[str] = None,
        options: Dict[str, Any] = None,
        preset_id: str = None,
    ) -> str:
        """Start a new deployment"""
        logger.info(f"Starting deployment: solution={solution.id}, preset={preset_id}")
        deployment_id = str(uuid4())

        # Initialize deployment state
        deployment = Deployment(
            id=deployment_id,
            solution_id=solution.id,
            started_at=datetime.utcnow(),
            status=DeploymentStatus.RUNNING,
            devices=[],
        )

        # Get devices list from guide.md
        devices_list = []
        deploy_order = []

        deployment_info = await solution_manager.get_deployment_from_guide(solution.id, "en")
        if deployment_info and deployment_info.get("devices"):
            all_devices = deployment_info["devices"]

            if preset_id and deployment_info.get("presets"):
                # Find preset and get its device IDs
                preset = next(
                    (p for p in deployment_info["presets"] if p["id"] == preset_id), None
                )
                if preset and preset.get("devices"):
                    deploy_order = preset["devices"]
                    devices_list = [d for d in all_devices if d["id"] in deploy_order]
                    logger.info(
                        f"Using preset '{preset_id}' with {len(devices_list)} devices"
                    )
                else:
                    logger.warning(
                        f"Preset '{preset_id}' not found, using all devices"
                    )
                    devices_list = all_devices
                    deploy_order = [d["id"] for d in all_devices]
            else:
                # No preset specified, use all devices
                devices_list = all_devices
                deploy_order = [d["id"] for d in all_devices]

        # Filter by selected_devices if provided
        if selected_devices:
            deploy_order = [d for d in deploy_order if d in selected_devices]

        # Initialize device deployments
        for device_id in deploy_order:
            device_ref = next(
                (d for d in devices_list if d.get("id") == device_id), None
            )
            if not device_ref:
                continue

            # Determine effective type and config_file
            device_type = device_ref.get("type")
            effective_type = device_type
            config_file = device_ref.get("config_file")
            logger.debug(
                f"Device {device_id}: type={device_type}, config_file={config_file}"
            )

            # Check for target override from device_connections (e.g., target: warehouse_remote)
            connection_info = device_connections.get(device_id, {})
            target_override = connection_info.get("target")

            if target_override:
                # Target specifies a device config file directly (e.g., warehouse_remote -> devices/warehouse_remote.yaml)
                config_file = f"devices/{target_override}.yaml"
                # Determine effective type from explicit target_type or fallback to name-based detection
                target_type = connection_info.get("target_type")
                if target_type == "remote":
                    effective_type = "docker_remote"
                elif target_type == "local":
                    effective_type = "docker_local"
                elif "remote" in target_override.lower():
                    # Fallback: detect from target name for backwards compatibility
                    effective_type = "docker_remote"
                else:
                    effective_type = "docker_local"
                logger.info(
                    f"Device {device_id}: using target override config_file={config_file}, effective_type={effective_type}"
                )
            elif device_type == "docker_deploy":
                # Get selected target from options (local/remote)
                deploy_target = (
                    options.get("deploy_target", "local") if options else "local"
                )
                effective_type = (
                    "docker_remote" if deploy_target == "remote" else "docker_local"
                )
                # Use config_file from options if provided, otherwise resolve from targets
                if options and options.get("config_file"):
                    config_file = options["config_file"]
                else:
                    targets = device_ref.get("targets")
                    if targets and deploy_target in targets:
                        target = targets[deploy_target]
                        if target.get("config_file"):
                            config_file = target["config_file"]
                logger.info(
                    f"docker_deploy resolved: target={deploy_target}, effective_type={effective_type}, config_file={config_file}"
                )
            elif options and options.get("config_file"):
                # Support config_file override for any device type with targets
                config_file = options["config_file"]
                logger.info(
                    f"{device_type}: using target config_file={config_file}"
                )

            # Skip devices without config_file (e.g., manual info-only steps)
            if not config_file:
                logger.info(f"Skipping device {device_id} (no config_file)")
                continue

            # Load device config to get steps
            config = await solution_manager.load_device_config(solution.id, config_file)
            if not config:
                continue

            # Check if we have connection info for this device
            is_required = device_ref.get("required", True)
            if device_id not in device_connections and is_required:
                # Skip if required device has no connection
                logger.warning(f"No connection info for required device: {device_id}")
                continue

            device_name = device_ref.get("name", device_id)
            device_deployment = DeviceDeployment(
                device_id=device_id,
                name=device_name,
                type=effective_type,  # Use effective type for deployer selection
                config_file=config_file,  # Store config_file for _run_deployment
                status=DeploymentStatus.PENDING,
                connection=device_connections.get(device_id),
                steps=[StepStatus(id=step.id, name=step.name) for step in config.steps],
            )
            deployment.devices.append(device_deployment)

        if not deployment.devices:
            raise ValueError("No devices to deploy")

        self.active_deployments[deployment_id] = deployment

        # Start deployment in background
        task = asyncio.create_task(self._run_deployment(deployment_id))
        self._running_tasks[deployment_id] = task

        # Broadcast initial log (don't await in sync context, use create_task)
        asyncio.create_task(
            self._broadcast_log(
                deployment_id,
                f"Started deployment for solution: {solution.id}",
                level="info",
            )
        )

        return deployment_id

    async def _run_deployment(self, deployment_id: str):
        """Execute deployment steps sequentially"""
        deployment = self.active_deployments.get(deployment_id)
        if not deployment:
            return

        solution = solution_manager.get_solution(deployment.solution_id)
        if not solution:
            deployment.status = DeploymentStatus.FAILED
            await self._broadcast_log(
                deployment_id, "Solution not found", level="error"
            )
            return

        try:
            for device_deployment in deployment.devices:
                if deployment.status == DeploymentStatus.CANCELLED:
                    break

                device_deployment.status = DeploymentStatus.RUNNING
                device_deployment.started_at = datetime.utcnow()

                await self._broadcast_log(
                    deployment_id,
                    f"Starting deployment for device: {device_deployment.device_id}",
                    level="info",
                    device_id=device_deployment.device_id,
                )
                await self._broadcast_update(
                    deployment_id,
                    {
                        "type": "device_started",
                        "device_id": device_deployment.device_id,
                    },
                )

                # Skip devices without config_file
                if not device_deployment.config_file:
                    device_deployment.status = DeploymentStatus.COMPLETED
                    device_deployment.completed_at = datetime.utcnow()
                    continue

                # Load device config using stored config_file path
                config = await solution_manager.load_device_config(
                    solution.id, device_deployment.config_file
                )
                if not config:
                    device_deployment.status = DeploymentStatus.FAILED
                    device_deployment.error = "Device config not found"
                    continue

                # Get the appropriate deployer
                deployer = self.deployers.get(config.type)
                if not deployer:
                    device_deployment.status = DeploymentStatus.FAILED
                    device_deployment.error = f"No deployer for type: {config.type}"
                    continue

                # Run pre-checks if defined
                # Skip local pre-checks for docker_remote type - remote checks are handled by the deployer
                # Use device_deployment.type (runtime effective type) instead of config.type (file-defined type)
                if config.pre_checks and device_deployment.type != "docker_remote":
                    await self._broadcast_log(
                        deployment_id,
                        "Running pre-deployment checks...",
                        level="info",
                        device_id=device_deployment.device_id,
                    )
                    await self._broadcast_update(
                        deployment_id,
                        {
                            "type": "pre_check_started",
                            "device_id": device_deployment.device_id,
                        },
                    )

                    check_results = await pre_check_validator.validate_all(
                        config.pre_checks
                    )
                    failed_checks = [r for r in check_results if not r.passed]

                    if failed_checks:
                        device_deployment.status = DeploymentStatus.FAILED
                        device_deployment.error = (
                            f"Pre-checks failed: {[c.message for c in failed_checks]}"
                        )
                        await self._broadcast_log(
                            deployment_id,
                            f"Pre-checks failed for {device_deployment.device_id}: {[c.message for c in failed_checks]}",
                            level="error",
                            device_id=device_deployment.device_id,
                        )
                        await self._broadcast_update(
                            deployment_id,
                            {
                                "type": "pre_check_failed",
                                "device_id": device_deployment.device_id,
                                "failures": [c.model_dump() for c in failed_checks],
                            },
                        )
                        deployment.status = DeploymentStatus.FAILED
                        continue

                    await self._broadcast_log(
                        deployment_id,
                        f"Pre-checks passed for {device_deployment.device_id}",
                        level="info",
                        device_id=device_deployment.device_id,
                    )
                    await self._broadcast_update(
                        deployment_id,
                        {
                            "type": "pre_check_passed",
                            "device_id": device_deployment.device_id,
                            "results": [c.model_dump() for c in check_results],
                        },
                    )

                # Create progress callback
                async def progress_callback(step_id: str, progress: int, message: str):
                    deployment.update_step(
                        device_deployment.device_id,
                        step_id,
                        "running" if progress < 100 else "completed",
                        progress,
                        message,
                    )
                    await self._broadcast_log(
                        deployment_id,
                        message,
                        level="info",
                        device_id=device_deployment.device_id,
                        step_id=step_id,
                    )
                    await self._broadcast_update(
                        deployment_id,
                        {
                            "type": "progress",
                            "device_id": device_deployment.device_id,
                            "step_id": step_id,
                            "progress": progress,
                            "message": message,
                        },
                    )

                # Execute deployment
                try:
                    # Add solution metadata to connection for label injection
                    enriched_connection = {
                        **device_deployment.connection,
                        "_solution_id": solution.id,
                        "_solution_name": solution.name,
                        "_device_id": device_deployment.device_id,
                    }

                    success = await deployer.deploy(
                        config=config,
                        connection=enriched_connection,
                        progress_callback=progress_callback,
                    )

                    if success:
                        device_deployment.status = DeploymentStatus.COMPLETED
                        device_deployment.completed_at = datetime.utcnow()
                        # Mark all steps as completed
                        for step in device_deployment.steps:
                            if step.status != "completed":
                                step.status = "completed"
                                step.progress = 100
                        await self._broadcast_log(
                            deployment_id,
                            f"Device {device_deployment.device_id} deployment completed successfully",
                            level="success",
                            device_id=device_deployment.device_id,
                        )
                    else:
                        device_deployment.status = DeploymentStatus.FAILED
                        deployment.status = DeploymentStatus.FAILED
                        await self._broadcast_log(
                            deployment_id,
                            f"Device {device_deployment.device_id} deployment failed",
                            level="error",
                            device_id=device_deployment.device_id,
                        )

                except RemoteDockerNotInstalled as e:
                    # Docker not installed - ask user for confirmation to install
                    logger.info(
                        f"Docker not installed on {device_deployment.device_id}: {e}"
                    )
                    device_deployment.status = DeploymentStatus.FAILED
                    device_deployment.error = str(e)
                    deployment.status = DeploymentStatus.FAILED

                    await self._broadcast_log(
                        deployment_id,
                        str(e),
                        level="warning",
                        device_id=device_deployment.device_id,
                    )

                    # Send special message to frontend for confirmation
                    await self._broadcast_update(
                        deployment_id,
                        {
                            "type": "docker_not_installed",
                            "device_id": device_deployment.device_id,
                            "message": str(e),
                            "can_auto_fix": e.can_auto_fix,
                            "fix_action": e.fix_action,
                        },
                    )

                except Exception as e:
                    logger.error(
                        f"Deployment error for {device_deployment.device_id}: {e}"
                    )
                    device_deployment.status = DeploymentStatus.FAILED
                    device_deployment.error = str(e)
                    deployment.status = DeploymentStatus.FAILED
                    await self._broadcast_log(
                        deployment_id,
                        f"Deployment error: {str(e)}",
                        level="error",
                        device_id=device_deployment.device_id,
                    )

                # Record deployment to history
                try:
                    step_records = [
                        StepRecord(
                            id=step.id,
                            name=step.name,
                            status=step.status,
                            started_at=step.started_at,
                            completed_at=step.completed_at,
                            error=step.message if step.status == "failed" else None,
                        )
                        for step in device_deployment.steps
                    ]
                    record = DeploymentRecord(
                        deployment_id=deployment_id,
                        solution_id=deployment.solution_id,
                        device_id=device_deployment.device_id,
                        device_type=device_deployment.type,
                        deployed_version=(
                            config.version if hasattr(config, "version") else "1.0"
                        ),
                        config_version=(
                            config.version if hasattr(config, "version") else "1.0"
                        ),
                        status=(
                            "completed"
                            if device_deployment.status == DeploymentStatus.COMPLETED
                            else "failed"
                        ),
                        deployed_at=datetime.utcnow(),
                        metadata={
                            "device_name": device_deployment.name,
                            "error": (
                                device_deployment.error
                                if device_deployment.error
                                else None
                            ),
                        },
                        steps=step_records,
                    )
                    await deployment_history.record_deployment(record)
                except Exception as history_error:
                    logger.error(
                        f"Failed to record deployment history: {history_error}"
                    )

                await self._broadcast_update(
                    deployment_id,
                    {
                        "type": "device_completed",
                        "device_id": device_deployment.device_id,
                        "status": device_deployment.status.value,
                    },
                )

                if device_deployment.status == DeploymentStatus.FAILED:
                    break

            # All devices completed
            if deployment.status != DeploymentStatus.FAILED:
                if all(
                    d.status == DeploymentStatus.COMPLETED for d in deployment.devices
                ):
                    deployment.status = DeploymentStatus.COMPLETED

            deployment.completed_at = datetime.utcnow()

            # Update stats
            if deployment.status == DeploymentStatus.COMPLETED:
                solution.intro.stats.deployed_count += 1

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            deployment.status = DeploymentStatus.FAILED
            await self._broadcast_log(
                deployment_id, f"Deployment error: {str(e)}", level="error"
            )

        finally:
            # Move to completed
            self.completed_deployments.insert(0, deployment)
            if len(self.completed_deployments) > 100:
                self.completed_deployments.pop()

            if deployment_id in self._running_tasks:
                del self._running_tasks[deployment_id]

            await self._broadcast_update(
                deployment_id,
                {
                    "type": "deployment_completed",
                    "status": deployment.status.value,
                },
            )

    async def cancel_deployment(self, deployment_id: str):
        """Cancel a running deployment"""
        deployment = self.active_deployments.get(deployment_id)
        if deployment:
            deployment.status = DeploymentStatus.CANCELLED
            await self._broadcast_log(
                deployment_id, "Deployment cancelled by user", level="warning"
            )

            # Cancel the task
            if deployment_id in self._running_tasks:
                self._running_tasks[deployment_id].cancel()

    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment by ID"""
        if deployment_id in self.active_deployments:
            return self.active_deployments[deployment_id]

        for deployment in self.completed_deployments:
            if deployment.id == deployment_id:
                return deployment

        return None

    def list_deployments(self, limit: int = 10) -> List[Deployment]:
        """List recent deployments"""
        all_deployments = (
            list(self.active_deployments.values()) + self.completed_deployments
        )
        all_deployments.sort(key=lambda d: d.started_at, reverse=True)
        return all_deployments[:limit]

    async def _broadcast_update(self, deployment_id: str, message: dict):
        """Broadcast update to WebSocket clients"""
        if self._websocket_manager:
            message["deployment_id"] = deployment_id
            message["timestamp"] = datetime.utcnow().isoformat()
            await self._websocket_manager.broadcast(deployment_id, message)

    async def _broadcast_log(
        self,
        deployment_id: str,
        message: str,
        level: str = "info",
        device_id: str = None,
        step_id: str = None,
    ):
        """Add log to deployment and broadcast to WebSocket clients"""
        deployment = self.active_deployments.get(deployment_id)
        if deployment:
            deployment.add_log(
                message, level=level, device_id=device_id, step_id=step_id
            )

        await self._broadcast_update(
            deployment_id,
            {
                "type": "log",
                "level": level,
                "message": message,
                "device_id": device_id,
                "step_id": step_id,
            },
        )


# Global instance
deployment_engine = DeploymentEngine()
