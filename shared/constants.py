"""
Shared constants that must stay synchronized between frontend and backend.

IMPORTANT: When modifying these values, ensure corresponding updates are made to:
- Frontend: frontend/src/modules/api.js (getBackendPort fallback, REQUEST_TIMEOUT)
- Backend: provisioning_station/config.py (Settings.port)
- Tests: tests/integration/test_port_configuration.py

These constants are the source of truth for the codebase.
"""

# Default backend server port
# Frontend fallback: api.js:54,64 (hardcoded 3260)
# Backend default: config.py:68 (port: int = 3260)
DEFAULT_PORT: int = 3260

# API version prefix (for future versioning)
API_VERSION: str = "v1"

# Supported language codes
SUPPORTED_LANGUAGES: list[str] = ["en", "zh"]

# Default language for API responses
DEFAULT_LANGUAGE: str = "zh"

# Request timeout in milliseconds
# Frontend: api.js:137 (REQUEST_TIMEOUT = 30000)
REQUEST_TIMEOUT_MS: int = 30000

# WebSocket message types
# These should match the frontend LogsWebSocket handler in api.js:1105-1147
WS_MESSAGE_TYPES: list[str] = [
    "log",
    "status",
    "progress",
    "device_started",
    "pre_check_started",
    "pre_check_passed",
    "pre_check_failed",
    "device_completed",
    "deployment_completed",
    "docker_not_installed",
    "ping",
    "pong",
]

# Device deployment types
# Backend: models/deployment.py DeviceType enum
# Frontend: test_deployment_api_contract.py:61-66
DEVICE_TYPES: list[str] = [
    "docker_local",
    "docker_deploy",
    "docker_remote",
    "esp32_usb",
    "himax_usb",
    "ssh_deb",
    "manual",
    "script",
    "preview",
    "recamera_cpp",
    "recamera_nodered",
]

# Deployment status values
DEPLOYMENT_STATUSES: list[str] = [
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
]

# Difficulty levels
DIFFICULTY_LEVELS: list[str] = [
    "beginner",
    "intermediate",
    "advanced",
]
