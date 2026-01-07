"""
Deployment orchestration engine
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from ..models.solution import Solution
from ..models.deployment import Deployment, DeviceDeployment, DeploymentStatus, StepStatus
from ..deployers.base import BaseDeployer
from ..deployers.esp32_deployer import ESP32Deployer
from ..deployers.docker_deployer import DockerDeployer
from ..deployers.ssh_deployer import SSHDeployer
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
            "docker_local": DockerDeployer(),
            "ssh_deb": SSHDeployer(),
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
    ) -> str:
        """Start a new deployment"""
        deployment_id = str(uuid4())

        # Initialize deployment state
        deployment = Deployment(
            id=deployment_id,
            solution_id=solution.id,
            started_at=datetime.utcnow(),
            status=DeploymentStatus.RUNNING,
            devices=[],
        )

        # Determine which devices to deploy
        deploy_order = solution.deployment.order
        if selected_devices:
            deploy_order = [d for d in deploy_order if d in selected_devices]

        # Initialize device deployments
        for device_id in deploy_order:
            device_ref = next(
                (d for d in solution.deployment.devices if d.id == device_id), None
            )
            if not device_ref:
                continue

            # Load device config to get steps
            config = await solution_manager.load_device_config(
                solution.id, device_ref.config_file
            )
            if not config:
                continue

            # Check if we have connection info for this device
            if device_id not in device_connections and device_ref.required:
                # Skip if required device has no connection
                logger.warning(f"No connection info for required device: {device_id}")
                continue

            device_deployment = DeviceDeployment(
                device_id=device_id,
                name=device_ref.name,
                type=device_ref.type,
                status=DeploymentStatus.PENDING,
                connection=device_connections.get(device_id),
                steps=[
                    StepStatus(id=step.id, name=step.name)
                    for step in config.steps
                ],
            )
            deployment.devices.append(device_deployment)

        if not deployment.devices:
            raise ValueError("No devices to deploy")

        self.active_deployments[deployment_id] = deployment

        # Start deployment in background
        task = asyncio.create_task(self._run_deployment(deployment_id))
        self._running_tasks[deployment_id] = task

        deployment.add_log(
            f"Started deployment for solution: {solution.id}",
            level="info",
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
            deployment.add_log("Solution not found", level="error")
            return

        try:
            for device_deployment in deployment.devices:
                if deployment.status == DeploymentStatus.CANCELLED:
                    break

                device_deployment.status = DeploymentStatus.RUNNING
                device_deployment.started_at = datetime.utcnow()

                await self._broadcast_update(deployment_id, {
                    "type": "device_started",
                    "device_id": device_deployment.device_id,
                })

                # Find device ref and load config
                device_ref = next(
                    (d for d in solution.deployment.devices if d.id == device_deployment.device_id),
                    None,
                )
                if not device_ref:
                    device_deployment.status = DeploymentStatus.FAILED
                    device_deployment.error = "Device reference not found"
                    continue

                config = await solution_manager.load_device_config(
                    solution.id, device_ref.config_file
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

                # Create progress callback
                async def progress_callback(step_id: str, progress: int, message: str):
                    deployment.update_step(
                        device_deployment.device_id,
                        step_id,
                        "running" if progress < 100 else "completed",
                        progress,
                        message,
                    )
                    deployment.add_log(
                        message,
                        device_id=device_deployment.device_id,
                        step_id=step_id,
                    )
                    await self._broadcast_update(deployment_id, {
                        "type": "progress",
                        "device_id": device_deployment.device_id,
                        "step_id": step_id,
                        "progress": progress,
                        "message": message,
                    })

                # Execute deployment
                try:
                    success = await deployer.deploy(
                        config=config,
                        connection=device_deployment.connection,
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
                    else:
                        device_deployment.status = DeploymentStatus.FAILED
                        deployment.status = DeploymentStatus.FAILED

                except Exception as e:
                    logger.error(f"Deployment error for {device_deployment.device_id}: {e}")
                    device_deployment.status = DeploymentStatus.FAILED
                    device_deployment.error = str(e)
                    deployment.status = DeploymentStatus.FAILED

                await self._broadcast_update(deployment_id, {
                    "type": "device_completed",
                    "device_id": device_deployment.device_id,
                    "status": device_deployment.status.value,
                })

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
            deployment.add_log(str(e), level="error")

        finally:
            # Move to completed
            self.completed_deployments.insert(0, deployment)
            if len(self.completed_deployments) > 100:
                self.completed_deployments.pop()

            if deployment_id in self._running_tasks:
                del self._running_tasks[deployment_id]

            await self._broadcast_update(deployment_id, {
                "type": "deployment_completed",
                "status": deployment.status.value,
            })

    async def cancel_deployment(self, deployment_id: str):
        """Cancel a running deployment"""
        deployment = self.active_deployments.get(deployment_id)
        if deployment:
            deployment.status = DeploymentStatus.CANCELLED
            deployment.add_log("Deployment cancelled by user", level="warning")

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


# Global instance
deployment_engine = DeploymentEngine()
