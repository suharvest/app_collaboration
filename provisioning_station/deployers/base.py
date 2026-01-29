"""
Base deployer abstract class
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from ..models.device import DeviceConfig


class BaseDeployer(ABC):
    """Abstract base class for deployers"""

    @abstractmethod
    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Execute deployment

        Args:
            config: Device configuration
            connection: Connection information (port, host, credentials, etc.)
            progress_callback: Async callback for progress updates
                              Signature: (step_id: str, progress: int, message: str) -> None

        Returns:
            True if deployment successful, False otherwise
        """
        pass

    async def _report_progress(
        self,
        callback: Optional[Callable],
        step_id: str,
        progress: int,
        message: str,
    ):
        """Helper to report progress if callback is set"""
        if callback:
            await callback(step_id, progress, message)
