"""
Serial Camera deployer - thin wrapper for serial_camera type steps

Similar to ManualDeployer: marks the step as complete immediately,
since the actual camera interaction happens via the serial camera API.
"""

import logging
from typing import Any, Callable, Dict, Optional

from ..models.device import DeviceConfig
from .base import BaseDeployer

logger = logging.getLogger(__name__)


class SerialCameraDeployer(BaseDeployer):
    """Serial camera deployment - interactive step handled by frontend."""

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        try:
            await self._report_progress(
                progress_callback,
                "serial_camera",
                0,
                "Serial camera step ready - use the camera interface",
            )

            await self._report_progress(
                progress_callback,
                "serial_camera",
                100,
                "Serial camera step completed",
            )

            return True

        except Exception as e:
            logger.error(f"Serial camera deployer error: {e}")
            await self._report_progress(
                progress_callback,
                "serial_camera",
                0,
                f"Error: {str(e)}",
            )
            return False
