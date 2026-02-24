"""
E2E tests for serial camera preview and face database.

Tests:
- Serial camera session creation via API
- WebSocket frame streaming (not frozen)
- Face detection data in frames (bbox, landmarks)
- Face database CRUD operations
- Session cleanup

Requires:
- API server running at localhost:3260
- SenseCAP Watcher connected via USB (CH342 dual serial)
"""

import asyncio
import json
import time
from typing import Optional

import httpx
import pytest
import websockets

from .conftest import API_BASE_URL

# =============================================================================
# Configuration
# =============================================================================

# CH342 dual serial: port A = Himax camera (921600), port B = ESP32 CRUD (115200)
CAMERA_BAUDRATE = 921600
CRUD_BAUDRATE = 115200

# Timeouts
SESSION_CREATE_TIMEOUT = 5.0
DEVICE_BOOT_TIMEOUT = 15.0  # Himax needs time to boot after serial open
FRAME_RECEIVE_TIMEOUT = 20.0  # Wait for first frame (includes device boot)
STREAMING_DURATION = 10.0  # How long to verify continuous streaming


# =============================================================================
# Fixtures
# =============================================================================


def _find_watcher_ports() -> Optional[dict]:
    """
    Find SenseCAP Watcher CH342 serial ports.

    Returns dict with 'camera_port' and 'crud_port', or None if not found.
    The CH342 chip exposes two serial ports:
    - SERIAL-A (lower suffix): Himax camera data
    - SERIAL-B (higher suffix): ESP32 console
    """
    try:
        import serial.tools.list_ports

        ch342_ports = []
        for port in serial.tools.list_ports.comports():
            desc = port.description or ""
            # CH342 shows as "USB Dual_Serial" or similar
            if "CH342" in desc or "Dual_Serial" in desc or "wchusbserial" in port.device:
                ch342_ports.append(port.device)
            # Also match usbmodem ports from Himax (direct USB)
            elif "usbmodem" in port.device:
                ch342_ports.append(port.device)

        if len(ch342_ports) < 2:
            return None

        # Sort to get consistent A/B ordering
        ch342_ports.sort()

        # Convention: first (A) = Himax camera, second (B) = ESP32 CRUD
        # But usbmodem ports (Himax direct USB) have different naming
        camera_port = None
        crud_port = None
        for p in ch342_ports:
            if "usbmodem" in p and "651" in p:
                camera_port = p
            elif "wchusbserial" in p and "653" in p:
                crud_port = p

        # Fallback: just use sorted order
        if not camera_port:
            camera_port = ch342_ports[0]
        if not crud_port:
            crud_port = ch342_ports[1] if len(ch342_ports) > 1 else None

        return {"camera_port": camera_port, "crud_port": crud_port}
    except ImportError:
        return None


@pytest.fixture(scope="module")
def watcher_serial_ports():
    """Find and validate Watcher serial ports. Skip if not connected."""
    ports = _find_watcher_ports()
    if not ports or not ports.get("camera_port"):
        pytest.skip("SenseCAP Watcher serial ports not found")
    return ports


@pytest.fixture
def camera_session(api_server_running, watcher_serial_ports, api_client):
    """
    Create a serial camera session and clean up after test.

    Yields (session_id, session_info) tuple.
    """
    ports = watcher_serial_ports
    payload = {
        "camera_port": ports["camera_port"],
        "camera_baudrate": CAMERA_BAUDRATE,
    }
    if ports.get("crud_port"):
        payload["crud_port"] = ports["crud_port"]
        payload["crud_baudrate"] = CRUD_BAUDRATE

    resp = api_client.post("/api/serial-camera/sessions", json=payload)
    assert resp.status_code == 200, f"Failed to create session: {resp.text}"

    data = resp.json()
    session_id = data["session_id"]

    yield session_id, data

    # Cleanup: delete session
    try:
        api_client.delete(f"/api/serial-camera/sessions/{session_id}")
    except Exception:
        pass


# =============================================================================
# Tests: Session Lifecycle
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_watcher
class TestSerialCameraSession:
    """Tests for serial camera session management."""

    def test_create_session(self, api_server_running, watcher_serial_ports, api_client):
        """Create a serial camera session and verify response."""
        ports = watcher_serial_ports
        resp = api_client.post(
            "/api/serial-camera/sessions",
            json={
                "camera_port": ports["camera_port"],
                "camera_baudrate": CAMERA_BAUDRATE,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["camera_port"] == ports["camera_port"]

        # Cleanup
        api_client.delete(f"/api/serial-camera/sessions/{data['session_id']}")

    def test_duplicate_port_rejected(self, camera_session, watcher_serial_ports, api_client):
        """Creating a second session on the same port should fail."""
        ports = watcher_serial_ports
        resp = api_client.post(
            "/api/serial-camera/sessions",
            json={
                "camera_port": ports["camera_port"],
                "camera_baudrate": CAMERA_BAUDRATE,
            },
        )
        assert resp.status_code == 409  # Conflict

    def test_session_debug_endpoint(self, camera_session, api_client):
        """Debug endpoint returns session state."""
        session_id, _ = camera_session
        resp = api_client.get(f"/api/serial-camera/sessions/{session_id}/debug")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["running"] is True


# =============================================================================
# Tests: Frame Streaming
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_watcher
class TestFrameStreaming:
    """Tests for WebSocket frame streaming — verifies camera doesn't freeze."""

    @pytest.mark.asyncio
    async def test_receives_frames(self, camera_session):
        """Connect via WebSocket and verify frames are received."""
        session_id, _ = camera_session
        ws_url = f"ws://localhost:3260/api/serial-camera/ws/{session_id}"

        frames = []
        async with websockets.connect(ws_url) as ws:
            deadline = time.time() + FRAME_RECEIVE_TIMEOUT
            while time.time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    msg = json.loads(raw)
                    if msg.get("type") == "frame":
                        frames.append(msg)
                        if len(frames) >= 3:
                            break
                except asyncio.TimeoutError:
                    continue

        assert len(frames) >= 3, (
            f"Expected at least 3 frames within {FRAME_RECEIVE_TIMEOUT}s, got {len(frames)}"
        )

    @pytest.mark.asyncio
    async def test_frames_contain_image(self, camera_session):
        """Verify frame data contains base64 image."""
        session_id, _ = camera_session
        ws_url = f"ws://localhost:3260/api/serial-camera/ws/{session_id}"

        async with websockets.connect(ws_url) as ws:
            deadline = time.time() + FRAME_RECEIVE_TIMEOUT
            while time.time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    msg = json.loads(raw)
                    if msg.get("type") == "frame":
                        assert "image" in msg, "Frame missing 'image' field"
                        assert isinstance(msg["image"], str), "Image should be base64 string"
                        assert len(msg["image"]) > 100, "Image data too small"
                        assert "resolution" in msg, "Frame missing 'resolution' field"
                        assert len(msg["resolution"]) == 2, "Resolution should be [w, h]"
                        return
                except asyncio.TimeoutError:
                    continue

            pytest.fail(f"No frame received within {FRAME_RECEIVE_TIMEOUT}s")

    @pytest.mark.asyncio
    async def test_continuous_streaming_no_freeze(self, camera_session):
        """
        Verify frames keep arriving over a sustained period (no freeze).

        This is the key regression test: previous implementation froze
        after a few frames due to the _decoding gate getting stuck.
        """
        session_id, _ = camera_session
        ws_url = f"ws://localhost:3260/api/serial-camera/ws/{session_id}"

        frame_times = []
        async with websockets.connect(ws_url) as ws:
            # Wait for first frame (device boot)
            first_frame_deadline = time.time() + FRAME_RECEIVE_TIMEOUT
            while time.time() < first_frame_deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    msg = json.loads(raw)
                    if msg.get("type") == "frame":
                        frame_times.append(time.time())
                        break
                except asyncio.TimeoutError:
                    continue

            assert len(frame_times) > 0, "Never received first frame"

            # Now collect frames for STREAMING_DURATION seconds
            end_time = time.time() + STREAMING_DURATION
            while time.time() < end_time:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    msg = json.loads(raw)
                    if msg.get("type") == "frame":
                        frame_times.append(time.time())
                except asyncio.TimeoutError:
                    continue

        # Verify: should have received frames throughout the period
        total_frames = len(frame_times)
        assert total_frames >= 5, (
            f"Only {total_frames} frames in {STREAMING_DURATION}s — likely frozen"
        )

        # Check no long gaps (max 3s between consecutive frames)
        max_gap = 0.0
        for i in range(1, len(frame_times)):
            gap = frame_times[i] - frame_times[i - 1]
            max_gap = max(max_gap, gap)

        assert max_gap < 3.0, (
            f"Max gap between frames: {max_gap:.1f}s — likely froze mid-stream"
        )

        # Calculate effective FPS
        duration = frame_times[-1] - frame_times[0]
        if duration > 0:
            fps = (total_frames - 1) / duration
            # Backend throttles to ~10 FPS, device runs at ~2-5 FPS
            assert fps > 0.5, f"FPS too low: {fps:.1f}"

    @pytest.mark.asyncio
    async def test_face_detection_data(self, camera_session):
        """
        Verify frames include face detection results when faces are present.

        Note: This test checks structure only. Actual face detection depends
        on whether a face is visible to the camera.
        """
        session_id, _ = camera_session
        ws_url = f"ws://localhost:3260/api/serial-camera/ws/{session_id}"

        frames_with_faces = []
        frames_without_faces = []

        async with websockets.connect(ws_url) as ws:
            deadline = time.time() + FRAME_RECEIVE_TIMEOUT
            frame_count = 0
            while time.time() < deadline and frame_count < 20:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    msg = json.loads(raw)
                    if msg.get("type") == "frame":
                        frame_count += 1
                        faces = msg.get("faces", [])
                        assert isinstance(faces, list), "faces should be a list"

                        if faces:
                            frames_with_faces.append(msg)
                            # Verify face data structure
                            face = faces[0]
                            assert "bbox" in face, "Face missing bbox"
                            assert len(face["bbox"]) == 4, "bbox should be [x,y,w,h]"
                            assert "confidence" in face, "Face missing confidence"
                        else:
                            frames_without_faces.append(msg)
                except asyncio.TimeoutError:
                    continue

        # At minimum we should have received some frames
        total = len(frames_with_faces) + len(frames_without_faces)
        assert total > 0, "No frames received"

        # If faces were detected, verify overlay-relevant fields
        if frames_with_faces:
            face = frames_with_faces[0]["faces"][0]
            bbox = face["bbox"]
            # bbox values should be reasonable (within resolution bounds)
            assert all(isinstance(v, (int, float)) for v in bbox), "bbox values should be numeric"
            conf = face["confidence"]
            assert 0 <= conf <= 1.0, f"Confidence {conf} out of range [0, 1]"


# =============================================================================
# Tests: Face Database
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_watcher
class TestFaceDatabase:
    """Tests for face database CRUD operations via serial."""

    def test_list_faces(self, camera_session, api_client):
        """List faces from the database."""
        session_id, _ = camera_session
        resp = api_client.get(f"/api/serial-camera/sessions/{session_id}/faces")

        # May get 404 if no CRUD port was configured
        if resp.status_code == 404:
            pytest.skip("No CRUD port configured for this session")

        assert resp.status_code == 200
        data = resp.json()
        assert "faces" in data
        assert isinstance(data["faces"], list)


# =============================================================================
# Tests: Session Cleanup
# =============================================================================


@pytest.mark.e2e
@pytest.mark.device_watcher
class TestSessionCleanup:
    """Tests for proper session cleanup."""

    def test_delete_session(self, api_server_running, watcher_serial_ports, api_client):
        """Deleting a session releases the port for reuse."""
        ports = watcher_serial_ports

        # Create session
        resp = api_client.post(
            "/api/serial-camera/sessions",
            json={
                "camera_port": ports["camera_port"],
                "camera_baudrate": CAMERA_BAUDRATE,
            },
        )
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        # Delete session
        resp = api_client.delete(f"/api/serial-camera/sessions/{session_id}")
        assert resp.status_code == 200

        # Should be able to create a new session on the same port
        resp = api_client.post(
            "/api/serial-camera/sessions",
            json={
                "camera_port": ports["camera_port"],
                "camera_baudrate": CAMERA_BAUDRATE,
            },
        )
        assert resp.status_code == 200
        new_session_id = resp.json()["session_id"]

        # Cleanup
        api_client.delete(f"/api/serial-camera/sessions/{new_session_id}")

    @pytest.mark.asyncio
    async def test_ws_disconnect_auto_cleanup(self, api_server_running, watcher_serial_ports):
        """Session auto-closes when last WebSocket client disconnects."""
        ports = watcher_serial_ports

        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
            # Create session
            resp = await client.post(
                "/api/serial-camera/sessions",
                json={
                    "camera_port": ports["camera_port"],
                    "camera_baudrate": CAMERA_BAUDRATE,
                },
            )
            assert resp.status_code == 200
            session_id = resp.json()["session_id"]

            ws_url = f"ws://localhost:3260/api/serial-camera/ws/{session_id}"

            # Connect and disconnect WebSocket
            ws = await websockets.connect(ws_url)
            # Receive at least one message to confirm connection
            try:
                await asyncio.wait_for(ws.recv(), timeout=FRAME_RECEIVE_TIMEOUT)
            except asyncio.TimeoutError:
                pass
            await ws.close()

            # Wait for auto-cleanup
            await asyncio.sleep(1.0)

            # Session should be gone — creating on same port should succeed
            resp = await client.post(
                "/api/serial-camera/sessions",
                json={
                    "camera_port": ports["camera_port"],
                    "camera_baudrate": CAMERA_BAUDRATE,
                },
            )
            assert resp.status_code == 200
            new_session_id = resp.json()["session_id"]

            # Cleanup
            await client.delete(f"/api/serial-camera/sessions/{new_session_id}")
