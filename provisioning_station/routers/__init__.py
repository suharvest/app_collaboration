"""
API routers
"""

from . import (
    deployments,
    device_management,
    devices,
    docker_devices,
    preview,
    solutions,
    versions,
    websocket,
)

__all__ = ["solutions", "devices", "deployments", "websocket", "versions", "device_management", "preview", "docker_devices"]
