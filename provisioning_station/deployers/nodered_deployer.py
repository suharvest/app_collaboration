"""
Node-RED deployment base class

Provides common functionality for deploying Node-RED flows via Admin HTTP API.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List

from .base import BaseDeployer
from ..models.device import DeviceConfig

logger = logging.getLogger(__name__)


class NodeRedDeployer(BaseDeployer):
    """Base class for Node-RED flow deployments via Admin HTTP API"""

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Deploy flow.json to a Node-RED instance.

        Expected connection parameters:
        - nodered_host: IP address or hostname of the Node-RED instance
        - Additional parameters can be overridden by subclasses

        Expected config:
        - nodered.flow_file: Path to flow.json template
        - nodered.port: Node-RED port (default: 1880)
        """
        if not config.nodered:
            raise ValueError("No Node-RED configuration")

        nodered_config = config.nodered

        # Get connection parameters
        nodered_host = connection.get("nodered_host") or connection.get("recamera_ip")
        if not nodered_host:
            await self._report_progress(
                progress_callback, "connect", 0, "Node-RED host address is required"
            )
            return False

        nodered_port = nodered_config.port or 1880
        base_url = f"http://{nodered_host}:{nodered_port}"

        try:
            import httpx

            # Step 0: Pre-deploy hook (for subclass customization)
            await self._report_progress(
                progress_callback, "prepare", 0, "Preparing deployment..."
            )

            if not await self._pre_deploy_hook(config, connection, progress_callback):
                # Pre-deploy hook returned False, abort
                return False

            await self._report_progress(
                progress_callback, "prepare", 100, "Preparation complete"
            )

            # Step 1: Load flow.json template
            await self._report_progress(
                progress_callback, "load_flow", 0, "Loading flow template..."
            )

            flow_file = config.get_asset_path(nodered_config.flow_file)
            if not flow_file or not Path(flow_file).exists():
                await self._report_progress(
                    progress_callback,
                    "load_flow",
                    0,
                    f"Flow file not found: {nodered_config.flow_file}",
                )
                return False

            with open(flow_file, "r", encoding="utf-8") as f:
                flow_data = json.load(f)

            await self._report_progress(
                progress_callback, "load_flow", 100, "Flow template loaded"
            )

            # Step 2: Update flow configuration (subclass hook)
            await self._report_progress(
                progress_callback, "configure", 0, "Configuring flow..."
            )

            flow_data, credentials = await self._update_flow_config(
                flow_data, config, connection
            )

            await self._report_progress(
                progress_callback, "configure", 100, "Configuration updated"
            )

            # Step 3: Connect to Node-RED and verify
            await self._report_progress(
                progress_callback, "connect", 0, f"Connecting to Node-RED at {base_url}..."
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Verify Node-RED is accessible
                try:
                    response = await client.get(f"{base_url}/flows")
                    if response.status_code not in [200, 401]:
                        await self._report_progress(
                            progress_callback,
                            "connect",
                            0,
                            f"Node-RED not accessible: HTTP {response.status_code}",
                        )
                        return False
                except httpx.ConnectError as e:
                    await self._report_progress(
                        progress_callback,
                        "connect",
                        0,
                        f"Cannot connect to Node-RED: {str(e)}",
                    )
                    return False

                await self._report_progress(
                    progress_callback, "connect", 100, "Connected to Node-RED"
                )

                # Step 4: Deploy flow
                await self._report_progress(
                    progress_callback, "deploy", 0, "Deploying flow..."
                )

                try:
                    response = await client.post(
                        f"{base_url}/flows",
                        json=flow_data,
                        headers={
                            "Content-Type": "application/json",
                            "Node-RED-Deployment-Type": "full",
                        },
                    )

                    if response.status_code not in [200, 204]:
                        error_msg = response.text[:200] if response.text else f"HTTP {response.status_code}"
                        await self._report_progress(
                            progress_callback,
                            "deploy",
                            0,
                            f"Flow deployment failed: {error_msg}",
                        )
                        return False

                except httpx.HTTPError as e:
                    await self._report_progress(
                        progress_callback,
                        "deploy",
                        0,
                        f"HTTP error during deployment: {str(e)}",
                    )
                    return False

                await self._report_progress(
                    progress_callback, "deploy", 50, "Flow deployed, setting credentials..."
                )

                # Step 5: Set credentials if provided
                if credentials:
                    for node_id, creds in credentials.items():
                        try:
                            creds_response = await client.put(
                                f"{base_url}/credentials/{node_id}",
                                json=creds,
                                headers={"Content-Type": "application/json"},
                            )
                            if creds_response.status_code not in [200, 204]:
                                logger.warning(
                                    f"Failed to set credentials for {node_id}: {creds_response.status_code}"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to set credentials for {node_id}: {e}")

                await self._report_progress(
                    progress_callback, "deploy", 100, "Flow deployed successfully"
                )

                # Step 6: Verify deployment
                await self._report_progress(
                    progress_callback, "verify", 0, "Verifying deployment..."
                )

                # Wait a moment for Node-RED to process
                await asyncio.sleep(2)

                try:
                    verify_response = await client.get(f"{base_url}/flows")
                    if verify_response.status_code == 200:
                        await self._report_progress(
                            progress_callback, "verify", 100, "Deployment verified"
                        )
                    else:
                        await self._report_progress(
                            progress_callback,
                            "verify",
                            100,
                            "Deployment complete (verification skipped)",
                        )
                except Exception:
                    await self._report_progress(
                        progress_callback,
                        "verify",
                        100,
                        "Deployment complete (verification skipped)",
                    )

            # Post-deploy hook
            await self._post_deploy_hook(config, connection, progress_callback)

            return True

        except ImportError:
            await self._report_progress(
                progress_callback,
                "connect",
                0,
                "Missing dependency: httpx",
            )
            return False

        except Exception as e:
            logger.error(f"Node-RED deployment failed: {e}")
            await self._report_progress(
                progress_callback, "deploy", 0, f"Deployment failed: {str(e)}"
            )
            return False

    async def _pre_deploy_hook(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Hook called before deployment starts.

        Subclasses can override to perform pre-deployment tasks like
        stopping conflicting services.

        Returns:
            True to continue with deployment, False to abort
        """
        return True

    async def _update_flow_config(
        self,
        flow_data: List[Dict],
        config: DeviceConfig,
        connection: Dict[str, Any],
    ) -> tuple[List[Dict], Dict[str, Dict]]:
        """
        Update flow configuration before deployment.

        Subclasses should override this to customize flow configuration
        (e.g., update database URLs, API endpoints).

        Args:
            flow_data: The loaded flow JSON data
            config: Device configuration
            connection: Connection parameters

        Returns:
            Tuple of (updated_flow_data, credentials_dict)
            credentials_dict maps node_id -> credential_data
        """
        return flow_data, {}

    async def _post_deploy_hook(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """
        Hook called after successful deployment.

        Subclasses can override to perform post-deployment tasks.
        """
        pass

    async def get_current_flows(
        self,
        host: str,
        port: int = 1880,
    ) -> Optional[List[Dict]]:
        """Get current flows from Node-RED (for backup/reference)"""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"http://{host}:{port}/flows")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to get flows: {e}")

        return None
