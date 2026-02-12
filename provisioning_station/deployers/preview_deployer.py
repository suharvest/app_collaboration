"""
Preview Deployer - For live preview steps

Preview steps are interactive and don't require traditional deployment.
The deployer just validates the configuration and marks the step as ready.
"""

import logging
from typing import Any, Callable, Dict, Optional

from ..models.device import DeviceConfig
from .base import BaseDeployer

logger = logging.getLogger(__name__)


class PreviewDeployer(BaseDeployer):
    """
    Preview deployment - for live video/MQTT preview steps.

    Preview steps are interactive:
    - User configures RTSP URL, MQTT broker, etc.
    - User clicks "Start Preview" to connect
    - Video and inference results are displayed in real-time
    - User marks step as complete after verification

    The deployer just validates that the preview can be started.
    """

    device_type = "preview"
    ui_traits = {
        "connection": "none",
        "auto_deploy": False,
        "renderer": "preview",
        "has_targets": False,
        "show_model_selection": False,
        "show_service_warning": False,
        "connection_scope": "device",
    }
    steps = [
        {"id": "preview_setup", "name": "Preview Setup", "name_zh": "预览设置"},
    ]

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        For preview deployments, we validate and prepare the preview.

        The actual preview is handled by the frontend using the preview
        WebSocket and stream proxy APIs.
        """
        try:
            await self._report_progress(
                progress_callback,
                "preview_setup",
                0,
                "Preparing live preview...",
            )

            # Get preview configuration from connection
            preview_config = connection.get("preview_config", {})
            rtsp_url = connection.get("rtsp_url")
            mqtt_broker = connection.get("mqtt_broker")
            mqtt_topic = connection.get("mqtt_topic")

            # Log configuration
            if rtsp_url:
                logger.info(f"Preview RTSP URL: {rtsp_url}")
                await self._report_progress(
                    progress_callback,
                    "preview_setup",
                    30,
                    f"RTSP stream configured: {rtsp_url}",
                )

            if mqtt_broker and mqtt_topic:
                logger.info(f"Preview MQTT: {mqtt_broker} - {mqtt_topic}")
                await self._report_progress(
                    progress_callback,
                    "preview_setup",
                    60,
                    f"MQTT configured: {mqtt_broker}/{mqtt_topic}",
                )

            # Preview is ready - actual connection handled by frontend
            await self._report_progress(
                progress_callback,
                "preview_setup",
                100,
                "Preview ready - click 'Start Preview' to connect",
            )

            return True

        except Exception as e:
            logger.error(f"Preview deployment error: {e}")
            await self._report_progress(
                progress_callback,
                "preview_setup",
                0,
                f"Error: {str(e)}",
            )
            return False
