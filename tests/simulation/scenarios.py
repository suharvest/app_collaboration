"""
Pre-built failure/behavior scenarios for SimulationDeployer.

Each scenario is a dict that can be passed directly to SimulationDeployer:
    sim = SimulationDeployer("esp32_usb", scenario=SCENARIOS["serial_port_busy"])

Scenarios are organized by failure category to help test all error paths.
"""

from typing import Any, Dict

# ---------------------------------------------------------------------------
# Success scenarios
# ---------------------------------------------------------------------------

FAST_SUCCESS: Dict[str, Any] = {
    "step_delay": 0.0,
    "record_calls": True,
}

REALISTIC_SUCCESS: Dict[str, Any] = {
    "step_delay": 0.3,
    "progress_increments": 5,
    "record_calls": True,
}

# ---------------------------------------------------------------------------
# Connection failure scenarios
# ---------------------------------------------------------------------------

CONNECTION_TIMEOUT: Dict[str, Any] = {
    "connection_validator": lambda conn: False,
    "record_calls": True,
}

SSH_AUTH_FAILURE: Dict[str, Any] = {
    "fail_at": {"connect": "Authentication failed: Invalid credentials for root@192.168.42.1"},
    "record_calls": True,
}

SSH_HOST_UNREACHABLE: Dict[str, Any] = {
    "fail_at": {"connect": "Connection refused: No route to host 192.168.42.1"},
    "record_calls": True,
}

# ---------------------------------------------------------------------------
# ESP32/Himax USB scenarios
# ---------------------------------------------------------------------------

SERIAL_PORT_BUSY: Dict[str, Any] = {
    "fail_at": {"detect": "Serial port /dev/ttyACM1 is busy (used by another process)"},
    "record_calls": True,
}

FLASH_WRITE_ERROR: Dict[str, Any] = {
    "fail_at": {"flash": "Flash write failed at address 0x10000: chip not responding"},
    "fail_at_progress": {"flash": 35},
    "record_calls": True,
}

FLASH_VERIFY_FAIL: Dict[str, Any] = {
    "fail_at": {"verify": "Verification failed: checksum mismatch at 0x20000"},
    "record_calls": True,
}

ERASE_TIMEOUT: Dict[str, Any] = {
    "fail_at": {"erase": "Erase flash timed out after 60s. Device may need manual reset."},
    "record_calls": True,
}

# ---------------------------------------------------------------------------
# Docker scenarios
# ---------------------------------------------------------------------------

DOCKER_PULL_TIMEOUT: Dict[str, Any] = {
    "fail_at": {"pull_images": "Timeout pulling image: registry.example.com/app:latest"},
    "fail_at_progress": {"pull_images": 20},
    "record_calls": True,
}

DOCKER_PULL_AUTH_ERROR: Dict[str, Any] = {
    "fail_at": {"pull_images": "Error response from daemon: unauthorized: authentication required"},
    "record_calls": True,
}

DOCKER_HEALTH_CHECK_FAIL: Dict[str, Any] = {
    "fail_at": {"health_check": "Service 'webapp' health check failed after 60s"},
    "record_calls": True,
}

DOCKER_VOLUME_ERROR: Dict[str, Any] = {
    "fail_at": {"create_volumes": "Error creating volume: permission denied"},
    "record_calls": True,
}

DOCKER_START_FAIL: Dict[str, Any] = {
    "fail_at": {"start_services": "Container exited with code 1: OOM killed"},
    "record_calls": True,
}

# ---------------------------------------------------------------------------
# SSH/reCamera scenarios
# ---------------------------------------------------------------------------

SSH_TRANSFER_FAIL: Dict[str, Any] = {
    "fail_at": {"transfer": "SCP transfer failed: Connection reset by peer"},
    "fail_at_progress": {"transfer": 60},
    "record_calls": True,
}

SSH_INSTALL_FAIL: Dict[str, Any] = {
    "fail_at": {"install": "dpkg: error: package architecture (armhf) does not match system (aarch64)"},
    "record_calls": True,
}

RECAMERA_PRECHECK_FAIL: Dict[str, Any] = {
    "fail_at": {"precheck": "Insufficient disk space: 12MB available, 50MB required"},
    "record_calls": True,
}

RECAMERA_MODEL_DEPLOY_FAIL: Dict[str, Any] = {
    "fail_at": {"models": "Model file not found: yolov5s.cvimodel"},
    "record_calls": True,
}

RECAMERA_SERVICE_START_FAIL: Dict[str, Any] = {
    "fail_at": {"start": "Service failed to start: exit code 127 (binary not found)"},
    "record_calls": True,
}

NODERED_FLOW_LOAD_FAIL: Dict[str, Any] = {
    "fail_at": {"load_flow": "Invalid flow.json: missing required node type 'mqtt-broker'"},
    "record_calls": True,
}

# ---------------------------------------------------------------------------
# Script scenarios
# ---------------------------------------------------------------------------

SCRIPT_SETUP_FAIL: Dict[str, Any] = {
    "fail_at": {"setup": "npm install failed: EACCES permission denied"},
    "record_calls": True,
}

SCRIPT_HEALTH_CHECK_TIMEOUT: Dict[str, Any] = {
    "fail_at": {"health_check": "Health check timed out: no log output matching 'Server started' within 30s"},
    "record_calls": True,
}

# ---------------------------------------------------------------------------
# HA Integration scenarios
# ---------------------------------------------------------------------------

HA_AUTH_FAIL: Dict[str, Any] = {
    "fail_at": {"auth": "Home Assistant authentication failed: invalid long-lived access token"},
    "record_calls": True,
}

HA_RESTART_TIMEOUT: Dict[str, Any] = {
    "fail_at": {"restart": "Home Assistant restart timed out after 120s"},
    "record_calls": True,
}

# ---------------------------------------------------------------------------
# Post-deploy failure
# ---------------------------------------------------------------------------

DEPLOY_RETURNS_FALSE: Dict[str, Any] = {
    "step_delay": 0.0,
    "final_failure": True,
    "record_calls": True,
}


# ---------------------------------------------------------------------------
# Convenience lookup
# ---------------------------------------------------------------------------

SCENARIOS: Dict[str, Dict[str, Any]] = {
    # Success
    "fast_success": FAST_SUCCESS,
    "realistic_success": REALISTIC_SUCCESS,
    # Connection
    "connection_timeout": CONNECTION_TIMEOUT,
    "ssh_auth_failure": SSH_AUTH_FAILURE,
    "ssh_host_unreachable": SSH_HOST_UNREACHABLE,
    # USB/Serial
    "serial_port_busy": SERIAL_PORT_BUSY,
    "flash_write_error": FLASH_WRITE_ERROR,
    "flash_verify_fail": FLASH_VERIFY_FAIL,
    "erase_timeout": ERASE_TIMEOUT,
    # Docker
    "docker_pull_timeout": DOCKER_PULL_TIMEOUT,
    "docker_pull_auth_error": DOCKER_PULL_AUTH_ERROR,
    "docker_health_check_fail": DOCKER_HEALTH_CHECK_FAIL,
    "docker_volume_error": DOCKER_VOLUME_ERROR,
    "docker_start_fail": DOCKER_START_FAIL,
    # SSH/reCamera
    "ssh_transfer_fail": SSH_TRANSFER_FAIL,
    "ssh_install_fail": SSH_INSTALL_FAIL,
    "recamera_precheck_fail": RECAMERA_PRECHECK_FAIL,
    "recamera_model_deploy_fail": RECAMERA_MODEL_DEPLOY_FAIL,
    "recamera_service_start_fail": RECAMERA_SERVICE_START_FAIL,
    "nodered_flow_load_fail": NODERED_FLOW_LOAD_FAIL,
    # Script
    "script_setup_fail": SCRIPT_SETUP_FAIL,
    "script_health_check_timeout": SCRIPT_HEALTH_CHECK_TIMEOUT,
    # HA
    "ha_auth_fail": HA_AUTH_FAIL,
    "ha_restart_timeout": HA_RESTART_TIMEOUT,
    # Post-deploy
    "deploy_returns_false": DEPLOY_RETURNS_FALSE,
}
