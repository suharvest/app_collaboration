"""
Serial Camera Router - API endpoints for serial camera preview and face management

Handles:
- Session lifecycle (create/delete)
- WebSocket frame streaming
- Face CRUD via serial device
- Face enrollment workflow
"""

import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..services.face_enroll_logic import FaceEnrollmentSession
from ..services.serial_camera_service import get_serial_camera_manager
from ..services.serial_crud_service import SerialCrudClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/serial-camera", tags=["serial-camera"])


# ============================================
# Request/Response Models
# ============================================


class CreateSessionRequest(BaseModel):
    camera_port: str
    camera_baudrate: int = 921600
    crud_port: Optional[str] = None
    crud_baudrate: int = 115200


class CreateSessionResponse(BaseModel):
    session_id: str
    camera_port: str


class FaceEntry(BaseModel):
    name: str
    index: int


class FaceListResponse(BaseModel):
    ok: bool
    faces: List[FaceEntry] = []
    count: int = 0
    max: int = 0


class AddFaceRequest(BaseModel):
    name: str
    embedding: List[float] = []


class RenameFaceRequest(BaseModel):
    new_name: str


class StartEnrollmentRequest(BaseModel):
    name: str
    duration: float = 5.0
    min_samples: int = 3
    min_confidence: float = 0.5


# ============================================
# Session state (CRUD clients + enrollments)
# ============================================

# Maps session_id -> SerialCrudClient
_crud_clients: dict = {}

# Maps session_id -> FaceEnrollmentSession
_enrollments: dict = {}


def _get_crud_client(session_id: str) -> Optional[SerialCrudClient]:
    return _crud_clients.get(session_id)


# ============================================
# Session Management
# ============================================


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest):
    """Create a new serial camera session."""
    manager = get_serial_camera_manager()

    try:
        session = manager.create_session(req.camera_port, req.camera_baudrate)
        session.start()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open camera port: {e}")

    # Open CRUD client if specified
    if req.crud_port:
        try:
            client = SerialCrudClient(req.crud_port, req.crud_baudrate)
            client.open()
            _crud_clients[session.session_id] = client
        except Exception as e:
            # Don't fail session creation if CRUD port fails
            logger.warning("Failed to open CRUD port %s: %s", req.crud_port, e)

    return CreateSessionResponse(
        session_id=session.session_id,
        camera_port=req.camera_port,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Close a serial camera session."""
    manager = get_serial_camera_manager()

    # Cancel any active enrollment
    enrollment = _enrollments.pop(session_id, None)
    if enrollment and enrollment.active:
        enrollment.cancel()

    # Close CRUD client
    client = _crud_clients.pop(session_id, None)
    if client:
        client.close()

    manager.close_session(session_id)
    return {"ok": True}


# ============================================
# WebSocket Frame Stream
# ============================================


@router.websocket("/ws/{session_id}")
async def websocket_frames(ws: WebSocket, session_id: str):
    """Stream camera frames via WebSocket.

    Uses threading.Queue from serial reader thread, polled with asyncio.sleep.
    """
    import queue as queue_mod

    manager = get_serial_camera_manager()
    session = manager.get_session(session_id)

    if not session:
        await ws.close(code=4004, reason="Session not found")
        return

    await ws.accept()
    q = session.add_client()
    logger.info("WS connected: session=%s, running=%s", session_id, session._running)

    # Send immediate status so client knows if reader is active
    if not session._running:
        await ws.send_json(
            {
                "type": "status",
                "status": "disconnected",
                "message": "Serial reader is not running",
            }
        )

    try:
        idle_count = 0
        while True:
            try:
                msg = q.get_nowait()
                await ws.send_text(msg)
                idle_count = 0
            except queue_mod.Empty:
                idle_count += 1
                if idle_count > 200:  # ~10s at 50ms poll → send ping
                    await ws.send_json({"type": "ping"})
                    idle_count = 0
                await asyncio.sleep(0.05)  # 50ms poll interval
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket error for session %s: %s", session_id, e)
    finally:
        session.remove_client(q)
        # Auto-close session when last client disconnects
        if session.client_count == 0:
            logger.info("Last WS client left session %s, auto-closing", session_id)
            manager.close_session(session_id)


# ============================================
# Debug
# ============================================


@router.get("/sessions/{session_id}/debug")
async def debug_session(session_id: str):
    """Debug endpoint to inspect session state."""
    manager = get_serial_camera_manager()
    session = manager.get_session(session_id)
    if not session:
        return {
            "error": "Session not found",
            "all_sessions": list(manager.active_sessions.keys()),
        }

    with session._clients_lock:
        client_info = [{"id": id(q), "qsize": q.qsize()} for q in session._clients]

    return {
        "session_id": session_id,
        "port": session.port,
        "running": session._running,
        "fps": session._fps,
        "frame_count": session._frame_count,
        "clients": client_info,
        "enrollment_active": session.enrollment_state is not None,
        "callbacks": len(session._frame_callbacks),
    }


# ============================================
# Face CRUD
# ============================================


@router.post("/sessions/{session_id}/faces/test-add")
async def test_add_face(session_id: str, name: str = "test"):
    """Debug: test face_add with given name and dummy 128D embedding."""
    client = _get_crud_client(session_id)
    if not client:
        raise HTTPException(
            status_code=404, detail="No database connection for this session"
        )

    dummy_embedding = [0.1] * 128
    try:
        result = await client.add_face(name, dummy_embedding)
        # Clean up if successful
        if result.get("ok"):
            await client.delete_face(name)
        return {"test_result": result, "name": name}
    except Exception as e:
        return {"test_result": {"ok": False, "error": str(e)}}


@router.get("/sessions/{session_id}/faces")
async def list_faces(session_id: str):
    """List all enrolled faces."""
    client = _get_crud_client(session_id)
    if not client:
        raise HTTPException(
            status_code=404, detail="No database connection for this session"
        )

    try:
        result = await client.list_faces()
        return result
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Device did not respond")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/faces")
async def add_face(session_id: str, req: AddFaceRequest):
    """Add a face directly (with embedding)."""
    client = _get_crud_client(session_id)
    if not client:
        raise HTTPException(
            status_code=404, detail="No database connection for this session"
        )

    try:
        result = await client.add_face(req.name, req.embedding)
        return result
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Device did not respond")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}/faces/{name}")
async def delete_face(session_id: str, name: str):
    """Delete a face from the database."""
    client = _get_crud_client(session_id)
    if not client:
        raise HTTPException(
            status_code=404, detail="No database connection for this session"
        )

    try:
        result = await client.delete_face(name)
        return result
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Device did not respond")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sessions/{session_id}/faces/{name}")
async def rename_face(session_id: str, name: str, req: RenameFaceRequest):
    """Rename a face in the database."""
    client = _get_crud_client(session_id)
    if not client:
        raise HTTPException(
            status_code=404, detail="No database connection for this session"
        )

    try:
        result = await client.rename_face(name, req.new_name)
        return result
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Device did not respond")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Enrollment
# ============================================


@router.post("/sessions/{session_id}/enroll/start")
async def start_enrollment(session_id: str, req: StartEnrollmentRequest):
    """Start face enrollment (collect embeddings from camera)."""
    manager = get_serial_camera_manager()
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Camera session not found")

    client = _get_crud_client(session_id)
    if not client:
        raise HTTPException(
            status_code=404, detail="No database connection for this session"
        )

    # Cancel existing enrollment
    existing = _enrollments.get(session_id)
    if existing and existing.active:
        existing.cancel()

    enrollment = FaceEnrollmentSession(
        camera_session=session,
        crud_client=client,
        name=req.name,
        duration=req.duration,
        min_samples=req.min_samples,
        min_confidence=req.min_confidence,
    )
    enrollment.start()
    _enrollments[session_id] = enrollment

    return {"ok": True, "name": req.name, "duration": req.duration}


@router.post("/sessions/{session_id}/enroll/cancel")
async def cancel_enrollment(session_id: str):
    """Cancel active enrollment."""
    enrollment = _enrollments.get(session_id)
    if enrollment and enrollment.active:
        enrollment.cancel()
        return {"ok": True}
    return {"ok": False, "error": "No active enrollment"}


@router.get("/sessions/{session_id}/enroll/status")
async def enrollment_status(session_id: str):
    """Get enrollment status and store result if complete."""
    enrollment = _enrollments.get(session_id)
    if not enrollment:
        return {"active": False}

    if enrollment.active:
        return {
            "active": True,
            "name": enrollment.name,
            "samples": len(enrollment._samples),
            "min_samples": enrollment.min_samples,
        }

    # Enrollment finished - check result
    result = enrollment.result
    # Clear enrollment_state on camera session to stop broadcasting
    enrollment.camera_session.enrollment_state = None

    if result and result.get("ok"):
        # Auto-store the result
        try:
            store_result = await enrollment.store()
            logger.info(
                "Enrollment store result for '%s': %s",
                enrollment.name,
                store_result,
            )
            _enrollments.pop(session_id, None)
            return {
                "active": False,
                "completed": True,
                "name": enrollment.name,
                "samples_collected": result.get("samples_collected", 0),
                "stored": store_result.get("ok", False),
            }
        except Exception as e:
            _enrollments.pop(session_id, None)
            return {
                "active": False,
                "completed": True,
                "error": f"Failed to store: {e}",
            }
    else:
        _enrollments.pop(session_id, None)
        return {
            "active": False,
            "completed": True,
            "error": result.get("error", "Unknown error") if result else "No result",
        }
