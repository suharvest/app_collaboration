"""
Deployment implementations
"""

from .base import BaseDeployer
from .docker_deployer import DockerDeployer
from .docker_remote_deployer import DockerRemoteDeployer
from .esp32_deployer import ESP32Deployer
from .manual_deployer import ManualDeployer

# Node-RED deployers
from .nodered_deployer import NodeRedDeployer
from .preview_deployer import PreviewDeployer

# reCamera C++ deployer
from .recamera_cpp_deployer import ReCameraCppDeployer
from .recamera_nodered_deployer import ReCameraNodeRedDeployer
from .script_deployer import ScriptDeployer
from .ssh_deployer import SSHDeployer

__all__ = [
    # Base classes
    "BaseDeployer",
    "NodeRedDeployer",
    # Concrete deployers
    "ESP32Deployer",
    "DockerDeployer",
    "DockerRemoteDeployer",
    "SSHDeployer",
    "ScriptDeployer",
    "ManualDeployer",
    "PreviewDeployer",
    # reCamera-specific deployers
    "ReCameraNodeRedDeployer",
    "ReCameraCppDeployer",
]
