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
import uuid
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
    camera_port: Optional[str] = None
    camera_baudrate: int = 921600
    crud_port: Optional[str] = None
    crud_baudrate: int = 115200


class CreateSessionResponse(BaseModel):
    session_id: str
    camera_port: Optional[str] = None


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

# CRUD-only sessions (no camera) - session_id -> True
_crud_only_sessions: dict = {}


def _get_crud_client(session_id: str) -> Optional[SerialCrudClient]:
    return _crud_clients.get(session_id)


# ============================================
# Session Management
# ============================================


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest):
    """Create a new serial camera session.

    At least one of camera_port or crud_port must be provided.
    - camera_port only: camera preview, no face DB
    - crud_port only: face DB CRUD, no camera preview
    - both: full functionality
    """
    if not req.camera_port and not req.crud_port:
        raise HTTPException(
            status_code=400,
            detail="At least one of camera_port or crud_port must be provided",
        )

    # Reject if both ports point to the same device
    if req.camera_port and req.crud_port and req.camera_port == req.crud_port:
        raise HTTPException(
            status_code=400,
            detail=f"camera_port and crud_port must be different (both are {req.camera_port})",
        )

    logger.info(
        "create_session: camera_port=%s, crud_port=%s",
        req.camera_port,
        req.crud_port,
    )

    session_id = None

    # Open CRUD client
    crud_client = None
    if req.crud_port:
        try:
            crud_client = SerialCrudClient(req.crud_port, req.crud_baudrate)
            crud_client.open()
            logger.info("CRUD client opened: port=%s", req.crud_port)
        except Exception as e:
            logger.warning("Failed to open CRUD port %s: %s", req.crud_port, e)

    if req.camera_port:
        # Pause ESP32 SPI inference so UART's AT+FACE=1 takes effect on Himax.
        # Without pause, SPI commands override face mode back to standard detection
        # (boxes, no image). With pause, Himax enters face mode which includes
        # JPEG image in UART responses (see face_invoke.hpp include_image logic).
        if crud_client:
            pause_ok = False
            for attempt in range(1, 4):
                try:
                    result = await crud_client.pause_inference()
                    logger.info("Inference paused (attempt %d): %s", attempt, result)
                    if result.get("ok"):
                        pause_ok = True
                        break
                except Exception as e:
                    logger.warning(
                        "Failed to pause inference (attempt %d): %s", attempt, e
                    )
                if attempt < 3:
                    await asyncio.sleep(0.5)
            if not pause_ok:
                logger.warning("Could not pause inference after 3 attempts")

        # Create camera session (generates session_id internally)
        manager = get_serial_camera_manager()
        try:
            session = manager.create_session(req.camera_port, req.camera_baudrate)
            session.start()
            session_id = session.session_id
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to open camera port: {e}"
            )
    else:
        # CRUD-only session — generate ID directly
        session_id = uuid.uuid4().hex[:8]
        _crud_only_sessions[session_id] = True

    # Register CRUD client for this session
    if crud_client:
        _crud_clients[session_id] = crud_client

    return CreateSessionResponse(
        session_id=session_id,
        camera_port=req.camera_port,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Close a serial camera session."""
    # Cancel any active enrollment
    enrollment = _enrollments.pop(session_id, None)
    if enrollment and enrollment.active:
        enrollment.cancel()

    # Resume inference if it was paused (e.g. during enrollment)
    client = _crud_clients.get(session_id)
    if client:
        try:
            result = await client.resume_inference()
            logger.info("Inference resumed after session close: %s", result)
        except Exception:
            pass  # Best-effort; ESP32 has 5min auto-resume timeout

    # Close camera session (stops UART AT commands to Himax)
    if session_id not in _crud_only_sessions:
        manager = get_serial_camera_manager()
        manager.close_session(session_id)
    else:
        _crud_only_sessions.pop(session_id, None)

    # Close CRUD client
    client = _crud_clients.pop(session_id, None)
    if client:
        client.close()

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
            # Resume inference if CRUD client exists (browser may have closed without calling delete_session)
            # Use fire-and-forget to release the serial port immediately — avoids blocking
            # new sessions that need to open the same port.
            client = _crud_clients.pop(session_id, None)
            if client:
                client.resume_inference_nowait()
                client.close()
                logger.info(
                    "Inference resume sent (nowait) on WS disconnect for session %s",
                    session_id,
                )


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
        logger.exception("list_faces failed session=%s", session_id)
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
        logger.exception("add_face failed session=%s", session_id)
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
        logger.exception("delete_face failed for name=%r session=%s", name, session_id)
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
        logger.exception("rename_face failed session=%s", session_id)
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
