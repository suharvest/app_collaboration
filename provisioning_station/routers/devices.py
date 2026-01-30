"""
Device detection API routes
"""

from typing import List

from fastapi import APIRouter, HTTPException, Query

from ..models.api import DetectedDevice, DeviceConnectionRequest
from ..services.device_detector import device_detector
from ..services.mdns_scanner import mdns_scanner
from ..services.solution_manager import solution_manager

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("/catalog")
async def get_device_catalog():
    """Get device catalog list for dropdown selectors.

    Returns all devices from devices/catalog.yaml for use in
    the required_devices selector on the management UI.
    """
    return {"devices": solution_manager.get_device_catalog_list()}


@router.get("/scan-mdns")
async def scan_mdns_devices(
    timeout: float = Query(3.0, ge=1.0, le=10.0, description="Scan timeout in seconds"),
    filter_known: bool = Query(True, description="Only return known IoT devices"),
):
    """Scan the local network for SSH-enabled devices using mDNS.

    Returns devices that advertise SSH services (_ssh._tcp.local).
    By default, filters to known IoT device patterns (Raspberry Pi, Jetson, etc.).

    Returns:
        List of devices with hostname, IP address, and port
    """
    devices = await mdns_scanner.scan_ssh_devices(
        timeout=timeout, filter_known=filter_known
    )
    return {"devices": devices}


@router.get("/detect/{solution_id}", response_model=List[DetectedDevice])
async def detect_devices(
    solution_id: str,
    lang: str = Query("en", pattern="^(en|zh)$"),
    preset: str = Query(None, description="Preset ID to get devices from"),
):
    """Detect devices for a solution"""
    solution = solution_manager.get_solution(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    # Get devices from preset or deployment
    devices = []
    if preset and solution.intro and solution.intro.presets:
        # Find the preset and get its devices
        for p in solution.intro.presets:
            if p.id == preset:
                devices = p.devices or []
                break

    # Fallback to deployment.devices if no preset or preset not found
    if not devices:
        devices = solution.deployment.devices if solution.deployment else []

    # Load device configs and detect
    detected = []
    for device_ref in devices:
        # Build section info if available
        section_info = None
        if device_ref.section:
            section = device_ref.section
            section_info = {
                "title": (
                    section.title
                    if lang == "en"
                    else (section.title_zh or section.title)
                ),
            }
            if section.wiring:
                section_info["wiring"] = {
                    "image": (
                        f"/api/solutions/{solution_id}/assets/{section.wiring.image}"
                        if section.wiring.image
                        else None
                    ),
                    "steps": (
                        section.wiring.steps_zh
                        if lang == "zh"
                        else section.wiring.steps
                    ),
                }

        # Handle devices without config files (manual/script types)
        if not device_ref.config_file:
            # For manual or script types, no detection needed
            detected.append(
                DetectedDevice(
                    config_id=device_ref.id,
                    name=(
                        device_ref.name
                        if lang == "en"
                        else (device_ref.name_zh or device_ref.name)
                    ),
                    name_zh=device_ref.name_zh,
                    type=device_ref.type,
                    status=(
                        "manual_required" if device_ref.type == "manual" else "detected"
                    ),
                    connection_info=None,
                    details=(
                        {
                            "user_inputs": [
                                ui.model_dump() for ui in device_ref.user_inputs
                            ]
                        }
                        if device_ref.user_inputs
                        else None
                    ),
                    section=section_info,
                )
            )
            continue

        config = await solution_manager.load_device_config(
            solution_id, device_ref.config_file
        )
        if config:
            result = await device_detector.detect_device(config)

            detected.append(
                DetectedDevice(
                    config_id=device_ref.id,  # Use device_ref.id, not config.id
                    name=(
                        config.name if lang == "en" else (config.name_zh or config.name)
                    ),
                    name_zh=config.name_zh,
                    type=config.type,
                    status=result["status"],
                    connection_info=result.get("connection_info"),
                    details=result.get("details"),
                    section=section_info,
                )
            )

    return detected


@router.get("/ports")
async def list_serial_ports():
    """List available serial ports"""
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Received request to list serial ports")
    try:
        ports = await device_detector.list_serial_ports()
        logger.info(f"Returning {len(ports)} ports: {[p.get('device') for p in ports]}")
        return {"ports": ports}
    except Exception as e:
        logger.error(f"Error listing serial ports: {e}", exc_info=True)
        return {"ports": [], "error": str(e)}


@router.post("/test-connection")
async def test_connection(request: DeviceConnectionRequest):
    """Test SSH connection to a remote device"""
    host = request.effective_host
    if not host:
        raise HTTPException(status_code=400, detail="Host is required")

    result = await device_detector.test_ssh_connection(
        host=host,
        port=request.port or 22,
        username=request.effective_username or "root",
        password=request.password,
    )

    if result.get("status") == "error":
        error_msg = result.get("details", {}).get("error", "Connection failed")
        raise HTTPException(status_code=400, detail=error_msg)

    return result


@router.post("/{solution_id}/{device_id}/connect")
async def configure_device_connection(
    solution_id: str,
    device_id: str,
    request: DeviceConnectionRequest,
):
    """Configure manual device connection (for SSH devices)"""
    solution = solution_manager.get_solution(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    # Find device ref from presets
    device_ref = solution_manager.find_device_in_solution(solution, device_id)

    if not device_ref:
        raise HTTPException(status_code=404, detail="Device not found")

    # Load device config
    config = await solution_manager.load_device_config(
        solution_id, device_ref.config_file
    )
    if not config:
        raise HTTPException(status_code=404, detail="Device config not found")

    # Test connection based on device type
    if config.type == "ssh_deb":
        result = await device_detector.test_ssh_connection(
            host=request.ip_address,
            port=request.port or 22,
            username=request.username or "root",
            password=request.password,
            key_file=request.ssh_key,
        )
    elif config.type == "esp32_usb":
        result = await device_detector.test_serial_port(request.serial_port)
    else:
        result = {"status": "detected", "connection_info": {"local": True}}

    return result


@router.get("/{solution_id}/{device_id}/config")
async def get_device_config(
    solution_id: str,
    device_id: str,
    lang: str = Query("en", pattern="^(en|zh)$"),
):
    """Get device configuration details"""
    solution = solution_manager.get_solution(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    # Find device ref from presets
    device_ref = solution_manager.find_device_in_solution(solution, device_id)

    if not device_ref:
        raise HTTPException(status_code=404, detail="Device not found")

    # Load device config
    config = await solution_manager.load_device_config(
        solution_id, device_ref.config_file
    )
    if not config:
        raise HTTPException(status_code=404, detail="Device config not found")

    # Build steps info
    steps = []
    for step in config.steps:
        steps.append(
            {
                "id": step.id,
                "name": step.name if lang == "en" else (step.name_zh or step.name),
                "description": (
                    step.description
                    if lang == "en"
                    else (step.description_zh or step.description)
                ),
                "optional": step.optional,
                "default": step.default,
            }
        )

    return {
        "id": config.id,
        "name": config.name if lang == "en" else (config.name_zh or config.name),
        "type": config.type,
        "steps": steps,
        "pre_checks": [check.model_dump() for check in config.pre_checks],
    }
