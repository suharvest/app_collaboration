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
import json
import logging
import time
from typing import List, Optional

import serial

logger = logging.getLogger(__name__)

# Default timeout for serial command responses
DEFAULT_TIMEOUT = 5.0

# USB FIFO chunk size and inter-chunk delay
CHUNK_SIZE = 32
CHUNK_DELAY = 0.01  # 10ms

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
        """
        if not self._serial or not self._serial.is_open:
            raise ConnectionError("Serial port not open")

        # Clear input buffer before sending
        self._serial.reset_input_buffer()

        # Flush any pending input on ESP32 side with a blank line
        if drain_echo:
            self._serial.write(b"\r\n")
            self._serial.flush()
            time.sleep(0.1)
            self._serial.reset_input_buffer()

        # Send command in chunks
        data = (cmd_str + "\n").encode("utf-8")
        self._send_chunked(data, drain_echo=drain_echo)

        # Read response lines, filter for JSON
        cmd_name = cmd_str.split()[0] if cmd_str else "?"
        start = time.time()
        while time.time() - start < timeout:
            raw = self._serial.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            # Only parse lines that look like JSON responses
            if not line.startswith("{"):
                if drain_echo:
                    logger.debug("[%s] echo: %s", cmd_name, line[:120])
                continue

            try:
                response = json.loads(line)
                return response
            except json.JSONDecodeError:
                logger.debug("Failed to parse JSON response: %s", line[:200])
                continue

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

        Embedding is sent as comma-separated floats with 6 decimal places.
        Returns: {ok: bool}
        """
        if not embedding:
            return {"ok": False, "error": "Empty embedding"}

        safe_name = _encode_name(name)
        emb_str = ",".join(f"{x:.6f}" for x in embedding)
        cmd = f"face_add {safe_name} {emb_str}"
        logger.info(
            "add_face: name='%s', embedding_dim=%d, cmd_len=%d, cmd_preview='%s...%s'",
            name,
            len(embedding),
            len(cmd),
            cmd[:60],
            cmd[-30:],
        )
        loop = asyncio.get_event_loop()
        # Use longer timeout and drain echo for large payload
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
