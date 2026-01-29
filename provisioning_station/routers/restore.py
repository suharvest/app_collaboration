"""
Device Restore API Routes

Endpoints for restoring devices to factory state:
- SenseCAP Watcher: USB firmware flashing
- reCamera: SSH-based uninstall and service restoration
"""

from typing import List, Optional

import serial.tools.list_ports
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services.restore_manager import get_restore_manager

router = APIRouter(prefix="/api/restore", tags=["restore"])


# ============================================
# Request/Response Models
# ============================================

class RestoreStartRequest(BaseModel):
    """Request to start a restore operation"""
    device_type: str
    connection: dict  # port for USB, host/username/password for SSH


class RestoreDeviceResponse(BaseModel):
    """Supported device information"""
    id: str
    name: str
    description: str
    type: str


class RestoreStatusResponse(BaseModel):
    """Restore operation status"""
    id: str
    device_type: str
    device_name: str
    status: str
    progress: int
    message: str
    current_step: str
    completed_steps: int
    total_steps: int
    error: Optional[str] = None
    logs: List[dict] = []


class PortInfo(BaseModel):
    """Serial port information"""
    device: str
    description: str
    hwid: str
    is_himax: bool


# ============================================
# Endpoints
# ============================================

@router.get("/devices", response_model=List[RestoreDeviceResponse])
async def get_supported_devices(
    lang: str = Query("en", pattern="^(en|zh)$"),
):
    """Get list of devices that support factory restore"""
    manager = get_restore_manager()
    devices = manager.get_supported_devices(lang)
    return devices


@router.get("/ports", response_model=List[PortInfo])
async def list_serial_ports():
    """List available serial ports for USB restore"""
    # Device USB identifiers
    # Watcher uses WCH chip: VID=0x1a86, PID=0x55d2
    WATCHER_VID = 0x1a86
    WATCHER_PID = 0x55d2
    # reCamera uses Cvitek chip: VID=0x3346, PID=0x1003
    RECAMERA_VID = 0x3346
    RECAMERA_PID = 0x1003

    ports = []
    for port in serial.tools.list_ports.comports():
        is_himax = False
        # Only mark as Himax if it's a Watcher's usbmodem port (WCH chip)
        if port.vid == WATCHER_VID and port.pid == WATCHER_PID:
            # Watcher has both wchusbserial (ESP32) and usbmodem (Himax) ports
            if 'usbmodem' in port.device.lower():
                is_himax = True

        ports.append(PortInfo(
            device=port.device,
            description=port.description or "Serial Port",
            hwid=port.hwid or "",
            is_himax=is_himax,
        ))

    return ports


@router.post("/start")
async def start_restore(request: RestoreStartRequest):
    """Start a device restore operation"""
    manager = get_restore_manager()

    # Validate device type
    device_config = manager.get_device_config(request.device_type)
    if not device_config:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported device type: {request.device_type}"
        )

    # Validate connection parameters
    device_type = device_config.get("type", "")

    if device_type == "himax_usb":
        if not request.connection.get("port"):
            raise HTTPException(status_code=400, detail="Serial port is required")
    elif device_type == "ssh_restore":
        if not request.connection.get("host"):
            raise HTTPException(status_code=400, detail="SSH host is required")
        if not request.connection.get("password"):
            raise HTTPException(status_code=400, detail="SSH password is required")

    try:
        operation = await manager.start_restore(
            device_type=request.device_type,
            connection=request.connection,
        )

        return {
            "success": True,
            "operation_id": operation.id,
            "message": "Restore operation started",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start restore: {str(e)}")


@router.get("/{operation_id}/status", response_model=RestoreStatusResponse)
async def get_restore_status(operation_id: str):
    """Get the status of a restore operation"""
    manager = get_restore_manager()
    operation = manager.get_operation(operation_id)

    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    return RestoreStatusResponse(
        id=operation.id,
        device_type=operation.device_type,
        device_name=operation.device_name,
        status=operation.status.value,
        progress=operation.progress,
        message=operation.message,
        current_step=operation.current_step,
        completed_steps=operation.completed_steps,
        total_steps=operation.total_steps,
        error=operation.error,
        logs=operation.logs,
    )
