"""
Serial CRUD Service - ESP Console command protocol for face database operations

Communicates with ESP32 via USB Serial JTAG using plain-text console commands.
Responses are JSON lines mixed with ESP logs; we filter for lines starting with '{'.

Protocol:
  face_list\n           -> {"ok":true,"faces":[...],"count":N,"max":M}
  face_add <name> <csv_embedding>\n  -> {"ok":true}
  face_delete <name>\n  -> {"ok":true}
  face_rename <old> <new>\n -> {"ok":true}

Important:
  - Must send in 32-byte chunks with 10ms inter-chunk delay (USB FIFO limit)
  - Commands are echoed back; skip lines not starting with '{'
  - ESP REPL prompt 'SenseCAP>' may appear; skip it too
"""

import asyncio
import base64
import json
import logging
import re
import struct
import threading
import time
from typing import List, Optional

import serial

logger = logging.getLogger(__name__)

# Default timeout for serial command responses
DEFAULT_TIMEOUT = 5.0

# USB FIFO chunk size and inter-chunk delay
CHUNK_SIZE = 32
CHUNK_DELAY = 0.03  # 30ms - increased for UART safety under load

# Regex to strip ANSI escape codes (cursor movement, colors, clear line, etc.)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\[\?[0-9;]*[A-Za-z]|\x00")

# Name encoding prefix for non-ASCII names
_NAME_PREFIX = "u_"


def _encode_name(name: str) -> str:
    """Encode non-ASCII name to hex for ESP32 console compatibility.

    "苏禾" → "u_e88b8fe7a6be"
    "Alice" → "Alice" (unchanged)
    """
    if name.isascii():
        return name
    return _NAME_PREFIX + name.encode("utf-8").hex()


def _decode_name(raw: str) -> str:
    """Decode hex-encoded name back to Unicode.

    "u_e88b8fe7a6be" → "苏禾"
    "Alice" → "Alice" (unchanged)
    """
    if raw.startswith(_NAME_PREFIX):
        try:
            return bytes.fromhex(raw[len(_NAME_PREFIX) :]).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            pass
    return raw


class SerialCrudClient:
    """ESP Console command client for face database CRUD.

    Sends plain-text commands over serial, reads JSON responses
    while filtering out echo, logs, and REPL prompts.
    """

    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._inference_paused = False

    def open(self):
        """Open serial connection."""
        if self._serial and self._serial.is_open:
            return
        self._serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=0.5,
        )
        # Drain any pending data
        self._serial.reset_input_buffer()

    def close(self):
        """Close serial connection."""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    def _send_chunked(self, data: bytes, drain_echo: bool = False):
        """Send data in 32-byte chunks with 10ms delay to avoid USB FIFO overflow.

        For long commands (e.g. face_add with 1KB+ payload), set drain_echo=True
        to read back echo data between chunks.  This prevents the device's output
        FIFO from filling up and stalling input processing.
        """
        for i in range(0, len(data), CHUNK_SIZE):
            self._serial.write(data[i : i + CHUNK_SIZE])
            self._serial.flush()
            if i + CHUNK_SIZE < len(data):
                time.sleep(CHUNK_DELAY)
                if drain_echo and self._serial.in_waiting > 0:
                    self._serial.read(self._serial.in_waiting)

    def _send_command(
        self,
        cmd_str: str,
        timeout: float = DEFAULT_TIMEOUT,
        drain_echo: bool = False,
    ) -> dict:
        """Send a plain-text command and wait for JSON response.

        Skips echo lines, ESP logs, and REPL prompts.
        Only parses lines starting with '{'.
        Raises TimeoutError if no valid JSON response within timeout.

        Thread-safe: serialized via self._lock to prevent concurrent access
        from corrupting commands/responses on the shared serial port.
        """
        if not self._serial or not self._serial.is_open:
            raise ConnectionError("Serial port not open")

        with self._lock:
            return self._send_command_locked(cmd_str, timeout, drain_echo)

    def _reconnect(self):
        """Close and reopen the serial port to recover from stale state."""
        logger.info("Reconnecting serial port %s", self.port)
        try:
            if self._serial:
                self._serial.close()
        except Exception:
            pass
        self._serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=0.5,
        )
        self._serial.reset_input_buffer()

    def _send_command_locked(
        self,
        cmd_str: str,
        timeout: float,
        drain_echo: bool,
    ) -> dict:
        """Inner send logic, must be called with self._lock held."""
        try:
            return self._try_send(cmd_str, timeout, drain_echo)
        except serial.SerialException as e:
            # Port went stale (device disconnected briefly, FIFO wedged, etc.)
            # Try reconnecting once and retry the command.
            logger.warning(
                "[%s] SerialException: %s — reconnecting", cmd_str.split()[0], e
            )
            try:
                self._reconnect()
                return self._try_send(cmd_str, timeout, drain_echo)
            except Exception as e2:
                raise ConnectionError(f"Serial reconnect failed: {e2}") from e

    def _try_send(
        self,
        cmd_str: str,
        timeout: float,
        drain_echo: bool,
    ) -> dict:
        """Single attempt to send command and read JSON response."""
        # Flush ESP32 REPL state: Ctrl+C aborts any partial input, then
        # drain all pending output (log spam, prompts, ANSI sequences).
        # The old \r\n approach caused command corruption when the REPL's
        # linenoise editor was mid-escape-sequence.
        self._serial.reset_input_buffer()
        self._serial.write(b"\x03\n")  # Ctrl+C + newline
        self._serial.flush()
        time.sleep(0.1)  # 100ms for REPL to settle
        # Drain everything the REPL echoed back
        if self._serial.in_waiting > 0:
            self._serial.read(self._serial.in_waiting)

        # Send command in chunks
        data = (cmd_str + "\n").encode("utf-8")
        self._send_chunked(data, drain_echo=drain_echo)

        # Read response lines, filter for JSON
        cmd_name = cmd_str.split()[0] if cmd_str else "?"
        start = time.time()
        lines_read = 0
        skipped_lines = []
        while time.time() - start < timeout:
            raw = self._serial.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            lines_read += 1

            # Strip ANSI escape codes (cursor movement, clear line, etc.)
            # ESP console linenoise editor injects these into output
            clean = _ANSI_RE.sub("", line).strip()
            if not clean:
                continue

            # Find JSON anywhere in the line (may be after prompt/ANSI residue)
            json_start = clean.find("{")
            if json_start < 0:
                skipped_lines.append(clean[:120])
                continue

            try:
                response = json.loads(clean[json_start:])
                logger.debug(
                    "[%s] response in %.1fs (%d lines): %s",
                    cmd_name,
                    time.time() - start,
                    lines_read,
                    str(response)[:200],
                )
                return response
            except json.JSONDecodeError:
                skipped_lines.append(f"BAD_JSON: {clean[:120]}")
                continue

        logger.warning(
            "[%s] TIMEOUT after %.1fs, read %d lines, content: %s",
            cmd_name,
            time.time() - start,
            lines_read,
            skipped_lines,
        )
        raise TimeoutError(f"No response within {timeout}s for command: {cmd_name}")

    async def list_faces(self) -> dict:
        """List all enrolled faces.

        Returns: {ok: bool, faces: [{name, index}], count, max}
        Decodes hex-encoded names back to Unicode.
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._send_command, "face_list")
        # Decode names
        for face in result.get("faces", []):
            if "name" in face:
                face["name"] = _decode_name(face["name"])
        return result

    async def add_face(self, name: str, embedding: List[float]) -> dict:
        """Add a face to the database.

        Encodes embedding as base64(float16) for compact transfer (~370 bytes
        vs ~1225 bytes CSV). ESP32 detects format automatically.
        Returns: {ok: bool}
        """
        if not embedding:
            return {"ok": False, "error": "Empty embedding"}

        if not self._inference_paused:
            logger.warning(
                "add_face called without inference paused — proceeding anyway (base64 cmd is short)"
            )

        safe_name = _encode_name(name)
        # Encode as float16 + base64 (128 floats → 256 bytes → 344 chars base64)
        raw = struct.pack(f"<{len(embedding)}e", *embedding)
        emb_b64 = base64.b64encode(raw).decode("ascii")
        cmd = f"face_add {safe_name} {emb_b64}"
        logger.info(
            "add_face: name='%s', embedding_dim=%d, cmd_len=%d (base64+fp16)",
            name,
            len(embedding),
            len(cmd),
        )
        loop = asyncio.get_event_loop()
        # Use longer timeout and drain echo for payload
        return await loop.run_in_executor(
            None,
            lambda: self._send_command(cmd, timeout=10.0, drain_echo=True),
        )

    async def delete_face(self, name: str) -> dict:
        """Delete a face from the database.

        Returns: {ok: bool}
        """
        safe_name = _encode_name(name)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._send_command, f"face_delete {safe_name}"
        )

    async def rename_face(self, old_name: str, new_name: str) -> dict:
        """Rename a face in the database.

        Returns: {ok: bool}
        """
        safe_old = _encode_name(old_name)
        safe_new = _encode_name(new_name)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._send_command, f"face_rename {safe_old} {safe_new}"
        )

    async def pause_inference(self) -> dict:
        """Pause ESP32 SPI inference so Himax UART enrollment can work."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._send_command, "inference_pause")
        if result.get("ok"):
            self._inference_paused = True
        return result

    async def resume_inference(self) -> dict:
        """Resume ESP32 SPI inference after enrollment."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._send_command, "inference_resume"
        )
        self._inference_paused = False
        return result

    def resume_inference_nowait(self):
        """Send inference_resume without waiting for response, then close port.

        Used during cleanup (e.g. WebSocket disconnect) to avoid holding the
        serial port open while awaiting a response — which would block new
        sessions from opening the same port.
        """
        self._inference_paused = False
        if not self._serial or not self._serial.is_open:
            return
        try:
            self._serial.write(b"inference_resume\n")
            self._serial.flush()
        except Exception:
            pass
