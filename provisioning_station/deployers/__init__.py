"""
Deployment implementations
"""

from .base import BaseDeployer
from .esp32_deployer import ESP32Deployer
from .docker_deployer import DockerDeployer
from .docker_remote_deployer import DockerRemoteDeployer
from .ssh_deployer import SSHDeployer
from .script_deployer import ScriptDeployer
from .manual_deployer import ManualDeployer
from .preview_deployer import PreviewDeployer

# Node-RED deployers
from .nodered_deployer import NodeRedDeployer
from .recamera_nodered_deployer import ReCameraNodeRedDeployer

# reCamera C++ deployer
from .recamera_cpp_deployer import ReCameraCppDeployer

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
