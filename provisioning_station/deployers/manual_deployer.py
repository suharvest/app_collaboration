"""
Manual deployment deployer - for steps that users perform manually
"""

import logging
from typing import Any, Callable, Dict, Optional

from ..models.device import DeviceConfig
from .base import BaseDeployer

logger = logging.getLogger(__name__)


class ManualDeployer(BaseDeployer):
    """Manual deployment - user performs steps manually"""

    device_type = "manual"
    ui_traits = {
        "connection": "none",
        "auto_deploy": False,
        "renderer": None,
        "has_targets": False,
        "show_model_selection": False,
        "show_service_warning": False,
        "connection_scope": "device",
    }

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        For manual deployments, we just mark the deployment as successful
        since the user is expected to perform the steps manually.
        """
        try:
            await self._report_progress(
                progress_callback,
                "manual_steps",
                0,
                "Manual deployment - please follow the instructions",
            )

            # For manual deployments, we consider them successful immediately
            # The user is expected to follow the on-screen instructions
            await self._report_progress(
                progress_callback,
                "manual_steps",
                100,
                "Manual steps completed - please verify the results",
            )

            return True

        except Exception as e:
            logger.error(f"Manual deployment error: {e}")
            await self._report_progress(
                progress_callback,
                "manual_steps",
                0,
                f"Error: {str(e)}",
            )
            return False
