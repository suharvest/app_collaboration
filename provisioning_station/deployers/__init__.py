"""
Deployment implementations

Auto-discovers all deployer classes with a non-empty ``device_type`` and
registers them in ``DEPLOYER_REGISTRY``.
"""

import importlib
import pkgutil

from .base import BaseDeployer

# ---------------------------------------------------------------------------
# Auto-discovery: scan all modules in this package and collect deployers
# ---------------------------------------------------------------------------

DEPLOYER_REGISTRY: dict[str, BaseDeployer] = {}

for _, module_name, _ in pkgutil.iter_modules(__path__):
    if module_name == "base":
        continue
    module = importlib.import_module(f".{module_name}", __package__)
    for attr_name in dir(module):
        cls = getattr(module, attr_name)
        if (
            isinstance(cls, type)
            and issubclass(cls, BaseDeployer)
            and cls is not BaseDeployer
            and getattr(cls, "device_type", "")
        ):
            DEPLOYER_REGISTRY[cls.device_type] = cls()

# ---------------------------------------------------------------------------
# Backward-compatible named exports
# ---------------------------------------------------------------------------

from .docker_deployer import DockerDeployer
from .docker_remote_deployer import DockerRemoteDeployer, RemoteDockerNotInstalled
from .esp32_deployer import ESP32Deployer
from .ha_integration_deployer import HAIntegrationDeployer
from .himax_deployer import HimaxDeployer
from .manual_deployer import ManualDeployer
from .nodered_deployer import NodeRedDeployer
from .preview_deployer import PreviewDeployer
from .recamera_cpp_deployer import ReCameraCppDeployer
from .recamera_nodered_deployer import ReCameraNodeRedDeployer
from .script_deployer import ScriptDeployer
from .serial_camera_deployer import SerialCameraDeployer
from .ssh_deployer import SSHDeployer
from .ssh_mixin import SSHMixin

__all__ = [
    # Registry
    "DEPLOYER_REGISTRY",
    # Base classes
    "BaseDeployer",
    "NodeRedDeployer",
    "SSHMixin",
    # Concrete deployers
    "ESP32Deployer",
    "DockerDeployer",
    "DockerRemoteDeployer",
    "RemoteDockerNotInstalled",
    "SSHDeployer",
    "ScriptDeployer",
    "ManualDeployer",
    "PreviewDeployer",
    "HimaxDeployer",
    "HAIntegrationDeployer",
    "SerialCameraDeployer",
    # reCamera-specific deployers
    "ReCameraNodeRedDeployer",
    "ReCameraCppDeployer",
]
