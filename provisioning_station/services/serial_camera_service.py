"""
Serial Camera Service - SSCMA JSON serial reader with WebSocket broadcast

Reads SSCMA face recognition data from serial port (Himax),
parses frames, and broadcasts to connected WebSocket clients.
"""

import json
import logging
import queue
import threading
import time
from typing import Callable, Dict, List, Optional
from uuid import uuid4

import serial

logger = logging.getLogger(__name__)


class SSCMAParser:
    """Parse SSCMA JSON messages from serial buffer.

    Protocol: messages framed as \\r{JSON}\\n (firmware sends \\r then JSON then \\n).
    JSON content is a single line with no embedded newlines.
    """

    def __init__(self):
        self._buffer = b""

    def feed(self, data: bytes) -> List[dict]:
        """Feed raw bytes and return parsed JSON messages."""
        self._buffer += data
        messages = []

        while True:
            # Find start marker: \r{
            start = self._buffer.find(b"\r{")
            if start == -1:
                # Keep last few bytes in case start marker is split
                if len(self._buffer) > 4:
                    self._buffer = self._buffer[-4:]
                break

            # Find end: first \n after start (JSON is single-line)
            end = self._buffer.find(b"\n", start + 2)
            if end == -1:
                # Incomplete message, keep from start
                self._buffer = self._buffer[start:]
                break

            # Extract JSON: skip leading \r, strip trailing \r if present
            json_bytes = self._buffer[start + 1 : end]
            if json_bytes.endswith(b"\r"):
                json_bytes = json_bytes[:-1]
            self._buffer = self._buffer[end + 1 :]

            try:
                msg = json.loads(json_bytes)
                messages.append(msg)
            except json.JSONDecodeError:
                logger.debug("Failed to parse SSCMA JSON: %s", json_bytes[:200])

        return messages

    def reset(self):
        self._buffer = b""


def parse_face_result(msg: dict) -> Optional[dict]:
    """Extract face data from SSCMA INVOKE message.

    Supports two formats:
    1. Custom face firmware: data.faces = [{box, score, landmarks, embedding}, ...]
    2. Standard SSCMA:       data.boxes = [[x,y,w,h,score], ...],
                             data.keypoints = [[x1,y1,s1,x2,y2,s2,...], ...]

    - score is integer 0-100 → normalized to 0-1
    """
    if msg.get("type") != 1:
        return None
    if msg.get("name") != "INVOKE":
        return None

    data = msg.get("data", {})
    image = data.get("image")
    resolution = data.get("resolution", [240, 240])

    faces = []

    # Format 1: Custom face firmware (data.faces is array of dicts)
    # SCRFD outputs top-left coords [x, y, w, h] — no conversion needed
    raw_faces = data.get("faces", [])
    if raw_faces:
        for f in raw_faces:
            # Support both field names: box/bbox, score/confidence
            raw_box = f.get("box") or f.get("bbox", [0, 0, 0, 0])
            score = f.get("score", f.get("confidence", 0))
            x, y, bw, bh = raw_box[:4] if len(raw_box) >= 4 else (0, 0, 0, 0)
            face = {
                "bbox": [x, y, bw, bh],
                "confidence": score / 100 if score > 1 else score,
                "quality": f.get("quality", 0),
                "landmarks": f.get("landmarks", []),
                "embedding": f.get("embedding", []),
            }
            if "recognized_name" in f:
                from .serial_crud_service import _decode_name

                face["recognized_name"] = _decode_name(f["recognized_name"])
            if "similarity" in f:
                face["similarity"] = f["similarity"]
            faces.append(face)
    else:
        # Format 2: Standard SSCMA (boxes + keypoints arrays)
        # SSCMA boxes = [[cx, cy, w, h, score, target], ...] — center-point coords
        boxes = data.get("boxes", [])
        keypoints = data.get("keypoints", [])
        for i, box in enumerate(boxes):
            if len(box) < 4:
                continue
            cx, cy, bw, bh = box[:4]
            score = box[4] if len(box) > 4 else 0
            face = {
                "bbox": [cx - bw / 2, cy - bh / 2, bw, bh],
                "confidence": score / 100 if score > 1 else score,
                "landmarks": [],
            }
            # Convert keypoints triplets [x1,y1,s1,x2,y2,s2,...] → pairs [[x1,y1],[x2,y2],...]
            if i < len(keypoints):
                kp = keypoints[i]
                face["landmarks"] = [
                    [kp[j], kp[j + 1]] for j in range(0, len(kp) - 2, 3)
                ]
            faces.append(face)

    return {
        "type": "frame",
        "image": image,
        "resolution": resolution,
        "faces": faces,
    }


class SerialCameraSession:
    """Manages a serial camera connection and broadcasts frames via WebSocket.

    Runs a background thread for serial I/O, bridges to async via
    asyncio.run_coroutine_threadsafe().
    """

    def __init__(
        self,
        session_id: str,
        port: str,
        baudrate: int = 921600,
        face_mode: bool = True,
    ):
        self.session_id = session_id
        self.port = port
        self.baudrate = baudrate
        self.face_mode = face_mode

        self._serial: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._parser = SSCMAParser()

        # WebSocket clients — use threading.Queue for cross-thread safety
        self._clients: List[queue.Queue] = []
        self._clients_lock = threading.Lock()

        # Frame callbacks (for enrollment logic)
        self._frame_callbacks: List[Callable] = []

        # Enrollment state (injected by FaceEnrollmentSession)
        self.enrollment_state: Optional[dict] = None

        # Stats
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._fps = 0.0

        # WS broadcast throttle (limit to ~10 FPS to reduce bandwidth)
        self._last_broadcast_time = 0.0
        self._broadcast_interval = 0.1  # 100ms = 10 FPS max

    def add_client(self) -> queue.Queue:
        """Add a WebSocket client queue (thread-safe)."""
        q: queue.Queue = queue.Queue(maxsize=5)
        with self._clients_lock:
            self._clients.append(q)
        logger.debug(
            "Session %s: client added (total=%d, running=%s)",
            self.session_id,
            len(self._clients),
            self._running,
        )
        return q

    def remove_client(self, q: queue.Queue):
        """Remove a WebSocket client queue."""
        with self._clients_lock:
            if q in self._clients:
                self._clients.remove(q)

    @property
    def client_count(self) -> int:
        """Number of connected WebSocket clients."""
        with self._clients_lock:
            return len(self._clients)

    def add_frame_callback(self, cb: Callable):
        self._frame_callbacks.append(cb)

    def remove_frame_callback(self, cb: Callable):
        if cb in self._frame_callbacks:
            self._frame_callbacks.remove(cb)

    def start(self):
        """Open serial port, send AT+INVOKE to start inference, and start reader."""
        if self._running:
            return

        self._serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=0.1,
        )
        self._serial.reset_input_buffer()
        self._running = True
        self._parser.reset()
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()
        logger.info(
            "Serial camera session %s started on %s", self.session_id, self.port
        )

    def stop(self):
        """Send AT+BREAK, stop reader thread, and close serial port."""
        self._running = False
        # Send break command to stop inference
        if self._serial and self._serial.is_open:
            try:
                self._serial.write(b"AT+BREAK\r")
                self._serial.flush()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None
        self._parser.reset()
        logger.info("Serial camera session %s stopped", self.session_id)

    def _wait_for_ready(self, timeout: float = 3.0) -> bool:
        """Wait for INIT@STAT? with is_ready=1 from device boot.

        Timeout reduced to 3s — if device is already running (no USB reset),
        it won't send INIT@STAT? and we shouldn't block the user.
        """
        start = time.time()
        buf = b""
        while time.time() - start < timeout and self._running:
            data = self._serial.read(4096)
            if not data:
                continue
            buf += data
            # Look for ready message in buffer
            while b"\r{" in buf:
                idx = buf.find(b"\r{")
                end = buf.find(b"\n", idx)
                if end == -1:
                    break
                msg_bytes = buf[idx + 1 : end]
                if msg_bytes.endswith(b"\r"):
                    msg_bytes = msg_bytes[:-1]
                buf = buf[end + 1 :]
                try:
                    msg = json.loads(msg_bytes)
                    if (
                        msg.get("name") == "INIT@STAT?"
                        and msg.get("data", {}).get("is_ready") == 1
                    ):
                        logger.info("Device ready on session %s", self.session_id)
                        return True
                except json.JSONDecodeError:
                    pass
        return False

    def _reader_loop(self):
        """Background thread: stop previous inference, wait for ready, then start."""
        self._broadcast_status("connecting", "Waiting for device...")

        # Stop any previously running inference first
        try:
            self._serial.write(b"AT+BREAK\r")
            self._serial.flush()
            time.sleep(0.5)
            self._serial.reset_input_buffer()
        except Exception:
            pass

        # Wait for device boot (USB port open may trigger reset)
        self._wait_for_ready()
        self._serial.reset_input_buffer()

        # Enable face mode (provides embeddings for enrollment) then start inference
        try:
            if self.face_mode:
                self._serial.write(b"AT+FACE=1\r")
                self._serial.flush()
                self._broadcast_status("connecting", "Loading face models...")
                time.sleep(2.0)
                self._serial.reset_input_buffer()
            self._serial.write(b"AT+INVOKE=-1,0,1\r")
            self._serial.flush()
        except Exception as e:
            logger.error("Failed to send AT commands: %s", e)
            self._broadcast_status("error", f"Failed to start inference: {e}")
            return

        self._broadcast_status("connected")

        while self._running:
            try:
                if not self._serial or not self._serial.is_open:
                    break

                # Read all available bytes to prevent OS buffer overflow
                waiting = self._serial.in_waiting
                data = self._serial.read(max(waiting, 1))
                if not data:
                    continue

                messages = self._parser.feed(data)
                for msg in messages:
                    frame = parse_face_result(msg)
                    if not frame:
                        continue

                    self._update_fps()
                    frame["fps"] = round(self._fps, 1)

                    # Attach enrollment state if active
                    if self.enrollment_state:
                        frame["enrollment"] = self.enrollment_state.copy()

                    # Call frame callbacks (for enrollment)
                    for cb in self._frame_callbacks:
                        try:
                            cb(frame)
                        except Exception as e:
                            logger.error("Frame callback error: %s", e)

                    # Broadcast to WebSocket clients (throttled, strip embeddings)
                    now = time.time()
                    if now - self._last_broadcast_time >= self._broadcast_interval:
                        self._last_broadcast_time = now
                        ws_frame = self._strip_embeddings(frame)
                        self._broadcast(ws_frame)

            except serial.SerialException as e:
                logger.error("Serial error in session %s: %s", self.session_id, e)
                self._broadcast_status("error", str(e))
                break
            except Exception as e:
                logger.error("Reader loop error: %s", e)
                continue

        self._running = False

    @staticmethod
    def _strip_embeddings(frame: dict) -> dict:
        """Remove embedding data from frame before sending to WebSocket clients."""
        stripped = dict(frame)
        if "faces" in stripped:
            stripped["faces"] = [
                {k: v for k, v in f.items() if k != "embedding"}
                for f in stripped["faces"]
            ]
        return stripped

    def _update_fps(self):
        self._frame_count += 1
        now = time.time()
        elapsed = now - self._last_fps_time
        if elapsed >= 1.0:
            self._fps = self._frame_count / elapsed
            self._frame_count = 0
            self._last_fps_time = now

    def _broadcast(self, data: dict):
        """Send frame data to all connected clients via thread-safe queues."""
        json_str = json.dumps(data)
        with self._clients_lock:
            n_clients = len(self._clients)
            for q in list(self._clients):
                try:
                    q.put_nowait(json_str)
                except queue.Full:
                    # Drop oldest frame if client is too slow
                    try:
                        q.get_nowait()
                        q.put_nowait(json_str)
                    except (queue.Empty, queue.Full):
                        pass

    def _broadcast_status(self, status: str, message: str = ""):
        """Broadcast a status message."""
        self._broadcast({"type": "status", "status": status, "message": message})


class SerialCameraManager:
    """Global manager for serial camera sessions.

    Ensures port exclusivity: one port can only be used by one session.
    """

    def __init__(self):
        self._sessions: Dict[str, SerialCameraSession] = {}
        self._port_map: Dict[str, str] = {}  # port -> session_id

    def create_session(
        self,
        port: str,
        baudrate: int = 921600,
        face_mode: bool = True,
    ) -> SerialCameraSession:
        """Create a new camera session."""
        # Check port exclusivity
        if port in self._port_map:
            existing_id = self._port_map[port]
            raise ValueError(f"Port {port} is already in use by session {existing_id}")

        session_id = str(uuid4())[:8]
        session = SerialCameraSession(session_id, port, baudrate, face_mode=face_mode)
        self._sessions[session_id] = session
        self._port_map[port] = session_id
        return session

    def get_session(self, session_id: str) -> Optional[SerialCameraSession]:
        return self._sessions.get(session_id)

    def close_session(self, session_id: str):
        """Stop and remove a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            session.stop()
            self._port_map.pop(session.port, None)

    def close_all(self):
        """Close all sessions."""
        for sid in list(self._sessions.keys()):
            self.close_session(sid)

    @property
    def active_sessions(self) -> Dict[str, SerialCameraSession]:
        return dict(self._sessions)


# Global singleton
_manager: Optional[SerialCameraManager] = None


def get_serial_camera_manager() -> SerialCameraManager:
    global _manager
    if _manager is None:
        _manager = SerialCameraManager()
    return _manager
